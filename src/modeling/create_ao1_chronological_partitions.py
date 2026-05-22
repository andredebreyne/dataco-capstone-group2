"""Create deterministic AO1 chronological development/test partitions.

This job reads the leakage-safe AO1 Gold analytical table, applies the frozen
chronological split policy, and writes a partitioned Delta table for downstream
AO1 model-selection work. It does not train models or fit preprocessing.
"""

from __future__ import annotations

import csv
import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    count as spark_count,
    lit,
    max as spark_max,
    min as spark_min,
    row_number,
    sum as spark_sum,
    when,
)
from pyspark.sql.window import Window


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

GOLD_AO1_INPUT_PATH = os.getenv(
    "DATACO_GOLD_AO1_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao1_late_delivery_analytical_table",
)

AO1_PARTITION_OUTPUT_PATH = os.getenv(
    "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao1_late_delivery_chronological_partitions",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")

JOIN_KEY_COLUMNS = ("Order_Id", "Order_Item_Id", "order_date_DateOrders")
ORDERING_COLUMNS = ("order_date_DateOrders", "Order_Id", "Order_Item_Id")
TARGET_COLUMN = "Late_delivery_risk"
ROW_NUMBER_COLUMN = "chronological_row_number"
PARTITION_COLUMN = "split_partition"
DEVELOPMENT_LABEL = "development"
TEST_LABEL = "test"
DEVELOPMENT_RATIO = 0.80
BOUNDARY_FORMULA = "row_number <= floor(total_rows * 0.80)"
VALIDATION_SUBPARTITION_DECISION = (
    "deferred: no materialized validation subpartition is defined in the frozen policy"
)

REQUIRED_COLUMNS = JOIN_KEY_COLUMNS + (TARGET_COLUMN,)

POLICY_REQUIRED_VALUES = {
    "split_anchor_column": "order_date_DateOrders",
    "primary_ordering_columns": "order_date_DateOrders; Order_Id; Order_Item_Id",
    "development_ratio": "0.80",
    "test_ratio": "0.20",
    "boundary_row_formula": "row_number <= floor(total_rows * 0.80)",
    "development_partition_label": DEVELOPMENT_LABEL,
    "test_partition_label": TEST_LABEL,
    "shuffle_allowed": "false",
    "test_set_refit_allowed": "false",
    "ao1_split_population": "ao1_gold_primary_population",
    "policy_status": "frozen",
}

SUMMARY_COLUMNS = (
    "summary_level",
    "split_partition",
    "row_count",
    "percentage_of_total",
    "min_order_date_DateOrders",
    "max_order_date_DateOrders",
    "late_delivery_count",
    "non_late_count",
    "late_delivery_rate",
    "target_missing_count",
    "min_chronological_row_number",
    "max_chronological_row_number",
    "total_ao1_gold_rows",
    "development_boundary_row_number",
    "split_formula_used",
    "ordering_columns_used",
    "final_test_untouched",
    "validation_subpartition_decision",
    "source_ao1_gold_path",
    "partition_output_path",
    "policy_reference_document",
    "execution_timestamp_utc",
)


def resolve_repo_root() -> Path:
    """Resolve repository root for local summary and policy artifacts."""
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
DEFAULT_POLICY_CSV_PATH = REPO_ROOT / "data" / "references" / "chronological_split_policy.csv"
DEFAULT_SUMMARY_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_CHRONOLOGICAL_PARTITION_SUMMARY_PATH",
        str(REPO_ROOT / "data" / "references" / "ao1_chronological_partition_summary.csv"),
    )
)


@dataclass(frozen=True)
class AO1ChronologicalPartitionConfig:
    """Configuration for AO1 chronological partition creation."""

    gold_input_path: str = GOLD_AO1_INPUT_PATH
    partition_output_path: str = AO1_PARTITION_OUTPUT_PATH
    policy_csv_path: Path = DEFAULT_POLICY_CSV_PATH
    summary_csv_path: Path = DEFAULT_SUMMARY_CSV_PATH
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_chronological_partitions")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_volume_paths(config: AO1ChronologicalPartitionConfig) -> None:
    """Validate Delta paths use Unity Catalog Volumes, not public DBFS roots."""
    configured_paths = {
        "gold_input_path": config.gold_input_path,
        "partition_output_path": config.partition_output_path,
    }

    for field_name, path in configured_paths.items():
        if path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
            raise ValueError(
                f"{field_name} points to the disabled public DBFS root: {path}. "
                "Use Unity Catalog Volumes under /Volumes/workspace/default/raw_data/."
            )
        if not path.startswith("/Volumes/"):
            raise ValueError(
                f"{field_name} must use a Unity Catalog Volume path. Received: {path}"
            )


