"""Register the granular geographic segment summary in Databricks SQL.

This scoped registration supports Issue #145 without modifying the broad serving
layer registry. It publishes the enriched P04 geography artifact as a managed
Power BI serving table.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_CATALOG = os.getenv("DATACO_POWERBI_SERVING_CATALOG", "workspace")
DEFAULT_SCHEMA = os.getenv("DATACO_POWERBI_SERVING_SCHEMA", "default")
DEFAULT_GEOGRAPHIC_SEGMENT_SUMMARY_PATH = os.getenv(
    "DATACO_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_geographic_segment_summary",
)
WORKFLOW_NAME = "powerbi_geographic_segment_serving_registration"

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}

REQUIRED_COLUMNS = (
    "map_location_country",
    "map_location_region",
    "map_location_state",
    "order_date_key",
    "order_week_key",
    "order_month_key",
    "ao3_priority_segment",
    "ao1_high_risk_flag",
    "ao2_expected_profit_band",
    "order_item_count",
    "high_risk_order_rate",
    "total_order_value",
)


@dataclass(frozen=True)
class PowerBIGeographicSegmentServingConfig:
    """Configuration for scoped P04 geographic segment serving registration."""

    catalog: str = DEFAULT_CATALOG
    schema: str = DEFAULT_SCHEMA
    source_path: str = DEFAULT_GEOGRAPHIC_SEGMENT_SUMMARY_PATH
    table_name: str = "powerbi_geographic_segment_summary"
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_POWERBI_GEOGRAPHIC_SEGMENT_SERVING_METADATA_PATH",
            str(Path.cwd() / "models/dashboard/powerbi_geographic_segment_serving_metadata.json"),
        )
    )
    read_format: str = "delta"


def configure_logging() -> logging.Logger:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_geographic_segment_registration")


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
    """Resolve repository root for local and Databricks execution."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]
    current_path = Path.cwd().resolve()
    for candidate in (current_path, *current_path.parents):
        if (candidate / "src").exists() and (candidate / "dashboard").exists():
            return candidate
    return current_path


def with_repo_defaults(
    config: PowerBIGeographicSegmentServingConfig,
) -> PowerBIGeographicSegmentServingConfig:
    """Use repository-root metadata defaults when environment overrides are absent."""
    repo_root = resolve_repo_root()
    return PowerBIGeographicSegmentServingConfig(
        catalog=config.catalog,
        schema=config.schema,
        source_path=config.source_path,
        table_name=config.table_name,
        metadata_output_path=Path(
            os.getenv(
                "DATACO_POWERBI_GEOGRAPHIC_SEGMENT_SERVING_METADATA_PATH",
                str(repo_root / "models/dashboard/powerbi_geographic_segment_serving_metadata.json"),
            )
        ),
        read_format=config.read_format,
    )


def full_table_name(config: PowerBIGeographicSegmentServingConfig) -> str:
    """Return fully qualified Databricks table name."""
    return f"{config.catalog}.{config.schema}.{config.table_name}"


def assert_required_columns(df: DataFrame) -> None:
    """Validate required serving columns."""
    missing_columns = sorted(column for column in REQUIRED_COLUMNS if column not in df.columns)
    if missing_columns:
        raise ValueError(f"Power BI geographic segment serving table missing columns: {missing_columns}")


def assert_no_forbidden_targets(df: DataFrame) -> None:
    """Prevent target and realized-outcome fields from entering serving tables."""
    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(df.columns))
    if forbidden_columns:
        raise ValueError(f"Power BI geographic segment table contains forbidden columns: {forbidden_columns}")


def run_powerbi_geographic_segment_serving_registration(
    config: PowerBIGeographicSegmentServingConfig,
    logger: logging.Logger,
) -> None:
    """Publish the geographic segment summary as a managed Databricks SQL table."""
    config = with_repo_defaults(config)
    spark = get_spark_session()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{config.schema}")

    logger.info("Starting geographic segment serving registration.")
    logger.info("Source Delta path: %s", config.source_path)
    logger.info("Target table: %s", full_table_name(config))

    source_df = spark.read.format(config.read_format).load(config.source_path)
    assert_required_columns(source_df)
    assert_no_forbidden_targets(source_df)

    target_table = full_table_name(config)
    (
        source_df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table)
    )

    written_df = spark.table(target_table)
    metadata = {
        "workflow_name": WORKFLOW_NAME,
        "issue": "#145",
        "source_path": config.source_path,
        "target_table": target_table,
        "row_count": int(written_df.count()),
        "column_count": len(written_df.columns),
        "target_or_outcome_columns_used": False,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.metadata_output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info("Published %s with %d rows.", target_table, metadata["row_count"])
    logger.info("Wrote serving metadata: %s", config.metadata_output_path)


def main() -> None:
    """Run the scoped geographic segment serving registration."""
    run_powerbi_geographic_segment_serving_registration(
        PowerBIGeographicSegmentServingConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
