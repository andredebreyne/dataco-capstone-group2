"""Train the AO1 Logistic Regression validation baseline.

This job consumes the official AO1 chronological partition table, creates a
time-preserving validation slice inside development when needed, fits the
approved AO1 preprocessing pipeline only on the training slice, and evaluates
Logistic Regression on validation only. The final test partition is never used
for fitting, model selection, threshold tuning, or validation metrics here.
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

import pandas as pd

from src.modeling.build_ao1_preprocessing_pipeline import (
    FEATURE_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    build_sklearn_preprocessor,
)
from src.modeling.create_ao1_chronological_partitions import (
    AO1_PARTITION_OUTPUT_PATH,
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
DEFAULT_THRESHOLD = 0.5
RANDOM_STATE = 620

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
    "_gold_ao1_processed_timestamp",
)


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
        "DATACO_AO1_LOGISTIC_OUTPUT_DIR",
        str(REPO_ROOT / "models" / "ao1_late_delivery" / "logistic_regression"),
    )
)

DEFAULT_METRICS_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO1_LOGISTIC_METRICS_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao1_logistic_regression_metrics.json"),
    )
)

DEFAULT_METADATA_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO1_LOGISTIC_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao1_logistic_regression_metadata.json"),
    )
)

DEFAULT_METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_LOGISTIC_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_logistic_regression_validation_metrics.csv"),
    )
)

DEFAULT_COEFFICIENTS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_LOGISTIC_COEFFICIENTS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_logistic_regression_coefficients.csv"),
    )
)

DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_LOGISTIC_VALIDATION_PREDICTIONS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_logistic_regression_validation_predictions.csv"),
    )
)

DEFAULT_PREPROCESSING_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_PREPROCESSING_METADATA_PATH",
        str(REPO_ROOT / "models" / "ao1_late_delivery" / "preprocessing" / "ao1_preprocessing_metadata.json"),
    )
)

DEFAULT_MODEL_ARTIFACT_PATH = os.getenv(
    "DATACO_AO1_LOGISTIC_MODEL_ARTIFACT_PATH",
    f"{VOLUME_ROOT}/models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_pipeline.joblib",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")


@dataclass(frozen=True)
class AO1LogisticRegressionBaselineConfig:
    """Configuration for AO1 Logistic Regression baseline training."""

    partition_input_path: str = os.getenv(
        "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO1_PARTITION_OUTPUT_PATH,
    )
    preprocessing_metadata_path: Path = DEFAULT_PREPROCESSING_METADATA_PATH
    metrics_json_path: Path = DEFAULT_METRICS_JSON_PATH
    metadata_json_path: Path = DEFAULT_METADATA_JSON_PATH
    metrics_csv_path: Path = DEFAULT_METRICS_CSV_PATH
    coefficients_csv_path: Path = DEFAULT_COEFFICIENTS_CSV_PATH
    validation_predictions_csv_path: Path = DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH
    model_artifact_path: str = DEFAULT_MODEL_ARTIFACT_PATH
    save_fitted_model: bool = (
        os.getenv("DATACO_AO1_SAVE_LOGISTIC_MODEL", "false").strip().lower()
        == "true"
    )
    read_format: str = "delta"
    inner_validation_ratio: float = 0.20
    threshold: float = DEFAULT_THRESHOLD
    logistic_solver: str = os.getenv("DATACO_AO1_LOGISTIC_SOLVER", "lbfgs")
    logistic_max_iter: int = int(os.getenv("DATACO_AO1_LOGISTIC_MAX_ITER", "1000"))
    logistic_penalty: str = os.getenv("DATACO_AO1_LOGISTIC_PENALTY", "l2")
    logistic_class_weight: str | None = os.getenv(
        "DATACO_AO1_LOGISTIC_CLASS_WEIGHT",
        "balanced",
    )
    random_state: int = RANDOM_STATE


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_logistic_regression_baseline")


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
        raise ValueError(f"AO1 partition table is missing required columns: {missing_columns}")


def assert_feature_list_is_safe() -> None:
    """Validate target, identifiers, partitions, and leakage fields are excluded."""
    feature_columns = set(FEATURE_COLUMNS)

    if TARGET_COLUMN in feature_columns:
        raise ValueError("AO1 target is present in feature columns.")

    identifier_overlap = sorted(feature_columns.intersection(EXCLUDED_IDENTIFIER_METADATA_COLUMNS))
    if identifier_overlap:
        raise ValueError(
            f"Identifier, partition, or metadata columns found in features: {identifier_overlap}"
        )

    forbidden_normalized = {
        normalize_column_name(column_name)
        for column_name in FORBIDDEN_LEAKAGE_COLUMNS
    }
    feature_normalized = {
        normalize_column_name(column_name)
        for column_name in feature_columns
    }
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    if forbidden_overlap:
        raise ValueError(f"Forbidden leakage columns found in AO1 features: {forbidden_overlap}")


def assert_target_contract(df: Any) -> None:
    """Validate AO1 target is complete and binary in the partition input."""
    from pyspark.sql.functions import col, sum as spark_sum, when

    target_summary = df.select(
        spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias("missing_count"),
        spark_sum(when(~col(TARGET_COLUMN).isin(0, 1), 1).otherwise(0)).alias("invalid_count"),
    ).collect()[0].asDict()

    if target_summary["missing_count"] != 0 or target_summary["invalid_count"] != 0:
        raise ValueError(
            "AO1 target must be complete and binary before modeling. "
            f"Summary: {target_summary}"
        )


def collect_partition_labels(df: Any) -> set[str]:
    """Collect and validate observed AO1 partition labels."""
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
    config: AO1LogisticRegressionBaselineConfig,
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
        "AO1 partition labels are unclear. Expected exactly "
        f"{sorted([DEVELOPMENT_LABEL, TEST_LABEL])} or "
        f"{sorted([TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL])}; found {sorted(labels)}."
    )


def class_distribution(y: pd.Series) -> dict[str, Any]:
    """Return class counts and positive rate for binary AO1 target values."""
    counts = y.value_counts(dropna=False).to_dict()
    total = int(len(y))
    positive_count = int(counts.get(1, 0))
    negative_count = int(counts.get(0, 0))
    return {
        "row_count": total,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "positive_rate": positive_count / total if total else 0.0,
    }


def assert_slice_has_both_classes(y: pd.Series, slice_name: str) -> None:
    """Validate a modeling slice contains both binary target classes."""
    observed_classes = set(y.dropna().astype(int).unique())
    if observed_classes != {0, 1}:
        raise ValueError(
            f"{slice_name} must contain both AO1 target classes for baseline training "
            f"and validation. Observed classes: {sorted(observed_classes)}."
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


def parse_class_weight(value: str | None) -> str | None:
    """Normalize the class-weight configuration for sklearn."""
    if value is None:
        return None
    normalized_value = value.strip().lower()
    if normalized_value in {"", "none", "null"}:
        return None
    if normalized_value == "balanced":
        return "balanced"
    raise ValueError(
        "DATACO_AO1_LOGISTIC_CLASS_WEIGHT must be `balanced`, `none`, or unset. "
        f"Received: {value}"
    )


def build_logistic_pipeline(config: AO1LogisticRegressionBaselineConfig) -> Any:
    """Build the approved preprocessing plus Logistic Regression baseline."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    class_weight = parse_class_weight(config.logistic_class_weight)
    model = LogisticRegression(
        max_iter=config.logistic_max_iter,
        solver=config.logistic_solver,
        class_weight=class_weight,
        penalty=config.logistic_penalty,
        random_state=config.random_state,
    )

    return Pipeline(
        steps=[
            ("preprocessor", build_sklearn_preprocessor()),
            ("model", model),
        ]
    )


