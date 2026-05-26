"""Validate AO2 results and H2 documentation artifacts."""

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
        if (candidate / "models").exists() and (candidate / "report").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()

METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_RESULTS_H2_METADATA_PATH",
        str(REPO_ROOT / "models/ao2_profitability/results/ao2_results_h2_metadata.json"),
    )
)
SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO2_RESULTS_H2_SUMMARY_PATH",
        str(REPO_ROOT / "report/tables/ao2_results_h2_summary.csv"),
    )
)
FINDINGS_PATH = Path(
    os.getenv(
        "DATACO_AO2_RESULTS_H2_FINDINGS_PATH",
        str(REPO_ROOT / "report/tables/ao2_results_h2_findings.md"),
    )
)
DOC_PATH = Path(
    os.getenv(
        "DATACO_AO2_RESULTS_H2_DOC_PATH",
        str(REPO_ROOT / "docs/ao2_results_h2.md"),
    )
)
EVALUATION_METRICS_PATH = Path(
    os.getenv(
        "DATACO_AO2_EVALUATION_METRICS_PATH",
        str(REPO_ROOT / "report/tables/ao2_model_evaluation_metrics.csv"),
    )
)
TARGET_AUDIT_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_TARGET_RECONSTRUCTION_METADATA_PATH",
        str(
            REPO_ROOT
            / "models/ao2_profitability/target_reconstruction_audit/ao2_target_reconstruction_audit_metadata.json"
        ),
    )
)

SUPPORTED_DECISIONS = {"validation_supported", "supported_validation"}
REQUIRED_SUMMARY_COLUMNS = {
    "hypothesis",
    "evidence_slice",
    "baseline_model",
    "primary_model",
    "baseline_rmse",
    "primary_rmse",
    "rmse_improvement",
    "baseline_mae",
    "primary_mae",
    "mae_improvement",
    "baseline_r2",
    "primary_r2",
    "h2_decision",
    "support_strength",
    "final_test_used",
    "target_policy_status",
    "main_limitations",
}
REQUIRED_TEXT_CONCEPTS = {
    "target definition": ("order_profit_per_order",),
    "ridge baseline": ("ridge baseline", "ridge regression"),
    "gradient boosting": ("gradient boosting", "xgboost"),
    "rmse": ("rmse",),
    "mae": ("mae",),
    "r-squared": ("r-squared", "r2", "r²"),
    "residual review": ("residual review", "residual"),
    "explainability": ("shap", "explainability"),
    "target reconstruction audit": ("target-reconstruction audit", "target reconstruction"),
    "final test not used": ("final test not used", "final test partition was not used"),
    "h2 conclusion": ("h2 conclusion", "h2 is supported"),
    "limitations": ("limitations",),
}


def read_json(path: Path) -> dict:
    """Read a required JSON artifact."""
    assert path.exists(), f"Missing required JSON artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def read_nonempty_csv(path: Path) -> pd.DataFrame:
    """Read a required non-empty CSV artifact."""
    assert path.exists(), f"Missing required CSV artifact: {path}"
    frame = pd.read_csv(path)
    assert not frame.empty, f"CSV artifact is empty: {path}"
    return frame


def normalize_text(text: str) -> str:
    """Normalize text for phrase checks."""
    return " ".join(text.lower().split())


def assert_numeric_nonnegative(value: object, field_name: str) -> float:
    """Assert a metric is numeric, finite, and non-negative."""
    numeric_value = float(value)
    assert math.isfinite(numeric_value), f"{field_name} must be finite."
    assert numeric_value >= 0, f"{field_name} must be non-negative."
    return numeric_value


def validate_metadata(metadata: dict, audit_metadata: dict) -> None:
    """Validate AO2 H2 metadata content."""
    assert metadata.get("metadata_status") == "ao2_results_h2_documented"
    assert metadata.get("issue_id") == "#39"
    assert metadata.get("issue") == "#39"
    assert metadata.get("target_column") == "Order_Profit_Per_Order"
    assert metadata.get("h2_statement"), "Missing H2 statement."
    assert metadata.get("h2_decision"), "Missing H2 decision."
    assert metadata.get("final_test_used") is False
    assert metadata.get("evidence_slice") == "development_inner_validation"
    assert metadata.get("models_compared", {}).get("baseline_model") == "ao2_ridge_baseline"
    assert (
        metadata.get("models_compared", {}).get("primary_model")
        == "ao2_gradient_boosting_regressor"
    )

    audit_decision = metadata.get("target_reconstruction_audit", {}).get(
        "final_audit_decision"
    )
    assert audit_decision, "Missing target-reconstruction audit decision."
    assert audit_decision == audit_metadata.get("final_audit_decision")
    assert audit_metadata.get("final_test_used") is False

    if audit_decision == "blocked" or audit_metadata.get("metadata_status") != (
        "ao2_target_reconstruction_audit_completed"
    ):
        assert metadata.get("h2_decision") not in SUPPORTED_DECISIONS

    key_metrics = metadata.get("key_metrics", {})
    assert key_metrics.get("validation_row_count") == 28883
    for model_key in ("ridge_baseline", "gradient_boosting_regressor"):
        model_metrics = key_metrics.get(model_key, {})
        assert model_metrics, f"Missing key metrics for {model_key}."
        assert_numeric_nonnegative(model_metrics["rmse"], f"{model_key}.rmse")
        assert_numeric_nonnegative(model_metrics["mae"], f"{model_key}.mae")
        assert_numeric_nonnegative(
            model_metrics["median_absolute_error"],
            f"{model_key}.median_absolute_error",
        )


