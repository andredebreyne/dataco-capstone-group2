"""Build the leakage-safe AO2 Gold analytical table.

This job creates the first model-ready Gold table for AO2 profitability
prediction. It joins the approved Silver and feature-engineering outputs,
selects conservative decision-time predictors, keeps the AO2 target separate,
and writes a Delta table for downstream chronological split and modeling.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, sum as spark_sum, when
from pyspark.sql.types import DoubleType, IntegerType, StringType, TimestampType

from src.data_engineering.clean_silver import SILVER_OUTPUT_PATH
from src.data_engineering.engineer_customer_regional_features import (
    CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH,
)
from src.data_engineering.engineer_order_time_features import (
    ORDER_TIME_FEATURE_OUTPUT_PATH,
)
from src.data_engineering.engineer_shipping_product_features import (
    SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

GOLD_AO2_OUTPUT_PATH = os.getenv(
    "DATACO_GOLD_AO2_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao2_profitability_analytical_table",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")
EXPECTED_SILVER_ROWS = 180_519
EXPECTED_AO2_GOLD_ROWS = 180_519

JOIN_KEY_COLUMNS = ("Order_Id", "Order_Item_Id", "order_date_DateOrders")

LINEAGE_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
)

TARGET_COLUMNS = ("Order_Profit_Per_Order",)

SILVER_PREDICTOR_COLUMNS = ("Type",)

ORDER_TIME_PREDICTOR_COLUMNS = (
    "order_year",
    "order_quarter",
    "order_month",
    "order_week_of_year",
    "order_day_of_month",
    "order_day_of_week",
    "order_hour",
    "order_is_weekend",
    "order_season",
)

SHIPPING_PRODUCT_PREDICTOR_COLUMNS = (
    "scheduled_shipping_days",
    "shipping_speed_tier",
    "shipping_mode_normalized",
    "is_same_day_or_next_day_shipping",
    "is_standard_shipping",
    "product_category_key",
    "product_department_key",
    "item_unit_price",
    "item_discount_rate",
    "order_item_quantity",
)

CUSTOMER_REGIONAL_PREDICTOR_COLUMNS = (
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

PREDICTOR_COLUMNS = (
    SILVER_PREDICTOR_COLUMNS
    + ORDER_TIME_PREDICTOR_COLUMNS
    + SHIPPING_PRODUCT_PREDICTOR_COLUMNS
    + CUSTOMER_REGIONAL_PREDICTOR_COLUMNS
)

AO3_SUPPORT_COLUMNS = ("ao3_order_value",)
TECHNICAL_COLUMNS = ("_gold_ao2_processed_timestamp",)

GOLD_AO2_OUTPUT_COLUMNS = (
    LINEAGE_COLUMNS
    + TARGET_COLUMNS
    + PREDICTOR_COLUMNS
    + AO3_SUPPORT_COLUMNS
    + TECHNICAL_COLUMNS
)

SILVER_REQUIRED_SUPPORT_COLUMNS = ("Order_Item_Total",)

FORBIDDEN_AO2_OUTPUT_COLUMNS = (
    "Delivery_Status",
    "Days_for_shipping_real",
    "shipping_date_DateOrders",
    "Order_Status",
    "Benefit_per_order",
    "Order_Item_Profit_Ratio",
    "Sales",
    "Sales_per_customer",
    "Order_Item_Total",
    "Product_Price",
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
    "item_discount_amount",
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

EXPECTED_GOLD_TYPES = {
    "Order_Id": IntegerType,
    "Order_Item_Id": IntegerType,
    "order_date_DateOrders": TimestampType,
    "Order_Profit_Per_Order": DoubleType,
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
    "item_unit_price": DoubleType,
    "item_discount_rate": DoubleType,
    "order_item_quantity": IntegerType,
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
    "ao3_order_value": DoubleType,
    "_gold_ao2_processed_timestamp": TimestampType,
}

REQUIRED_NON_NULL_COLUMNS = (
    LINEAGE_COLUMNS
    + TARGET_COLUMNS
    + ORDER_TIME_PREDICTOR_COLUMNS
    + SHIPPING_PRODUCT_PREDICTOR_COLUMNS
    + CUSTOMER_REGIONAL_PREDICTOR_COLUMNS
    + AO3_SUPPORT_COLUMNS
)


@dataclass(frozen=True)
class GoldAO2Config:
    """Configuration for the AO2 Gold analytical table job."""

    silver_input_path: str = SILVER_OUTPUT_PATH
    order_time_feature_input_path: str = ORDER_TIME_FEATURE_OUTPUT_PATH
    shipping_product_feature_input_path: str = SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH
    customer_regional_feature_input_path: str = CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH
    gold_output_path: str = GOLD_AO2_OUTPUT_PATH
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"
    expected_silver_rows: int = EXPECTED_SILVER_ROWS
    expected_gold_rows: int = EXPECTED_AO2_GOLD_ROWS


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.gold_ao2")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_paths(config: GoldAO2Config) -> None:
    """Validate that Gold job paths use Unity Catalog Volumes."""
    configured_paths = {
        "silver_input_path": config.silver_input_path,
        "order_time_feature_input_path": config.order_time_feature_input_path,
        "shipping_product_feature_input_path": config.shipping_product_feature_input_path,
        "customer_regional_feature_input_path": config.customer_regional_feature_input_path,
        "gold_output_path": config.gold_output_path,
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


def read_delta(spark: SparkSession, path: str, config: GoldAO2Config) -> DataFrame:
    """Read a Delta dataset from a configured path."""
    return spark.read.format(config.read_format).load(path)


def assert_required_columns(df: DataFrame, required_columns: tuple[str, ...], name: str) -> None:
    """Validate that a DataFrame contains the required columns."""
    missing_columns = sorted(
        column_name for column_name in required_columns if column_name not in df.columns
    )
    if missing_columns:
        raise ValueError(f"Missing required {name} columns: {missing_columns}")


def assert_unique_keys(df: DataFrame, key_columns: tuple[str, ...], name: str) -> None:
    """Validate that the configured key columns are unique in a DataFrame."""
    row_count = df.count()
    distinct_key_count = df.select(*key_columns).distinct().count()
    if row_count != distinct_key_count:
        raise ValueError(
            f"{name} contains duplicate join keys. "
            f"Rows: {row_count}; distinct keys: {distinct_key_count}."
        )


def validate_input_contracts(
    silver_df: DataFrame,
    order_time_df: DataFrame,
    shipping_product_df: DataFrame,
    customer_regional_df: DataFrame,
    config: GoldAO2Config,
) -> None:
    """Validate row counts, keys, and required fields before joining."""
    silver_row_count = silver_df.count()
    if silver_row_count != config.expected_silver_rows:
        raise ValueError(
            f"Unexpected Silver row count. Expected {config.expected_silver_rows}, "
            f"found {silver_row_count}."
        )

    assert_required_columns(
        silver_df,
        JOIN_KEY_COLUMNS
        + TARGET_COLUMNS
        + SILVER_PREDICTOR_COLUMNS
        + SILVER_REQUIRED_SUPPORT_COLUMNS,
        "Silver",
    )
    assert_required_columns(
        order_time_df,
        JOIN_KEY_COLUMNS + ORDER_TIME_PREDICTOR_COLUMNS,
        "order-time feature",
    )
    assert_required_columns(
        shipping_product_df,
        JOIN_KEY_COLUMNS + SHIPPING_PRODUCT_PREDICTOR_COLUMNS,
        "shipping/product feature",
    )
    assert_required_columns(
        customer_regional_df,
        JOIN_KEY_COLUMNS + CUSTOMER_REGIONAL_PREDICTOR_COLUMNS,
        "customer/regional feature",
    )

    assert_unique_keys(silver_df, JOIN_KEY_COLUMNS, "Silver input")
    assert_unique_keys(order_time_df, JOIN_KEY_COLUMNS, "Order-time feature input")
    assert_unique_keys(shipping_product_df, JOIN_KEY_COLUMNS, "Shipping/product feature input")
    assert_unique_keys(customer_regional_df, JOIN_KEY_COLUMNS, "Customer/regional feature input")


def select_feature_columns(
    df: DataFrame,
    feature_columns: tuple[str, ...],
) -> DataFrame:
    """Select join keys and a feature subset from an upstream feature table."""
    return df.select(*(JOIN_KEY_COLUMNS + feature_columns))


def build_gold_ao2_dataframe(
    silver_df: DataFrame,
    order_time_df: DataFrame,
    shipping_product_df: DataFrame,
    customer_regional_df: DataFrame,
) -> DataFrame:
    """Build the AO2 Gold DataFrame from approved upstream inputs."""
    ao2_base_df = silver_df.select(
        *(LINEAGE_COLUMNS + TARGET_COLUMNS + SILVER_PREDICTOR_COLUMNS),
        col("Order_Item_Total").cast("double").alias("ao3_order_value"),
    )

    gold_df = (
        ao2_base_df.join(
            select_feature_columns(order_time_df, ORDER_TIME_PREDICTOR_COLUMNS),
            list(JOIN_KEY_COLUMNS),
            "inner",
        )
        .join(
            select_feature_columns(shipping_product_df, SHIPPING_PRODUCT_PREDICTOR_COLUMNS),
            list(JOIN_KEY_COLUMNS),
            "inner",
        )
        .join(
            select_feature_columns(customer_regional_df, CUSTOMER_REGIONAL_PREDICTOR_COLUMNS),
            list(JOIN_KEY_COLUMNS),
            "inner",
        )
        .withColumn("_gold_ao2_processed_timestamp", current_timestamp())
    )

    return gold_df.select(*GOLD_AO2_OUTPUT_COLUMNS)


def validate_gold_ao2_dataframe(df: DataFrame, config: GoldAO2Config) -> None:
    """Validate the AO2 Gold table contract before and after writing."""
    row_count = df.count()
    if row_count != config.expected_gold_rows:
        raise ValueError(
            f"Unexpected AO2 Gold row count. Expected {config.expected_gold_rows}, "
            f"found {row_count}."
        )

    unexpected_columns = sorted(
        column_name for column_name in df.columns if column_name not in GOLD_AO2_OUTPUT_COLUMNS
    )
    if unexpected_columns:
        raise ValueError(f"Unexpected AO2 Gold output columns: {unexpected_columns}")

    missing_columns = sorted(
        column_name for column_name in GOLD_AO2_OUTPUT_COLUMNS if column_name not in df.columns
    )
    if missing_columns:
        raise ValueError(f"Missing AO2 Gold output columns: {missing_columns}")

    forbidden_columns = sorted(
        column_name for column_name in FORBIDDEN_AO2_OUTPUT_COLUMNS if column_name in df.columns
    )
    if forbidden_columns:
        raise ValueError(
            "Forbidden AO2 leakage, duplicate, or deferred columns found in Gold: "
            f"{forbidden_columns}"
        )

    assert_unique_keys(df, JOIN_KEY_COLUMNS, "AO2 Gold output")

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
    if columns_with_nulls:
        raise ValueError(f"AO2 Gold required columns contain nulls: {columns_with_nulls}")

    nonpositive_order_value_count = df.filter(col("ao3_order_value") <= lit(0)).count()
    if nonpositive_order_value_count:
        raise ValueError(
            "AO3 support denominator ao3_order_value must be positive. "
            f"Invalid rows: {nonpositive_order_value_count}."
        )

    schema_by_name = {field.name: field.dataType for field in df.schema.fields}
    invalid_types = {}
    for column_name, expected_type_class in EXPECTED_GOLD_TYPES.items():
        data_type = schema_by_name.get(column_name)
        if data_type is not None and not isinstance(data_type, expected_type_class):
            invalid_types[column_name] = {
                "expected": expected_type_class.__name__,
                "found": data_type.simpleString(),
            }
    if invalid_types:
        raise ValueError(f"AO2 Gold schema type validation failed: {invalid_types}")


def write_delta(df: DataFrame, output_path: str, config: GoldAO2Config) -> None:
    """Write the AO2 Gold DataFrame as Delta."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def run_gold_ao2_build(config: GoldAO2Config, logger: logging.Logger) -> None:
    """Execute the AO2 Gold analytical table workflow."""
    spark = get_spark_session()

    logger.info("Starting DataCo AO2 Gold analytical table build.")
    logger.info("Silver input path: %s", config.silver_input_path)
    logger.info("Order-time feature input path: %s", config.order_time_feature_input_path)
    logger.info("Shipping/product feature input path: %s", config.shipping_product_feature_input_path)
    logger.info("Customer/regional feature input path: %s", config.customer_regional_feature_input_path)
    logger.info("AO2 Gold output path: %s", config.gold_output_path)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        silver_df = read_delta(spark, config.silver_input_path, config)
        order_time_df = read_delta(spark, config.order_time_feature_input_path, config)
        shipping_product_df = read_delta(
            spark,
            config.shipping_product_feature_input_path,
            config,
        )
        customer_regional_df = read_delta(
            spark,
            config.customer_regional_feature_input_path,
            config,
        )
        logger.info("Upstream Delta inputs loaded successfully.")

        validate_input_contracts(
            silver_df,
            order_time_df,
            shipping_product_df,
            customer_regional_df,
            config,
        )
        logger.info("Upstream input contracts validated successfully.")

        gold_df = build_gold_ao2_dataframe(
            silver_df,
            order_time_df,
            shipping_product_df,
            customer_regional_df,
        )
        logger.info("AO2 Gold DataFrame created successfully.")

        validate_gold_ao2_dataframe(gold_df, config)
        logger.info("AO2 Gold pre-write validation completed successfully.")

        write_delta(gold_df, config.gold_output_path, config)
        logger.info("AO2 Gold Delta write completed successfully.")

        written_df = read_delta(spark, config.gold_output_path, config)
        validate_gold_ao2_dataframe(written_df, config)
        logger.info("AO2 Gold post-write validation completed successfully.")
        logger.info("DataCo AO2 Gold analytical table build completed successfully.")

    except Exception:
        logger.exception("AO2 Gold analytical table build failed.")
        raise


def main() -> None:
    """Run the AO2 Gold analytical table build with default configuration."""
    logger = configure_logging()
    config = GoldAO2Config()
    run_gold_ao2_build(config, logger)


if __name__ == "__main__":
    main()
