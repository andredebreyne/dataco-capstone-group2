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
    "finding",
    "corrective_action",
}

REQUIRED_DOC_PHRASES = {
    "final test partition remains reserved",
    "validation only",
    "forbidden as AO1 predictors",
    "SMOTE is not used",
    "Top SHAP driver review",
    "shipping_mode_normalized_first_class",
    "scheduled_shipping_days",
    "order_state_normalized",
    "historical aggregate features were not used",
    "No model-removal corrective action is required",
    "leakage-safe-with-caveats status",
    "not causal effects",
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
    "historical_aggregate_review",
    "shap_plausibility",
    "final_conclusion",
}

ALLOWED_STATUSES = {"passed", "caution", "failed", "pending"}
COMPLETED_REVIEW_STATUSES = {"passed", "caution"}

METRICS_PATH = REPO_ROOT / "report/tables/ao1_model_validation_comparison.csv"
SHAP_DRIVER_SUMMARY_PATH = REPO_ROOT / "report/tables/ao1_shap_driver_summary.csv"

FORBIDDEN_OVERCLAIM_PHRASES = {
    "guarantees no leakage",
    "proves no leakage",
    "proven no leakage",
    "confirmed no leakage exists",
    "causal proof",
    "causes late delivery",
}


def assert_required_phrases(audit_text: str) -> None:
    """Validate required audit memo coverage."""
    missing_phrases = sorted(
        phrase for phrase in REQUIRED_DOC_PHRASES if phrase.lower() not in audit_text
    )
    assert not missing_phrases, f"Audit document is missing required phrases: {missing_phrases}"


def assert_no_overclaim_language(audit_text: str) -> None:
    """Validate that the memo avoids causal or leakage-impossibility overclaims."""
    overclaims = sorted(
        phrase for phrase in FORBIDDEN_OVERCLAIM_PHRASES if phrase in audit_text
    )
    assert not overclaims, f"Audit document contains overclaim language: {overclaims}"


def assert_metrics_are_current(audit_text: str) -> None:
    """Confirm the memo references current committed validation metrics."""
    assert METRICS_PATH.exists(), f"Missing AO1 validation metrics artifact: {METRICS_PATH}"
    metrics_df = pd.read_csv(METRICS_PATH)
    required_models = {"ao1_logistic_regression_baseline", "ao1_xgboost_classifier"}
    observed_models = set(metrics_df["model_name"])
    missing_models = sorted(required_models.difference(observed_models))
    assert not missing_models, f"Metrics artifact is missing models: {missing_models}"

    for model_name in required_models:
        row = metrics_df.loc[metrics_df["model_name"] == model_name].iloc[0]
        expected_values = [
            f"{row['roc_auc']:.6f}",
            f"{row['pr_auc']:.6f}",
            f"{row['recall']:.6f}",
        ]
        missing_values = [value for value in expected_values if value not in audit_text]
        assert not missing_values, (
            f"Audit document does not include current metrics for {model_name}: "
            f"{missing_values}"
        )


def assert_shap_review_is_current(audit_text: str) -> None:
    """Confirm the memo reviews actual committed SHAP top-driver output."""
    assert SHAP_DRIVER_SUMMARY_PATH.exists(), (
        f"Missing AO1 SHAP driver summary: {SHAP_DRIVER_SUMMARY_PATH}"
    )
    shap_df = pd.read_csv(SHAP_DRIVER_SUMMARY_PATH)
    assert not shap_df.empty, "AO1 SHAP driver summary is empty."

    top_feature = str(shap_df.sort_values("rank").iloc[0]["feature_name"]).lower()
    assert top_feature in audit_text, (
        f"Audit document does not mention current top SHAP driver: {top_feature}"
    )


def main() -> None:
    """Run AO1 post-model leakage audit validation checks."""
    assert AUDIT_DOC_PATH.exists(), f"Missing audit document: {AUDIT_DOC_PATH}"
    assert AUDIT_REFERENCE_PATH.exists(), f"Missing audit reference CSV: {AUDIT_REFERENCE_PATH}"

    audit_text = AUDIT_DOC_PATH.read_text(encoding="utf-8").lower()
    assert_required_phrases(audit_text)
    assert_no_overclaim_language(audit_text)
    assert_metrics_are_current(audit_text)
    assert_shap_review_is_current(audit_text)

    audit_df = pd.read_csv(AUDIT_REFERENCE_PATH)
    assert not audit_df.empty, "AO1 leakage audit reference table is empty."

    missing_columns = sorted(REQUIRED_AUDIT_COLUMNS.difference(audit_df.columns))
    assert not missing_columns, f"Audit reference is missing columns: {missing_columns}"

    observed_areas = set(audit_df["audit_area"])
    missing_areas = sorted(REQUIRED_AUDIT_AREAS.difference(observed_areas))
    assert not missing_areas, f"Audit reference is missing audit areas: {missing_areas}"

    invalid_statuses = sorted(set(audit_df["status"]) - ALLOWED_STATUSES)
    assert not invalid_statuses, f"Audit reference has invalid statuses: {invalid_statuses}"

    shap_rows = audit_df.loc[audit_df["audit_area"] == "shap_plausibility"]
    assert len(shap_rows) == 1, "Audit reference must contain exactly one SHAP plausibility row."
    shap_status = shap_rows.iloc[0]["status"]
    assert shap_status in COMPLETED_REVIEW_STATUSES, (
        "SHAP plausibility must be marked passed or caution after Issue #30 review. "
        f"Observed: {shap_status}"
    )

    print("All AO1 post-model leakage audit validation checks passed.")


if __name__ == "__main__":
    main()