def read_policy_rows(policy_csv_path: Path) -> list[dict[str, str]]:
    """Read the frozen chronological split policy CSV."""
    if not policy_csv_path.exists():
        raise FileNotFoundError(f"Missing chronological split policy CSV: {policy_csv_path}")

    with policy_csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_frozen_policy(policy_csv_path: Path) -> None:
    """Validate the partition job is using the approved frozen policy values."""
    rows = read_policy_rows(policy_csv_path)
    rows_by_key = {row["policy_key"]: row for row in rows}

    missing_keys = sorted(set(POLICY_REQUIRED_VALUES).difference(rows_by_key))
    if missing_keys:
        raise ValueError(f"Frozen split policy is missing required keys: {missing_keys}")

    invalid_values = []
    for policy_key, expected_value in POLICY_REQUIRED_VALUES.items():
        actual_value = rows_by_key[policy_key]["policy_value"]
        if actual_value != expected_value:
            invalid_values.append((policy_key, expected_value, actual_value))

    if invalid_values:
        raise ValueError(f"Frozen split policy contradicts AO1 requirements: {invalid_values}")


def read_delta(spark: SparkSession, path: str, read_format: str) -> DataFrame:
    """Read a Delta dataset from a configured path."""
    return spark.read.format(read_format).load(path)


def assert_required_columns(df: DataFrame) -> None:
    """Validate the AO1 Gold table has columns required for splitting."""
    missing_columns = sorted(column for column in REQUIRED_COLUMNS if column not in df.columns)
    if missing_columns:
        raise ValueError(f"AO1 Gold table is missing split-required columns: {missing_columns}")


def assert_unique_keys(df: DataFrame, name: str) -> None:
    """Validate one row per AO1 order item key."""
    row_count = df.count()
    distinct_key_count = df.select(*JOIN_KEY_COLUMNS).distinct().count()
    if row_count != distinct_key_count:
        raise ValueError(
            f"{name} contains duplicate keys. Rows: {row_count}; "
            f"distinct keys: {distinct_key_count}."
        )


def assert_target_contract(df: DataFrame) -> None:
    """Validate the AO1 target is complete and binary before partitioning."""
    target_summary = df.select(
        spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias("missing_count")
    ).collect()[0]

    if target_summary["missing_count"] != 0:
        raise ValueError(
            f"AO1 target contains {target_summary['missing_count']} missing values."
        )

    target_values = {
        row[TARGET_COLUMN]
        for row in df.select(TARGET_COLUMN).distinct().collect()
    }
    if not target_values.issubset({0, 1}):
        raise ValueError(f"AO1 target contains unexpected values: {sorted(target_values)}")


def build_partitioned_dataframe(df: DataFrame) -> tuple[DataFrame, int, int]:
    """Assign deterministic 1-based row numbers and development/test labels."""
    total_rows = df.count()
    if total_rows == 0:
        raise ValueError("AO1 Gold table is empty; cannot create chronological partitions.")

    development_boundary = math.floor(total_rows * DEVELOPMENT_RATIO)
    ordering_window = Window.orderBy(*[col(column_name).asc() for column_name in ORDERING_COLUMNS])

    partitioned_df = (
        df.withColumn(ROW_NUMBER_COLUMN, row_number().over(ordering_window))
        .withColumn(
            PARTITION_COLUMN,
            when(col(ROW_NUMBER_COLUMN) <= lit(development_boundary), lit(DEVELOPMENT_LABEL))
            .otherwise(lit(TEST_LABEL)),
        )
    )

    return partitioned_df, total_rows, development_boundary


