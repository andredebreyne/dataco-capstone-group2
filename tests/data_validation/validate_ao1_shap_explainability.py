"""Validate AO1 SHAP explainability artifacts."""

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
        if (candidate / "src").exists() and (candidate / "report").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()

METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_SHAP_METADATA_PATH",
        str(
            REPO_ROOT
            / "models/ao1_late_delivery/explainability/ao1_shap_explainability_metadata.json"
        ),
    )
)
SHAP_IMPORTANCE_PATH = Path(
    os.getenv(
        "DATACO_AO1_SHAP_IMPORTANCE_PATH",
        str(REPO_ROOT / "report/tables/ao1_shap_feature_importance.csv"),
    )
)
DRIVER_SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO1_SHAP_DRIVER_SUMMARY_PATH",
        str(REPO_ROOT / "report/tables/ao1_shap_driver_summary.csv"),
    )
)
FIGURE_PATH = Path(
    os.getenv(
        "DATACO_AO1_SHAP_TOP_FEATURES_FIGURE_PATH",
        str(REPO_ROOT / "report/figures/ao1_shap_top_features.png"),
    )
)
FINDINGS_PATH = Path(
    os.getenv(
        "DATACO_AO1_SHAP_FINDINGS_PATH",
        str(REPO_ROOT / "report/tables/ao1_shap_explainability_findings.md"),
    )
)

REQUIRED_IMPORTANCE_COLUMNS = {
    "rank",
    "feature_name",
    "mean_abs_shap",
    "mean_signed_shap",
    "importance_share",
}

REQUIRED_DRIVER_COLUMNS = {
    "rank",
    "feature_name",
    "mean_abs_shap",
    "importance_share",
    "mean_signed_shap",
    "driver_direction_note",
}

REQUIRED_METADATA_FIELDS = {
    "final_test_used",
    "feature_count",
    "input_partition_path",
    "input_slice",
    "limitations",
    "model_source",
    "output_artifacts",
    "random_state",
    "sample_size",
    "selected_candidate_name",
    "shap_method",
    "shap_version",
    "top_driver_count",
    "xgboost_metadata_path",
    "xgboost_version",
}

VALID_MODEL_SOURCES = {"saved_model", "deterministic_reconstruction"}
PINNED_XGBOOST_VERSION = "2.0.3"

FORBIDDEN_FEATURE_TOKENS = {
    "actual",
    "benefit_per_order",
    "days_for_shipping_real",
    "delivery_status",
    "final_test",
    "holdout",
    "late_delivery_risk",
    "order_item_total",
    "order_profit",
    "profit_ratio",
    "sales",
    "shipping_date",
    "test_partition",
}


def read_required_csv(path: Path) -> pd.DataFrame:
    """Read a required non-empty CSV."""
    assert path.exists(), f"Missing required artifact: {path}"
    frame = pd.read_csv(path)
    assert not frame.empty, f"Artifact is empty: {path}"
    return frame


def assert_columns(frame: pd.DataFrame, required_columns: set[str], name: str) -> None:
    """Assert that a DataFrame contains required columns."""
    missing_columns = sorted(required_columns.difference(frame.columns))
    assert not missing_columns, f"{name} is missing columns: {missing_columns}"


def assert_numeric_non_negative(frame: pd.DataFrame, column_name: str) -> None:
    """Assert numeric values are finite and non-negative."""
    values = pd.to_numeric(frame[column_name], errors="coerce")
    assert values.notna().all(), f"{column_name} has non-numeric values."
    assert values.map(math.isfinite).all(), f"{column_name} has non-finite values."
    assert (values >= 0).all(), f"{column_name} has negative values."


