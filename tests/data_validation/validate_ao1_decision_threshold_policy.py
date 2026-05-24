"""Validate AO1 decision-threshold policy artifacts."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pandas as pd


def resolve_repo_root() -> Path:
    """Resolve repository root for local artifact paths."""
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


REPO_ROOT = resolve_repo_root()
POLICY_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_DECISION_THRESHOLD_POLICY_PATH",
        str(REPO_ROOT / "data/references/ao1_decision_threshold_policy.csv"),
    )
)
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_DECISION_THRESHOLD_METADATA_PATH",
        str(REPO_ROOT / "models/ao1_late_delivery/threshold/ao1_decision_threshold_metadata.json"),
    )
)
FINDINGS_PATH = Path(
    os.getenv(
        "DATACO_AO1_DECISION_THRESHOLD_FINDINGS_PATH",
        str(REPO_ROOT / "report/tables/ao1_decision_threshold_recommendation.md"),
    )
)

REQUIRED_POLICY_COLUMNS = {
    "policy_name",
    "issue",
    "decision_status",
    "model_name",
    "selected_threshold",
    "selection_reason",
    "minimum_recall_target",
    "maximum_alert_rate_target",
    "validation_row_count",
    "validation_positive_class_rate",
    "validation_predicted_positive_rate",
    "validation_precision",
    "validation_recall",
    "validation_f1",
    "validation_true_negative",
    "validation_false_positive",
    "validation_false_negative",
    "validation_true_positive",
    "final_test_used",
    "ao3_dashboard_reuse_rule",
}

VALID_STATUSES = {
    "provisional_pending_primary_model",
    "ready_for_team_review",
    "final_approved",
}

UNIT_INTERVAL_COLUMNS = {
    "selected_threshold",
    "minimum_recall_target",
    "maximum_alert_rate_target",
    "validation_positive_class_rate",
    "validation_predicted_positive_rate",
    "validation_precision",
    "validation_recall",
    "validation_f1",
}

COUNT_COLUMNS = {
    "validation_row_count",
    "validation_true_negative",
    "validation_false_positive",
    "validation_false_negative",
    "validation_true_positive",
}


def assert_unit_interval_values(row: pd.Series) -> None:
    """Validate unit-interval policy values."""
    for column_name in UNIT_INTERVAL_COLUMNS:
        value = float(row[column_name])
        assert math.isfinite(value), f"{column_name} must be finite."
        assert 0.0 <= value <= 1.0, f"{column_name} must be within [0, 1]. Found {value}."


def assert_count_values(row: pd.Series) -> None:
    """Validate count-like policy values."""
    for column_name in COUNT_COLUMNS:
        value = float(row[column_name])
        assert value >= 0, f"{column_name} must be non-negative."
        assert value.is_integer(), f"{column_name} must be integer-like."


def main() -> None:
    """Run AO1 decision-threshold policy validation."""
    assert POLICY_CSV_PATH.exists(), f"Missing AO1 threshold policy: {POLICY_CSV_PATH}"
    assert METADATA_PATH.exists(), f"Missing AO1 threshold metadata: {METADATA_PATH}"
    assert FINDINGS_PATH.exists(), f"Missing AO1 threshold findings: {FINDINGS_PATH}"

    policy_df = pd.read_csv(POLICY_CSV_PATH)
    assert len(policy_df) == 1, "AO1 threshold policy must contain exactly one row."

    missing_columns = sorted(REQUIRED_POLICY_COLUMNS.difference(policy_df.columns))
    assert not missing_columns, f"AO1 threshold policy missing columns: {missing_columns}"

    row = policy_df.iloc[0]
    assert row["issue"] == "#67"
    assert row["policy_name"] == "ao1_late_delivery_operating_threshold"
    assert row["decision_status"] in VALID_STATUSES
    assert str(row["final_test_used"]).lower() == "false"
    assert "selected_threshold" in row["ao3_dashboard_reuse_rule"]

    assert_unit_interval_values(row)
    assert_count_values(row)

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["issue"] == "#67"
    assert metadata["metadata_status"] == row["decision_status"]
    assert metadata["selected_policy"]["selected_threshold"] == float(row["selected_threshold"])
    assert metadata["selected_policy"]["final_test_used"] is False

    print("All AO1 decision-threshold policy validation checks passed.")


if __name__ == "__main__":
    main()
