"""Validate the static Power BI Databricks serving-layer contract.

This validator intentionally avoids live Databricks access. It checks that the
serving-layer registration script, orchestrator wiring, and documentation expose
the expected governed tables without hard-coded personal workspace paths.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path


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


REPO_ROOT = resolve_repo_root()
SCRIPT_PATH = REPO_ROOT / "src/dashboard/register_powerbi_databricks_tables.py"
ORCHESTRATOR_PATH = REPO_ROOT / "notebooks/pipeline/run_project_workflow.py"

EXPECTED_TABLE_NAMES = {
    "powerbi_ao3_order_segments",
    "powerbi_ao1_ao2_test_scores",
    "powerbi_geographic_summary",
    "powerbi_ao1_decision_threshold_policy",
    "powerbi_ao1_ao2_test_score_summary",
    "powerbi_ao3_risk_margin_policy",
    "powerbi_ao3_segment_summary",
    "powerbi_ao3_benchmark_segment_summary",
    "powerbi_ao3_benchmark_insights",
    "powerbi_ao3_operational_recommendations",
    "powerbi_ao1_model_validation",
    "powerbi_ao1_threshold_tradeoff",
    "powerbi_ao1_confusion_by_threshold",
    "powerbi_ao2_model_validation",
    "powerbi_ao2_evaluation_metrics",
    "powerbi_serving_layer_manifest",
}

EXPECTED_MANIFEST_FIELDS = {
    "generated_timestamp_utc",
    "workflow_name",
    "serving_catalog",
    "serving_schema",
    "target_table",
    "table_name",
    "source_type",
    "source_path",
    "artifact_category",
    "row_count",
    "column_count",
    "run_status",
    "description",
}

REQUIRED_ENVIRONMENT_OVERRIDES = {
    "DATACO_REPO_ROOT",
    "DATACO_POWERBI_SERVING_CATALOG",
    "DATACO_POWERBI_SERVING_SCHEMA",
    "DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH",
    "DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH",
    "DATACO_POWERBI_GEOGRAPHIC_SUMMARY_OUTPUT_PATH",
}

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}

REQUIRED_DOC_REFERENCES = {
    "README.md": "register_powerbi_databricks_tables.py",
    "docs/powerbi_databricks_serving_layer.md": "RUN_POWERBI_DATABRICKS_SERVING_LAYER",
    "dashboard/README.md": "register_powerbi_databricks_tables.py",
    "dashboard/powerbi_semantic_model.md": "RUN_POWERBI_DATABRICKS_SERVING_LAYER",
    "docs/project_orchestrator.md": "RUN_POWERBI_DATABRICKS_SERVING_LAYER",
}

ACTIVE_CODE_PATHS = (
    Path("src/dashboard/build_powerbi_geographic_summary.py"),
    Path("src/dashboard/register_powerbi_databricks_tables.py"),
    Path("notebooks/pipeline/run_project_workflow.py"),
    Path("tests/data_validation/validate_powerbi_geographic_summary.py"),
    Path("tests/data_validation/validate_powerbi_databricks_serving_layer.py"),
)


def parse_script_ast() -> ast.Module:
    """Parse the serving-layer script without importing PySpark."""
    assert SCRIPT_PATH.exists(), f"Missing serving-layer script: {SCRIPT_PATH}"
    return ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))


def literal_sequence_constant(tree: ast.Module, name: str) -> tuple[str, ...]:
    """Return a top-level tuple/list/set string constant from the parsed script."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = [
                target.id for target in node.targets if isinstance(target, ast.Name)
            ]
            if name in target_names:
                value = ast.literal_eval(node.value)
                return tuple(value)
    raise AssertionError(f"Missing top-level constant: {name}")


def collect_string_literals(tree: ast.AST) -> set[str]:
    """Collect all string literals from an AST."""
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def assert_expected_table_contract(script_text: str, tree: ast.Module) -> None:
    """Validate expected serving table names and configuration entries."""
    script_literals = collect_string_literals(tree)
    missing_tables = sorted(EXPECTED_TABLE_NAMES.difference(script_literals))
    assert not missing_tables, f"Serving-layer script missing table names: {missing_tables}"

    missing_env_vars = sorted(
        env_var for env_var in REQUIRED_ENVIRONMENT_OVERRIDES if env_var not in script_text
    )
    assert not missing_env_vars, f"Serving-layer script missing env overrides: {missing_env_vars}"


def assert_allowlists_are_safe(tree: ast.Module) -> None:
    """Validate dashboard-safe Delta projections do not include forbidden fields."""
    for constant_name in ("AO1_AO2_SCORE_COLUMNS", "AO3_SEGMENT_COLUMNS"):
        columns = set(literal_sequence_constant(tree, constant_name))
        forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(columns))
        assert not forbidden_columns, (
            f"{constant_name} includes forbidden target/outcome columns: {forbidden_columns}"
        )


def assert_manifest_fields(script_text: str) -> None:
    """Validate the manifest metadata fields are defined in the script."""
    missing_fields = sorted(field for field in EXPECTED_MANIFEST_FIELDS if field not in script_text)
    assert not missing_fields, f"Serving-layer manifest missing fields: {missing_fields}"


def assert_orchestrator_wiring(orchestrator_text: str) -> None:
    """Validate the optional serving-layer orchestrator step is wired but disabled."""
    assert "RUN_POWERBI_DATABRICKS_SERVING_LAYER = False" in orchestrator_text
    assert "run_powerbi_databricks_serving_layer_registration" in orchestrator_text
    assert "register_powerbi_databricks_tables.py" in orchestrator_text


def assert_docs_reference_serving_layer() -> None:
    """Validate project docs describe the Databricks serving-layer workflow."""
    for relative_path, required_text in REQUIRED_DOC_REFERENCES.items():
        doc_path = REPO_ROOT / relative_path
        assert doc_path.exists(), f"Missing documentation file: {relative_path}"
        doc_text = doc_path.read_text(encoding="utf-8")
        assert required_text in doc_text, f"{relative_path} missing {required_text!r}"
        assert (
            "Azure Databricks" in doc_text
            or "Databricks serving" in doc_text
            or "Databricks SQL serving" in doc_text
        ), (
            f"{relative_path} does not describe the Databricks serving workflow"
        )


def assert_no_personal_paths_in_active_code() -> None:
    """Ensure active code does not hard-code personal Databricks workspace paths."""
    forbidden_tokens = ("andredebreyne" + "@gmail.com", "/Workspace/Users/" + "bruno.")
    offenders: list[str] = []
    for relative_path in ACTIVE_CODE_PATHS:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                offenders.append(f"{relative_path}: {token}")
    assert not offenders, f"Personal Databricks paths found in active code: {offenders}"


def main() -> None:
    """Run static serving-layer validation."""
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = parse_script_ast()
    orchestrator_text = ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert_expected_table_contract(script_text, tree)
    assert_allowlists_are_safe(tree)
    assert_manifest_fields(script_text)
    assert_orchestrator_wiring(orchestrator_text)
    assert_docs_reference_serving_layer()
    assert_no_personal_paths_in_active_code()

    print("Power BI Databricks serving-layer static validation passed.")


if __name__ == "__main__":
    main()
