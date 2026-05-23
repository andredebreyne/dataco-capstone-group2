"""Validate AO1 preprocessing pipeline metadata and runtime isolation rules.

Run this script in Databricks after
`src/modeling/build_ao1_preprocessing_pipeline.py` completes. Static metadata
checks can also run before the Delta input is available, but data-dependent
checks require the AO1 chronological partition table.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

DEFAULT_AO1_PARTITION_PATH = f"{VOLUME_ROOT}/gold/ao1_late_delivery_chronological_partitions"
AO1_PARTITION_PATH = os.getenv(
    "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
    DEFAULT_AO1_PARTITION_PATH,
)

TARGET_COLUMN = "Late_delivery_risk"
PARTITION_COLUMN = "split_partition"
TEST_LABEL = "test"
ALLOWED_FIT_PARTITIONS = {"development", "train"}

IDENTIFIER_METADATA_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    "_gold_ao1_processed_timestamp",
}

FORBIDDEN_LEAKAGE_COLUMNS = {
    TARGET_COLUMN,
    "Delivery_Status",
    "Delivery Status",
    "Days_for_shipping_real",
    "Days for shipping (real)",
    "shipping_date_DateOrders",
    "shipping date (DateOrders)",
    "Order_Status",
    "Order Status",
    "Order_Profit_Per_Order",
    "Order Profit Per Order",
    "Benefit_per_order",
    "Benefit per order",
    "Order_Item_Profit_Ratio",
    "Order Item Profit Ratio",
}

REQUIRED_METADATA_KEYS = {
    "input_path",
    "partition_column",
    "partition_usage",
    "fit_source_partition",
    "fit_uses_test",
    "target_column",
    "feature_columns",
    "excluded_identifier_metadata_columns",
    "numeric_continuous_columns",
    "binary_flag_columns",
    "categorical_columns",
    "preprocessing",
    "smote",
    "pipeline_specification",
    "fitted_artifact",
}


def resolve_repo_root() -> Path:
    """Resolve repository root for local metadata artifacts."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]

    current_path = Path.cwd().resolve()
    for candidate in (current_path, *current_path.parents):
        if (candidate / "models").exists() and (candidate / "src").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_PREPROCESSING_METADATA_PATH",
        str(
            REPO_ROOT
            / "models"
            / "ao1_late_delivery"
            / "preprocessing"
            / "ao1_preprocessing_metadata.json"
        ),
    )
)


def get_spark_session() -> Any | None:
    """Return the active Databricks Spark session when PySpark is available."""
    try:
        from pyspark.sql import SparkSession
    except ModuleNotFoundError:
        print("PySpark is unavailable; static metadata checks completed only.")
        return None

    return SparkSession.builder.getOrCreate()


def read_metadata() -> dict[str, Any]:
    """Read the AO1 preprocessing metadata JSON."""
    assert METADATA_PATH.exists(), f"Missing AO1 preprocessing metadata: {METADATA_PATH}"
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


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


def assert_required_metadata_keys(metadata: dict[str, Any]) -> None:
    """Validate the metadata contains required top-level keys."""
    missing_keys = sorted(REQUIRED_METADATA_KEYS.difference(metadata))
    assert not missing_keys, f"AO1 preprocessing metadata is missing keys: {missing_keys}"


def assert_feature_list_is_safe(metadata: dict[str, Any]) -> None:
    """Validate target, identifiers, partitions, and leakage fields are excluded."""
    feature_columns = set(metadata["feature_columns"])
    assert metadata["target_column"] == TARGET_COLUMN, (
        f"Unexpected AO1 target column: {metadata['target_column']}"
    )
    assert TARGET_COLUMN not in feature_columns, "AO1 target is present in feature columns."

    identifier_overlap = sorted(feature_columns.intersection(IDENTIFIER_METADATA_COLUMNS))
    assert not identifier_overlap, (
        f"Identifier, partition, or metadata columns found in features: {identifier_overlap}"
    )

    forbidden_normalized = {normalize_column_name(column_name) for column_name in FORBIDDEN_LEAKAGE_COLUMNS}
    feature_normalized = {normalize_column_name(column_name) for column_name in feature_columns}
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    assert not forbidden_overlap, f"Forbidden leakage columns found in features: {forbidden_overlap}"


def assert_column_groups_are_valid(metadata: dict[str, Any]) -> None:
    """Validate declared feature groups are non-overlapping and complete."""
    groups = {
        "numeric_continuous_columns": set(metadata["numeric_continuous_columns"]),
        "binary_flag_columns": set(metadata["binary_flag_columns"]),
        "categorical_columns": set(metadata["categorical_columns"]),
    }

    group_names = list(groups)
    for index, left_name in enumerate(group_names):
        for right_name in group_names[index + 1 :]:
            overlap = sorted(groups[left_name].intersection(groups[right_name]))
            assert not overlap, f"Column groups overlap between {left_name} and {right_name}: {overlap}"

    grouped_features = set().union(*groups.values())
    feature_columns = set(metadata["feature_columns"])
    assert grouped_features == feature_columns, (
        "Column groups must exactly cover AO1 feature columns. "
        f"Missing from groups: {sorted(feature_columns.difference(grouped_features))}; "
        f"unexpected in groups: {sorted(grouped_features.difference(feature_columns))}."
    )


def assert_fit_scope_is_valid(metadata: dict[str, Any]) -> None:
    """Validate preprocessing fit source excludes validation/test data."""
    fit_source = metadata["fit_source_partition"]
    assert fit_source in ALLOWED_FIT_PARTITIONS, (
        f"Preprocessing fit source must be development or train only. Found: {fit_source}"
    )
    assert not metadata["fit_uses_test"], "AO1 preprocessing metadata says the test set was used for fit."
    assert metadata["partition_usage"]["fitting_partition"] == fit_source, (
        "Partition usage fitting partition does not match fit_source_partition."
    )


