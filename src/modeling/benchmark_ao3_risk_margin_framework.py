"""Benchmark AO3 risk-margin segments against single-signal prioritization.

This job consumes the AO3 segment table from Issue #42 and compares the combined
risk-margin view against risk-only and margin-only prioritization. It produces
review artifacts for H3 without training models, changing thresholds, or using
actual final-test target outcomes.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import avg, col, lit, sum as spark_sum, when
from pyspark.sql.window import Window


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
SEGMENT_INPUT_PATH = os.getenv(
    "DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments",
)

FORBIDDEN_TARGET_COLUMNS = (
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
)

REQUIRED_COLUMNS = (
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
)

VALID_SEGMENTS = (
    "protect_high_value_at_risk",
    "expedite_selectively",
    "preserve_service",
    "standard_process",
    "requires_score_review",
    "requires_margin_review",
)

SEGMENT_SUMMARY_COLUMNS = (
    "ao3_priority_segment",
    "row_count",
    "share_of_rows",
    "avg_ao1_predicted_late_delivery_probability",
    "avg_ao2_predicted_order_profit",
    "avg_ao3_predicted_margin",
)

CROSSWALK_COLUMNS = (
    "priority_signal",
    "single_signal_group",
    "ao3_priority_segment",
    "row_count",
    "share_of_single_signal_group",
    "avg_ao1_predicted_late_delivery_probability",
    "avg_ao2_predicted_order_profit",
    "avg_ao3_predicted_margin",
)

INSIGHT_COLUMNS = (
    "metric_name",
    "metric_value",
    "decision_relevance",
)


@dataclass(frozen=True)
class AO3RiskMarginBenchmarkConfig:
    """Configuration for AO3 risk-margin benchmark artifacts."""

    segment_input_path: str = SEGMENT_INPUT_PATH
    segment_summary_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_BENCHMARK_SEGMENT_SUMMARY_PATH",
            str(Path.cwd() / "data/references/ao3_risk_margin_benchmark_segment_summary.csv"),
        )
    )
    crosswalk_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_BENCHMARK_CROSSWALK_PATH",
            str(Path.cwd() / "data/references/ao3_risk_margin_benchmark_crosswalk.csv"),
        )
    )
    insight_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_BENCHMARK_INSIGHT_PATH",
            str(Path.cwd() / "data/references/ao3_risk_margin_benchmark_insights.csv"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_BENCHMARK_METADATA_PATH",
            str(
                Path.cwd()
                / "models/ao3_integration/risk_margin_benchmark/ao3_risk_margin_benchmark_metadata.json"
            ),
        )
    )
    read_format: str = "delta"


def configure_logging() -> logging.Logger:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao3_risk_margin_benchmark")


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
    """Resolve repository root for local artifact outputs."""
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


def with_repo_defaults(config: AO3RiskMarginBenchmarkConfig) -> AO3RiskMarginBenchmarkConfig:
    """Replace cwd-based artifact defaults with repository-root defaults."""
    repo_root = resolve_repo_root()
    return AO3RiskMarginBenchmarkConfig(
        segment_input_path=config.segment_input_path,
        segment_summary_output_path=Path(
            os.getenv(
                "DATACO_AO3_BENCHMARK_SEGMENT_SUMMARY_PATH",
                str(repo_root / "data/references/ao3_risk_margin_benchmark_segment_summary.csv"),
            )
        ),
        crosswalk_output_path=Path(
            os.getenv(
                "DATACO_AO3_BENCHMARK_CROSSWALK_PATH",
                str(repo_root / "data/references/ao3_risk_margin_benchmark_crosswalk.csv"),
            )
        ),
        insight_output_path=Path(
            os.getenv(
                "DATACO_AO3_BENCHMARK_INSIGHT_PATH",
                str(repo_root / "data/references/ao3_risk_margin_benchmark_insights.csv"),
            )
        ),
        metadata_output_path=Path(
            os.getenv(
                "DATACO_AO3_BENCHMARK_METADATA_PATH",
                str(
                    repo_root
                    / "models/ao3_integration/risk_margin_benchmark/ao3_risk_margin_benchmark_metadata.json"
                ),
            )
        ),
        read_format=config.read_format,
    )


def validate_input_contract(df: DataFrame) -> None:
    """Validate AO3 benchmark input columns and leakage exclusions."""
    missing_columns = sorted(column for column in REQUIRED_COLUMNS if column not in df.columns)
    if missing_columns:
        raise ValueError(f"AO3 benchmark input missing required columns: {missing_columns}")

    forbidden_columns = sorted(column for column in FORBIDDEN_TARGET_COLUMNS if column in df.columns)
    if forbidden_columns:
        raise ValueError(f"AO3 benchmark input contains target/outcome columns: {forbidden_columns}")

    row_count = df.count()
    if row_count == 0:
        raise ValueError("AO3 benchmark input contains no rows.")

    non_test_count = df.filter(
        (col("split_partition") != lit("test")) | (col("ao2_split_partition") != lit("test"))
    ).count()
    if non_test_count:
        raise ValueError(f"AO3 benchmark input contains non-test rows: {non_test_count}")

    invalid_segment_count = df.filter(~col("ao3_priority_segment").isin(*VALID_SEGMENTS)).count()
    if invalid_segment_count:
        raise ValueError(f"AO3 benchmark input contains invalid segments: {invalid_segment_count}")


def add_single_signal_groups(df: DataFrame) -> DataFrame:
    """Add risk-only and margin-only priority groups for comparison."""
    return (
        df.withColumn(
            "risk_only_group",
            when(col("ao3_high_risk_flag").isNull(), lit("requires_score_review"))
            .when(col("ao3_high_risk_flag"), lit("high_risk"))
            .otherwise(lit("low_risk")),
        )
        .withColumn(
            "margin_only_group",
            when(col("ao3_high_margin_flag").isNull(), lit("requires_margin_review"))
            .when(col("ao3_high_margin_flag"), lit("high_margin"))
            .otherwise(lit("low_margin")),
        )
    )


def rows_from_df(df: DataFrame) -> list[dict[str, object]]:
    """Convert a Spark DataFrame to plain dict rows."""
    return [row.asDict(recursive=True) for row in df.collect()]


def build_segment_summary(df: DataFrame) -> list[dict[str, object]]:
    """Build AO3 segment summary rows."""
    total_rows = df.count()
    summary_df = df.groupBy("ao3_priority_segment").agg(
        spark_sum(lit(1)).alias("row_count"),
        avg("ao1_predicted_late_delivery_probability").alias(
            "avg_ao1_predicted_late_delivery_probability"
        ),
        avg("ao2_predicted_order_profit").alias("avg_ao2_predicted_order_profit"),
        avg("ao3_predicted_margin").alias("avg_ao3_predicted_margin"),
    )

    rows_by_segment = {}
    for row in rows_from_df(summary_df):
        row_count = int(row["row_count"])
        rows_by_segment[row["ao3_priority_segment"]] = {
            "ao3_priority_segment": row["ao3_priority_segment"],
            "row_count": row_count,
            "share_of_rows": row_count / total_rows if total_rows else 0.0,
            "avg_ao1_predicted_late_delivery_probability": row[
                "avg_ao1_predicted_late_delivery_probability"
            ],
            "avg_ao2_predicted_order_profit": row["avg_ao2_predicted_order_profit"],
            "avg_ao3_predicted_margin": row["avg_ao3_predicted_margin"],
        }

    for segment in VALID_SEGMENTS:
        rows_by_segment.setdefault(
            segment,
            {
                "ao3_priority_segment": segment,
                "row_count": 0,
                "share_of_rows": 0.0,
                "avg_ao1_predicted_late_delivery_probability": None,
                "avg_ao2_predicted_order_profit": None,
                "avg_ao3_predicted_margin": None,
            },
        )

    return sorted(rows_by_segment.values(), key=lambda item: str(item["ao3_priority_segment"]))


def build_crosswalk(df: DataFrame) -> list[dict[str, object]]:
    """Build single-signal-to-AO3 segment crosswalk rows."""
    risk_rows = build_single_signal_crosswalk(df, "risk_only", "risk_only_group")
    margin_rows = build_single_signal_crosswalk(df, "margin_only", "margin_only_group")
    return sorted(risk_rows + margin_rows, key=lambda item: tuple(str(value) for value in item.values()))


def build_single_signal_crosswalk(
    df: DataFrame,
    priority_signal: str,
    group_column: str,
) -> list[dict[str, object]]:
    """Summarize how one single-signal group splits across AO3 segments."""
    group_window = Window.partitionBy(group_column)
    crosswalk_df = (
        df.groupBy(group_column, "ao3_priority_segment")
        .agg(
            spark_sum(lit(1)).alias("row_count"),
            avg("ao1_predicted_late_delivery_probability").alias(
                "avg_ao1_predicted_late_delivery_probability"
            ),
            avg("ao2_predicted_order_profit").alias("avg_ao2_predicted_order_profit"),
            avg("ao3_predicted_margin").alias("avg_ao3_predicted_margin"),
        )
        .withColumn("single_signal_group_count", spark_sum("row_count").over(group_window))
        .withColumn("share_of_single_signal_group", col("row_count") / col("single_signal_group_count"))
    )

    rows = []
    for row in rows_from_df(crosswalk_df):
        rows.append(
            {
                "priority_signal": priority_signal,
                "single_signal_group": row[group_column],
                "ao3_priority_segment": row["ao3_priority_segment"],
                "row_count": int(row["row_count"]),
                "share_of_single_signal_group": row["share_of_single_signal_group"],
                "avg_ao1_predicted_late_delivery_probability": row[
                    "avg_ao1_predicted_late_delivery_probability"
                ],
                "avg_ao2_predicted_order_profit": row["avg_ao2_predicted_order_profit"],
                "avg_ao3_predicted_margin": row["avg_ao3_predicted_margin"],
            }
        )
    return rows


def count_where(df: DataFrame, condition) -> int:
    """Count rows matching a Spark condition."""
    return int(df.filter(condition).count())


def build_insights(df: DataFrame) -> list[dict[str, object]]:
    """Build compact decision-relevant benchmark metrics."""
    total_rows = df.count()
    high_risk_count = count_where(df, col("risk_only_group") == lit("high_risk"))
    high_margin_count = count_where(df, col("margin_only_group") == lit("high_margin"))
    protect_count = count_where(df, col("ao3_priority_segment") == lit("protect_high_value_at_risk"))
    expedite_count = count_where(df, col("ao3_priority_segment") == lit("expedite_selectively"))
    preserve_count = count_where(df, col("ao3_priority_segment") == lit("preserve_service"))

    high_risk_high_margin_share = protect_count / high_risk_count if high_risk_count else 0.0
    high_risk_low_margin_share = expedite_count / high_risk_count if high_risk_count else 0.0
    high_margin_high_risk_share = protect_count / high_margin_count if high_margin_count else 0.0
    high_margin_low_risk_share = preserve_count / high_margin_count if high_margin_count else 0.0

    return [
        {
            "metric_name": "total_scored_orders",
            "metric_value": total_rows,
            "decision_relevance": "Benchmark population size from the AO3 held-out segment table.",
        },
        {
            "metric_name": "high_risk_orders",
            "metric_value": high_risk_count,
            "decision_relevance": "Orders that risk-only prioritization would group together.",
        },
        {
            "metric_name": "high_risk_share_high_margin",
            "metric_value": high_risk_high_margin_share,
            "decision_relevance": "Share of high-risk orders that AO3 separates as high-margin protection priorities.",
        },
        {
            "metric_name": "high_risk_share_low_margin",
            "metric_value": high_risk_low_margin_share,
            "decision_relevance": "Share of high-risk orders that AO3 separates as selective-expedite candidates.",
        },
        {
            "metric_name": "high_margin_orders",
            "metric_value": high_margin_count,
            "decision_relevance": "Orders that margin-only prioritization would group together.",
        },
        {
            "metric_name": "high_margin_share_high_risk",
            "metric_value": high_margin_high_risk_share,
            "decision_relevance": "Share of high-margin orders that AO3 elevates because delivery risk is also high.",
        },
        {
            "metric_name": "high_margin_share_low_risk",
            "metric_value": high_margin_low_risk_share,
            "decision_relevance": "Share of high-margin orders that AO3 keeps in preserve-service rather than urgent intervention.",
        },
        {
            "metric_name": "h3_support_statement",
            "metric_value": (
                "AO3 adds decision-layer value mainly by splitting high-margin orders into high-risk "
                "protection priorities and low-risk preserve-service orders; risk-only differentiation "
                "should be interpreted from the observed split in this held-out sample."
            ),
            "decision_relevance": (
                "Supports H3 as a practical prioritization comparison, without overstating causal impact "
                "or final-test outcome performance."
            ),
        },
    ]


def write_csv(rows: list[dict[str, object]], fieldnames: tuple[str, ...], output_path: Path) -> None:
    """Write rows to CSV with a stable schema."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metadata(
    *,
    config: AO3RiskMarginBenchmarkConfig,
    row_count: int,
    insight_rows: list[dict[str, object]],
) -> None:
    """Write AO3 benchmark metadata."""
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "issue": "#43",
        "workflow": "ao3_risk_margin_framework_benchmark",
        "segment_input_path": config.segment_input_path,
        "segment_summary_output_path": str(config.segment_summary_output_path),
        "crosswalk_output_path": str(config.crosswalk_output_path),
        "insight_output_path": str(config.insight_output_path),
        "row_count": row_count,
        "comparison_signals": ["ao3_combined", "risk_only", "margin_only"],
        "input_source": "Issue #42 AO3 risk-margin segment table",
        "same_held_out_scored_data_as_ao3": True,
        "final_test_targets_used_for_benchmark": False,
        "performance_metrics_calculated": False,
        "h3_support_statement": next(
            row["metric_value"] for row in insight_rows if row["metric_name"] == "h3_support_statement"
        ),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    config.metadata_output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def run_ao3_risk_margin_benchmark(
    config: AO3RiskMarginBenchmarkConfig,
    logger: logging.Logger,
) -> None:
    """Execute the AO3 risk-margin benchmark workflow."""
    config = with_repo_defaults(config)
    spark = get_spark_session()

    logger.info("Starting AO3 risk-margin framework benchmark.")
    logger.info("Segment input path: %s", config.segment_input_path)

    segment_df = spark.read.format(config.read_format).load(config.segment_input_path)
    validate_input_contract(segment_df)

    benchmark_df = add_single_signal_groups(segment_df)
    segment_summary_rows = build_segment_summary(benchmark_df)
    crosswalk_rows = build_crosswalk(benchmark_df)
    insight_rows = build_insights(benchmark_df)

    write_csv(segment_summary_rows, SEGMENT_SUMMARY_COLUMNS, config.segment_summary_output_path)
    write_csv(crosswalk_rows, CROSSWALK_COLUMNS, config.crosswalk_output_path)
    write_csv(insight_rows, INSIGHT_COLUMNS, config.insight_output_path)
    write_metadata(config=config, row_count=benchmark_df.count(), insight_rows=insight_rows)

    logger.info("AO3 risk-margin framework benchmark completed successfully.")


def main() -> None:
    """Run AO3 risk-margin benchmark with default configuration."""
    run_ao3_risk_margin_benchmark(AO3RiskMarginBenchmarkConfig(), configure_logging())


if __name__ == "__main__":
    main()
