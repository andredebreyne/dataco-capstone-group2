"""Validate AO2 preprocessing pipeline metadata and fit-scope rules.

Run this script in Databricks after
`src/modeling/build_ao2_preprocessing_pipeline.py` completes. Static metadata
checks can also run before the Delta input is available, but data-dependent
checks require the AO2 chronological partition table.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

DEFAULT_AO2_PARTITION_PATH = f"{VOLUME_ROOT}/gold/ao2_profitability_chronological_partitions"
AO2_PARTITION_PATH = os.getenv(
    "DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
    DEFAULT_AO2_PARTITION_PATH,
)

TARGET_COLUMN = "Order_Profit_Per_Order"
PARTITION_COLUMN = "split_partition"
DEVELOPMENT_LABEL = "development"
TRAIN_LABEL = "train"
VALIDATION_LABEL = "validation"
TEST_LABEL = "test"
ALLOWED_FIT_PARTITIONS = {DEVELOPMENT_LABEL, TRAIN_LABEL}

IDENTIFIER_METADATA_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    "_gold_ao2_processed_timestamp",
}

FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS = {
    TARGET_COLUMN,
    "Order Profit Per Order",
    "Benefit_per_order",
    "Benefit per order",
    "Order_Item_Profit_Ratio",
    "Order Item Profit Ratio",
    "Order_Item_Total",
    "Order Item Total",
    "ao3_order_value",
    "Sales",
    "Sales_per_customer",
    "Sales per customer",
    "Order_Item_Discount",
    "Order Item Discount",
    "Product_Price",
    "Product Price",
}

FORBIDDEN_POST_SHIPMENT_COLUMNS = {
    "Delivery_Status",
    "Delivery Status",
    "Days_for_shipping_real",
    "Days for shipping (real)",
    "shipping_date_DateOrders",
    "shipping date (DateOrders)",
    "Order_Status",
    "Order Status",
    "Late_delivery_risk",
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
    "excluded_target_proxy_near_formula_columns",
    "excluded_ao3_support_columns",
    "forbidden_target_reconstruction_columns",
    "numeric_continuous_columns",
    "binary_flag_columns",
    "categorical_columns",
    "preprocessing",
    "ao2_target_policy",
    "pipeline_specification",
    "fitted_artifact",
    "limitations",
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


def get_spark_session() -> Any | None:
    """Return the active Databricks Spark session when PySpark is available."""
    try:
        from pyspark.sql import SparkSession
    except ModuleNotFoundError:
        print("PySpark is unavailable; static metadata checks completed only.")
        return None

    return SparkSession.builder.getOrCreate()


def read_metadata() -> dict[str, Any]:
    """Read the AO2 preprocessing metadata JSON."""
    assert METADATA_PATH.exists(), f"Missing AO2 preprocessing metadata: {METADATA_PATH}"
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
    assert not missing_keys, f"AO2 preprocessing metadata is missing keys: {missing_keys}"


def assert_feature_list_is_safe(metadata: dict[str, Any]) -> None:
    """Validate target, identifiers, partitions, AO3 support, and leakage fields are excluded."""
    feature_columns = set(metadata["feature_columns"])
    assert metadata["target_column"] == TARGET_COLUMN, (
        f"Unexpected AO2 target column: {metadata['target_column']}"
    )
    assert TARGET_COLUMN not in feature_columns, "AO2 target is present in feature columns."
    assert "ao3_order_value" not in feature_columns, (
        "ao3_order_value is an AO3 support denominator and must not be an AO2 predictor."
    )

    identifier_overlap = sorted(feature_columns.intersection(IDENTIFIER_METADATA_COLUMNS))
    assert not identifier_overlap, (
        f"Identifier, partition, date, or metadata columns found in features: {identifier_overlap}"
    )

    forbidden_columns = FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS.union(FORBIDDEN_POST_SHIPMENT_COLUMNS)
    forbidden_normalized = {normalize_column_name(column_name) for column_name in forbidden_columns}
    feature_normalized = {normalize_column_name(column_name) for column_name in feature_columns}
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    assert not forbidden_overlap, (
        f"Forbidden AO2 target/proxy/leakage columns found in features: {forbidden_overlap}"
    )


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
        "Column groups must exactly cover AO2 feature columns. "
        f"Missing from groups: {sorted(feature_columns.difference(grouped_features))}; "
        f"unexpected in groups: {sorted(grouped_features.difference(feature_columns))}."
    )


def assert_fit_scope_is_valid(metadata: dict[str, Any]) -> None:
    """Validate preprocessing fit source excludes validation/test data."""
    fit_source = metadata["fit_source_partition"]
    partition_usage = metadata["partition_usage"]
    assert fit_source in ALLOWED_FIT_PARTITIONS, (
        f"Preprocessing fit source must be development or train only. Found: {fit_source}"
    )
    assert not metadata["fit_uses_test"], "AO2 preprocessing metadata says the test set was used for fit."
    assert not metadata.get("fit_uses_validation", False), (
        "AO2 standalone preprocessing metadata says validation was used for fit."
    )
    assert partition_usage["fitting_partition"] == fit_source, (
        "Partition usage fitting partition does not match fit_source_partition."
    )

    partition_structure = partition_usage["partition_structure"]
    if partition_structure == "development_test":
        assert fit_source == DEVELOPMENT_LABEL, (
            "Development/test AO2 partitions must fit preprocessing on development only."
        )
        assert partition_usage["transform_partitions"] == [DEVELOPMENT_LABEL, TEST_LABEL], (
            "Development/test AO2 transform partitions must be development and test."
        )
    elif partition_structure == "train_validation_test":
        assert fit_source == TRAIN_LABEL, (
            "Train/validation/test AO2 partitions must fit preprocessing on train only."
        )
        assert partition_usage["transform_partitions"] == [TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL], (
            "Train/validation/test AO2 transform partitions must be train, validation, and test."
        )
    else:
        raise AssertionError(f"Unexpected AO2 partition structure: {partition_structure}")


def assert_ao2_target_policy_is_valid(metadata: dict[str, Any]) -> None:
    """Validate AO2 target-policy safeguards recorded in metadata."""
    policy = metadata["ao2_target_policy"]
    assert policy["target_only"] == TARGET_COLUMN, "AO2 target policy must identify the target-only column."
    assert policy["ao3_order_value_excluded_as_predictor"] is True, (
        "Metadata must confirm ao3_order_value is excluded as an AO2 predictor."
    )
    assert policy["model_training_in_this_issue"] is False, (
        "AO2 preprocessing issue must not train models."
    )
    assert policy["margin_derivation_in_this_issue"] is False, (
        "AO2 preprocessing issue must not derive AO3 margins."
    )


def read_partition_delta_if_available(spark: Any | None, path: str) -> Any | None:
    """Read the AO2 partition Delta table when available."""
    if spark is None:
        return None

    try:
        return spark.read.format("delta").load(path)
    except Exception as exc:
        print(
            "AO2 partition Delta table is unavailable; static metadata checks completed only. "
            f"Path: {path}. Error: {type(exc).__name__}: {exc}"
        )
        return None


def assert_feature_columns_exist_in_partition(metadata: dict[str, Any], df: Any) -> None:
    """Validate declared feature columns exist in the AO2 partition table."""
    missing_columns = sorted(
        column_name for column_name in metadata["feature_columns"] if column_name not in df.columns
    )
    assert not missing_columns, f"Metadata feature columns missing from AO2 partition table: {missing_columns}"


def assert_partition_fit_source_matches_data(metadata: dict[str, Any], df: Any) -> None:
    """Validate partition labels and final test availability against the data."""
    labels = {row[PARTITION_COLUMN] for row in df.select(PARTITION_COLUMN).distinct().collect()}
    assert TEST_LABEL in labels, f"Final test partition `{TEST_LABEL}` is missing."
    expected_label_sets = {
        frozenset({DEVELOPMENT_LABEL, TEST_LABEL}),
        frozenset({TRAIN_LABEL, VALIDATION_LABEL, TEST_LABEL}),
    }
    assert frozenset(labels) in expected_label_sets, (
        f"Unexpected AO2 partition labels: {sorted(labels)}"
    )
    assert metadata["fit_source_partition"] in labels, (
        f"Fit source partition {metadata['fit_source_partition']} not present in data labels {sorted(labels)}."
    )
    assert metadata["fit_source_partition"] != TEST_LABEL, "Final test rows must never be used for fitting."


def assert_target_numeric_complete_and_not_feature(metadata: dict[str, Any], df: Any) -> None:
    """Validate target type, completeness, and exclusion from predictors."""
    from pyspark.sql.functions import col, sum as spark_sum, when
    from pyspark.sql.types import NumericType

    schema_by_name = {field.name: field.dataType for field in df.schema.fields}
    target_type = schema_by_name.get(TARGET_COLUMN)
    assert target_type is not None and isinstance(target_type, NumericType), (
        f"AO2 target must be numeric. Found: {target_type.simpleString() if target_type else 'missing'}"
    )
    assert TARGET_COLUMN not in metadata["feature_columns"], (
        "AO2 target must not be transformed as a predictor."
    )

    missing_count = df.select(
        spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias("missing_count")
    ).collect()[0]["missing_count"]
    assert missing_count == 0, f"AO2 target contains missing values: {missing_count}"


def assert_unique_keys(df: Any) -> None:
    """Validate one row per AO2 order item key."""
    key_columns = ("Order_Id", "Order_Item_Id", "order_date_DateOrders")
    row_count = df.count()
    distinct_key_count = df.select(*key_columns).distinct().count()
    assert row_count == distinct_key_count, (
        f"AO2 partition keys must remain unique. Rows: {row_count}; distinct keys: {distinct_key_count}."
    )


def assert_transformed_shapes_match_row_counts(metadata: dict[str, Any], df: Any) -> None:
    """Validate transform shape metadata preserves row counts without test fitting."""
    from pyspark.sql.functions import col

    shapes = metadata.get("transformed_output_shape_by_partition", {})
    if not shapes:
        print(
            "No transformed shape metadata is present. Run the AO2 preprocessing build job "
            "in Databricks to validate transform compatibility."
        )
        return

    assert TEST_LABEL in shapes, "Runtime metadata must include transformed final test shape."
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


def print_validation_summary(metadata: dict[str, Any]) -> None:
    """Print a concise validation report."""
    print("\nAO2 preprocessing validation summary:")
    print(f"- Metadata path: {METADATA_PATH}")
    print(f"- Metadata status: {metadata.get('metadata_status')}")
    print(f"- AO2 partition input path: {metadata['input_path']}")
    print(f"- Fit source partition: {metadata['fit_source_partition']}")
    print(f"- Transform partitions: {metadata['partition_usage']['transform_partitions']}")
    print(f"- Feature columns: {len(metadata['feature_columns'])}")
    print(f"- Numeric columns: {len(metadata['numeric_continuous_columns'])}")
    print(f"- Binary flag columns: {len(metadata['binary_flag_columns'])}")
    print(f"- Categorical columns: {len(metadata['categorical_columns'])}")
    print("- ao3_order_value excluded as predictor: true")


def run_validation() -> None:
    """Run all AO2 preprocessing metadata validations."""
    metadata = read_metadata()
    assert_required_metadata_keys(metadata)
    assert_feature_list_is_safe(metadata)
    assert_column_groups_are_valid(metadata)
    assert_fit_scope_is_valid(metadata)
    assert_ao2_target_policy_is_valid(metadata)

    spark = get_spark_session()
    partition_df = read_partition_delta_if_available(spark, metadata["input_path"])
    if partition_df is not None:
        assert_feature_columns_exist_in_partition(metadata, partition_df)
        assert_partition_fit_source_matches_data(metadata, partition_df)
        assert_target_numeric_complete_and_not_feature(metadata, partition_df)
        assert_unique_keys(partition_df)
        assert_transformed_shapes_match_row_counts(metadata, partition_df)

    print_validation_summary(metadata)
    print("\nAO2 preprocessing validation passed.")


if __name__ == "__main__":
    run_validation()
