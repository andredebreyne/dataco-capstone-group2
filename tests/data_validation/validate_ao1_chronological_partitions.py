"""Validate AO1 chronological development/test partitions.

Run this script in Databricks after
`src/modeling/create_ao1_chronological_partitions.py` completes. The checks
confirm that the saved AO1 partition table follows the frozen chronological
split policy and preserves the AO1 Gold population exactly.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    count as spark_count,
    lag,
    max as spark_max,
    min as spark_min,
    sum as spark_sum,
    when,
)
from pyspark.sql.window import Window


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

DEFAULT_GOLD_AO1_PATH = f"{VOLUME_ROOT}/gold/ao1_late_delivery_analytical_table"
GOLD_AO1_PATH = os.getenv("DATACO_GOLD_AO1_OUTPUT_PATH", DEFAULT_GOLD_AO1_PATH)

DEFAULT_PARTITION_PATH = f"{VOLUME_ROOT}/gold/ao1_late_delivery_chronological_partitions"
AO1_PARTITION_PATH = os.getenv(
    "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
    DEFAULT_PARTITION_PATH,
)

JOIN_KEY_COLUMNS = ("Order_Id", "Order_Item_Id", "order_date_DateOrders")
ORDERING_COLUMNS = ("order_date_DateOrders", "Order_Id", "Order_Item_Id")
TARGET_COLUMN = "Late_delivery_risk"
ROW_NUMBER_COLUMN = "chronological_row_number"
PARTITION_COLUMN = "split_partition"
DEVELOPMENT_LABEL = "development"
TEST_LABEL = "test"
VALID_PARTITION_LABELS = {DEVELOPMENT_LABEL, TEST_LABEL}
DEVELOPMENT_RATIO = 0.80

REQUIRED_PARTITION_COLUMNS = (
    *JOIN_KEY_COLUMNS,
    TARGET_COLUMN,
    ROW_NUMBER_COLUMN,
    PARTITION_COLUMN,
)

ALLOWED_ADDED_COLUMNS = {ROW_NUMBER_COLUMN, PARTITION_COLUMN}


def resolve_repo_root() -> Path:
    """Resolve repository root for scripts and notebooks."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]

    current_path = Path.cwd().resolve()
    for candidate in (current_path, *current_path.parents):
        if (
            candidate / "data" / "references" / "chronological_split_policy.csv"
        ).exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()
SUMMARY_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_CHRONOLOGICAL_PARTITION_SUMMARY_PATH",
        str(REPO_ROOT / "data" / "references" / "ao1_chronological_partition_summary.csv"),
    )
)


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def read_delta_or_fail(spark: SparkSession, path: str, table_name: str) -> DataFrame:
    """Read a Delta table and raise a clear assertion if it is unavailable."""
    try:
        return spark.read.format("delta").load(path)
    except Exception as exc:
        raise AssertionError(f"{table_name} Delta output does not exist or is unreadable: {path}") from exc


def assert_required_columns_exist(partitioned_df: DataFrame) -> None:
    """Validate that required partition columns exist."""
    missing_columns = sorted(
        column_name
        for column_name in REQUIRED_PARTITION_COLUMNS
        if column_name not in partitioned_df.columns
    )
    assert not missing_columns, f"Missing AO1 partition columns: {missing_columns}"


def assert_gold_columns_preserved(gold_df: DataFrame, partitioned_df: DataFrame) -> None:
    """Validate partition output contains Gold rows plus only split metadata."""
    missing_gold_columns = sorted(
        column_name for column_name in gold_df.columns if column_name not in partitioned_df.columns
    )
    assert not missing_gold_columns, (
        f"AO1 partition output is missing AO1 Gold columns: {missing_gold_columns}"
    )

    unexpected_added_columns = sorted(
        set(partitioned_df.columns).difference(gold_df.columns).difference(ALLOWED_ADDED_COLUMNS)
    )
    assert not unexpected_added_columns, (
        "AO1 partition output contains unexpected helper columns. "
        f"Only {sorted(ALLOWED_ADDED_COLUMNS)} may be added. "
        f"Found: {unexpected_added_columns}"
    )


def assert_row_count_matches(gold_df: DataFrame, partitioned_df: DataFrame) -> int:
    """Validate partition output row count equals AO1 Gold row count."""
    gold_count = gold_df.count()
    partition_count = partitioned_df.count()
    assert partition_count == gold_count, (
        f"AO1 partition row count must equal AO1 Gold. "
        f"Gold: {gold_count}; partitioned: {partition_count}."
    )
    assert gold_count > 0, "AO1 Gold is empty; chronological partitions cannot be valid."
    return gold_count


