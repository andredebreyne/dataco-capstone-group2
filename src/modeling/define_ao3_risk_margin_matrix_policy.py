"""Generate the AO3 risk-margin matrix policy CSV for Issue #40."""

from __future__ import annotations

import csv
import os
from pathlib import Path


POLICY_COLUMNS = [
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
]


def resolve_repo_root() -> Path:
    """Resolve repository root for local and Databricks executions."""
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


def read_single_csv_row(path: Path) -> dict[str, str]:
    """Read a one-row CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as input_file:
        rows = list(csv.DictReader(input_file))
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one row in {path}; found {len(rows)}.")
    return rows[0]


def load_ao1_threshold(ao1_policy_path: Path) -> float:
    """Load the approved AO1 threshold reused by AO3."""
    ao1_policy = read_single_csv_row(ao1_policy_path)
    if ao1_policy.get("model_name") != "ao1_xgboost_classifier":
        raise ValueError("AO1 threshold policy must reference ao1_xgboost_classifier.")
    if str(ao1_policy.get("final_test_used", "")).lower() != "false":
        raise ValueError("AO1 threshold policy must not use final test data.")
    return float(ao1_policy["selected_threshold"])


def build_policy_row(risk_cutoff: float) -> dict[str, object]:
    """Build the governed AO3 policy row."""
    return {
        "policy_name": "ao3_risk_margin_matrix",
        "issue": "#40",
        "policy_status": "ready_for_team_review",
        "risk_signal": "ao1_predicted_late_delivery_probability",
        "risk_cutoff": risk_cutoff,
        "risk_cutoff_source": "data/references/ao1_decision_threshold_policy.csv",
        "margin_signal": "ao3_predicted_margin",
        "margin_cutoff": 0.0,
        "margin_cutoff_source": "break_even_predicted_margin_policy",
        "order_value_denominator": "ao3_order_value",
        "high_risk_high_margin_segment": "protect_high_value_at_risk",
        "high_risk_low_margin_segment": "expedite_selectively",
        "low_risk_high_margin_segment": "preserve_service",
        "low_risk_low_margin_segment": "standard_process",
        "final_test_used": False,
        "notes": "Use predicted AO1 risk and predicted AO2 profit only for segment assignment.",
    }


def write_policy_csv(policy_row: dict[str, object], output_path: Path) -> None:
    """Write the AO3 policy row to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=POLICY_COLUMNS)
        writer.writeheader()
        writer.writerow(policy_row)


def main() -> None:
    """Generate the AO3 risk-margin matrix policy CSV."""
    repo_root = resolve_repo_root()
    ao1_policy_path = Path(
        os.getenv(
            "DATACO_AO1_DECISION_THRESHOLD_POLICY_PATH",
            str(repo_root / "data/references/ao1_decision_threshold_policy.csv"),
        )
    )
    output_path = Path(
        os.getenv(
            "DATACO_AO3_RISK_MARGIN_POLICY_PATH",
            str(repo_root / "data/references/ao3_risk_margin_matrix_policy.csv"),
        )
    )
    write_policy_csv(build_policy_row(load_ao1_threshold(ao1_policy_path)), output_path)
    print(f"AO3 risk-margin matrix policy written to {output_path}")


if __name__ == "__main__":
    main()
