"""Validate AO2 target-reconstruction audit artifacts."""

from __future__ import annotations

import json
import math
import os
import re
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
        if (candidate / "models").exists() and (candidate / "report").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()

METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_TARGET_RECONSTRUCTION_METADATA_PATH",
        str(
            REPO_ROOT
            / "models/ao2_profitability/target_reconstruction_audit/ao2_target_reconstruction_audit_metadata.json"
        ),
    )
)
FORBIDDEN_CHECK_PATH = Path(
    os.getenv(
        "DATACO_AO2_TARGET_RECONSTRUCTION_FORBIDDEN_CHECK_PATH",
        str(REPO_ROOT / "report/tables/ao2_target_reconstruction_forbidden_feature_check.csv"),
    )
)
DRIVER_REVIEW_PATH = Path(
    os.getenv(
        "DATACO_AO2_TARGET_RECONSTRUCTION_DRIVER_REVIEW_PATH",
        str(REPO_ROOT / "report/tables/ao2_target_reconstruction_driver_review.csv"),
    )
)
FINDINGS_PATH = Path(
    os.getenv(
        "DATACO_AO2_TARGET_RECONSTRUCTION_FINDINGS_PATH",
        str(REPO_ROOT / "report/tables/ao2_target_reconstruction_audit_findings.md"),
    )
)

VALID_FINAL_DECISIONS = {"accepted", "accepted_with_caution", "blocked"}
FORBIDDEN_ROLES_FOR_AO3_VALUE = {
    "predictor",
    "shap_driver",
    "feature_importance_driver",
}

REQUIRED_FORBIDDEN_CHECK_COLUMNS = {
    "source_artifact",
    "feature_name",
    "normalized_feature_name",
    "feature_role",
    "policy_status",
    "matched_policy_rule",
    "review_note",
}
REQUIRED_DRIVER_REVIEW_COLUMNS = {
    "driver_source",
    "feature_name",
    "rank",
    "importance_value",
    "mean_abs_shap_value",
    "policy_status",
    "target_reconstruction_risk",
    "business_plausibility",
    "review_decision",
    "review_note",
}


def normalize_feature_name(feature_name: object) -> str:
    """Normalize feature names for policy checks."""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(feature_name).strip().lower())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def read_required_csv(path: Path) -> pd.DataFrame:
    """Read a required non-empty CSV artifact."""
    assert path.exists(), f"Missing required artifact: {path}"
    frame = pd.read_csv(path)
    assert not frame.empty, f"Artifact is empty: {path}"
    return frame


def assert_columns(frame: pd.DataFrame, required_columns: set[str], name: str) -> None:
    """Assert expected columns are present."""
    missing_columns = sorted(required_columns.difference(frame.columns))
    assert not missing_columns, f"{name} is missing columns: {missing_columns}"


def validate_metadata() -> dict:
    """Validate AO2 target-reconstruction audit metadata."""
    assert METADATA_PATH.exists(), f"Missing metadata artifact: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert metadata["metadata_status"] == "ao2_target_reconstruction_audit_completed"
    assert metadata["issue_id"] == "#73"
    assert metadata["issue"] == "#73"
    assert metadata["final_test_used"] is False
    assert metadata["target_column"] == "Order_Profit_Per_Order"
    assert metadata["selected_ao2_model_reviewed"] == "ao2_gradient_boosting_regressor"
    assert metadata["selected_candidate"], "Selected candidate is missing."
    assert metadata["final_audit_decision"] in VALID_FINAL_DECISIONS
    assert isinstance(metadata["output_artifact_paths"], dict)
    assert metadata["input_artifacts_reviewed"], "Input artifacts reviewed are missing."
    assert metadata["ablation_sensitivity_status"], "Ablation/sensitivity status is missing."
    assert metadata["accepted_caveats"], "Accepted caveats or blockers are missing."

    forbidden_count = metadata["forbidden_feature_count"]
    assert isinstance(forbidden_count, (int, float)), "Forbidden feature count must be numeric."
    assert math.isfinite(float(forbidden_count)), "Forbidden feature count must be finite."
    assert float(forbidden_count) >= 0, "Forbidden feature count must be non-negative."

    if float(forbidden_count) > 0:
        assert metadata["final_audit_decision"] == "blocked"
    if metadata["final_audit_decision"] in {"accepted", "accepted_with_caution"}:
        assert float(forbidden_count) == 0

    return metadata