def evaluate_validation_predictions(
    y_true: pd.Series,
    y_probability: Any,
    threshold: float,
) -> dict[str, Any]:
    """Compute validation-only AO1 baseline metrics."""
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        confusion_matrix,
        f1_score,
        log_loss,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y_predicted = (y_probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_predicted, labels=[0, 1]).ravel()

    return {
        "roc_auc": float(roc_auc_score(y_true, y_probability)),
        "pr_auc": float(average_precision_score(y_true, y_probability)),
        "accuracy": float(accuracy_score(y_true, y_predicted)),
        "precision": float(precision_score(y_true, y_predicted, zero_division=0)),
        "recall": float(recall_score(y_true, y_predicted, zero_division=0)),
        "f1": float(f1_score(y_true, y_predicted, zero_division=0)),
        "log_loss": float(log_loss(y_true, y_probability, labels=[0, 1])),
        "validation_positive_class_rate": float(y_true.mean()),
        "validation_predicted_positive_rate_at_0_5": float(y_predicted.mean()),
        "threshold": float(threshold),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
    }


def extract_coefficients(pipeline: Any) -> pd.DataFrame:
    """Extract coefficient rows from the fitted Logistic Regression pipeline."""
    import numpy as np

    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    feature_names = preprocessor.get_feature_names_out()
    coefficients = model.coef_[0]

    coefficient_df = pd.DataFrame(
        {
            "feature_name": feature_names,
            "coefficient": coefficients,
        }
    )
    coefficient_df["absolute_coefficient"] = coefficient_df["coefficient"].abs()
    coefficient_df["odds_ratio"] = np.exp(
        coefficient_df["coefficient"].clip(lower=-700, upper=700)
    )
    coefficient_df["direction"] = coefficient_df["coefficient"].map(
        lambda value: "positive" if value > 0 else "negative" if value < 0 else "neutral"
    )

    return coefficient_df.sort_values(
        ["absolute_coefficient", "feature_name"],
        ascending=[False, True],
    )


