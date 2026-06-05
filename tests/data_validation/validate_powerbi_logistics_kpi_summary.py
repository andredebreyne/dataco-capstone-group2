"""Validate Power BI logistics KPI risk exposure summary for Issue #150."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
LOGISTICS_KPI_SUMMARY_PATH = os.getenv(
    "DATACO_POWERBI_LOGISTICS_KPI_SUMMARY_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_logistics_kpi_summary",
)

REQUIRED_COLUMNS = {
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
    "ao3_priority_segment",
    "ao3_action_queue_label",
    "ao3_action_queue_sort_order",
    "risk_band",
    "risk_band_sort_order",
    "order_count",
    "order_item_count",
    "units_ordered",
    "total_sales_amount",
    "total_order_value",
    "valid_delivery_metric_count",
    "historical_on_time_count",
    "historical_late_count",
    "historical_otd_rate",
    "historical_late_delivery_rate",
    "avg_scheduled_shipping_days",
    "avg_actual_shipping_days",
    "avg_delivery_delay_gap",
    "expected_late_delivery_rate",
    "expected_otd_rate",
    "expected_otd_exposure_pp",
    "expected_late_order_equivalent_count",
    "high_risk_order_count",
    "high_risk_delivery_exposure_rate",
    "service_protection_queue_count",
    "selective_expedite_review_count",
    "preserve_service_queue_count",
    "standard_process_queue_count",
    "intervention_required_count",
    "intervention_load_rate",
    "avg_predicted_order_profit",
    "avg_predicted_margin",
    "total_predicted_profit",
    "powerbi_logistics_kpi_summary_timestamp_utc",
}

RAW_OUTCOME_COLUMNS_NOT_EXPOSED = {
    "Days_for_shipping_real",
    "Delivery_Status",
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Benefit_per_order",
    "Order_Item_Profit_Ratio",
}

APPROVED_RISK_BANDS = {"Low Risk", "Medium Risk", "High Risk"}
APPROVED_ACTION_LABELS = {
    "Protect First",
    "Review Selective Expedite",
    "Preserve Service",
    "Standard Process",
    "Review Score or Margin",
}


def resolve_repo_root() -> Path:
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]
    return Path.cwd().resolve()


REPO_ROOT = resolve_repo_root()
METADATA_PATH = Path(
    os.getenv(
        "DATACO_POWERBI_LOGISTICS_KPI_SUMMARY_METADATA_PATH",
        str(REPO_ROOT / "models/dashboard/powerbi_logistics_kpi_summary_metadata.json"),
    )
)


def get_spark_session() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def main() -> None:
    spark = get_spark_session()
    summary_df = spark.read.format("delta").load(LOGISTICS_KPI_SUMMARY_PATH)

    row_count = summary_df.count()
    assert row_count > 0, "Power BI logistics KPI summary must contain rows."

    missing_columns = sorted(REQUIRED_COLUMNS.difference(summary_df.columns))
    assert not missing_columns, f"Missing columns: {missing_columns}"

    exposed_columns = sorted(RAW_OUTCOME_COLUMNS_NOT_EXPOSED.intersection(summary_df.columns))
    assert not exposed_columns, f"Raw outcome or target columns exposed: {exposed_columns}"

    for column_name in [
        "order_month_key",
        "shipping_mode_normalized",
        "product_category_key",
        "ao3_priority_segment",
        "ao3_action_queue_label",
        "risk_band",
    ]:
        null_count = summary_df.filter(col(column_name).isNull()).count()
        assert null_count == 0, f"{column_name} contains null rows: {null_count}"

    invalid_risk_rows = summary_df.filter(~col("risk_band").isin(*APPROVED_RISK_BANDS)).count()
    assert invalid_risk_rows == 0, f"Invalid risk band rows: {invalid_risk_rows}"

    invalid_action_rows = summary_df.filter(~col("ao3_action_queue_label").isin(*APPROVED_ACTION_LABELS)).count()
    assert invalid_action_rows == 0, f"Invalid action queue rows: {invalid_action_rows}"

    non_negative_columns = [
        "order_count",
        "order_item_count",
        "units_ordered",
        "total_sales_amount",
        "total_order_value",
        "valid_delivery_metric_count",
        "historical_on_time_count",
        "historical_late_count",
        "expected_late_order_equivalent_count",
        "high_risk_order_count",
        "service_protection_queue_count",
        "selective_expedite_review_count",
        "preserve_service_queue_count",
        "standard_process_queue_count",
        "intervention_required_count",
    ]
    for column_name in non_negative_columns:
        negative_count = summary_df.filter(col(column_name) < 0).count()
        assert negative_count == 0, f"{column_name} has negative rows: {negative_count}"

    rate_columns = [
        "historical_otd_rate",
        "historical_late_delivery_rate",
        "expected_late_delivery_rate",
        "expected_otd_rate",
        "high_risk_delivery_exposure_rate",
        "intervention_load_rate",
    ]
    for column_name in rate_columns:
        invalid_rate_count = summary_df.filter(
            col(column_name).isNotNull() & ~col(column_name).between(0, 1)
        ).count()
        assert invalid_rate_count == 0, f"{column_name} has invalid rate rows: {invalid_rate_count}"

    total_order_items = summary_df.agg(spark_sum("order_item_count").alias("total")).collect()[0]["total"]
    assert total_order_items and int(total_order_items) > 0

    assert METADATA_PATH.exists(), f"Missing metadata: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["workflow"] == "powerbi_logistics_kpi_summary"
    assert metadata["issue"] == "#150"
    assert metadata["output_path"] == LOGISTICS_KPI_SUMMARY_PATH
    assert metadata["row_count"] == row_count
    assert metadata["historical_kpi_fields_use_post_delivery_outcomes"] is True
    assert metadata["predictive_exposure_uses_governed_ao1_ao2_ao3_outputs"] is True
    assert metadata["causal_intervention_impact_claimed"] is False
    assert metadata["official_ao1_ao2_ao3_policy_changed"] is False

    print("Power BI logistics KPI summary validation passed.")


if __name__ == "__main__":
    main()
