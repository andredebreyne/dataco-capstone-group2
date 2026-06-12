"""Validate local Power BI dashboard export artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


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


REPO_ROOT = resolve_repo_root()
EXPORT_ROOT = Path(
    os.getenv("DATACO_POWERBI_EXPORT_ROOT", str(REPO_ROOT / "dashboard/exports"))
)

REQUIRED_EXPORTS = {
    "ao1_ao2_test_scores.csv",
    "ao3_risk_margin_segments.csv",
    "powerbi_geographic_summary.csv",
    "powerbi_logistics_kpi_summary.csv",
    "ao1_decision_threshold_policy.csv",
    "ao1_ao2_test_score_summary.csv",
    "ao3_risk_margin_matrix_policy.csv",
    "ao3_segment_summary.csv",
    "ao3_risk_margin_benchmark_segment_summary.csv",
    "ao3_risk_margin_benchmark_insights.csv",
    "ao1_model_validation_comparison.csv",
    "ao1_threshold_tradeoff_grid.csv",
    "ao1_confusion_matrix_by_threshold.csv",
    "ao2_model_validation_comparison.csv",
    "ao2_model_evaluation_metrics.csv",
    "powerbi_export_manifest.json",
}

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}

REQUIRED_SCORE_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "split_partition",
    "ao2_split_partition",
    "ao1_predicted_late_delivery_probability",
    "ao1_decision_threshold",
    "ao1_high_risk_flag",
    "ao2_predicted_order_profit",
    "ao3_order_value",
    "ao3_predicted_margin",
}

REQUIRED_AO3_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "ao1_predicted_late_delivery_probability",
    "ao1_high_risk_flag",
    "ao2_predicted_order_profit",
    "ao3_order_value",
    "ao3_predicted_margin",
    "ao3_high_risk_flag",
    "ao3_high_margin_flag",
    "ao3_priority_segment",
}

REQUIRED_GEOGRAPHIC_COLUMNS = {
    "map_location_label",
    "map_location_country",
    "map_location_region",
    "map_location_state",
    "map_latitude",
    "map_longitude",
    "geo_coordinates_available",
    "order_count",
    "order_item_count",
    "high_risk_order_count",
    "high_risk_order_rate",
    "avg_ao1_predicted_late_delivery_probability",
    "avg_ao2_predicted_order_profit",
    "avg_ao3_predicted_margin",
    "protect_high_value_at_risk_count",
    "expedite_selectively_count",
    "preserve_service_count",
    "standard_process_count",
    "requires_review_count",
}

REQUIRED_LOGISTICS_KPI_COLUMNS = {
    "order_month_key",
    "market_normalized",
    "map_location_country",
    "map_location_region",
    "shipping_mode_normalized",
    "shipping_speed_tier",
    "product_category_key",
    "product_department_key",
    "ao3_priority_segment",
    "ao3_action_queue_label",
    "risk_band",
    "order_count",
    "order_item_count",
    "valid_delivery_metric_count",
    "historical_on_time_count",
    "historical_late_count",
    "historical_otd_rate",
    "historical_late_delivery_rate",
    "expected_late_delivery_rate",
    "expected_otd_rate",
    "expected_otd_exposure_pp",
    "expected_late_order_equivalent_count",
    "expected_on_time_order_equivalent_count",
    "high_risk_order_count",
    "high_risk_delivery_exposure_rate",
    "intervention_required_count",
    "intervention_load_rate",
    "total_order_value",
    "total_predicted_profit",
}

DAX_SOURCE_SCHEMA_REQUIREMENTS = {
    "ao1_decision_threshold_policy.csv": {
        "selected_threshold",
        "validation_recall",
        "validation_precision",
        "validation_predicted_positive_rate",
    },
    "ao3_risk_margin_matrix_policy.csv": {
        "risk_cutoff",
        "margin_cutoff",
    },
    "ao3_segment_summary.csv": {
        "ao3_priority_segment",
        "row_count",
        "share_of_rows",
        "avg_ao1_predicted_late_delivery_probability",
        "avg_ao2_predicted_order_profit",
        "avg_ao3_predicted_margin",
    },
    "ao3_risk_margin_benchmark_segment_summary.csv": {
        "ao3_priority_segment",
        "row_count",
        "share_of_rows",
        "avg_ao1_predicted_late_delivery_probability",
        "avg_ao2_predicted_order_profit",
        "avg_ao3_predicted_margin",
    },
    "ao3_risk_margin_benchmark_insights.csv": {
        "metric_name",
        "metric_value",
        "decision_relevance",
    },
    "ao1_model_validation_comparison.csv": {
        "row_count",
        "roc_auc",
        "pr_auc",
        "recall",
        "precision",
    },
    "ao1_threshold_tradeoff_grid.csv": {
        "f1",
        "recall",
        "predicted_positive_rate",
    },
    "ao1_confusion_matrix_by_threshold.csv": {
        "false_positive",
        "false_negative",
        "true_positive",
        "true_negative",
    },
    "ao2_model_validation_comparison.csv": {
        "validation_rows",
        "rmse",
        "mae",
        "r2",
    },
    "ao2_model_evaluation_metrics.csv": {
        "wrong_profit_sign_share",
    },
}


def assert_required_columns(
    *,
    dataframe: pd.DataFrame,
    required_columns: set[str],
    file_name: str,
) -> None:
    """Assert that a Power BI export contains the columns used by DAX measures."""
    missing_columns = sorted(required_columns.difference(dataframe.columns))
    assert not missing_columns, f"{file_name} missing required columns: {missing_columns}"


def read_export_csv(file_name: str) -> pd.DataFrame:
    """Read a generated Power BI CSV export."""
    return pd.read_csv(EXPORT_ROOT / file_name)


def main() -> None:
    """Validate exported Power BI files."""
    missing_exports = sorted(
        file_name for file_name in REQUIRED_EXPORTS if not (EXPORT_ROOT / file_name).exists()
    )
    assert not missing_exports, f"Missing Power BI exports: {missing_exports}"

    manifest = json.loads((EXPORT_ROOT / "powerbi_export_manifest.json").read_text(encoding="utf-8"))
    assert manifest["export_purpose"] == "Power BI dashboard import layer"
    assert manifest["final_test_targets_used"] is False
    manifest_exports = {row["name"]: row for row in manifest["exports"]}
    assert "ao1_ao2_test_scores" in manifest_exports
    assert "ao3_risk_margin_segments" in manifest_exports
    assert "powerbi_geographic_summary" in manifest_exports
    assert "powerbi_logistics_kpi_summary" in manifest_exports

    score_df = read_export_csv("ao1_ao2_test_scores.csv")
    segment_df = read_export_csv("ao3_risk_margin_segments.csv")
    geographic_df = read_export_csv("powerbi_geographic_summary.csv")
    logistics_kpi_df = read_export_csv("powerbi_logistics_kpi_summary.csv")
    assert not score_df.empty, "AO1/AO2 score export must contain rows."
    assert not segment_df.empty, "AO3 segment export must contain rows."
    assert not geographic_df.empty, "Power BI geographic summary export must contain rows."
    assert not logistics_kpi_df.empty, "Power BI logistics KPI summary export must contain rows."

    forbidden_score_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(score_df.columns))
    forbidden_segment_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(segment_df.columns))
    forbidden_geographic_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(geographic_df.columns))
    forbidden_logistics_columns = sorted(
        FORBIDDEN_TARGET_COLUMNS.intersection(logistics_kpi_df.columns)
    )
    assert not forbidden_score_columns, f"Score export contains target columns: {forbidden_score_columns}"
    assert not forbidden_segment_columns, (
        f"Segment export contains target columns: {forbidden_segment_columns}"
    )
    assert not forbidden_geographic_columns, (
        f"Geographic export contains target columns: {forbidden_geographic_columns}"
    )
    assert not forbidden_logistics_columns, (
        f"Logistics KPI export contains target columns: {forbidden_logistics_columns}"
    )

    assert_required_columns(
        dataframe=score_df,
        required_columns=REQUIRED_SCORE_COLUMNS,
        file_name="ao1_ao2_test_scores.csv",
    )
    assert_required_columns(
        dataframe=segment_df,
        required_columns=REQUIRED_AO3_COLUMNS,
        file_name="ao3_risk_margin_segments.csv",
    )
    assert_required_columns(
        dataframe=geographic_df,
        required_columns=REQUIRED_GEOGRAPHIC_COLUMNS,
        file_name="powerbi_geographic_summary.csv",
    )
    assert_required_columns(
        dataframe=logistics_kpi_df,
        required_columns=REQUIRED_LOGISTICS_KPI_COLUMNS,
        file_name="powerbi_logistics_kpi_summary.csv",
    )

    assert segment_df["ao3_priority_segment"].notna().all(), "AO3 segment labels must not be null."
    assert segment_df["ao1_predicted_late_delivery_probability"].between(0, 1).all(), (
        "AO1 probabilities must be in [0, 1]."
    )
    assert geographic_df["high_risk_order_rate"].between(0, 1).all(), (
        "Geographic high-risk rates must be in [0, 1]."
    )
    assert geographic_df["map_location_label"].notna().all(), (
        "Geographic map labels must not be null."
    )
    for rate_column in [
        "historical_otd_rate",
        "historical_late_delivery_rate",
        "expected_late_delivery_rate",
        "expected_otd_rate",
        "high_risk_delivery_exposure_rate",
        "intervention_load_rate",
    ]:
        assert logistics_kpi_df[rate_column].dropna().between(0, 1).all(), (
            f"{rate_column} must be in [0, 1]."
        )
    assert (logistics_kpi_df["order_item_count"] > 0).all(), (
        "Logistics KPI summary grain must contain positive order-item counts."
    )

    for file_name, required_columns in DAX_SOURCE_SCHEMA_REQUIREMENTS.items():
        export_df = read_export_csv(file_name)
        assert_required_columns(
            dataframe=export_df,
            required_columns=required_columns,
            file_name=file_name,
        )

    print("Power BI Gold export validation passed.")


if __name__ == "__main__":
    main()
