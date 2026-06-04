# Databricks notebook source
"""Run the scoped Power BI P04 geographic segment workflow.

This workflow is intentionally narrow and supports Issue #145. It builds the
filter-compatible geographic segment summary, applies serving-layer decision
enrichments, validates the output, optionally exports a CSV fallback, and
optionally registers the Databricks SQL serving table.
"""

# COMMAND ----------

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


# ----------------------------
# P04 geographic workflow flags
# ----------------------------
RUN_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY = True
RUN_POWERBI_GEOGRAPHIC_DECISION_ENRICHMENT = True
RUN_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_VALIDATION = True
RUN_POWERBI_GEOGRAPHIC_SEGMENT_EXPORT = False
RUN_POWERBI_GEOGRAPHIC_SEGMENT_SERVING_REGISTRATION = False


def local_path_exists(path: Path) -> bool:
    """Return whether a local path exists, treating inaccessible probes as absent."""
    try:
        return path.exists()
    except OSError:
        return False


def find_repo_root() -> Path:
    """Find the repo root from Databricks Repos, local execution, or an env var."""
    env_root = os.getenv("DATACO_REPO_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    candidate_roots: list[Path] = []
    try:
        candidate_roots.append(Path(__file__).resolve().parent)
    except NameError:
        pass
    candidate_roots.append(Path.cwd().resolve())

    for starting_point in candidate_roots:
        for candidate in [starting_point, *starting_point.parents]:
            if (
                local_path_exists(candidate / "src" / "dashboard")
                and local_path_exists(candidate / "tests" / "data_validation")
            ):
                return candidate

    raise FileNotFoundError(
        "Could not find repo root. Set DATACO_REPO_ROOT to the repository checkout path."
    )


REPO_ROOT = find_repo_root()
os.environ.setdefault("DATACO_REPO_ROOT", str(REPO_ROOT))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print(f"Repo root: {REPO_ROOT}")

# COMMAND ----------

from src.dashboard.build_powerbi_geographic_segment_summary import (  # noqa: E402
    PowerBIGeographicSegmentSummaryConfig,
    configure_logging as configure_geographic_segment_logging,
    run_powerbi_geographic_segment_summary,
)
from src.dashboard.enrich_powerbi_geographic_segment_summary import (  # noqa: E402
    PowerBIGeographicDecisionEnrichmentConfig,
    configure_logging as configure_geographic_enrichment_logging,
    run_powerbi_geographic_decision_enrichment,
)
from src.dashboard.export_powerbi_geographic_segment_summary import (  # noqa: E402
    PowerBIGeographicSegmentExportConfig,
    configure_logging as configure_geographic_segment_export_logging,
    run_powerbi_geographic_segment_export,
)
from src.dashboard.register_powerbi_geographic_segment_table import (  # noqa: E402
    PowerBIGeographicSegmentServingConfig,
    configure_logging as configure_geographic_segment_serving_logging,
    run_powerbi_geographic_segment_serving_registration,
)


# COMMAND ----------


def run_step(name: str, enabled: bool, action) -> None:
    """Run one workflow step with simple notebook-friendly status messages."""
    if not enabled:
        print(f"SKIPPED: {name}")
        return
    print(f"STARTED: {name}")
    action()
    print(f"COMPLETED: {name}")


def run_validation_script(relative_path: Path) -> None:
    """Execute one repository validation script."""
    script_path = REPO_ROOT / relative_path
    if not local_path_exists(script_path):
        raise FileNotFoundError(f"Expected validation script not found: {script_path}")
    runpy.run_path(str(script_path), run_name="__main__")


# COMMAND ----------


def main() -> None:
    """Execute the scoped P04 geographic segment workflow."""
    run_step(
        "Build Power BI geographic segment summary",
        RUN_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY,
        lambda: run_powerbi_geographic_segment_summary(
            PowerBIGeographicSegmentSummaryConfig(),
            configure_geographic_segment_logging(),
        ),
    )
    run_step(
        "Enrich Power BI geographic segment summary",
        RUN_POWERBI_GEOGRAPHIC_DECISION_ENRICHMENT,
        lambda: run_powerbi_geographic_decision_enrichment(
            PowerBIGeographicDecisionEnrichmentConfig(),
            configure_geographic_enrichment_logging(),
        ),
    )
    run_step(
        "Validate Power BI geographic segment summary",
        RUN_POWERBI_GEOGRAPHIC_SEGMENT_SUMMARY_VALIDATION,
        lambda: run_validation_script(
            Path("tests/data_validation/validate_powerbi_geographic_segment_summary.py")
        ),
    )
    run_step(
        "Export Power BI geographic segment CSV fallback",
        RUN_POWERBI_GEOGRAPHIC_SEGMENT_EXPORT,
        lambda: run_powerbi_geographic_segment_export(
            PowerBIGeographicSegmentExportConfig(),
            configure_geographic_segment_export_logging(),
        ),
    )
    run_step(
        "Register Power BI geographic segment serving table",
        RUN_POWERBI_GEOGRAPHIC_SEGMENT_SERVING_REGISTRATION,
        lambda: run_powerbi_geographic_segment_serving_registration(
            PowerBIGeographicSegmentServingConfig(),
            configure_geographic_segment_serving_logging(),
        ),
    )

    print("P04 geographic segment workflow completed.")
    print("Delta output: /Volumes/workspace/default/raw_data/gold/powerbi_geographic_segment_summary")
    print("Serving table: workspace.default.powerbi_geographic_segment_summary")
    print("CSV fallback: dashboard/exports/powerbi_geographic_segment_summary.csv")


if __name__ == "__main__":
    main()
