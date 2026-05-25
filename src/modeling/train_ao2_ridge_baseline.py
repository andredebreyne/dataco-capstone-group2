"""Train the AO2 Ridge Regression validation baseline.

This job consumes the official AO2 chronological partition table, creates a
time-preserving validation slice inside development when needed, fits the
approved AO2 preprocessing pipeline only on the training slice, and evaluates
Ridge Regression on validation only. The final test partition is never used for
fitting, model selection, residual review, or validation metrics here.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.modeling.build_ao2_preprocessing_pipeline import (
    FEATURE_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS,
    build_sklearn_preprocessor,
)
from src.modeling.create_ao2_chronological_partitions import (
    AO2_PARTITION_OUTPUT_PATH,
    DEVELOPMENT_LABEL,
    JOIN_KEY_COLUMNS,
    ORDERING_COLUMNS,
    PARTITION_COLUMN,
    ROW_NUMBER_COLUMN,
    TARGET_COLUMN,
    TEST_LABEL,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

TRAIN_LABEL = "train"
VALIDATION_LABEL = "validation"
INNER_TRAIN_LABEL = "development_inner_train"
INNER_VALIDATION_LABEL = "development_inner_validation"
MODEL_NAME = "ao2_ridge_baseline"

REQUIRED_INPUT_COLUMNS = (
    *JOIN_KEY_COLUMNS,
    TARGET_COLUMN,
    PARTITION_COLUMN,
    ROW_NUMBER_COLUMN,
)

EXCLUDED_IDENTIFIER_METADATA_COLUMNS = (
    *JOIN_KEY_COLUMNS,
    ROW_NUMBER_COLUMN,
    PARTITION_COLUMN,
    "_gold_ao2_processed_timestamp",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")


def resolve_repo_root() -> Path:
    """Resolve repository root for local and Databricks notebook execution."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]

    current_path = Path.cwd().resolve()
    for candidate in (current_path, *current_path.parents):
        if (candidate / "src").exists() and (candidate / "models").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()

DEFAULT_OUTPUT_DIR = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_OUTPUT_DIR",
        str(REPO_ROOT / "models" / "ao2_profitability" / "ridge_baseline"),
    )
)

DEFAULT_METRICS_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_METRICS_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_ridge_baseline_metrics.json"),
    )
)

DEFAULT_METADATA_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_ridge_baseline_metadata.json"),
    )
)

DEFAULT_VALIDATION_METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_validation_metrics.csv"),
    )
)

DEFAULT_RESIDUAL_DIAGNOSTICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_RESIDUAL_DIAGNOSTICS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_residual_diagnostics.csv"),
    )
)

DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_VALIDATION_PREDICTIONS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_validation_predictions.csv"),
    )
)

DEFAULT_COEFFICIENTS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_COEFFICIENTS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_coefficients.csv"),
    )
)

DEFAULT_PREPROCESSING_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_PREPROCESSING_METADATA_PATH",
        str(
            REPO_ROOT
            / "models"
            / "ao2_profitability"
            / "preprocessing"
            / "ao2_preprocessing_metadata.json"
        ),
    )
)

DEFAULT_MODEL_ARTIFACT_PATH = os.getenv(
    "DATACO_AO2_RIDGE_MODEL_ARTIFACT_PATH",
    f"{VOLUME_ROOT}/models/ao2_profitability/ridge_baseline/ao2_ridge_baseline_pipeline.joblib",
)


