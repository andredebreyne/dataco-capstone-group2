"""Order-time feature engineering for the DataCo Silver dataset.

This job reads the cleaned Silver Delta dataset and derives decision-time
calendar variables from order_date_DateOrders only. It does not use shipping
dates, delivery outcomes, actual fulfillment durations, targets, or any
post-order information.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    dayofmonth,
    dayofweek,
    hour,
    lit,
    max as spark_max,
    min as spark_min,
    month,
    quarter,
    weekofyear,
    when,
    year,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

SILVER_INPUT_PATH = os.getenv(
    "DATACO_SILVER_INPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_orders_silver",
)

ORDER_TIME_FEATURE_OUTPUT_PATH = os.getenv(
    "DATACO_ORDER_TIME_FEATURE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_orders_order_time_features",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")
EXPECTED_SILVER_ROWS = 180_519
ORDER_TIMESTAMP_COLUMN = "order_date_DateOrders"

ORDER_TIME_FEATURE_COLUMNS = (
    "order_year",
    "order_quarter",
    "order_month",
    "order_week_of_year",
    "order_day_of_month",
    "order_day_of_week",
    "order_hour",
    "order_is_weekend",
    "order_season",
    "_order_time_features_processed_timestamp",
)

ORDER_TIME_FEATURE_TYPES = {
    "order_year": "int",
    "order_quarter": "int",
    "order_month": "int",
    "order_week_of_year": "int",
    "order_day_of_month": "int",
    "order_day_of_week": "int",
    "order_hour": "int",
    "order_is_weekend": "int",
    "order_season": "string",
    "_order_time_features_processed_timestamp": "timestamp",
}

ORDER_TIME_FEATURE_RANGES = {
    "order_quarter": (1, 4),
    "order_month": (1, 12),
    "order_week_of_year": (1, 53),
    "order_day_of_month": (1, 31),
    "order_day_of_week": (1, 7),
    "order_hour": (0, 23),
    "order_is_weekend": (0, 1),
}

APPROVED_ORDER_SEASONS = ("fall", "spring", "summer", "winter")


@dataclass(frozen=True)
class OrderTimeFeatureConfig:
    """Configuration for the order-time feature engineering job."""

    silver_input_path: str = SILVER_INPUT_PATH
    feature_output_path: str = ORDER_TIME_FEATURE_OUTPUT_PATH
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"
    expected_silver_rows: int = EXPECTED_SILVER_ROWS
    order_timestamp_column: str = ORDER_TIMESTAMP_COLUMN


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.order_time_features")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_paths(config: OrderTimeFeatureConfig) -> None:
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


def read_silver_delta(spark: SparkSession, config: OrderTimeFeatureConfig) -> DataFrame:
    """Read the cleaned Silver Delta dataset."""
    return spark.read.format(config.read_format).load(config.silver_input_path)


def validate_input_contract(df: DataFrame, config: OrderTimeFeatureConfig) -> None:
    """Validate the input fields required for order-time feature engineering."""
    if config.order_timestamp_column not in df.columns:
        raise ValueError(
            f"Missing required order timestamp column: {config.order_timestamp_column}"
        )

    timestamp_type = df.schema[config.order_timestamp_column].dataType.simpleString()
    if timestamp_type != "timestamp":
        raise ValueError(
            f"{config.order_timestamp_column} must be timestamp. "
            f"Found {timestamp_type}."
        )

    row_count = df.count()
    if row_count != config.expected_silver_rows:
        raise ValueError(
            f"Unexpected Silver row count. Expected {config.expected_silver_rows}, "
            f"found {row_count}."
        )


def derive_order_time_features(df: DataFrame, config: OrderTimeFeatureConfig) -> DataFrame:
    """Add deterministic decision-time calendar features from the order timestamp."""
    order_ts = col(config.order_timestamp_column)

    featured_df = (
        df.withColumn("order_year", year(order_ts).cast("int"))
        .withColumn("order_quarter", quarter(order_ts).cast("int"))
        .withColumn("order_month", month(order_ts).cast("int"))
        .withColumn("order_week_of_year", weekofyear(order_ts).cast("int"))
        .withColumn("order_day_of_month", dayofmonth(order_ts).cast("int"))
        .withColumn("order_day_of_week", dayofweek(order_ts).cast("int"))
        .withColumn("order_hour", hour(order_ts).cast("int"))
        .withColumn(
            "order_is_weekend",
            when(dayofweek(order_ts).isin(1, 7), lit(1)).otherwise(lit(0)).cast("int"),
        )
        .withColumn(
            "order_season",
            when(month(order_ts).isin(12, 1, 2), lit("winter"))
            .when(month(order_ts).isin(3, 4, 5), lit("spring"))
            .when(month(order_ts).isin(6, 7, 8), lit("summer"))
            .otherwise(lit("fall")),
        )
        .withColumn("_order_time_features_processed_timestamp", current_timestamp())
    )

    return featured_df


def write_delta(df: DataFrame, output_path: str, config: OrderTimeFeatureConfig) -> None:
    """Write a DataFrame to Delta using the configured write policy."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def validate_order_time_feature_schema(feature_df: DataFrame) -> None:
    """Validate generated order-time feature columns and Spark data types."""
    missing_features = sorted(
        column_name
        for column_name in ORDER_TIME_FEATURE_COLUMNS
        if column_name not in feature_df.columns
    )
    if missing_features:
        raise ValueError(f"Missing order-time feature columns: {missing_features}")

    invalid_types = {}
    for column_name, expected_type in ORDER_TIME_FEATURE_TYPES.items():
        actual_type = feature_df.schema[column_name].dataType.simpleString()
        if actual_type != expected_type:
            invalid_types[column_name] = {
                "expected": expected_type,
                "actual": actual_type,
            }

    if invalid_types:
        raise ValueError(f"Invalid order-time feature column types: {invalid_types}")


