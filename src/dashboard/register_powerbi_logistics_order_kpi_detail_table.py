"""Register the logistics order KPI detail table for Power BI in Databricks SQL."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_CATALOG = os.getenv("DATACO_POWERBI_SERVING_CATALOG", "workspace")
DEFAULT_SCHEMA = os.getenv("DATACO_POWERBI_SERVING_SCHEMA", "default")
DEFAULT_SOURCE_PATH = os.getenv(
    "DATACO_POWERBI_LOGISTICS_ORDER_KPI_DETAIL_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_logistics_order_kpi_detail",
)
WORKFLOW_NAME = "powerbi_logistics_order_kpi_detail_registration"


@dataclass(frozen=True)
class LogisticsOrderKPIRegistrationConfig:
    catalog: str = DEFAULT_CATALOG
    schema: str = DEFAULT_SCHEMA
    source_path: str = DEFAULT_SOURCE_PATH
    table_name: str = "powerbi_logistics_order_kpi_detail"
    manifest_table_name: str = "powerbi_logistics_order_kpi_detail_manifest"
    read_format: str = "delta"


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_logistics_order_kpi_detail_registration")


def get_spark_session() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def full_table_name(config: LogisticsOrderKPIRegistrationConfig, table_name: str) -> str:
    return f"{config.catalog}.{config.schema}.{table_name}"


def run_registration(config: LogisticsOrderKPIRegistrationConfig, logger: logging.Logger) -> None:
    spark = get_spark_session()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{config.schema}")

    logger.info("Registering logistics order KPI detail for Power BI.")
    logger.info("Source path: %s", config.source_path)
    logger.info("Target table: %s", full_table_name(config, config.table_name))

    detail_df = spark.read.format(config.read_format).load(config.source_path)
    target_table = full_table_name(config, config.table_name)
    (
        detail_df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table)
    )

    written_df = spark.table(target_table)
    manifest = {
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_name": WORKFLOW_NAME,
        "issue": "#152",
        "serving_catalog": config.catalog,
        "serving_schema": config.schema,
        "target_table": target_table,
        "source_path": config.source_path,
        "row_count": int(written_df.count()),
        "column_count": len(written_df.columns),
        "artifact_category": "gold_delta_audit_export",
        "serving_grain": ["Order_Id", "Order_Item_Id"],
        "actual_delivery_fields_for_audit_only": True,
        "causal_intervention_impact_claimed": False,
    }
    manifest_df = spark.createDataFrame([manifest])
    manifest_table = full_table_name(config, config.manifest_table_name)
    (
        manifest_df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(manifest_table)
    )

    logger.info("Registered %s with %d rows.", target_table, manifest["row_count"])
    logger.info("Wrote manifest table: %s", manifest_table)


def main() -> None:
    run_registration(LogisticsOrderKPIRegistrationConfig(), configure_logging())


if __name__ == "__main__":
    main()
