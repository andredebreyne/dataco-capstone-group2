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
SILVER_PATH = os.getenv("DATACO_SILVER_OUTPUT_PATH", DEFAULT_SILVER_PATH)
EXPECTED_ROW_COUNT = 180_519

REQUIRED_NON_NULL_COLUMNS = (
    "Order_Id",
    "order_date_DateOrders",
    "Sales",
    "Late_delivery_risk",
)


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def read_silver_delta(spark: SparkSession, silver_path: str = SILVER_PATH) -> DataFrame:
    """Read the Silver Delta dataset from the configured project path."""
    return spark.read.format("delta").load(silver_path)


def assert_row_count(df: DataFrame, expected_count: int = EXPECTED_ROW_COUNT) -> None:
    """Validate the Silver dataset row count."""
    actual_count = df.count()

    assert actual_count == expected_count, (
        f"Unexpected Silver row count. Expected {expected_count}, "
        f"found {actual_count}."
    )


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


def assert_order_date_is_timestamp(df: DataFrame) -> None:
    """Validate the timestamp contract for the order date field."""
    order_date_type = df.schema["order_date_DateOrders"].dataType.simpleString()

    assert order_date_type == "timestamp", (
        "order_date_DateOrders must be timestamp. "
        f"Found {order_date_type}."
    )


def run_silver_quality_tests() -> None:
    """Run all Silver quality tests."""
    spark = get_spark_session()
    silver_df = read_silver_delta(spark)

    assert_row_count(silver_df)
    assert_required_columns_are_not_null(silver_df)
    assert_order_date_is_timestamp(silver_df)

    print("All Silver quality tests passed.")


if __name__ == "__main__":
    run_silver_quality_tests()
