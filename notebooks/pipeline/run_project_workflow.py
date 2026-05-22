# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "2"
# ///
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
RUN_REPO_STRUCTURE_CHECK = True
RUN_VOLUME_SETUP = True
RUN_RAW_DATA_CHECK = True
RUN_REFERENCE_REGISTRATION = True
RUN_BRONZE = True
RUN_SILVER = True
RUN_SILVER_VALIDATION = True
RUN_FEATURE_ENGINEERING = True
RUN_GOLD = True
RUN_AO1_PARTITIONS = True
RUN_AO1_PARTITION_VALIDATION = True
RUN_AO1_PREPROCESSING = True
RUN_AO1_PREPROCESSING_VALIDATION = True
RUN_AO1_LOGISTIC_BASELINE = True
RUN_AO1_LOGISTIC_BASELINE_VALIDATION = True
RUN_SILVER_CSV_EXPORT = True
RUN_PRE_GOLD_GOVERNANCE_CHECKS = True
RUN_EDA = False
RUN_FINAL_CHECKLIST = True

# Feature engineering substeps. These are only considered when
# RUN_FEATURE_ENGINEERING is True.
RUN_ORDER_TIME_FEATURES = True
RUN_SHIPPING_PRODUCT_FEATURES = True
RUN_CUSTOMER_REGIONAL_FEATURES = True
RUN_AO1_GOLD = True

# EDA is optional and disabled by default because broad EDA reruns can overwrite
# report artifacts. Use "check" for artifact validation or "run_python_scripts"
# for the implemented Python EDA scripts.
EDA_ACTION = "check"

LOCAL_SILVER_CSV_RELATIVE_PATH = Path("data/silver/dataco_orders_silver.csv")

VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

STANDARD_VOLUME_DIRECTORIES = (
    VOLUME_ROOT,
    f"{VOLUME_ROOT}/bronze",
    f"{VOLUME_ROOT}/silver",
    f"{VOLUME_ROOT}/gold",
    f"{VOLUME_ROOT}/references",
    f"{VOLUME_ROOT}/eda",
)

REQUIRED_REPOSITORY_PATHS = (
    Path("README.md"),
    Path("docs/project_orchestrator.md"),
    Path("data/references/feature_availability_map.csv"),
    Path("src/00_test_databricks_env.py"),
    Path("src/data_engineering"),
    Path("src/data_engineering/ingest_bronze.py"),
    Path("src/data_engineering/clean_silver.py"),
    Path("src/data_engineering/engineer_order_time_features.py"),
    Path("src/data_engineering/engineer_shipping_product_features.py"),
    Path("src/data_engineering/engineer_customer_regional_features.py"),
    Path("src/data_engineering/build_gold_ao1_table.py"),
    Path("src/data_engineering/register_feature_availability_map.py"),
    Path("src/modeling/create_ao1_chronological_partitions.py"),
    Path("src/modeling/build_ao1_preprocessing_pipeline.py"),
    Path("src/modeling/train_ao1_logistic_regression_baseline.py"),
    Path("tests/data_validation"),
    Path("tests/data_validation/test_silver_quality.py"),
    Path("tests/data_validation/test_gold_ao1_table.py"),
    Path("tests/data_validation/validate_ao1_chronological_partitions.py"),
    Path("tests/data_validation/validate_ao1_preprocessing_pipeline.py"),
    Path("tests/data_validation/validate_ao1_logistic_regression_baseline.py"),
    Path("notebooks/eda"),
    Path("notebooks/pipeline"),
)

EDA_PYTHON_SCRIPTS = (
    Path("notebooks/eda/eda_univariate_distribution_analysis.py"),
    Path("notebooks/eda/ao1_bivariate_late_delivery_eda.py"),
    Path("notebooks/eda/ao2_bivariate_profitability_eda.py"),
    Path("notebooks/eda/ao1_class_imbalance_analysis.py"),
)

