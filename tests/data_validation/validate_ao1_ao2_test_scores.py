"""Validate integrated AO1/AO2 held-out test score artifacts.

Run this script after `src/modeling/score_ao1_ao2_test_set.py` completes in
Databricks. It validates the Delta score table and lightweight metadata without
calculating final-test model performance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pyspark.sql.functions import col, count as spark_count, sum as spark_sum, when


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
SCORE_OUTPUT_PATH = os.getenv(
    "DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao1_ao2_test_scores",
)

REQUIRED_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    "ao2_chronological_row_number",
    "ao2_split_partition",
    "ao1_model_name",
    "ao1_selected_candidate",
    "ao1_scoring_mode",
    "ao1_predicted_late_delivery_probability",
    "ao1_decision_threshold",
    "ao1_high_risk_flag",
    "ao2_model_name",
    "ao2_selected_candidate",
    "ao2_scoring_mode",
    "ao2_predicted_order_profit",
    "ao3_order_value",
    "ao3_predicted_margin",
    "scoring_timestamp_utc",
}

FORBIDDEN_OUTPUT_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
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
        if (candidate / "models").exists() and (candidate / "src").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_AO2_TEST_SCORE_METADATA_PATH",
        str(
            REPO_ROOT
            / "models"
            / "ao3_integration"
            / "ao1_ao2_test_scores"
            / "ao1_ao2_test_score_metadata.json"
        ),
    )
)
SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO1_AO2_TEST_SCORE_SUMMARY_PATH",
        str(REPO_ROOT / "data" / "references" / "ao1_ao2_test_score_summary.csv"),
    )
)


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def read_json(path: Path) -> dict[str, Any]:
    """Read a local JSON artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing metadata JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """Run AO1/AO2 test score validation."""
    metadata = read_json(METADATA_PATH)
    assert SUMMARY_PATH.exists(), f"Missing scoring summary CSV: {SUMMARY_PATH}"

    assert metadata["issue"] == "#41"
    assert metadata["metadata_status"] == "runtime_scoring_completed"
    assert metadata["test_set_usage"]["used_for_prediction_only"] is True
    assert metadata["test_set_usage"]["used_for_training"] is False
    assert metadata["test_set_usage"]["used_for_model_selection"] is False
    assert metadata["test_set_usage"]["used_for_threshold_selection"] is False
    assert metadata["test_set_usage"]["used_for_performance_metrics"] is False
    assert metadata["ao1_threshold_reference"]["selected_threshold"] == 0.35

    spark = get_spark_session()
    score_df = spark.read.format("delta").load(SCORE_OUTPUT_PATH)

    missing_columns = sorted(REQUIRED_COLUMNS.difference(score_df.columns))
    assert not missing_columns, f"Missing score columns: {missing_columns}"

    forbidden_columns = sorted(FORBIDDEN_OUTPUT_COLUMNS.intersection(score_df.columns))
    assert not forbidden_columns, f"Forbidden final-test target columns found: {forbidden_columns}"

    row_count = score_df.count()
    assert row_count == metadata["summary"]["integrated_scored_rows"]
    assert row_count > 0

    partition_summary = score_df.groupBy("split_partition").agg(spark_count("*").alias("rows")).collect()
    observed_partitions = {row["split_partition"] for row in partition_summary}
    assert observed_partitions == {"test"}, f"Unexpected AO1 partitions: {observed_partitions}"

    ao2_partition_summary = score_df.groupBy("ao2_split_partition").agg(spark_count("*").alias("rows")).collect()
    observed_ao2_partitions = {row["ao2_split_partition"] for row in ao2_partition_summary}
    assert observed_ao2_partitions == {"test"}, f"Unexpected AO2 partitions: {observed_ao2_partitions}"

    quality_summary = score_df.select(
        spark_sum(
            when(col("ao1_predicted_late_delivery_probability").isNull(), 1).otherwise(0)
        ).alias("missing_ao1_probability"),
        spark_sum(
            when(col("ao2_predicted_order_profit").isNull(), 1).otherwise(0)
        ).alias("missing_ao2_prediction"),
        spark_sum(when(col("ao3_order_value").isNull(), 1).otherwise(0)).alias(
            "missing_ao3_order_value"
        ),
        spark_sum(
            when(
                (col("ao1_predicted_late_delivery_probability") < 0)
                | (col("ao1_predicted_late_delivery_probability") > 1),
                1,
            ).otherwise(0)
        ).alias("invalid_ao1_probability"),
        spark_sum(when(col("ao1_decision_threshold") != 0.35, 1).otherwise(0)).alias(
            "invalid_threshold"
        ),
    ).collect()[0].asDict()

    assert quality_summary["missing_ao1_probability"] == 0, quality_summary
    assert quality_summary["missing_ao2_prediction"] == 0, quality_summary
    assert quality_summary["missing_ao3_order_value"] == 0, quality_summary
    assert quality_summary["invalid_ao1_probability"] == 0, quality_summary
    assert quality_summary["invalid_threshold"] == 0, quality_summary

    print("AO1/AO2 held-out test score validation passed.")


if __name__ == "__main__":
    main()
