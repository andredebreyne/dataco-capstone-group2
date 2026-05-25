"""Validate AO2 model evaluation pack artifacts.

Run this script after `src/modeling/evaluate_ao2_models.py` has completed. It
checks the validation-only metrics, residual diagnostics, error slices,
findings note, and metadata needed to summarize AO2 H2 evidence without using
the final test partition.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pandas as pd


EXPECTED_MODELS = {
    "ao2_ridge_baseline",
    "ao2_gradient_boosting_regressor",
}
FINAL_TEST_LABELS = {
    "test",
    "final_test",
    "holdout",
    "hold_out",
    "heldout",
    "held_out",
}

REQUIRED_METRIC_COLUMNS = {
    "model_name",
    "candidate_name",
    "validation_rows",
    "rmse",
    "mae",
    "r2",
    "median_absolute_error",
    "mean_error",
    "target_mean",
    "target_std",
    "prediction_mean",
    "prediction_std",
    "wrong_profit_sign_share",
    "final_test_used",
}

REQUIRED_RESIDUAL_COLUMNS = {
    "model_name",
    "candidate_name",
    "validation_rows",
    "residual_mean",
    "residual_standard_deviation",
    "residual_median",
    "residual_min",
    "residual_max",
    "residual_p10",
    "residual_p25",
    "residual_p50",
    "residual_p75",
    "residual_p90",
    "absolute_error_p50",
    "absolute_error_p75",
    "absolute_error_p90",
    "wrong_profit_sign_share",
}

REQUIRED_ERROR_SLICE_COLUMNS = {
    "slice_type",
    "slice_value",
    "model_name",
    "candidate_name",
    "row_count",
    "rmse",
    "mae",
    "mean_error",
    "median_absolute_error",
    "wrong_profit_sign_share",
    "is_unstable_small_slice",
}


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
        "DATACO_AO2_EVALUATION_METADATA_PATH",
        str(REPO_ROOT / "models/ao2_profitability/evaluation/ao2_evaluation_metadata.json"),
    )
)
METRICS_PATH = Path(
    os.getenv(
        "DATACO_AO2_EVALUATION_METRICS_PATH",
        str(REPO_ROOT / "report/tables/ao2_model_evaluation_metrics.csv"),
    )
)
RESIDUAL_DIAGNOSTICS_PATH = Path(
    os.getenv(
        "DATACO_AO2_EVALUATION_RESIDUAL_DIAGNOSTICS_PATH",
        str(REPO_ROOT / "report/tables/ao2_residual_diagnostics_by_model.csv"),
    )
)
ERROR_SLICES_PATH = Path(
    os.getenv(
        "DATACO_AO2_EVALUATION_ERROR_SLICES_PATH",
        str(REPO_ROOT / "report/tables/ao2_error_slices.csv"),
    )
)
FINDINGS_PATH = Path(
    os.getenv(
        "DATACO_AO2_EVALUATION_FINDINGS_PATH",
        str(REPO_ROOT / "report/tables/ao2_model_evaluation_findings.md"),
    )
)


def read_required_csv(path: Path) -> pd.DataFrame:
    """Read a required non-empty CSV artifact."""
    assert path.exists(), f"Missing required artifact: {path}"
    frame = pd.read_csv(path)
    assert not frame.empty, f"Artifact is empty: {path}"
    return frame


def assert_columns(frame: pd.DataFrame, required_columns: set[str], name: str) -> None:
    """Assert that a DataFrame contains required columns."""
    missing_columns = sorted(required_columns.difference(frame.columns))
    assert not missing_columns, f"{name} is missing columns: {missing_columns}"


def assert_numeric_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    """Assert selected columns contain finite numeric values."""
    for column_name in columns:
        values = pd.to_numeric(frame[column_name], errors="coerce")
        assert not values.isna().any(), f"{name}.{column_name} has non-numeric values."
        assert values.map(math.isfinite).all(), f"{name}.{column_name} has non-finite values."


def normalize_label(value: object) -> str:
    """Normalize slice labels for final-test boundary checks."""
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def assert_no_final_test_slices(frame: pd.DataFrame, name: str) -> None:
    """Assert no slice/split columns contain final-test or holdout labels."""
    slice_columns = [
        column_name
        for column_name in frame.columns
        if any(token in column_name.lower() for token in ("slice", "split", "partition"))
    ]
    for column_name in slice_columns:
        labels = set(frame[column_name].dropna().map(normalize_label))
        blocked_labels = sorted(labels.intersection(FINAL_TEST_LABELS))
        assert not blocked_labels, (
            f"{name}.{column_name} contains final-test/holdout labels: {blocked_labels}"
        )


def validate_metadata() -> dict:
    """Validate the AO2 evaluation metadata artifact."""
    assert METADATA_PATH.exists(), f"Missing metadata artifact: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["metadata_status"] == "ao2_validation_evaluation_completed"
    assert metadata["issue"] == "#37"
    assert metadata["final_test_used"] is False
    assert metadata["comparison_status"] in {"complete", "partial"}
    assert metadata["target_column"] == "Order_Profit_Per_Order"
    assert metadata["evaluation_slice"] == "development_inner_validation"
    assert "validation" in metadata["evaluation_slice"]
    assert normalize_label(metadata["evaluation_slice"]) not in FINAL_TEST_LABELS
    assert set(metadata["expected_models"]) == EXPECTED_MODELS
    assert metadata["metrics_generated"], "Metrics output path is not recorded."
    assert metadata["residual_diagnostics_generated"], (
        "Residual diagnostics output path is not recorded."
    )
    assert metadata["error_slices_generated"], "Error slices output path is not recorded."
    assert metadata["findings_generated"], "Findings output path is not recorded."
    assert metadata["target_policy_caveat"], "Target-policy caveat is missing."

    if metadata["comparison_status"] == "complete":
        assert set(metadata["evaluated_models"]) == EXPECTED_MODELS
        assert not metadata["missing_artifacts"], "Complete comparison has missing artifacts."

    return metadata


def validate_metrics(metrics_df: pd.DataFrame, metadata: dict) -> None:
    """Validate metrics table structure and ranges."""
    assert_columns(metrics_df, REQUIRED_METRIC_COLUMNS, "AO2 evaluation metrics")
    numeric_columns = REQUIRED_METRIC_COLUMNS.difference({"model_name", "candidate_name"})
    assert_numeric_columns(metrics_df, numeric_columns, "AO2 evaluation metrics")
    assert (metrics_df["validation_rows"] > 0).all(), "Validation row counts must be positive."
    assert (metrics_df["rmse"] >= 0).all(), "RMSE must be non-negative."
    assert (metrics_df["mae"] >= 0).all(), "MAE must be non-negative."
    assert metrics_df["final_test_used"].isin([False, "False", "false"]).all(), (
        "Metrics must mark final_test_used as false."
    )
    assert_no_final_test_slices(metrics_df, "AO2 evaluation metrics")

    if metadata["comparison_status"] == "complete":
        assert EXPECTED_MODELS.issubset(set(metrics_df["model_name"])), (
            "Complete comparison must include Ridge and Gradient Boosting rows."
        )


def validate_residual_diagnostics(residual_df: pd.DataFrame, metadata: dict) -> None:
    """Validate residual diagnostics table structure and ranges."""
    assert_columns(residual_df, REQUIRED_RESIDUAL_COLUMNS, "AO2 residual diagnostics")
    numeric_columns = REQUIRED_RESIDUAL_COLUMNS.difference({"model_name", "candidate_name"})
    assert_numeric_columns(residual_df, numeric_columns, "AO2 residual diagnostics")
    assert (residual_df["validation_rows"] > 0).all(), (
        "Residual diagnostics row counts must be positive."
    )
    assert (residual_df["absolute_error_p50"] >= 0).all()
    assert (residual_df["absolute_error_p75"] >= 0).all()
    assert (residual_df["absolute_error_p90"] >= 0).all()
    assert residual_df["wrong_profit_sign_share"].between(0.0, 1.0).all()
    assert_no_final_test_slices(residual_df, "AO2 residual diagnostics")

    if metadata["comparison_status"] == "complete":
        assert EXPECTED_MODELS.issubset(set(residual_df["model_name"])), (
            "Complete comparison must include both models in residual diagnostics."
        )


def validate_error_slices(error_slices_df: pd.DataFrame, metadata: dict) -> None:
    """Validate compact error-slice diagnostics."""
    assert_columns(error_slices_df, REQUIRED_ERROR_SLICE_COLUMNS, "AO2 error slices")
    numeric_columns = REQUIRED_ERROR_SLICE_COLUMNS.difference(
        {"slice_type", "slice_value", "model_name", "candidate_name", "is_unstable_small_slice"}
    )
    assert_numeric_columns(error_slices_df, numeric_columns, "AO2 error slices")
    assert (error_slices_df["row_count"] > 0).all(), "Error-slice row counts must be positive."
    assert (error_slices_df["rmse"] >= 0).all(), "Error-slice RMSE must be non-negative."
    assert (error_slices_df["mae"] >= 0).all(), "Error-slice MAE must be non-negative."
    assert error_slices_df["wrong_profit_sign_share"].between(0.0, 1.0).all()
    assert {"actual_profit_band", "actual_profit_quantile", "absolute_error_band"}.issubset(
        set(error_slices_df["slice_type"])
    )
    assert_no_final_test_slices(error_slices_df, "AO2 error slices")

    if metadata["comparison_status"] == "complete":
        assert EXPECTED_MODELS.issubset(set(error_slices_df["model_name"])), (
            "Complete comparison must include both models in error slices."
        )


def validate_findings_text() -> None:
    """Validate that the findings note covers required evaluation topics."""
    assert FINDINGS_PATH.exists(), f"Missing findings artifact: {FINDINGS_PATH}"
    findings_text = FINDINGS_PATH.read_text(encoding="utf-8").lower()
    required_phrases = {
        "rmse",
        "mae",
        "residual review",
        "error slices",
        "h2 evidence",
        "final test not used",
        "target-policy caveat",
    }
    for phrase in required_phrases:
        assert phrase in findings_text, f"Findings note must mention `{phrase}`."
    assert "r-squared" in findings_text, "Findings note must mention R-squared."


def main() -> None:
    """Run all AO2 evaluation pack validation checks."""
    metadata = validate_metadata()
    metrics_df = read_required_csv(METRICS_PATH)
    residual_df = read_required_csv(RESIDUAL_DIAGNOSTICS_PATH)
    error_slices_df = read_required_csv(ERROR_SLICES_PATH)

    validate_metrics(metrics_df, metadata)
    validate_residual_diagnostics(residual_df, metadata)
    validate_error_slices(error_slices_df, metadata)
    validate_findings_text()

    print("AO2 evaluation pack validation passed.")


if __name__ == "__main__":
    main()
