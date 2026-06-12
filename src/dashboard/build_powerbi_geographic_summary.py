"""Build Power BI geographic summary data for the global map page.

This Databricks-compatible job joins governed AO3 order segments with the
customer/regional feature output to create a dashboard-safe geographic summary.
It keeps location text and rounded coordinates for Power BI map flexibility
without exposing target or realized-outcome fields.
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
from pyspark.sql.functions import (
    avg,
    col,
    concat_ws,
    countDistinct,
    current_timestamp,
    lit,
    max as spark_max,
    min as spark_min,
    sum as spark_sum,
    when,
)
from pyspark.sql.types import DoubleType, IntegerType, StringType

from src.dashboard.country_label_standardization import standardize_country_display_label


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

DEFAULT_AO3_SEGMENT_PATH = os.getenv(
    "DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments",
)

DEFAULT_CUSTOMER_REGIONAL_FEATURE_PATH = os.getenv(
    "DATACO_CUSTOMER_REGIONAL_FEATURE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/silver/dataco_customer_regional_features",
)

DEFAULT_GEOGRAPHIC_SUMMARY_OUTPUT_PATH = os.getenv(
    "DATACO_POWERBI_GEOGRAPHIC_SUMMARY_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_geographic_summary",
)

WORKFLOW_NAME = "powerbi_geographic_summary"

JOIN_KEY_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
)

AO3_REQUIRED_COLUMNS = JOIN_KEY_COLUMNS + (
    "split_partition",
    "ao2_split_partition",
    "ao1_predicted_late_delivery_probability",
    "ao1_high_risk_flag",
    "ao2_predicted_order_profit",
    "ao3_order_value",
    "ao3_predicted_margin",
    "ao3_high_margin_flag",
    "ao3_priority_segment",
)

GEOGRAPHIC_REQUIRED_COLUMNS = JOIN_KEY_COLUMNS + (
    "market_normalized",
    "order_country_normalized",
    "order_region_normalized",
    "order_state_normalized",
    "latitude_rounded",
    "longitude_rounded",
    "geo_coordinates_available",
)

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}

GEOGRAPHIC_GROUP_COLUMNS = (
    "map_location_label",
    "map_location_country",
    "map_location_region",
    "map_location_state",
    "map_latitude",
    "map_longitude",
    "geo_coordinates_available",
)

GEOGRAPHIC_SUMMARY_COLUMNS = GEOGRAPHIC_GROUP_COLUMNS + (
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
    "min_order_date_DateOrders",
    "max_order_date_DateOrders",
    "powerbi_geographic_summary_timestamp_utc",
)


@dataclass(frozen=True)
class PowerBIGeographicSummaryConfig:
    """Configuration for the Power BI geographic summary job."""

    ao3_segment_path: str = DEFAULT_AO3_SEGMENT_PATH
    customer_regional_feature_path: str = DEFAULT_CUSTOMER_REGIONAL_FEATURE_PATH
    geographic_summary_output_path: str = DEFAULT_GEOGRAPHIC_SUMMARY_OUTPUT_PATH
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_POWERBI_GEOGRAPHIC_SUMMARY_METADATA_PATH",
            str(Path.cwd() / "models/dashboard/powerbi_geographic_summary_metadata.json"),
        )
    )
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"


def configure_logging() -> logging.Logger:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_geographic_summary")


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


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


def with_repo_defaults(config: PowerBIGeographicSummaryConfig) -> PowerBIGeographicSummaryConfig:
    """Use repository-root defaults when environment overrides are absent."""
    repo_root = resolve_repo_root()
    return PowerBIGeographicSummaryConfig(
        ao3_segment_path=config.ao3_segment_path,
        customer_regional_feature_path=config.customer_regional_feature_path,
        geographic_summary_output_path=config.geographic_summary_output_path,
        metadata_output_path=Path(
            os.getenv(
                "DATACO_POWERBI_GEOGRAPHIC_SUMMARY_METADATA_PATH",
                str(repo_root / "models/dashboard/powerbi_geographic_summary_metadata.json"),
            )
        ),
        read_format=config.read_format,
        write_format=config.write_format,
        write_mode=config.write_mode,
    )


def assert_required_columns(df: DataFrame, required_columns: tuple[str, ...], table_name: str) -> None:
    """Validate required source columns."""
    missing_columns = sorted(column for column in required_columns if column not in df.columns)
    if missing_columns:
        raise ValueError(f"{table_name} is missing required columns: {missing_columns}")


def assert_no_forbidden_targets(df: DataFrame, table_name: str) -> None:
    """Prevent target and realized-outcome fields from entering dashboard data."""
    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(df.columns))
    if forbidden_columns:
        raise ValueError(f"{table_name} contains forbidden target/outcome columns: {forbidden_columns}")


def read_delta(spark: SparkSession, path: str, config: PowerBIGeographicSummaryConfig) -> DataFrame:
    """Read a configured Delta source."""
    return spark.read.format(config.read_format).load(path)


def validate_source_contracts(ao3_df: DataFrame, geographic_df: DataFrame) -> None:
    """Validate input schemas before joining."""
    assert_required_columns(ao3_df, AO3_REQUIRED_COLUMNS, "AO3 segment table")
    assert_required_columns(
        geographic_df,
        GEOGRAPHIC_REQUIRED_COLUMNS,
        "customer/regional feature table",
    )
    assert_no_forbidden_targets(ao3_df, "AO3 segment table")
    assert_no_forbidden_targets(geographic_df, "customer/regional feature table")


def build_geographic_summary_dataframe(ao3_df: DataFrame, geographic_df: DataFrame) -> DataFrame:
    """Join AO3 scores to geography and aggregate map-ready metrics."""
    ao3_projection = ao3_df.select(*AO3_REQUIRED_COLUMNS)
    geographic_projection = geographic_df.select(*GEOGRAPHIC_REQUIRED_COLUMNS)

    joined_df = ao3_projection.join(
        geographic_projection,
        on=list(JOIN_KEY_COLUMNS),
        how="left",
    )

    map_location_country = when(
        col("order_country_normalized").isNull() | (col("order_country_normalized") == ""),
        lit("unknown_country"),
    ).otherwise(col("order_country_normalized"))
    map_location_region = when(
        col("order_region_normalized").isNull() | (col("order_region_normalized") == ""),
        lit("unknown_region"),
    ).otherwise(col("order_region_normalized"))
    map_location_state = when(
        col("order_state_normalized").isNull() | (col("order_state_normalized") == ""),
        lit("unknown_state"),
    ).otherwise(col("order_state_normalized"))

    enriched_df = (
        joined_df.withColumn(
            "map_location_country",
            standardize_country_display_label(map_location_country).cast(StringType()),
        )
        .withColumn("map_location_region", map_location_region.cast(StringType()))
        .withColumn("map_location_state", map_location_state.cast(StringType()))
        .withColumn(
            "map_location_label",
            concat_ws(", ", col("map_location_state"), col("map_location_region"), col("map_location_country")),
        )
        .withColumn("map_latitude", col("latitude_rounded").cast(DoubleType()))
        .withColumn("map_longitude", col("longitude_rounded").cast(DoubleType()))
        .withColumn(
            "geo_coordinates_available",
            when(
                (col("geo_coordinates_available") == 1)
                & col("map_latitude").between(-90, 90)
                & col("map_longitude").between(-180, 180),
                lit(1),
            )
            .otherwise(lit(0))
            .cast(IntegerType()),
        )
    )

    grouped_df = enriched_df.groupBy(*GEOGRAPHIC_GROUP_COLUMNS).agg(
        countDistinct("Order_Id").alias("order_count"),
        spark_sum(lit(1)).alias("order_item_count"),
        spark_sum(when(col("ao1_high_risk_flag"), lit(1)).otherwise(lit(0))).alias(
            "high_risk_order_count"
        ),
        spark_sum(when(col("ao3_high_margin_flag"), lit(1)).otherwise(lit(0))).alias(
            "high_margin_order_count"
        ),
        avg("ao1_predicted_late_delivery_probability").alias(
            "avg_ao1_predicted_late_delivery_probability"
        ),
        avg("ao2_predicted_order_profit").alias("avg_ao2_predicted_order_profit"),
        avg("ao3_predicted_margin").alias("avg_ao3_predicted_margin"),
        spark_sum("ao2_predicted_order_profit").alias("total_predicted_profit"),
        spark_sum("ao3_order_value").alias("total_order_value"),
        spark_sum(
            when(col("ao3_priority_segment") == "protect_high_value_at_risk", lit(1)).otherwise(lit(0))
        ).alias("protect_high_value_at_risk_count"),
        spark_sum(
            when(col("ao3_priority_segment") == "expedite_selectively", lit(1)).otherwise(lit(0))
        ).alias("expedite_selectively_count"),
        spark_sum(when(col("ao3_priority_segment") == "preserve_service", lit(1)).otherwise(lit(0))).alias(
            "preserve_service_count"
        ),
        spark_sum(when(col("ao3_priority_segment") == "standard_process", lit(1)).otherwise(lit(0))).alias(
            "standard_process_count"
        ),
        spark_sum(
            when(
                col("ao3_priority_segment").isin("requires_score_review", "requires_margin_review"),
                lit(1),
            ).otherwise(lit(0))
        ).alias("requires_review_count"),
        spark_min("order_date_DateOrders").alias("min_order_date_DateOrders"),
        spark_max("order_date_DateOrders").alias("max_order_date_DateOrders"),
    )

    return (
        grouped_df.withColumn(
            "high_risk_order_rate",
            (col("high_risk_order_count") / col("order_item_count")).cast(DoubleType()),
        )
        .withColumn(
            "high_margin_order_rate",
            (col("high_margin_order_count") / col("order_item_count")).cast(DoubleType()),
        )
        .withColumn("powerbi_geographic_summary_timestamp_utc", current_timestamp())
        .select(*GEOGRAPHIC_SUMMARY_COLUMNS)
    )


def validate_geographic_summary_output(df: DataFrame) -> None:
    """Validate map-ready output before writing."""
    row_count = df.count()
    if row_count == 0:
        raise ValueError("Power BI geographic summary contains no rows.")

    assert_required_columns(df, GEOGRAPHIC_SUMMARY_COLUMNS, "Power BI geographic summary")
    assert_no_forbidden_targets(df, "Power BI geographic summary")

    invalid_latitude_count = df.filter(
        (col("map_latitude").isNotNull()) & ~col("map_latitude").between(-90, 90)
    ).count()
    if invalid_latitude_count:
        raise ValueError(f"Invalid map latitude rows: {invalid_latitude_count}")

    invalid_longitude_count = df.filter(
        (col("map_longitude").isNotNull()) & ~col("map_longitude").between(-180, 180)
    ).count()
    if invalid_longitude_count:
        raise ValueError(f"Invalid map longitude rows: {invalid_longitude_count}")

    negative_count_rows = df.filter(
        (col("order_count") < 0) | (col("order_item_count") < 0)
    ).count()
    if negative_count_rows:
        raise ValueError(f"Negative geographic count rows: {negative_count_rows}")

    invalid_rate_rows = df.filter(
        ~col("high_risk_order_rate").between(0, 1)
        | ~col("high_margin_order_rate").between(0, 1)
    ).count()
    if invalid_rate_rows:
        raise ValueError(f"Invalid geographic rate rows: {invalid_rate_rows}")


def write_delta(df: DataFrame, output_path: str, config: PowerBIGeographicSummaryConfig) -> None:
    """Write the geographic summary as Delta."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def write_metadata(
    *,
    config: PowerBIGeographicSummaryConfig,
    summary_df: DataFrame,
    logger: logging.Logger,
) -> None:
    """Write run metadata for reviewer traceability."""
    coordinate_rows = int(summary_df.filter(col("geo_coordinates_available") == 1).count())
    metadata = {
        "workflow": WORKFLOW_NAME,
        "issue": "#51",
        "source_ao3_segment_path": config.ao3_segment_path,
        "source_customer_regional_feature_path": config.customer_regional_feature_path,
        "output_path": config.geographic_summary_output_path,
        "row_count": int(summary_df.count()),
        "coordinate_available_group_count": coordinate_rows,
        "location_grain": "order destination country/region/state plus rounded latitude/longitude",
        "target_or_outcome_columns_used": False,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.metadata_output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote Power BI geographic summary metadata: %s", config.metadata_output_path)


def run_powerbi_geographic_summary(
    config: PowerBIGeographicSummaryConfig,
    logger: logging.Logger,
) -> None:
    """Build and write the Power BI geographic summary table."""
    config = with_repo_defaults(config)
    spark = get_spark_session()

    logger.info("Starting Power BI geographic summary build.")
    logger.info("AO3 segment input path: %s", config.ao3_segment_path)
    logger.info("Customer/regional feature input path: %s", config.customer_regional_feature_path)
    logger.info("Geographic summary output path: %s", config.geographic_summary_output_path)

    ao3_df = read_delta(spark, config.ao3_segment_path, config)
    geographic_df = read_delta(spark, config.customer_regional_feature_path, config)
    validate_source_contracts(ao3_df, geographic_df)

    summary_df = build_geographic_summary_dataframe(ao3_df, geographic_df)
    validate_geographic_summary_output(summary_df)
    write_delta(summary_df, config.geographic_summary_output_path, config)

    written_df = read_delta(spark, config.geographic_summary_output_path, config)
    validate_geographic_summary_output(written_df)
    write_metadata(config=config, summary_df=written_df, logger=logger)

    logger.info("Power BI geographic summary build completed with %d rows.", written_df.count())


def main() -> None:
    """Run the Power BI geographic summary job."""
    run_powerbi_geographic_summary(PowerBIGeographicSummaryConfig(), configure_logging())


if __name__ == "__main__":
    main()
