# Databricks notebook source
"""Run the Issue #152 logistics order KPI audit workflow.

This task-level orchestrator builds the order-item-level logistics audit table,
validates it, exports the CSV fallback for Power BI, and optionally registers the
Databricks SQL serving table.
"""

from __future__ import annotations

import logging
import os
import runpy
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


# COMMAND ----------

RUN_LOGISTICS_ORDER_KPI_DETAIL_BUILD = True
RUN_LOGISTICS_ORDER_KPI_DETAIL_VALIDATION = True
RUN_LOGISTICS_ORDER_KPI_DETAIL_CSV_EXPORT = True
RUN_LOGISTICS_ORDER_KPI_DETAIL_DATABRICKS_REGISTRATION = False
RUN_FINAL_CHECKLIST = True


@dataclass
class StepResult:
    name: str
    status: str
    required: bool
    detail: str = ""


STEP_RESULTS: list[StepResult] = []


def local_path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def find_repo_root() -> Path:
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

from src.dashboard.build_powerbi_logistics_order_kpi_detail import (  # noqa: E402
    PowerBILogisticsOrderKPIDetailConfig,
    configure_logging as configure_detail_build_logging,
    run_powerbi_logistics_order_kpi_detail,
)
from src.dashboard.export_powerbi_logistics_order_kpi_detail import (  # noqa: E402
    LogisticsOrderKPIExportConfig,
    configure_logging as configure_detail_export_logging,
    run_logistics_order_kpi_export,
)
from src.dashboard.register_powerbi_logistics_order_kpi_detail_table import (  # noqa: E402
    LogisticsOrderKPIRegistrationConfig,
    configure_logging as configure_detail_registration_logging,
    run_registration as run_logistics_order_kpi_registration,
)


def workflow_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.logistics_order_kpi_workflow")


LOGGER = workflow_logger()


def run_python_file(relative_path: Path) -> None:
    script_path = REPO_ROOT / relative_path
    if not local_path_exists(script_path):
        raise FileNotFoundError(f"Expected executable script not found: {script_path}")
    runpy.run_path(str(script_path), run_name="__main__")


def run_step(
    step_name: str,
    enabled: bool,
    action: Callable[[], None],
    *,
    required: bool = True,
) -> None:
    if not enabled:
        print(f"[SKIP] {step_name}")
        STEP_RESULTS.append(StepResult(step_name, "skipped", required))
        return

    print(f"\n[START] {step_name}")
    try:
        action()
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        STEP_RESULTS.append(StepResult(step_name, "failed", required, detail))
        print(f"[FAIL] {step_name}: {detail}")
        traceback.print_exc()
        if required:
            raise RuntimeError(f"Logistics order KPI workflow failed during step: {step_name}") from exc
        LOGGER.warning("Optional workflow step failed: %s", step_name, exc_info=True)
        return

    STEP_RESULTS.append(StepResult(step_name, "completed", required))
    print(f"[DONE] {step_name}")


def build_logistics_order_kpi_detail() -> None:
    run_powerbi_logistics_order_kpi_detail(
        PowerBILogisticsOrderKPIDetailConfig(),
        configure_detail_build_logging(),
    )


def validate_logistics_order_kpi_detail() -> None:
    run_python_file(Path("tests/data_validation/validate_powerbi_logistics_order_kpi_detail.py"))


def export_logistics_order_kpi_detail_csv() -> None:
    run_logistics_order_kpi_export(
        LogisticsOrderKPIExportConfig(),
        configure_detail_export_logging(),
    )


def register_logistics_order_kpi_detail_table() -> None:
    run_logistics_order_kpi_registration(
        LogisticsOrderKPIRegistrationConfig(),
        configure_detail_registration_logging(),
    )


def print_final_checklist() -> None:
    print("\nLogistics order KPI audit workflow checklist:")
    for result in STEP_RESULTS:
        required_label = "required" if result.required else "optional"
        detail = f" - {result.detail}" if result.detail else ""
        print(f"- {result.status.upper()}: {result.name} ({required_label}){detail}")

    build_config = PowerBILogisticsOrderKPIDetailConfig()
    export_config = LogisticsOrderKPIExportConfig()
    registration_config = LogisticsOrderKPIRegistrationConfig()

    print("\nExpected outputs:")
    print(f"- Delta audit table path: {build_config.output_path}")
    print(f"- Metadata JSON: {build_config.metadata_output_path}")
    print(f"- CSV export: {export_config.export_root / export_config.export_file_name}")
    print(f"- CSV export manifest: {export_config.export_root / export_config.manifest_file_name}")
    print(
        "- Databricks SQL table: "
        f"{registration_config.catalog}.{registration_config.schema}."
        f"{registration_config.table_name}"
    )

    print("\nGovernance notes:")
    print("- AO1 high risk means high predicted probability of late delivery.")
    print("- Actual delivery outcomes are exposed only for audit and KPI validation.")
    print("- This workflow does not retrain AO1, AO2, or AO3.")
    print("- Databricks SQL registration runs only when the registration switch is enabled.")


def main() -> None:
    run_step(
        "Power BI logistics order KPI detail build",
        RUN_LOGISTICS_ORDER_KPI_DETAIL_BUILD,
        build_logistics_order_kpi_detail,
        required=RUN_LOGISTICS_ORDER_KPI_DETAIL_BUILD,
    )
    run_step(
        "Power BI logistics order KPI detail validation",
        RUN_LOGISTICS_ORDER_KPI_DETAIL_BUILD and RUN_LOGISTICS_ORDER_KPI_DETAIL_VALIDATION,
        validate_logistics_order_kpi_detail,
        required=RUN_LOGISTICS_ORDER_KPI_DETAIL_BUILD and RUN_LOGISTICS_ORDER_KPI_DETAIL_VALIDATION,
    )
    run_step(
        "Power BI logistics order KPI detail CSV export",
        RUN_LOGISTICS_ORDER_KPI_DETAIL_CSV_EXPORT,
        export_logistics_order_kpi_detail_csv,
        required=RUN_LOGISTICS_ORDER_KPI_DETAIL_CSV_EXPORT,
    )
    run_step(
        "Power BI logistics order KPI detail Databricks registration",
        RUN_LOGISTICS_ORDER_KPI_DETAIL_DATABRICKS_REGISTRATION,
        register_logistics_order_kpi_detail_table,
        required=RUN_LOGISTICS_ORDER_KPI_DETAIL_DATABRICKS_REGISTRATION,
    )
    run_step("Final execution checklist", RUN_FINAL_CHECKLIST, print_final_checklist, required=False)


if __name__ == "__main__":
    main()