EXPECTED_EDA_ARTIFACTS = (
    Path("report/tables/eda_univariate_summary.csv"),
    Path("report/tables/univariate_distribution_eda_findings.md"),
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


def local_path_exists(path: Path) -> bool:
    """Return whether a local path exists, treating inaccessible probes as absent."""
    try:
        return path.exists()
    except OSError:
        return False


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
                local_path_exists(
                    candidate / "data" / "references" / "feature_availability_map.csv"
                )
                and local_path_exists(
                    candidate / "src" / "data_engineering" / "ingest_bronze.py"
                )
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
from src.data_engineering.build_gold_ao1_table import (  # noqa: E402
    GoldAO1Config,
    configure_logging as configure_gold_ao1_logging,
    run_gold_ao1_build,
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
from src.modeling.create_ao1_chronological_partitions import (  # noqa: E402
    AO1ChronologicalPartitionConfig,
    configure_logging as configure_ao1_partition_logging,
    run_ao1_chronological_partitioning,
)
from src.modeling.build_ao1_preprocessing_pipeline import (  # noqa: E402
    AO1PreprocessingConfig,
    configure_logging as configure_ao1_preprocessing_logging,
    run_ao1_preprocessing_pipeline,
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
    if not local_path_exists(script_path):
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


def create_databricks_directory(path_value: str) -> None:
    """Create a Databricks Volume directory when running in Databricks."""
    databricks_utils = globals().get("dbutils")
    if databricks_utils is not None:
        databricks_utils.fs.mkdirs(path_value)
        return

    if path_value.startswith("/Volumes/"):
        raise RuntimeError(
            "Databricks dbutils is required to create Unity Catalog Volume paths. "
            f"Run this step in Databricks or disable RUN_VOLUME_SETUP. Path: {path_value}"
        )

    Path(path_value).mkdir(parents=True, exist_ok=True)


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
    run_python_file(Path("src/00_test_databricks_env.py"))


def validate_repository_structure() -> None:
    """Validate that Databricks is running against the full repository checkout."""
    missing_paths = [
        str(REPO_ROOT / relative_path)
        for relative_path in REQUIRED_REPOSITORY_PATHS
        if not local_path_exists(REPO_ROOT / relative_path)
    ]
    if missing_paths:
        raise FileNotFoundError(
            "Missing expected repository paths. Run from the full repository checkout "
            "or set DATACO_REPO_ROOT to the repository root. Missing paths: "
            f"{missing_paths}"
        )

    print("Required repository folders, scripts, tests, and reference files are present.")


def setup_standard_volume_directories() -> None:
    """Create and validate the standard Databricks Volume directory layout."""
    for directory_path in STANDARD_VOLUME_DIRECTORIES:
        create_databricks_directory(directory_path)

    missing_directories = [
        directory_path
        for directory_path in STANDARD_VOLUME_DIRECTORIES
        if not databricks_path_exists(directory_path)
    ]
    if missing_directories:
        raise FileNotFoundError(
            f"Standard Databricks Volume directories were not created: {missing_directories}"
        )

    print("Standard Databricks Volume directories are available:")
    for directory_path in STANDARD_VOLUME_DIRECTORIES:
        print(f"- {directory_path}")


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


def run_ao1_gold_validation() -> None:
    """Run the AO1 Gold analytical table quality validation."""
    run_python_file(Path("tests/data_validation/test_gold_ao1_table.py"))


def run_ao1_partition_validation() -> None:
    """Run the AO1 chronological partition validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_chronological_partitions.py"))


def run_ao1_preprocessing_validation() -> None:
    """Run the AO1 preprocessing metadata validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_preprocessing_pipeline.py"))


def run_ao1_logistic_baseline() -> None:
    """Run the AO1 Logistic Regression baseline training job."""
    run_python_file(Path("src/modeling/train_ao1_logistic_regression_baseline.py"))


def run_ao1_logistic_baseline_validation() -> None:
    """Run the AO1 Logistic Regression baseline artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_logistic_regression_baseline.py"))


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

    print("- NOT RUN: AO2 Gold, modeling, scoring, and dashboard exports are outside this orchestrator.")
    print("- OPTIONAL: AO1 chronological partitions run only when RUN_AO1_PARTITIONS is True.")
    print("- OPTIONAL: AO1 preprocessing runs only when RUN_AO1_PREPROCESSING is True.")
    print("- OPTIONAL: AO1 Logistic Regression runs only when RUN_AO1_LOGISTIC_BASELINE is True.")
    print("- REVIEW: Confirm any Databricks path overrides in the PR notes.")
    print("- REVIEW: Update docs/project_orchestrator.md for future executable workflow changes.")

    bronze_config = BronzeIngestionConfig()
    silver_config = SilverCleaningConfig()
    feature_map_config = FeatureAvailabilityMapConfig(
        input_csv_path=REPO_ROOT / "data/references/feature_availability_map.csv"
    )
    order_time_config = OrderTimeFeatureConfig()
    shipping_product_config = ShippingProductFeatureConfig()
    customer_regional_config = CustomerRegionalFeatureConfig()
    gold_ao1_config = GoldAO1Config()
    ao1_partition_config = AO1ChronologicalPartitionConfig()
    ao1_preprocessing_config = AO1PreprocessingConfig()

    print("\nPrimary workflow output paths:")
    print(f"- Volume root: {VOLUME_ROOT}")
    print(f"- Raw DataCo CSV: {bronze_config.input_path}")
    print(f"- Bronze Delta: {bronze_config.output_path}")
    print(f"- Bronze column mapping Delta: {bronze_config.column_mapping_output_path}")
    print(f"- Feature availability map Delta: {feature_map_config.delta_output_path}")
    print(f"- Silver Delta: {silver_config.silver_output_path}")
    print(f"- Silver quality report Delta: {silver_config.quality_report_output_path}")
    print(f"- Order-time features Delta: {order_time_config.feature_output_path}")
    print(f"- Shipping/product features Delta: {shipping_product_config.feature_output_path}")
    print(f"- Customer/regional features Delta: {customer_regional_config.feature_output_path}")
    print(f"- AO1 Gold analytical table Delta: {gold_ao1_config.gold_output_path}")
    print(f"- AO1 chronological partitions Delta: {ao1_partition_config.partition_output_path}")
    print(f"- AO1 preprocessing metadata: {ao1_preprocessing_config.metadata_output_path}")
    print("- AO1 Logistic Regression metadata: models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_metadata.json")
    print(f"- Local Silver CSV clone: {REPO_ROOT / LOCAL_SILVER_CSV_RELATIVE_PATH}")


# COMMAND ----------


def main() -> None:
    """Execute the configured project workflow."""
    run_step("Environment validation", RUN_ENV_CHECK, validate_databricks_environment)
    run_step(
        "Repository structure validation",
        RUN_REPO_STRUCTURE_CHECK,
        validate_repository_structure,
    )
    run_step(
        "Databricks Volume directory setup",
        RUN_VOLUME_SETUP,
        setup_standard_volume_directories,
    )
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
    run_step(
        "Pre-Gold governance checks",
        RUN_PRE_GOLD_GOVERNANCE_CHECKS,
        run_pre_gold_governance_checks,
    )
    run_step(
        "AO1 Gold analytical table build",
        RUN_GOLD and RUN_AO1_GOLD,
        lambda: run_gold_ao1_build(GoldAO1Config(), configure_gold_ao1_logging()),
    )
    run_step("AO1 Gold quality validation", RUN_GOLD and RUN_AO1_GOLD, run_ao1_gold_validation)
    run_step(
        "AO1 chronological partition creation",
        RUN_AO1_PARTITIONS,
        lambda: run_ao1_chronological_partitioning(
            AO1ChronologicalPartitionConfig(),
            configure_ao1_partition_logging(),
        ),
        required=RUN_AO1_PARTITIONS,
    )
    run_step(
        "AO1 chronological partition validation",
        RUN_AO1_PARTITIONS and RUN_AO1_PARTITION_VALIDATION,
        run_ao1_partition_validation,
        required=RUN_AO1_PARTITIONS and RUN_AO1_PARTITION_VALIDATION,
    )
    run_step(
        "AO1 preprocessing pipeline build",
        RUN_AO1_PREPROCESSING,
        lambda: run_ao1_preprocessing_pipeline(
            AO1PreprocessingConfig(),
            configure_ao1_preprocessing_logging(),
        ),
        required=RUN_AO1_PREPROCESSING,
    )
    run_step(
        "AO1 preprocessing pipeline validation",
        RUN_AO1_PREPROCESSING and RUN_AO1_PREPROCESSING_VALIDATION,
        run_ao1_preprocessing_validation,
        required=RUN_AO1_PREPROCESSING and RUN_AO1_PREPROCESSING_VALIDATION,
    )
    run_step(
        "AO1 Logistic Regression baseline training",
        RUN_AO1_LOGISTIC_BASELINE,
        run_ao1_logistic_baseline,
        required=RUN_AO1_LOGISTIC_BASELINE,
    )
    run_step(
        "AO1 Logistic Regression baseline validation",
        RUN_AO1_LOGISTIC_BASELINE and RUN_AO1_LOGISTIC_BASELINE_VALIDATION,
        run_ao1_logistic_baseline_validation,
        required=RUN_AO1_LOGISTIC_BASELINE and RUN_AO1_LOGISTIC_BASELINE_VALIDATION,
    )
    run_step("Local Silver CSV export for EDA", RUN_SILVER_CSV_EXPORT, run_local_silver_csv_export)
    run_step("EDA artifact workflow", RUN_EDA, run_eda_workflow, required=False)
    run_step("Final execution checklist", RUN_FINAL_CHECKLIST, print_final_checklist, required=False)


if __name__ == "__main__":
    main()