@dataclass(frozen=True)
class AO2RidgeBaselineConfig:
    """Configuration for AO2 Ridge baseline training."""

    partition_input_path: str = os.getenv(
        "DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO2_PARTITION_OUTPUT_PATH,
    )
    preprocessing_metadata_path: Path = DEFAULT_PREPROCESSING_METADATA_PATH
    metrics_json_path: Path = DEFAULT_METRICS_JSON_PATH
    metadata_json_path: Path = DEFAULT_METADATA_JSON_PATH
    validation_metrics_csv_path: Path = DEFAULT_VALIDATION_METRICS_CSV_PATH
    residual_diagnostics_csv_path: Path = DEFAULT_RESIDUAL_DIAGNOSTICS_CSV_PATH
    validation_predictions_csv_path: Path = DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH
    coefficients_csv_path: Path = DEFAULT_COEFFICIENTS_CSV_PATH
    model_artifact_path: str = DEFAULT_MODEL_ARTIFACT_PATH
    save_fitted_model: bool = (
        os.getenv("DATACO_AO2_SAVE_RIDGE_MODEL", "false").strip().lower() == "true"
    )
    read_format: str = "delta"
    inner_validation_ratio: float = float(os.getenv("DATACO_AO2_INNER_VALIDATION_RATIO", "0.20"))
    ridge_alpha: float = float(os.getenv("DATACO_AO2_RIDGE_ALPHA", "1.0"))
    max_coefficients: int = int(os.getenv("DATACO_AO2_RIDGE_MAX_COEFFICIENTS", "100"))


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao2_ridge_baseline")


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def validate_volume_path(path: str, field_name: str) -> None:
    """Validate that Delta input paths use Unity Catalog Volumes."""
    if path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
        raise ValueError(
            f"{field_name} points to the disabled public DBFS root: {path}. "
            "Use Unity Catalog Volumes under /Volumes/workspace/default/raw_data/."
        )
    if not path.startswith("/Volumes/"):
        raise ValueError(f"{field_name} must use a Unity Catalog Volume path. Received: {path}")


def normalize_column_name(column_name: str) -> str:
    """Return a loose normalized name for leakage-list comparisons."""
    return (
        column_name.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
    )


