"""Bronze ingestion job for the DataCo Smart Supply Chain dataset.

This script ingests the raw DataCo CSV file from a Unity Catalog Volume into a
Delta-backed Bronze location. The Bronze layer preserves source values as
strings and adds minimal ingestion metadata for lineage.
"""

from __future__ import annotations

import logging
import re
import sys
import os

from dataclasses import dataclass
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, lit


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

INPUT_PATH = os.getenv(
    "DATACO_RAW_INPUT_PATH",
    f"{VOLUME_ROOT}/DataCoSupplyChainDataset.csv",
)

OUTPUT_PATH = os.getenv(
    "DATACO_BRONZE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/bronze/dataco_supply_chain",
)

COLUMN_MAPPING_OUTPUT_PATH = os.getenv(
    "DATACO_COLUMN_MAPPING_OUTPUT_PATH",
    f"{VOLUME_ROOT}/bronze/dataco_supply_chain_column_mapping",
)

SOURCE_FILE_NAME = "DataCoSupplyChainDataset.csv"
DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")

EXPECTED_SOURCE_ROWS = 180_519
EXPECTED_SOURCE_COLUMNS = 53
LINEAGE_COLUMNS = ("_ingest_timestamp", "_source_file")

@dataclass(frozen=True)
class BronzeIngestionConfig:
    """Configuration for the Bronze ingestion job."""

    input_path: str = INPUT_PATH
    output_path: str = OUTPUT_PATH
    column_mapping_output_path: str = COLUMN_MAPPING_OUTPUT_PATH
    source_file_name: str = SOURCE_FILE_NAME
    read_format: str = "csv"
    write_format: str = "delta"
    write_mode: str = "overwrite"
    encoding: str = "iso-8859-1"
    expected_source_rows: int = EXPECTED_SOURCE_ROWS
    expected_source_columns: int = EXPECTED_SOURCE_COLUMNS


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.bronze_ingestion")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def read_raw_csv(spark: SparkSession, config: BronzeIngestionConfig) -> DataFrame:
    """Read the raw CSV dataset while preserving all source fields as strings."""
    return (
        spark.read.format(config.read_format)
        .option("header", "true")
        .option("encoding", config.encoding)
        .option("inferSchema", "false")
        .load(config.input_path)
    )


def validate_paths(config: BronzeIngestionConfig) -> None:
    """Validate that ingestion paths use Unity Catalog Volumes, not public DBFS."""
    configured_paths = {
        "input_path": config.input_path,
        "output_path": config.output_path,
        "column_mapping_output_path": config.column_mapping_output_path,
    }

    for field_name, path in configured_paths.items():
        if path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
            raise ValueError(
                f"{field_name} points to the disabled public DBFS root: {path}. "
                "Use Unity Catalog Volumes under /Volumes/workspace/default/raw_data/."
            )

    if not config.input_path.startswith("/Volumes/"):
        raise ValueError(
            f"input_path must use a Unity Catalog Volume path. Received: {config.input_path}"
        )

    if not config.output_path.startswith("/Volumes/"):
        raise ValueError(
            f"output_path must use a Unity Catalog Volume path. Received: {config.output_path}"
        )
    if not config.column_mapping_output_path.startswith("/Volumes/"):
        raise ValueError(
            "column_mapping_output_path must use a Unity Catalog Volume path. "
            f"Received: {config.column_mapping_output_path}"
        )

def add_lineage_columns(df: DataFrame, config: BronzeIngestionConfig) -> DataFrame:
    """Append ingestion metadata columns required for Bronze-layer lineage."""
    return (
        df.withColumn("_ingest_timestamp", current_timestamp())
        .withColumn("_source_file", lit(config.source_file_name))
    )


def sanitize_column_name(column_name: str) -> str:
    """Convert a raw source column name into a Delta-compatible Bronze name."""
    cleaned_name = column_name.strip()
    cleaned_name = re.sub(r"[ ,;{}()\n\t=]", "_", cleaned_name)
    cleaned_name = re.sub(r"_+", "_", cleaned_name)
    return cleaned_name.strip("_")


def build_column_mapping(source_columns: list[str]) -> list[tuple[int, str, str, bool]]:
    """Create an ordered mapping from raw source names to Bronze column names."""
    mapping = []

    for position, original_name in enumerate(source_columns, start=1):
        bronze_name = sanitize_column_name(original_name)
        mapping.append(
            (
                position,
                original_name,
                bronze_name,
                original_name != bronze_name,
            )
        )

    cleaned_names = [row[2] for row in mapping]

    if len(set(cleaned_names)) != len(cleaned_names):
        duplicate_names = sorted(
            {
                column_name
                for column_name in cleaned_names
                if cleaned_names.count(column_name) > 1
            }
        )
        raise ValueError(
            "Column-name cleaning created duplicate Bronze column names: "
            f"{duplicate_names}"
        )

    return mapping


