"""Validate AO2 chronological development/test partitions.

Run this script in Databricks after
`src/modeling/create_ao2_chronological_partitions.py` completes. The checks
confirm that the saved AO2 partition table follows the frozen chronological
split policy and preserves the AO2 Gold population exactly.
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

DEFAULT_GOLD_AO2_PATH = f"{VOLUME_ROOT}/gold/ao2_profitability_analytical_table"
GOLD_AO2_PATH = os.getenv("DATACO_GOLD_AO2_OUTPUT_PATH", DEFAULT_GOLD_AO2_PATH)

DEFAULT_PARTITION_PATH = f"{VOLUME_ROOT}/gold/ao2_profitability_chronological_partitions"
AO2_PARTITION_PATH = os.getenv(
    "DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
    DEFAULT_PARTITION_PATH,
)

JOIN_KEY_COLUMNS = ("Order_Id", "Order_Item_Id", "order_date_DateOrders")
ORDERING_COLUMNS = ("order_date_DateOrders", "Order_Id", "Order_Item_Id")
TARGET_COLUMN = "Order_Profit_Per_Order"
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
        if (candidate / "data" / "references" / "chronological_split_policy.csv").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()
SUMMARY_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_CHRONOLOGICAL_PARTITION_SUMMARY_PATH",
        str(REPO_ROOT / "data" / "references" / "ao2_chronological_partition_summary.csv"),
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
        raise AssertionError(
            f"{table_name} Delta output does not exist or is unreadable: {path}"
        ) from exc


def assert_required_columns_exist(partitioned_df: DataFrame) -> None:
    """Validate that required partition columns exist."""
    missing_columns = sorted(
        column_name
        for column_name in REQUIRED_PARTITION_COLUMNS
        if column_name not in partitioned_df.columns
    )
    assert not missing_columns, f"Missing AO2 partition columns: {missing_columns}"


def assert_gold_columns_preserved(gold_df: DataFrame, partitioned_df: DataFrame) -> None:
    """Validate partition output contains AO2 Gold rows plus only split metadata."""
    missing_gold_columns = sorted(
        column_name for column_name in gold_df.columns if column_name not in partitioned_df.columns
    )
    assert not missing_gold_columns, (
        f"AO2 partition output is missing AO2 Gold columns: {missing_gold_columns}"
    )

    unexpected_added_columns = sorted(
        set(partitioned_df.columns).difference(gold_df.columns).difference(ALLOWED_ADDED_COLUMNS)
    )
    assert not unexpected_added_columns, (
        "AO2 partition output contains unexpected helper columns. "
        f"Only {sorted(ALLOWED_ADDED_COLUMNS)} may be added. "
        f"Found: {unexpected_added_columns}"
    )


def assert_row_count_matches(gold_df: DataFrame, partitioned_df: DataFrame) -> int:
    """Validate partition output row count equals AO2 Gold row count."""
    gold_count = gold_df.count()
    partition_count = partitioned_df.count()
    assert partition_count == gold_count, (
        f"AO2 partition row count must equal AO2 Gold. "
        f"Gold: {gold_count}; partitioned: {partition_count}."
    )
    assert gold_count > 0, "AO2 Gold is empty; chronological partitions cannot be valid."
    return gold_count


def assert_unique_keys(df: DataFrame, table_name: str) -> None:
    """Validate one row per AO2 order item key."""
    row_count = df.count()
    distinct_key_count = df.select(*JOIN_KEY_COLUMNS).distinct().count()
    assert row_count == distinct_key_count, (
        f"{table_name} contains duplicate keys. "
        f"Rows: {row_count}; distinct keys: {distinct_key_count}."
    )


def assert_keys_match_gold(gold_df: DataFrame, partitioned_df: DataFrame) -> None:
    """Validate no AO2 Gold keys were lost or duplicated in partition output."""
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
        "AO2 partition keys do not exactly match AO2 Gold keys. "
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
        f"Invalid AO2 partition labels. Expected {sorted(VALID_PARTITION_LABELS)}, "
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
    assert invalid_development_rows == 0, (
        f"Development rows found after boundary {boundary}: {invalid_development_rows}"
    )
    assert invalid_test_rows == 0, (
        f"Test rows found at or before boundary {boundary}: {invalid_test_rows}"
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


def assert_target_complete(partitioned_df: DataFrame) -> None:
    """Validate the AO2 target remains complete in each partition."""
    invalid_target_count = partitioned_df.filter(col(TARGET_COLUMN).isNull()).count()
    assert invalid_target_count == 0, (
        f"AO2 target must be complete in every partition. Invalid rows: {invalid_target_count}."
    )


def print_partition_report(
    partitioned_df: DataFrame,
    total_rows: int,
    boundary: int,
) -> None:
    """Print a concise partition report for validation logs."""
    print("\nAO2 chronological partition validation summary:")
    print(f"- AO2 Gold rows: {total_rows:,}")
    print(f"- Development boundary row number: {boundary:,}")
    print(f"- Split formula: row_number <= floor(total_rows * 0.80)")
    print(f"- Ordering columns: {'; '.join(ORDERING_COLUMNS)}")
    print(f"- Partition output path: {AO2_PARTITION_PATH}")

    rows = (
        partitioned_df.groupBy(PARTITION_COLUMN)
        .agg(
            spark_count("*").alias("row_count"),
            spark_min(col("order_date_DateOrders")).alias("min_date"),
            spark_max(col("order_date_DateOrders")).alias("max_date"),
            spark_min(col(TARGET_COLUMN)).alias("target_min"),
            spark_max(col(TARGET_COLUMN)).alias("target_max"),
            spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias("target_missing"),
            spark_min(col(ROW_NUMBER_COLUMN)).alias("min_row_number"),
            spark_max(col(ROW_NUMBER_COLUMN)).alias("max_row_number"),
        )
        .collect()
    )
    for row in sorted(
        rows,
        key=lambda value: {DEVELOPMENT_LABEL: 1, TEST_LABEL: 2}.get(value[PARTITION_COLUMN], 99),
    ):
        print(
            "- "
            f"{row[PARTITION_COLUMN]}: rows={row['row_count']:,}, "
            f"dates={row['min_date']} to {row['max_date']}, "
            f"row_numbers={row['min_row_number']:,} to {row['max_row_number']:,}, "
            f"target_min={row['target_min']}, target_max={row['target_max']}, "
            f"target_missing={row['target_missing']:,}"
        )

    if SUMMARY_CSV_PATH.exists():
        print(f"- Summary CSV found: {SUMMARY_CSV_PATH}")
    else:
        print(
            "- Summary CSV not found locally; run the partition creation script "
            f"to generate it at {SUMMARY_CSV_PATH}."
        )


def run_validation() -> None:
    """Run all AO2 chronological partition validations."""
    spark = get_spark_session()
    gold_df = read_delta_or_fail(spark, GOLD_AO2_PATH, "AO2 Gold")
    partitioned_df = read_delta_or_fail(
        spark,
        AO2_PARTITION_PATH,
        "AO2 chronological partition",
    )

    assert_required_columns_exist(partitioned_df)
    assert_gold_columns_preserved(gold_df, partitioned_df)
    total_rows = assert_row_count_matches(gold_df, partitioned_df)
    assert_unique_keys(gold_df, "AO2 Gold")
    assert_unique_keys(partitioned_df, "AO2 chronological partitions")
    assert_keys_match_gold(gold_df, partitioned_df)
    assert_valid_partition_labels(partitioned_df)
    boundary = assert_boundary_counts(partitioned_df, total_rows)
    assert_row_numbers_are_complete(partitioned_df, total_rows)
    assert_row_number_boundary_assignment(partitioned_df, boundary)
    assert_chronological_ordering_monotonic(partitioned_df)
    assert_test_range_follows_development(partitioned_df)
    assert_target_complete(partitioned_df)

    print_partition_report(partitioned_df, total_rows, boundary)
    print("\nAO2 chronological partition validation passed.")


if __name__ == "__main__":
    run_validation()
