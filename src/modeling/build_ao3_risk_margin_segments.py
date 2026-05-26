"""Build AO3 risk-margin segment assignments for held-out scored orders.

This job consumes the integrated AO1/AO2 test score table from Issue #41 and
the governed AO3 policy from Issue #40. It assigns AO3 operational segments
without using actual final-test labels or realized profit outcomes.
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
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, sum as spark_sum, when
from pyspark.sql.types import BooleanType, DoubleType, StringType


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

INPUT_SCORE_PATH = os.getenv(
    "DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao1_ao2_test_scores",
)

OUTPUT_SEGMENT_PATH = os.getenv(
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

REQUIRED_INPUT_COLUMNS = (
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


@dataclass(frozen=True)
class AO3RiskMarginSegmentConfig:
    """Configuration for AO3 risk-margin segment assignment."""

    input_score_path: str = INPUT_SCORE_PATH
    output_segment_path: str = OUTPUT_SEGMENT_PATH
    policy_csv_path: Path = Path(
        os.getenv(
            "DATACO_AO3_RISK_MARGIN_POLICY_PATH",
            str(Path.cwd() / "data/references/ao3_risk_margin_matrix_policy.csv"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_SEGMENT_METADATA_PATH",
            str(
                Path.cwd()
                / "models/ao3_integration/risk_margin_segments/ao3_segment_assignment_metadata.json"
            ),
        )
    )
    summary_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_SEGMENT_SUMMARY_PATH",
            str(Path.cwd() / "data/references/ao3_segment_summary.csv"),
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
    return logging.getLogger("dataco.ao3_risk_margin_segments")


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
    """Resolve repository root for artifact outputs."""
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


def with_repo_defaults(config: AO3RiskMarginSegmentConfig) -> AO3RiskMarginSegmentConfig:
    """Replace cwd-based local artifact defaults with repository-root defaults."""
    repo_root = resolve_repo_root()
    return AO3RiskMarginSegmentConfig(
        input_score_path=config.input_score_path,
        output_segment_path=config.output_segment_path,
        policy_csv_path=Path(
            os.getenv(
                "DATACO_AO3_RISK_MARGIN_POLICY_PATH",
                str(repo_root / "data/references/ao3_risk_margin_matrix_policy.csv"),
            )
        ),
        metadata_output_path=Path(
            os.getenv(
                "DATACO_AO3_SEGMENT_METADATA_PATH",
                str(
                    repo_root
                    / "models/ao3_integration/risk_margin_segments/ao3_segment_assignment_metadata.json"
                ),
            )
        ),
        summary_output_path=Path(
            os.getenv(
                "DATACO_AO3_SEGMENT_SUMMARY_PATH",
                str(repo_root / "data/references/ao3_segment_summary.csv"),
            )
        ),
        read_format=config.read_format,
        write_format=config.write_format,
        write_mode=config.write_mode,
    )


def read_policy(policy_csv_path: Path) -> dict[str, str]:
    """Read the one-row AO3 policy CSV."""
    if not policy_csv_path.exists():
        raise FileNotFoundError(f"Missing AO3 policy CSV: {policy_csv_path}")

    with policy_csv_path.open("r", encoding="utf-8", newline="") as policy_file:
        rows = list(csv.DictReader(policy_file))

    if len(rows) != 1:
        raise ValueError(f"AO3 policy CSV must contain exactly one row. Found {len(rows)}.")

    return rows[0]


def validate_policy(policy: dict[str, str]) -> None:
    """Validate required AO3 policy fields before scoring."""
    required_fields = {
        "policy_name",
        "risk_signal",
        "risk_cutoff",
        "margin_signal",
        "margin_cutoff",
        "order_value_denominator",
        "high_risk_high_margin_segment",
        "high_risk_low_margin_segment",
        "low_risk_high_margin_segment",
        "low_risk_low_margin_segment",
        "final_test_used",
    }
    missing_fields = sorted(required_fields.difference(policy))
    if missing_fields:
        raise ValueError(f"AO3 policy missing fields: {missing_fields}")

    if str(policy["final_test_used"]).lower() != "false":
        raise ValueError("AO3 segment policy must not be selected using final test outcomes.")

    if policy["risk_signal"] != "ao1_predicted_late_delivery_probability":
        raise ValueError(f"Unexpected AO3 risk signal: {policy['risk_signal']}")

    if policy["margin_signal"] != "ao3_predicted_margin":
        raise ValueError(f"Unexpected AO3 margin signal: {policy['margin_signal']}")

    if policy["order_value_denominator"] != "ao3_order_value":
        raise ValueError(f"Unexpected AO3 margin denominator: {policy['order_value_denominator']}")


def validate_input_contract(df: DataFrame) -> None:
    """Validate input score table columns and exclusions."""
    missing_columns = sorted(column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns)
    if missing_columns:
        raise ValueError(f"AO1/AO2 score input missing required columns: {missing_columns}")

    forbidden_columns = sorted(column for column in FORBIDDEN_TARGET_COLUMNS if column in df.columns)
    if forbidden_columns:
        raise ValueError(f"AO3 input contains forbidden target/outcome columns: {forbidden_columns}")

    non_test_count = df.filter(
        (col("split_partition") != lit("test")) | (col("ao2_split_partition") != lit("test"))
    ).count()
    if non_test_count:
        raise ValueError(f"AO3 segment input contains non-test rows: {non_test_count}")


def build_segment_dataframe(df: DataFrame, policy: dict[str, str]) -> DataFrame:
    """Apply AO3 policy rules and assign operational segments."""
    risk_cutoff = float(policy["risk_cutoff"])
    margin_cutoff = float(policy["margin_cutoff"])

    risk_score = col("ao1_predicted_late_delivery_probability")
    profit_score = col("ao2_predicted_order_profit")
    order_value = col("ao3_order_value")
    predicted_margin = col("ao3_predicted_margin")

    high_risk = risk_score >= lit(risk_cutoff)
    high_margin = predicted_margin >= lit(margin_cutoff)
    invalid_score = risk_score.isNull() | profit_score.isNull()
    invalid_margin = order_value.isNull() | predicted_margin.isNull() | (order_value <= lit(0))

    return (
        df.withColumn("ao3_policy_name", lit(policy["policy_name"]).cast(StringType()))
        .withColumn("ao3_risk_cutoff", lit(risk_cutoff).cast(DoubleType()))
        .withColumn("ao3_margin_cutoff", lit(margin_cutoff).cast(DoubleType()))
        .withColumn("ao3_high_risk_flag", high_risk.cast(BooleanType()))
        .withColumn("ao3_high_margin_flag", high_margin.cast(BooleanType()))
        .withColumn(
            "ao3_priority_segment",
            when(invalid_score, lit("requires_score_review"))
            .when(invalid_margin, lit("requires_margin_review"))
            .when(high_risk & high_margin, lit(policy["high_risk_high_margin_segment"]))
            .when(high_risk & ~high_margin, lit(policy["high_risk_low_margin_segment"]))
            .when(~high_risk & high_margin, lit(policy["low_risk_high_margin_segment"]))
            .otherwise(lit(policy["low_risk_low_margin_segment"])),
        )
        .withColumn("ao3_segment_assignment_timestamp_utc", current_timestamp())
    )


def validate_segment_output(df: DataFrame) -> None:
    """Validate AO3 segment assignment output before writing."""
    row_count = df.count()
    if row_count == 0:
        raise ValueError("AO3 segment output contains no rows.")

    forbidden_columns = sorted(column for column in FORBIDDEN_TARGET_COLUMNS if column in df.columns)
    if forbidden_columns:
        raise ValueError(f"AO3 output contains forbidden target/outcome columns: {forbidden_columns}")

    required_output_columns = set(REQUIRED_INPUT_COLUMNS).union(
        {
            "ao3_policy_name",
            "ao3_risk_cutoff",
            "ao3_margin_cutoff",
            "ao3_high_risk_flag",
            "ao3_high_margin_flag",
            "ao3_priority_segment",
            "ao3_segment_assignment_timestamp_utc",
        }
    )
    missing_columns = sorted(required_output_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"AO3 segment output missing columns: {missing_columns}")

    invalid_segment_count = df.filter(~col("ao3_priority_segment").isin(*VALID_SEGMENTS)).count()
    if invalid_segment_count:
        raise ValueError(f"AO3 output contains invalid segment labels: {invalid_segment_count}")

    null_segment_count = df.filter(col("ao3_priority_segment").isNull()).count()
    if null_segment_count:
        raise ValueError(f"AO3 output contains null segments: {null_segment_count}")


def write_delta(df: DataFrame, output_path: str, config: AO3RiskMarginSegmentConfig) -> None:
    """Write AO3 segment output as Delta."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(output_path)
    )


