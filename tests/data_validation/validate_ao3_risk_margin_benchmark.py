"""Validate AO3 risk-margin benchmark artifacts for Issue #43."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
SEGMENT_PATH = os.getenv(
    "DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments",
)

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}

REQUIRED_SEGMENT_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "split_partition",
    "ao2_split_partition",
    "ao1_predicted_late_delivery_probability",
    "ao2_predicted_order_profit",
    "ao3_predicted_margin",
    "ao3_high_risk_flag",
    "ao3_high_margin_flag",
    "ao3_priority_segment",
}

VALID_SEGMENTS = {
    "protect_high_value_at_risk",
    "expedite_selectively",
    "preserve_service",
    "standard_process",
    "requires_score_review",
    "requires_margin_review",
}

REQUIRED_INSIGHT_METRICS = {
    "total_scored_orders",
    "high_risk_orders",
    "high_risk_share_high_margin",
    "high_risk_share_low_margin",
    "high_margin_orders",
    "high_margin_share_high_risk",
    "high_margin_share_low_risk",
    "h3_support_statement",
}


def resolve_repo_root() -> Path:
    """Resolve repository root for local artifact paths."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]
    current_path = Path.cwd().resolve()
    for candidate in (current_path, *current_path.parents):
        if (candidate / "src").exists() and (candidate / "data").exists():
            return candidate
    return current_path


REPO_ROOT = resolve_repo_root()
SEGMENT_SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO3_BENCHMARK_SEGMENT_SUMMARY_PATH",
        str(REPO_ROOT / "data/references/ao3_risk_margin_benchmark_segment_summary.csv"),
    )
)
CROSSWALK_PATH = Path(
    os.getenv(
        "DATACO_AO3_BENCHMARK_CROSSWALK_PATH",
        str(REPO_ROOT / "data/references/ao3_risk_margin_benchmark_crosswalk.csv"),
    )
)
INSIGHT_PATH = Path(
    os.getenv(
        "DATACO_AO3_BENCHMARK_INSIGHT_PATH",
        str(REPO_ROOT / "data/references/ao3_risk_margin_benchmark_insights.csv"),
    )
)
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO3_BENCHMARK_METADATA_PATH",
        str(
            REPO_ROOT
            / "models/ao3_integration/risk_margin_benchmark/ao3_risk_margin_benchmark_metadata.json"
        ),
    )
)


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def assert_file_exists(path: Path) -> None:
    """Assert an expected benchmark artifact exists."""
    assert path.exists(), f"Missing AO3 benchmark artifact: {path}"


def main() -> None:
    """Run AO3 risk-margin benchmark validation."""
    for path in (SEGMENT_SUMMARY_PATH, CROSSWALK_PATH, INSIGHT_PATH, METADATA_PATH):
        assert_file_exists(path)

    spark = get_spark_session()
    segment_df = spark.read.format("delta").load(SEGMENT_PATH)
    row_count = segment_df.count()
    assert row_count > 0, "AO3 benchmark source table must contain rows."

    missing_columns = sorted(REQUIRED_SEGMENT_COLUMNS.difference(segment_df.columns))
    assert not missing_columns, f"AO3 benchmark source missing columns: {missing_columns}"

    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(segment_df.columns))
    assert not forbidden_columns, f"AO3 benchmark source contains target columns: {forbidden_columns}"

    non_test_count = segment_df.filter(
        (col("split_partition") != lit("test")) | (col("ao2_split_partition") != lit("test"))
    ).count()
    assert non_test_count == 0, f"AO3 benchmark source contains non-test rows: {non_test_count}"

    invalid_segment_count = segment_df.filter(~col("ao3_priority_segment").isin(*VALID_SEGMENTS)).count()
    assert invalid_segment_count == 0, f"AO3 benchmark source has invalid segments: {invalid_segment_count}"

    segment_summary_df = pd.read_csv(SEGMENT_SUMMARY_PATH)
    crosswalk_df = pd.read_csv(CROSSWALK_PATH)
    insight_df = pd.read_csv(INSIGHT_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert not segment_summary_df.empty, "AO3 benchmark segment summary must not be empty."
    assert int(segment_summary_df["row_count"].sum()) == row_count, (
        "AO3 benchmark segment summary row count does not match source table."
    )
    summary_segments = set(segment_summary_df["ao3_priority_segment"].astype(str))
    assert summary_segments == VALID_SEGMENTS, (
        f"AO3 benchmark segment summary must include all valid segments; found {sorted(summary_segments)}."
    )

    assert not crosswalk_df.empty, "AO3 benchmark crosswalk must not be empty."
    required_signals = {"risk_only", "margin_only"}
    crosswalk_signals = set(crosswalk_df["priority_signal"].astype(str))
    assert required_signals.issubset(crosswalk_signals), (
        f"AO3 benchmark crosswalk missing signals: {sorted(required_signals.difference(crosswalk_signals))}"
    )
    for signal in required_signals:
        signal_count = int(crosswalk_df.loc[crosswalk_df["priority_signal"] == signal, "row_count"].sum())
        assert signal_count == row_count, (
            f"AO3 benchmark crosswalk count for {signal} does not match source table."
        )

    assert not insight_df.empty, "AO3 benchmark insights must not be empty."
    insight_metrics = set(insight_df["metric_name"].astype(str))
    missing_metrics = sorted(REQUIRED_INSIGHT_METRICS.difference(insight_metrics))
    assert not missing_metrics, f"AO3 benchmark insights missing metrics: {missing_metrics}"

    total_metric = insight_df.loc[insight_df["metric_name"] == "total_scored_orders", "metric_value"].iloc[0]
    assert int(float(total_metric)) == row_count, "AO3 benchmark total_scored_orders mismatch."

    assert metadata["issue"] == "#43"
    assert metadata["workflow"] == "ao3_risk_margin_framework_benchmark"
    assert metadata["row_count"] == row_count
    assert metadata["same_held_out_scored_data_as_ao3"] is True
    assert metadata["final_test_targets_used_for_benchmark"] is False
    assert metadata["performance_metrics_calculated"] is False
    assert set(metadata["comparison_signals"]) == {"ao3_combined", "risk_only", "margin_only"}

    print("AO3 risk-margin benchmark validation passed.")


if __name__ == "__main__":
    main()