def validate_forbidden_check(frame: pd.DataFrame, metadata: dict) -> None:
    """Validate forbidden-feature check table."""
    assert_columns(frame, REQUIRED_FORBIDDEN_CHECK_COLUMNS, "Forbidden feature check")
    assert set(frame["policy_status"]).issubset({"allowed", "caution", "forbidden"})

    forbidden_rule_rows = frame["matched_policy_rule"].astype(str).str.startswith("forbidden")
    incorrectly_allowed_forbidden = frame[
        forbidden_rule_rows & (frame["policy_status"] == "allowed")
    ]
    assert incorrectly_allowed_forbidden.empty, (
        "No forbidden feature rule may be classified as allowed."
    )

    forbidden_rows = frame[frame["policy_status"] == "forbidden"]
    assert len(forbidden_rows) == int(metadata["forbidden_feature_count"])

    ao3_rows = frame[
        frame["normalized_feature_name"].astype(str).map(normalize_feature_name).str.contains(
            "ao3_order_value",
            regex=False,
        )
        & frame["feature_role"].isin(FORBIDDEN_ROLES_FOR_AO3_VALUE)
    ]
    assert ao3_rows.empty, "`ao3_order_value` must not appear as predictor, SHAP driver, or importance driver."


def validate_driver_review(frame: pd.DataFrame) -> None:
    """Validate compact driver review table."""
    assert_columns(frame, REQUIRED_DRIVER_REVIEW_COLUMNS, "Driver review")
    assert set(frame["driver_source"]).issubset({"xgboost_importance", "shap"})
    assert set(frame["policy_status"]).issubset({"allowed", "caution", "forbidden"})
    assert set(frame["review_decision"]).issubset(
        {"accepted", "accepted_with_caution", "blocked"}
    )

    ranks = pd.to_numeric(frame["rank"], errors="coerce")
    assert ranks.notna().all(), "Driver review ranks must be numeric."
    assert (ranks > 0).all(), "Driver review ranks must be positive."
    assert ((ranks % 1) == 0).all(), "Driver review ranks must be integers."

    ao3_rows = frame[
        frame["feature_name"].astype(str).map(normalize_feature_name).str.contains(
            "ao3_order_value",
            regex=False,
        )
    ]
    assert ao3_rows.empty, "`ao3_order_value` must not appear in driver review."


def validate_findings() -> None:
    """Validate required findings-language coverage."""
    assert FINDINGS_PATH.exists(), f"Missing findings artifact: {FINDINGS_PATH}"
    findings_text = FINDINGS_PATH.read_text(encoding="utf-8").lower()
    required_phrases = {
        "target reconstruction",
        "predictor audit",
        "shap",
        "feature importance",
        "ablation",
        "sensitivity",
        "final test not used",
        "accepted caveats",
        "final audit decision",
    }
    missing_phrases = [phrase for phrase in sorted(required_phrases) if phrase not in findings_text]
    assert not missing_phrases, f"Findings are missing required language: {missing_phrases}"
    assert "blocked" in findings_text or "accepted" in findings_text, (
        "Findings must mention accepted caveats or blockers."
    )


def main() -> None:
    """Run all AO2 target-reconstruction audit validations."""
    metadata = validate_metadata()
    forbidden_check_df = read_required_csv(FORBIDDEN_CHECK_PATH)
    driver_review_df = read_required_csv(DRIVER_REVIEW_PATH)

    assert FINDINGS_PATH.exists(), f"Missing findings markdown: {FINDINGS_PATH}"
    validate_forbidden_check(forbidden_check_df, metadata)
    validate_driver_review(driver_review_df)
    validate_findings()

    print("AO2 target-reconstruction audit validation passed.")


if __name__ == "__main__":
    main()
