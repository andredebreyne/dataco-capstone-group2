"""Build the AO1 preprocessing pipeline specification and metadata.

This job reads the already leakage-safe AO1 chronological partition table and
fits learned preprocessing only on the approved fitting partition. It does not
train AO1 models, tune thresholds, or apply SMOTE.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, sum as spark_sum, when

from src.data_engineering.build_gold_ao1_table import (
    FORBIDDEN_AO1_OUTPUT_COLUMNS,
    PREDICTOR_COLUMNS,
)
from src.modeling.create_ao1_chronological_partitions import (
    AO1_PARTITION_OUTPUT_PATH,
    DEVELOPMENT_LABEL,
    JOIN_KEY_COLUMNS,
    PARTITION_COLUMN,
    ROW_NUMBER_COLUMN,
    TARGET_COLUMN,
    TEST_LABEL,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

AO1_PARTITION_INPUT_PATH = os.getenv(
    "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
    AO1_PARTITION_OUTPUT_PATH,
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")

TRAIN_LABEL = "train"
VALIDATION_LABEL = "validation"

NUMERIC_CONTINUOUS_COLUMNS = (
    "order_year",
    "order_quarter",
    "order_month",
    "order_week_of_year",
    "order_day_of_month",
    "order_day_of_week",
    "order_hour",
    "scheduled_shipping_days",
)

BINARY_FLAG_COLUMNS = (
    "order_is_weekend",
    "is_same_day_or_next_day_shipping",
    "is_standard_shipping",
    "customer_zipcode_available",
    "order_zipcode_available",
    "customer_order_country_match",
    "customer_order_state_match",
    "geo_coordinates_available",
)

CATEGORICAL_COLUMNS = (
    "Type",
    "order_season",
    "shipping_speed_tier",
    "shipping_mode_normalized",
    "product_category_key",
    "product_department_key",
    "customer_segment_normalized",
    "customer_country_normalized",
    "customer_state_normalized",
    "market_normalized",
    "order_country_normalized",
    "order_region_normalized",
    "order_state_normalized",
)

FEATURE_COLUMNS = (
    NUMERIC_CONTINUOUS_COLUMNS
    + BINARY_FLAG_COLUMNS
    + CATEGORICAL_COLUMNS
)

EXCLUDED_IDENTIFIER_METADATA_COLUMNS = (
    *JOIN_KEY_COLUMNS,
    ROW_NUMBER_COLUMN,
    PARTITION_COLUMN,
    "_gold_ao1_processed_timestamp",
)

REQUIRED_COLUMNS = (
    *JOIN_KEY_COLUMNS,
    TARGET_COLUMN,
    PARTITION_COLUMN,
    ROW_NUMBER_COLUMN,
)

FORBIDDEN_LEAKAGE_COLUMNS = tuple(
    sorted(
        {
            TARGET_COLUMN,
            *FORBIDDEN_AO1_OUTPUT_COLUMNS,
            "Delivery Status",
            "Days for shipping (real)",
            "shipping date (DateOrders)",
            "Order Status",
            "Order Profit Per Order",
            "Benefit per order",
            "Order Item Profit Ratio",
        }
    )
)

DEFAULT_METADATA_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_PREPROCESSING_METADATA_PATH",
        str(
            Path(__file__).resolve().parents[2]
            / "models"
            / "ao1_late_delivery"
            / "preprocessing"
            / "ao1_preprocessing_metadata.json"
        ),
    )
)

DEFAULT_FITTED_PREPROCESSOR_OUTPUT_PATH = os.getenv(
    "DATACO_AO1_PREPROCESSOR_ARTIFACT_PATH",
    f"{VOLUME_ROOT}/models/ao1_late_delivery/preprocessing/ao1_preprocessor.joblib",
)


@dataclass(frozen=True)
class AO1PreprocessingConfig:
    """Configuration for AO1 preprocessing metadata generation."""

    partition_input_path: str = AO1_PARTITION_INPUT_PATH
    metadata_output_path: Path = DEFAULT_METADATA_OUTPUT_PATH
    read_format: str = "delta"
    save_fitted_preprocessor: bool = (
        os.getenv("DATACO_AO1_SAVE_FITTED_PREPROCESSOR", "false").strip().lower()
        == "true"
    )
    fitted_preprocessor_output_path: str = DEFAULT_FITTED_PREPROCESSOR_OUTPUT_PATH


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_preprocessing")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_input_path(path: str, field_name: str) -> None:
    """Validate that configured data paths use Unity Catalog Volumes."""
    if path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
        raise ValueError(
            f"{field_name} points to the disabled public DBFS root: {path}. "
            "Use Unity Catalog Volumes under /Volumes/workspace/default/raw_data/."
        )
    if not path.startswith("/Volumes/"):
        raise ValueError(f"{field_name} must use a Unity Catalog Volume path. Received: {path}")


def read_delta(spark: SparkSession, path: str, read_format: str) -> DataFrame:
    """Read a Delta dataset from a configured path."""
    return spark.read.format(read_format).load(path)


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


def assert_required_columns_exist(df: DataFrame) -> None:
    """Validate that AO1 partition input contains required columns."""
    missing_columns = sorted(column_name for column_name in REQUIRED_COLUMNS if column_name not in df.columns)
    if missing_columns:
        raise ValueError(f"AO1 partition table is missing required columns: {missing_columns}")

    missing_predictors = sorted(column_name for column_name in FEATURE_COLUMNS if column_name not in df.columns)
    if missing_predictors:
        raise ValueError(f"AO1 partition table is missing approved predictor columns: {missing_predictors}")


def assert_column_group_contract() -> None:
    """Validate predictor groups are explicit, complete, and non-overlapping."""
    declared_groups = {
        "numeric_continuous": set(NUMERIC_CONTINUOUS_COLUMNS),
        "binary_flags": set(BINARY_FLAG_COLUMNS),
        "categorical": set(CATEGORICAL_COLUMNS),
    }

    overlaps: dict[str, list[str]] = {}
    group_names = list(declared_groups)
    for index, left_name in enumerate(group_names):
        for right_name in group_names[index + 1 :]:
            overlap = sorted(declared_groups[left_name].intersection(declared_groups[right_name]))
            if overlap:
                overlaps[f"{left_name}__{right_name}"] = overlap
    if overlaps:
        raise ValueError(f"AO1 preprocessing column groups overlap: {overlaps}")

    grouped_features = set().union(*declared_groups.values())
    approved_features = set(PREDICTOR_COLUMNS)
    if grouped_features != approved_features:
        raise ValueError(
            "AO1 preprocessing groups must exactly match AO1 Gold predictors. "
            f"Missing from groups: {sorted(approved_features.difference(grouped_features))}; "
            f"unexpected in groups: {sorted(grouped_features.difference(approved_features))}."
        )

    forbidden_normalized = {normalize_column_name(column_name) for column_name in FORBIDDEN_LEAKAGE_COLUMNS}
    feature_normalized = {normalize_column_name(column_name) for column_name in FEATURE_COLUMNS}
    forbidden_features = sorted(feature_normalized.intersection(forbidden_normalized))
    if forbidden_features:
        raise ValueError(f"Forbidden leakage columns found in AO1 feature list: {forbidden_features}")

    excluded_overlap = sorted(set(FEATURE_COLUMNS).intersection(EXCLUDED_IDENTIFIER_METADATA_COLUMNS))
    if excluded_overlap:
        raise ValueError(f"Identifier or metadata columns found in AO1 feature list: {excluded_overlap}")


def assert_target_contract(df: DataFrame) -> None:
    """Validate AO1 target is complete and binary in partition input."""
    invalid_summary = df.select(
        spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias("missing_count"),
        spark_sum(when(~col(TARGET_COLUMN).isin(0, 1), 1).otherwise(0)).alias("invalid_count"),
    ).collect()[0].asDict()

    if invalid_summary["missing_count"] != 0 or invalid_summary["invalid_count"] != 0:
        raise ValueError(
            "AO1 target must be complete and binary before preprocessing. "
            f"Summary: {invalid_summary}"
        )


def determine_partition_usage(labels: set[str]) -> dict[str, Any]:
    """Determine the allowed fitting and transformation partitions."""
    if labels == {TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL}:
        return {
            "partition_structure": "train_validation_test",
            "fitting_partition": TRAIN_LABEL,
            "transform_partitions": [TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL],
            "validation_partition_available": True,
            "final_test_treatment": (
                "transformed for compatibility with objects fit on train only; "
                "never used for fitting, tuning, or threshold selection"
            ),
            "future_validation_note": (
                "Use the materialized validation partition for model selection without refitting "
                "preprocessing on validation or test."
            ),
        }

    if labels == {DEVELOPMENT_LABEL, TEST_LABEL}:
        return {
            "partition_structure": "development_test",
            "fitting_partition": DEVELOPMENT_LABEL,
            "transform_partitions": [DEVELOPMENT_LABEL, TEST_LABEL],
            "validation_partition_available": False,
            "final_test_treatment": (
                "transformed only as a compatibility check with objects fit on development; "
                "not used for fitting, tuning, threshold selection, or model selection"
            ),
            "future_validation_note": (
                "Future AO1 model selection must create time-preserving validation folds or "
                "a further chronological validation split inside development, and must refit "
                "preprocessing inside each inner training fold."
            ),
        }

    raise ValueError(
        "AO1 partition labels are unclear. Expected exactly "
        f"{sorted([DEVELOPMENT_LABEL, TEST_LABEL])} or "
        f"{sorted([TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL])}; found {sorted(labels)}."
    )


def collect_partition_labels(df: DataFrame) -> set[str]:
    """Collect partition labels from the AO1 partition artifact."""
    labels = {row[PARTITION_COLUMN] for row in df.select(PARTITION_COLUMN).distinct().collect()}
    if TEST_LABEL not in labels:
        raise ValueError(f"Final test partition label `{TEST_LABEL}` is missing from AO1 partitions.")
    return labels


def build_sklearn_preprocessor() -> Any:
    """Build the sklearn ColumnTransformer for AO1 preprocessing."""
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    try:
        one_hot_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        one_hot_encoder = OneHotEncoder(handle_unknown="ignore", sparse=True)

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    binary_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("onehot", one_hot_encoder),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric_continuous", numeric_transformer, list(NUMERIC_CONTINUOUS_COLUMNS)),
            ("binary_flags", binary_transformer, list(BINARY_FLAG_COLUMNS)),
            ("categorical", categorical_transformer, list(CATEGORICAL_COLUMNS)),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )


def load_partition_as_pandas(df: DataFrame, partition_label: str) -> Any:
    """Collect one partition's target and predictors as a pandas DataFrame."""
    selected_columns = [*FEATURE_COLUMNS, TARGET_COLUMN]
    return (
        df.filter(col(PARTITION_COLUMN) == partition_label)
        .select(*selected_columns)
        .toPandas()
    )


