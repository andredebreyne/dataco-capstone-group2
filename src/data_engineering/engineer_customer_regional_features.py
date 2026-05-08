"""Customer and regional feature engineering for the DataCo Silver dataset.

This job reads the cleaned Silver Delta dataset and derives decision-time
customer segment and regional features. It excludes personal identifiers,
address-level details, targets, post-shipment outcomes, and learned historical
aggregates.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    concat_ws,
    current_timestamp,
    lit,
    lower,
    regexp_replace,
    round as spark_round,
    trim,
    when,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

SILVER_INPUT_PATH = os.getenv(
    "DATACO_SILVER_INPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_orders_silver",
)

CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH = os.getenv(
    "DATACO_CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_customer_regional_features",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")
EXPECTED_SILVER_ROWS = 180_519

REQUIRED_INPUT_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "_ingest_timestamp",
    "_source_file",
    "_silver_processed_timestamp",
    "Customer_Segment",
    "Customer_Country",
    "Customer_State",
    "Customer_City",
    "Customer_Zipcode",
    "Market",
    "Order_Country",
    "Order_Region",
    "Order_State",
    "Order_City",
    "Order_Zipcode",
    "Latitude",
    "Longitude",
)

OUTPUT_KEY_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "_ingest_timestamp",
    "_source_file",
    "_silver_processed_timestamp",
)

CUSTOMER_REGIONAL_FEATURE_COLUMNS = (
    "customer_segment_normalized",
    "customer_country_normalized",
    "customer_state_normalized",
    "customer_city_normalized",
    "customer_zipcode_available",
    "market_normalized",
    "order_country_normalized",
    "order_region_normalized",
    "order_state_normalized",
    "order_city_normalized",
    "order_zipcode_available",
    "customer_region_key",
    "order_region_key",
    "customer_order_country_match",
    "customer_order_state_match",
    "latitude_rounded",
    "longitude_rounded",
    "geo_coordinates_available",
    "_customer_regional_features_processed_timestamp",
)

EXPECTED_OUTPUT_COLUMNS = OUTPUT_KEY_COLUMNS + CUSTOMER_REGIONAL_FEATURE_COLUMNS

FORBIDDEN_INPUT_COLUMNS = (
    "Customer_Email",
    "Customer_Fname",
    "Customer_Lname",
    "Customer_Password",
    "Customer_Street",
    "Delivery_Status",
    "Late_delivery_risk",
    "Days_for_shipping_real",
    "shipping_date_DateOrders",
    "Order_Status",
    "Order_Profit_Per_Order",
    "Benefit_per_order",
    "Order_Item_Profit_Ratio",
)


@dataclass(frozen=True)
class CustomerRegionalFeatureConfig:
    """Configuration for customer and regional feature engineering."""

    silver_input_path: str = SILVER_INPUT_PATH
    feature_output_path: str = CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"
    expected_silver_rows: int = EXPECTED_SILVER_ROWS


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.customer_regional_features")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_paths(config: CustomerRegionalFeatureConfig) -> None:
    """Validate that configured paths use Unity Catalog Volumes."""
    configured_paths = {
        "silver_input_path": config.silver_input_path,
        "feature_output_path": config.feature_output_path,
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


def read_silver_delta(
    spark: SparkSession,
    config: CustomerRegionalFeatureConfig,
) -> DataFrame:
    """Read the cleaned Silver Delta dataset."""
    return spark.read.format(config.read_format).load(config.silver_input_path)


def validate_input_contract(df: DataFrame, config: CustomerRegionalFeatureConfig) -> None:
    """Validate required Silver fields and row count before feature derivation."""
    missing_columns = sorted(
        column_name
        for column_name in REQUIRED_INPUT_COLUMNS
        if column_name not in df.columns
    )
    if missing_columns:
        raise ValueError(f"Missing required Silver columns: {missing_columns}")

    row_count = df.count()
    if row_count != config.expected_silver_rows:
        raise ValueError(
            f"Unexpected Silver row count. Expected {config.expected_silver_rows}, "
            f"found {row_count}."
        )


def normalize_text_column(column_name: str):
    """Normalize a string column into a stable lowercase feature token."""
    return regexp_replace(lower(trim(col(column_name))), r"\s+", "_")


def clean_location_token(column_name: str):
    """Normalize a location field and remove punctuation from the token."""
    normalized = normalize_text_column(column_name)
    return regexp_replace(normalized, r"[^a-z0-9_]", "")


def availability_flag(column_name: str):
    """Return an integer flag indicating whether a value is present."""
    return when(col(column_name).isNotNull(), lit(1)).otherwise(lit(0)).cast("int")


def derive_customer_regional_features(df: DataFrame) -> DataFrame:
    """Add deterministic customer and regional features available at order time."""
    customer_country = clean_location_token("Customer_Country")
    customer_state = clean_location_token("Customer_State")
    customer_city = clean_location_token("Customer_City")
    order_country = clean_location_token("Order_Country")
    order_region = clean_location_token("Order_Region")
    order_state = clean_location_token("Order_State")
    order_city = clean_location_token("Order_City")

    featured_df = (
        df.withColumn("customer_segment_normalized", normalize_text_column("Customer_Segment"))
        .withColumn("customer_country_normalized", customer_country)
        .withColumn("customer_state_normalized", customer_state)
        .withColumn("customer_city_normalized", customer_city)
        .withColumn("customer_zipcode_available", availability_flag("Customer_Zipcode"))
        .withColumn("market_normalized", clean_location_token("Market"))
        .withColumn("order_country_normalized", order_country)
        .withColumn("order_region_normalized", order_region)
        .withColumn("order_state_normalized", order_state)
        .withColumn("order_city_normalized", order_city)
        .withColumn("order_zipcode_available", availability_flag("Order_Zipcode"))
        .withColumn(
            "customer_region_key",
            concat_ws("_", customer_country, customer_state, customer_city),
        )
        .withColumn(
            "order_region_key",
            concat_ws("_", order_country, order_region, order_state, order_city),
        )
        .withColumn(
            "customer_order_country_match",
            when(customer_country == order_country, lit(1)).otherwise(lit(0)).cast("int"),
        )
        .withColumn(
            "customer_order_state_match",
            when(customer_state == order_state, lit(1)).otherwise(lit(0)).cast("int"),
        )
        .withColumn("latitude_rounded", spark_round(col("Latitude"), 2).cast("double"))
        .withColumn("longitude_rounded", spark_round(col("Longitude"), 2).cast("double"))
        .withColumn(
            "geo_coordinates_available",
            when(col("Latitude").isNotNull() & col("Longitude").isNotNull(), lit(1))
            .otherwise(lit(0))
            .cast("int"),
        )
        .withColumn("_customer_regional_features_processed_timestamp", current_timestamp())
    )

    return featured_df.select(*(OUTPUT_KEY_COLUMNS + CUSTOMER_REGIONAL_FEATURE_COLUMNS))


def write_delta(
    df: DataFrame,
    output_path: str,
    config: CustomerRegionalFeatureConfig,
) -> None:
    """Write a DataFrame to Delta using the configured write policy."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def validate_feature_output(
    spark: SparkSession,
    config: CustomerRegionalFeatureConfig,
) -> None:
    """Validate the written customer and regional feature dataset."""
    feature_df = spark.read.format(config.write_format).load(config.feature_output_path)

    row_count = feature_df.count()
    if row_count != config.expected_silver_rows:
        raise ValueError(
            f"Unexpected feature output row count. Expected {config.expected_silver_rows}, "
            f"found {row_count}."
        )

    missing_columns = sorted(
        column_name
        for column_name in EXPECTED_OUTPUT_COLUMNS
        if column_name not in feature_df.columns
    )
    if missing_columns:
        raise ValueError(f"Missing customer/regional output columns: {missing_columns}")

    unexpected_columns = sorted(
        column_name
        for column_name in feature_df.columns
        if column_name not in EXPECTED_OUTPUT_COLUMNS
    )
    if unexpected_columns:
        raise ValueError(
            "Customer/regional feature output contains unexpected columns: "
            f"{unexpected_columns}"
        )

    forbidden_output_columns = sorted(
        column_name
        for column_name in FORBIDDEN_INPUT_COLUMNS
        if column_name in feature_df.columns
    )
    if forbidden_output_columns:
        raise ValueError(
            "Forbidden customer, target, or post-shipment columns are present: "
            f"{forbidden_output_columns}"
        )

    required_non_null_features = (
        "customer_segment_normalized",
        "customer_country_normalized",
        "customer_state_normalized",
        "customer_city_normalized",
        "market_normalized",
        "order_country_normalized",
        "order_region_normalized",
        "order_state_normalized",
        "order_city_normalized",
        "customer_region_key",
        "order_region_key",
    )

    null_counts = feature_df.select(
        [
            when(col(column_name).isNull(), lit(1)).otherwise(lit(0)).alias(column_name)
            for column_name in required_non_null_features
        ]
    ).groupBy().sum().collect()[0].asDict()

    columns_with_nulls = {
        metric_name.replace("sum(", "").replace(")", ""): null_count
        for metric_name, null_count in null_counts.items()
        if null_count != 0
    }

    if columns_with_nulls:
        raise ValueError(
            "Required customer/regional features contain null values: "
            f"{columns_with_nulls}"
        )


