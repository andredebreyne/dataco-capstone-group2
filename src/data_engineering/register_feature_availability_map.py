"""Register the DataCo feature availability map in Databricks.

This script loads the versioned CSV reference artifact from the repository,
validates its contract, copies the CSV to the project Unity Catalog Volume,
and writes a Delta version for Spark-based downstream consumption.
"""

from __future__ import annotations

import csv
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, lit
from pyspark.sql.types import StringType, StructField, StructType


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

REPO_FEATURE_MAP_PATH = Path("data/references/feature_availability_map.csv")

FEATURE_MAP_INPUT_PATH = Path(
    os.getenv("DATACO_FEATURE_AVAILABILITY_MAP_INPUT_PATH", str(REPO_FEATURE_MAP_PATH))
)

FEATURE_MAP_VOLUME_CSV_PATH = Path(
    os.getenv(
        "DATACO_FEATURE_AVAILABILITY_MAP_VOLUME_CSV_PATH",
        f"{VOLUME_ROOT}/references/feature_availability_map.csv",
    )
)

FEATURE_MAP_DELTA_OUTPUT_PATH = os.getenv(
    "DATACO_FEATURE_AVAILABILITY_MAP_DELTA_OUTPUT_PATH",
    f"{VOLUME_ROOT}/references/feature_availability_map",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")
EXPECTED_ROW_COUNT = 53

EXPECTED_COLUMNS = (
    "source_column",
    "silver_column",
    "semantic_group",
    "availability_timing",
    "ao1_policy",
    "ao2_policy",
    "dashboard_policy",
    "modeling_use",
    "rationale",
    "derived_feature_guidance",
    "related_document",
)

ALLOWED_AVAILABILITY_TIMING = {
    "order_creation",
    "before_dispatch",
    "after_shipment",
    "after_delivery",
    "after_order_review",
    "target_or_outcome",
    "sensitive_identifier",
    "descriptive_only",
}

ALLOWED_POLICY_VALUES = {"allowed", "review", "forbidden", "target"}
ALLOWED_DASHBOARD_POLICY_VALUES = {"allowed", "review", "forbidden"}
ALLOWED_MODELING_USE_VALUES = {
    "direct_candidate",
    "derived_only",
    "training_only_aggregate",
    "join_key_only",
    "review",
    "dashboard_only",
    "exclude",
}


@dataclass(frozen=True)
class FeatureAvailabilityMapConfig:
    """Configuration for registering the feature availability map."""

    input_csv_path: Path = FEATURE_MAP_INPUT_PATH
    volume_csv_path: Path = FEATURE_MAP_VOLUME_CSV_PATH
    delta_output_path: str = FEATURE_MAP_DELTA_OUTPUT_PATH
    write_format: str = "delta"
    write_mode: str = "overwrite"
    expected_row_count: int = EXPECTED_ROW_COUNT


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.feature_availability_map")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_volume_path(path: str, field_name: str) -> None:
    """Validate that a target path uses Unity Catalog Volumes."""
    if path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
        raise ValueError(
            f"{field_name} points to the disabled public DBFS root: {path}. "
            "Use Unity Catalog Volumes under /Volumes/workspace/default/raw_data/."
        )

    if not path.startswith("/Volumes/"):
        raise ValueError(
            f"{field_name} must use a Unity Catalog Volume path. Received: {path}"
        )


def validate_paths(config: FeatureAvailabilityMapConfig) -> None:
    """Validate configured source and target paths."""
    if not config.input_csv_path.exists():
        raise FileNotFoundError(
            f"Feature availability map CSV not found: {config.input_csv_path}. "
            "Run the script from the repository root or set "
            "DATACO_FEATURE_AVAILABILITY_MAP_INPUT_PATH."
        )

    validate_volume_path(str(config.volume_csv_path), "volume_csv_path")
    validate_volume_path(config.delta_output_path, "delta_output_path")


def read_feature_map_rows(config: FeatureAvailabilityMapConfig) -> list[dict[str, str]]:
    """Read the feature availability map CSV as dictionaries."""
    with config.input_csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    return rows


def validate_feature_map_rows(
    rows: list[dict[str, str]],
    config: FeatureAvailabilityMapConfig,
) -> None:
    """Validate the feature availability map schema and controlled values."""
    if len(rows) != config.expected_row_count:
        raise ValueError(
            f"Unexpected feature map row count. Expected {config.expected_row_count}, "
            f"found {len(rows)}."
        )

    if not rows:
        raise ValueError("Feature availability map is empty.")

    actual_columns = tuple(rows[0].keys())
    if actual_columns != EXPECTED_COLUMNS:
        raise ValueError(
            f"Unexpected feature map columns. Expected {EXPECTED_COLUMNS}, "
            f"found {actual_columns}."
        )

    source_columns = [row["source_column"] for row in rows]
    if len(set(source_columns)) != len(source_columns):
        duplicate_columns = sorted(
            {
                source_column
                for source_column in source_columns
                if source_columns.count(source_column) > 1
            }
        )
        raise ValueError(f"Duplicate source columns found: {duplicate_columns}")

    rows_with_blank_cells = [
        index
        for index, row in enumerate(rows, start=2)
        if any(value is None or value == "" for value in row.values())
    ]
    if rows_with_blank_cells:
        raise ValueError(
            "Feature availability map contains blank cells on CSV rows: "
            f"{rows_with_blank_cells}"
        )

    invalid_values: list[tuple[str, str, str]] = []

    for row in rows:
        source_column = row["source_column"]

        if row["availability_timing"] not in ALLOWED_AVAILABILITY_TIMING:
            invalid_values.append(
                (source_column, "availability_timing", row["availability_timing"])
            )

        if row["ao1_policy"] not in ALLOWED_POLICY_VALUES:
            invalid_values.append((source_column, "ao1_policy", row["ao1_policy"]))

        if row["ao2_policy"] not in ALLOWED_POLICY_VALUES:
            invalid_values.append((source_column, "ao2_policy", row["ao2_policy"]))

        if row["dashboard_policy"] not in ALLOWED_DASHBOARD_POLICY_VALUES:
            invalid_values.append(
                (source_column, "dashboard_policy", row["dashboard_policy"])
            )

        if row["modeling_use"] not in ALLOWED_MODELING_USE_VALUES:
            invalid_values.append((source_column, "modeling_use", row["modeling_use"]))

    if invalid_values:
        raise ValueError(f"Invalid controlled values found: {invalid_values}")


def copy_csv_to_volume(config: FeatureAvailabilityMapConfig) -> None:
    """Copy the reference CSV to the project Databricks Volume."""
    config.volume_csv_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config.input_csv_path, config.volume_csv_path)


