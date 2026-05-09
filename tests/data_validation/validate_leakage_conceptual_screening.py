"""Validate the conceptual leakage screening reference table.

This lightweight script is intended to run from the repository root. It checks
the CSV contract for the reviewer-facing leakage screening artifact without
requiring Spark, model training, or Gold-table construction.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path


def resolve_repo_root() -> Path:
    """Resolve the repository root in scripts and Databricks notebook runs."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).resolve()

    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]

    current_path = Path.cwd().resolve()
    candidate_paths = (current_path, *current_path.parents)
    for candidate_path in candidate_paths:
        if (candidate_path / "data" / "references" / "feature_availability_map.csv").exists():
            return candidate_path

    return current_path


REPO_ROOT = resolve_repo_root()
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

EXPECTED_ENGINEERED_FEATURES = {
    "order_time_engineered": {
        "order_year",
        "order_quarter",
        "order_month",
        "order_week_of_year",
        "order_day_of_month",
        "order_day_of_week",
        "order_hour",
        "order_is_weekend",
        "order_season",
        "_order_time_features_processed_timestamp",
    },
    "shipping_product_engineered": {
        "scheduled_shipping_days",
        "shipping_speed_tier",
        "shipping_mode_normalized",
        "is_same_day_or_next_day_shipping",
        "is_standard_shipping",
        "product_category_key",
        "product_department_key",
        "product_catalog_key",
        "product_name_normalized",
        "product_status_flag",
        "product_list_price",
        "order_item_quantity",
        "item_unit_price",
        "item_discount_amount",
        "item_discount_rate",
        "item_gross_sales_estimate",
        "item_net_sales_amount",
        "item_discount_share_of_gross",
        "_shipping_product_features_processed_timestamp",
    },
    "customer_regional_engineered": {
        "customer_segment_normalized",
        "customer_country_normalized",
        "customer_state_normalized",
        "customer_city_normalized",
        "customer_zipcode_available",
        "market_normalized",
        "order_country_normalized",
        "order_region_normalized",
        "order_state_normalized",
        "order_city_normalized",
        "order_zipcode_available",
        "customer_region_key",
        "order_region_key",
        "customer_order_country_match",
        "customer_order_state_match",
        "latitude_rounded",
        "longitude_rounded",
        "geo_coordinates_available",
        "_customer_regional_features_processed_timestamp",
    },
}

CRITICAL_FORBIDDEN_PROXY_FIELDS = {
    "Delivery Status",
    "Days for shipping (real)",
    "Benefit per order",
    "Order Item Profit Ratio",
    "shipping date (DateOrders)",
    "Order Status",
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


def assert_engineered_feature_coverage(rows: list[dict[str, str]]) -> None:
    """Validate current engineered feature contracts are represented by feature."""
    screened_by_origin: dict[str, set[str]] = {}
    for row in rows:
        screened_by_origin.setdefault(row["variable_origin"], set()).add(
            row["variable_name"]
        )

    missing_features: dict[str, list[str]] = {}
    for origin, expected_features in EXPECTED_ENGINEERED_FEATURES.items():
        if not any(path.exists() for path in ENGINEERED_FAMILIES[origin]):
            continue

        missing_for_origin = sorted(
            expected_features.difference(screened_by_origin.get(origin, set()))
        )
        if missing_for_origin:
            missing_features[origin] = missing_for_origin

    if missing_features:
        raise AssertionError(
            "Implemented engineered features missing from screening table: "
            f"{missing_features}"
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


def assert_critical_forbidden_proxy_rows(rows: list[dict[str, str]]) -> None:
    """Validate critical leakage proxies remain forbidden for AO1 and AO2."""
    rows_by_name = {
        row["variable_name"]: row
        for row in rows
        if row["variable_origin"] == "raw_dataco"
    }
    missing_fields = sorted(
        field_name
        for field_name in CRITICAL_FORBIDDEN_PROXY_FIELDS
        if field_name not in rows_by_name
    )
    if missing_fields:
        raise AssertionError(
            f"Missing critical forbidden/proxy fields: {missing_fields}"
        )

    invalid_fields = []
    for field_name in sorted(CRITICAL_FORBIDDEN_PROXY_FIELDS):
        row = rows_by_name[field_name]
        if (
            row["ao1_policy"] != "forbidden"
            or row["ao2_policy"] != "forbidden"
            or row["dashboard_policy"] != "dashboard_only"
            or row["modeling_policy"] != "dashboard_only"
        ):
            invalid_fields.append(
                (
                    field_name,
                    row["ao1_policy"],
                    row["ao2_policy"],
                    row["dashboard_policy"],
                    row["modeling_policy"],
                )
            )

    if invalid_fields:
        raise AssertionError(
            "Critical leakage/proxy fields must stay forbidden for AO1/AO2 "
            f"and dashboard_only for dashboard/modeling: {invalid_fields}"
        )


def run_validation() -> None:
    """Run all conceptual screening validations."""
    rows = read_csv(SCREENING_PATH)

    assert_required_columns(rows)
    assert_no_blank_variable_names(rows)
    assert_no_duplicate_variable_origin(rows)
    assert_controlled_values(rows)
    assert_raw_feature_map_coverage(rows)
    assert_engineered_family_coverage(rows)
    assert_engineered_feature_coverage(rows)
    assert_target_rows(rows)
    assert_critical_forbidden_proxy_rows(rows)

    print("Conceptual leakage screening validation passed.")


if __name__ == "__main__":
    run_validation()
