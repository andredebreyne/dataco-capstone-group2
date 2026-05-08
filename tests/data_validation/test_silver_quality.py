"""Silver-layer quality checks for the DataCo dataset.

This script is intended to run in Databricks after the Bronze ingestion and
Silver cleaning jobs have completed. It validates the Silver Delta contract
required by downstream feature engineering, AO1 late-delivery modeling, and
AO2 profitability modeling.
"""

from __future__ import annotations

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, sum as spark_sum, when


DEFAULT_SILVER_PATH = "/Volumes/workspace/default/raw_data/silver/dataco_orders_silver"
DEFAULT_QUALITY_REPORT_PATH = (
    "/Volumes/workspace/default/raw_data/silver/dataco_orders_silver_quality_report"
)
SILVER_PATH = os.getenv("DATACO_SILVER_OUTPUT_PATH", DEFAULT_SILVER_PATH)
QUALITY_REPORT_PATH = os.getenv(
    "DATACO_SILVER_QUALITY_REPORT_OUTPUT_PATH",
    DEFAULT_QUALITY_REPORT_PATH,
)
EXPECTED_ROW_COUNT = 180_519

REQUIRED_COLUMNS = (
    "Order_Id",
    "order_date_DateOrders",
    "shipping_date_DateOrders",
    "Sales",
    "Late_delivery_risk",
    "Benefit_per_order",
    "Order_Profit_Per_Order",
    "_ingest_timestamp",
    "_source_file",
    "_silver_processed_timestamp",
)

REQUIRED_NON_NULL_COLUMNS = (
    "Order_Id",
    "order_date_DateOrders",
    "Sales",
    "Late_delivery_risk",
)

EXPECTED_COLUMN_TYPES = {
    "Order_Id": "int",
    "order_date_DateOrders": "timestamp",
    "shipping_date_DateOrders": "timestamp",
    "Sales": "double",
    "Late_delivery_risk": "int",
    "Benefit_per_order": "double",
    "Order_Profit_Per_Order": "double",
    "_ingest_timestamp": "timestamp",
    "_source_file": "string",
    "_silver_processed_timestamp": "timestamp",
}

EXPECTED_QUALITY_METRICS = (
    "bronze_row_count",
    "silver_row_count",
    "dropped_row_count",
    "expected_bronze_rows",
    "silver_column_count",
)


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def read_silver_delta(spark: SparkSession, silver_path: str = SILVER_PATH) -> DataFrame:
    """Read the Silver Delta dataset from the configured project path."""
    return spark.read.format("delta").load(silver_path)


def read_quality_report_delta(
    spark: SparkSession,
    quality_report_path: str = QUALITY_REPORT_PATH,
) -> DataFrame:
    """Read the Silver quality-report Delta dataset."""
    return spark.read.format("delta").load(quality_report_path)


def assert_row_count(df: DataFrame, expected_count: int = EXPECTED_ROW_COUNT) -> None:
    """Validate the Silver dataset row count."""
    actual_count = df.count()

    assert actual_count == expected_count, (
        f"Unexpected Silver row count. Expected {expected_count}, "
        f"found {actual_count}."
    )


def assert_required_columns_exist(df: DataFrame) -> None:
    """Validate that the Silver dataset contains the required contract columns."""
    missing_columns = sorted(
        column_name for column_name in REQUIRED_COLUMNS if column_name not in df.columns
    )

    assert not missing_columns, f"Missing required Silver columns: {missing_columns}"


def count_nulls(df: DataFrame, column_name: str) -> int:
    """Count null values in a Silver column."""
    return df.select(
        spark_sum(when(col(column_name).isNull(), 1).otherwise(0)).alias("null_count")
    ).collect()[0]["null_count"]


def assert_required_columns_are_not_null(df: DataFrame) -> None:
    """Validate that critical modeling fields do not contain nulls."""
    for column_name in REQUIRED_NON_NULL_COLUMNS:
        null_count = count_nulls(df, column_name)
        assert null_count == 0, (
            f"Column {column_name} contains {null_count} null values."
        )


def assert_expected_column_types(df: DataFrame) -> None:
    """Validate key Silver schema fields used by downstream AO work."""
    actual_types = {
        field.name: field.dataType.simpleString()
        for field in df.schema.fields
    }

    type_mismatches = sorted(
        (
            column_name,
            expected_type,
            actual_types.get(column_name),
        )
        for column_name, expected_type in EXPECTED_COLUMN_TYPES.items()
        if actual_types.get(column_name) != expected_type
    )

    assert not type_mismatches, (
        "Silver schema type validation failed. "
        f"Mismatches: {type_mismatches}"
    )


def assert_quality_report_contract(quality_report_df: DataFrame) -> None:
    """Validate that the Silver quality report contains expected audit metrics."""
    required_columns = {"metric_name", "metric_value", "metric_details"}
    missing_columns = sorted(required_columns.difference(quality_report_df.columns))

    assert not missing_columns, (
        f"Missing required Silver quality-report columns: {missing_columns}"
    )

    actual_metrics = {
        row["metric_name"]
        for row in quality_report_df.select("metric_name").distinct().collect()
    }
    missing_metrics = sorted(
        metric_name
        for metric_name in EXPECTED_QUALITY_METRICS
        if metric_name not in actual_metrics
    )

    assert not missing_metrics, (
        f"Missing required Silver quality-report metrics: {missing_metrics}"
    )


def run_silver_quality_tests() -> None:
    """Run all Silver quality tests."""
    spark = get_spark_session()
    silver_df = read_silver_delta(spark)
    quality_report_df = read_quality_report_delta(spark)

    assert_row_count(silver_df)
    assert_required_columns_exist(silver_df)
    assert_required_columns_are_not_null(silver_df)
    assert_expected_column_types(silver_df)
    assert_quality_report_contract(quality_report_df)

    print("All Silver quality tests passed.")


if __name__ == "__main__":
    run_silver_quality_tests()
