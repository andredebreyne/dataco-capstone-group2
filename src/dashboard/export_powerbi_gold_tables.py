"""Export governed Gold outputs for the Power BI dashboard.

This Databricks-compatible script reads the approved Gold Delta outputs used by
AO3 and writes small, dashboard-ready CSV files under ``dashboard/exports``.
It does not recreate model scores, retune thresholds, calculate final-test
performance metrics, or use actual target labels.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

DEFAULT_AO1_AO2_SCORE_PATH = os.getenv(
    "DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao1_ao2_test_scores",
)

DEFAULT_AO3_SEGMENT_PATH = os.getenv(
    "DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments",
)

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

REFERENCE_EXPORT_FILES = (
    "ao1_decision_threshold_policy.csv",
    "ao1_ao2_test_score_summary.csv",
    "ao3_risk_margin_matrix_policy.csv",
    "ao3_segment_summary.csv",
    "ao3_risk_margin_benchmark_segment_summary.csv",
    "ao3_risk_margin_benchmark_insights.csv",
)

REPORT_EXPORT_FILES = (
    "ao1_model_validation_comparison.csv",
    "ao1_threshold_tradeoff_grid.csv",
    "ao1_confusion_matrix_by_threshold.csv",
    "ao2_model_validation_comparison.csv",
    "ao2_model_evaluation_metrics.csv",
)

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}


@dataclass(frozen=True)
class PowerBIExportConfig:
    """Configuration for Power BI dashboard exports."""

    ao1_ao2_score_path: str = DEFAULT_AO1_AO2_SCORE_PATH
    ao3_segment_path: str = DEFAULT_AO3_SEGMENT_PATH
    export_root: Path = Path(
        os.getenv("DATACO_POWERBI_EXPORT_ROOT", str(Path.cwd() / "dashboard/exports"))
    )
    reference_root: Path = Path(
        os.getenv("DATACO_REFERENCE_ROOT", str(Path.cwd() / "data/references"))
    )
    report_table_root: Path = Path(
        os.getenv("DATACO_REPORT_TABLE_ROOT", str(Path.cwd() / "report/tables"))
    )
    read_format: str = "delta"
    export_mode: str = "overwrite"


def configure_logging() -> logging.Logger:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_gold_export")


def get_spark_session() -> SparkSession:
    """Return the active Spark session."""
    return SparkSession.builder.getOrCreate()


def resolve_repo_root() -> Path:
    """Resolve the repository root in local and Databricks notebook contexts."""
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


def with_repo_defaults(config: PowerBIExportConfig) -> PowerBIExportConfig:
    """Use repository-root defaults when environment overrides are absent."""
    repo_root = resolve_repo_root()
    return PowerBIExportConfig(
        ao1_ao2_score_path=config.ao1_ao2_score_path,
        ao3_segment_path=config.ao3_segment_path,
        export_root=Path(
            os.getenv("DATACO_POWERBI_EXPORT_ROOT", str(repo_root / "dashboard/exports"))
        ),
        reference_root=Path(
            os.getenv("DATACO_REFERENCE_ROOT", str(repo_root / "data/references"))
        ),
        report_table_root=Path(
            os.getenv("DATACO_REPORT_TABLE_ROOT", str(repo_root / "report/tables"))
        ),
        read_format=config.read_format,
        export_mode=config.export_mode,
    )


def assert_required_columns(df: DataFrame, required_columns: tuple[str, ...], table_name: str) -> None:
    """Validate required dashboard columns."""
    missing_columns = sorted(column for column in required_columns if column not in df.columns)
    if missing_columns:
        raise ValueError(f"{table_name} is missing required columns: {missing_columns}")


def assert_no_forbidden_targets(df: DataFrame, table_name: str) -> None:
    """Prevent target and outcome labels from entering dashboard exports."""
    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(df.columns))
    if forbidden_columns:
        raise ValueError(f"{table_name} contains forbidden target/outcome columns: {forbidden_columns}")


def select_dashboard_columns(df: DataFrame, columns: tuple[str, ...], table_name: str) -> DataFrame:
    """Return a dashboard-safe column projection."""
    assert_required_columns(df, columns, table_name)
    assert_no_forbidden_targets(df, table_name)
    return df.select(*(col(column) for column in columns))


def clear_output_path(path: Path) -> None:
    """Clear an existing generated file or temporary folder."""
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def write_single_csv(df: DataFrame, output_path: Path) -> int:
    """Write a DataFrame to a deterministic single CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    clear_output_path(output_path)
    clear_output_path(temporary_path)

    row_count = df.count()
    (
        df.coalesce(1)
        .write.mode("overwrite")
        .option("header", "true")
        .option("encoding", "UTF-8")
        .csv(str(temporary_path))
    )

    part_files = sorted(temporary_path.glob("part-*.csv"))
    if len(part_files) != 1:
        raise RuntimeError(f"Expected one CSV part file in {temporary_path}; found {len(part_files)}.")

    shutil.move(str(part_files[0]), str(output_path))
    shutil.rmtree(temporary_path)
    return row_count


