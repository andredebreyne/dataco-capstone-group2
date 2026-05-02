"""Bronze ingestion job for the DataCo Smart Supply Chain dataset.

This script ingests the raw DataCo CSV file from a Unity Catalog Volume into a
Delta-backed Bronze location. The Bronze layer preserves source values as
strings and adds minimal ingestion metadata for lineage.
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, lit


INPUT_PATH = "/Volumes/workspace/default/raw_data/DataCoSupplyChainDataset.csv"
OUTPUT_PATH = "/Volumes/workspace/default/raw_data/bronze/dataco_supply_chain"
SOURCE_FILE_NAME = "DataCoSupplyChainDataset.csv"
DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")


@dataclass(frozen=True)
class BronzeIngestionConfig:
    """Configuration for the Bronze ingestion job."""

    input_path: str = INPUT_PATH
    output_path: str = OUTPUT_PATH
    source_file_name: str = SOURCE_FILE_NAME
    read_format: str = "csv"
    write_format: str = "delta"
    write_mode: str = "overwrite"
    encoding: str = "iso-8859-1"


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


def add_lineage_columns(df: DataFrame, config: BronzeIngestionConfig) -> DataFrame:
    """Append ingestion metadata columns required for Bronze-layer lineage."""
    return (
        df.withColumn("_ingest_timestamp", current_timestamp())
        .withColumn("_source_file", lit(config.source_file_name))
    )


def clean_column_names(df: DataFrame) -> DataFrame:
    """Replace invalid Delta column-name characters with underscores."""
    cleaned_columns = [
        re.sub(r"[ ,;{}()\n\t=]", "_", column_name)
        for column_name in df.columns
    ]
    return df.toDF(*cleaned_columns)


def write_bronze_delta(df: DataFrame, config: BronzeIngestionConfig) -> None:
    """Write the Bronze DataFrame as Delta using the configured output mode."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .save(config.output_path)
    )


def run_bronze_ingestion(config: BronzeIngestionConfig, logger: logging.Logger) -> None:
    """Execute the DataCo Bronze ingestion workflow."""
    spark = get_spark_session()

    logger.info("Starting DataCo Bronze ingestion job.")
    logger.info("Input path: %s", config.input_path)
    logger.info("Output path: %s", config.output_path)
    logger.info("Read format: %s", config.read_format)
    logger.info("Write format: %s", config.write_format)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        raw_df = read_raw_csv(spark, config)
        logger.info("Raw CSV loaded successfully with %d columns.", len(raw_df.columns))

        cleaned_df = clean_column_names(raw_df)
        logger.info("Column names cleaned for Delta compatibility.")

        bronze_df = add_lineage_columns(cleaned_df, config)
        logger.info("Lineage columns appended: _ingest_timestamp, _source_file.")

        write_bronze_delta(bronze_df, config)
        logger.info("Bronze Delta write completed successfully.")
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