def read_optional_json(path: Path) -> dict[str, Any] | None:
    """Read optional JSON metadata when present."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_package_version(package_name: str) -> str | None:
    """Return an installed package version if available."""
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def assert_required_columns_exist(df: Any) -> None:
    """Validate required identifiers, target, partition columns, and predictors."""
    required_columns = (*REQUIRED_INPUT_COLUMNS, *FEATURE_COLUMNS)
    missing_columns = sorted(column_name for column_name in required_columns if column_name not in df.columns)
    if missing_columns:
        raise ValueError(f"AO2 partition table is missing required columns: {missing_columns}")


def assert_feature_list_is_safe() -> None:
    """Validate target, identifiers, partition fields, and forbidden fields are excluded."""
    feature_columns = set(FEATURE_COLUMNS)

    if TARGET_COLUMN in feature_columns:
        raise ValueError("AO2 target is present in feature columns.")

    if "ao3_order_value" in feature_columns:
        raise ValueError("ao3_order_value is an AO3 support denominator, not an AO2 predictor.")

    identifier_overlap = sorted(feature_columns.intersection(EXCLUDED_IDENTIFIER_METADATA_COLUMNS))
    if identifier_overlap:
        raise ValueError(
            f"Identifier, partition, or metadata columns found in features: {identifier_overlap}"
        )

    forbidden_columns = set(FORBIDDEN_LEAKAGE_COLUMNS).union(FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS)
    forbidden_normalized = {normalize_column_name(column_name) for column_name in forbidden_columns}
    feature_normalized = {normalize_column_name(column_name) for column_name in feature_columns}
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    if forbidden_overlap:
        raise ValueError(f"Forbidden AO2 target/proxy/leakage columns found in features: {forbidden_overlap}")


def assert_target_contract(df: Any) -> None:
    """Validate AO2 target is numeric and complete in the partition input."""
    from pyspark.sql.functions import col, sum as spark_sum, when
    from pyspark.sql.types import NumericType

    schema_by_name = {field.name: field.dataType for field in df.schema.fields}
    target_type = schema_by_name.get(TARGET_COLUMN)
    if target_type is None or not isinstance(target_type, NumericType):
        raise ValueError(
            f"AO2 target `{TARGET_COLUMN}` must be numeric before modeling. "
            f"Found: {target_type.simpleString() if target_type else 'missing'}"
        )

    missing_count = df.select(
        spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias("missing_count")
    ).collect()[0]["missing_count"]
    if missing_count != 0:
        raise ValueError(
            f"AO2 target `{TARGET_COLUMN}` contains {missing_count} missing values. "
            "Handle target missingness before modeling according to AO2 target policy."
        )


def assert_unique_keys(df: Any) -> None:
    """Validate one row per AO2 order item key."""
    row_count = df.count()
    distinct_key_count = df.select(*JOIN_KEY_COLUMNS).distinct().count()
    if row_count != distinct_key_count:
        raise ValueError(
            "AO2 partitions contain duplicate keys. "
            f"Rows: {row_count}; distinct keys: {distinct_key_count}."
        )


def collect_partition_labels(df: Any) -> set[str]:
    """Collect observed AO2 partition labels and require final test to exist."""
    labels = {row[PARTITION_COLUMN] for row in df.select(PARTITION_COLUMN).distinct().collect()}
    if TEST_LABEL not in labels:
        raise ValueError(f"Final test partition label `{TEST_LABEL}` is missing.")
    return labels


def collect_partition_counts(df: Any) -> dict[str, int]:
    """Collect partition row counts without materializing the test set locally."""
    from pyspark.sql.functions import count as spark_count

    return {
        row[PARTITION_COLUMN]: int(row["row_count"])
        for row in df.groupBy(PARTITION_COLUMN)
        .agg(spark_count("*").alias("row_count"))
        .collect()
    }


def load_partition_slice_as_pandas(df: Any, partition_label: str) -> pd.DataFrame:
    """Load one modeling slice as pandas after deterministic chronological ordering."""
    from pyspark.sql.functions import col

    selected_columns = [
        *JOIN_KEY_COLUMNS,
        ROW_NUMBER_COLUMN,
        PARTITION_COLUMN,
        TARGET_COLUMN,
        *FEATURE_COLUMNS,
    ]
    return (
        df.filter(col(PARTITION_COLUMN) == partition_label)
        .orderBy(*[col(column_name).asc() for column_name in ORDERING_COLUMNS])
        .select(*selected_columns)
        .toPandas()
    )


def determine_modeling_slices(
    partitioned_df: Any,
    config: AO2RidgeBaselineConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return training and validation slices without using the final test set."""
    labels = collect_partition_labels(partitioned_df)

    if labels == {TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL}:
        train_pdf = load_partition_slice_as_pandas(partitioned_df, TRAIN_LABEL)
        validation_pdf = load_partition_slice_as_pandas(partitioned_df, VALIDATION_LABEL)
        split_metadata = {
            "partition_structure": "train_validation_test",
            "training_slice": TRAIN_LABEL,
            "validation_slice": VALIDATION_LABEL,
            "validation_rule": "materialized_validation_partition",
            "inner_validation_ratio": None,
            "final_test_partition_label": TEST_LABEL,
            "final_test_used": False,
        }
        return train_pdf, validation_pdf, split_metadata

    if labels == {DEVELOPMENT_LABEL, TEST_LABEL}:
        development_pdf = load_partition_slice_as_pandas(partitioned_df, DEVELOPMENT_LABEL)
        development_rows = len(development_pdf)
        inner_train_boundary = math.floor(development_rows * (1.0 - config.inner_validation_ratio))
        if inner_train_boundary <= 0 or inner_train_boundary >= development_rows:
            raise ValueError(
                "Internal validation split is impossible with the available development rows. "
                f"Rows: {development_rows}; boundary: {inner_train_boundary}."
            )

        train_pdf = development_pdf.iloc[:inner_train_boundary].copy()
        validation_pdf = development_pdf.iloc[inner_train_boundary:].copy()
        split_metadata = {
            "partition_structure": "development_test",
            "training_slice": INNER_TRAIN_LABEL,
            "validation_slice": INNER_VALIDATION_LABEL,
            "validation_rule": (
                "first 80% of development rows as inner training and final 20% "
                "as validation, ordered by order_date_DateOrders, Order_Id, Order_Item_Id"
            ),
            "inner_validation_ratio": config.inner_validation_ratio,
            "development_rows": development_rows,
            "inner_train_boundary_row_count": inner_train_boundary,
            "final_test_partition_label": TEST_LABEL,
            "final_test_used": False,
        }
        return train_pdf, validation_pdf, split_metadata

    raise ValueError(
        "AO2 partition labels are unclear. Expected exactly "
        f"{sorted([DEVELOPMENT_LABEL, TEST_LABEL])} or "
        f"{sorted([TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL])}; found {sorted(labels)}."
    )


