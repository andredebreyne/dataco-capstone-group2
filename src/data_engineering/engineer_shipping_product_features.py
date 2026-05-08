"""Shipping and product feature engineering for the DataCo Silver dataset.

This job reads the cleaned Silver Delta dataset and derives decision-time
features from planned shipping, product, category, department, and order-item
composition fields. It avoids post-shipment outcomes, delivery status fields,
actual fulfillment durations, and target variables.
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

SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH = os.getenv(
    "DATACO_SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_shipping_product_features",
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
    "Days_for_shipment_scheduled",
    "Shipping_Mode",
    "Category_Id",
    "Category_Name",
    "Department_Id",
    "Department_Name",
    "Product_Card_Id",
    "Product_Category_Id",
    "Product_Name",
    "Product_Price",
    "Product_Status",
    "Order_Item_Cardprod_Id",
    "Order_Item_Product_Price",
    "Order_Item_Quantity",
    "Order_Item_Discount",
    "Order_Item_Discount_Rate",
    "Order_Item_Total",
)

OUTPUT_KEY_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "_ingest_timestamp",
    "_source_file",
    "_silver_processed_timestamp",
)

SHIPPING_PRODUCT_FEATURE_COLUMNS = (
    "scheduled_shipping_days",
    "shipping_speed_tier",
    "shipping_mode_normalized",
    "is_same_day_or_next_day_shipping",
    "is_standard_shipping",
    "product_category_key",
    "product_department_key",
    "product_catalog_key",
    "product_name_normalized",
    "product_status_flag",
    "product_list_price",
    "order_item_quantity",
    "item_unit_price",
    "item_discount_amount",
    "item_discount_rate",
    "item_gross_sales_estimate",
    "item_net_sales_amount",
    "item_discount_share_of_gross",
    "_shipping_product_features_processed_timestamp",
)

EXPECTED_OUTPUT_COLUMNS = OUTPUT_KEY_COLUMNS + SHIPPING_PRODUCT_FEATURE_COLUMNS

FORBIDDEN_INPUT_COLUMNS = (
    "Days_for_shipping_real",
    "Delivery_Status",
    "Late_delivery_risk",
    "shipping_date_DateOrders",
    "Order_Status",
    "Order_Profit_Per_Order",
    "Benefit_per_order",
    "Order_Item_Profit_Ratio",
)


@dataclass(frozen=True)
class ShippingProductFeatureConfig:
    """Configuration for shipping and product feature engineering."""

    silver_input_path: str = SILVER_INPUT_PATH
    feature_output_path: str = SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH
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
    return logging.getLogger("dataco.shipping_product_features")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_paths(config: ShippingProductFeatureConfig) -> None:
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
    config: ShippingProductFeatureConfig,
) -> DataFrame:
    """Read the cleaned Silver Delta dataset."""
    return spark.read.format(config.read_format).load(config.silver_input_path)


def validate_input_contract(df: DataFrame, config: ShippingProductFeatureConfig) -> None:
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


def derive_shipping_product_features(
    df: DataFrame,
) -> DataFrame:
    """Add deterministic shipping and product features available before dispatch."""
    scheduled_days = col("Days_for_shipment_scheduled")
    gross_sales_estimate = col("Order_Item_Product_Price") * col("Order_Item_Quantity")

    featured_df = (
        df.withColumn("scheduled_shipping_days", scheduled_days.cast("int"))
        .withColumn(
            "shipping_speed_tier",
            when(scheduled_days <= 1, lit("expedited"))
            .when(scheduled_days <= 3, lit("standard"))
            .otherwise(lit("economy")),
        )
        .withColumn("shipping_mode_normalized", normalize_text_column("Shipping_Mode"))
        .withColumn(
            "is_same_day_or_next_day_shipping",
            when(scheduled_days <= 1, lit(1)).otherwise(lit(0)).cast("int"),
        )
        .withColumn(
            "is_standard_shipping",
            when(lower(trim(col("Shipping_Mode"))) == "standard class", lit(1))
            .otherwise(lit(0))
            .cast("int"),
        )
        .withColumn(
            "product_category_key",
            concat_ws(
                "_",
                col("Category_Id").cast("string"),
                normalize_text_column("Category_Name"),
            ),
        )
        .withColumn(
            "product_department_key",
            concat_ws(
                "_",
                col("Department_Id").cast("string"),
                normalize_text_column("Department_Name"),
            ),
        )
        .withColumn(
            "product_catalog_key",
            concat_ws(
                "_",
                col("Product_Card_Id").cast("string"),
                col("Product_Category_Id").cast("string"),
                col("Order_Item_Cardprod_Id").cast("string"),
            ),
        )
        .withColumn("product_name_normalized", normalize_text_column("Product_Name"))
        .withColumn("product_status_flag", col("Product_Status").cast("int"))
        .withColumn("product_list_price", col("Product_Price").cast("double"))
        .withColumn("order_item_quantity", col("Order_Item_Quantity").cast("int"))
        .withColumn("item_unit_price", col("Order_Item_Product_Price").cast("double"))
        .withColumn("item_discount_amount", col("Order_Item_Discount").cast("double"))
        .withColumn("item_discount_rate", col("Order_Item_Discount_Rate").cast("double"))
        .withColumn("item_gross_sales_estimate", spark_round(gross_sales_estimate, 2))
        .withColumn("item_net_sales_amount", col("Order_Item_Total").cast("double"))
        .withColumn(
            "item_discount_share_of_gross",
            when(gross_sales_estimate > 0, col("Order_Item_Discount") / gross_sales_estimate)
            .otherwise(lit(None))
            .cast("double"),
        )
        .withColumn("_shipping_product_features_processed_timestamp", current_timestamp())
    )

    return featured_df.select(*(OUTPUT_KEY_COLUMNS + SHIPPING_PRODUCT_FEATURE_COLUMNS))


def write_delta(
    df: DataFrame,
    output_path: str,
    config: ShippingProductFeatureConfig,
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
    config: ShippingProductFeatureConfig,
) -> None:
    """Validate the written shipping and product feature dataset."""
    feature_df = spark.read.format(config.write_format).load(config.feature_output_path)

    row_count = feature_df.count()
    if row_count != config.expected_silver_rows:
        raise ValueError(
            f"Unexpected feature output row count. Expected {config.expected_silver_rows}, "
            f"found {row_count}."
        )

    missing_features = sorted(
        column_name
        for column_name in EXPECTED_OUTPUT_COLUMNS
        if column_name not in feature_df.columns
    )
    if missing_features:
        raise ValueError(f"Missing shipping/product output columns: {missing_features}")

    unexpected_columns = sorted(
        column_name
        for column_name in feature_df.columns
        if column_name not in EXPECTED_OUTPUT_COLUMNS
    )
    if unexpected_columns:
        raise ValueError(
            "Shipping/product feature output contains unexpected columns: "
            f"{unexpected_columns}"
        )

    forbidden_generated_columns = sorted(
        column_name
        for column_name in FORBIDDEN_INPUT_COLUMNS
        if column_name in feature_df.columns
    )
    if forbidden_generated_columns:
        raise ValueError(
            "Forbidden columns were generated as shipping/product features: "
            f"{forbidden_generated_columns}"
        )

    required_non_null_features = (
        "scheduled_shipping_days",
        "shipping_speed_tier",
        "shipping_mode_normalized",
        "product_category_key",
        "product_department_key",
        "product_status_flag",
        "product_list_price",
        "order_item_quantity",
        "item_unit_price",
        "item_net_sales_amount",
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
            "Required shipping/product features contain null values: "
            f"{columns_with_nulls}"
        )


def run_shipping_product_feature_engineering(
    config: ShippingProductFeatureConfig,
    logger: logging.Logger,
) -> None:
    """Execute the DataCo shipping and product feature engineering workflow."""
    spark = get_spark_session()

    logger.info("Starting DataCo shipping/product feature engineering job.")
    logger.info("Silver input path: %s", config.silver_input_path)
    logger.info("Feature output path: %s", config.feature_output_path)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        silver_df = read_silver_delta(spark, config)
        logger.info("Silver Delta loaded successfully with %d columns.", len(silver_df.columns))

        validate_input_contract(silver_df, config)
        logger.info("Silver input contract validated successfully.")

        feature_df = derive_shipping_product_features(silver_df)
        logger.info("Shipping/product feature derivation completed successfully.")

        write_delta(feature_df, config.feature_output_path, config)
        logger.info("Shipping/product feature Delta write completed successfully.")

        validate_feature_output(spark, config)
        logger.info("Shipping/product feature output validation completed successfully.")
        logger.info("DataCo shipping/product feature engineering job completed successfully.")

    except Exception:
        logger.exception("Shipping/product feature engineering failed.")
        raise


def main() -> None:
    """Run the shipping/product feature engineering job with default configuration."""
    logger = configure_logging()
    config = ShippingProductFeatureConfig()
    run_shipping_product_feature_engineering(config, logger)


if __name__ == "__main__":
    main()
