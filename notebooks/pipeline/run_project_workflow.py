# Databricks notebook source
"""Run the DataCo project workflow from one Databricks-compatible entry point.

This notebook is intentionally thin. Reusable Bronze, Silver, feature
engineering, validation, and EDA logic lives in existing project scripts. This
orchestrator only controls order, flags, status messages, and failure handling.
"""

# COMMAND ----------

from __future__ import annotations

import logging
import os
import runpy
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


# Keep these switches simple for Databricks review runs.
RUN_ENV_CHECK = True
RUN_RAW_DATA_CHECK = True
RUN_REFERENCE_REGISTRATION = True
RUN_BRONZE = True
RUN_SILVER = True
RUN_SILVER_VALIDATION = True
RUN_FEATURE_ENGINEERING = True
RUN_SILVER_CSV_EXPORT = True
RUN_PRE_GOLD_GOVERNANCE_CHECKS = True
RUN_EDA = False
RUN_FINAL_CHECKLIST = True

# Feature engineering substeps. These are only considered when
# RUN_FEATURE_ENGINEERING is True.
RUN_ORDER_TIME_FEATURES = True
RUN_SHIPPING_PRODUCT_FEATURES = True
RUN_CUSTOMER_REGIONAL_FEATURES = True

# EDA is optional and disabled by default because broad EDA reruns can overwrite
# report artifacts. Use "check" for artifact validation or "run_python_scripts"
# for the implemented Python EDA scripts.
EDA_ACTION = "check"

LOCAL_SILVER_CSV_RELATIVE_PATH = Path("data/silver/dataco_orders_silver.csv")

EDA_PYTHON_SCRIPTS = (
    Path("notebooks/eda/ao1_bivariate_late_delivery_eda.py"),
    Path("notebooks/eda/ao2_bivariate_profitability_eda.py"),
    Path("notebooks/eda/ao1_class_imbalance_analysis.py"),
)

EXPECTED_EDA_ARTIFACTS = (
    Path("docs/ao1_bivariate_eda.md"),
    Path("docs/ao2_bivariate_eda.md"),
    Path("docs/ao1_class_imbalance_analysis.md"),
    Path("docs/eda_findings_summary.md"),
    Path("report/tables/ao1_late_delivery_bivariate_summary.csv"),
    Path("report/tables/ao2_profitability_bivariate_summary.csv"),
    Path("report/tables/ao1_class_imbalance_overall.csv"),
)


@dataclass
class StepResult:
    """Execution status for one orchestrator step."""

    name: str
    status: str
    required: bool
    detail: str = ""


STEP_RESULTS: list[StepResult] = []


