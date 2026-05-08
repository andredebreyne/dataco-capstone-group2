"""Silver cleaning job for the DataCo Smart Supply Chain dataset.

This script reads the Bronze Delta dataset, standardizes missing values,
casts approved analytical data types, parses order timestamps, normalizes
categorical strings, and writes a cleaned Silver Delta dataset.

Silver does not perform model-training imputations, scaling, resampling, or
one-hot/label encoding. Those steps must be fit on training data only in later
modeling pipelines.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    lit,
    regexp_replace,
    sum as spark_sum,
    to_timestamp,
    trim,
    when,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

BRONZE_INPUT_PATH = os.getenv(
    "DATACO_BRONZE_INPUT_PATH",
    f"{VOLUME_ROOT}/bronze/dataco_supply_chain",
)

SILVER_OUTPUT_PATH = os.getenv(
    "DATACO_SILVER_OUTPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_orders_silver",
)

QUALITY_REPORT_OUTPUT_PATH = os.getenv(
    "DATACO_SILVER_QUALITY_REPORT_OUTPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_orders_silver_quality_report",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")
EXPECTED_BRONZE_ROWS = 180_519

INTEGER_COLUMNS = (
    "Days_for_shipping_real",
    "Days_for_shipment_scheduled",
    "Late_delivery_risk",
    "Category_Id",
    "Customer_Id",
    "Department_Id",
    "Order_Customer_Id",
    "Order_Id",
    "Order_Item_Cardprod_Id",
    "Order_Item_Id",
    "Order_Item_Quantity",
    "Product_Card_Id",
    "Product_Category_Id",
    "Product_Status",
)

DECIMAL_COLUMNS = (
    "Benefit_per_order",
    "Sales_per_customer",
    "Latitude",
    "Longitude",
    "Order_Item_Discount",
    "Order_Item_Discount_Rate",
    "Order_Item_Product_Price",
    "Order_Item_Profit_Ratio",
    "Sales",
    "Order_Item_Total",
    "Order_Profit_Per_Order",
    "Product_Price",
)

TIMESTAMP_COLUMNS = (
    "order_date_DateOrders",
    "shipping_date_DateOrders",
)

CATEGORICAL_COLUMNS = (
    "Type",
    "Delivery_Status",
    "Category_Name",
    "Customer_City",
    "Customer_Country",
    "Customer_Email",
    "Customer_Fname",
    "Customer_Lname",
    "Customer_Password",
    "Customer_Segment",
    "Customer_State",
    "Customer_Street",
    "Customer_Zipcode",
    "Department_Name",
    "Market",
    "Order_City",
    "Order_Country",
    "Order_Region",
    "Order_State",
    "Order_Status",
    "Order_Zipcode",
    "Product_Description",
    "Product_Image",
    "Product_Name",
    "Shipping_Mode",
    "_source_file",
)

REQUIRED_COLUMNS = set(
    INTEGER_COLUMNS
    + DECIMAL_COLUMNS
    + TIMESTAMP_COLUMNS
    + CATEGORICAL_COLUMNS
    + BRONZE_LINEAGE_COLUMNS
    )
BRONZE_LINEAGE_COLUMNS = ("_ingest_timestamp", "_source_file")
SILVER_LINEAGE_COLUMNS = ("_silver_processed_timestamp",)


@dataclass(frozen=True)
class SilverCleaningConfig:
    """Configuration for the Silver cleaning job."""

    bronze_input_path: str = BRONZE_INPUT_PATH
    silver_output_path: str = SILVER_OUTPUT_PATH
    quality_report_output_path: str = QUALITY_REPORT_OUTPUT_PATH
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"
    expected_bronze_rows: int = EXPECTED_BRONZE_ROWS
    timestamp_pattern: str = "M/d/yyyy H:mm"


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.silver_cleaning")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_paths(config: SilverCleaningConfig) -> None:
    """Validate that Silver paths use Unity Catalog Volumes, not public DBFS."""
    configured_paths = {
        "bronze_input_path": config.bronze_input_path,
        "silver_output_path": config.silver_output_path,
        "quality_report_output_path": config.quality_report_output_path,
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


def read_bronze_delta(spark: SparkSession, config: SilverCleaningConfig) -> DataFrame:
    """Read the Bronze Delta dataset."""
    return spark.read.format(config.read_format).load(config.bronze_input_path)


def canonicalize_column_name(column_name: str) -> str:
    """Return the canonical project column name used by downstream Silver logic."""
    canonical_name = column_name.strip()
    canonical_name = re.sub(r"[ ,;{}()\n\t=]", "_", canonical_name)
    canonical_name = re.sub(r"_+", "_", canonical_name)
    if column_name.startswith("_"):
        return canonical_name
    return canonical_name.strip("_")


def canonicalize_bronze_column_names(df: DataFrame) -> DataFrame:
    """Normalize Bronze column names before applying the Silver schema contract."""
    canonical_columns = [canonicalize_column_name(column_name) for column_name in df.columns]

    if len(set(canonical_columns)) != len(canonical_columns):
        duplicate_columns = sorted(
            {
                column_name
                for column_name in canonical_columns
                if canonical_columns.count(column_name) > 1
            }
        )
        raise ValueError(
            "Bronze column-name canonicalization created duplicate columns: "
            f"{duplicate_columns}"
        )

    if canonical_columns == df.columns:
        return df

    return df.toDF(*canonical_columns)


def validate_required_columns(df: DataFrame) -> None:
    """Validate that the Bronze dataset contains the columns needed for Silver."""
    missing_columns = sorted(REQUIRED_COLUMNS.difference(df.columns))

    if missing_columns:
        raise ValueError(f"Missing required Bronze columns: {missing_columns}")


def nullify_blank_strings(df: DataFrame) -> DataFrame:
    """Convert empty strings to nulls and trim all string columns."""
    cleaned_df = df

    for field in cleaned_df.schema.fields:
        if field.dataType.simpleString() == "string":
            cleaned_df = cleaned_df.withColumn(
                field.name,
                when(trim(col(field.name)) == "", lit(None)).otherwise(trim(col(field.name))),
            )

    return cleaned_df


def normalize_categorical_strings(df: DataFrame) -> DataFrame:
    """Collapse repeated whitespace in categorical string columns."""
    normalized_df = df

    for column_name in CATEGORICAL_COLUMNS:
        if column_name in normalized_df.columns:
            normalized_df = normalized_df.withColumn(
                column_name,
                when(
                    col(column_name).isNull(),
                    lit(None),
                ).otherwise(regexp_replace(col(column_name), r"\s+", " ")),
            )

    return normalized_df


def cast_integer_columns(df: DataFrame) -> DataFrame:
    """Cast integer-like source columns to integer."""
    typed_df = df

    for column_name in INTEGER_COLUMNS:
        typed_df = typed_df.withColumn(column_name, col(column_name).cast("int"))

    return typed_df


def cast_decimal_columns(df: DataFrame) -> DataFrame:
    """Cast decimal-like source columns to double."""
    typed_df = df

    for column_name in DECIMAL_COLUMNS:
        typed_df = typed_df.withColumn(column_name, col(column_name).cast("double"))

    return typed_df


def parse_timestamp_columns(df: DataFrame, config: SilverCleaningConfig) -> DataFrame:
    """Parse timestamp source columns using the approved DataCo timestamp pattern."""
    typed_df = df

    for column_name in TIMESTAMP_COLUMNS:
        typed_df = typed_df.withColumn(
            column_name,
            to_timestamp(col(column_name), config.timestamp_pattern),
        )

    return typed_df


def add_silver_lineage(df: DataFrame) -> DataFrame:
    """Append Silver processing metadata."""
    return df.withColumn("_silver_processed_timestamp", current_timestamp())


def apply_silver_cleaning(df: DataFrame, config: SilverCleaningConfig) -> DataFrame:
    """Apply deterministic Silver cleaning rules."""
    cleaned_df = nullify_blank_strings(df)
    cleaned_df = normalize_categorical_strings(cleaned_df)
    cleaned_df = cast_integer_columns(cleaned_df)
    cleaned_df = cast_decimal_columns(cleaned_df)
    cleaned_df = parse_timestamp_columns(cleaned_df, config)
    cleaned_df = add_silver_lineage(cleaned_df)
    return cleaned_df


def build_quality_metrics(
    bronze_df: DataFrame,
    cleaned_string_df: DataFrame,
    silver_df: DataFrame,
    config: SilverCleaningConfig,
) -> list[tuple[str, str, str]]:
    """Build quality-control metrics for the Silver cleaning run."""
    metrics: list[tuple[str, str, str]] = []

    bronze_row_count = bronze_df.count()
    silver_row_count = silver_df.count()
    dropped_row_count = bronze_row_count - silver_row_count

    metrics.append(("bronze_row_count", str(bronze_row_count), "Rows read from Bronze Delta."))
    metrics.append(("silver_row_count", str(silver_row_count), "Rows written to Silver Delta."))
    metrics.append(("dropped_row_count", str(dropped_row_count), "Rows dropped by Silver cleaning."))
    metrics.append(
        (
            "expected_bronze_rows",
            str(config.expected_bronze_rows),
            "Expected row count from source verification.",
        )
    )

    important_missing_columns = (
        "Product_Description",
        "Order_Zipcode",
        "Customer_Lname",
        "Customer_Zipcode",
        "order_date_DateOrders",
        "shipping_date_DateOrders",
    )

    for column_name in important_missing_columns:
        missing_count = silver_df.select(
            spark_sum(when(col(column_name).isNull(), 1).otherwise(0)).alias("missing_count")
        ).collect()[0]["missing_count"]
        metrics.append(
            (
                f"missing_{column_name}",
                str(missing_count),
                "Null values after Silver cleaning.",
            )
        )

    for column_name in INTEGER_COLUMNS:
        invalid_count = cleaned_string_df.select(
            spark_sum(
                when(
                    col(column_name).isNotNull()
                    & col(column_name).cast("int").isNull(),
                    1,
                ).otherwise(0)
            ).alias("invalid_count")
        ).collect()[0]["invalid_count"]
    
        metrics.append(
            (
                f"invalid_integer_cast_{column_name}",
                str(invalid_count),
                "Non-null source values that could not be cast to integer.",
            )
        )

    for column_name in DECIMAL_COLUMNS:
        invalid_count = cleaned_string_df.select(
            spark_sum(
                when(
                    col(column_name).isNotNull()
                    & col(column_name).cast("double").isNull(),
                    1,
                ).otherwise(0)
            ).alias("invalid_count")
        ).collect()[0]["invalid_count"]
    
        metrics.append(
            (
                f"invalid_decimal_cast_{column_name}",
                str(invalid_count),
                "Non-null source values that could not be cast to double.",
            )
        )
        
    for column_name in TIMESTAMP_COLUMNS:
        invalid_count = cleaned_string_df.select(
            spark_sum(
                when(
                    col(column_name).isNotNull()
                    & to_timestamp(col(column_name), config.timestamp_pattern).isNull(),
                    1,
                ).otherwise(0)
            ).alias("invalid_count")
        ).collect()[0]["invalid_count"]
        metrics.append(
            (
                f"invalid_timestamp_parse_{column_name}",
                str(invalid_count),
                "Non-null source values that could not be parsed as timestamps.",
            )
        )

    output_columns = ",".join(silver_df.columns)
    metrics.append(("silver_column_count", str(len(silver_df.columns)), output_columns))

    return metrics


def write_delta(df: DataFrame, output_path: str, config: SilverCleaningConfig) -> None:
    """Write a DataFrame to Delta using the project overwrite policy."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def write_quality_report(
    spark: SparkSession,
    metrics: list[tuple[str, str, str]],
    config: SilverCleaningConfig,
) -> None:
    """Write Silver cleaning metrics as a Delta report."""
    metrics_df = spark.createDataFrame(
        metrics,
        schema="metric_name STRING, metric_value STRING, metric_details STRING",
    ).withColumn("_report_timestamp", current_timestamp())

    write_delta(metrics_df, config.quality_report_output_path, config)