def write_delta(
    df: DataFrame,
    output_path: str,
    config: AO1ChronologicalPartitionConfig,
) -> None:
    """Write the partitioned AO1 DataFrame as Delta."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def format_summary_value(value: Any) -> str:
    """Return a stable CSV-friendly representation for summary values."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.10f}".rstrip("0").rstrip(".")
    return str(value)


def collect_summary_stats(
    df: DataFrame,
    grouping_column: str | None,
) -> list[dict[str, Any]]:
    """Collect partition or overall summary stats."""
    aggregations = [
        spark_count(lit(1)).alias("row_count"),
        spark_min(col("order_date_DateOrders")).alias("min_order_date_DateOrders"),
        spark_max(col("order_date_DateOrders")).alias("max_order_date_DateOrders"),
        spark_sum(when(col(TARGET_COLUMN) == 1, 1).otherwise(0)).alias("late_delivery_count"),
        spark_sum(when(col(TARGET_COLUMN) == 0, 1).otherwise(0)).alias("non_late_count"),
        spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias(
            "target_missing_count"
        ),
        spark_min(col(ROW_NUMBER_COLUMN)).alias("min_chronological_row_number"),
        spark_max(col(ROW_NUMBER_COLUMN)).alias("max_chronological_row_number"),
    ]

    if grouping_column is None:
        return [df.agg(*aggregations).collect()[0].asDict()]

    return [
        row.asDict()
        for row in df.groupBy(grouping_column).agg(*aggregations).collect()
    ]


def build_summary_rows(
    partitioned_df: DataFrame,
    total_rows: int,
    development_boundary: int,
    config: AO1ChronologicalPartitionConfig,
) -> list[dict[str, str]]:
    """Build overall and by-partition summary rows for reviewer documentation."""
    execution_timestamp = datetime.now(timezone.utc).isoformat()
    ordering_columns_used = "; ".join(ORDERING_COLUMNS)

    def enrich_summary_row(summary_level: str, split_partition: str, stats: dict[str, Any]) -> dict[str, str]:
        row_count = int(stats["row_count"])
        late_delivery_count = int(stats["late_delivery_count"])
        late_delivery_rate = (
            late_delivery_count / row_count if row_count else 0.0
        )
        percentage_of_total = row_count / total_rows if total_rows else 0.0

        values = {
            "summary_level": summary_level,
            "split_partition": split_partition,
            "row_count": row_count,
            "percentage_of_total": percentage_of_total,
            "min_order_date_DateOrders": stats["min_order_date_DateOrders"],
            "max_order_date_DateOrders": stats["max_order_date_DateOrders"],
            "late_delivery_count": late_delivery_count,
            "non_late_count": int(stats["non_late_count"]),
            "late_delivery_rate": late_delivery_rate,
            "target_missing_count": int(stats["target_missing_count"]),
            "min_chronological_row_number": stats["min_chronological_row_number"],
            "max_chronological_row_number": stats["max_chronological_row_number"],
            "total_ao1_gold_rows": total_rows,
            "development_boundary_row_number": development_boundary,
            "split_formula_used": BOUNDARY_FORMULA,
            "ordering_columns_used": ordering_columns_used,
            "final_test_untouched": "true",
            "validation_subpartition_decision": VALIDATION_SUBPARTITION_DECISION,
            "source_ao1_gold_path": config.gold_input_path,
            "partition_output_path": config.partition_output_path,
            "policy_reference_document": "docs/chronological_split_policy.md",
            "execution_timestamp_utc": execution_timestamp,
        }
        return {column_name: format_summary_value(values[column_name]) for column_name in SUMMARY_COLUMNS}

    overall_stats = collect_summary_stats(partitioned_df, None)[0]
    summary_rows = [enrich_summary_row("overall", "overall", overall_stats)]

    partition_stats = collect_summary_stats(partitioned_df, PARTITION_COLUMN)
    sort_order = {DEVELOPMENT_LABEL: 1, TEST_LABEL: 2}
    for stats in sorted(
        partition_stats,
        key=lambda row: sort_order.get(row[PARTITION_COLUMN], 99),
    ):
        summary_rows.append(
            enrich_summary_row("partition", stats[PARTITION_COLUMN], stats)
        )

    return summary_rows


