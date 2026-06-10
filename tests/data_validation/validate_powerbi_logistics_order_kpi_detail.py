"""Validate Power BI logistics order KPI detail for Issue #152."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
LOGISTICS_ORDER_KPI_DETAIL_PATH = os.getenv(
    "DATACO_POWERBI_LOGISTICS_ORDER_KPI_DETAIL_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_logistics_order_kpi_detail",
)

REQUIRED_COLUMNS = {
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
}

APPROVED_RISK_BANDS = {"Low Risk", "Medium Risk", "High Risk"}
APPROVED_ACTION_LABELS = {
    "Protect First",
    "Review Selective Expedite",
    "Preserve Service",
    "Standard Process",
    "Review Score or Margin",
}
AUDIT_GRAIN = ["Order_Id", "Order_Item_Id"]
CRITICAL_GOVERNED_COLUMNS = [
    "ao1_predicted_late_delivery_probability",
    "ao1_high_risk_flag",
    "ao2_predicted_order_profit",
    "ao3_predicted_margin",
    "ao3_order_value",
    "ao3_priority_segment",
]


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
        "DATACO_POWERBI_LOGISTICS_ORDER_KPI_DETAIL_METADATA_PATH",
        str(REPO_ROOT / "models/dashboard/powerbi_logistics_order_kpi_detail_metadata.json"),
    )
)


def get_spark_session() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def main() -> None:
    spark = get_spark_session()
    detail_df = spark.read.format("delta").load(LOGISTICS_ORDER_KPI_DETAIL_PATH)

    row_count = detail_df.count()
    assert row_count > 0, "Power BI logistics order KPI detail must contain rows."

    missing_columns = sorted(REQUIRED_COLUMNS.difference(detail_df.columns))
    assert not missing_columns, f"Missing columns: {missing_columns}"

    duplicate_grain_rows = detail_df.groupBy(*AUDIT_GRAIN).count().filter(col("count") > 1).count()
    assert duplicate_grain_rows == 0, f"Duplicated audit grain rows: {duplicate_grain_rows}"

    required_non_null_columns = AUDIT_GRAIN + [
        "order_month_key",
        "shipping_mode_normalized",
        "product_category_key",
        "risk_band",
        "ao3_action_queue_label",
        *CRITICAL_GOVERNED_COLUMNS,
    ]
    for column_name in required_non_null_columns:
        null_count = detail_df.filter(col(column_name).isNull()).count()
        assert null_count == 0, f"{column_name} contains null rows: {null_count}"

    invalid_risk_rows = detail_df.filter(~col("risk_band").isin(*APPROVED_RISK_BANDS)).count()
    assert invalid_risk_rows == 0, f"Invalid risk band rows: {invalid_risk_rows}"

    invalid_action_rows = detail_df.filter(~col("ao3_action_queue_label").isin(*APPROVED_ACTION_LABELS)).count()
    assert invalid_action_rows == 0, f"Invalid action queue rows: {invalid_action_rows}"

    for column_name in ["ao1_predicted_late_delivery_probability", "ao1_expected_on_time_probability"]:
        invalid_probability_count = detail_df.filter(
            col(column_name).isNotNull() & ~col(column_name).between(0, 1)
        ).count()
        assert invalid_probability_count == 0, f"{column_name} has invalid probability rows: {invalid_probability_count}"

    flag_columns = [
        "valid_delivery_metric_flag",
        "actual_on_time_delivery_flag",
        "actual_late_delivery_flag",
        "ao1_high_risk_flag",
        "true_positive_flag",
        "false_positive_flag",
        "false_negative_flag",
        "true_negative_flag",
        "intervention_required_flag",
    ]
    for column_name in flag_columns:
        invalid_flag_count = detail_df.filter(~col(column_name).isin(0, 1)).count()
        assert invalid_flag_count == 0, f"{column_name} has non-binary rows: {invalid_flag_count}"

    invalid_outcome_flags = detail_df.filter(
        (col("actual_on_time_delivery_flag") + col("actual_late_delivery_flag"))
        != col("valid_delivery_metric_flag")
    ).count()
    assert invalid_outcome_flags == 0, f"Invalid outcome flag rows: {invalid_outcome_flags}"

    invalid_classification_flags = detail_df.filter(
        (
            col("true_positive_flag")
            + col("false_positive_flag")
            + col("false_negative_flag")
            + col("true_negative_flag")
        )
        != col("valid_delivery_metric_flag")
    ).count()
    assert invalid_classification_flags == 0, f"Invalid classification flag rows: {invalid_classification_flags}"

    assert METADATA_PATH.exists(), f"Missing metadata: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["workflow"] == "powerbi_logistics_order_kpi_detail"
    assert metadata["issue"] == "#152"
    assert metadata["output_path"] == LOGISTICS_ORDER_KPI_DETAIL_PATH
    assert metadata["row_count"] == row_count
    assert metadata["serving_grain"] == AUDIT_GRAIN
    assert metadata["ao1_target_interpretation"] == "risk of late delivery"
    assert metadata["actual_outcomes_exposed_for_audit_only"] is True
    assert metadata["actual_outcomes_used_as_model_predictors"] is False
    assert metadata["predictive_exposure_uses_governed_ao1_ao2_ao3_outputs"] is True
    assert metadata["causal_intervention_impact_claimed"] is False
    assert metadata["official_ao1_ao2_ao3_policy_changed"] is False

    print("Power BI logistics order KPI detail validation passed.")


if __name__ == "__main__":
    main()
