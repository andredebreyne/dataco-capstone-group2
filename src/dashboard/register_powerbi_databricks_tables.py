"""Register curated Power BI serving tables in Databricks SQL.

This Databricks-compatible script publishes the same logical artifacts used by
``dashboard/exports`` as managed ``workspace.default.powerbi_*`` tables. The
purpose is to let Power BI Desktop connect through the Azure Databricks
connector instead of relying only on local CSV imports.

The script does not recreate AO1/AO2 scores, retune thresholds, recalculate AO3
margins, reassign AO3 segments, union unrelated artifacts, or expose final-test
target/outcome columns. It only publishes governed outputs for dashboard
consumption.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_CATALOG = os.getenv("DATACO_POWERBI_SERVING_CATALOG", "workspace")
DEFAULT_SCHEMA = os.getenv("DATACO_POWERBI_SERVING_SCHEMA", "default")
WORKFLOW_NAME = "powerbi_databricks_serving_layer_registration"

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}

AO1_AO2_SCORE_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "split_partition",
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
)

AO3_SEGMENT_COLUMNS = (
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
    "ao3_policy_name",
    "ao3_risk_cutoff",
    "ao3_margin_cutoff",
    "ao3_high_risk_flag",
    "ao3_high_margin_flag",
    "ao3_priority_segment",
    "ao3_segment_assignment_timestamp_utc",
)


@dataclass(frozen=True)
class PowerBIDatabricksTableSpec:
    """Registration contract for one Power BI serving table."""

    table_name: str
    source_type: str
    source_path: str
    artifact_category: str
    description: str
    dashboard_columns: tuple[str, ...] | None = None


@dataclass(frozen=True)
class PowerBIDatabricksRegistrationConfig:
    """Configuration for Databricks SQL Power BI serving-layer registration."""

    catalog: str = DEFAULT_CATALOG
    schema: str = DEFAULT_SCHEMA
    ao1_ao2_score_path: str = os.getenv(
        "DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH",
        f"{VOLUME_ROOT}/gold/ao1_ao2_test_scores",
    )
    ao3_segment_path: str = os.getenv(
        "DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH",
        f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments",
    )
    geographic_summary_path: str = os.getenv(
        "DATACO_POWERBI_GEOGRAPHIC_SUMMARY_OUTPUT_PATH",
        f"{VOLUME_ROOT}/gold/powerbi_geographic_summary",
    )
    logistics_kpi_summary_path: str = os.getenv(
        "DATACO_POWERBI_LOGISTICS_KPI_SUMMARY_OUTPUT_PATH",
        f"{VOLUME_ROOT}/gold/powerbi_logistics_kpi_summary",
    )
    repo_root: Path = Path(
        os.getenv("DATACO_REPO_ROOT", str(Path.cwd()))
    ).expanduser().resolve()


def configure_logging() -> logging.Logger:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_databricks_registration")


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
    """Resolve repository root for Databricks Repos and local execution."""
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


def with_repo_defaults(
    config: PowerBIDatabricksRegistrationConfig,
) -> PowerBIDatabricksRegistrationConfig:
    """Use repository-root defaults when environment overrides are absent."""
    return PowerBIDatabricksRegistrationConfig(
        catalog=config.catalog,
        schema=config.schema,
        ao1_ao2_score_path=config.ao1_ao2_score_path,
        ao3_segment_path=config.ao3_segment_path,
        geographic_summary_path=config.geographic_summary_path,
        logistics_kpi_summary_path=config.logistics_kpi_summary_path,
        repo_root=resolve_repo_root(),
    )


def build_table_specs(config: PowerBIDatabricksRegistrationConfig) -> tuple[PowerBIDatabricksTableSpec, ...]:
    """Return the governed Power BI serving table publication contract."""
    repo_root = config.repo_root
    return (
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao3_order_segments",
            source_type="delta",
            source_path=config.ao3_segment_path,
            artifact_category="gold_delta_dashboard_fact",
            description="AO3 order-level risk-margin segment fact table.",
            dashboard_columns=AO3_SEGMENT_COLUMNS,
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao1_ao2_test_scores",
            source_type="delta",
            source_path=config.ao1_ao2_score_path,
            artifact_category="gold_delta_dashboard_fact",
            description="Integrated AO1/AO2 held-out prediction table used upstream of AO3.",
            dashboard_columns=AO1_AO2_SCORE_COLUMNS,
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_geographic_summary",
            source_type="delta",
            source_path=config.geographic_summary_path,
            artifact_category="gold_delta_dashboard_summary",
            description="Map-ready Power BI geographic summary with destination text and rounded coordinates.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_logistics_kpi_summary",
            source_type="delta",
            source_path=config.logistics_kpi_summary_path,
            artifact_category="gold_delta_dashboard_summary",
            description="Power BI logistics KPI risk exposure summary with historical KPI context and governed AO1/AO2/AO3 exposure fields.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao1_decision_threshold_policy",
            source_type="csv",
            source_path=str(repo_root / "data/references/ao1_decision_threshold_policy.csv"),
            artifact_category="reference_csv",
            description="Approved AO1 operating threshold policy.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao1_ao2_test_score_summary",
            source_type="csv",
            source_path=str(repo_root / "data/references/ao1_ao2_test_score_summary.csv"),
            artifact_category="reference_csv",
            description="AO1/AO2 test-score summary artifact.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao3_risk_margin_policy",
            source_type="csv",
            source_path=str(repo_root / "data/references/ao3_risk_margin_matrix_policy.csv"),
            artifact_category="reference_csv",
            description="Governed AO3 risk-margin matrix policy.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao3_segment_summary",
            source_type="csv",
            source_path=str(repo_root / "data/references/ao3_segment_summary.csv"),
            artifact_category="reference_csv",
            description="AO3 segment count and average-score summary.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao3_benchmark_segment_summary",
            source_type="csv",
            source_path=str(repo_root / "data/references/ao3_risk_margin_benchmark_segment_summary.csv"),
            artifact_category="reference_csv",
            description="AO3 benchmark segment summary.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao3_benchmark_insights",
            source_type="csv",
            source_path=str(repo_root / "data/references/ao3_risk_margin_benchmark_insights.csv"),
            artifact_category="reference_csv",
            description="AO3 benchmark insight table.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao3_operational_recommendations",
            source_type="csv",
            source_path=str(repo_root / "data/references/ao3_operational_recommendation_matrix.csv"),
            artifact_category="reference_csv",
            description="AO3 operational recommendation matrix by segment.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao1_model_validation",
            source_type="csv",
            source_path=str(repo_root / "report/tables/ao1_model_validation_comparison.csv"),
            artifact_category="report_csv",
            description="AO1 validation-stage model comparison table.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao1_threshold_tradeoff",
            source_type="csv",
            source_path=str(repo_root / "report/tables/ao1_threshold_tradeoff_grid.csv"),
            artifact_category="report_csv",
            description="AO1 validation threshold trade-off grid.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao1_confusion_by_threshold",
            source_type="csv",
            source_path=str(repo_root / "report/tables/ao1_confusion_matrix_by_threshold.csv"),
            artifact_category="report_csv",
            description="AO1 confusion matrix by validation threshold.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao2_model_validation",
            source_type="csv",
            source_path=str(repo_root / "report/tables/ao2_model_validation_comparison.csv"),
            artifact_category="report_csv",
            description="AO2 validation-stage model comparison table.",
        ),
        PowerBIDatabricksTableSpec(
            table_name="powerbi_ao2_evaluation_metrics",
            source_type="csv",
            source_path=str(repo_root / "report/tables/ao2_model_evaluation_metrics.csv"),
            artifact_category="report_csv",
            description="AO2 validation diagnostic metrics table.",
        ),
    )


def full_table_name(config: PowerBIDatabricksRegistrationConfig, table_name: str) -> str:
    """Return fully qualified Databricks table name."""
    return f"{config.catalog}.{config.schema}.{table_name}"


def assert_no_forbidden_targets(df: DataFrame, table_name: str) -> None:
    """Prevent target and realized-outcome fields from entering Power BI serving tables."""
    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(df.columns))
    if forbidden_columns:
        raise ValueError(f"{table_name} contains forbidden target/outcome columns: {forbidden_columns}")


def assert_required_columns(df: DataFrame, columns: tuple[str, ...], table_name: str) -> None:
    """Validate that a serving table source contains the governed dashboard columns."""
    missing_columns = sorted(column for column in columns if column not in df.columns)
    if missing_columns:
        raise ValueError(f"{table_name} is missing required serving-layer columns: {missing_columns}")


def project_dashboard_columns(df: DataFrame, spec: PowerBIDatabricksTableSpec) -> DataFrame:
    """Apply dashboard-safe column projection before publishing serving tables."""
    assert_no_forbidden_targets(df, spec.table_name)
    if spec.dashboard_columns is None:
        return df
    assert_required_columns(df, spec.dashboard_columns, spec.table_name)
    return df.select(*spec.dashboard_columns)


def read_source_dataframe(spark: SparkSession, spec: PowerBIDatabricksTableSpec) -> DataFrame:
    """Read one governed source artifact as a Spark DataFrame."""
    if spec.source_type == "delta":
        return spark.read.format("delta").load(spec.source_path)

    if spec.source_type == "csv":
        source_path = Path(spec.source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Missing CSV artifact for Power BI serving layer: {source_path}")
        return (
            spark.read.option("header", True)
            .option("inferSchema", True)
            .csv(str(source_path))
        )

    raise ValueError(f"Unsupported source type for {spec.table_name}: {spec.source_type}")


def publish_table(
    *,
    spark: SparkSession,
    config: PowerBIDatabricksRegistrationConfig,
    spec: PowerBIDatabricksTableSpec,
) -> dict[str, object]:
    """Publish one artifact as a managed Databricks SQL serving table."""
    source_df = read_source_dataframe(spark, spec)
    serving_df = project_dashboard_columns(source_df, spec)

    target_table = full_table_name(config, spec.table_name)
    (
        serving_df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table)
    )

    written_df = spark.table(target_table)
    return {
        "serving_catalog": config.catalog,
        "serving_schema": config.schema,
        "target_table": target_table,
        "table_name": spec.table_name,
        "source_type": spec.source_type,
        "source_path": spec.source_path,
        "artifact_category": spec.artifact_category,
        "row_count": int(written_df.count()),
        "column_count": len(written_df.columns),
        "run_status": "success",
        "description": spec.description,
    }


def run_powerbi_databricks_registration(
    config: PowerBIDatabricksRegistrationConfig,
    logger: logging.Logger,
) -> None:
    """Create or replace the managed Databricks SQL serving tables for Power BI."""
    config = with_repo_defaults(config)
    spark = get_spark_session()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {config.catalog}.{config.schema}")

    logger.info("Starting Power BI Databricks serving-layer registration.")
    logger.info("Target schema: %s.%s", config.catalog, config.schema)
    logger.info("Repository root: %s", config.repo_root)

    generated_timestamp_utc = datetime.now(timezone.utc).isoformat()
    summary_rows: list[dict[str, object]] = []
    for spec in build_table_specs(config):
        summary_row = publish_table(spark=spark, config=config, spec=spec)
        summary_row["generated_timestamp_utc"] = generated_timestamp_utc
        summary_row["workflow_name"] = WORKFLOW_NAME
        summary_rows.append(summary_row)
        logger.info(
            "Published %s with %d rows and %d columns.",
            summary_row["target_table"],
            summary_row["row_count"],
            summary_row["column_count"],
        )

    summary_df = spark.createDataFrame(
        summary_rows,
    )
    summary_table = full_table_name(config, "powerbi_serving_layer_manifest")
    (
        summary_df.write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(summary_table)
    )

    logger.info("Published Power BI serving-layer manifest: %s", summary_table)
    logger.info("Power BI Databricks serving-layer registration completed successfully.")


def main() -> None:
    """Run the Power BI Databricks serving-layer registration job."""
    run_powerbi_databricks_registration(
        PowerBIDatabricksRegistrationConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