def copy_reference_file(source_path: Path, output_path: Path) -> int:
    """Copy a governed small reference CSV into the Power BI export folder."""
    if not source_path.exists():
        raise FileNotFoundError(f"Missing reference artifact for Power BI export: {source_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output_path)
    with output_path.open("r", encoding="utf-8") as exported_file:
        return max(sum(1 for _ in exported_file) - 1, 0)


def write_manifest(manifest_rows: list[dict[str, object]], output_path: Path) -> None:
    """Write a manifest describing generated Power BI exports."""
    output_path.write_text(
        json.dumps(
            {
                "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "export_purpose": "Power BI dashboard import layer",
                "final_test_targets_used": False,
                "exports": manifest_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def run_powerbi_gold_export(config: PowerBIExportConfig, logger: logging.Logger) -> None:
    """Export dashboard-ready Gold and reference artifacts for Power BI."""
    config = with_repo_defaults(config)
    spark = get_spark_session()
    manifest_rows: list[dict[str, object]] = []

    logger.info("Starting Power BI Gold export.")
    logger.info("AO1/AO2 score input path: %s", config.ao1_ao2_score_path)
    logger.info("AO3 segment input path: %s", config.ao3_segment_path)
    logger.info("Power BI export root: %s", config.export_root)

    score_df = spark.read.format(config.read_format).load(config.ao1_ao2_score_path)
    score_export_df = select_dashboard_columns(
        score_df,
        AO1_AO2_SCORE_COLUMNS,
        "AO1/AO2 score table",
    )
    score_rows = write_single_csv(
        score_export_df,
        config.export_root / "ao1_ao2_test_scores.csv",
    )
    manifest_rows.append(
        {
            "name": "ao1_ao2_test_scores",
            "source": config.ao1_ao2_score_path,
            "output": str(config.export_root / "ao1_ao2_test_scores.csv"),
            "row_count": score_rows,
            "type": "gold_delta_export",
        }
    )
    logger.info("Exported AO1/AO2 score table with %d rows.", score_rows)

    segment_df = spark.read.format(config.read_format).load(config.ao3_segment_path)
    segment_export_df = select_dashboard_columns(
        segment_df,
        AO3_SEGMENT_COLUMNS,
        "AO3 segment table",
    )
    segment_rows = write_single_csv(
        segment_export_df,
        config.export_root / "ao3_risk_margin_segments.csv",
    )
    manifest_rows.append(
        {
            "name": "ao3_risk_margin_segments",
            "source": config.ao3_segment_path,
            "output": str(config.export_root / "ao3_risk_margin_segments.csv"),
            "row_count": segment_rows,
            "type": "gold_delta_export",
        }
    )
    logger.info("Exported AO3 segment table with %d rows.", segment_rows)

    for file_name in REFERENCE_EXPORT_FILES:
        source_path = config.reference_root / file_name
        output_path = config.export_root / file_name
        row_count = copy_reference_file(source_path, output_path)
        manifest_rows.append(
            {
                "name": source_path.stem,
                "source": str(source_path),
                "output": str(output_path),
                "row_count": row_count,
                "type": "reference_csv_copy",
            }
        )
        logger.info("Copied reference export %s with %d rows.", file_name, row_count)

    for file_name in REPORT_EXPORT_FILES:
        source_path = config.report_table_root / file_name
        output_path = config.export_root / file_name
        row_count = copy_reference_file(source_path, output_path)
        manifest_rows.append(
            {
                "name": source_path.stem,
                "source": str(source_path),
                "output": str(output_path),
                "row_count": row_count,
                "type": "report_csv_copy",
            }
        )
        logger.info("Copied report export %s with %d rows.", file_name, row_count)

    write_manifest(manifest_rows, config.export_root / "powerbi_export_manifest.json")
    logger.info("Power BI Gold export completed successfully.")


def main() -> None:
    """Run the Power BI Gold export job."""
    run_powerbi_gold_export(PowerBIExportConfig(), configure_logging())


if __name__ == "__main__":
    main()
