"""Validate the conceptual leakage screening reference table.

This lightweight script is intended to run from the repository root. It checks
the CSV contract for the reviewer-facing leakage screening artifact without
requiring Spark, model training, or Gold-table construction.
"""

from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCREENING_PATH = REPO_ROOT / "data" / "references" / "leakage_conceptual_screening.csv"
FEATURE_MAP_PATH = REPO_ROOT / "data" / "references" / "feature_availability_map.csv"

REQUIRED_COLUMNS = (
    "variable_name",
    "variable_origin",
    "source_artifact",
    "decision_time_availability",
    "ao1_policy",
    "ao2_policy",
    "dashboard_policy",
    "modeling_policy",
    "screening_status",
    "rationale",
    "required_action",
    "related_document",
)

ALLOWED_AO_POLICY_VALUES = {
    "allowed",
    "forbidden",
    "conditional",
    "target",
    "not_applicable",
}
ALLOWED_DASHBOARD_POLICY_VALUES = {
    "allowed",
    "dashboard_only",
    "restricted",
    "not_applicable",
}
ALLOWED_MODELING_POLICY_VALUES = {
    "candidate_feature",
    "forbidden_predictor",
    "conditional_review",
    "target_only",
    "dashboard_only",
}
ALLOWED_SCREENING_STATUS_VALUES = {
    "approved",
    "needs_group_review",
    "deferred_to_gold",
    "excluded",
}

ENGINEERED_FAMILIES = {
    "order_time_engineered": (
        REPO_ROOT / "src" / "data_engineering" / "engineer_order_time_features.py",
        REPO_ROOT / "docs" / "order_time_features.md",
    ),
    "shipping_product_engineered": (
        REPO_ROOT / "src" / "data_engineering" / "engineer_shipping_product_features.py",
        REPO_ROOT / "docs" / "shipping_product_features.md",
    ),
    "customer_regional_engineered": (
        REPO_ROOT / "src" / "data_engineering" / "engineer_customer_regional_features.py",
        REPO_ROOT / "docs" / "customer_regional_features.md",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of dictionaries."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_required_columns(rows: list[dict[str, str]]) -> None:
    """Validate the screening table has the required columns."""
    if not rows:
        raise AssertionError(f"Screening table is empty: {SCREENING_PATH}")

    actual_columns = tuple(rows[0].keys())
    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(actual_columns))
    if missing_columns:
        raise AssertionError(f"Missing required columns: {missing_columns}")


def assert_no_blank_variable_names(rows: list[dict[str, str]]) -> None:
    """Validate every row has a variable name."""
    blank_rows = [
        row_number
        for row_number, row in enumerate(rows, start=2)
        if not row["variable_name"].strip()
    ]
    if blank_rows:
        raise AssertionError(f"Blank variable_name values on rows: {blank_rows}")


def assert_no_duplicate_variable_origin(rows: list[dict[str, str]]) -> None:
    """Validate variable name plus origin uniquely identifies each row."""
    seen: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()

    for row in rows:
        key = (row["variable_name"], row["variable_origin"])
        if key in seen:
            duplicates.add(key)
        seen.add(key)

    if duplicates:
        raise AssertionError(
            f"Duplicate variable_name + variable_origin rows: {sorted(duplicates)}"
        )


def assert_controlled_values(rows: list[dict[str, str]]) -> None:
    """Validate controlled vocabulary columns."""
    validators = {
        "ao1_policy": ALLOWED_AO_POLICY_VALUES,
        "ao2_policy": ALLOWED_AO_POLICY_VALUES,
        "dashboard_policy": ALLOWED_DASHBOARD_POLICY_VALUES,
        "modeling_policy": ALLOWED_MODELING_POLICY_VALUES,
        "screening_status": ALLOWED_SCREENING_STATUS_VALUES,
    }
    invalid_values: list[tuple[str, str, str]] = []

    for row in rows:
        for column_name, allowed_values in validators.items():
            value = row[column_name]
            if value not in allowed_values:
                invalid_values.append((row["variable_name"], column_name, value))

    if invalid_values:
        raise AssertionError(f"Invalid controlled values found: {invalid_values}")


def assert_raw_feature_map_coverage(rows: list[dict[str, str]]) -> None:
    """Validate every raw feature-map field appears in the screening table."""
    feature_map_rows = read_csv(FEATURE_MAP_PATH)
    raw_source_columns = {row["source_column"] for row in feature_map_rows}
    screened_raw_columns = {
        row["variable_name"]
        for row in rows
        if row["variable_origin"] == "raw_dataco"
    }

    missing_raw_columns = sorted(raw_source_columns.difference(screened_raw_columns))
    if missing_raw_columns:
        raise AssertionError(
            "Raw feature map fields missing from screening table: "
            f"{missing_raw_columns}"
        )


def assert_engineered_family_coverage(rows: list[dict[str, str]]) -> None:
    """Validate implemented feature families are represented in the screening table."""
    screened_origins = {row["variable_origin"] for row in rows}
    missing_families = []

    for origin, source_files in ENGINEERED_FAMILIES.items():
        if any(path.exists() for path in source_files) and origin not in screened_origins:
            missing_families.append(origin)

    if missing_families:
        raise AssertionError(
            "Implemented engineered feature families missing from screening table: "
            f"{missing_families}"
        )


def assert_target_rows(rows: list[dict[str, str]]) -> None:
    """Validate the two primary target fields are marked target-only."""
    row_by_key = {
        (row["variable_name"], row["variable_origin"]): row
        for row in rows
    }

    ao1_target = row_by_key.get(("Late_delivery_risk", "raw_dataco"))
    if not ao1_target:
        raise AssertionError("Missing raw AO1 target row: Late_delivery_risk")
    if ao1_target["ao1_policy"] != "target" or ao1_target["modeling_policy"] != "target_only":
        raise AssertionError("Late_delivery_risk must be marked as AO1 target_only.")

    ao2_target = row_by_key.get(("Order Profit Per Order", "raw_dataco"))
    if not ao2_target:
        raise AssertionError("Missing raw AO2 target row: Order Profit Per Order")
    if ao2_target["ao2_policy"] != "target" or ao2_target["modeling_policy"] != "target_only":
        raise AssertionError("Order Profit Per Order must be marked as AO2 target_only.")


def run_validation() -> None:
    """Run all conceptual screening validations."""
    rows = read_csv(SCREENING_PATH)

    assert_required_columns(rows)
    assert_no_blank_variable_names(rows)
    assert_no_duplicate_variable_origin(rows)
    assert_controlled_values(rows)
    assert_raw_feature_map_coverage(rows)
    assert_engineered_family_coverage(rows)
    assert_target_rows(rows)

    print("Conceptual leakage screening validation passed.")


if __name__ == "__main__":
    run_validation()