def assert_unique_keys(df: DataFrame, table_name: str) -> None:
    """Validate one row per AO1 order item key."""
    row_count = df.count()
    distinct_key_count = df.select(*JOIN_KEY_COLUMNS).distinct().count()
    assert row_count == distinct_key_count, (
        f"{table_name} contains duplicate keys. "
        f"Rows: {row_count}; distinct keys: {distinct_key_count}."
    )


def assert_keys_match_gold(gold_df: DataFrame, partitioned_df: DataFrame) -> None:
    """Validate no AO1 Gold keys were lost or duplicated in partition output."""
    gold_keys = gold_df.select(*JOIN_KEY_COLUMNS)
    partition_keys = partitioned_df.select(*JOIN_KEY_COLUMNS)

    missing_from_partitions = gold_keys.join(
        partition_keys,
        list(JOIN_KEY_COLUMNS),
        "left_anti",
    ).count()
    unexpected_in_partitions = partition_keys.join(
        gold_keys,
        list(JOIN_KEY_COLUMNS),
        "left_anti",
    ).count()

    assert missing_from_partitions == 0 and unexpected_in_partitions == 0, (
        "AO1 partition keys do not exactly match AO1 Gold keys. "
        f"Missing from partitions: {missing_from_partitions}; "
        f"unexpected in partitions: {unexpected_in_partitions}."
    )


def assert_valid_partition_labels(partitioned_df: DataFrame) -> None:
    """Validate partition labels are the approved frozen labels."""
    actual_labels = {
        row[PARTITION_COLUMN]
        for row in partitioned_df.select(PARTITION_COLUMN).distinct().collect()
    }
    assert actual_labels == VALID_PARTITION_LABELS, (
        f"Invalid AO1 partition labels. Expected {sorted(VALID_PARTITION_LABELS)}, "
        f"found {sorted(actual_labels)}."
    )


def assert_boundary_counts(partitioned_df: DataFrame, total_rows: int) -> int:
    """Validate development/test counts match the frozen 80/20 boundary."""
    boundary = math.floor(total_rows * DEVELOPMENT_RATIO)
    development_count = partitioned_df.filter(col(PARTITION_COLUMN) == DEVELOPMENT_LABEL).count()
    test_count = partitioned_df.filter(col(PARTITION_COLUMN) == TEST_LABEL).count()

    assert development_count == boundary, (
        f"Development row count must equal floor(total_rows * 0.80). "
        f"Expected {boundary}; found {development_count}."
    )
    assert test_count == total_rows - boundary, (
        f"Test row count must equal total_rows - boundary. "
        f"Expected {total_rows - boundary}; found {test_count}."
    )
    return boundary


def assert_row_numbers_are_complete(partitioned_df: DataFrame, total_rows: int) -> None:
    """Validate row numbers are deterministic 1-based row numbers with no gaps."""
    row_number_stats = partitioned_df.agg(
        spark_min(col(ROW_NUMBER_COLUMN)).alias("min_row_number"),
        spark_max(col(ROW_NUMBER_COLUMN)).alias("max_row_number"),
        spark_count(col(ROW_NUMBER_COLUMN)).alias("non_null_row_number_count"),
    ).collect()[0]
    distinct_row_numbers = partitioned_df.select(ROW_NUMBER_COLUMN).distinct().count()

    assert row_number_stats["min_row_number"] == 1, (
        f"Minimum chronological row number must be 1; "
        f"found {row_number_stats['min_row_number']}."
    )
    assert row_number_stats["max_row_number"] == total_rows, (
        f"Maximum chronological row number must equal total rows {total_rows}; "
        f"found {row_number_stats['max_row_number']}."
    )
    assert row_number_stats["non_null_row_number_count"] == total_rows, (
        "Chronological row numbers contain nulls."
    )
    assert distinct_row_numbers == total_rows, (
        f"Chronological row numbers must be unique and gap-free. "
        f"Distinct row numbers: {distinct_row_numbers}; total rows: {total_rows}."
    )