def validate_order_time_feature_ranges(feature_df: DataFrame) -> None:
    """Validate deterministic ranges for generated order-time features."""
    range_stats = feature_df.select(
        [
            aggregation.alias(f"{column_name}__{stat_name}")
            for column_name in ORDER_TIME_FEATURE_RANGES
            for stat_name, aggregation in (
                ("min", spark_min(col(column_name))),
                ("max", spark_max(col(column_name))),
            )
        ]
    ).collect()[0].asDict()

    range_errors = {}
    for column_name, (
        minimum_allowed,
        maximum_allowed,
    ) in ORDER_TIME_FEATURE_RANGES.items():
        observed_min = range_stats[f"{column_name}__min"]
        observed_max = range_stats[f"{column_name}__max"]
        if observed_min is None or observed_max is None:
            range_errors[column_name] = "contains only null values"
        elif observed_min < minimum_allowed or observed_max > maximum_allowed:
            range_errors[column_name] = {
                "expected_range": [minimum_allowed, maximum_allowed],
                "observed_range": [observed_min, observed_max],
            }

    invalid_seasons = [
        row["order_season"]
        for row in (
            feature_df.filter(~col("order_season").isin(*APPROVED_ORDER_SEASONS))
            .select("order_season")
            .distinct()
            .limit(20)
            .collect()
        )
    ]
    if invalid_seasons:
        range_errors["order_season"] = {
            "approved_values": list(APPROVED_ORDER_SEASONS),
            "observed_invalid_values": invalid_seasons,
        }

    if range_errors:
        raise ValueError(f"Invalid order-time feature values: {range_errors}")


def validate_feature_output(
    spark: SparkSession,
    config: OrderTimeFeatureConfig,
) -> None:
    """Validate the written order-time feature dataset."""
    feature_df = spark.read.format(config.write_format).load(config.feature_output_path)

    row_count = feature_df.count()
    if row_count != config.expected_silver_rows:
        raise ValueError(
            f"Unexpected feature output row count. Expected {config.expected_silver_rows}, "
            f"found {row_count}."
        )

    validate_order_time_feature_schema(feature_df)

    null_metrics = feature_df.select(
        [
            when(col(column_name).isNull(), lit(1)).otherwise(lit(0)).alias(column_name)
            for column_name in ORDER_TIME_FEATURE_COLUMNS
        ]
    )

    null_counts = null_metrics.groupBy().sum().collect()[0].asDict()
    columns_with_nulls = {
        metric_name.replace("sum(", "").replace(")", ""): null_count
        for metric_name, null_count in null_counts.items()
        if null_count != 0
    }

    if columns_with_nulls:
        raise ValueError(
            "Order-time feature output contains null values: "
            f"{columns_with_nulls}"
        )

    validate_order_time_feature_ranges(feature_df)


def run_order_time_feature_engineering(
    config: OrderTimeFeatureConfig,
    logger: logging.Logger,
) -> None:
    """Execute the DataCo order-time feature engineering workflow."""
    spark = get_spark_session()

    logger.info("Starting DataCo order-time feature engineering job.")
    logger.info("Silver input path: %s", config.silver_input_path)
    logger.info("Feature output path: %s", config.feature_output_path)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        silver_df = read_silver_delta(spark, config)
        logger.info("Silver Delta loaded successfully with %d columns.", len(silver_df.columns))

        validate_input_contract(silver_df, config)
        logger.info("Silver input contract validated successfully.")

        feature_df = derive_order_time_features(silver_df, config)
        logger.info("Order-time feature derivation completed successfully.")

        write_delta(feature_df, config.feature_output_path, config)
        logger.info("Order-time feature Delta write completed successfully.")

        validate_feature_output(spark, config)
        logger.info("Order-time feature output validation completed successfully.")
        logger.info("DataCo order-time feature engineering job completed successfully.")

    except Exception:
        logger.exception("Order-time feature engineering failed.")
        raise


def main() -> None:
    """Run the order-time feature engineering job with default configuration."""
    logger = configure_logging()
    config = OrderTimeFeatureConfig()
    run_order_time_feature_engineering(config, logger)


if __name__ == "__main__":
    main()