def build_summary(df: DataFrame) -> list[dict[str, object]]:
    """Build segment-level summary rows for report and validation."""
    total_rows = df.count()
    summary_df = (
        df.groupBy("ao3_priority_segment")
        .agg(
            spark_sum(lit(1)).alias("row_count"),
            {"ao1_predicted_late_delivery_probability": "avg", "ao2_predicted_order_profit": "avg", "ao3_predicted_margin": "avg"},
        )
    )

    rows = []
    for row in summary_df.collect():
        row_dict = row.asDict()
        rows.append(
            {
                "ao3_priority_segment": row_dict["ao3_priority_segment"],
                "row_count": int(row_dict["row_count"]),
                "share_of_rows": int(row_dict["row_count"]) / total_rows if total_rows else 0.0,
                "avg_ao1_predicted_late_delivery_probability": row_dict[
                    "avg(ao1_predicted_late_delivery_probability)"
                ],
                "avg_ao2_predicted_order_profit": row_dict["avg(ao2_predicted_order_profit)"],
                "avg_ao3_predicted_margin": row_dict["avg(ao3_predicted_margin)"],
            }
        )
    return sorted(rows, key=lambda item: str(item["ao3_priority_segment"]))


def write_summary_csv(summary_rows: list[dict[str, object]], output_path: Path) -> None:
    """Write AO3 segment summary CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=SEGMENT_SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)


def write_metadata(
    *,
    config: AO3RiskMarginSegmentConfig,
    policy: dict[str, str],
    row_count: int,
    summary_rows: list[dict[str, object]],
) -> None:
    """Write lightweight AO3 segment assignment metadata."""
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "issue": "#42",
        "workflow": "ao3_risk_margin_segment_assignment",
        "input_score_path": config.input_score_path,
        "output_segment_path": config.output_segment_path,
        "policy_csv_path": str(config.policy_csv_path),
        "policy_name": policy["policy_name"],
        "risk_cutoff": float(policy["risk_cutoff"]),
        "margin_cutoff": float(policy["margin_cutoff"]),
        "row_count": row_count,
        "segment_counts": {
            row["ao3_priority_segment"]: int(row["row_count"]) for row in summary_rows
        },
        "final_test_targets_used_for_assignment": False,
        "performance_metrics_calculated": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    config.metadata_output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def run_ao3_segment_assignment(config: AO3RiskMarginSegmentConfig, logger: logging.Logger) -> None:
    """Execute AO3 risk-margin segment assignment."""
    config = with_repo_defaults(config)
    spark = get_spark_session()

    logger.info("Starting AO3 risk-margin segment assignment.")
    logger.info("Input score path: %s", config.input_score_path)
    logger.info("Output segment path: %s", config.output_segment_path)
    logger.info("Policy CSV path: %s", config.policy_csv_path)

    policy = read_policy(config.policy_csv_path)
    validate_policy(policy)

    score_df = spark.read.format(config.read_format).load(config.input_score_path)
    validate_input_contract(score_df)

    segment_df = build_segment_dataframe(score_df, policy)
    validate_segment_output(segment_df)

    write_delta(segment_df, config.output_segment_path, config)
    written_df = spark.read.format(config.write_format).load(config.output_segment_path)
    validate_segment_output(written_df)

    summary_rows = build_summary(written_df)
    write_summary_csv(summary_rows, config.summary_output_path)
    write_metadata(
        config=config,
        policy=policy,
        row_count=written_df.count(),
        summary_rows=summary_rows,
    )

    logger.info("AO3 segment assignment completed successfully.")


def main() -> None:
    """Run AO3 segment assignment with default configuration."""
    run_ao3_segment_assignment(AO3RiskMarginSegmentConfig(), configure_logging())


if __name__ == "__main__":
    main()
