# Databricks notebook source
# Dependency installation is controlled by RUN_REQUIREMENTS_INSTALL below.
# Do not declare a Databricks Workspace requirements path in notebook metadata:
# each Community Edition user has a different /Workspace/Users/<email>/ path.
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
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


# ============================================================
# Project workflow switches
# ============================================================

# ----------------------------
# 0. Environment and repository checks
# ----------------------------
RUN_REQUIREMENTS_INSTALL = False
RUN_ENV_CHECK = True
RUN_REPO_STRUCTURE_CHECK = True
RUN_VOLUME_SETUP = True
RUN_RAW_DATA_CHECK = True

# ----------------------------
# 1. Reference and governance setup
# ----------------------------
RUN_REFERENCE_REGISTRATION = False
RUN_PRE_GOLD_GOVERNANCE_CHECKS = False

# ----------------------------
# 2. Medallion data pipeline
# ----------------------------
RUN_BRONZE = False
RUN_SILVER = False
RUN_SILVER_VALIDATION = False
RUN_FEATURE_ENGINEERING = False
RUN_GOLD = False

RUN_ORDER_TIME_FEATURES = False
RUN_SHIPPING_PRODUCT_FEATURES = False
RUN_CUSTOMER_REGIONAL_FEATURES = False

RUN_AO1_GOLD = False
RUN_AO2_GOLD = False

# ----------------------------
# 3. Chronological partitions
# ----------------------------
RUN_AO1_PARTITIONS = False
RUN_AO1_PARTITION_VALIDATION = True

RUN_AO2_PARTITIONS = False
RUN_AO2_PARTITION_VALIDATION = True

# ----------------------------
# 4. AO1 modeling workflow
# ----------------------------
RUN_AO1_PREPROCESSING = False
RUN_AO1_PREPROCESSING_VALIDATION = False

RUN_AO1_LOGISTIC_BASELINE = False
RUN_AO1_LOGISTIC_BASELINE_VALIDATION = False

RUN_AO1_XGBOOST_CLASSIFIER = False
RUN_AO1_XGBOOST_CLASSIFIER_VALIDATION = False

RUN_AO1_EVALUATION_PACK = False
RUN_AO1_EVALUATION_PACK_VALIDATION = False

RUN_AO1_SHAP_EXPLAINABILITY = False
RUN_AO1_SHAP_EXPLAINABILITY_VALIDATION = False

RUN_AO1_DECISION_THRESHOLD = False
RUN_AO1_DECISION_THRESHOLD_VALIDATION = False

RUN_AO1_POST_MODEL_LEAKAGE_AUDIT_VALIDATION = False
RUN_AO1_RESULTS_H1_VALIDATION = False

# ----------------------------
# 5. AO2 modeling workflow
# ----------------------------
RUN_AO2_PREPROCESSING = False
RUN_AO2_PREPROCESSING_VALIDATION = False

RUN_AO2_RIDGE_BASELINE = False
RUN_AO2_RIDGE_BASELINE_VALIDATION = False

RUN_AO2_GRADIENT_BOOSTING_REGRESSOR = False
RUN_AO2_GRADIENT_BOOSTING_REGRESSOR_VALIDATION = False

RUN_AO2_EVALUATION_PACK = False
RUN_AO2_EVALUATION_PACK_VALIDATION = False

RUN_AO2_SHAP_EXPLAINABILITY = False
RUN_AO2_SHAP_EXPLAINABILITY_VALIDATION = False

RUN_AO2_TARGET_RECONSTRUCTION_AUDIT = False
RUN_AO2_TARGET_RECONSTRUCTION_AUDIT_VALIDATION = False

RUN_AO2_RESULTS_H2 = False
RUN_AO2_RESULTS_H2_VALIDATION = True

# ----------------------------
# 6. AO3 integration workflow
# ----------------------------
RUN_AO3_RISK_MARGIN_MATRIX_VALIDATION = True

RUN_AO1_AO2_TEST_SCORING = False
RUN_AO1_AO2_TEST_SCORING_VALIDATION = True

RUN_AO3_SEGMENT_ASSIGNMENT = False
RUN_AO3_SEGMENT_ASSIGNMENT_VALIDATION = True

RUN_AO3_RISK_MARGIN_BENCHMARK = False
RUN_AO3_RISK_MARGIN_BENCHMARK_VALIDATION = True

RUN_AO3_KMEANS_EXTENSION = False
RUN_AO3_KMEANS_EXTENSION_VALIDATION = False

