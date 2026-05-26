"""Validate AO3 risk-margin segment assignment artifacts for Issue #42."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col


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

REQUIRED_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "split_partition",
    "ao2_split_partition",
    "ao1_predicted_late_delivery_probability",
    "ao1_high_risk_flag",
    "ao1_decision_threshold",
    "ao2_predicted_order_profit",
    "ao3_order_value",
    "ao3_predicted_margin",
    "ao3_policy_name",
    "ao3_risk_cutoff",
    "ao3_margin_cutoff",
    "ao3_high_risk_flag",
    "ao3_high_margin_flag",
    "ao3_priority_segment",
    "ao3_segment_assignment_timestamp_utc",
}

VALID_SEGMENTS = {
    "protect_high_value_at_risk",
    "expedite_selectively",
    "preserve_service",
    "standard_process",
    "requires_score_review",
    "requires_margin_review",
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
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO3_SEGMENT_METADATA_PATH",
        str(
            REPO_ROOT
            / "models/ao3_integration/risk_margin_segments/ao3_segment_assignment_metadata.json"
        ),
    )
)
SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO3_SEGMENT_SUMMARY_PATH",
        str(REPO_ROOT / "data/references/ao3_segment_summary.csv"),
    )
)
POLICY_PATH = Path(
    os.getenv(
        "DATACO_AO3_RISK_MARGIN_POLICY_PATH",
        str(REPO_ROOT / "data/references/ao3_risk_margin_matrix_policy.csv"),
    )
)


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def main() -> None:
    """Run AO3 risk-margin segment validation."""
    assert POLICY_PATH.exists(), f"Missing AO3 policy CSV: {POLICY_PATH}"
    assert METADATA_PATH.exists(), f"Missing AO3 segment metadata: {METADATA_PATH}"
    assert SUMMARY_PATH.exists(), f"Missing AO3 segment summary CSV: {SUMMARY_PATH}"

    spark = get_spark_session()
    segment_df = spark.read.format("delta").load(SEGMENT_PATH)
    row_count = segment_df.count()
    assert row_count > 0, "AO3 segment table must contain rows."

    missing_columns = sorted(REQUIRED_COLUMNS.difference(segment_df.columns))
    assert not missing_columns, f"AO3 segment table missing columns: {missing_columns}"

    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(segment_df.columns))
    assert not forbidden_columns, f"AO3 output contains forbidden target columns: {forbidden_columns}"

    non_test_count = segment_df.filter(
        (col("split_partition") != "test") | (col("ao2_split_partition") != "test")
    ).count()
    assert non_test_count == 0, f"AO3 output contains non-test rows: {non_test_count}"

    invalid_segment_count = segment_df.filter(~col("ao3_priority_segment").isin(*VALID_SEGMENTS)).count()
    assert invalid_segment_count == 0, f"Invalid AO3 segment labels found: {invalid_segment_count}"

    null_segment_count = segment_df.filter(col("ao3_priority_segment").isNull()).count()
    assert null_segment_count == 0, f"Null AO3 segment labels found: {null_segment_count}"

    bad_probability_count = segment_df.filter(
        (col("ao1_predicted_late_delivery_probability") < 0)
        | (col("ao1_predicted_late_delivery_probability") > 1)
    ).count()
    assert bad_probability_count == 0, f"AO1 probabilities outside [0, 1]: {bad_probability_count}"

    threshold_mismatch_count = segment_df.filter(col("ao3_risk_cutoff") != col("ao1_decision_threshold")).count()
    assert threshold_mismatch_count == 0, (
        f"AO3 risk cutoff differs from AO1 threshold on {threshold_mismatch_count} rows."
    )

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["issue"] == "#42"
    assert metadata["workflow"] == "ao3_risk_margin_segment_assignment"
    assert metadata["row_count"] == row_count
    assert metadata["final_test_targets_used_for_assignment"] is False
    assert metadata["performance_metrics_calculated"] is False

    summary_df = pd.read_csv(SUMMARY_PATH)
    assert not summary_df.empty, "AO3 segment summary must contain rows."
    assert int(summary_df["row_count"].sum()) == row_count, (
        "AO3 segment summary row count does not match Delta output."
    )
    summary_segments = set(summary_df["ao3_priority_segment"].astype(str))
    assert summary_segments.issubset(VALID_SEGMENTS), (
        f"Summary contains invalid segments: {sorted(summary_segments.difference(VALID_SEGMENTS))}"
    )

    print("AO3 risk-margin segment validation passed.")


if __name__ == "__main__":
    main()