def date_range_summary(pdf: pd.DataFrame) -> dict[str, str | int]:
    """Return a compact date and row-number summary for a modeling slice."""
    return {
        "row_count": int(len(pdf)),
        "min_order_date_DateOrders": pd.to_datetime(pdf["order_date_DateOrders"]).min().isoformat(),
        "max_order_date_DateOrders": pd.to_datetime(pdf["order_date_DateOrders"]).max().isoformat(),
        "min_chronological_row_number": int(pdf[ROW_NUMBER_COLUMN].min()),
        "max_chronological_row_number": int(pdf[ROW_NUMBER_COLUMN].max()),
    }


def build_ridge_pipeline(config: AO2RidgeBaselineConfig) -> Any:
    """Build the approved preprocessing plus Ridge Regression baseline."""
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline

    model = Ridge(alpha=config.ridge_alpha)
    return Pipeline(
        steps=[
            ("preprocessor", build_sklearn_preprocessor()),
            ("model", model),
        ]
    )


def evaluate_validation_predictions(y_true: pd.Series, y_predicted: np.ndarray) -> dict[str, Any]:
    """Compute validation-only AO2 baseline metrics."""
    from sklearn.metrics import (
        mean_absolute_error,
        mean_squared_error,
        median_absolute_error,
        r2_score,
    )

    residuals = y_true.to_numpy(dtype=float) - y_predicted
    absolute_errors = np.abs(residuals)

    return {
        "rmse": float(mean_squared_error(y_true, y_predicted, squared=False)),
        "mae": float(mean_absolute_error(y_true, y_predicted)),
        "r2": float(r2_score(y_true, y_predicted)),
        "median_absolute_error": float(median_absolute_error(y_true, y_predicted)),
        "mean_error_bias": float(np.mean(residuals)),
        "validation_row_count": int(len(y_true)),
        "target_mean": float(np.mean(y_true)),
        "target_standard_deviation": float(np.std(y_true, ddof=1)) if len(y_true) > 1 else 0.0,
        "prediction_mean": float(np.mean(y_predicted)),
        "prediction_standard_deviation": float(np.std(y_predicted, ddof=1)) if len(y_predicted) > 1 else 0.0,
        "absolute_error_p50": float(np.percentile(absolute_errors, 50)),
        "absolute_error_p90": float(np.percentile(absolute_errors, 90)),
    }


def build_residual_diagnostics(
    y_true: pd.Series,
    y_predicted: np.ndarray,
) -> dict[str, Any]:
    """Build residual diagnostics for validation predictions."""
    residuals = y_true.to_numpy(dtype=float) - y_predicted
    absolute_errors = np.abs(residuals)
    sign_mismatch = np.sign(y_true.to_numpy(dtype=float)) != np.sign(y_predicted)

    diagnostics: dict[str, Any] = {
        "residual_mean": float(np.mean(residuals)),
        "residual_standard_deviation": float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0,
        "residual_median": float(np.median(residuals)),
        "residual_min": float(np.min(residuals)),
        "residual_max": float(np.max(residuals)),
        "absolute_error_mean": float(np.mean(absolute_errors)),
        "absolute_error_median": float(np.median(absolute_errors)),
        "wrong_profit_sign_share": float(np.mean(sign_mismatch)),
    }
    for percentile in (10, 25, 50, 75, 90):
        diagnostics[f"residual_p{percentile}"] = float(np.percentile(residuals, percentile))
        diagnostics[f"absolute_error_p{percentile}"] = float(np.percentile(absolute_errors, percentile))

    return diagnostics