def assert_row_number_boundary_assignment(partitioned_df: DataFrame, boundary: int) -> None:
    """Validate partitions are assigned only from row-number boundary logic."""
    invalid_development_rows = partitioned_df.filter(
        (col(PARTITION_COLUMN) == DEVELOPMENT_LABEL)
        & (col(ROW_NUMBER_COLUMN) > boundary)
    ).count()
    invalid_test_rows = partitioned_df.filter(
        (col(PARTITION_COLUMN) == TEST_LABEL)
        & (col(ROW_NUMBER_COLUMN) <= boundary)
    ).count()
    invalid_labels_by_rule = partitioned_df.filter(
        when(col(ROW_NUMBER_COLUMN) <= boundary, col(PARTITION_COLUMN) != DEVELOPMENT_LABEL)
        .otherwise(col(PARTITION_COLUMN) != TEST_LABEL)
    ).count()

    assert invalid_development_rows == 0, (
        f"Development rows found after boundary {boundary}: {invalid_development_rows}"
    )
    assert invalid_test_rows == 0, (
        f"Test rows found at or before boundary {boundary}: {invalid_test_rows}"
    )
    assert invalid_labels_by_rule == 0, (
        "Partition labels do not exactly match row-number boundary assignment. "
        f"Invalid rows: {invalid_labels_by_rule}."
    )


def assert_chronological_ordering_monotonic(partitioned_df: DataFrame) -> None:
    """Validate ordering columns are monotonic when sorted by row number."""
    window_by_row_number = Window.orderBy(col(ROW_NUMBER_COLUMN).asc())
    ordered_df = (
        partitioned_df
        .select(ROW_NUMBER_COLUMN, *ORDERING_COLUMNS)
        .withColumn("_previous_order_date", lag(col("order_date_DateOrders")).over(window_by_row_number))
        .withColumn("_previous_order_id", lag(col("Order_Id")).over(window_by_row_number))
        .withColumn("_previous_order_item_id", lag(col("Order_Item_Id")).over(window_by_row_number))
    )

    violations = ordered_df.filter(
        (col("_previous_order_date").isNotNull())
        & (
            (col("_previous_order_date") > col("order_date_DateOrders"))
            | (
                (col("_previous_order_date") == col("order_date_DateOrders"))
                & (col("_previous_order_id") > col("Order_Id"))
            )
            | (
                (col("_previous_order_date") == col("order_date_DateOrders"))
                & (col("_previous_order_id") == col("Order_Id"))
                & (col("_previous_order_item_id") > col("Order_Item_Id"))
            )
        )
    ).count()

    assert violations == 0, (
        "Chronological row numbers are not monotonic by "
        "`order_date_DateOrders`, `Order_Id`, and `Order_Item_Id`. "
        f"Violations: {violations}."
    )


def assert_test_range_follows_development(partitioned_df: DataFrame) -> None:
    """Validate final test dates are later than or equal to the development boundary."""
    range_rows = {
        row[PARTITION_COLUMN]: row.asDict()
        for row in partitioned_df.groupBy(PARTITION_COLUMN).agg(
            spark_min(col("order_date_DateOrders")).alias("min_date"),
            spark_max(col("order_date_DateOrders")).alias("max_date"),
        ).collect()
    }

    development_max = range_rows[DEVELOPMENT_LABEL]["max_date"]
    test_min = range_rows[TEST_LABEL]["min_date"]
    assert test_min >= development_max, (
        "Final test date range must be later than or equal to the development "
        f"boundary. Development max: {development_max}; test min: {test_min}."
    )


def collect_target_distribution(partitioned_df: DataFrame) -> list[dict[str, Any]]:
    """Collect target distribution by partition for reporting."""
    rows = (
        partitioned_df.groupBy(PARTITION_COLUMN)
        .agg(
            spark_count("*").alias("row_count"),
            spark_sum(when(col(TARGET_COLUMN) == 1, 1).otherwise(0)).alias("late_count"),
            spark_sum(when(col(TARGET_COLUMN) == 0, 1).otherwise(0)).alias("non_late_count"),
            spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias(
                "target_missing_count"
            ),
        )
        .collect()
    )

    distribution = []
    for row in rows:
        row_dict = row.asDict()
        row_count = row_dict["row_count"]
        row_dict["late_delivery_rate"] = (
            row_dict["late_count"] / row_count if row_count else 0.0
        )
        distribution.append(row_dict)

    return sorted(
        distribution,
        key=lambda row: {DEVELOPMENT_LABEL: 1, TEST_LABEL: 2}.get(row[PARTITION_COLUMN], 99),
    )


def assert_target_complete_and_binary_by_partition(partitioned_df: DataFrame) -> None:
    """Validate the AO1 target remains complete and binary in each partition."""
    invalid_target_count = partitioned_df.filter(
        col(TARGET_COLUMN).isNull() | (~col(TARGET_COLUMN).isin(0, 1))
    ).count()
    assert invalid_target_count == 0, (
        f"AO1 target must be complete and binary in every partition. "
        f"Invalid rows: {invalid_target_count}."
    )

    for row in collect_target_distribution(partitioned_df):
        assert row["late_count"] > 0 and row["non_late_count"] > 0, (
            "Each AO1 partition should contain both target classes for model "
            f"evaluation. Distribution row: {row}."
        )