def write_summary_csv(summary_rows: list[dict[str, str]], summary_csv_path: Path) -> None:
    """Write the small AO1 partition summary CSV artifact."""
    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)


def validate_written_partitions(
    spark: SparkSession,
    source_df: DataFrame,
    total_rows: int,
    development_boundary: int,
    config: AO1ChronologicalPartitionConfig,
) -> None:
    """Validate the persisted partition table before reporting success."""
    written_df = read_delta(spark, config.partition_output_path, config.read_format)

    if written_df.count() != total_rows:
        raise ValueError(
            f"Partition output row count does not match AO1 Gold. "
            f"Expected {total_rows}, found {written_df.count()}."
        )

    assert_unique_keys(written_df, "AO1 chronological partition output")

    source_keys = source_df.select(*JOIN_KEY_COLUMNS)
    output_keys = written_df.select(*JOIN_KEY_COLUMNS)
    missing_from_output = source_keys.join(output_keys, list(JOIN_KEY_COLUMNS), "left_anti").count()
    unexpected_in_output = output_keys.join(source_keys, list(JOIN_KEY_COLUMNS), "left_anti").count()
    if missing_from_output or unexpected_in_output:
        raise ValueError(
            "AO1 chronological partitions do not match AO1 Gold keys. "
            f"Missing from output: {missing_from_output}; "
            f"unexpected in output: {unexpected_in_output}."
        )

    development_count = written_df.filter(col(PARTITION_COLUMN) == DEVELOPMENT_LABEL).count()
    test_count = written_df.filter(col(PARTITION_COLUMN) == TEST_LABEL).count()
    if development_count != development_boundary:
        raise ValueError(
            f"Development row count must equal boundary {development_boundary}; "
            f"found {development_count}."
        )
    if test_count != total_rows - development_boundary:
        raise ValueError(
            f"Test row count must equal {total_rows - development_boundary}; "
            f"found {test_count}."
        )


def run_ao1_chronological_partitioning(
    config: AO1ChronologicalPartitionConfig,
    logger: logging.Logger,
) -> None:
    """Execute AO1 chronological partition creation and summary generation."""
    spark = get_spark_session()

    logger.info("Starting AO1 chronological partition creation.")
    logger.info("AO1 Gold input path: %s", config.gold_input_path)
    logger.info("AO1 partition output path: %s", config.partition_output_path)
    logger.info("Policy CSV path: %s", config.policy_csv_path)
    logger.info("Summary CSV path: %s", config.summary_csv_path)

    try:
        validate_volume_paths(config)
        validate_frozen_policy(config.policy_csv_path)
        logger.info("Frozen chronological split policy validation completed.")

        gold_df = read_delta(spark, config.gold_input_path, config.read_format)
        assert_required_columns(gold_df)
        assert_unique_keys(gold_df, "AO1 Gold input")
        assert_target_contract(gold_df)
        logger.info("AO1 Gold input contract validation completed.")

        partitioned_df, total_rows, development_boundary = build_partitioned_dataframe(gold_df)
        logger.info("AO1 Gold row count: %s", total_rows)
        logger.info("Development boundary row number: %s", development_boundary)
        logger.info("Test row count: %s", total_rows - development_boundary)

        write_delta(partitioned_df, config.partition_output_path, config)
        logger.info("AO1 chronological partition Delta write completed.")

        validate_written_partitions(
            spark,
            gold_df,
            total_rows,
            development_boundary,
            config,
        )
        logger.info("AO1 chronological partition post-write validation completed.")

        written_df = read_delta(spark, config.partition_output_path, config.read_format)
        summary_rows = build_summary_rows(
            written_df,
            total_rows,
            development_boundary,
            config,
        )
        write_summary_csv(summary_rows, config.summary_csv_path)
        logger.info("AO1 partition summary CSV written: %s", config.summary_csv_path)
        logger.info("AO1 chronological partition creation completed successfully.")

    except Exception:
        logger.exception("AO1 chronological partition creation failed.")
        raise


def main() -> None:
    """Run AO1 chronological partition creation with default configuration."""
    run_ao1_chronological_partitioning(
        AO1ChronologicalPartitionConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