def extract_coefficients(pipeline: Any, max_coefficients: int) -> pd.DataFrame:
    """Extract the largest Ridge coefficients by absolute magnitude."""
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    coefficient_df = pd.DataFrame(
        {
            "model_name": MODEL_NAME,
            "feature_name": preprocessor.get_feature_names_out(),
            "coefficient": model.coef_,
        }
    )
    coefficient_df["absolute_coefficient"] = coefficient_df["coefficient"].abs()
    coefficient_df["sign"] = coefficient_df["coefficient"].map(
        lambda value: "positive" if value > 0 else "negative" if value < 0 else "neutral"
    )

    coefficient_df = coefficient_df.sort_values(
        ["absolute_coefficient", "feature_name"],
        ascending=[False, True],
    ).reset_index(drop=True)
    coefficient_df["coefficient_rank"] = coefficient_df.index + 1

    if max_coefficients > 0:
        return coefficient_df.head(max_coefficients).copy()
    return coefficient_df


def save_json(payload: dict[str, Any], path: Path) -> None:
    """Write a JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def save_metrics_csv(metrics: dict[str, Any], path: Path) -> None:
    """Write validation metrics in a compact report-friendly CSV format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"metric": metric_name, "value": metric_value} for metric_name, metric_value in metrics.items()]
    ).to_csv(path, index=False)