def run_customer_regional_feature_engineering(
    config: CustomerRegionalFeatureConfig,
    logger: logging.Logger,
) -> None:
    """Execute the DataCo customer and regional feature engineering workflow."""
    spark = get_spark_session()

    logger.info("Starting DataCo customer/regional feature engineering job.")
    logger.info("Silver input path: %s", config.silver_input_path)
    logger.info("Feature output path: %s", config.feature_output_path)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        silver_df = read_silver_delta(spark, config)
        logger.info("Silver Delta loaded successfully with %d columns.", len(silver_df.columns))

        validate_input_contract(silver_df, config)
        logger.info("Silver input contract validated successfully.")

        feature_df = derive_customer_regional_features(silver_df)
        logger.info("Customer/regional feature derivation completed successfully.")

        write_delta(feature_df, config.feature_output_path, config)
        logger.info("Customer/regional feature Delta write completed successfully.")

        validate_feature_output(spark, config)
        logger.info("Customer/regional feature output validation completed successfully.")
        logger.info("DataCo customer/regional feature engineering job completed successfully.")

    except Exception:
        logger.exception("Customer/regional feature engineering failed.")
        raise


def main() -> None:
    """Run the customer/regional feature engineering job with default configuration."""
    logger = configure_logging()
    config = CustomerRegionalFeatureConfig()
    run_customer_regional_feature_engineering(config, logger)


if __name__ == "__main__":
    main()