def create_feature_map_dataframe(
    spark: SparkSession,
    rows: list[dict[str, str]],
    config: FeatureAvailabilityMapConfig,
) -> DataFrame:
    """Create a Spark DataFrame from validated feature map rows."""
    schema = StructType(
        [StructField(column_name, StringType(), nullable=False) for column_name in EXPECTED_COLUMNS]
    )

    ordered_rows = [
        tuple(row[column_name] for column_name in EXPECTED_COLUMNS)
        for row in rows
    ]

    return (
        spark.createDataFrame(ordered_rows, schema=schema)
        .withColumn("_registered_timestamp", current_timestamp())
        .withColumn("_source_file", lit(str(config.volume_csv_path)))
    )


def write_delta(df: DataFrame, config: FeatureAvailabilityMapConfig) -> None:
    """Write the feature availability map as a Delta reference table."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(config.delta_output_path)
    )


def validate_delta_output(
    spark: SparkSession,
    config: FeatureAvailabilityMapConfig,
) -> None:
    """Validate the written Delta feature availability map."""
    feature_map_df = spark.read.format(config.write_format).load(config.delta_output_path)
    row_count = feature_map_df.count()

    if row_count != config.expected_row_count:
        raise ValueError(
            f"Unexpected Delta feature map row count. "
            f"Expected {config.expected_row_count}, found {row_count}."
        )

    required_columns = set(EXPECTED_COLUMNS + ("_registered_timestamp", "_source_file"))
    missing_columns = sorted(required_columns.difference(feature_map_df.columns))

    if missing_columns:
        raise ValueError(
            f"Missing columns in Delta feature availability map: {missing_columns}"
        )


def run_feature_availability_map_registration(
    config: FeatureAvailabilityMapConfig,
    logger: logging.Logger,
) -> None:
    """Register the feature availability map CSV and Delta reference outputs."""
    spark = get_spark_session()

    logger.info("Starting feature availability map registration.")
    logger.info("Input CSV path: %s", config.input_csv_path)
    logger.info("Volume CSV path: %s", config.volume_csv_path)
    logger.info("Delta output path: %s", config.delta_output_path)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        rows = read_feature_map_rows(config)
        validate_feature_map_rows(rows, config)
        logger.info("Feature availability map CSV validation completed successfully.")

        copy_csv_to_volume(config)
        logger.info("Feature availability map CSV copied to Volume successfully.")

        feature_map_df = create_feature_map_dataframe(spark, rows, config)
        write_delta(feature_map_df, config)
        logger.info("Feature availability map Delta write completed successfully.")

        validate_delta_output(spark, config)
        logger.info("Feature availability map Delta validation completed successfully.")
        logger.info("Feature availability map registration completed successfully.")

    except Exception:
        logger.exception("Feature availability map registration failed.")
        raise


def main() -> None:
    """Run the feature availability map registration with default configuration."""
    logger = configure_logging()
    config = FeatureAvailabilityMapConfig()
    run_feature_availability_map_registration(config, logger)


if __name__ == "__main__":
    main()
