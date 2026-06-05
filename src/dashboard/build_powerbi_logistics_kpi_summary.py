"""Build Power BI logistics KPI risk exposure summary for Issue #150.

The output connects historical fulfillment KPIs with predictive pre-dispatch
exposure from governed AO1/AO2/AO3 outputs. Historical KPIs may use
post-delivery outcomes for descriptive reporting. Predictive exposure is based
on model outputs and should not be interpreted as causal intervention impact.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import avg, col, countDistinct, current_timestamp, date_format, lit, sum as spark_sum, to_date, when
from pyspark.sql.types import DoubleType, IntegerType, StringType


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_SILVER_INPUT_PATH = os.getenv("DATACO_SILVER_INPUT_PATH", f"{VOLUME_ROOT}/silver/dataco_orders_silver")
DEFAULT_AO3_SEGMENT_PATH = os.getenv("DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH", f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments")
DEFAULT_SHIPPING_PRODUCT_FEATURE_PATH = os.getenv("DATACO_SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH", f"{VOLUME_ROOT}/silver/dataco_shipping_product_features")
DEFAULT_CUSTOMER_REGIONAL_FEATURE_PATH = os.getenv("DATACO_CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH", f"{VOLUME_ROOT}/silver/dataco_customer_regional_features")
DEFAULT_OUTPUT_PATH = os.getenv("DATACO_POWERBI_LOGISTICS_KPI_SUMMARY_OUTPUT_PATH", f"{VOLUME_ROOT}/gold/powerbi_logistics_kpi_summary")

WORKFLOW_NAME = "powerbi_logistics_kpi_summary"
JOIN_KEYS = ["Order_Id", "Order_Item_Id", "order_date_DateOrders"]

RAW_OUTCOME_COLUMNS_NOT_EXPOSED = {
    "Days_for_shipping_real",
    "Delivery_Status",
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Benefit_per_order",
    "Order_Item_Profit_Ratio",
}

OUTPUT_COLUMNS = [
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
]


@dataclass(frozen=True)
class PowerBILogisticsKPISummaryConfig:
    silver_input_path: str = DEFAULT_SILVER_INPUT_PATH
    ao3_segment_path: str = DEFAULT_AO3_SEGMENT_PATH
    shipping_product_feature_path: str = DEFAULT_SHIPPING_PRODUCT_FEATURE_PATH
    customer_regional_feature_path: str = DEFAULT_CUSTOMER_REGIONAL_FEATURE_PATH
    output_path: str = DEFAULT_OUTPUT_PATH
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_POWERBI_LOGISTICS_KPI_SUMMARY_METADATA_PATH",
            str(Path.cwd() / "models/dashboard/powerbi_logistics_kpi_summary_metadata.json"),
        )
    )
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"


def configure_logging() -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
    return logging.getLogger("dataco.powerbi_logistics_kpi_summary")


def get_spark_session() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]
    return Path.cwd().resolve()


def with_repo_defaults(config: PowerBILogisticsKPISummaryConfig) -> PowerBILogisticsKPISummaryConfig:
    repo_root = resolve_repo_root()
    return PowerBILogisticsKPISummaryConfig(
        silver_input_path=config.silver_input_path,
        ao3_segment_path=config.ao3_segment_path,
        shipping_product_feature_path=config.shipping_product_feature_path,
        customer_regional_feature_path=config.customer_regional_feature_path,
        output_path=config.output_path,
        metadata_output_path=Path(os.getenv("DATACO_POWERBI_LOGISTICS_KPI_SUMMARY_METADATA_PATH", str(repo_root / "models/dashboard/powerbi_logistics_kpi_summary_metadata.json"))),
        read_format=config.read_format,
        write_format=config.write_format,
        write_mode=config.write_mode,
    )


def assert_required_columns(df: DataFrame, required_columns: list[str], table_name: str) -> None:
    missing = sorted(column for column in required_columns if column not in df.columns)
    if missing:
        raise ValueError(f"{table_name} is missing required columns: {missing}")


def safe_label(column_name: str, fallback: str):
    return when(col(column_name).isNull() | (col(column_name) == ""), lit(fallback)).otherwise(col(column_name))


def build_powerbi_logistics_kpi_summary_dataframe(silver_df: DataFrame, ao3_df: DataFrame, shipping_df: DataFrame, geo_df: DataFrame) -> DataFrame:
    assert_required_columns(silver_df, JOIN_KEYS + ["Days_for_shipment_scheduled", "Days_for_shipping_real"], "Silver table")
    assert_required_columns(ao3_df, JOIN_KEYS + ["ao1_predicted_late_delivery_probability", "ao1_high_risk_flag", "ao2_predicted_order_profit", "ao3_predicted_margin", "ao3_priority_segment", "ao3_order_value"], "AO3 segment table")
    assert_required_columns(shipping_df, JOIN_KEYS + ["shipping_speed_tier", "shipping_mode_normalized", "product_category_key", "product_department_key", "order_item_quantity", "item_net_sales_amount"], "Shipping/product feature table")
    assert_required_columns(geo_df, JOIN_KEYS + ["market_normalized", "order_country_normalized", "order_region_normalized", "order_state_normalized"], "Customer/regional feature table")

    joined_df = (
        ao3_df.join(silver_df.select(*JOIN_KEYS, "Days_for_shipment_scheduled", "Days_for_shipping_real"), JOIN_KEYS, "left")
        .join(shipping_df.select(*JOIN_KEYS, "shipping_speed_tier", "shipping_mode_normalized", "product_category_key", "product_department_key", "order_item_quantity", "item_net_sales_amount"), JOIN_KEYS, "left")
        .join(geo_df.select(*JOIN_KEYS, "market_normalized", "order_country_normalized", "order_region_normalized", "order_state_normalized"), JOIN_KEYS, "left")
    )

    actual_days = col("Days_for_shipping_real").cast(DoubleType())
    scheduled_days = col("Days_for_shipment_scheduled").cast(DoubleType())
    valid_delivery = actual_days.isNotNull() & scheduled_days.isNotNull()
    probability = col("ao1_predicted_late_delivery_probability").cast(DoubleType())
    segment = col("ao3_priority_segment")

    enriched_df = (
        joined_df.withColumn("order_date", to_date(col("order_date_DateOrders")))
        .withColumn("order_month_key", date_format(col("order_date"), "yyyy-MM"))
        .withColumn("order_year", date_format(col("order_date"), "yyyy").cast(IntegerType()))
        .withColumn("order_month", date_format(col("order_date"), "MM").cast(IntegerType()))
        .withColumn("market_normalized", safe_label("market_normalized", "unknown_market"))
        .withColumn("map_location_country", safe_label("order_country_normalized", "unknown_country"))
        .withColumn("map_location_region", safe_label("order_region_normalized", "unknown_region"))
        .withColumn("map_location_state", safe_label("order_state_normalized", "unknown_state"))
        .withColumn("shipping_mode_normalized", safe_label("shipping_mode_normalized", "unknown_shipping_mode"))
        .withColumn("shipping_speed_tier", safe_label("shipping_speed_tier", "unknown_speed_tier"))
        .withColumn("product_category_key", safe_label("product_category_key", "unknown_category"))
        .withColumn("product_department_key", safe_label("product_department_key", "unknown_department"))
        .withColumn("delivery_metric_available", when(valid_delivery, lit(1)).otherwise(lit(0)))
        .withColumn("historical_otd_flag", when(valid_delivery & (actual_days <= scheduled_days), lit(1)).otherwise(lit(0)))
        .withColumn("historical_late_flag", when(valid_delivery & (actual_days > scheduled_days), lit(1)).otherwise(lit(0)))
        .withColumn("delivery_delay_gap", when(valid_delivery, actual_days - scheduled_days).otherwise(lit(None)).cast(DoubleType()))
        .withColumn("expected_late_probability", probability)
        .withColumn("expected_on_time_probability", lit(1.0) - probability)
        .withColumn("risk_band", when(probability < 0.35, lit("Low Risk")).when(probability < 0.65, lit("Medium Risk")).otherwise(lit("High Risk")).cast(StringType()))
        .withColumn("risk_band_sort_order", when(col("risk_band") == "High Risk", lit(1)).when(col("risk_band") == "Medium Risk", lit(2)).otherwise(lit(3)).cast(IntegerType()))
        .withColumn("ao3_action_queue_label", when(segment == "protect_high_value_at_risk", lit("Protect First")).when(segment == "expedite_selectively", lit("Review Selective Expedite")).when(segment == "preserve_service", lit("Preserve Service")).when(segment == "standard_process", lit("Standard Process")).otherwise(lit("Review Score or Margin")).cast(StringType()))
        .withColumn("ao3_action_queue_sort_order", when(col("ao3_action_queue_label") == "Protect First", lit(1)).when(col("ao3_action_queue_label") == "Review Selective Expedite", lit(2)).when(col("ao3_action_queue_label") == "Preserve Service", lit(3)).when(col("ao3_action_queue_label") == "Standard Process", lit(4)).otherwise(lit(98)).cast(IntegerType()))
        .withColumn("intervention_required_flag", when(segment.isin("protect_high_value_at_risk", "expedite_selectively"), lit(1)).otherwise(lit(0)))
    )

    grouped_df = enriched_df.groupBy(*OUTPUT_COLUMNS[:16]).agg(
        countDistinct("Order_Id").alias("order_count"),
        spark_sum(lit(1)).alias("order_item_count"),
        spark_sum(col("order_item_quantity").cast(DoubleType())).alias("units_ordered"),
        spark_sum(col("item_net_sales_amount").cast(DoubleType())).alias("total_sales_amount"),
        spark_sum(col("ao3_order_value").cast(DoubleType())).alias("total_order_value"),
        spark_sum("delivery_metric_available").alias("valid_delivery_metric_count"),
        spark_sum("historical_otd_flag").alias("historical_on_time_count"),
        spark_sum("historical_late_flag").alias("historical_late_count"),
        avg("Days_for_shipment_scheduled").alias("avg_scheduled_shipping_days"),
        avg("Days_for_shipping_real").alias("avg_actual_shipping_days"),
        avg("delivery_delay_gap").alias("avg_delivery_delay_gap"),
        avg("expected_late_probability").alias("expected_late_delivery_rate"),
        avg("expected_on_time_probability").alias("expected_otd_rate"),
        spark_sum("expected_late_probability").alias("expected_late_order_equivalent_count"),
        spark_sum(when(col("ao1_high_risk_flag"), lit(1)).otherwise(lit(0))).alias("high_risk_order_count"),
        spark_sum(when(segment == "protect_high_value_at_risk", lit(1)).otherwise(lit(0))).alias("service_protection_queue_count"),
        spark_sum(when(segment == "expedite_selectively", lit(1)).otherwise(lit(0))).alias("selective_expedite_review_count"),
        spark_sum(when(segment == "preserve_service", lit(1)).otherwise(lit(0))).alias("preserve_service_queue_count"),
        spark_sum(when(segment == "standard_process", lit(1)).otherwise(lit(0))).alias("standard_process_queue_count"),
        spark_sum("intervention_required_flag").alias("intervention_required_count"),
        avg("ao2_predicted_order_profit").alias("avg_predicted_order_profit"),
        avg("ao3_predicted_margin").alias("avg_predicted_margin"),
        spark_sum("ao2_predicted_order_profit").alias("total_predicted_profit"),
    )

    return (
        grouped_df.withColumn("historical_otd_rate", when(col("valid_delivery_metric_count") > 0, col("historical_on_time_count") / col("valid_delivery_metric_count")).otherwise(lit(None)).cast(DoubleType()))
        .withColumn("historical_late_delivery_rate", when(col("valid_delivery_metric_count") > 0, col("historical_late_count") / col("valid_delivery_metric_count")).otherwise(lit(None)).cast(DoubleType()))
        .withColumn("expected_otd_exposure_pp", (col("historical_otd_rate") - col("expected_otd_rate")).cast(DoubleType()))
        .withColumn("high_risk_delivery_exposure_rate", (col("high_risk_order_count") / col("order_item_count")).cast(DoubleType()))
        .withColumn("intervention_load_rate", (col("intervention_required_count") / col("order_item_count")).cast(DoubleType()))
        .withColumn("powerbi_logistics_kpi_summary_timestamp_utc", current_timestamp())
        .select(*OUTPUT_COLUMNS)
    )


def validate_output(df: DataFrame) -> None:
    if df.count() == 0:
        raise ValueError("Power BI logistics KPI summary contains no rows.")
    assert_required_columns(df, OUTPUT_COLUMNS, "Power BI logistics KPI summary")
    exposed = sorted(RAW_OUTCOME_COLUMNS_NOT_EXPOSED.intersection(df.columns))
    if exposed:
        raise ValueError(f"Raw outcome columns exposed in output: {exposed}")
    for column_name in ["historical_otd_rate", "historical_late_delivery_rate", "expected_late_delivery_rate", "expected_otd_rate", "high_risk_delivery_exposure_rate", "intervention_load_rate"]:
        invalid = df.filter(col(column_name).isNotNull() & ~col(column_name).between(0, 1)).count()
        if invalid:
            raise ValueError(f"{column_name} has invalid rate rows: {invalid}")


def write_metadata(config: PowerBILogisticsKPISummaryConfig, df: DataFrame, logger: logging.Logger) -> None:
    metadata = {
        "workflow": WORKFLOW_NAME,
        "issue": "#150",
        "output_path": config.output_path,
        "row_count": int(df.count()),
        "historical_kpi_fields_use_post_delivery_outcomes": True,
        "predictive_exposure_uses_governed_ao1_ao2_ao3_outputs": True,
        "causal_intervention_impact_claimed": False,
        "official_ao1_ao2_ao3_policy_changed": False,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.metadata_output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote metadata to %s", config.metadata_output_path)


def run_powerbi_logistics_kpi_summary(config: PowerBILogisticsKPISummaryConfig, logger: logging.Logger) -> None:
    config = with_repo_defaults(config)
    spark = get_spark_session()
    silver_df = spark.read.format(config.read_format).load(config.silver_input_path)
    ao3_df = spark.read.format(config.read_format).load(config.ao3_segment_path)
    shipping_df = spark.read.format(config.read_format).load(config.shipping_product_feature_path)
    geo_df = spark.read.format(config.read_format).load(config.customer_regional_feature_path)
    summary_df = build_powerbi_logistics_kpi_summary_dataframe(silver_df, ao3_df, shipping_df, geo_df)
    validate_output(summary_df)
    summary_df.write.format(config.write_format).mode(config.write_mode).option("overwriteSchema", "true").save(config.output_path)
    written_df = spark.read.format(config.read_format).load(config.output_path)
    validate_output(written_df)
    write_metadata(config, written_df, logger)


def main() -> None:
    run_powerbi_logistics_kpi_summary(PowerBILogisticsKPISummaryConfig(), configure_logging())


if __name__ == "__main__":
    main()
