"""Export order-level logistics KPI audit data for Power BI."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_SOURCE_PATH = os.getenv(
    "DATACO_POWERBI_LOGISTICS_ORDER_KPI_DETAIL_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_logistics_order_kpi_detail",
)

EXPORT_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "shipping_date_DateOrders",
    "order_month_key",
    "order_year",
    "order_month",
    "market_normalized",
    "map_location_country",
    "map_location_region",
    "map_location_state",
    "shipping_mode_normalized",
    "shipping_speed_tier",
    "product_category_key",
    "product_department_key",
    "order_item_quantity",
    "item_net_sales_amount",
    "ao3_order_value",
    "Days_for_shipment_scheduled",
    "Days_for_shipping_real",
    "scheduled_shipping_days",
    "actual_shipping_lead_time",
    "delivery_delay_gap",
    "valid_delivery_metric_flag",
    "actual_on_time_delivery_flag",
    "actual_late_delivery_flag",
    "delivery_status_normalized",
    "ao1_predicted_late_delivery_probability",
    "ao1_expected_on_time_probability",
    "ao1_high_risk_flag",
    "risk_band",
    "risk_band_sort_order",
    "true_positive_flag",
    "false_positive_flag",
    "false_negative_flag",
    "true_negative_flag",
    "ao2_predicted_order_profit",
    "ao3_predicted_margin",
    "ao3_priority_segment",
    "ao3_action_queue_label",
    "ao3_action_queue_sort_order",
    "intervention_required_flag",
    "powerbi_logistics_order_kpi_detail_timestamp_utc",
)


@dataclass(frozen=True)
class LogisticsOrderKPIExportConfig:
    source_path: str = DEFAULT_SOURCE_PATH
    export_root: Path = Path(
        os.getenv("DATACO_POWERBI_EXPORT_ROOT", str(Path.cwd() / "dashboard/exports"))
    )
    export_file_name: str = "powerbi_logistics_order_kpi_detail.csv"
    manifest_file_name: str = "powerbi_logistics_order_kpi_detail_export_manifest.json"
    read_format: str = "delta"


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_logistics_order_kpi_detail_export")


def get_spark_session() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
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


def with_repo_defaults(config: LogisticsOrderKPIExportConfig) -> LogisticsOrderKPIExportConfig:
    repo_root = resolve_repo_root()
    return LogisticsOrderKPIExportConfig(
        source_path=config.source_path,
        export_root=Path(
            os.getenv("DATACO_POWERBI_EXPORT_ROOT", str(repo_root / "dashboard/exports"))
        ),
        export_file_name=config.export_file_name,
        manifest_file_name=config.manifest_file_name,
        read_format=config.read_format,
    )


def assert_required_columns(df: DataFrame, required_columns: tuple[str, ...], table_name: str) -> None:
    missing_columns = sorted(column for column in required_columns if column not in df.columns)
    if missing_columns:
        raise ValueError(f"{table_name} is missing required columns: {missing_columns}")


def write_single_csv(df: DataFrame, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_pdf = df.toPandas()
    output_pdf.to_csv(output_path, index=False, encoding="utf-8")
    return int(len(output_pdf))


def run_logistics_order_kpi_export(config: LogisticsOrderKPIExportConfig, logger: logging.Logger) -> None:
    config = with_repo_defaults(config)
    spark = get_spark_session()

    detail_df = spark.read.format(config.read_format).load(config.source_path)
    assert_required_columns(detail_df, EXPORT_COLUMNS, "Power BI logistics order KPI detail")
    export_df = detail_df.select(*(col(column) for column in EXPORT_COLUMNS))

    output_path = config.export_root / config.export_file_name
    row_count = write_single_csv(export_df, output_path)

    manifest = {
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "workflow": "powerbi_logistics_order_kpi_detail_export",
        "issue": "#152",
        "source": config.source_path,
        "output": str(output_path),
        "row_count": row_count,
        "type": "gold_delta_audit_export",
        "serving_grain": ["Order_Id", "Order_Item_Id"],
        "actual_delivery_fields_for_audit_only": True,
        "causal_intervention_impact_claimed": False,
    }
    (config.export_root / config.manifest_file_name).write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    logger.info("Exported logistics order KPI detail with %d rows.", row_count)


def main() -> None:
    run_logistics_order_kpi_export(LogisticsOrderKPIExportConfig(), configure_logging())


if __name__ == "__main__":
    main()