def get_package_version(package_name: str) -> str | None:
    """Return an installed package version if available."""
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def build_static_metadata(
    config: AO1PreprocessingConfig,
    partition_usage: dict[str, Any],
    *,
    partition_labels: list[str],
    transformed_shapes: dict[str, dict[str, int | None]] | None = None,
    partition_row_counts: dict[str, int] | None = None,
    fitted_artifact_saved: bool = False,
) -> dict[str, Any]:
    """Build lightweight metadata for the AO1 preprocessing layer."""
    return {
        "metadata_status": "runtime_fit_completed",
        "issue": "#26",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": config.partition_input_path,
        "partition_column": PARTITION_COLUMN,
        "partition_labels_observed": partition_labels,
        "partition_usage": partition_usage,
        "fit_source_partition": partition_usage["fitting_partition"],
        "fit_uses_validation": False,
        "fit_uses_test": False,
        "target_column": TARGET_COLUMN,
        "feature_columns": list(FEATURE_COLUMNS),
        "excluded_identifier_metadata_columns": list(EXCLUDED_IDENTIFIER_METADATA_COLUMNS),
        "excluded_columns": list(EXCLUDED_IDENTIFIER_METADATA_COLUMNS),
        "forbidden_leakage_columns": list(FORBIDDEN_LEAKAGE_COLUMNS),
        "numeric_continuous_columns": list(NUMERIC_CONTINUOUS_COLUMNS),
        "binary_flag_columns": list(BINARY_FLAG_COLUMNS),
        "categorical_columns": list(CATEGORICAL_COLUMNS),
        "preprocessing": {
            "numeric_continuous": {
                "imputer": "SimpleImputer(strategy='median')",
                "scaler": "StandardScaler()",
                "fit_scope": "fit partition only",
            },
            "binary_flags": {
                "imputer": "SimpleImputer(strategy='most_frequent')",
                "scaler": "none",
                "encoding": "passthrough after imputation",
                "fit_scope": "fit partition only",
            },
            "categorical": {
                "imputer": "SimpleImputer(strategy='constant', fill_value='unknown')",
                "encoder": "OneHotEncoder(handle_unknown='ignore')",
                "fit_scope": "fit partition only",
            },
            "target_encoding": "not_used",
            "remainder": "drop",
        },
        "smote": {
            "decision": "deferred",
            "enabled_in_this_issue": False,
            "executed_in_this_issue": False,
            "training_only": True,
            "validation_resampling_allowed": False,
            "test_resampling_allowed": False,
            "apply_before_split_allowed": False,
            "save_resampled_dataset": False,
            "sampling_strategy_if_enabled_later": "auto",
            "random_state_if_enabled_later": 620,
            "k_neighbors_if_enabled_later": 5,
            "rationale": (
                "AO1 class imbalance analysis reports mild imbalance "
                "(majority/minority ratio about 1.214:1). Keep SMOTE off in the "
                "preprocessing artifact; future AO1 training may enable it only "
                "inside the training fold if validation results justify it."
            ),
        },
        "transformed_output_shape_by_partition": transformed_shapes or {},
        "partition_row_counts_before_smote": partition_row_counts or {},
        "no_resampled_validation_or_test_outputs_created": True,
        "fitted_artifact": {
            "saved": fitted_artifact_saved,
            "path": config.fitted_preprocessor_output_path if fitted_artifact_saved else None,
            "default_policy": (
                "Do not commit large fitted binary artifacts. Save a fitted "
                "preprocessor to a Databricks Volume only when explicitly enabled."
            ),
        },
        "pipeline_specification": {
            "library": "sklearn",
            "object": "ColumnTransformer",
            "transformers": [
                "numeric_continuous",
                "binary_flags",
                "categorical",
            ],
        },
        "versions": {
            "sklearn": get_package_version("scikit-learn"),
            "imbalanced_learn": get_package_version("imbalanced-learn"),
        },
    }


