"""Validate the Silver schema data dictionary reference artifact.

This lightweight script is intended to run from the repository root. It checks
the CSV contract for the reviewer-facing Silver schema dictionary without
requiring Spark, Delta Lake, Gold-table construction, or model training.
"""

from __future__ import annotations

import ast
import csv
import os
from pathlib import Path


def resolve_repo_root() -> Path:
    """Resolve the repository root without relying on __file__ in notebooks."""
    candidates = [Path.cwd()]
    configured_root = os.getenv("DATACO_REPO_ROOT")

    if configured_root:
        candidates.insert(0, Path(configured_root))

    if "__file__" in globals():
        candidates.append(Path(__file__).resolve().parents[2])

    if "dbutils" in globals():
        try:
            notebook_path = (
                dbutils.notebook.entry_point.getDbutils()
                .notebook()
                .getContext()
                .notebookPath()
                .get()
            )
            workspace_path = Path("/Workspace") / notebook_path.strip("/")
            candidates.extend([workspace_path, *workspace_path.parents])
        except Exception:
            pass

    for candidate in candidates:
        if (
            (candidate / "data" / "references" / "silver_schema_data_dictionary.csv").exists()
            and (candidate / "src" / "data_engineering" / "clean_silver.py").exists()
        ):
            return candidate

    raise RuntimeError(
        "Run this validation from the repository root, or set DATACO_REPO_ROOT "
        "to the repository path."
    )


REPO_ROOT = resolve_repo_root()
DICTIONARY_PATH = REPO_ROOT / "data" / "references" / "silver_schema_data_dictionary.csv"
CLEAN_SILVER_PATH = REPO_ROOT / "src" / "data_engineering" / "clean_silver.py"
SCREENING_PATH = REPO_ROOT / "data" / "references" / "leakage_conceptual_screening.csv"

REQUIRED_COLUMNS = (
    "silver_column_name",
    "silver_data_type",
    "source_column_name",
    "source_layer",
    "derivation_or_cleaning_note",
    "business_meaning",
    "missing_value_rule",
    "quality_caveat",
    "decision_time_availability",
    "ao1_usage",
    "ao2_usage",
    "dashboard_usage",
    "target_relevance",
    "leakage_restriction",
    "approved_use_note",
    "review_status",
    "related_document",
)

ALLOWED_SOURCE_LAYER_VALUES = {
    "bronze",
    "silver_lineage",
    "derived_silver",
}
ALLOWED_AO_USAGE_VALUES = {
    "allowed",
    "forbidden",
    "target",
    "conditional",
    "not_applicable",
}
ALLOWED_DASHBOARD_USAGE_VALUES = {
    "allowed",
    "dashboard_only",
    "restricted",
    "not_applicable",
}
ALLOWED_TARGET_RELEVANCE_VALUES = {
    "ao1_target",
    "ao2_target",
    "profit_proxy",
    "outcome_proxy",
    "not_target",
}
ALLOWED_REVIEW_STATUS_VALUES = {
    "approved",
    "needs_review",
    "deferred_to_gold",
}

SILVER_SCHEMA_CONSTANTS = (
    "INTEGER_COLUMNS",
    "DECIMAL_COLUMNS",
    "TIMESTAMP_COLUMNS",
    "CATEGORICAL_COLUMNS",
    "BRONZE_LINEAGE_COLUMNS",
    "SILVER_LINEAGE_COLUMNS",
)
LINEAGE_COLUMNS = {
    "_ingest_timestamp",
    "_source_file",
    "_silver_processed_timestamp",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of dictionaries."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_required_columns(rows: list[dict[str, str]]) -> None:
    """Validate the dictionary table has the required columns."""
    if not rows:
        raise AssertionError(f"Silver schema dictionary is empty: {DICTIONARY_PATH}")

    actual_columns = tuple(rows[0].keys())
    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(actual_columns))
    if missing_columns:
        raise AssertionError(f"Missing required columns: {missing_columns}")


def assert_no_blank_silver_column_names(rows: list[dict[str, str]]) -> None:
    """Validate every row has a Silver column name."""
    blank_rows = [
        row_number
        for row_number, row in enumerate(rows, start=2)
        if not row["silver_column_name"].strip()
    ]
    if blank_rows:
        raise AssertionError(f"Blank silver_column_name values on rows: {blank_rows}")


def assert_no_duplicate_silver_column_names(rows: list[dict[str, str]]) -> None:
    """Validate each Silver column appears once."""
    seen: set[str] = set()
    duplicates: set[str] = set()

    for row in rows:
        column_name = row["silver_column_name"]
        if column_name in seen:
            duplicates.add(column_name)
        seen.add(column_name)

    if duplicates:
        raise AssertionError(f"Duplicate silver_column_name values: {sorted(duplicates)}")


def assert_controlled_values(rows: list[dict[str, str]]) -> None:
    """Validate controlled vocabulary columns."""
    validators = {
        "source_layer": ALLOWED_SOURCE_LAYER_VALUES,
        "ao1_usage": ALLOWED_AO_USAGE_VALUES,
        "ao2_usage": ALLOWED_AO_USAGE_VALUES,
        "dashboard_usage": ALLOWED_DASHBOARD_USAGE_VALUES,
        "target_relevance": ALLOWED_TARGET_RELEVANCE_VALUES,
        "review_status": ALLOWED_REVIEW_STATUS_VALUES,
    }
    invalid_values: list[tuple[str, str, str]] = []

    for row in rows:
        for column_name, allowed_values in validators.items():
            value = row[column_name]
            if value not in allowed_values:
                invalid_values.append((row["silver_column_name"], column_name, value))

    if invalid_values:
        raise AssertionError(f"Invalid controlled values found: {invalid_values}")