def find_repo_root() -> Path:
    """Find the repo root from Databricks Repos, local execution, or an env var."""
    env_root = os.getenv("DATACO_REPO_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    candidate_roots: list[Path] = []
    try:
        candidate_roots.append(Path(__file__).resolve().parent)
    except NameError:
        pass
    candidate_roots.append(Path.cwd().resolve())

    for starting_point in candidate_roots:
        for candidate in [starting_point, *starting_point.parents]:
            if (
                (candidate / "data" / "references" / "feature_availability_map.csv").exists()
                and (candidate / "src" / "data_engineering" / "ingest_bronze.py").exists()
            ):
                return candidate

    raise FileNotFoundError(
        "Could not find repo root. Set DATACO_REPO_ROOT to the repository checkout path."
    )


REPO_ROOT = find_repo_root()
os.environ.setdefault("DATACO_REPO_ROOT", str(REPO_ROOT))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print(f"Repo root: {REPO_ROOT}")


# COMMAND ----------

from src.data_engineering.clean_silver import (  # noqa: E402
    SilverCleaningConfig,
    configure_logging as configure_silver_logging,
    run_silver_cleaning,
)
from src.data_engineering.engineer_customer_regional_features import (  # noqa: E402
    CustomerRegionalFeatureConfig,
    configure_logging as configure_customer_regional_logging,
    run_customer_regional_feature_engineering,
)
from src.data_engineering.engineer_order_time_features import (  # noqa: E402
    OrderTimeFeatureConfig,
    configure_logging as configure_order_time_logging,
    run_order_time_feature_engineering,
)
from src.data_engineering.engineer_shipping_product_features import (  # noqa: E402
    ShippingProductFeatureConfig,
    configure_logging as configure_shipping_product_logging,
    run_shipping_product_feature_engineering,
)
from src.data_engineering.ingest_bronze import (  # noqa: E402
    BronzeIngestionConfig,
    configure_logging as configure_bronze_logging,
    run_bronze_ingestion,
)
from src.data_engineering.register_feature_availability_map import (  # noqa: E402
    FeatureAvailabilityMapConfig,
    configure_logging as configure_feature_map_logging,
    run_feature_availability_map_registration,
)


def workflow_logger() -> logging.Logger:
    """Return a small orchestration logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.project_workflow")


LOGGER = workflow_logger()


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    active_spark = globals().get("spark")
    if active_spark is not None:
        return active_spark

    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def run_python_file(relative_path: Path) -> None:
    """Execute an existing project Python script by path."""
    script_path = REPO_ROOT / relative_path
    if not script_path.exists():
        raise FileNotFoundError(f"Expected executable script not found: {script_path}")

    runpy.run_path(str(script_path), run_name="__main__")


def databricks_path_exists(path_value: str) -> bool:
    """Return whether a local or Databricks Volume path appears to exist."""
    try:
        if Path(path_value).exists():
            return True
    except OSError:
        pass

    databricks_utils = globals().get("dbutils")
    if databricks_utils is None:
        return False

    try:
        databricks_utils.fs.ls(path_value)
        return True
    except Exception:
        pass

    try:
        path = Path(path_value)
        parent_path = str(path.parent).replace("\\", "/")
        expected_name = path.name.rstrip("/")
        return any(
            item.name.rstrip("/") == expected_name
            for item in databricks_utils.fs.ls(parent_path)
        )
    except Exception:
        return False


def run_step(
    step_name: str,
    enabled: bool,
    action: Callable[[], None],
    *,
    required: bool = True,
) -> None:
    """Run one workflow step with consistent status and failure handling."""
    if not enabled:
        print(f"[SKIP] {step_name}")
        STEP_RESULTS.append(StepResult(step_name, "skipped", required))
        return

    print(f"\n[START] {step_name}")
    try:
        action()
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        STEP_RESULTS.append(StepResult(step_name, "failed", required, detail))
        print(f"[FAIL] {step_name}: {detail}")
        if required:
            raise RuntimeError(f"Project workflow failed during step: {step_name}") from exc
        LOGGER.warning("Optional workflow step failed: %s", step_name, exc_info=True)
        return

    STEP_RESULTS.append(StepResult(step_name, "completed", required))
    print(f"[DONE] {step_name}")


# COMMAND ----------


def validate_databricks_environment() -> None:
    """Validate the repo root and run the existing Databricks smoke test."""
    required_paths = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "data" / "references" / "feature_availability_map.csv",
        REPO_ROOT / "src" / "data_engineering" / "ingest_bronze.py",
    )
    missing_paths = [path for path in required_paths if not path.exists()]
    if missing_paths:
        raise FileNotFoundError(f"Missing expected repository paths: {missing_paths}")

    run_python_file(Path("src/00_test_databricks_env.py"))


def validate_raw_dataset_available() -> None:
    """Validate that the raw DataCo dataset path configured for Bronze exists."""
    config = BronzeIngestionConfig()
    if not databricks_path_exists(config.input_path):
        raise FileNotFoundError(
            "Raw DataCo dataset was not found at "
            f"{config.input_path}. Upload the file or set DATACO_RAW_INPUT_PATH."
        )

    print(f"Raw DataCo dataset available: {config.input_path}")


def register_feature_availability_reference() -> None:
    """Register the feature availability map without changing its contents."""
    run_feature_availability_map_registration(
        FeatureAvailabilityMapConfig(
            input_csv_path=REPO_ROOT / "data/references/feature_availability_map.csv"
        ),
        configure_feature_map_logging(),
    )


def run_bronze() -> None:
    """Run the existing Bronze ingestion job."""
    run_bronze_ingestion(BronzeIngestionConfig(), configure_bronze_logging())


def run_silver() -> None:
    """Run the existing Silver cleaning job."""
    run_silver_cleaning(SilverCleaningConfig(), configure_silver_logging())


def run_silver_validation() -> None:
    """Run the existing Silver quality validation."""
    run_python_file(Path("tests/data_validation/test_silver_quality.py"))


def export_silver_delta_to_local_csv(
    silver_delta_path: str,
    output_csv_path: Path,
) -> None:
    """Export the Silver Delta table to the gitignored local CSV clone path."""
    spark_session = get_spark_session()
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    silver_df = spark_session.read.format("delta").load(silver_delta_path)
    row_count = silver_df.count()

    if output_csv_path.exists():
        output_csv_path.unlink()

    silver_df.toPandas().to_csv(output_csv_path, index=False)
    print(f"Exported {row_count:,} Silver rows to {output_csv_path}")


def run_local_silver_csv_export() -> None:
    """Export the current Silver Delta table for local EDA scripts."""
    export_silver_delta_to_local_csv(
        SilverCleaningConfig().silver_output_path,
        REPO_ROOT / LOCAL_SILVER_CSV_RELATIVE_PATH,
    )


def run_pre_gold_governance_checks() -> None:
    """Run lightweight governance validations for reference documentation."""
    run_python_file(Path("tests/data_validation/validate_silver_schema_dictionary.py"))
    run_python_file(Path("tests/data_validation/validate_leakage_conceptual_screening.py"))


def check_eda_artifacts() -> None:
    """Validate that expected EDA documentation and artifact files exist."""
    missing_artifacts = [
        str(REPO_ROOT / artifact)
        for artifact in EXPECTED_EDA_ARTIFACTS
        if not (REPO_ROOT / artifact).exists()
    ]
    if missing_artifacts:
        raise FileNotFoundError(f"Missing expected EDA artifacts: {missing_artifacts}")

    print("Expected EDA documentation and summary artifacts are present.")


def run_eda_workflow() -> None:
    """Run or validate EDA artifacts depending on EDA_ACTION."""
    if EDA_ACTION == "check":
        check_eda_artifacts()
        return

    if EDA_ACTION == "run_python_scripts":
        for script_path in EDA_PYTHON_SCRIPTS:
            run_python_file(script_path)
        return

    raise ValueError(
        "EDA_ACTION must be either 'check' or 'run_python_scripts'. "
        f"Received: {EDA_ACTION}"
    )


def print_final_checklist() -> None:
    """Print a concise end-of-run checklist for reviewers."""
    print("\nProject workflow execution checklist:")
    for result in STEP_RESULTS:
        required_label = "required" if result.required else "optional"
        detail = f" - {result.detail}" if result.detail else ""
        print(f"- {result.status.upper()}: {result.name} ({required_label}){detail}")

    print("- NOT RUN: Gold/modeling and dashboard exports are outside this orchestrator.")
    print("- REVIEW: Confirm any Databricks path overrides in the PR notes.")
    print("- REVIEW: Update docs/project_orchestrator.md for future executable workflow changes.")


# COMMAND ----------


def main() -> None:
    """Execute the configured project workflow."""
    run_step("Environment validation", RUN_ENV_CHECK, validate_databricks_environment)
    run_step("Raw DataCo dataset availability", RUN_RAW_DATA_CHECK, validate_raw_dataset_available)
    run_step(
        "Feature availability map registration",
        RUN_REFERENCE_REGISTRATION,
        register_feature_availability_reference,
    )
    run_step("Bronze ingestion", RUN_BRONZE, run_bronze)
    run_step("Silver cleaning", RUN_SILVER, run_silver)
    run_step("Silver quality validation", RUN_SILVER_VALIDATION, run_silver_validation)
    run_step(
        "Order-time feature engineering",
        RUN_FEATURE_ENGINEERING and RUN_ORDER_TIME_FEATURES,
        lambda: run_order_time_feature_engineering(
            OrderTimeFeatureConfig(),
            configure_order_time_logging(),
        ),
    )
    run_step(
        "Shipping/product feature engineering",
        RUN_FEATURE_ENGINEERING and RUN_SHIPPING_PRODUCT_FEATURES,
        lambda: run_shipping_product_feature_engineering(
            ShippingProductFeatureConfig(),
            configure_shipping_product_logging(),
        ),
    )
    run_step(
        "Customer/regional feature engineering",
        RUN_FEATURE_ENGINEERING and RUN_CUSTOMER_REGIONAL_FEATURES,
        lambda: run_customer_regional_feature_engineering(
            CustomerRegionalFeatureConfig(),
            configure_customer_regional_logging(),
        ),
    )
    run_step("Local Silver CSV export for EDA", RUN_SILVER_CSV_EXPORT, run_local_silver_csv_export)
    run_step(
        "Pre-Gold governance checks",
        RUN_PRE_GOLD_GOVERNANCE_CHECKS,
        run_pre_gold_governance_checks,
    )
    run_step("EDA artifact workflow", RUN_EDA, run_eda_workflow, required=False)
    run_step("Final execution checklist", RUN_FINAL_CHECKLIST, print_final_checklist, required=False)


if __name__ == "__main__":
    main()
