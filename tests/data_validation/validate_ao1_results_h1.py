"""Validate AO1 results and H1 documentation artifacts."""

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

DOC_PATH = Path(
    os.getenv(
        "DATACO_AO1_RESULTS_H1_DOC_PATH",
        str(REPO_ROOT / "docs/ao1_results_h1_validation.md"),
    )
)
SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO1_RESULTS_H1_SUMMARY_PATH",
        str(REPO_ROOT / "data/references/ao1_results_h1_summary.csv"),
    )
)
MODEL_COMPARISON_PATH = Path(
    os.getenv(
        "DATACO_AO1_MODEL_COMPARISON_PATH",
        str(REPO_ROOT / "report/tables/ao1_model_validation_comparison.csv"),
    )
)
THRESHOLD_GRID_PATH = Path(
    os.getenv(
        "DATACO_AO1_THRESHOLD_GRID_PATH",
        str(REPO_ROOT / "report/tables/ao1_threshold_tradeoff_grid.csv"),
    )
)
SHAP_DRIVER_SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO1_SHAP_DRIVER_SUMMARY_PATH",
        str(REPO_ROOT / "report/tables/ao1_shap_driver_summary.csv"),
    )
)
LEAKAGE_AUDIT_PATH = Path(
    os.getenv(
        "DATACO_AO1_POST_MODEL_LEAKAGE_AUDIT_PATH",
        str(REPO_ROOT / "docs/ao1_post_model_leakage_audit.md"),
    )
)

REQUIRED_DOC_PHRASES = {
    "for late-delivery prediction, an xgboost classifier will outperform logistic regression",
    "h1 is supported at the validation stage",
    "final test partition remains reserved",
    "xgboost outperforms the logistic regression baseline",
    "predicted_probability >= 0.35",
    "leakage-safe enough to report with caveats",
    "no evidence of post-outcome leakage",
    "model associations, not causal effects",
    "first class",
    "geography",
    "validation evidence supports h1",
}

REQUIRED_SUMMARY_COLUMNS = {
    "hypothesis",
    "evidence_source",
    "logistic_regression_roc_auc",
    "xgboost_roc_auc",
    "logistic_regression_recall",
    "xgboost_recall",
    "h1_decision",
    "threshold_reference",
    "leakage_audit_status",
    "shap_driver_caveat",
    "final_test_status",
    "limitations",
}
STALE_STATUS_WORDS = {"pending", "provisional", "pending_final_qa"}


