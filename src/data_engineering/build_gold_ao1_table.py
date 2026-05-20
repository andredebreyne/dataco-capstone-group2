"""Build the leakage-safe AO1 Gold analytical table.

This job creates the first model-ready Gold table for AO1 late-delivery risk.
It joins the approved Silver and feature-engineering outputs, applies the
primary AO1 population rule, selects only approved decision-time predictors,
and writes a Delta table for downstream chronological split and modeling.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, sum as spark_sum, when
from pyspark.sql.types import IntegerType, StringType, TimestampType

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

GOLD_AO1_OUTPUT_PATH = os.getenv(
    "DATACO_GOLD_AO1_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao1_late_delivery_analytical_table",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")
EXPECTED_SILVER_ROWS = 180_519
EXPECTED_PRIMARY_AO1_ROWS = 172_765

JOIN_KEY_COLUMNS = ("Order_Id", "Order_Item_Id", "order_date_DateOrders")

LINEAGE_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
)

TARGET_COLUMNS = ("Late_delivery_risk",)

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

TECHNICAL_COLUMNS = ("_gold_ao1_processed_timestamp",)

GOLD_AO1_OUTPUT_COLUMNS = (
    LINEAGE_COLUMNS
    + TARGET_COLUMNS
    + PREDICTOR_COLUMNS
    + TECHNICAL_COLUMNS
)

POPULATION_FILTER_COLUMNS = ("Delivery_Status", "Order_Status")

FORBIDDEN_AO1_OUTPUT_COLUMNS = (
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

EXPECTED_GOLD_TYPES = {
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

REQUIRED_NON_NULL_COLUMNS = (
    LINEAGE_COLUMNS
    + TARGET_COLUMNS
    + ORDER_TIME_PREDICTOR_COLUMNS
    + SHIPPING_PRODUCT_PREDICTOR_COLUMNS
    + CUSTOMER_REGIONAL_PREDICTOR_COLUMNS
)


@dataclass(frozen=True)
class GoldAO1Config:
    """Configuration for the AO1 Gold analytical table job."""

    silver_input_path: str = SILVER_OUTPUT_PATH
    order_time_feature_input_path: str = ORDER_TIME_FEATURE_OUTPUT_PATH
    shipping_product_feature_input_path: str = SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH
    customer_regional_feature_input_path: str = CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH
    gold_output_path: str = GOLD_AO1_OUTPUT_PATH
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"
    expected_silver_rows: int = EXPECTED_SILVER_ROWS
    expected_gold_rows: int = EXPECTED_PRIMARY_AO1_ROWS


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.gold_ao1")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_paths(config: GoldAO1Config) -> None:
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


def read_delta(spark: SparkSession, path: str, config: GoldAO1Config) -> DataFrame:
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
    config: GoldAO1Config,
) -> None:
    """Validate row counts, keys, and required fields before joining."""
    if silver_df.count() != config.expected_silver_rows:
        raise ValueError(
            f"Unexpected Silver row count. Expected {config.expected_silver_rows}, "
            f"found {silver_df.count()}."
        )

    assert_required_columns(
        silver_df,
        JOIN_KEY_COLUMNS + TARGET_COLUMNS + SILVER_PREDICTOR_COLUMNS + POPULATION_FILTER_COLUMNS,
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


def filter_primary_ao1_population(silver_df: DataFrame) -> DataFrame:
    """Apply the approved primary AO1 population rule."""
    return silver_df.filter(
        (col("Delivery_Status") != lit("Shipping canceled"))
        & (~col("Order_Status").isin("CANCELED", "SUSPECTED_FRAUD"))
    )


def select_feature_columns(
    df: DataFrame,
    feature_columns: tuple[str, ...],
) -> DataFrame:
    """Select join keys and a feature subset from an upstream feature table."""
    return df.select(*(JOIN_KEY_COLUMNS + feature_columns))


def build_gold_ao1_dataframe(
    silver_df: DataFrame,
    order_time_df: DataFrame,
    shipping_product_df: DataFrame,
    customer_regional_df: DataFrame,
) -> DataFrame:
    """Build the AO1 Gold DataFrame from approved upstream inputs."""
    ao1_base_df = filter_primary_ao1_population(silver_df).select(
        *(LINEAGE_COLUMNS + TARGET_COLUMNS + SILVER_PREDICTOR_COLUMNS)
    )

    gold_df = (
        ao1_base_df.join(
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
        .withColumn("_gold_ao1_processed_timestamp", current_timestamp())
    )

    return gold_df.select(*GOLD_AO1_OUTPUT_COLUMNS)


def validate_gold_ao1_dataframe(df: DataFrame, config: GoldAO1Config) -> None:
    """Validate the AO1 Gold table contract before and after writing."""
    row_count = df.count()
    if row_count != config.expected_gold_rows:
        raise ValueError(
            f"Unexpected AO1 Gold row count. Expected {config.expected_gold_rows}, "
            f"found {row_count}."
        )

    unexpected_columns = sorted(
        column_name for column_name in df.columns if column_name not in GOLD_AO1_OUTPUT_COLUMNS
    )
    if unexpected_columns:
        raise ValueError(f"Unexpected AO1 Gold output columns: {unexpected_columns}")

    missing_columns = sorted(
        column_name for column_name in GOLD_AO1_OUTPUT_COLUMNS if column_name not in df.columns
    )
    if missing_columns:
        raise ValueError(f"Missing AO1 Gold output columns: {missing_columns}")

    forbidden_columns = sorted(
        column_name for column_name in FORBIDDEN_AO1_OUTPUT_COLUMNS if column_name in df.columns
    )
    if forbidden_columns:
        raise ValueError(f"Forbidden AO1 leakage columns found in Gold: {forbidden_columns}")

    assert_unique_keys(df, JOIN_KEY_COLUMNS, "AO1 Gold output")

    target_values = {
        row["Late_delivery_risk"]
        for row in df.select("Late_delivery_risk").distinct().collect()
    }
    if not target_values.issubset({0, 1}):
        raise ValueError(f"AO1 target contains unexpected values: {sorted(target_values)}")

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
        raise ValueError(f"AO1 Gold required columns contain nulls: {columns_with_nulls}")

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
        raise ValueError(f"AO1 Gold schema type validation failed: {invalid_types}")


def write_delta(df: DataFrame, output_path: str, config: GoldAO1Config) -> None:
    """Write the AO1 Gold DataFrame as Delta."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def run_gold_ao1_build(config: GoldAO1Config, logger: logging.Logger) -> None:
    """Execute the AO1 Gold analytical table workflow."""
    spark = get_spark_session()

    logger.info("Starting DataCo AO1 Gold analytical table build.")
    logger.info("Silver input path: %s", config.silver_input_path)
    logger.info("Order-time feature input path: %s", config.order_time_feature_input_path)
    logger.info("Shipping/product feature input path: %s", config.shipping_product_feature_input_path)
    logger.info("Customer/regional feature input path: %s", config.customer_regional_feature_input_path)
    logger.info("AO1 Gold output path: %s", config.gold_output_path)

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

        gold_df = build_gold_ao1_dataframe(
            silver_df,
            order_time_df,
            shipping_product_df,
            customer_regional_df,
        )
        logger.info("AO1 Gold DataFrame created successfully.")

        validate_gold_ao1_dataframe(gold_df, config)
        logger.info("AO1 Gold pre-write validation completed successfully.")

        write_delta(gold_df, config.gold_output_path, config)
        logger.info("AO1 Gold Delta write completed successfully.")

        written_df = read_delta(spark, config.gold_output_path, config)
        validate_gold_ao1_dataframe(written_df, config)
        logger.info("AO1 Gold post-write validation completed successfully.")
        logger.info("DataCo AO1 Gold analytical table build completed successfully.")

    except Exception:
        logger.exception("AO1 Gold analytical table build failed.")
        raise


def main() -> None:
    """Run the AO1 Gold analytical table build with default configuration."""
    logger = configure_logging()
    config = GoldAO1Config()
    run_gold_ao1_build(config, logger)


if __name__ == "__main__":
    main()