def normalize_feature_name(feature_name: str) -> str:
    """Normalize feature names for leakage-token matching."""
    normalized = feature_name.strip().lower()
    for character in (" ", "-", "/", "(", ")", "[", "]", "{", "}", "."):
        normalized = normalized.replace(character, "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def assert_no_forbidden_feature_tokens(frame: pd.DataFrame) -> None:
    """Assert SHAP features do not include obvious AO1 leakage fields."""
    normalized_features = frame["feature_name"].astype(str).map(normalize_feature_name)
    matched = sorted(
        token
        for token in FORBIDDEN_FEATURE_TOKENS
        if normalized_features.str.contains(token, regex=False).any()
    )
    assert not matched, f"SHAP output contains forbidden leakage-like tokens: {matched}"


def validate_metadata() -> dict:
    """Validate AO1 SHAP metadata."""
    assert METADATA_PATH.exists(), f"Missing metadata artifact: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    missing_metadata = sorted(REQUIRED_METADATA_FIELDS.difference(metadata))
    assert not missing_metadata, f"SHAP metadata is missing fields: {missing_metadata}"
    assert metadata["metadata_status"] == "ao1_shap_explainability_completed"
    assert metadata["issue"] == "#30"
    assert metadata["selected_model"] == "ao1_xgboost_classifier"
    assert metadata["selected_candidate_id"], "Selected candidate is missing."
    assert metadata["selected_candidate_name"], "Selected candidate name is missing."
    assert metadata["final_test_used"] is False
    assert metadata["input_partition_path"], "Input partition path is missing."
    assert metadata["input_slice"], "Input slice is missing."
    assert metadata["training_slice"], "Training slice is missing."
    assert metadata["validation_slice"], "Validation slice is missing."
    assert metadata["shap_method"], "SHAP method is missing."
    assert metadata["model_source"] in VALID_MODEL_SOURCES
    assert metadata["xgboost_metadata_path"], "XGBoost metadata path is missing."
    assert metadata["xgboost_version"] == PINNED_XGBOOST_VERSION
    assert metadata["sample_size"] > 0
    assert metadata["sample_row_count"] > 0
    assert metadata["random_state"] == 620
    assert metadata["feature_count"] > 0
    assert metadata["top_driver_count"] > 0
    assert metadata["top_n_features"] > 0
    assert metadata["target_column"] == "Late_delivery_risk"
    assert isinstance(metadata["output_artifacts"], dict)
    assert metadata["limitations"], "Limitations are missing."
    return metadata


def main() -> None:
    """Run AO1 SHAP artifact validation checks."""
    metadata = validate_metadata()
    importance_df = read_required_csv(SHAP_IMPORTANCE_PATH)
    driver_df = read_required_csv(DRIVER_SUMMARY_PATH)

    assert FINDINGS_PATH.exists(), f"Missing findings document: {FINDINGS_PATH}"
    assert FIGURE_PATH.exists(), f"Missing SHAP figure: {FIGURE_PATH}"
    assert FIGURE_PATH.stat().st_size > 0, f"SHAP figure is empty: {FIGURE_PATH}"

    assert_columns(importance_df, REQUIRED_IMPORTANCE_COLUMNS, "SHAP importance")
    assert_columns(driver_df, REQUIRED_DRIVER_COLUMNS, "driver summary")
    assert_numeric_non_negative(importance_df, "mean_abs_shap")
    assert_numeric_non_negative(driver_df, "mean_abs_shap")
    assert_no_forbidden_feature_tokens(importance_df)
    assert_no_forbidden_feature_tokens(driver_df)

    assert len(driver_df) <= metadata["top_n_features"]
    assert len(driver_df) == metadata["top_driver_count"]
    assert len(importance_df) == metadata["feature_count"]
    assert set(driver_df["feature_name"]).issubset(set(importance_df["feature_name"]))

    findings_text = FINDINGS_PATH.read_text(encoding="utf-8").lower()
    assert "final test partition is not used" in findings_text
    assert "not causal" in findings_text
    assert "business plausibility" in findings_text
    assert "top-driver interpretation" in findings_text
    assert "late_delivery_risk = 1" in findings_text

    print("All AO1 SHAP explainability validation checks passed.")


if __name__ == "__main__":
    main()