def assert_smote_policy_is_valid(metadata: dict[str, Any]) -> None:
    """Validate SMOTE is configured as training-only and not applied to test/validation."""
    smote = metadata["smote"]
    assert smote["training_only"] is True, "SMOTE configuration must be training-only."
    assert smote["test_resampling_allowed"] is False, "SMOTE must not be allowed on test data."
    assert smote["validation_resampling_allowed"] is False, (
        "SMOTE must not be allowed on validation data."
    )
    assert smote["apply_before_split_allowed"] is False, "SMOTE must not be applied before split."
    assert smote["save_resampled_dataset"] is False, "Do not save resampled datasets as source of truth."
    assert metadata["no_resampled_validation_or_test_outputs_created"] is True, (
        "Metadata must confirm no resampled validation/test outputs were created."
    )


def read_partition_delta_if_available(spark: Any | None, path: str) -> Any | None:
    """Read the AO1 partition Delta table when available."""
    if spark is None:
        return None

    try:
        return spark.read.format("delta").load(path)
    except Exception as exc:
        print(
            "AO1 partition Delta table is unavailable; static metadata checks completed only. "
            f"Path: {path}. Error: {type(exc).__name__}: {exc}"
        )
        return None


def assert_feature_columns_exist_in_partition(metadata: dict[str, Any], df: Any) -> None:
    """Validate declared feature columns exist in the AO1 partition table."""
    missing_columns = sorted(
        column_name for column_name in metadata["feature_columns"] if column_name not in df.columns
    )
    assert not missing_columns, f"Metadata feature columns missing from AO1 partition table: {missing_columns}"


def assert_partition_fit_source_matches_data(metadata: dict[str, Any], df: Any) -> None:
    """Validate partition labels and final test availability against the data."""
    labels = {row[PARTITION_COLUMN] for row in df.select(PARTITION_COLUMN).distinct().collect()}
    assert TEST_LABEL in labels, f"Final test partition `{TEST_LABEL}` is missing."
    assert metadata["fit_source_partition"] in labels, (
        f"Fit source partition {metadata['fit_source_partition']} not present in data labels {sorted(labels)}."
    )


def assert_transformed_shapes_match_row_counts(metadata: dict[str, Any], df: Any) -> None:
    """Validate transform shape metadata preserves row counts before any SMOTE step."""
    from pyspark.sql.functions import col

    shapes = metadata.get("transformed_output_shape_by_partition", {})
    if not shapes:
        print(
            "No transformed shape metadata is present. Run the preprocessing build job "
            "in Databricks to validate transform compatibility."
        )
        return

    for partition_label, shape in shapes.items():
        input_count = df.filter(col(PARTITION_COLUMN) == partition_label).count()
        assert shape["input_rows"] == input_count, (
            f"Input row count mismatch for {partition_label}. "
            f"Metadata: {shape['input_rows']}; data: {input_count}."
        )
        assert shape["transformed_rows"] == input_count, (
            f"Transformed row count mismatch for {partition_label}. "
            f"Metadata: {shape['transformed_rows']}; data: {input_count}."
        )
        assert shape["transformed_columns"] > 0, (
            f"Transformed feature count must be positive for {partition_label}."
        )


def assert_no_resampled_validation_or_test_outputs() -> None:
    """Validate no local resampled validation or test artifacts were created."""
    preprocessing_dir = METADATA_PATH.parent
    if not preprocessing_dir.exists():
        return

    forbidden_patterns = (
        "*validation*smote*",
        "*validation*resampled*",
        "*test*smote*",
        "*test*resampled*",
    )
    forbidden_outputs: list[str] = []
    for pattern in forbidden_patterns:
        forbidden_outputs.extend(str(path) for path in preprocessing_dir.glob(pattern))

    assert not forbidden_outputs, (
        "Validation/test resampled outputs must not be created. "
        f"Found: {sorted(forbidden_outputs)}"
    )


def print_validation_summary(metadata: dict[str, Any]) -> None:
    """Print a concise validation report."""
    print("\nAO1 preprocessing validation summary:")
    print(f"- Metadata path: {METADATA_PATH}")
    print(f"- AO1 partition input path: {metadata['input_path']}")
    print(f"- Fit source partition: {metadata['fit_source_partition']}")
    print(f"- Transform partitions: {metadata['partition_usage']['transform_partitions']}")
    print(f"- Feature columns: {len(metadata['feature_columns'])}")
    print(f"- Numeric columns: {len(metadata['numeric_continuous_columns'])}")
    print(f"- Binary flag columns: {len(metadata['binary_flag_columns'])}")
    print(f"- Categorical columns: {len(metadata['categorical_columns'])}")
    print(f"- SMOTE decision: {metadata['smote']['decision']}")


def run_validation() -> None:
    """Run all AO1 preprocessing metadata validations."""
    metadata = read_metadata()
    assert_required_metadata_keys(metadata)
    assert_feature_list_is_safe(metadata)
    assert_column_groups_are_valid(metadata)
    assert_fit_scope_is_valid(metadata)
    assert_smote_policy_is_valid(metadata)
    assert_no_resampled_validation_or_test_outputs()

    spark = get_spark_session()
    partition_df = read_partition_delta_if_available(spark, metadata["input_path"])
    if partition_df is not None:
        assert_feature_columns_exist_in_partition(metadata, partition_df)
        assert_partition_fit_source_matches_data(metadata, partition_df)
        assert_transformed_shapes_match_row_counts(metadata, partition_df)

    print_validation_summary(metadata)
    print("\nAO1 preprocessing validation passed.")


if __name__ == "__main__":
    run_validation()