def clean_column_names(
        df: DataFrame,
    ) -> tuple[DataFrame, list[tuple[int, str, str, bool]]]:
    """Replace invalid Delta column-name characters and return mapping metadata."""
    column_mapping = build_column_mapping(df.columns)
    cleaned_columns = [row[2] for row in column_mapping]
    cleaned_df = df.toDF(*cleaned_columns)
    return cleaned_df, column_mapping

def write_column_mapping(
        spark: SparkSession,
        column_mapping: list[tuple[int, str, str, bool]],
        config: BronzeIngestionConfig,
    ) -> None:
    """Write the raw-to-Bronze column mapping as a Delta reference table."""
    mapping_df = spark.createDataFrame(
        column_mapping,
        schema=(
            "ordinal_position INT, "
            "source_column_name STRING, "
            "bronze_column_name STRING, "
            "was_renamed BOOLEAN"
        ),
    )

    (
        mapping_df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(config.column_mapping_output_path)
    )

def write_bronze_delta(df: DataFrame, config: BronzeIngestionConfig) -> None:
    """Write the Bronze DataFrame as Delta using the configured output mode."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(config.output_path)
    )

def validate_bronze_output(
        spark: SparkSession,
        config: BronzeIngestionConfig,
    ) -> None:
    """Validate the written Bronze Delta dataset."""
    bronze_df = spark.read.format(config.write_format).load(config.output_path)

    row_count = bronze_df.count()
    if row_count != config.expected_source_rows:
        raise ValueError(
            f"Unexpected Bronze row count. "
            f"Expected {config.expected_source_rows}, found {row_count}."
        )

    missing_lineage_columns = [
        column_name
        for column_name in LINEAGE_COLUMNS
        if column_name not in bronze_df.columns
    ]

    if missing_lineage_columns:
        raise ValueError(
            f"Missing required lineage columns: {missing_lineage_columns}"
        )

    source_columns = [
        column_name
        for column_name in bronze_df.columns
        if column_name not in LINEAGE_COLUMNS
    ]

    if len(source_columns) != config.expected_source_columns:
        raise ValueError(
            f"Unexpected source column count. "
            f"Expected {config.expected_source_columns}, found {len(source_columns)}."
        )

    expected_total_columns = config.expected_source_columns + len(LINEAGE_COLUMNS)
    if len(bronze_df.columns) != expected_total_columns:
        raise ValueError(
            f"Unexpected total Bronze column count. "
            f"Expected {expected_total_columns}, found {len(bronze_df.columns)}."
        )

    non_string_source_columns = [
        field.name
        for field in bronze_df.schema.fields
        if field.name in source_columns and field.dataType.simpleString() != "string"
    ]

    if non_string_source_columns:
        raise ValueError(
            "Bronze source fields must remain strings. "
            f"Non-string source columns found: {non_string_source_columns}"
        )


def run_bronze_ingestion(config: BronzeIngestionConfig, logger: logging.Logger) -> None:
    """Execute the DataCo Bronze ingestion workflow.

    This workflow preserves raw source values as strings, applies only technical
    Bronze-layer transformations required for Delta compatibility, writes a
    raw-to-Bronze column mapping for traceability, appends lineage metadata, and
    validates the written Bronze Delta output.
    """
    spark = get_spark_session()

    logger.info("Starting DataCo Bronze ingestion job.")
    logger.info("Input path: %s", config.input_path)
    logger.info("Output path: %s", config.output_path)
    logger.info("Column mapping output path: %s", config.column_mapping_output_path)
    logger.info("Read format: %s", config.read_format)
    logger.info("Write format: %s", config.write_format)
    logger.info("Write mode: %s", config.write_mode)
    logger.info("Encoding: %s", config.encoding)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        raw_df = read_raw_csv(spark, config)
        logger.info(
            "Raw CSV loaded successfully with %d columns.",
            len(raw_df.columns),
        )

        cleaned_df, column_mapping = clean_column_names(raw_df)
        logger.info("Column names cleaned for Delta compatibility.")

        write_column_mapping(spark, column_mapping, config)
        logger.info(
            "Column mapping written successfully to %s.",
            config.column_mapping_output_path,
        )

        bronze_df = add_lineage_columns(cleaned_df, config)
        logger.info("Lineage columns appended: _ingest_timestamp, _source_file.")

        write_bronze_delta(bronze_df, config)
        logger.info("Bronze Delta write completed successfully.")

        validate_bronze_output(spark, config)
        logger.info("Bronze Delta validation completed successfully.")

        logger.info("DataCo Bronze ingestion job completed successfully.")

    except Exception:
        logger.exception("Bronze ingestion failed.")
        raise

def main() -> None:
    """Run the Bronze ingestion job with the default project configuration."""
    logger = configure_logging()
    config = BronzeIngestionConfig()
    run_bronze_ingestion(config, logger)


if __name__ == "__main__":
    main()
