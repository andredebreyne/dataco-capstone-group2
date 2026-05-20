"""AO1 Gold analytical table quality checks.

Run this script in Databricks after the AO1 Gold builder completes. The checks
verify the leakage-safe table contract required by downstream chronological
split and AO1 modeling tasks.
"""

from __future__ import annotations

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, sum as spark_sum, when
from pyspark.sql.types import IntegerType, StringType, TimestampType


DEFAULT_GOLD_AO1_PATH = (
    "/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_analytical_table"
)
GOLD_AO1_PATH = os.getenv("DATACO_GOLD_AO1_OUTPUT_PATH", DEFAULT_GOLD_AO1_PATH)

EXPECTED_ROW_COUNT = 172_765

JOIN_KEY_COLUMNS = ("Order_Id", "Order_Item_Id", "order_date_DateOrders")
TARGET_COLUMN = "Late_delivery_risk"

REQUIRED_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "Late_delivery_risk",
    "Type",
    "order_year",
    "order_quarter",
    "order_month",
    "order_week_of_year",
    "order_day_of_month",
    "order_day_of_week",
    "order_hour",
    "order_is_weekend",
    "order_season",
    "scheduled_shipping_days",
    "shipping_speed_tier",
    "shipping_mode_normalized",
    "is_same_day_or_next_day_shipping",
    "is_standard_shipping",
    "product_category_key",
    "product_department_key",
    "customer_segment_normalized",
    "customer_country_normalized",
    "customer_state_normalized",
    "customer_zipcode_available",
    "market_normalized",
    "order_country_normalized",
    "order_region_normalized",
    "order_state_normalized",
    "order_zipcode_available",
    "customer_order_country_match",
    "customer_order_state_match",
    "geo_coordinates_available",
    "_gold_ao1_processed_timestamp",
)

REQUIRED_NON_NULL_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "Late_delivery_risk",
    "order_year",
    "order_quarter",
    "order_month",
    "order_week_of_year",
    "order_day_of_month",
    "order_day_of_week",
    "order_hour",
    "order_is_weekend",
    "order_season",
    "scheduled_shipping_days",
    "shipping_speed_tier",
    "shipping_mode_normalized",
    "is_same_day_or_next_day_shipping",
    "is_standard_shipping",
    "product_category_key",
    "product_department_key",
    "customer_segment_normalized",
    "customer_country_normalized",
    "customer_state_normalized",
    "customer_zipcode_available",
    "market_normalized",
    "order_country_normalized",
    "order_region_normalized",
    "order_state_normalized",
    "order_zipcode_available",
    "customer_order_country_match",
    "customer_order_state_match",
    "geo_coordinates_available",
)

FORBIDDEN_AO1_COLUMNS = (
    "Delivery_Status",
    "Days_for_shipping_real",
    "shipping_date_DateOrders",
    "Order_Status",
    "Order_Profit_Per_Order",
    "Benefit_per_order",
    "Order_Item_Profit_Ratio",
    "Sales",
    "Sales_per_customer",
    "Order_Item_Total",
    "Product_Image",
    "Product_Description",
    "Customer_Email",
    "Customer_Fname",
    "Customer_Lname",
    "Customer_Password",
    "Customer_Street",
    "Customer_Id",
    "Order_Customer_Id",
    "Customer_City",
    "Order_City",
    "Customer_Zipcode",
    "Order_Zipcode",
    "Latitude",
    "Longitude",
    "Product_Card_Id",
    "Order_Item_Cardprod_Id",
    "Product_Category_Id",
    "Product_Name",
    "product_catalog_key",
    "product_name_normalized",
    "product_status_flag",
    "product_list_price",
    "item_unit_price",
    "item_discount_amount",
    "item_discount_rate",
    "item_gross_sales_estimate",
    "item_net_sales_amount",
    "item_discount_share_of_gross",
    "customer_city_normalized",
    "order_city_normalized",
    "customer_region_key",
    "order_region_key",
    "latitude_rounded",
    "longitude_rounded",
)