def save_json(payload: dict[str, Any], path: Path) -> None:
    """Write a JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def save_metrics_csv(metrics: dict[str, Any], path: Path) -> None:
    """Write validation metrics in a compact report-friendly CSV format."""
    confusion_matrix = metrics["confusion_matrix"]
    metric_rows = [
        {"metric": "roc_auc", "value": metrics["roc_auc"]},
        {"metric": "pr_auc", "value": metrics["pr_auc"]},
        {"metric": "accuracy", "value": metrics["accuracy"]},
        {"metric": "precision", "value": metrics["precision"]},
        {"metric": "recall", "value": metrics["recall"]},
        {"metric": "f1", "value": metrics["f1"]},
        {"metric": "log_loss", "value": metrics["log_loss"]},
        {
            "metric": "validation_positive_class_rate",
            "value": metrics["validation_positive_class_rate"],
        },
        {
            "metric": "validation_predicted_positive_rate_at_0_5",
            "value": metrics["validation_predicted_positive_rate_at_0_5"],
        },
        {"metric": "threshold", "value": metrics["threshold"]},
        {"metric": "confusion_matrix_true_negative", "value": confusion_matrix["true_negative"]},
        {"metric": "confusion_matrix_false_positive", "value": confusion_matrix["false_positive"]},
        {"metric": "confusion_matrix_false_negative", "value": confusion_matrix["false_negative"]},
        {"metric": "confusion_matrix_true_positive", "value": confusion_matrix["true_positive"]},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metric_rows).to_csv(path, index=False)


def save_validation_predictions(
    validation_pdf: pd.DataFrame,
    y_probability: Any,
    threshold: float,
    path: Path,
) -> None:
    """Write validation prediction records for downstream AO1 evaluation."""
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
    prediction_df["model_name"] = "ao1_logistic_regression_baseline"
    prediction_df["evaluation_slice"] = INNER_VALIDATION_LABEL
    prediction_df["predicted_probability"] = y_probability
    prediction_df["prediction_threshold"] = threshold
    prediction_df["predicted_label"] = (
        prediction_df["predicted_probability"] >= threshold
    ).astype(int)

    output_columns = [
        "model_name",
        "evaluation_slice",
        "Order_Id",
        "Order_Item_Id",
        "order_date_DateOrders",
        ROW_NUMBER_COLUMN,
        PARTITION_COLUMN,
        TARGET_COLUMN,
        "predicted_probability",
        "prediction_threshold",
        "predicted_label",
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
    config: AO1LogisticRegressionBaselineConfig,
    preprocessing_metadata: dict[str, Any] | None,
    partition_labels: set[str],
    partition_counts: dict[str, int],
    split_metadata: dict[str, Any],
    train_pdf: pd.DataFrame,
    validation_pdf: pd.DataFrame,
    pipeline: Any,
    metrics: dict[str, Any],
    model_artifact_saved: bool,
) -> dict[str, Any]:
    """Build reproducibility metadata for the validation baseline."""
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    model_params = model.get_params(deep=False)

    return {
        "metadata_status": "runtime_training_completed",
        "issue": "#27",
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
            "used_for_threshold_selection": False,
            "treatment": "reserved for final AO1 model evaluation; not touched by issue #27",
        },
        "target_column": TARGET_COLUMN,
        "feature_columns": list(FEATURE_COLUMNS),
        "excluded_identifier_metadata_columns": list(EXCLUDED_IDENTIFIER_METADATA_COLUMNS),
        "forbidden_leakage_columns": list(FORBIDDEN_LEAKAGE_COLUMNS),
        "feature_count_before_preprocessing": len(FEATURE_COLUMNS),
        "feature_count_after_preprocessing": int(len(preprocessor.get_feature_names_out())),
        "preprocessing_reference": {
            "factory": "src.modeling.build_ao1_preprocessing_pipeline.build_sklearn_preprocessor",
            "metadata_path": str(config.preprocessing_metadata_path),
            "metadata_status": (
                preprocessing_metadata.get("metadata_status") if preprocessing_metadata else None
            ),
            "fit_scope": "fitted inside issue #27 on training slice only",
        },
        "smote": {
            "used": False,
            "decision": "not used for this baseline",
            "rationale": (
                "Issue #26 marks SMOTE as deferred and AO1 imbalance as mild. "
                "This baseline uses class_weight='balanced' instead of SMOTE."
            ),
            "training_only": True,
            "validation_resampling_allowed": False,
            "test_resampling_allowed": False,
            "class_distribution_before_resampling": {
                "training": class_distribution(train_pdf[TARGET_COLUMN].astype(int)),
                "validation": class_distribution(validation_pdf[TARGET_COLUMN].astype(int)),
            },
            "class_distribution_after_resampling": {
                "training": class_distribution(train_pdf[TARGET_COLUMN].astype(int)),
                "validation": class_distribution(validation_pdf[TARGET_COLUMN].astype(int)),
            },
        },
        "logistic_regression": {
            "library": "sklearn.linear_model.LogisticRegression",
            "parameters": model_params,
            "baseline_threshold": config.threshold,
            "tuning": "none",
            "threshold_tuning": "none",
        },
        "validation_metrics": metrics,
        "artifacts": {
            "metrics_json": str(config.metrics_json_path),
            "metadata_json": str(config.metadata_json_path),
            "metrics_csv": str(config.metrics_csv_path),
            "coefficients_csv": str(config.coefficients_csv_path),
            "validation_predictions_csv": str(config.validation_predictions_csv_path),
            "model_artifact_saved": model_artifact_saved,
            "model_artifact_path": config.model_artifact_path if model_artifact_saved else None,
        },
        "interpretability_notes": {
            "coefficient_scope": "coefficients are from the preprocessed feature space",
            "odds_ratio_note": (
                "Odds ratios are computed from standardized/encoded features and should be "
                "interpreted as associative, not causal."
            ),
        },
        "versions": {
            "python": sys.version.split()[0],
            "pandas": get_package_version("pandas"),
            "sklearn": get_package_version("scikit-learn"),
            "pyspark": get_package_version("pyspark"),
            "joblib": get_package_version("joblib"),
        },
    }


def run_ao1_logistic_regression_baseline(
    config: AO1LogisticRegressionBaselineConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Train and validate the AO1 Logistic Regression baseline."""
    logger.info("Starting AO1 Logistic Regression baseline training.")
    logger.info("AO1 partition input path: %s", config.partition_input_path)
    logger.info("Metrics output path: %s", config.metrics_json_path)
    logger.info("Metadata output path: %s", config.metadata_json_path)

    validate_volume_path(config.partition_input_path, "partition_input_path")
    assert_feature_list_is_safe()

    spark = get_spark_session()
    partitioned_df = spark.read.format(config.read_format).load(config.partition_input_path)
    assert_required_columns_exist(partitioned_df)
    assert_target_contract(partitioned_df)

    partition_labels = collect_partition_labels(partitioned_df)
    partition_counts = collect_partition_counts(partitioned_df)
    train_pdf, validation_pdf, split_metadata = determine_modeling_slices(partitioned_df, config)
    preprocessing_metadata = read_optional_json(config.preprocessing_metadata_path)

    x_train = train_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_train = train_pdf[TARGET_COLUMN].astype(int)
    x_validation = validation_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_validation = validation_pdf[TARGET_COLUMN].astype(int)
    assert_slice_has_both_classes(y_train, "AO1 Logistic Regression training slice")
    assert_slice_has_both_classes(y_validation, "AO1 Logistic Regression validation slice")

    pipeline = build_logistic_pipeline(config)
    pipeline.fit(x_train, y_train)

    y_validation_probability = pipeline.predict_proba(x_validation)[:, 1]
    metrics = evaluate_validation_predictions(
        y_validation,
        y_validation_probability,
        config.threshold,
    )

    coefficient_df = extract_coefficients(pipeline)
    config.coefficients_csv_path.parent.mkdir(parents=True, exist_ok=True)
    coefficient_df.to_csv(config.coefficients_csv_path, index=False)

    save_validation_predictions(
        validation_pdf,
        y_validation_probability,
        config.threshold,
        config.validation_predictions_csv_path,
    )
    save_metrics_csv(metrics, config.metrics_csv_path)
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
        model_artifact_saved,
    )
    save_json(metadata, config.metadata_json_path)

    logger.info("AO1 Logistic Regression validation ROC-AUC: %.6f", metrics["roc_auc"])
    logger.info("AO1 Logistic Regression validation recall: %.6f", metrics["recall"])
    logger.info("AO1 Logistic Regression baseline training completed successfully.")
    return metadata


def main() -> None:
    """Run AO1 Logistic Regression baseline training with default configuration."""
    run_ao1_logistic_regression_baseline(
        AO1LogisticRegressionBaselineConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
