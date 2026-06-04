"""Export the enriched Power BI geographic segment summary to CSV.

This scoped export supports Issue #145 by writing a deterministic CSV fallback
for Power BI local testing without requiring the full dashboard export workflow.
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


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
DEFAULT_GEOGRAPHIC_SEGMENT_SUMMARY_PATH = os.getenv(
    "DATACO_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/powerbi_geographic_segment_summary",
)

WORKFLOW_NAME = "powerbi_geographic_segment_summary_export"

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}


@dataclass(frozen=True)
class PowerBIGeographicSegmentExportConfig:
    """Configuration for the scoped P04 geographic segment CSV export."""

    geographic_segment_summary_path: str = DEFAULT_GEOGRAPHIC_SEGMENT_SUMMARY_PATH
    export_root: Path = Path(
        os.getenv("DATACO_POWERBI_EXPORT_ROOT", str(Path.cwd() / "dashboard/exports"))
    )
    read_format: str = "delta"


def configure_logging() -> logging.Logger:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.powerbi_geographic_segment_export")


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
    config: PowerBIGeographicSegmentExportConfig,
) -> PowerBIGeographicSegmentExportConfig:
    """Use repository-root export defaults when environment overrides are absent."""
    repo_root = resolve_repo_root()
    return PowerBIGeographicSegmentExportConfig(
        geographic_segment_summary_path=config.geographic_segment_summary_path,
        export_root=Path(
            os.getenv("DATACO_POWERBI_EXPORT_ROOT", str(repo_root / "dashboard/exports"))
        ),
        read_format=config.read_format,
    )


def assert_no_forbidden_targets(df: DataFrame, table_name: str) -> None:
    """Prevent target and outcome labels from entering dashboard exports."""
    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(df.columns))
    if forbidden_columns:
        raise ValueError(f"{table_name} contains forbidden target/outcome columns: {forbidden_columns}")


def clear_output_path(path: Path) -> None:
    """Clear an existing generated file or temporary folder."""
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def write_single_csv(df: DataFrame, output_path: Path) -> int:
    """Write a compact Spark DataFrame to a deterministic single CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clear_output_path(output_path)
    output_pdf = df.toPandas()
    output_pdf.to_csv(output_path, index=False, encoding="utf-8")
    return int(len(output_pdf))


def run_powerbi_geographic_segment_export(
    config: PowerBIGeographicSegmentExportConfig,
    logger: logging.Logger,
) -> None:
    """Export the enriched geographic segment summary for Power BI."""
    config = with_repo_defaults(config)
    spark = get_spark_session()

    logger.info("Starting Power BI geographic segment CSV export.")
    logger.info("Input Delta path: %s", config.geographic_segment_summary_path)
    logger.info("Export root: %s", config.export_root)

    geographic_df = spark.read.format(config.read_format).load(config.geographic_segment_summary_path)
    assert_no_forbidden_targets(geographic_df, "Power BI geographic segment summary")

    row_count = write_single_csv(
        geographic_df,
        config.export_root / "powerbi_geographic_segment_summary.csv",
    )

    manifest = {
        "workflow_name": WORKFLOW_NAME,
        "issue": "#145",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": config.geographic_segment_summary_path,
        "output": str(config.export_root / "powerbi_geographic_segment_summary.csv"),
        "row_count": row_count,
        "target_or_outcome_columns_used": False,
    }
    manifest_path = config.export_root / "powerbi_geographic_segment_summary_export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    logger.info("Exported Power BI geographic segment summary with %d rows.", row_count)
    logger.info("Wrote export manifest: %s", manifest_path)


def main() -> None:
    """Run the scoped P04 geographic segment export."""
    run_powerbi_geographic_segment_export(
        PowerBIGeographicSegmentExportConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