EXPECTED_COLUMN_TYPES = {
    "Order_Id": IntegerType,
    "Order_Item_Id": IntegerType,
    "order_date_DateOrders": TimestampType,
    "Late_delivery_risk": IntegerType,
    "Type": StringType,
    "order_year": IntegerType,
    "order_quarter": IntegerType,
    "order_month": IntegerType,
    "order_week_of_year": IntegerType,
    "order_day_of_month": IntegerType,
    "order_day_of_week": IntegerType,
    "order_hour": IntegerType,
    "order_is_weekend": IntegerType,
    "order_season": StringType,
    "scheduled_shipping_days": IntegerType,
    "shipping_speed_tier": StringType,
    "shipping_mode_normalized": StringType,
    "is_same_day_or_next_day_shipping": IntegerType,
    "is_standard_shipping": IntegerType,
    "product_category_key": StringType,
    "product_department_key": StringType,
    "customer_segment_normalized": StringType,
    "customer_country_normalized": StringType,
    "customer_state_normalized": StringType,
    "customer_zipcode_available": IntegerType,
    "market_normalized": StringType,
    "order_country_normalized": StringType,
    "order_region_normalized": StringType,
    "order_state_normalized": StringType,
    "order_zipcode_available": IntegerType,
    "customer_order_country_match": IntegerType,
    "customer_order_state_match": IntegerType,
    "geo_coordinates_available": IntegerType,
    "_gold_ao1_processed_timestamp": TimestampType,
}


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def read_gold_ao1_delta(spark: SparkSession) -> DataFrame:
    """Read the AO1 Gold Delta table from the configured project path."""
    return spark.read.format("delta").load(GOLD_AO1_PATH)


def assert_row_count(df: DataFrame) -> None:
    """Validate the AO1 Gold primary population row count."""
    actual_count = df.count()
    assert actual_count == EXPECTED_ROW_COUNT, (
        f"Unexpected AO1 Gold row count. Expected {EXPECTED_ROW_COUNT}, "
        f"found {actual_count}."
    )


def assert_required_columns_exist(df: DataFrame) -> None:
    """Validate the AO1 Gold schema includes required modeling columns."""
    missing_columns = sorted(
        column_name for column_name in REQUIRED_COLUMNS if column_name not in df.columns
    )
    assert not missing_columns, f"Missing AO1 Gold columns: {missing_columns}"


def assert_forbidden_columns_absent(df: DataFrame) -> None:
    """Validate that leakage and deferred fields are not present in AO1 Gold."""
    forbidden_columns = sorted(
        column_name for column_name in FORBIDDEN_AO1_COLUMNS if column_name in df.columns
    )
    assert not forbidden_columns, (
        f"Forbidden AO1 leakage or deferred columns found: {forbidden_columns}"
    )


def assert_required_columns_are_not_null(df: DataFrame) -> None:
    """Validate key, target, and required predictor completeness."""
    null_counts = df.select(
        [
            spark_sum(when(col(column_name).isNull(), 1).otherwise(0)).alias(column_name)
            for column_name in REQUIRED_NON_NULL_COLUMNS
        ]
    ).collect()[0].asDict()
    columns_with_nulls = {
        column_name: null_count
        for column_name, null_count in null_counts.items()
        if null_count != 0
    }

    assert not columns_with_nulls, (
        f"AO1 Gold required columns contain nulls: {columns_with_nulls}"
    )


def assert_unique_keys(df: DataFrame) -> None:
    """Validate that AO1 Gold keeps one row per order item."""
    row_count = df.count()
    distinct_key_count = df.select(*JOIN_KEY_COLUMNS).distinct().count()
    assert row_count == distinct_key_count, (
        "AO1 Gold contains duplicate keys. "
        f"Rows: {row_count}; distinct keys: {distinct_key_count}."
    )


def assert_target_contract(df: DataFrame) -> None:
    """Validate the AO1 target is binary and complete."""
    target_values = {
        row[TARGET_COLUMN]
        for row in df.select(TARGET_COLUMN).distinct().collect()
    }
    assert target_values.issubset({0, 1}), (
        f"AO1 target contains unexpected values: {sorted(target_values)}"
    )


def assert_expected_column_types(df: DataFrame) -> None:
    """Validate key AO1 Gold schema field types."""
    schema_by_name = {field.name: field.dataType for field in df.schema.fields}
    invalid_types = {}

    for column_name, expected_type_class in EXPECTED_COLUMN_TYPES.items():
        data_type = schema_by_name.get(column_name)
        if data_type is not None and not isinstance(data_type, expected_type_class):
            invalid_types[column_name] = {
                "expected": expected_type_class.__name__,
                "found": data_type.simpleString(),
            }

    assert not invalid_types, f"AO1 Gold schema type validation failed: {invalid_types}"


def run_gold_ao1_quality_tests() -> None:
    """Run all AO1 Gold table quality tests."""
    spark = get_spark_session()
    gold_df = read_gold_ao1_delta(spark)

    assert_row_count(gold_df)
    assert_required_columns_exist(gold_df)
    assert_forbidden_columns_absent(gold_df)
    assert_required_columns_are_not_null(gold_df)
    assert_unique_keys(gold_df)
    assert_target_contract(gold_df)
    assert_expected_column_types(gold_df)

    print("All AO1 Gold analytical table tests passed.")


if __name__ == "__main__":
    run_gold_ao1_quality_tests()
