"""Validate AO1 model evaluation pack artifacts.

Run this script after `src/modeling/evaluate_ao1_models.py` has completed. It
validates that the evaluation outputs contain the metrics, threshold trade-offs,
curve points, and metadata needed for threshold selection.
"""

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
        "DATACO_AO1_EVALUATION_METADATA_PATH",
        str(REPO_ROOT / "models/ao1_late_delivery/evaluation/ao1_evaluation_metadata.json"),
    )
)
METRICS_PATH = Path(
    os.getenv(
        "DATACO_AO1_EVALUATION_METRICS_PATH",
        str(REPO_ROOT / "report/tables/ao1_model_validation_comparison.csv"),
    )
)
THRESHOLD_PATH = Path(
    os.getenv(
        "DATACO_AO1_THRESHOLD_TRADEOFF_PATH",
        str(REPO_ROOT / "report/tables/ao1_threshold_tradeoff_grid.csv"),
    )
)
CONFUSION_PATH = Path(
    os.getenv(
        "DATACO_AO1_CONFUSION_MATRIX_PATH",
        str(REPO_ROOT / "report/tables/ao1_confusion_matrix_by_threshold.csv"),
    )
)
ROC_PATH = Path(
    os.getenv(
        "DATACO_AO1_ROC_CURVE_PATH",
        str(REPO_ROOT / "report/tables/ao1_roc_curve_points.csv"),
    )
)
PR_PATH = Path(
    os.getenv(
        "DATACO_AO1_PR_CURVE_PATH",
        str(REPO_ROOT / "report/tables/ao1_precision_recall_curve_points.csv"),
    )
)
CALIBRATION_PATH = Path(
    os.getenv(
        "DATACO_AO1_CALIBRATION_PATH",
        str(REPO_ROOT / "report/tables/ao1_calibration_by_probability_bin.csv"),
    )
)
FINDINGS_PATH = Path(
    os.getenv(
        "DATACO_AO1_EVALUATION_FINDINGS_PATH",
        str(REPO_ROOT / "report/tables/ao1_model_evaluation_findings.md"),
    )
)

REQUIRED_METRIC_COLUMNS = {
    "model_name",
    "threshold",
    "row_count",
    "positive_class_rate",
    "predicted_positive_rate",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "true_negative",
    "false_positive",
    "false_negative",
    "true_positive",
    "roc_auc",
    "pr_auc",
    "log_loss",
}

REQUIRED_THRESHOLD_COLUMNS = {
    "model_name",
    "threshold",
    "row_count",
    "precision",
    "recall",
    "f1",
    "false_negative",
    "false_positive",
}

UNIT_INTERVAL_COLUMNS = {
    "threshold",
    "positive_class_rate",
    "predicted_positive_rate",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "pr_auc",
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


def assert_unit_interval_values(frame: pd.DataFrame, columns: set[str]) -> None:
    """Assert selected numeric columns are finite and within [0, 1]."""
    for column_name in columns.intersection(frame.columns):
        values = frame[column_name].dropna()
        assert values.map(math.isfinite).all(), f"{column_name} has non-finite values."
        assert values.between(0.0, 1.0).all(), f"{column_name} has values outside [0, 1]."


def assert_non_negative_integer_columns(frame: pd.DataFrame, columns: set[str]) -> None:
    """Assert selected columns contain non-negative count-like values."""
    for column_name in columns:
        values = frame[column_name]
        assert (values >= 0).all(), f"{column_name} has negative values."
        assert (values.round() == values).all(), f"{column_name} has non-integer values."


def validate_metadata() -> dict:
    """Validate metadata artifact."""
    assert METADATA_PATH.exists(), f"Missing metadata artifact: {METADATA_PATH}"
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["metadata_status"] == "ao1_validation_evaluation_completed"
    assert metadata["evaluation_status"] in {
        "complete_validation_model_comparison",
        "partial_validation_model_comparison",
    }
    assert metadata["issue"] == "#29"
    assert metadata["final_test_used"] is False
    assert metadata["target_column"] == "Late_delivery_risk"
    assert metadata["probability_column"] == "predicted_probability"
    assert metadata["evaluation_slice"] == "development_inner_validation"
    assert metadata["split_partition"] == "development"
    assert set(metadata["expected_models"]) == {
        "ao1_logistic_regression_baseline",
        "ao1_xgboost_classifier",
    }
    assert metadata["evaluated_models"], "No evaluated models are recorded."
    assert metadata["threshold_grid"], "Threshold grid is empty."

    evaluated_models = set(metadata["evaluated_models"])
    missing_models = set(metadata["missing_models"])
    expected_models = set(metadata["expected_models"])
    assert evaluated_models.union(missing_models) == expected_models
    assert not evaluated_models.intersection(missing_models)

    if missing_models:
        assert metadata["evaluation_status"] == "partial_validation_model_comparison"
    else:
        assert metadata["evaluation_status"] == "complete_validation_model_comparison"

    return metadata


def main() -> None:
    """Run AO1 evaluation pack validation checks."""
    metadata = validate_metadata()
    metrics_df = read_required_csv(METRICS_PATH)
    threshold_df = read_required_csv(THRESHOLD_PATH)
    confusion_df = read_required_csv(CONFUSION_PATH)
    roc_df = read_required_csv(ROC_PATH)
    pr_df = read_required_csv(PR_PATH)
    calibration_df = read_required_csv(CALIBRATION_PATH)

    assert FINDINGS_PATH.exists(), f"Missing findings artifact: {FINDINGS_PATH}"
    assert_columns(metrics_df, REQUIRED_METRIC_COLUMNS, "metrics comparison")
    assert_columns(threshold_df, REQUIRED_THRESHOLD_COLUMNS, "threshold grid")
    assert_unit_interval_values(metrics_df, UNIT_INTERVAL_COLUMNS)
    assert_unit_interval_values(threshold_df, UNIT_INTERVAL_COLUMNS)

    count_columns = {
        "row_count",
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
    }
    assert_non_negative_integer_columns(metrics_df, count_columns)
    assert_non_negative_integer_columns(confusion_df, count_columns)

    model_names = set(metrics_df["model_name"])
    assert model_names == set(metadata["evaluated_models"]), (
        "Metadata evaluated_models do not match metrics output."
    )
    assert set(threshold_df["model_name"]) == model_names
    assert set(confusion_df["model_name"]) == model_names
    assert set(roc_df["model_name"]) == model_names
    assert set(pr_df["model_name"]) == model_names
    assert set(calibration_df["model_name"]) == model_names

    findings_text = FINDINGS_PATH.read_text(encoding="utf-8")
    assert metadata["evaluation_status"] in findings_text
    if metadata["missing_models"]:
        assert "This run is partial" in findings_text
    else:
        assert "This run includes all expected AO1 candidate models." in findings_text

    print("All AO1 evaluation pack validation checks passed.")


if __name__ == "__main__":
    main()