def main() -> None:
    """Run AO1 H1 results validation checks."""
    assert DOC_PATH.exists(), f"Missing AO1 H1 results document: {DOC_PATH}"
    assert SUMMARY_PATH.exists(), f"Missing AO1 H1 summary CSV: {SUMMARY_PATH}"
    assert MODEL_COMPARISON_PATH.exists(), (
        f"Missing AO1 model comparison: {MODEL_COMPARISON_PATH}"
    )
    assert THRESHOLD_GRID_PATH.exists(), f"Missing AO1 threshold grid: {THRESHOLD_GRID_PATH}"
    assert SHAP_DRIVER_SUMMARY_PATH.exists(), (
        f"Missing AO1 SHAP driver summary: {SHAP_DRIVER_SUMMARY_PATH}"
    )
    assert LEAKAGE_AUDIT_PATH.exists(), f"Missing AO1 leakage audit: {LEAKAGE_AUDIT_PATH}"

    document_text = DOC_PATH.read_text(encoding="utf-8")
    normalized_document_text = " ".join(document_text.lower().split())
    missing_phrases = sorted(
        phrase for phrase in REQUIRED_DOC_PHRASES if phrase not in normalized_document_text
    )
    assert not missing_phrases, f"AO1 H1 document is missing phrases: {missing_phrases}"
    assert "final test" in normalized_document_text
    assert "not used" in normalized_document_text
    assert "causal" in normalized_document_text

    leakage_audit_text = LEAKAGE_AUDIT_PATH.read_text(encoding="utf-8").lower()
    assert "leakage-safe-with-caveats" in leakage_audit_text
    assert "final test partition remains untouched" in leakage_audit_text

    summary_df = pd.read_csv(SUMMARY_PATH)
    missing_summary_columns = sorted(
        REQUIRED_SUMMARY_COLUMNS.difference(set(summary_df.columns))
    )
    assert not missing_summary_columns, (
        f"AO1 H1 summary is missing columns: {missing_summary_columns}"
    )
    assert len(summary_df) == 1, "AO1 H1 summary should contain one summary row."

    normalized_summary_text = " ".join(
        summary_df.astype(str).to_string(index=False).lower().split()
    )
    stale_words = sorted(word for word in STALE_STATUS_WORDS if word in normalized_summary_text)
    assert not stale_words, f"AO1 H1 summary contains stale status words: {stale_words}"

    summary_row = summary_df.iloc[0]
    assert summary_row["h1_decision"] == "validation_supported"
    assert "leakage_safe_with_caveats" in str(summary_row["leakage_audit_status"])
    assert summary_row["final_test_status"] == "reserved_unused"
    assert "0.35" in str(summary_row["threshold_reference"])
    assert "not causal" in str(summary_row["limitations"]).lower()
    assert "geography" in str(summary_row["shap_driver_caveat"]).lower()

    shap_df = pd.read_csv(SHAP_DRIVER_SUMMARY_PATH)
    assert not shap_df.empty, "AO1 SHAP driver summary should not be empty."
    top_shap_feature = str(shap_df.iloc[0]["feature_name"])
    assert top_shap_feature in document_text
    assert float(shap_df.iloc[0]["importance_share"]) > 0

    has_geography_driver = shap_df["feature_name"].str.contains(
        "order_state|order_country", case=False, regex=True
    ).any()
    assert has_geography_driver, "Expected geography SHAP drivers in summary artifact."

    if "shipping_mode" in top_shap_feature:
        assert "dominant" in normalized_document_text
        assert "shipping" in normalized_document_text

    if has_geography_driver:
        assert "high-cardinality" in normalized_document_text
        assert "sparse" in normalized_document_text

    metrics_df = pd.read_csv(MODEL_COMPARISON_PATH)
    required_models = {"ao1_xgboost_classifier", "ao1_logistic_regression_baseline"}
    assert required_models.issubset(set(metrics_df["model_name"]))

    xgboost_row = metrics_df.loc[
        metrics_df["model_name"] == "ao1_xgboost_classifier"
    ].iloc[0]
    logistic_row = metrics_df.loc[
        metrics_df["model_name"] == "ao1_logistic_regression_baseline"
    ].iloc[0]
    assert xgboost_row["roc_auc"] > logistic_row["roc_auc"]
    assert xgboost_row["recall"] > logistic_row["recall"]
    assert bool(xgboost_row["roc_auc"] < 0.95), "AO1 validation metric is implausibly high."
    assert summary_row["xgboost_roc_auc"] == round(float(xgboost_row["roc_auc"]), 4)
    assert summary_row["logistic_regression_roc_auc"] == round(
        float(logistic_row["roc_auc"]), 4
    )
    assert summary_row["xgboost_recall"] == round(float(xgboost_row["recall"]), 4)
    assert summary_row["logistic_regression_recall"] == round(
        float(logistic_row["recall"]), 4
    )

    threshold_df = pd.read_csv(THRESHOLD_GRID_PATH)
    selected = threshold_df[
        (threshold_df["model_name"] == "ao1_xgboost_classifier")
        & (threshold_df["threshold"] == 0.35)
    ]
    assert len(selected) == 1, "Expected XGBoost threshold 0.35 in threshold grid."
    selected_row = selected.iloc[0]
    assert selected_row["predicted_positive_rate"] <= 0.65
    assert selected_row["recall"] > xgboost_row["recall"]

    print("All AO1 H1 results validation checks passed.")


if __name__ == "__main__":
    main()
