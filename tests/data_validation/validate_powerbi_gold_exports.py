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

    score_df = pd.read_csv(EXPORT_ROOT / "ao1_ao2_test_scores.csv")
    segment_df = pd.read_csv(EXPORT_ROOT / "ao3_risk_margin_segments.csv")
    assert not score_df.empty, "AO1/AO2 score export must contain rows."
    assert not segment_df.empty, "AO3 segment export must contain rows."

    forbidden_score_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(score_df.columns))
    forbidden_segment_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(segment_df.columns))
    assert not forbidden_score_columns, f"Score export contains target columns: {forbidden_score_columns}"
    assert not forbidden_segment_columns, (
        f"Segment export contains target columns: {forbidden_segment_columns}"
    )

    missing_ao3_columns = sorted(REQUIRED_AO3_COLUMNS.difference(segment_df.columns))
    assert not missing_ao3_columns, f"AO3 segment export missing columns: {missing_ao3_columns}"

    assert segment_df["ao3_priority_segment"].notna().all(), "AO3 segment labels must not be null."
    assert segment_df["ao1_predicted_late_delivery_probability"].between(0, 1).all(), (
        "AO1 probabilities must be in [0, 1]."
    )

    print("Power BI Gold export validation passed.")


if __name__ == "__main__":
    main()