def validate_summary(summary_df: pd.DataFrame, metadata: dict) -> None:
    """Validate the compact AO2 H2 summary CSV."""
    missing_columns = sorted(REQUIRED_SUMMARY_COLUMNS.difference(summary_df.columns))
    assert not missing_columns, f"Summary CSV is missing columns: {missing_columns}"
    assert len(summary_df) == 1, "Summary CSV should contain exactly one row."

    row = summary_df.iloc[0]
    assert "order-profitability estimation" in str(row["hypothesis"]).lower()
    assert row["evidence_slice"] == metadata["evidence_slice"]
    assert str(row["final_test_used"]).lower() in {"false", "0"}
    assert row["target_policy_status"] == metadata["target_policy_status"]

    baseline_rmse = assert_numeric_nonnegative(row["baseline_rmse"], "baseline_rmse")
    primary_rmse = assert_numeric_nonnegative(row["primary_rmse"], "primary_rmse")
    baseline_mae = assert_numeric_nonnegative(row["baseline_mae"], "baseline_mae")
    primary_mae = assert_numeric_nonnegative(row["primary_mae"], "primary_mae")
    assert_numeric_nonnegative(row["rmse_improvement"], "rmse_improvement")
    assert_numeric_nonnegative(row["mae_improvement"], "mae_improvement")

    if row["h2_decision"] in SUPPORTED_DECISIONS:
        assert primary_rmse <= baseline_rmse, (
            "Supported H2 decision requires Gradient Boosting RMSE <= Ridge RMSE."
        )
        assert primary_mae <= baseline_mae, (
            "Supported H2 decision requires Gradient Boosting MAE <= Ridge MAE."
        )


def validate_source_metrics(summary_df: pd.DataFrame) -> None:
    """Validate required Ridge and Gradient Boosting metrics are present."""
    metrics_df = read_nonempty_csv(EVALUATION_METRICS_PATH)
    required_models = {"ao2_ridge_baseline", "ao2_gradient_boosting_regressor"}
    assert required_models.issubset(set(metrics_df["model_name"])), (
        "AO2 evaluation metrics must include Ridge and Gradient Boosting rows."
    )

    ridge_row = metrics_df.loc[metrics_df["model_name"] == "ao2_ridge_baseline"].iloc[0]
    gb_row = metrics_df.loc[
        metrics_df["model_name"] == "ao2_gradient_boosting_regressor"
    ].iloc[0]
    assert float(ridge_row["validation_rows"]) == 28883
    assert float(gb_row["validation_rows"]) == 28883
    assert str(ridge_row["final_test_used"]).lower() in {"false", "0"}
    assert str(gb_row["final_test_used"]).lower() in {"false", "0"}

    summary_row = summary_df.iloc[0]
    assert round(float(summary_row["baseline_rmse"]), 4) == round(float(ridge_row["rmse"]), 4)
    assert round(float(summary_row["primary_rmse"]), 4) == round(float(gb_row["rmse"]), 4)
    assert round(float(summary_row["baseline_mae"]), 4) == round(float(ridge_row["mae"]), 4)
    assert round(float(summary_row["primary_mae"]), 4) == round(float(gb_row["mae"]), 4)


def validate_text_artifacts() -> None:
    """Validate findings and documentation language coverage."""
    assert FINDINGS_PATH.exists(), f"Missing findings markdown: {FINDINGS_PATH}"
    assert DOC_PATH.exists(), f"Missing documentation file: {DOC_PATH}"

    combined_text = normalize_text(
        FINDINGS_PATH.read_text(encoding="utf-8")
        + "\n"
        + DOC_PATH.read_text(encoding="utf-8")
    )

    missing_concepts = []
    for concept, phrase_options in REQUIRED_TEXT_CONCEPTS.items():
        if not any(phrase in combined_text for phrase in phrase_options):
            missing_concepts.append(concept)
    assert not missing_concepts, (
        "AO2 results H2 documentation is missing concepts: "
        f"{missing_concepts}"
    )

    forbidden_overclaims = {
        "confirmed on final test",
        "final test confirms",
        "has causal impact",
        "causal impact of",
        "causal effect of",
        "profit is fully known",
        "profitability is fully known",
        "perfectly predicts",
    }
    overclaims_found = sorted(
        phrase for phrase in forbidden_overclaims if phrase in combined_text
    )
    assert not overclaims_found, f"Documentation contains overclaims: {overclaims_found}"


def main() -> None:
    """Run AO2 results and H2 validations."""
    metadata = read_json(METADATA_PATH)
    audit_metadata = read_json(TARGET_AUDIT_METADATA_PATH)
    summary_df = read_nonempty_csv(SUMMARY_PATH)

    validate_metadata(metadata, audit_metadata)
    validate_summary(summary_df, metadata)
    validate_source_metrics(summary_df)
    validate_text_artifacts()

    print("AO2 results and H2 validation checks passed.")


if __name__ == "__main__":
    main()