def save_residual_diagnostics_csv(diagnostics: dict[str, Any], path: Path) -> None:
    """Write residual diagnostics in a compact report-friendly CSV format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"diagnostic": diagnostic_name, "value": diagnostic_value} for diagnostic_name, diagnostic_value in diagnostics.items()]
    ).to_csv(path, index=False)


def save_validation_predictions(
    validation_pdf: pd.DataFrame,
    y_predicted: np.ndarray,
    evaluation_slice: str,
    path: Path,
) -> None:
    """Write validation prediction records for downstream AO2 comparison."""
    prediction_df = validation_pdf.loc[
        :,
        [
            "Order_Id",
            "Order_Item_Id",
            "order_date_DateOrders",
            ROW_NUMBER_COLUMN,
            PARTITION_COLUMN,
            TARGET_COLUMN,
        ],
    ].copy()
    prediction_df["model_name"] = MODEL_NAME
    prediction_df["evaluation_slice"] = evaluation_slice
    prediction_df["predicted_profit"] = y_predicted
    prediction_df["residual"] = prediction_df[TARGET_COLUMN] - prediction_df["predicted_profit"]
    prediction_df["absolute_error"] = prediction_df["residual"].abs()

    output_columns = [
        "model_name",
        "evaluation_slice",
        "Order_Id",
        "Order_Item_Id",
        "order_date_DateOrders",
        ROW_NUMBER_COLUMN,
        PARTITION_COLUMN,
        TARGET_COLUMN,
        "predicted_profit",
        "residual",
        "absolute_error",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    prediction_df.to_csv(path, index=False, columns=output_columns)


def save_model_artifact(pipeline: Any, output_path: str) -> None:
    """Persist the fitted preprocessing-plus-model pipeline when enabled."""
    if output_path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
        raise ValueError(
            f"Model artifact path points to the disabled public DBFS root: {output_path}"
        )

    from joblib import dump

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    dump(pipeline, output_path)


def build_metadata(
    config: AO2RidgeBaselineConfig,
    preprocessing_metadata: dict[str, Any] | None,
    partition_labels: set[str],
    partition_counts: dict[str, int],
    split_metadata: dict[str, Any],
    train_pdf: pd.DataFrame,
    validation_pdf: pd.DataFrame,
    pipeline: Any,
    metrics: dict[str, Any],
    residual_diagnostics: dict[str, Any],
    model_artifact_saved: bool,
) -> dict[str, Any]:
    """Build reproducibility metadata for the AO2 Ridge validation baseline."""
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    return {
        "metadata_status": "runtime_training_completed",
        "issue": "#35",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_partition_path": config.partition_input_path,
        "input_partition_read_format": config.read_format,
        "partition_column": PARTITION_COLUMN,
        "partition_labels_observed": sorted(partition_labels),
        "partition_row_counts": partition_counts,
        "split_metadata": split_metadata,
        "training_slice_summary": date_range_summary(train_pdf),
        "validation_slice_summary": date_range_summary(validation_pdf),
        "final_test_partition_status": {
            "label": TEST_LABEL,
            "used_for_training": False,
            "used_for_preprocessing_fit": False,
            "used_for_validation_metrics": False,
            "used_for_residual_diagnostics": False,
            "used_for_model_selection": False,
            "treatment": "reserved for final AO2 model evaluation; not touched by issue #35",
        },
        "target_column": TARGET_COLUMN,
        "target_transformation": "none",
        "feature_columns": list(FEATURE_COLUMNS),
        "excluded_identifier_metadata_columns": list(EXCLUDED_IDENTIFIER_METADATA_COLUMNS),
        "forbidden_target_reconstruction_columns": list(FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS),
        "forbidden_leakage_columns": list(FORBIDDEN_LEAKAGE_COLUMNS),
        "ao3_order_value_excluded_as_predictor": "ao3_order_value" not in FEATURE_COLUMNS,
        "feature_count_before_preprocessing": len(FEATURE_COLUMNS),
        "feature_count_after_preprocessing": int(len(preprocessor.get_feature_names_out())),
        "preprocessing_reference": {
            "factory": "src.modeling.build_ao2_preprocessing_pipeline.build_sklearn_preprocessor",
            "metadata_path": str(config.preprocessing_metadata_path),
            "metadata_status": (
                preprocessing_metadata.get("metadata_status") if preprocessing_metadata else None
            ),
            "fit_scope": "fitted inside issue #35 on training slice only",
            "validation_transform_scope": "validation transformed with training-fitted preprocessing only",
            "test_transform_scope": "not transformed by this baseline job",
        },
        "ridge_regression": {
            "library": "sklearn.linear_model.Ridge",
            "parameters": model.get_params(deep=False),
            "tuning": "none",
            "alpha_selection": "fixed alpha=1.0 baseline unless DATACO_AO2_RIDGE_ALPHA overrides it intentionally",
        },
        "validation_metrics": metrics,
        "residual_diagnostics": residual_diagnostics,
        "artifacts": {
            "metrics_json": str(config.metrics_json_path),
            "metadata_json": str(config.metadata_json_path),
            "validation_metrics_csv": str(config.validation_metrics_csv_path),
            "residual_diagnostics_csv": str(config.residual_diagnostics_csv_path),
            "validation_predictions_csv": str(config.validation_predictions_csv_path),
            "coefficients_csv": str(config.coefficients_csv_path),
            "coefficient_output_scope": (
                "top coefficients by absolute magnitude"
                if config.max_coefficients > 0
                else "all coefficients"
            ),
            "max_coefficients": config.max_coefficients,
            "model_artifact_saved": model_artifact_saved,
            "model_artifact_path": config.model_artifact_path if model_artifact_saved else None,
        },
        "interpretability_notes": [
            "Coefficients are from the preprocessed feature space after scaling and one-hot encoding.",
            "Coefficient signs and magnitudes are associative, not causal.",
            "Correlated predictors can make individual coefficient interpretation unstable.",
            "Ridge shrinks coefficients for stability in the presence of multicollinearity.",
            "This baseline is useful for H2 comparison but may underfit nonlinear profitability patterns.",
        ],
        "limitations": [
            "No grid search or broad hyperparameter tuning is performed in this issue.",
            "The final test partition is not used.",
            "The target remains raw Order_Profit_Per_Order; no log transform is applied.",
            "The model excludes ao3_order_value and target-reconstruction fields from AO2 predictors.",
            "No gradient boosting regressor or AO3 segmentation is implemented in this issue.",
        ],
        "versions": {
            "python": sys.version.split()[0],
            "numpy": get_package_version("numpy"),
            "pandas": get_package_version("pandas"),
            "sklearn": get_package_version("scikit-learn"),
            "pyspark": get_package_version("pyspark"),
            "joblib": get_package_version("joblib"),
        },
    }


def run_ao2_ridge_baseline(
    config: AO2RidgeBaselineConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Train and validate the AO2 Ridge baseline."""
    logger.info("Starting AO2 Ridge baseline training.")
    logger.info("AO2 partition input path: %s", config.partition_input_path)
    logger.info("Metrics output path: %s", config.metrics_json_path)
    logger.info("Metadata output path: %s", config.metadata_json_path)

    validate_volume_path(config.partition_input_path, "partition_input_path")
    assert_feature_list_is_safe()

    spark = get_spark_session()
    partitioned_df = spark.read.format(config.read_format).load(config.partition_input_path)
    assert_required_columns_exist(partitioned_df)
    assert_target_contract(partitioned_df)
    assert_unique_keys(partitioned_df)

    partition_labels = collect_partition_labels(partitioned_df)
    partition_counts = collect_partition_counts(partitioned_df)
    train_pdf, validation_pdf, split_metadata = determine_modeling_slices(partitioned_df, config)
    preprocessing_metadata = read_optional_json(config.preprocessing_metadata_path)

    x_train = train_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_train = train_pdf[TARGET_COLUMN].astype(float)
    x_validation = validation_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_validation = validation_pdf[TARGET_COLUMN].astype(float)

    pipeline = build_ridge_pipeline(config)
    pipeline.fit(x_train, y_train)

    y_validation_predicted = pipeline.predict(x_validation)
    metrics = evaluate_validation_predictions(y_validation, y_validation_predicted)
    residual_diagnostics = build_residual_diagnostics(y_validation, y_validation_predicted)

    coefficient_df = extract_coefficients(pipeline, config.max_coefficients)
    config.coefficients_csv_path.parent.mkdir(parents=True, exist_ok=True)
    coefficient_df.to_csv(config.coefficients_csv_path, index=False)

    save_validation_predictions(
        validation_pdf,
        y_validation_predicted,
        str(split_metadata.get("validation_slice", INNER_VALIDATION_LABEL)),
        config.validation_predictions_csv_path,
    )
    save_metrics_csv(metrics, config.validation_metrics_csv_path)
    save_residual_diagnostics_csv(residual_diagnostics, config.residual_diagnostics_csv_path)
    save_json(metrics, config.metrics_json_path)

    model_artifact_saved = False
    if config.save_fitted_model:
        save_model_artifact(pipeline, config.model_artifact_path)
        model_artifact_saved = True

    metadata = build_metadata(
        config,
        preprocessing_metadata,
        partition_labels,
        partition_counts,
        split_metadata,
        train_pdf,
        validation_pdf,
        pipeline,
        metrics,
        residual_diagnostics,
        model_artifact_saved,
    )
    save_json(metadata, config.metadata_json_path)

    logger.info("AO2 Ridge validation RMSE: %.6f", metrics["rmse"])
    logger.info("AO2 Ridge validation MAE: %.6f", metrics["mae"])
    logger.info("AO2 Ridge validation R2: %.6f", metrics["r2"])
    logger.info("AO2 Ridge baseline training completed successfully.")
    return metadata


def main() -> None:
    """Run AO2 Ridge baseline training with default configuration."""
    run_ao2_ridge_baseline(AO2RidgeBaselineConfig(), configure_logging())


if __name__ == "__main__":
    main()