def validate_expected_column_types(silver_df: DataFrame) -> None:
    """Validate that Silver output columns match the approved schema contract."""
    actual_types = {
        field.name: field.dataType.simpleString()
        for field in silver_df.schema.fields
    }

    expected_types: dict[str, str] = {}

    for column_name in INTEGER_COLUMNS:
        expected_types[column_name] = "int"

    for column_name in DECIMAL_COLUMNS:
        expected_types[column_name] = "double"

    for column_name in TIMESTAMP_COLUMNS:
        expected_types[column_name] = "timestamp"

    for column_name in CATEGORICAL_COLUMNS:
        expected_types[column_name] = "string"

    expected_types["_ingest_timestamp"] = "timestamp"
    expected_types["_source_file"] = "string"
    expected_types["_silver_processed_timestamp"] = "timestamp"

    missing_columns = sorted(
        column_name
        for column_name in expected_types
        if column_name not in actual_types
    )

    if missing_columns:
        raise ValueError(
            f"Missing expected Silver schema columns: {missing_columns}"
        )

    type_mismatches = sorted(
        (
            column_name,
            expected_type,
            actual_types[column_name],
        )
        for column_name, expected_type in expected_types.items()
        if actual_types[column_name] != expected_type
    )

    if type_mismatches:
        mismatch_details = [
            f"{column_name}: expected {expected_type}, found {actual_type}"
            for column_name, expected_type, actual_type in type_mismatches
        ]

        raise ValueError(
            "Silver schema type validation failed. "
            f"Mismatches: {mismatch_details}"
        )

