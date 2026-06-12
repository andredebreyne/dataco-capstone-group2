"""Enrich Power BI geographic segment summary with decision-profile fields.

This Databricks-compatible job reads the granular geography serving table built
for Issue #145 and adds Power BI-friendly decision fields. The enrichment is a
serving-layer interpretation on top of governed AO1, AO2, and AO3 outputs. It
keeps the official AO3 policy unchanged.
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
from pyspark.sql.functions import col, current_timestamp, lit, when
from pyspark.sql.types import IntegerType, StringType


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_SEGMENT_SUMMARY_PATH = os.getenv(
    "DATACO_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_geographic_segment_summary",
)

WORKFLOW_NAME = "powerbi_geographic_decision_enrichment"

REQUIRED_COLUMNS = (
    "map_location_country",
    "map_location_region",
    "map_location_state",
    "map_latitude",
    "map_longitude",
    "geo_coordinates_available",
    "order_date_key",
    "order_week_key",
    "order_month_key",
    "ao3_priority_segment",
    "ao1_high_risk_flag",
    "ao2_expected_profit_band",
    "order_item_count",
    "high_risk_order_rate",
    "avg_ao3_predicted_margin",
    "total_order_value",
)

ENRICHED_COLUMNS = (
    "ao3_priority_segment_label",
    "ao3_priority_segment_sort_order",
    "ao1_high_risk_label",
    "ao1_high_risk_sort_order",
    "ao2_expected_profit_band_sort_order",
    "ao2_margin_policy_tier",
    "ao2_margin_policy_tier_sort_order",
    "geo_data_quality_status",
    "geo_exposure_tier",
    "geo_exposure_tier_sort_order",
    "geo_risk_intensity_tier",
    "geo_risk_intensity_tier_sort_order",
    "geo_decision_archetype",
    "geo_decision_archetype_sort_order",
    "geo_recommended_focus",
    "powerbi_geographic_decision_enrichment_timestamp_utc",
)

PROFIT_BANDS = (
    "Negative Profit",
    "$0 - $10",
    "$10 - $25",
    "$25 - $50",
    "$50 - $100",
    "$100+",
)

MARGIN_POLICY_TIERS = (
    "Loss or Negative Margin",
    "Low Positive Margin",
    "Core Positive Margin",
    "Strategic Positive Margin",
)

GEO_DECISION_ARCHETYPES = (
    "Priority Protection Geography",
    "Selective Recovery Review",
    "Preserve Service Geography",
    "Standard Monitoring Geography",
    "Operational Monitoring Geography",
    "Data Quality Review",
)


@dataclass(frozen=True)
class PowerBIGeographicDecisionEnrichmentConfig:
    """Configuration for the P04 geographic decision enrichment job."""

    input_path: str = DEFAULT_SEGMENT_SUMMARY_PATH
    output_path: str = DEFAULT_SEGMENT_SUMMARY_PATH
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_POWERBI_GEOGRAPHIC_DECISION_ENRICHMENT_METADATA_PATH",
            str(Path.cwd() / "models/dashboard/powerbi_geographic_decision_enrichment_metadata.json"),
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
    return logging.getLogger("dataco.powerbi_geographic_decision_enrichment")


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


def with_repo_defaults(
    config: PowerBIGeographicDecisionEnrichmentConfig,
) -> PowerBIGeographicDecisionEnrichmentConfig:
    """Use repository-root metadata defaults when environment overrides are absent."""
    repo_root = resolve_repo_root()
    return PowerBIGeographicDecisionEnrichmentConfig(
        input_path=config.input_path,
        output_path=config.output_path,
        metadata_output_path=Path(
            os.getenv(
                "DATACO_POWERBI_GEOGRAPHIC_DECISION_ENRICHMENT_METADATA_PATH",
                str(repo_root / "models/dashboard/powerbi_geographic_decision_enrichment_metadata.json"),
            )
        ),
        read_format=config.read_format,
        write_format=config.write_format,
        write_mode=config.write_mode,
    )


def assert_required_columns(df: DataFrame, required_columns: tuple[str, ...], table_name: str) -> None:
    """Validate required columns."""
    missing_columns = sorted(column for column in required_columns if column not in df.columns)
    if missing_columns:
        raise ValueError(f"{table_name} is missing required columns: {missing_columns}")


def metric_quantiles(df: DataFrame, column_name: str, probabilities: list[float]) -> list[float]:
    """Return approximate quantiles with a defensive fallback."""
    quantiles = df.approxQuantile(column_name, probabilities, 0.01)
    if len(quantiles) != len(probabilities):
        return [0.0 for _ in probabilities]
    return [float(value) for value in quantiles]


def segment_label_expression() -> object:
    """Return display labels for AO3 segment slicers."""
    segment = col("ao3_priority_segment")
    return (
        when(segment == "protect_high_value_at_risk", lit("Protect High-Value at Risk"))
        .when(segment == "expedite_selectively", lit("Expedite Selectively"))
        .when(segment == "preserve_service", lit("Preserve Service"))
        .when(segment == "standard_process", lit("Standard Process"))
        .when(segment == "requires_score_review", lit("Requires Score Review"))
        .when(segment == "requires_margin_review", lit("Requires Margin Review"))
        .otherwise(lit("Unknown Segment"))
    )


def segment_sort_expression() -> object:
    """Return display sort order for AO3 segment slicers."""
    segment = col("ao3_priority_segment")
    return (
        when(segment == "protect_high_value_at_risk", lit(1))
        .when(segment == "expedite_selectively", lit(2))
        .when(segment == "preserve_service", lit(3))
        .when(segment == "standard_process", lit(4))
        .otherwise(lit(99))
        .cast(IntegerType())
    )


def high_risk_label_expression() -> object:
    """Return display label for AO1 high-risk flag."""
    return when(col("ao1_high_risk_flag"), lit("High Delivery Risk")).otherwise(lit("Standard Delivery Risk"))


def profit_band_sort_expression() -> object:
    """Return display sort order for expected-profit bands."""
    band = col("ao2_expected_profit_band")
    return (
        when(band == "Negative Profit", lit(1))
        .when(band == "$0 - $10", lit(2))
        .when(band == "$10 - $25", lit(3))
        .when(band == "$25 - $50", lit(4))
        .when(band == "$50 - $100", lit(5))
        .when(band == "$100+", lit(6))
        .otherwise(lit(99))
        .cast(IntegerType())
    )


def margin_policy_tier_expression(median_positive_margin: float, upper_positive_margin: float) -> object:
    """Return decision tier for margin granularity inside the positive-margin population."""
    margin = col("avg_ao3_predicted_margin")
    return (
        when(margin < 0, lit("Loss or Negative Margin"))
        .when(margin < lit(median_positive_margin), lit("Low Positive Margin"))
        .when(margin < lit(upper_positive_margin), lit("Core Positive Margin"))
        .otherwise(lit("Strategic Positive Margin"))
    )


def margin_policy_sort_expression() -> object:
    """Return display sort order for margin policy tiers."""
    tier = col("ao2_margin_policy_tier")
    return (
        when(tier == "Loss or Negative Margin", lit(1))
        .when(tier == "Low Positive Margin", lit(2))
        .when(tier == "Core Positive Margin", lit(3))
        .when(tier == "Strategic Positive Margin", lit(4))
        .otherwise(lit(99))
        .cast(IntegerType())
    )


def geography_quality_expression() -> object:
    """Return geography data-quality status for filtering and governance."""
    unknown_geography = (
        (col("map_location_country") == "unknown_country")
        | (col("map_location_region") == "unknown_region")
        | (col("map_location_state") == "unknown_state")
    )
    return (
        when(unknown_geography, lit("Unknown Geography"))
        .when(col("geo_coordinates_available") == 0, lit("Missing Coordinates"))
        .otherwise(lit("Complete Coordinates"))
    )


def exposure_tier_expression(low_threshold: float, high_threshold: float) -> object:
    """Return geography exposure tier based on order value."""
    value = col("total_order_value")
    return (
        when(value >= lit(high_threshold), lit("High Exposure Geography"))
        .when(value >= lit(low_threshold), lit("Medium Exposure Geography"))
        .otherwise(lit("Low Exposure Geography"))
    )


def risk_intensity_expression(low_threshold: float, high_threshold: float) -> object:
    """Return geography risk-intensity tier based on high-risk rate."""
    rate = col("high_risk_order_rate")
    return (
        when(rate >= lit(high_threshold), lit("High Risk Intensity"))
        .when(rate >= lit(low_threshold), lit("Moderate Risk Intensity"))
        .otherwise(lit("Low Risk Intensity"))
    )


def decision_archetype_expression() -> object:
    """Return executive decision archetype for geographic filtering."""
    return (
        when(col("geo_data_quality_status") != "Complete Coordinates", lit("Data Quality Review"))
        .when(
            (col("ao3_priority_segment") == "protect_high_value_at_risk")
            & col("geo_exposure_tier").isin("High Exposure Geography", "Medium Exposure Geography")
            & col("geo_risk_intensity_tier").isin("High Risk Intensity", "Moderate Risk Intensity"),
            lit("Priority Protection Geography"),
        )
        .when(col("ao3_priority_segment") == "expedite_selectively", lit("Selective Recovery Review"))
        .when(
            (col("ao3_priority_segment") == "preserve_service")
            & col("ao2_margin_policy_tier").isin("Core Positive Margin", "Strategic Positive Margin"),
            lit("Preserve Service Geography"),
        )
        .when(col("ao3_priority_segment") == "standard_process", lit("Standard Monitoring Geography"))
        .otherwise(lit("Operational Monitoring Geography"))
    )


def archetype_sort_expression() -> object:
    """Return display sort order for geographic decision archetypes."""
    archetype = col("geo_decision_archetype")
    return (
        when(archetype == "Priority Protection Geography", lit(1))
        .when(archetype == "Selective Recovery Review", lit(2))
        .when(archetype == "Preserve Service Geography", lit(3))
        .when(archetype == "Standard Monitoring Geography", lit(4))
        .when(archetype == "Operational Monitoring Geography", lit(5))
        .when(archetype == "Data Quality Review", lit(99))
        .otherwise(lit(100))
        .cast(IntegerType())
    )


def recommended_focus_expression() -> object:
    """Return short recommended focus for executive visuals."""
    archetype = col("geo_decision_archetype")
    return (
        when(archetype == "Priority Protection Geography", lit("Protect Value at Risk"))
        .when(archetype == "Selective Recovery Review", lit("Review Selective Expedite"))
        .when(archetype == "Preserve Service Geography", lit("Preserve Service Quality"))
        .when(archetype == "Standard Monitoring Geography", lit("Standard Monitoring"))
        .when(archetype == "Data Quality Review", lit("Review Geography Data"))
        .otherwise(lit("Monitor Operational Exposure"))
    )


def enrich_geographic_segment_summary(df: DataFrame) -> DataFrame:
    """Return the geographic segment summary with decision-profile fields."""
    assert_required_columns(df, REQUIRED_COLUMNS, "Power BI geographic segment summary")

    positive_margin_df = df.filter(col("avg_ao3_predicted_margin") >= 0)
    margin_median, margin_upper = metric_quantiles(
        positive_margin_df,
        "avg_ao3_predicted_margin",
        [0.50, 0.75],
    )
    exposure_low, exposure_high = metric_quantiles(df, "total_order_value", [0.25, 0.75])
    risk_low, risk_high = metric_quantiles(df, "high_risk_order_rate", [0.33, 0.67])

    return (
        df.withColumn("ao3_priority_segment_label", segment_label_expression().cast(StringType()))
        .withColumn("ao3_priority_segment_sort_order", segment_sort_expression())
        .withColumn("ao1_high_risk_label", high_risk_label_expression().cast(StringType()))
        .withColumn("ao1_high_risk_sort_order", when(col("ao1_high_risk_flag"), lit(1)).otherwise(lit(2)))
        .withColumn("ao2_expected_profit_band_sort_order", profit_band_sort_expression())
        .withColumn(
            "ao2_margin_policy_tier",
            margin_policy_tier_expression(margin_median, margin_upper).cast(StringType()),
        )
        .withColumn("ao2_margin_policy_tier_sort_order", margin_policy_sort_expression())
        .withColumn("geo_data_quality_status", geography_quality_expression().cast(StringType()))
        .withColumn("geo_exposure_tier", exposure_tier_expression(exposure_low, exposure_high).cast(StringType()))
        .withColumn(
            "geo_exposure_tier_sort_order",
            when(col("geo_exposure_tier") == "High Exposure Geography", lit(1))
            .when(col("geo_exposure_tier") == "Medium Exposure Geography", lit(2))
            .otherwise(lit(3))
            .cast(IntegerType()),
        )
        .withColumn("geo_risk_intensity_tier", risk_intensity_expression(risk_low, risk_high).cast(StringType()))
        .withColumn(
            "geo_risk_intensity_tier_sort_order",
            when(col("geo_risk_intensity_tier") == "High Risk Intensity", lit(1))
            .when(col("geo_risk_intensity_tier") == "Moderate Risk Intensity", lit(2))
            .otherwise(lit(3))
            .cast(IntegerType()),
        )
        .withColumn("geo_decision_archetype", decision_archetype_expression().cast(StringType()))
        .withColumn("geo_decision_archetype_sort_order", archetype_sort_expression())
        .withColumn("geo_recommended_focus", recommended_focus_expression().cast(StringType()))
        .withColumn("powerbi_geographic_decision_enrichment_timestamp_utc", current_timestamp())
    )


def validate_enriched_output(df: DataFrame) -> None:
    """Validate enriched output columns and controlled values."""
    assert_required_columns(df, REQUIRED_COLUMNS + ENRICHED_COLUMNS, "enriched geographic segment summary")
    row_count = df.count()
    if row_count == 0:
        raise ValueError("Enriched geographic segment summary contains no rows.")

    invalid_profit_bands = df.filter(~col("ao2_expected_profit_band").isin(*PROFIT_BANDS)).count()
    if invalid_profit_bands:
        raise ValueError(f"Invalid AO2 profit-band rows: {invalid_profit_bands}")

    invalid_margin_tiers = df.filter(~col("ao2_margin_policy_tier").isin(*MARGIN_POLICY_TIERS)).count()
    if invalid_margin_tiers:
        raise ValueError(f"Invalid margin policy tier rows: {invalid_margin_tiers}")

    invalid_archetypes = df.filter(~col("geo_decision_archetype").isin(*GEO_DECISION_ARCHETYPES)).count()
    if invalid_archetypes:
        raise ValueError(f"Invalid geographic decision archetype rows: {invalid_archetypes}")

    missing_enrichment_rows = df.filter(
        col("geo_recommended_focus").isNull()
        | col("geo_exposure_tier").isNull()
        | col("geo_risk_intensity_tier").isNull()
        | col("geo_data_quality_status").isNull()
    ).count()
    if missing_enrichment_rows:
        raise ValueError(f"Rows with missing decision enrichments: {missing_enrichment_rows}")


def write_delta(df: DataFrame, output_path: str, config: PowerBIGeographicDecisionEnrichmentConfig) -> None:
    """Write enriched Delta output."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def write_metadata(
    *,
    config: PowerBIGeographicDecisionEnrichmentConfig,
    enriched_df: DataFrame,
    logger: logging.Logger,
) -> None:
    """Write enrichment metadata."""
    metadata = {
        "workflow": WORKFLOW_NAME,
        "issue": "#145",
        "input_path": config.input_path,
        "output_path": config.output_path,
        "row_count": int(enriched_df.count()),
        "enriched_columns": list(ENRICHED_COLUMNS),
        "official_ao3_policy_changed": False,
        "model_outputs_recomputed": False,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.metadata_output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Wrote geographic decision enrichment metadata: %s", config.metadata_output_path)


def run_powerbi_geographic_decision_enrichment(
    config: PowerBIGeographicDecisionEnrichmentConfig,
    logger: logging.Logger,
) -> None:
    """Run the geographic decision enrichment workflow."""
    config = with_repo_defaults(config)
    spark = get_spark_session()

    logger.info("Starting Power BI geographic decision enrichment.")
    logger.info("Input path: %s", config.input_path)
    logger.info("Output path: %s", config.output_path)

    source_df = spark.read.format(config.read_format).load(config.input_path)
    enriched_df = enrich_geographic_segment_summary(source_df)
    validate_enriched_output(enriched_df)
    write_delta(enriched_df, config.output_path, config)

    written_df = spark.read.format(config.read_format).load(config.output_path)
    validate_enriched_output(written_df)
    write_metadata(config=config, enriched_df=written_df, logger=logger)

    logger.info("Power BI geographic decision enrichment completed with %d rows.", written_df.count())


def main() -> None:
    """Run the Power BI geographic decision enrichment job."""
    run_powerbi_geographic_decision_enrichment(
        PowerBIGeographicDecisionEnrichmentConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