def assert_no_random_or_target_based_split_helpers(
    gold_df: DataFrame,
    partitioned_df: DataFrame,
) -> None:
    """Validate split output has no random or target-derived helper columns."""
    assert_gold_columns_preserved(gold_df, partitioned_df)

    suspicious_terms = ("random", "shuffle", "stratified", "target_split", "label_split")
    suspicious_columns = sorted(
        column_name
        for column_name in partitioned_df.columns
        if column_name not in gold_df.columns
        and any(term in column_name.lower() for term in suspicious_terms)
    )
    assert not suspicious_columns, (
        f"Partition output contains random or target-split helper columns: {suspicious_columns}"
    )


def print_partition_report(
    partitioned_df: DataFrame,
    total_rows: int,
    boundary: int,
) -> None:
    """Print a concise partition report for validation logs."""
    print("\nAO1 chronological partition validation summary:")
    print(f"- AO1 Gold rows: {total_rows:,}")
    print(f"- Development boundary row number: {boundary:,}")
    print(f"- Split formula: row_number <= floor(total_rows * 0.80)")
    print(f"- Ordering columns: {'; '.join(ORDERING_COLUMNS)}")
    print(f"- Partition output path: {AO1_PARTITION_PATH}")

    date_ranges = (
        partitioned_df.groupBy(PARTITION_COLUMN)
        .agg(
            spark_count("*").alias("row_count"),
            spark_min(col("order_date_DateOrders")).alias("min_date"),
            spark_max(col("order_date_DateOrders")).alias("max_date"),
            spark_min(col(ROW_NUMBER_COLUMN)).alias("min_row_number"),
            spark_max(col(ROW_NUMBER_COLUMN)).alias("max_row_number"),
        )
        .collect()
    )
    for row in sorted(
        date_ranges,
        key=lambda value: {DEVELOPMENT_LABEL: 1, TEST_LABEL: 2}.get(value[PARTITION_COLUMN], 99),
    ):
        print(
            "- "
            f"{row[PARTITION_COLUMN]}: rows={row['row_count']:,}, "
            f"dates={row['min_date']} to {row['max_date']}, "
            f"row_numbers={row['min_row_number']:,} to {row['max_row_number']:,}"
        )

    print("- Target distribution:")
    for row in collect_target_distribution(partitioned_df):
        print(
            "  "
            f"{row[PARTITION_COLUMN]}: late={row['late_count']:,}, "
            f"non_late={row['non_late_count']:,}, "
            f"missing={row['target_missing_count']:,}, "
            f"late_rate={row['late_delivery_rate']:.4f}"
        )

    if SUMMARY_CSV_PATH.exists():
        print(f"- Summary CSV found: {SUMMARY_CSV_PATH}")
    else:
        print(
            "- Summary CSV not found locally; run the partition creation script "
            f"to generate it at {SUMMARY_CSV_PATH}."
        )


def run_validation() -> None:
    """Run all AO1 chronological partition validations."""
    spark = get_spark_session()
    gold_df = read_delta_or_fail(spark, GOLD_AO1_PATH, "AO1 Gold")
    partitioned_df = read_delta_or_fail(
        spark,
        AO1_PARTITION_PATH,
        "AO1 chronological partition",
    )

    assert_required_columns_exist(partitioned_df)
    assert_no_random_or_target_based_split_helpers(gold_df, partitioned_df)
    total_rows = assert_row_count_matches(gold_df, partitioned_df)
    assert_unique_keys(gold_df, "AO1 Gold")
    assert_unique_keys(partitioned_df, "AO1 chronological partitions")
    assert_keys_match_gold(gold_df, partitioned_df)
    assert_valid_partition_labels(partitioned_df)
    boundary = assert_boundary_counts(partitioned_df, total_rows)
    assert_row_numbers_are_complete(partitioned_df, total_rows)
    assert_row_number_boundary_assignment(partitioned_df, boundary)
    assert_chronological_ordering_monotonic(partitioned_df)
    assert_test_range_follows_development(partitioned_df)
    assert_target_complete_and_binary_by_partition(partitioned_df)

    print_partition_report(partitioned_df, total_rows, boundary)
    print("\nAO1 chronological partition validation passed.")


if __name__ == "__main__":
    run_validation()

