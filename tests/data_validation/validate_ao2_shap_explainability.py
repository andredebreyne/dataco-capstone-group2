"""Validate AO2 SHAP explainability artifacts."""

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
        if (candidate / "src").exists() and (candidate / "report").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()

METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_SHAP_METADATA_PATH",
        str(
            REPO_ROOT
            / "models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json"
        ),
    )
)
SHAP_IMPORTANCE_PATH = Path(
    os.getenv(
        "DATACO_AO2_SHAP_IMPORTANCE_PATH",
        str(REPO_ROOT / "report/tables/ao2_shap_feature_importance.csv"),
    )
)
DRIVER_SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO2_SHAP_DRIVER_SUMMARY_PATH",
        str(REPO_ROOT / "report/tables/ao2_shap_driver_summary.csv"),
    )
)
FINDINGS_PATH = Path(
    os.getenv(
        "DATACO_AO2_SHAP_FINDINGS_PATH",
        str(REPO_ROOT / "report/tables/ao2_shap_explainability_findings.md"),
    )
)

REQUIRED_IMPORTANCE_COLUMNS = {
    "feature_name",
    "final_test_used",
    "input_slice",
    "mean_abs_shap_value",
    "model_name",
    "rank",
    "sample_size",
}

REQUIRED_DRIVER_COLUMNS = {
    "business_plausibility_note",
    "driver_category",
    "feature_name",
    "final_test_used",
    "input_slice",
    "interpretation_note",
    "mean_abs_shap_value",
    "rank",
    "target_policy_status",
}

REQUIRED_METADATA_FIELDS = {
    "evaluation_dependency_status",
    "feature_count",
    "final_test_used",
    "forbidden_feature_check_status",
    "input_partition_path",
    "input_slice",
    "issue",
    "limitations",
    "metadata_status",
    "model_output_space",
    "model_source",
    "output_artifact_paths",
    "preprocessing_reference",
    "random_state",
    "sample_size",
    "selected_candidate_name",
    "selected_model_metadata_path",
    "selected_model_name",
    "shap_method",
    "shap_version",
    "target_column",
    "target_policy_check_status",
    "top_driver_count",
    "xgboost_version",
}

VALID_MODEL_SOURCES = {"saved_model", "deterministic_reconstruction"}
FORBIDDEN_FEATURE_TOKENS = {
    "actual_delivery",
    "actual_profit",
    "ao3_order_value",
    "benefit_per_order",
    "chronological_row_number",
    "days_for_shipping_real",
    "delivery_status",
    "final_test",
    "gold_ao2_processed_timestamp",
    "held_out",
    "holdout",
    "late_delivery_risk",
    "order_date_dateorders",
    "order_id",
    "order_item_discount",
    "order_item_id",
    "order_item_profit_ratio",
    "order_item_total",
    "order_profit_per_order",
    "order_status",
    "partition",
    "product_price",
    "profit_margin",
    "profit_outcome",
    "profit_ratio",
    "realized_margin",
    "realized_profit",
    "sales",
    "sales_per_customer",
    "shipping_date",
    "split_partition",
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
    """Normalize feature names for target-policy token matching."""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(feature_name).strip().lower())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def assert_no_forbidden_feature_tokens(frame: pd.DataFrame) -> None:
    """Assert SHAP features do not include AO2 target/proxy/leakage fields."""
    normalized_features = frame["feature_name"].astype(str).map(normalize_feature_name)
    matched = sorted(
        token
        for token in FORBIDDEN_FEATURE_TOKENS
        if normalized_features.str.contains(token, regex=False).any()
    )
    assert not matched, f"SHAP output contains forbidden AO2 target-policy tokens: {matched}"


def assert_ranks_are_valid(frame: pd.DataFrame) -> None:
    """Assert rank values are positive integers and unique."""
    ranks = pd.to_numeric(frame["rank"], errors="coerce")
    assert ranks.notna().all(), "Ranks contain non-numeric values."
    assert (ranks > 0).all(), "Ranks must be positive."
    assert ((ranks % 1) == 0).all(), "Ranks must be integers."
    assert ranks.is_unique, "Ranks must be unique."