def save_metadata(metadata: dict[str, Any], output_path: Path) -> None:
    """Write JSON metadata to the configured lightweight artifact path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")


def save_fitted_preprocessor(preprocessor: Any, output_path: str) -> None:
    """Persist a fitted sklearn preprocessor when explicitly enabled."""
    if output_path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
        raise ValueError(
            f"Fitted preprocessor path points to the disabled public DBFS root: {output_path}"
        )

    from joblib import dump

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    dump(preprocessor, output_path)


def run_ao1_preprocessing_pipeline(
    config: AO1PreprocessingConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Fit AO1 preprocessing on the fitting partition and write metadata."""
    spark = get_spark_session()

    logger.info("Starting AO1 preprocessing pipeline build.")
    logger.info("AO1 partition input path: %s", config.partition_input_path)
    logger.info("Metadata output path: %s", config.metadata_output_path)

    validate_input_path(config.partition_input_path, "partition_input_path")
    partitioned_df = read_delta(spark, config.partition_input_path, config.read_format)

    assert_required_columns_exist(partitioned_df)
    assert_column_group_contract()
    assert_target_contract(partitioned_df)

    partition_labels = collect_partition_labels(partitioned_df)
    partition_usage = determine_partition_usage(partition_labels)
    fitting_partition = partition_usage["fitting_partition"]

    logger.info("Observed partition labels: %s", sorted(partition_labels))
    logger.info("Fitting preprocessing on partition: %s", fitting_partition)

    fit_pdf = load_partition_as_pandas(partitioned_df, fitting_partition)
    x_fit = fit_pdf.loc[:, list(FEATURE_COLUMNS)]

    preprocessor = build_sklearn_preprocessor()
    preprocessor.fit(x_fit)
    logger.info("Preprocessing object fit completed on %s rows.", len(x_fit))

    transformed_shapes: dict[str, dict[str, int | None]] = {}
    partition_row_counts: dict[str, int] = {}
    for partition_label in partition_usage["transform_partitions"]:
        partition_pdf = (
            fit_pdf
            if partition_label == fitting_partition
            else load_partition_as_pandas(partitioned_df, partition_label)
        )
        x_partition = partition_pdf.loc[:, list(FEATURE_COLUMNS)]
        transformed = preprocessor.transform(x_partition)
        transformed_shapes[partition_label] = {
            "input_rows": int(len(x_partition)),
            "transformed_rows": int(transformed.shape[0]),
            "transformed_columns": int(transformed.shape[1]),
        }
        partition_row_counts[partition_label] = int(len(x_partition))
        logger.info(
            "Transformed partition %s without refit: rows=%s, columns=%s",
            partition_label,
            transformed.shape[0],
            transformed.shape[1],
        )

    fitted_artifact_saved = False
    if config.save_fitted_preprocessor:
        save_fitted_preprocessor(preprocessor, config.fitted_preprocessor_output_path)
        fitted_artifact_saved = True
        logger.info("Saved fitted preprocessor: %s", config.fitted_preprocessor_output_path)

    metadata = build_static_metadata(
        config,
        partition_usage,
        partition_labels=sorted(partition_labels),
        transformed_shapes=transformed_shapes,
        partition_row_counts=partition_row_counts,
        fitted_artifact_saved=fitted_artifact_saved,
    )
    save_metadata(metadata, config.metadata_output_path)
    logger.info("AO1 preprocessing metadata written: %s", config.metadata_output_path)
    logger.info("AO1 preprocessing pipeline build completed successfully.")
    return metadata


def main() -> None:
    """Run AO1 preprocessing pipeline build with default configuration."""
    run_ao1_preprocessing_pipeline(AO1PreprocessingConfig(), configure_logging())


if __name__ == "__main__":
    main()