# ----------------------------
# 7. EDA, exports, and final checks
# ----------------------------
RUN_EDA = False
RUN_SILVER_CSV_EXPORT = False
RUN_POWERBI_GOLD_EXPORT = False
RUN_POWERBI_GOLD_EXPORT_VALIDATION = True
RUN_FINAL_CHECKLIST = True

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
    Path("src/data_engineering/build_gold_ao2_table.py"),
    Path("src/data_engineering/register_feature_availability_map.py"),
    Path("src/modeling/create_ao1_chronological_partitions.py"),
    Path("src/modeling/create_ao2_chronological_partitions.py"),
    Path("src/modeling/build_ao1_preprocessing_pipeline.py"),
    Path("src/modeling/build_ao2_preprocessing_pipeline.py"),
    Path("src/modeling/train_ao1_logistic_regression_baseline.py"),
    Path("src/modeling/train_ao2_ridge_baseline.py"),
    Path("src/modeling/train_ao2_gradient_boosting_regressor.py"),
    Path("src/modeling/evaluate_ao1_models.py"),
    Path("src/modeling/evaluate_ao2_models.py"),
    Path("src/modeling/train_ao1_xgboost_classifier.py"),
    Path("src/modeling/explain_ao1_xgboost_shap.py"),
    Path("src/modeling/explain_ao2_gradient_boosting_shap.py"),
    Path("src/modeling/audit_ao2_target_reconstruction.py"),
    Path("src/modeling/select_ao1_decision_threshold.py"),
    Path("src/modeling/score_ao1_ao2_test_set.py"),
    Path("src/modeling/build_ao3_risk_margin_segments.py"),
    Path("src/modeling/benchmark_ao3_risk_margin_framework.py"),
    Path("src/modeling/run_ao3_kmeans_extension.py"),
    Path("src/dashboard/export_powerbi_gold_tables.py"),
    Path("tests/data_validation"),
    Path("tests/data_validation/test_silver_quality.py"),
    Path("tests/data_validation/test_gold_ao1_table.py"),
    Path("tests/data_validation/test_gold_ao2_table.py"),
    Path("tests/data_validation/validate_ao1_chronological_partitions.py"),
    Path("tests/data_validation/validate_ao2_chronological_partitions.py"),
    Path("tests/data_validation/validate_ao1_preprocessing_pipeline.py"),
    Path("tests/data_validation/validate_ao2_preprocessing_pipeline.py"),
    Path("tests/data_validation/validate_ao1_logistic_regression_baseline.py"),
    Path("tests/data_validation/validate_ao2_ridge_baseline.py"),
    Path("tests/data_validation/validate_ao2_gradient_boosting_regressor.py"),
    Path("tests/data_validation/validate_ao1_evaluation_pack.py"),
    Path("tests/data_validation/validate_ao2_evaluation_pack.py"),
    Path("tests/data_validation/validate_ao1_xgboost_classifier.py"),
    Path("tests/data_validation/validate_ao1_shap_explainability.py"),
    Path("tests/data_validation/validate_ao2_shap_explainability.py"),
    Path("tests/data_validation/validate_ao2_target_reconstruction_audit.py"),
    Path("tests/data_validation/validate_ao2_results_h2.py"),
    Path("tests/data_validation/validate_ao3_risk_margin_matrix_policy.py"),
    Path("tests/data_validation/validate_ao1_decision_threshold_policy.py"),
    Path("tests/data_validation/validate_ao1_post_model_leakage_audit.py"),
    Path("tests/data_validation/validate_ao1_results_h1.py"),
    Path("tests/data_validation/validate_ao1_ao2_test_scores.py"),
    Path("tests/data_validation/validate_ao3_risk_margin_segments.py"),
    Path("tests/data_validation/validate_ao3_risk_margin_benchmark.py"),
    Path("tests/data_validation/validate_ao3_kmeans_extension.py"),
    Path("tests/data_validation/validate_powerbi_gold_exports.py"),
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


def resolve_requirements_path() -> Path:
    """Resolve the project requirements file without user-specific Workspace paths."""
    override_path = os.getenv("DATACO_REQUIREMENTS_PATH")
    if override_path:
        candidate = Path(override_path).expanduser()
        if local_path_exists(candidate):
            return candidate.resolve()
        raise FileNotFoundError(
            "DATACO_REQUIREMENTS_PATH is set, but the file was not found: "
            f"{candidate}. Point DATACO_REQUIREMENTS_PATH to this repo's requirements.txt."
        )

    candidate_paths = [
        REPO_ROOT / "requirements.txt",
        Path.cwd().resolve() / "requirements.txt",
    ]

    try:
        workflow_path = Path(__file__).resolve()
        candidate_paths.extend(parent / "requirements.txt" for parent in workflow_path.parents)
    except NameError:
        pass

    for candidate in candidate_paths:
        if local_path_exists(candidate):
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not find requirements.txt. Set DATACO_REQUIREMENTS_PATH to the "
        "requirements.txt file in your Databricks repo checkout before enabling "
        "RUN_REQUIREMENTS_INSTALL."
    )


def install_project_requirements() -> None:
    """Install project requirements from a portable, resolved requirements path."""
    requirements_path = resolve_requirements_path()
    print(f"Installing project requirements from: {requirements_path}")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]
    )


