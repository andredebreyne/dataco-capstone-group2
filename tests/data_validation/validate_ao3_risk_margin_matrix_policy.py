"""Validate the AO3 risk-margin matrix design artifacts."""

from __future__ import annotations

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
        if (candidate / "src").exists() and (candidate / "docs").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()

AO3_DOC_PATH = Path(
    os.getenv(
        "DATACO_AO3_RISK_MARGIN_DOC_PATH",
        str(REPO_ROOT / "docs/ao3_risk_margin_matrix.md"),
    )
)
AO3_POLICY_PATH = Path(
    os.getenv(
        "DATACO_AO3_RISK_MARGIN_POLICY_PATH",
        str(REPO_ROOT / "data/references/ao3_risk_margin_matrix_policy.csv"),
    )
)
AO3_GENERATOR_PATH = Path(
    os.getenv(
        "DATACO_AO3_RISK_MARGIN_GENERATOR_PATH",
        str(REPO_ROOT / "src/modeling/define_ao3_risk_margin_matrix_policy.py"),
    )
)
AO1_THRESHOLD_PATH = Path(
    os.getenv(
        "DATACO_AO1_DECISION_THRESHOLD_POLICY_PATH",
        str(REPO_ROOT / "data/references/ao1_decision_threshold_policy.csv"),
    )
)

REQUIRED_POLICY_COLUMNS = {
    "policy_name",
    "issue",
    "policy_status",
    "risk_signal",
    "risk_cutoff",
    "risk_cutoff_source",
    "margin_signal",
    "margin_cutoff",
    "margin_cutoff_source",
    "order_value_denominator",
    "high_risk_high_margin_segment",
    "high_risk_low_margin_segment",
    "low_risk_high_margin_segment",
    "low_risk_low_margin_segment",
    "final_test_used",
    "notes",
}

REQUIRED_DOC_PHRASES = {
    "AO3 Risk-Margin Matrix Logic",
    "ao1_predicted_late_delivery_probability >= 0.35",
    "ao3_predicted_margin = ao2_predicted_order_profit / ao3_order_value",
    "high_margin = ao3_predicted_margin >= 0.00",
    "src/modeling/define_ao3_risk_margin_matrix_policy.py",
    "protect_high_value_at_risk",
    "expedite_selectively",
    "preserve_service",
    "standard_process",
    "Use predicted AO1 risk, not actual `Late_delivery_risk`",
    "Use predicted AO2 profit, not actual `Order_Profit_Per_Order`",
}


def main() -> None:
    """Run AO3 risk-margin matrix policy validation."""
    assert AO3_DOC_PATH.exists(), f"Missing AO3 design document: {AO3_DOC_PATH}"
    assert AO3_POLICY_PATH.exists(), f"Missing AO3 policy CSV: {AO3_POLICY_PATH}"
    assert AO3_GENERATOR_PATH.exists(), f"Missing AO3 policy generator: {AO3_GENERATOR_PATH}"
    assert AO1_THRESHOLD_PATH.exists(), f"Missing AO1 threshold policy: {AO1_THRESHOLD_PATH}"

    document_text = AO3_DOC_PATH.read_text(encoding="utf-8")
    missing_phrases = sorted(
        phrase for phrase in REQUIRED_DOC_PHRASES if phrase not in document_text
    )
    assert not missing_phrases, f"AO3 document is missing required phrases: {missing_phrases}"

    policy_df = pd.read_csv(AO3_POLICY_PATH)
    assert len(policy_df) == 1, "AO3 risk-margin policy must contain exactly one row."

    missing_columns = sorted(REQUIRED_POLICY_COLUMNS.difference(policy_df.columns))
    assert not missing_columns, f"AO3 policy missing columns: {missing_columns}"

    policy = policy_df.iloc[0]
    assert policy["issue"] == "#40"
    assert policy["policy_name"] == "ao3_risk_margin_matrix"
    assert policy["policy_status"] == "ready_for_team_review"
    assert policy["risk_signal"] == "ao1_predicted_late_delivery_probability"
    assert float(policy["risk_cutoff"]) == 0.35
    assert policy["margin_signal"] == "ao3_predicted_margin"
    assert float(policy["margin_cutoff"]) == 0.0
    assert policy["order_value_denominator"] == "ao3_order_value"
    assert str(policy["final_test_used"]).lower() == "false"

    segments = {
        policy["high_risk_high_margin_segment"],
        policy["high_risk_low_margin_segment"],
        policy["low_risk_high_margin_segment"],
        policy["low_risk_low_margin_segment"],
    }
    expected_segments = {
        "protect_high_value_at_risk",
        "expedite_selectively",
        "preserve_service",
        "standard_process",
    }
    assert segments == expected_segments, f"Unexpected AO3 segments: {segments}"

    ao1_policy_df = pd.read_csv(AO1_THRESHOLD_PATH)
    assert len(ao1_policy_df) == 1, "AO1 threshold policy must contain exactly one row."
    ao1_policy = ao1_policy_df.iloc[0]
    assert ao1_policy["model_name"] == "ao1_xgboost_classifier"
    assert float(ao1_policy["selected_threshold"]) == float(policy["risk_cutoff"])
    assert str(ao1_policy["final_test_used"]).lower() == "false"

    forbidden_phrases = {
        "use actual profit",
        "use actual late delivery",
        "retune using final test",
    }
    normalized_text = document_text.lower()
    matched_forbidden = sorted(
        phrase for phrase in forbidden_phrases if phrase in normalized_text
    )
    assert not matched_forbidden, (
        f"AO3 document contains unsafe wording: {matched_forbidden}"
    )

    print("AO3 risk-margin matrix policy validation passed.")


if __name__ == "__main__":
    main()
