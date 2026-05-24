"""Validate AO1 post-model leakage audit documentation."""

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

AUDIT_DOC_PATH = Path(
    os.getenv(
        "DATACO_AO1_POST_MODEL_LEAKAGE_AUDIT_DOC_PATH",
        str(REPO_ROOT / "docs/ao1_post_model_leakage_audit.md"),
    )
)
AUDIT_REFERENCE_PATH = Path(
    os.getenv(
        "DATACO_AO1_POST_MODEL_LEAKAGE_AUDIT_REFERENCE_PATH",
        str(REPO_ROOT / "data/references/ao1_post_model_leakage_audit.csv"),
    )
)

REQUIRED_AUDIT_COLUMNS = {
    "audit_area",
    "source_artifact",
    "check_performed",
    "result",
    "status",
}

REQUIRED_DOC_PHRASES = {
    "final test partition remains reserved",
    "validation only",
    "forbidden as AO1 predictors",
    "SMOTE is not used",
    "SHAP outputs must be reviewed",
    "provisional leakage-safe status",
}

REQUIRED_AUDIT_AREAS = {
    "chronological_split",
    "preprocessing_fit_scope",
    "logistic_baseline_scope",
    "xgboost_scope",
    "evaluation_pack_scope",
    "threshold_policy_scope",
    "performance_plausibility",
    "forbidden_predictor_review",
    "resampling_review",
    "shap_plausibility",
    "final_conclusion",
}

ALLOWED_STATUSES = {"passed", "pending", "provisional"}


def main() -> None:
    """Run AO1 post-model leakage audit validation checks."""
    assert AUDIT_DOC_PATH.exists(), f"Missing audit document: {AUDIT_DOC_PATH}"
    assert AUDIT_REFERENCE_PATH.exists(), f"Missing audit reference CSV: {AUDIT_REFERENCE_PATH}"

    audit_text = AUDIT_DOC_PATH.read_text(encoding="utf-8").lower()
    missing_phrases = sorted(
        phrase for phrase in REQUIRED_DOC_PHRASES if phrase.lower() not in audit_text
    )
    assert not missing_phrases, f"Audit document is missing required phrases: {missing_phrases}"

    audit_df = pd.read_csv(AUDIT_REFERENCE_PATH)
    assert not audit_df.empty, "AO1 leakage audit reference table is empty."

    missing_columns = sorted(REQUIRED_AUDIT_COLUMNS.difference(audit_df.columns))
    assert not missing_columns, f"Audit reference is missing columns: {missing_columns}"

    observed_areas = set(audit_df["audit_area"])
    missing_areas = sorted(REQUIRED_AUDIT_AREAS.difference(observed_areas))
    assert not missing_areas, f"Audit reference is missing audit areas: {missing_areas}"

    invalid_statuses = sorted(set(audit_df["status"]) - ALLOWED_STATUSES)
    assert not invalid_statuses, f"Audit reference has invalid statuses: {invalid_statuses}"

    assert "shap_plausibility" in set(
        audit_df.loc[audit_df["status"].isin({"pending", "provisional"}), "audit_area"]
    ), "SHAP plausibility must remain pending/provisional until Issue #30 is reviewed."

    print("All AO1 post-model leakage audit validation checks passed.")


if __name__ == "__main__":
    main()