if RUN_REQUIREMENTS_INSTALL:
    install_project_requirements()


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
from src.data_engineering.build_gold_ao2_table import (  # noqa: E402
    GoldAO2Config,
    configure_logging as configure_gold_ao2_logging,
    run_gold_ao2_build,
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
from src.modeling.create_ao2_chronological_partitions import (  # noqa: E402
    AO2ChronologicalPartitionConfig,
    configure_logging as configure_ao2_partition_logging,
    run_ao2_chronological_partitioning,
)
from src.modeling.build_ao1_preprocessing_pipeline import (  # noqa: E402
    AO1PreprocessingConfig,
    configure_logging as configure_ao1_preprocessing_logging,
    run_ao1_preprocessing_pipeline,
)
from src.modeling.build_ao2_preprocessing_pipeline import (  # noqa: E402
    AO2PreprocessingConfig,
    configure_logging as configure_ao2_preprocessing_logging,
    run_ao2_preprocessing_pipeline,
)
from src.modeling.train_ao2_ridge_baseline import (  # noqa: E402
    AO2RidgeBaselineConfig,
    configure_logging as configure_ao2_ridge_logging,
    run_ao2_ridge_baseline as run_ao2_ridge_baseline_job,
)
from src.modeling.train_ao2_gradient_boosting_regressor import (  # noqa: E402
    AO2GradientBoostingRegressorConfig,
    configure_logging as configure_ao2_gradient_boosting_logging,
    run_ao2_gradient_boosting_regressor as run_ao2_gradient_boosting_regressor_job,
)
from src.modeling.train_ao1_xgboost_classifier import (  # noqa: E402
    AO1XGBoostClassifierConfig,
    configure_logging as configure_ao1_xgboost_logging,
    run_ao1_xgboost_classifier,
)
from src.modeling.explain_ao1_xgboost_shap import (  # noqa: E402
    AO1SHAPExplainabilityConfig,
    configure_logging as configure_ao1_shap_logging,
    run_ao1_shap_explainability,
)
from src.modeling.explain_ao2_gradient_boosting_shap import (  # noqa: E402
    AO2SHAPExplainabilityConfig,
    configure_logging as configure_ao2_shap_logging,
    run_ao2_shap_explainability,
)
from src.modeling.audit_ao2_target_reconstruction import (  # noqa: E402
    AO2TargetReconstructionAuditConfig,
    configure_logging as configure_ao2_target_reconstruction_logging,
    run_ao2_target_reconstruction_audit,
)
from src.modeling.run_ao3_kmeans_extension import (  # noqa: E402
    AO3KMeansExtensionConfig,
    configure_logging as configure_ao3_kmeans_logging,
    run_ao3_kmeans_extension as run_ao3_kmeans_extension_job,
)
from src.dashboard.export_powerbi_gold_tables import (  # noqa: E402
    PowerBIExportConfig,
    configure_logging as configure_powerbi_export_logging,
    run_powerbi_gold_export,
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
        traceback.print_exc()
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


def run_ao2_gold_validation() -> None:
    """Run the AO2 Gold analytical table quality validation."""
    run_python_file(Path("tests/data_validation/test_gold_ao2_table.py"))


def run_ao1_partition_validation() -> None:
    """Run the AO1 chronological partition validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_chronological_partitions.py"))


def run_ao2_partition_validation() -> None:
    """Run the AO2 chronological partition validation."""
    run_python_file(Path("tests/data_validation/validate_ao2_chronological_partitions.py"))


def run_ao1_preprocessing_validation() -> None:
    """Run the AO1 preprocessing metadata validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_preprocessing_pipeline.py"))


def run_ao2_preprocessing_validation() -> None:
    """Run the AO2 preprocessing metadata validation."""
    run_python_file(Path("tests/data_validation/validate_ao2_preprocessing_pipeline.py"))


def run_ao1_logistic_baseline() -> None:
    """Run the AO1 Logistic Regression baseline training job."""
    run_python_file(Path("src/modeling/train_ao1_logistic_regression_baseline.py"))


def run_ao1_logistic_baseline_validation() -> None:
    """Run the AO1 Logistic Regression baseline artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_logistic_regression_baseline.py"))


def run_ao2_ridge_baseline_training() -> None:
    """Run the AO2 Ridge baseline training job."""
    run_ao2_ridge_baseline_job(
        AO2RidgeBaselineConfig(),
        configure_ao2_ridge_logging(),
    )


def run_ao2_ridge_baseline_validation() -> None:
    """Run the AO2 Ridge baseline artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao2_ridge_baseline.py"))


def run_ao2_gradient_boosting_regressor_training() -> None:
    """Run the AO2 Gradient Boosting regressor training job."""
    run_ao2_gradient_boosting_regressor_job(
        AO2GradientBoostingRegressorConfig(),
        configure_ao2_gradient_boosting_logging(),
    )


def run_ao2_gradient_boosting_regressor_validation() -> None:
    """Run the AO2 Gradient Boosting regressor artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao2_gradient_boosting_regressor.py"))


def run_ao2_evaluation_pack() -> None:
    """Run the AO2 model validation evaluation pack."""
    run_python_file(Path("src/modeling/evaluate_ao2_models.py"))


def run_ao2_evaluation_pack_validation() -> None:
    """Run the AO2 model validation evaluation artifact checks."""
    run_python_file(Path("tests/data_validation/validate_ao2_evaluation_pack.py"))


def run_ao2_shap_validation() -> None:
    """Run the AO2 SHAP explainability artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao2_shap_explainability.py"))


def run_ao2_target_reconstruction_audit_validation() -> None:
    """Run the AO2 target-reconstruction audit artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao2_target_reconstruction_audit.py"))


def check_ao2_results_h2_artifacts() -> None:
    """Validate that manually generated AO2 H2 result artifacts exist."""
    expected_artifacts = (
        Path("docs/ao2_results_h2.md"),
        Path("report/tables/ao2_results_h2_summary.csv"),
        Path("report/tables/ao2_results_h2_findings.md"),
        Path("models/ao2_profitability/results/ao2_results_h2_metadata.json"),
    )
    missing_artifacts = [
        str(REPO_ROOT / artifact)
        for artifact in expected_artifacts
        if not local_path_exists(REPO_ROOT / artifact)
    ]
    if missing_artifacts:
        raise FileNotFoundError(f"Missing AO2 H2 result artifacts: {missing_artifacts}")

    print("AO2 H2 result documentation artifacts are present.")


def run_ao2_results_h2_validation() -> None:
    """Run the AO2 results and H2 artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao2_results_h2.py"))


def run_ao3_risk_margin_matrix_validation() -> None:
    """Run the AO3 risk-margin matrix policy validation."""
    run_python_file(Path("tests/data_validation/validate_ao3_risk_margin_matrix_policy.py"))


def run_ao1_evaluation_pack() -> None:
    """Run the AO1 model validation evaluation pack."""
    run_python_file(Path("src/modeling/evaluate_ao1_models.py"))


def run_ao1_evaluation_pack_validation() -> None:
    """Run the AO1 model validation evaluation artifact checks."""
    run_python_file(Path("tests/data_validation/validate_ao1_evaluation_pack.py"))


def run_ao1_xgboost_validation() -> None:
    """Run the AO1 XGBoost classifier artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_xgboost_classifier.py"))


def run_ao1_shap_validation() -> None:
    """Run the AO1 SHAP explainability artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_shap_explainability.py"))


def run_ao1_decision_threshold_selection() -> None:
    """Run the AO1 decision-threshold selection policy job."""
    run_python_file(Path("src/modeling/select_ao1_decision_threshold.py"))


def run_ao1_decision_threshold_validation() -> None:
    """Run the AO1 decision-threshold policy artifact checks."""
    run_python_file(Path("tests/data_validation/validate_ao1_decision_threshold_policy.py"))


def run_ao1_post_model_leakage_audit_validation() -> None:
    """Run the AO1 post-model leakage audit validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_post_model_leakage_audit.py"))


def run_ao1_results_h1_validation() -> None:
    """Run the AO1 results and H1 validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_results_h1.py"))


def run_ao1_ao2_test_scoring() -> None:
    """Run AO1/AO2 held-out test scoring for AO3 integration."""
    try:
        import xgboost  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency: xgboost. On Databricks Serverless, make sure "
            "the notebook environment installs xgboost==2.0.3 from the "
            "Databricks environment dependencies block, then detach/restart "
            "the Python session before rerunning this workflow."
        ) from exc
    run_python_file(Path("src/modeling/score_ao1_ao2_test_set.py"))


def run_ao1_ao2_test_scoring_validation() -> None:
    """Run AO1/AO2 held-out test score validation."""
    run_python_file(Path("tests/data_validation/validate_ao1_ao2_test_scores.py"))


def run_ao3_segment_assignment() -> None:
    """Run AO3 risk-margin segment assignment."""
    run_python_file(Path("src/modeling/build_ao3_risk_margin_segments.py"))


def run_ao3_segment_assignment_validation() -> None:
    """Run AO3 risk-margin segment validation."""
    run_python_file(Path("tests/data_validation/validate_ao3_risk_margin_segments.py"))


def run_ao3_risk_margin_benchmark() -> None:
    """Run AO3 risk-margin benchmark against single-signal prioritization."""
    run_python_file(Path("src/modeling/benchmark_ao3_risk_margin_framework.py"))


def run_ao3_risk_margin_benchmark_validation() -> None:
    """Run AO3 risk-margin benchmark validation."""
    run_python_file(Path("tests/data_validation/validate_ao3_risk_margin_benchmark.py"))


def run_ao3_kmeans_extension() -> None:
    """Run the optional AO3 K-means clustering extension."""
    run_ao3_kmeans_extension_job(
        AO3KMeansExtensionConfig(),
        configure_ao3_kmeans_logging(),
    )


def run_ao3_kmeans_extension_validation() -> None:
    """Run AO3 K-means extension artifact validation."""
    run_python_file(Path("tests/data_validation/validate_ao3_kmeans_extension.py"))


def run_powerbi_dashboard_export() -> None:
    """Export dashboard-ready Gold outputs for Power BI."""
    run_powerbi_gold_export(PowerBIExportConfig(), configure_powerbi_export_logging())


def run_powerbi_dashboard_export_validation() -> None:
    """Run Power BI export artifact validation."""
    run_python_file(Path("tests/data_validation/validate_powerbi_gold_exports.py"))


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

    print("- NOT RUN: final test-set performance evaluation is outside this orchestrator.")
    print("- OPTIONAL: AO1 chronological partitions run only when RUN_AO1_PARTITIONS is True.")
    print("- OPTIONAL: AO2 chronological partitions run only when RUN_AO2_PARTITIONS is True.")
    print("- OPTIONAL: AO1 preprocessing runs only when RUN_AO1_PREPROCESSING is True.")
    print("- OPTIONAL: AO2 preprocessing runs only when RUN_AO2_PREPROCESSING is True.")
    print("- OPTIONAL: AO2 Ridge baseline runs only when RUN_AO2_RIDGE_BASELINE is True.")
    print("- OPTIONAL: AO2 Gradient Boosting regressor runs only when RUN_AO2_GRADIENT_BOOSTING_REGRESSOR is True.")
    print("- OPTIONAL: AO2 evaluation pack runs only when RUN_AO2_EVALUATION_PACK is True.")
    print("- OPTIONAL: AO2 SHAP explainability runs only when RUN_AO2_SHAP_EXPLAINABILITY is True.")
    print("- OPTIONAL: AO2 target-reconstruction audit runs only when RUN_AO2_TARGET_RECONSTRUCTION_AUDIT is True.")
    print("- OPTIONAL: AO2 H2 result artifact check runs only when RUN_AO2_RESULTS_H2 is True.")
    print("- OPTIONAL: AO2 H2 results validation runs only when RUN_AO2_RESULTS_H2_VALIDATION is True.")
    print("- OPTIONAL: AO3 risk-margin matrix validation runs only when RUN_AO3_RISK_MARGIN_MATRIX_VALIDATION is True.")
    print("- OPTIONAL: AO1 Logistic Regression runs only when RUN_AO1_LOGISTIC_BASELINE is True.")
    print("- OPTIONAL: AO1 evaluation pack runs only when RUN_AO1_EVALUATION_PACK is True.")
    print("- OPTIONAL: AO1 XGBoost runs only when RUN_AO1_XGBOOST_CLASSIFIER is True.")
    print("- OPTIONAL: AO1 SHAP explainability runs only when RUN_AO1_SHAP_EXPLAINABILITY is True.")
    print("- OPTIONAL: AO1 decision threshold runs only when RUN_AO1_DECISION_THRESHOLD is True.")
    print("- OPTIONAL: AO1 post-model leakage audit validation runs only when RUN_AO1_POST_MODEL_LEAKAGE_AUDIT_VALIDATION is True.")
    print("- OPTIONAL: AO1 H1 results validation runs only when RUN_AO1_RESULTS_H1_VALIDATION is True.")
    print("- OPTIONAL: AO1/AO2 test scoring runs only when RUN_AO1_AO2_TEST_SCORING is True.")
    print("- OPTIONAL: AO1/AO2 test score validation runs only when RUN_AO1_AO2_TEST_SCORING_VALIDATION is True.")
    print("- OPTIONAL: AO3 segment assignment runs only when RUN_AO3_SEGMENT_ASSIGNMENT is True.")
    print("- OPTIONAL: AO3 segment validation runs only when RUN_AO3_SEGMENT_ASSIGNMENT_VALIDATION is True.")
    print("- OPTIONAL: AO3 risk-margin benchmark runs only when RUN_AO3_RISK_MARGIN_BENCHMARK is True.")
    print("- OPTIONAL: AO3 risk-margin benchmark validation runs only when RUN_AO3_RISK_MARGIN_BENCHMARK_VALIDATION is True.")
    print("- OPTIONAL: AO3 K-means extension runs only when RUN_AO3_KMEANS_EXTENSION is True.")
    print("- OPTIONAL: AO3 K-means extension validation runs only when RUN_AO3_KMEANS_EXTENSION_VALIDATION is True.")
    print("- OPTIONAL: Power BI Gold export runs only when RUN_POWERBI_GOLD_EXPORT is True.")
    print("- OPTIONAL: Power BI Gold export validation runs only when RUN_POWERBI_GOLD_EXPORT_VALIDATION is True.")
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
    gold_ao2_config = GoldAO2Config()
    ao1_partition_config = AO1ChronologicalPartitionConfig()
    ao2_partition_config = AO2ChronologicalPartitionConfig()
    ao1_preprocessing_config = AO1PreprocessingConfig()
    ao2_preprocessing_config = AO2PreprocessingConfig()
    ao2_ridge_config = AO2RidgeBaselineConfig()
    ao2_gradient_boosting_config = AO2GradientBoostingRegressorConfig()
    ao1_xgboost_config = AO1XGBoostClassifierConfig()
    ao1_shap_config = AO1SHAPExplainabilityConfig()
    ao2_shap_config = AO2SHAPExplainabilityConfig()
    ao2_target_reconstruction_config = AO2TargetReconstructionAuditConfig()
    ao3_kmeans_config = AO3KMeansExtensionConfig()
    powerbi_export_config = PowerBIExportConfig()

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
    print(f"- AO2 Gold analytical table Delta: {gold_ao2_config.gold_output_path}")
    print(f"- AO1 chronological partitions Delta: {ao1_partition_config.partition_output_path}")
    print(f"- AO2 chronological partitions Delta: {ao2_partition_config.partition_output_path}")
    print(f"- AO1 preprocessing metadata: {ao1_preprocessing_config.metadata_output_path}")
    print(f"- AO2 preprocessing metadata: {ao2_preprocessing_config.metadata_output_path}")
    print(f"- AO2 Ridge baseline metadata: {ao2_ridge_config.metadata_json_path}")
    print(f"- AO2 Ridge validation predictions: {ao2_ridge_config.validation_predictions_csv_path}")
    print(f"- AO2 Gradient Boosting metadata: {ao2_gradient_boosting_config.metadata_json_path}")
    print(f"- AO2 Gradient Boosting validation predictions: {ao2_gradient_boosting_config.validation_predictions_csv_path}")
    print("- AO2 evaluation metadata: models/ao2_profitability/evaluation/ao2_evaluation_metadata.json")
    print(f"- AO2 SHAP driver summary: {ao2_shap_config.driver_summary_output_path}")
    print(f"- AO2 target-reconstruction audit metadata: {ao2_target_reconstruction_config.metadata_output_path}")
    print("- AO2 H2 results metadata: models/ao2_profitability/results/ao2_results_h2_metadata.json")
    print("- AO2 H2 results summary: report/tables/ao2_results_h2_summary.csv")
    print("- AO3 risk-margin matrix policy: data/references/ao3_risk_margin_matrix_policy.csv")
    print("- AO1 Logistic Regression metadata: models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_metadata.json")
    print("- AO1 evaluation metadata: models/ao1_late_delivery/evaluation/ao1_evaluation_metadata.json")
    print(f"- AO1 XGBoost metadata: {ao1_xgboost_config.metadata_json_path}")
    print(f"- AO1 XGBoost validation predictions: {ao1_xgboost_config.validation_predictions_csv_path}")
    print(f"- AO1 SHAP driver summary: {ao1_shap_config.driver_summary_output_path}")
    print("- AO1 decision threshold policy: data/references/ao1_decision_threshold_policy.csv")
    print("- AO1 post-model leakage audit: data/references/ao1_post_model_leakage_audit.csv")
    print("- AO1 H1 results summary: data/references/ao1_results_h1_summary.csv")
    print(f"- AO1/AO2 test score Delta: {VOLUME_ROOT}/gold/ao1_ao2_test_scores")
    print("- AO1/AO2 test score metadata: models/ao3_integration/ao1_ao2_test_scores/ao1_ao2_test_score_metadata.json")
    print(f"- AO3 risk-margin segments Delta: {VOLUME_ROOT}/gold/ao3_risk_margin_segments")
    print("- AO3 segment assignment metadata: models/ao3_integration/risk_margin_segments/ao3_segment_assignment_metadata.json")
    print("- AO3 risk-margin benchmark metadata: models/ao3_integration/risk_margin_benchmark/ao3_risk_margin_benchmark_metadata.json")
    print("- AO3 risk-margin benchmark insights: data/references/ao3_risk_margin_benchmark_insights.csv")
    print(f"- AO3 K-means extension metadata: {ao3_kmeans_config.metadata_output_path}")
    print(f"- AO3 K-means cluster profiles: {ao3_kmeans_config.cluster_profiles_output_path}")
    print(f"- Power BI dashboard export folder: {powerbi_export_config.export_root}")
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
        "AO2 Gold analytical table build",
        RUN_GOLD and RUN_AO2_GOLD,
        lambda: run_gold_ao2_build(GoldAO2Config(), configure_gold_ao2_logging()),
    )
    run_step("AO2 Gold quality validation", RUN_GOLD and RUN_AO2_GOLD, run_ao2_gold_validation)
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
        "AO2 chronological partition creation",
        RUN_AO2_PARTITIONS,
        lambda: run_ao2_chronological_partitioning(
            AO2ChronologicalPartitionConfig(),
            configure_ao2_partition_logging(),
        ),
        required=RUN_AO2_PARTITIONS,
    )
    run_step(
        "AO2 chronological partition validation",
        RUN_AO2_PARTITIONS and RUN_AO2_PARTITION_VALIDATION,
        run_ao2_partition_validation,
        required=RUN_AO2_PARTITIONS and RUN_AO2_PARTITION_VALIDATION,
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
        "AO2 preprocessing pipeline build",
        RUN_AO2_PREPROCESSING,
        lambda: run_ao2_preprocessing_pipeline(
            AO2PreprocessingConfig(),
            configure_ao2_preprocessing_logging(),
        ),
        required=RUN_AO2_PREPROCESSING,
    )
    run_step(
        "AO2 preprocessing pipeline validation",
        RUN_AO2_PREPROCESSING and RUN_AO2_PREPROCESSING_VALIDATION,
        run_ao2_preprocessing_validation,
        required=RUN_AO2_PREPROCESSING and RUN_AO2_PREPROCESSING_VALIDATION,
    )
    run_step(
        "AO2 Ridge baseline training",
        RUN_AO2_RIDGE_BASELINE,
        run_ao2_ridge_baseline_training,
        required=RUN_AO2_RIDGE_BASELINE,
    )
    run_step(
        "AO2 Ridge baseline validation",
        RUN_AO2_RIDGE_BASELINE and RUN_AO2_RIDGE_BASELINE_VALIDATION,
        run_ao2_ridge_baseline_validation,
        required=RUN_AO2_RIDGE_BASELINE and RUN_AO2_RIDGE_BASELINE_VALIDATION,
    )
    run_step(
        "AO2 Gradient Boosting regressor training",
        RUN_AO2_GRADIENT_BOOSTING_REGRESSOR,
        run_ao2_gradient_boosting_regressor_training,
        required=RUN_AO2_GRADIENT_BOOSTING_REGRESSOR,
    )
    run_step(
        "AO2 Gradient Boosting regressor validation",
        RUN_AO2_GRADIENT_BOOSTING_REGRESSOR and RUN_AO2_GRADIENT_BOOSTING_REGRESSOR_VALIDATION,
        run_ao2_gradient_boosting_regressor_validation,
        required=RUN_AO2_GRADIENT_BOOSTING_REGRESSOR
        and RUN_AO2_GRADIENT_BOOSTING_REGRESSOR_VALIDATION,
    )
    run_step(
        "AO2 model evaluation pack",
        RUN_AO2_EVALUATION_PACK,
        run_ao2_evaluation_pack,
        required=RUN_AO2_EVALUATION_PACK,
    )
    run_step(
        "AO2 model evaluation pack validation",
        RUN_AO2_EVALUATION_PACK and RUN_AO2_EVALUATION_PACK_VALIDATION,
        run_ao2_evaluation_pack_validation,
        required=RUN_AO2_EVALUATION_PACK and RUN_AO2_EVALUATION_PACK_VALIDATION,
    )
    run_step(
        "AO2 SHAP explainability",
        RUN_AO2_SHAP_EXPLAINABILITY,
        lambda: run_ao2_shap_explainability(
            AO2SHAPExplainabilityConfig(),
            configure_ao2_shap_logging(),
        ),
        required=RUN_AO2_SHAP_EXPLAINABILITY,
    )
    run_step(
        "AO2 SHAP explainability validation",
        RUN_AO2_SHAP_EXPLAINABILITY and RUN_AO2_SHAP_EXPLAINABILITY_VALIDATION,
        run_ao2_shap_validation,
        required=RUN_AO2_SHAP_EXPLAINABILITY and RUN_AO2_SHAP_EXPLAINABILITY_VALIDATION,
    )
    run_step(
        "AO2 target-reconstruction audit",
        RUN_AO2_TARGET_RECONSTRUCTION_AUDIT,
        lambda: run_ao2_target_reconstruction_audit(
            AO2TargetReconstructionAuditConfig(),
            configure_ao2_target_reconstruction_logging(),
        ),
        required=RUN_AO2_TARGET_RECONSTRUCTION_AUDIT,
    )
    run_step(
        "AO2 target-reconstruction audit validation",
        RUN_AO2_TARGET_RECONSTRUCTION_AUDIT
        and RUN_AO2_TARGET_RECONSTRUCTION_AUDIT_VALIDATION,
        run_ao2_target_reconstruction_audit_validation,
        required=RUN_AO2_TARGET_RECONSTRUCTION_AUDIT
        and RUN_AO2_TARGET_RECONSTRUCTION_AUDIT_VALIDATION,
    )
    run_step(
        "AO2 H2 result artifact check",
        RUN_AO2_RESULTS_H2,
        check_ao2_results_h2_artifacts,
        required=RUN_AO2_RESULTS_H2,
    )
    run_step(
        "AO2 H2 results validation",
        RUN_AO2_RESULTS_H2_VALIDATION,
        run_ao2_results_h2_validation,
        required=RUN_AO2_RESULTS_H2_VALIDATION,
    )
    run_step(
        "AO3 risk-margin matrix validation",
        RUN_AO3_RISK_MARGIN_MATRIX_VALIDATION,
        run_ao3_risk_margin_matrix_validation,
        required=RUN_AO3_RISK_MARGIN_MATRIX_VALIDATION,
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
    run_step(
        "AO1 XGBoost classifier training",
        RUN_AO1_XGBOOST_CLASSIFIER,
        lambda: run_ao1_xgboost_classifier(
            AO1XGBoostClassifierConfig(),
            configure_ao1_xgboost_logging(),
        ),
        required=RUN_AO1_XGBOOST_CLASSIFIER,
    )
    run_step(
        "AO1 XGBoost classifier validation",
        RUN_AO1_XGBOOST_CLASSIFIER and RUN_AO1_XGBOOST_CLASSIFIER_VALIDATION,
        run_ao1_xgboost_validation,
        required=RUN_AO1_XGBOOST_CLASSIFIER and RUN_AO1_XGBOOST_CLASSIFIER_VALIDATION,
    )
    run_step(
        "AO1 SHAP explainability",
        RUN_AO1_SHAP_EXPLAINABILITY,
        lambda: run_ao1_shap_explainability(
            AO1SHAPExplainabilityConfig(),
            configure_ao1_shap_logging(),
        ),
        required=RUN_AO1_SHAP_EXPLAINABILITY,
    )
    run_step(
        "AO1 SHAP explainability validation",
        RUN_AO1_SHAP_EXPLAINABILITY and RUN_AO1_SHAP_EXPLAINABILITY_VALIDATION,
        run_ao1_shap_validation,
        required=RUN_AO1_SHAP_EXPLAINABILITY and RUN_AO1_SHAP_EXPLAINABILITY_VALIDATION,
    )
    run_step(
        "AO1 model evaluation pack",
        RUN_AO1_EVALUATION_PACK,
        run_ao1_evaluation_pack,
        required=RUN_AO1_EVALUATION_PACK,
    )
    run_step(
        "AO1 model evaluation pack validation",
        RUN_AO1_EVALUATION_PACK and RUN_AO1_EVALUATION_PACK_VALIDATION,
        run_ao1_evaluation_pack_validation,
        required=RUN_AO1_EVALUATION_PACK and RUN_AO1_EVALUATION_PACK_VALIDATION,
    )
    run_step(
        "AO1 decision threshold selection",
        RUN_AO1_DECISION_THRESHOLD,
        run_ao1_decision_threshold_selection,
        required=RUN_AO1_DECISION_THRESHOLD,
    )
    run_step(
        "AO1 decision threshold validation",
        RUN_AO1_DECISION_THRESHOLD and RUN_AO1_DECISION_THRESHOLD_VALIDATION,
        run_ao1_decision_threshold_validation,
        required=RUN_AO1_DECISION_THRESHOLD and RUN_AO1_DECISION_THRESHOLD_VALIDATION,
    )
    run_step(
        "AO1 post-model leakage audit validation",
        RUN_AO1_POST_MODEL_LEAKAGE_AUDIT_VALIDATION,
        run_ao1_post_model_leakage_audit_validation,
        required=RUN_AO1_POST_MODEL_LEAKAGE_AUDIT_VALIDATION,
    )
    run_step(
        "AO1 H1 results validation",
        RUN_AO1_RESULTS_H1_VALIDATION,
        run_ao1_results_h1_validation,
        required=RUN_AO1_RESULTS_H1_VALIDATION,
    )
    run_step(
        "AO1/AO2 held-out test scoring",
        RUN_AO1_AO2_TEST_SCORING,
        run_ao1_ao2_test_scoring,
        required=RUN_AO1_AO2_TEST_SCORING,
    )
    run_step(
        "AO1/AO2 held-out test score validation",
        RUN_AO1_AO2_TEST_SCORING and RUN_AO1_AO2_TEST_SCORING_VALIDATION,
        run_ao1_ao2_test_scoring_validation,
        required=RUN_AO1_AO2_TEST_SCORING and RUN_AO1_AO2_TEST_SCORING_VALIDATION,
    )
    run_step(
        "AO3 risk-margin segment assignment",
        RUN_AO3_SEGMENT_ASSIGNMENT,
        run_ao3_segment_assignment,
        required=RUN_AO3_SEGMENT_ASSIGNMENT,
    )
    run_step(
        "AO3 risk-margin segment validation",
        RUN_AO3_SEGMENT_ASSIGNMENT and RUN_AO3_SEGMENT_ASSIGNMENT_VALIDATION,
        run_ao3_segment_assignment_validation,
        required=RUN_AO3_SEGMENT_ASSIGNMENT and RUN_AO3_SEGMENT_ASSIGNMENT_VALIDATION,
    )
    run_step(
        "AO3 risk-margin benchmark",
        RUN_AO3_RISK_MARGIN_BENCHMARK,
        run_ao3_risk_margin_benchmark,
        required=RUN_AO3_RISK_MARGIN_BENCHMARK,
    )
    run_step(
        "AO3 risk-margin benchmark validation",
        RUN_AO3_RISK_MARGIN_BENCHMARK and RUN_AO3_RISK_MARGIN_BENCHMARK_VALIDATION,
        run_ao3_risk_margin_benchmark_validation,
        required=RUN_AO3_RISK_MARGIN_BENCHMARK and RUN_AO3_RISK_MARGIN_BENCHMARK_VALIDATION,
    )
    run_step(
        "AO3 K-means optional extension",
        RUN_AO3_KMEANS_EXTENSION,
        run_ao3_kmeans_extension,
        required=False,
    )
    run_step(
        "AO3 K-means optional extension validation",
        RUN_AO3_KMEANS_EXTENSION and RUN_AO3_KMEANS_EXTENSION_VALIDATION,
        run_ao3_kmeans_extension_validation,
        required=False,
    )
    run_step(
        "Power BI Gold dashboard export",
        RUN_POWERBI_GOLD_EXPORT,
        run_powerbi_dashboard_export,
        required=RUN_POWERBI_GOLD_EXPORT,
    )
    run_step(
        "Power BI Gold dashboard export validation",
        RUN_POWERBI_GOLD_EXPORT and RUN_POWERBI_GOLD_EXPORT_VALIDATION,
        run_powerbi_dashboard_export_validation,
        required=RUN_POWERBI_GOLD_EXPORT and RUN_POWERBI_GOLD_EXPORT_VALIDATION,
    )
    run_step("Local Silver CSV export for EDA", RUN_SILVER_CSV_EXPORT, run_local_silver_csv_export)
    run_step("EDA artifact workflow", RUN_EDA, run_eda_workflow, required=False)
    run_step("Final execution checklist", RUN_FINAL_CHECKLIST, print_final_checklist, required=False)


if __name__ == "__main__":
    main()