def validate_metadata() -> dict:
    """Validate AO2 SHAP metadata."""
    assert METADATA_PATH.exists(), f"Missing metadata artifact: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    missing_metadata = sorted(REQUIRED_METADATA_FIELDS.difference(metadata))
    assert not missing_metadata, f"AO2 SHAP metadata is missing fields: {missing_metadata}"

    assert metadata["metadata_status"] == "ao2_shap_explainability_completed"
    assert metadata["issue"] == "#38"
    assert metadata["selected_model_name"] == "ao2_gradient_boosting_regressor"
    assert metadata["selected_candidate_name"], "Selected candidate is missing."
    assert metadata["model_source"] in VALID_MODEL_SOURCES
    assert metadata["final_test_used"] is False
    assert str(metadata["input_slice"]).lower() not in {
        "test",
        "final_test",
        "holdout",
        "held_out",
    }
    assert metadata["target_column"] == "Order_Profit_Per_Order"
    assert metadata["shap_method"], "SHAP method is missing."
    assert metadata["model_output_space"], "Model output space is missing."
    assert metadata["xgboost_version"], "XGBoost version is missing."
    assert metadata["shap_version"], "SHAP version is missing."
    assert metadata["sample_size"] > 0
    assert metadata["feature_count"] > 0
    assert metadata["top_driver_count"] > 0
    assert metadata["forbidden_feature_check_status"] == "passed"
    assert metadata["target_policy_check_status"] == "passed"
    assert isinstance(metadata["output_artifact_paths"], dict)
    assert metadata["evaluation_dependency_status"]["final_test_used"] is False
    assert metadata["limitations"], "Limitations are missing."
    return metadata


def validate_artifact_paths(metadata: dict) -> None:
    """Validate documented artifact paths exist."""
    paths = metadata["output_artifact_paths"]
    artifact_fallbacks = {
        "shap_feature_importance_csv": SHAP_IMPORTANCE_PATH,
        "shap_driver_summary_csv": DRIVER_SUMMARY_PATH,
        "shap_findings_markdown": FINDINGS_PATH,
    }
    for key, fallback_path in artifact_fallbacks.items():
        documented_path = Path(paths[key])
        assert documented_path.exists() or fallback_path.exists(), (
            f"Missing documented artifact `{key}`. Checked {documented_path} "
            f"and fallback {fallback_path}."
        )
    if paths.get("shap_top_features_figure"):
        figure_path = Path(paths["shap_top_features_figure"])
        fallback_figure_path = REPO_ROOT / "report/figures/modeling/ao2_shap_top_features.png"
        existing_figure_path = figure_path if figure_path.exists() else fallback_figure_path
        assert existing_figure_path.exists(), (
            f"Missing documented SHAP figure. Checked {figure_path} and "
            f"fallback {fallback_figure_path}."
        )
        assert existing_figure_path.stat().st_size > 0, (
            f"SHAP figure is empty: {existing_figure_path}"
        )


def validate_findings() -> None:
    """Validate report-facing AO2 SHAP findings coverage."""
    assert FINDINGS_PATH.exists(), f"Missing findings document: {FINDINGS_PATH}"
    findings_text = FINDINGS_PATH.read_text(encoding="utf-8").lower()
    required_phrases = [
        "business plausibility",
        "target-policy review",
        "final test partition",
        "not used",
        "not causal",
        "top drivers",
        "model explanations",
    ]
    missing_phrases = [phrase for phrase in required_phrases if phrase not in findings_text]
    assert not missing_phrases, f"Findings are missing required language: {missing_phrases}"


def main() -> None:
    """Run AO2 SHAP artifact validation checks."""
    metadata = validate_metadata()
    importance_df = read_required_csv(SHAP_IMPORTANCE_PATH)
    driver_df = read_required_csv(DRIVER_SUMMARY_PATH)

    validate_artifact_paths(metadata)
    validate_findings()

    assert_columns(importance_df, REQUIRED_IMPORTANCE_COLUMNS, "SHAP importance")
    assert_columns(driver_df, REQUIRED_DRIVER_COLUMNS, "driver summary")
    assert_numeric_non_negative(importance_df, "mean_abs_shap_value")
    assert_numeric_non_negative(driver_df, "mean_abs_shap_value")
    assert_ranks_are_valid(importance_df)
    assert_ranks_are_valid(driver_df)
    assert_no_forbidden_feature_tokens(importance_df)
    assert_no_forbidden_feature_tokens(driver_df)

    assert len(importance_df) == metadata["feature_count"]
    assert len(driver_df) == metadata["top_driver_count"]
    assert set(driver_df["feature_name"]).issubset(set(importance_df["feature_name"]))
    assert not importance_df["feature_name"].astype(str).map(normalize_feature_name).str.contains(
        "ao3_order_value",
        regex=False,
    ).any()
    assert not driver_df["feature_name"].astype(str).map(normalize_feature_name).str.contains(
        "ao3_order_value",
        regex=False,
    ).any()
    assert (importance_df["final_test_used"] == False).all()  # noqa: E712
    assert (driver_df["final_test_used"] == False).all()  # noqa: E712
    assert not importance_df["input_slice"].astype(str).str.lower().isin(
        ["test", "final_test", "holdout", "held_out"]
    ).any()

    print("All AO2 SHAP explainability validation checks passed.")


if __name__ == "__main__":
    main()