def extract_clean_silver_constants() -> dict[str, tuple[str, ...]]:
    """Extract Silver column constants from clean_silver.py without importing Spark."""
    module = ast.parse(CLEAN_SILVER_PATH.read_text(encoding="utf-8"))
    constants: dict[str, tuple[str, ...]] = {}

    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in SILVER_SCHEMA_CONSTANTS:
                constants[target.id] = ast.literal_eval(node.value)

    missing_constants = sorted(set(SILVER_SCHEMA_CONSTANTS).difference(constants))
    if missing_constants:
        raise AssertionError(f"Missing clean_silver schema constants: {missing_constants}")

    return constants


def expected_silver_columns() -> set[str]:
    """Return the Silver output columns defined by clean_silver.py."""
    constants = extract_clean_silver_constants()
    columns: set[str] = set()

    for constant_name in SILVER_SCHEMA_CONSTANTS:
        columns.update(constants[constant_name])

    return columns


def expected_silver_types() -> dict[str, str]:
    """Return expected Silver data types from the clean_silver.py schema constants."""
    constants = extract_clean_silver_constants()
    expected_types: dict[str, str] = {}

    for column_name in constants["INTEGER_COLUMNS"]:
        expected_types[column_name] = "int"
    for column_name in constants["DECIMAL_COLUMNS"]:
        expected_types[column_name] = "double"
    for column_name in constants["TIMESTAMP_COLUMNS"]:
        expected_types[column_name] = "timestamp"
    for column_name in constants["CATEGORICAL_COLUMNS"]:
        expected_types[column_name] = "string"

    expected_types["_ingest_timestamp"] = "timestamp"
    expected_types["_source_file"] = "string"
    expected_types["_silver_processed_timestamp"] = "timestamp"

    return expected_types


def assert_clean_silver_column_coverage(rows: list[dict[str, str]]) -> None:
    """Validate dictionary coverage matches the clean_silver.py output contract."""
    expected_columns = expected_silver_columns()
    documented_columns = {row["silver_column_name"] for row in rows}

    missing_columns = sorted(expected_columns.difference(documented_columns))
    unexpected_columns = sorted(documented_columns.difference(expected_columns))

    if missing_columns:
        raise AssertionError(f"Silver columns missing from dictionary: {missing_columns}")
    if unexpected_columns:
        raise AssertionError(f"Unexpected columns in Silver dictionary: {unexpected_columns}")


def assert_clean_silver_type_alignment(rows: list[dict[str, str]]) -> None:
    """Validate documented data types match the clean_silver.py schema contract."""
    expected_types = expected_silver_types()
    type_mismatches = sorted(
        (
            row["silver_column_name"],
            expected_types[row["silver_column_name"]],
            row["silver_data_type"],
        )
        for row in rows
        if row["silver_data_type"] != expected_types[row["silver_column_name"]]
    )

    if type_mismatches:
        raise AssertionError(
            "Silver dictionary data types do not match clean_silver.py: "
            f"{type_mismatches}"
        )


def assert_non_lineage_fields_have_policy_notes(rows: list[dict[str, str]]) -> None:
    """Validate non-lineage rows carry usage, leakage, or review guidance."""
    incomplete_rows = [
        row["silver_column_name"]
        for row in rows
        if row["silver_column_name"] not in LINEAGE_COLUMNS
        and not (
            row["approved_use_note"].strip()
            or row["leakage_restriction"].strip()
            or row["review_status"].strip()
        )
    ]

    if incomplete_rows:
        raise AssertionError(
            "Non-lineage Silver fields missing policy guidance: "
            f"{sorted(incomplete_rows)}"
        )


def assert_bronze_fields_align_to_screening(rows: list[dict[str, str]]) -> None:
    """Ensure non-lineage Bronze fields are represented in the leakage screening table."""
    screening_source_columns = {
        row["variable_name"]
        for row in read_csv(SCREENING_PATH)
        if row["variable_origin"] == "raw_dataco"
    }
    missing_from_screening = [
        row["silver_column_name"]
        for row in rows
        if row["source_layer"] == "bronze"
        and row["source_column_name"] not in screening_source_columns
        and row["review_status"] != "needs_review"
    ]

    if missing_from_screening:
        raise AssertionError(
            "Bronze Silver fields missing from leakage screening without needs_review: "
            f"{sorted(missing_from_screening)}"
        )


def run_validation() -> None:
    """Run all Silver schema dictionary validations."""
    rows = read_csv(DICTIONARY_PATH)

    assert_required_columns(rows)
    assert_no_blank_silver_column_names(rows)
    assert_no_duplicate_silver_column_names(rows)
    assert_controlled_values(rows)
    assert_clean_silver_column_coverage(rows)
    assert_clean_silver_type_alignment(rows)
    assert_non_lineage_fields_have_policy_notes(rows)
    assert_bronze_fields_align_to_screening(rows)

    print("Silver schema dictionary validation passed.")


if __name__ == "__main__":
    run_validation()
