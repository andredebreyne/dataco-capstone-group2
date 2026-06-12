"""Build Power BI order-level logistics KPI audit table for Issue #152.

The output keeps AO1 late-delivery predictions, actual delivery outcomes,
AO2 financial context, and AO3 action queues at the order-item grain. Actual
outcome columns are exposed only for KPI reporting and predicted-vs-actual
audit. They must not be used as AO1, AO2, or AO3 predictors.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

if "__file__" in globals():
    repo_root_for_imports = Path(__file__).resolve().parents[2]
    if str(repo_root_for_imports) not in sys.path:
        sys.path.insert(0, str(repo_root_for_imports))

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, date_format, lit, to_date, when
from pyspark.sql.types import DoubleType, IntegerType, StringType

from src.dashboard.country_label_standardization import standardize_country_display_label


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_SILVER_INPUT_PATH = os.getenv("DATACO_SILVER_INPUT_PATH", f"{VOLUME_ROOT}/silver/dataco_orders_silver")
DEFAULT_AO3_SEGMENT_PATH = os.getenv("DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH", f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments")
DEFAULT_SHIPPING_PRODUCT_FEATURE_PATH = os.getenv("DATACO_SHIPPING_PRODUCT_FEATURE_OUTPUT_PATH", f"{VOLUME_ROOT}/silver/dataco_shipping_product_features")
DEFAULT_CUSTOMER_REGIONAL_FEATURE_PATH = os.getenv("DATACO_CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH", f"{VOLUME_ROOT}/silver/dataco_customer_regional_features")
DEFAULT_OUTPUT_PATH = os.getenv("DATACO_POWERBI_LOGISTICS_ORDER_KPI_DETAIL_OUTPUT_PATH", f"{VOLUME_ROOT}/gold/powerbi_logistics_order_kpi_detail")

WORKFLOW_NAME = "powerbi_logistics_order_kpi_detail"
ISSUE_ID = "#152"
JOIN_KEYS = ["Order_Id", "Order_Item_Id", "order_date_DateOrders"]
AUDIT_GRAIN = ["Order_Id", "Order_Item_Id"]
CRITICAL_GOVERNED_COLUMNS = [
    "ao1_predicted_late_delivery_probability",
    "ao1_high_risk_flag",
    "ao2_predicted_order_profit",
    "ao3_predicted_margin",
    "ao3_order_value",
    "ao3_priority_segment",
]

OUTPUT_COLUMNS = [
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
]


@dataclass(frozen=True)
class PowerBILogisticsOrderKPIDetailConfig:
    silver_input_path: str = DEFAULT_SILVER_INPUT_PATH
    ao3_segment_path: str = DEFAULT_AO3_SEGMENT_PATH
    shipping_product_feature_path: str = DEFAULT_SHIPPING_PRODUCT_FEATURE_PATH
    customer_regional_feature_path: str = DEFAULT_CUSTOMER_REGIONAL_FEATURE_PATH
    output_path: str = DEFAULT_OUTPUT_PATH
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_POWERBI_LOGISTICS_ORDER_KPI_DETAIL_METADATA_PATH",
            str(Path.cwd() / "models/dashboard/powerbi_logistics_order_kpi_detail_metadata.json"),
        )
    )
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_logistics_order_kpi_detail")


def get_spark_session() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]
    return Path.cwd().resolve()


def with_repo_defaults(config: PowerBILogisticsOrderKPIDetailConfig) -> PowerBILogisticsOrderKPIDetailConfig:
    repo_root = resolve_repo_root()
    return PowerBILogisticsOrderKPIDetailConfig(
        silver_input_path=config.silver_input_path,
        ao3_segment_path=config.ao3_segment_path,
        shipping_product_feature_path=config.shipping_product_feature_path,
        customer_regional_feature_path=config.customer_regional_feature_path,
        output_path=config.output_path,
        metadata_output_path=Path(
            os.getenv(
                "DATACO_POWERBI_LOGISTICS_ORDER_KPI_DETAIL_METADATA_PATH",
                str(repo_root / "models/dashboard/powerbi_logistics_order_kpi_detail_metadata.json"),
            )
        ),
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


def build_powerbi_logistics_order_kpi_detail_dataframe(
    silver_df: DataFrame,
    ao3_df: DataFrame,
    shipping_df: DataFrame,
    geo_df: DataFrame,
) -> DataFrame:
    assert_required_columns(
        silver_df,
        JOIN_KEYS + ["shipping_date_DateOrders", "Days_for_shipment_scheduled", "Days_for_shipping_real", "Delivery_Status"],
        "Silver table",
    )
    assert_required_columns(
        ao3_df,
        JOIN_KEYS + ["ao1_predicted_late_delivery_probability", "ao1_high_risk_flag", "ao2_predicted_order_profit", "ao3_predicted_margin", "ao3_priority_segment", "ao3_order_value"],
        "AO3 segment table",
    )
    assert_required_columns(
        shipping_df,
        JOIN_KEYS + ["shipping_speed_tier", "shipping_mode_normalized", "product_category_key", "product_department_key", "order_item_quantity", "item_net_sales_amount"],
        "Shipping/product feature table",
    )
    assert_required_columns(
        geo_df,
        JOIN_KEYS + ["market_normalized", "order_country_normalized", "order_region_normalized", "order_state_normalized"],
        "Customer/regional feature table",
    )

    joined_df = (
        ao3_df.join(
            silver_df.select(
                *JOIN_KEYS,
                "shipping_date_DateOrders",
                "Days_for_shipment_scheduled",
                "Days_for_shipping_real",
                "Delivery_Status",
            ),
            JOIN_KEYS,
            "left",
        )
        .join(
            shipping_df.select(
                *JOIN_KEYS,
                "shipping_speed_tier",
                "shipping_mode_normalized",
                "product_category_key",
                "product_department_key",
                "order_item_quantity",
                "item_net_sales_amount",
            ),
            JOIN_KEYS,
            "left",
        )
        .join(
            geo_df.select(
                *JOIN_KEYS,
                "market_normalized",
                "order_country_normalized",
                "order_region_normalized",
                "order_state_normalized",
            ),
            JOIN_KEYS,
            "left",
        )
    )

    actual_days = col("Days_for_shipping_real").cast(DoubleType())
    scheduled_days = col("Days_for_shipment_scheduled").cast(DoubleType())
    valid_delivery = actual_days.isNotNull() & scheduled_days.isNotNull()
    actual_late = valid_delivery & (actual_days > scheduled_days)
    actual_on_time = valid_delivery & (actual_days <= scheduled_days)
    probability = col("ao1_predicted_late_delivery_probability").cast(DoubleType())
    high_risk = col("ao1_high_risk_flag").cast("boolean")
    segment = col("ao3_priority_segment")

    return (
        joined_df.withColumn("order_date", to_date(col("order_date_DateOrders")))
        .withColumn("order_month_key", date_format(col("order_date"), "yyyy-MM"))
        .withColumn("order_year", date_format(col("order_date"), "yyyy").cast(IntegerType()))
        .withColumn("order_month", date_format(col("order_date"), "MM").cast(IntegerType()))
        .withColumn("market_normalized", safe_label("market_normalized", "unknown_market"))
        .withColumn(
            "map_location_country",
            standardize_country_display_label(safe_label("order_country_normalized", "unknown_country")),
        )
        .withColumn("map_location_region", safe_label("order_region_normalized", "unknown_region"))
        .withColumn("map_location_state", safe_label("order_state_normalized", "unknown_state"))
        .withColumn("shipping_mode_normalized", safe_label("shipping_mode_normalized", "unknown_shipping_mode"))
        .withColumn("shipping_speed_tier", safe_label("shipping_speed_tier", "unknown_speed_tier"))
        .withColumn("product_category_key", safe_label("product_category_key", "unknown_category"))
        .withColumn("product_department_key", safe_label("product_department_key", "unknown_department"))
        .withColumn("order_item_quantity", col("order_item_quantity").cast(DoubleType()))
        .withColumn("item_net_sales_amount", col("item_net_sales_amount").cast(DoubleType()))
        .withColumn("ao3_order_value", col("ao3_order_value").cast(DoubleType()))
        .withColumn("scheduled_shipping_days", scheduled_days)
        .withColumn("actual_shipping_lead_time", actual_days)
        .withColumn("delivery_delay_gap", when(valid_delivery, actual_days - scheduled_days).otherwise(lit(None)).cast(DoubleType()))
        .withColumn("valid_delivery_metric_flag", when(valid_delivery, lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("actual_on_time_delivery_flag", when(actual_on_time, lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("actual_late_delivery_flag", when(actual_late, lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("delivery_status_normalized", safe_label("Delivery_Status", "unknown_delivery_status"))
        .withColumn("ao1_predicted_late_delivery_probability", probability)
        .withColumn("ao1_expected_on_time_probability", lit(1.0) - probability)
        .withColumn("ao1_high_risk_flag", when(high_risk, lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("risk_band", when(probability < 0.35, lit("Low Risk")).when(probability < 0.65, lit("Medium Risk")).otherwise(lit("High Risk")).cast(StringType()))
        .withColumn("risk_band_sort_order", when(col("risk_band") == "High Risk", lit(1)).when(col("risk_band") == "Medium Risk", lit(2)).otherwise(lit(3)).cast(IntegerType()))
        .withColumn("true_positive_flag", when((col("ao1_high_risk_flag") == 1) & (col("actual_late_delivery_flag") == 1), lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("false_positive_flag", when((col("ao1_high_risk_flag") == 1) & (col("actual_on_time_delivery_flag") == 1), lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("false_negative_flag", when((col("ao1_high_risk_flag") == 0) & (col("actual_late_delivery_flag") == 1), lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("true_negative_flag", when((col("ao1_high_risk_flag") == 0) & (col("actual_on_time_delivery_flag") == 1), lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("ao2_predicted_order_profit", col("ao2_predicted_order_profit").cast(DoubleType()))
        .withColumn("ao3_predicted_margin", col("ao3_predicted_margin").cast(DoubleType()))
        .withColumn("ao3_action_queue_label", when(segment == "protect_high_value_at_risk", lit("Protect First")).when(segment == "expedite_selectively", lit("Review Selective Expedite")).when(segment == "preserve_service", lit("Preserve Service")).when(segment == "standard_process", lit("Standard Process")).otherwise(lit("Review Score or Margin")).cast(StringType()))
        .withColumn("ao3_action_queue_sort_order", when(col("ao3_action_queue_label") == "Protect First", lit(1)).when(col("ao3_action_queue_label") == "Review Selective Expedite", lit(2)).when(col("ao3_action_queue_label") == "Preserve Service", lit(3)).when(col("ao3_action_queue_label") == "Standard Process", lit(4)).otherwise(lit(98)).cast(IntegerType()))
        .withColumn("intervention_required_flag", when(segment.isin("protect_high_value_at_risk", "expedite_selectively"), lit(1)).otherwise(lit(0)).cast(IntegerType()))
        .withColumn("powerbi_logistics_order_kpi_detail_timestamp_utc", current_timestamp())
        .select(*OUTPUT_COLUMNS)
    )


def validate_output(df: DataFrame) -> None:
    if df.count() == 0:
        raise ValueError("Power BI logistics order KPI detail contains no rows.")
    assert_required_columns(df, OUTPUT_COLUMNS, "Power BI logistics order KPI detail")

    duplicate_grain_rows = df.groupBy(*AUDIT_GRAIN).count().filter(col("count") > 1).count()
    if duplicate_grain_rows:
        raise ValueError(f"Order-level KPI detail contains duplicated grain rows: {duplicate_grain_rows}")

    required_non_null_columns = AUDIT_GRAIN + [
        "order_month_key",
        "shipping_mode_normalized",
        "risk_band",
        "ao3_action_queue_label",
        *CRITICAL_GOVERNED_COLUMNS,
    ]
    for column_name in required_non_null_columns:
        null_count = df.filter(col(column_name).isNull()).count()
        if null_count:
            raise ValueError(f"{column_name} contains null rows: {null_count}")

    for column_name in ["ao1_predicted_late_delivery_probability", "ao1_expected_on_time_probability"]:
        invalid = df.filter(col(column_name).isNotNull() & ~col(column_name).between(0, 1)).count()
        if invalid:
            raise ValueError(f"{column_name} has invalid probability rows: {invalid}")

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
        invalid = df.filter(~col(column_name).isin(0, 1)).count()
        if invalid:
            raise ValueError(f"{column_name} has non-binary rows: {invalid}")

    invalid_outcome_flags = df.filter(
        (col("actual_on_time_delivery_flag") + col("actual_late_delivery_flag")) != col("valid_delivery_metric_flag")
    ).count()
    if invalid_outcome_flags:
        raise ValueError(f"Invalid actual outcome flag rows: {invalid_outcome_flags}")

    invalid_classification_flags = df.filter(
        (col("true_positive_flag") + col("false_positive_flag") + col("false_negative_flag") + col("true_negative_flag"))
        != col("valid_delivery_metric_flag")
    ).count()
    if invalid_classification_flags:
        raise ValueError(f"Invalid prediction classification rows: {invalid_classification_flags}")


def write_metadata(config: PowerBILogisticsOrderKPIDetailConfig, df: DataFrame, logger: logging.Logger) -> None:
    metadata = {
        "workflow": WORKFLOW_NAME,
        "issue": ISSUE_ID,
        "output_path": config.output_path,
        "row_count": int(df.count()),
        "serving_grain": AUDIT_GRAIN,
        "ao1_target_interpretation": "risk of late delivery",
        "actual_outcomes_exposed_for_audit_only": True,
        "actual_outcomes_used_as_model_predictors": False,
        "predictive_exposure_uses_governed_ao1_ao2_ao3_outputs": True,
        "causal_intervention_impact_claimed": False,
        "official_ao1_ao2_ao3_policy_changed": False,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.metadata_output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote metadata to %s", config.metadata_output_path)


def run_powerbi_logistics_order_kpi_detail(config: PowerBILogisticsOrderKPIDetailConfig, logger: logging.Logger) -> None:
    config = with_repo_defaults(config)
    spark = get_spark_session()
    silver_df = spark.read.format(config.read_format).load(config.silver_input_path)
    ao3_df = spark.read.format(config.read_format).load(config.ao3_segment_path)
    shipping_df = spark.read.format(config.read_format).load(config.shipping_product_feature_path)
    geo_df = spark.read.format(config.read_format).load(config.customer_regional_feature_path)

    detail_df = build_powerbi_logistics_order_kpi_detail_dataframe(silver_df, ao3_df, shipping_df, geo_df)
    validate_output(detail_df)
    detail_df.write.format(config.write_format).mode(config.write_mode).option("overwriteSchema", "true").save(config.output_path)
    written_df = spark.read.format(config.read_format).load(config.output_path)
    validate_output(written_df)
    write_metadata(config, written_df, logger)


def main() -> None:
    run_powerbi_logistics_order_kpi_detail(PowerBILogisticsOrderKPIDetailConfig(), configure_logging())


if __name__ == "__main__":
    main()
