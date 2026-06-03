"""Validate the granular Power BI geographic segment summary table for Issue #145."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

GEOGRAPHIC_SEGMENT_SUMMARY_PATH = os.getenv(
    "DATACO_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_geographic_segment_summary",
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
    "map_location_label",
    "map_location_country",
    "map_location_region",
    "map_location_state",
    "map_latitude",
    "map_longitude",
    "geo_coordinates_available",
    "order_date_DateOrders",
    "order_date_key",
    "order_week_key",
    "order_month_key",
    "ao3_priority_segment",
    "ao1_high_risk_flag",
    "ao2_expected_profit_band",
    "order_count",
    "order_item_count",
    "high_risk_order_count",
    "high_risk_order_rate",
    "high_margin_order_count",
    "high_margin_order_rate",
    "avg_ao1_predicted_late_delivery_probability",
    "avg_ao2_predicted_order_profit",
    "avg_ao3_predicted_margin",
    "total_predicted_profit",
    "total_order_value",
    "protect_high_value_at_risk_count",
    "expedite_selectively_count",
    "preserve_service_count",
    "standard_process_count",
    "requires_review_count",
    "powerbi_geographic_segment_summary_timestamp_utc",
}

PROFIT_BANDS = {
    "Negative Profit",
    "$0 - $10",
    "$10 - $25",
    "$25 - $50",
    "$50 - $100",
    "$100+",
}

AO3_SEGMENTS = {
    "protect_high_value_at_risk",
    "expedite_selectively",
    "preserve_service",
    "standard_process",
    "requires_score_review",
    "requires_margin_review",
}


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
METADATA_PATH = Path(
    os.getenv(
        "DATACO_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_METADATA_PATH",
        str(REPO_ROOT / "models/dashboard/powerbi_geographic_segment_summary_metadata.json"),
    )
)


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def main() -> None:
    """Run Power BI geographic segment summary validation."""
    spark = get_spark_session()
    summary_df = spark.read.format("delta").load(GEOGRAPHIC_SEGMENT_SUMMARY_PATH)

    missing_columns = sorted(REQUIRED_COLUMNS.difference(summary_df.columns))
    assert not missing_columns, f"Power BI geographic segment summary missing columns: {missing_columns}"

    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(summary_df.columns))
    assert not forbidden_columns, (
        f"Power BI geographic segment summary contains forbidden target/outcome columns: {forbidden_columns}"
    )

    row_count = summary_df.count()
    assert row_count > 0, "Power BI geographic segment summary must contain rows."

    assert summary_df.filter(col("map_location_label").isNull()).count() == 0
    assert summary_df.filter(col("map_location_country").isNull()).count() == 0
    assert summary_df.filter(col("ao3_priority_segment").isNull()).count() == 0
    assert summary_df.filter(col("ao1_high_risk_flag").isNull()).count() == 0
    assert summary_df.filter(col("ao2_expected_profit_band").isNull()).count() == 0
    assert summary_df.filter(col("order_date_key").isNull()).count() == 0

    invalid_segment_count = summary_df.filter(~col("ao3_priority_segment").isin(*AO3_SEGMENTS)).count()
    assert invalid_segment_count == 0, f"Invalid AO3 segment rows: {invalid_segment_count}"

    invalid_profit_band_count = summary_df.filter(
        ~col("ao2_expected_profit_band").isin(*PROFIT_BANDS)
    ).count()
    assert invalid_profit_band_count == 0, f"Invalid AO2 profit-band rows: {invalid_profit_band_count}"

    invalid_latitude_count = summary_df.filter(
        (col("map_latitude").isNotNull()) & ~col("map_latitude").between(-90, 90)
    ).count()
    invalid_longitude_count = summary_df.filter(
        (col("map_longitude").isNotNull()) & ~col("map_longitude").between(-180, 180)
    ).count()
    assert invalid_latitude_count == 0, f"Invalid latitude rows: {invalid_latitude_count}"
    assert invalid_longitude_count == 0, f"Invalid longitude rows: {invalid_longitude_count}"

    invalid_rate_count = summary_df.filter(
        ~col("high_risk_order_rate").between(0, 1)
        | ~col("high_margin_order_rate").between(0, 1)
    ).count()
    assert invalid_rate_count == 0, f"Invalid geographic segment rate rows: {invalid_rate_count}"

    negative_metric_count = summary_df.filter(
        (col("order_count") < 0)
        | (col("order_item_count") < 0)
        | (col("high_risk_order_count") < 0)
        | (col("high_margin_order_count") < 0)
        | (col("protect_high_value_at_risk_count") < 0)
        | (col("expedite_selectively_count") < 0)
        | (col("preserve_service_count") < 0)
        | (col("standard_process_count") < 0)
    ).count()
    assert negative_metric_count == 0, f"Negative geographic segment metric rows: {negative_metric_count}"

    total_order_items = summary_df.agg(spark_sum("order_item_count").alias("total")).collect()[0][
        "total"
    ]
    assert total_order_items and int(total_order_items) > 0

    coordinate_rows = summary_df.filter(col("geo_coordinates_available") == 1).count()
    assert coordinate_rows > 0, "At least one geographic segment group must have map coordinates."

    assert METADATA_PATH.exists(), f"Missing geographic segment summary metadata: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["workflow"] == "powerbi_geographic_segment_summary"
    assert metadata["issue"] == "#145"
    assert metadata["target_or_outcome_columns_used"] is False
    assert metadata["output_path"] == GEOGRAPHIC_SEGMENT_SUMMARY_PATH
    assert metadata["row_count"] == row_count

    print("Power BI geographic segment summary validation passed.")


if __name__ == "__main__":
    main()
