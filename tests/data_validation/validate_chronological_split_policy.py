"""Validate the master chronological split policy reference artifact.

This lightweight script checks the CSV and documentation contract for the
project-wide chronological split policy without requiring Spark, Delta Lake,
Gold-table construction, or model training.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path


def resolve_repo_root() -> Path:
    """Resolve repository root for scripts and notebooks."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).resolve()

    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]

    current_path = Path.cwd().resolve()
    for candidate in (current_path, *current_path.parents):
        if (
            candidate / "data" / "references" / "chronological_split_policy.csv"
        ).exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()
POLICY_PATH = REPO_ROOT / "data" / "references" / "chronological_split_policy.csv"
POLICY_DOC_PATH = REPO_ROOT / "docs" / "chronological_split_policy.md"

REQUIRED_COLUMNS = (
    "policy_key",
    "policy_value",
    "policy_scope",
    "rationale",
    "validation_rule",
    "related_document",
)

REQUIRED_POLICY_VALUES = {
    "split_anchor_column": "order_date_DateOrders",
    "primary_ordering_columns": "order_date_DateOrders; Order_Id; Order_Item_Id",
    "development_ratio": "0.80",
    "test_ratio": "0.20",
    "development_partition_label": "development",
    "test_partition_label": "test",
    "shuffle_allowed": "false",
    "test_set_refit_allowed": "false",
    "ao1_split_population": "ao1_gold_primary_population",
    "ao2_split_population": "ao2_gold_full_population",
}

ALLOWED_SCOPES = {
    "AO1",
    "AO2",
    "AO3",
    "AO1; AO2",
    "AO1; AO2; AO3",
}

REQUIRED_DOC_PHRASES = (
    "order_date_DateOrders",
    "order_date_DateOrders ASC",
    "Order_Id ASC",
    "Order_Item_Id ASC",
    "Earliest 80% of rows",
    "Most recent 20% of rows",
    "development",
    "test",
    "Fit only on development/training data",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of dictionaries."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_required_columns(rows: list[dict[str, str]]) -> None:
    """Validate that the policy table has the required columns."""
    if not rows:
        raise AssertionError(f"Chronological split policy is empty: {POLICY_PATH}")

    actual_columns = tuple(rows[0].keys())
    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(actual_columns))
    if missing_columns:
        raise AssertionError(f"Missing required columns: {missing_columns}")


def assert_no_blank_required_cells(rows: list[dict[str, str]]) -> None:
    """Validate required cells are populated."""
    blank_cells = []
    for row_number, row in enumerate(rows, start=2):
        for column_name in REQUIRED_COLUMNS:
            if not row[column_name].strip():
                blank_cells.append((row_number, column_name))

    if blank_cells:
        raise AssertionError(f"Blank required policy cells: {blank_cells}")


def assert_unique_policy_keys(rows: list[dict[str, str]]) -> None:
    """Validate that policy keys are unique."""
    seen: set[str] = set()
    duplicates: set[str] = set()

    for row in rows:
        policy_key = row["policy_key"]
        if policy_key in seen:
            duplicates.add(policy_key)
        seen.add(policy_key)

    if duplicates:
        raise AssertionError(f"Duplicate policy_key values: {sorted(duplicates)}")


def assert_required_policy_values(rows: list[dict[str, str]]) -> None:
    """Validate that required frozen policy values are present and exact."""
    rows_by_key = {row["policy_key"]: row for row in rows}

    missing_keys = sorted(set(REQUIRED_POLICY_VALUES).difference(rows_by_key))
    if missing_keys:
        raise AssertionError(f"Missing required policy keys: {missing_keys}")

    invalid_values = []
    for policy_key, expected_value in REQUIRED_POLICY_VALUES.items():
        actual_value = rows_by_key[policy_key]["policy_value"]
        if actual_value != expected_value:
            invalid_values.append((policy_key, expected_value, actual_value))

    if invalid_values:
        raise AssertionError(f"Invalid chronological split policy values: {invalid_values}")


def assert_ratio_sum(rows: list[dict[str, str]]) -> None:
    """Validate development and test ratios sum to one."""
    rows_by_key = {row["policy_key"]: row for row in rows}
    development_ratio = float(rows_by_key["development_ratio"]["policy_value"])
    test_ratio = float(rows_by_key["test_ratio"]["policy_value"])

    if round(development_ratio + test_ratio, 10) != 1.0:
        raise AssertionError(
            "Chronological split ratios must sum to 1.0. "
            f"Found development={development_ratio}, test={test_ratio}."
        )


def assert_controlled_scopes(rows: list[dict[str, str]]) -> None:
    """Validate policy_scope values use the approved scope vocabulary."""
    invalid_scopes = sorted(
        {
            row["policy_scope"]
            for row in rows
            if row["policy_scope"] not in ALLOWED_SCOPES
        }
    )
    if invalid_scopes:
        raise AssertionError(f"Invalid policy_scope values: {invalid_scopes}")


def assert_related_documents_exist(rows: list[dict[str, str]]) -> None:
    """Validate that every related document path exists."""
    missing_documents = sorted(
        {
            row["related_document"]
            for row in rows
            if not (REPO_ROOT / row["related_document"]).exists()
        }
    )
    if missing_documents:
        raise AssertionError(f"Missing related policy documents: {missing_documents}")


def assert_policy_document_contract() -> None:
    """Validate the written policy contains core reproducibility rules."""
    if not POLICY_DOC_PATH.exists():
        raise AssertionError(f"Missing chronological split policy doc: {POLICY_DOC_PATH}")

    text = POLICY_DOC_PATH.read_text(encoding="utf-8")
    missing_phrases = [
        phrase for phrase in REQUIRED_DOC_PHRASES if phrase not in text
    ]
    if missing_phrases:
        raise AssertionError(
            "Chronological split policy doc is missing required phrases: "
            f"{missing_phrases}"
        )


def run_validation() -> None:
    """Run all chronological split policy validations."""
    rows = read_csv(POLICY_PATH)

    assert_required_columns(rows)
    assert_no_blank_required_cells(rows)
    assert_unique_policy_keys(rows)
    assert_required_policy_values(rows)
    assert_ratio_sum(rows)
    assert_controlled_scopes(rows)
    assert_related_documents_exist(rows)
    assert_policy_document_contract()

    print("Chronological split policy validation passed.")


if __name__ == "__main__":
    run_validation()