def validate_silver_output(
    spark: SparkSession,
    config: SilverCleaningConfig,
) -> None:
    """Validate the written Silver Delta dataset."""
    silver_df = spark.read.format(config.write_format).load(config.silver_output_path)

    row_count = silver_df.count()
    if row_count != config.expected_bronze_rows:
        raise ValueError(
            f"Unexpected Silver row count. Expected {config.expected_bronze_rows}, "
            f"found {row_count}."
        )

    required_lineage = set(BRONZE_LINEAGE_COLUMNS + SILVER_LINEAGE_COLUMNS)
    missing_lineage = sorted(required_lineage.difference(silver_df.columns))

    if missing_lineage:
        raise ValueError(f"Missing lineage columns in Silver output: {missing_lineage}")

    validate_expected_column_types(silver_df)

def run_silver_cleaning(config: SilverCleaningConfig, logger: logging.Logger) -> None:
    """Execute the DataCo Silver cleaning workflow."""
    spark = get_spark_session()

    logger.info("Starting DataCo Silver cleaning job.")
    logger.info("Bronze input path: %s", config.bronze_input_path)
    logger.info("Silver output path: %s", config.silver_output_path)
    logger.info("Quality report output path: %s", config.quality_report_output_path)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        bronze_df = read_bronze_delta(spark, config)
        logger.info("Bronze Delta loaded successfully with %d columns.", len(bronze_df.columns))

        bronze_df = canonicalize_bronze_column_names(bronze_df)
        logger.info("Bronze column names canonicalized for Silver compatibility.")

        validate_required_columns(bronze_df)
        logger.info("Required Bronze columns validated successfully.")

        cleaned_string_df = normalize_categorical_strings(nullify_blank_strings(bronze_df))
        silver_df = apply_silver_cleaning(bronze_df, config)
        logger.info("Silver cleaning transformations completed successfully.")

        write_delta(silver_df, config.silver_output_path, config)
        logger.info("Silver Delta write completed successfully.")

        metrics = build_quality_metrics(bronze_df, cleaned_string_df, silver_df, config)
        write_quality_report(spark, metrics, config)
        logger.info("Silver quality report written successfully.")

        validate_silver_output(spark, config)
        logger.info("Silver Delta validation completed successfully.")
        logger.info("DataCo Silver cleaning job completed successfully.")

    except Exception:
        logger.exception("Silver cleaning failed.")
        raise


def main() -> None:
    """Run the Silver cleaning job with the default project configuration."""
    logger = configure_logging()
    config = SilverCleaningConfig()
    run_silver_cleaning(config, logger)


if __name__ == "__main__":
    main()
