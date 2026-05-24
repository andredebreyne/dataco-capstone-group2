"""Build the AO1 model evaluation pack from validation prediction records.

This script compares AO1 candidate models on the validation slice only. It
expects each candidate model to publish row-level validation probabilities using
the contract documented for issue #29. The final test partition is not read,
scored, or evaluated here.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TARGET_COLUMN = "Late_delivery_risk"
PROBABILITY_COLUMN = "predicted_probability"
MODEL_COLUMN = "model_name"
DEFAULT_THRESHOLD = 0.50
THRESHOLD_GRID = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
FINAL_TEST_LABELS = {
    "test",
    "final_test",
    "holdout",
    "hold_out",
    "holdout_test",
    "hold_out_test",
    "heldout",
    "held_out",
    "heldout_test",
    "held_out_test",
    "final_holdout",
    "final_hold_out",
}

REQUIRED_PREDICTION_COLUMNS = {
    MODEL_COLUMN,
    TARGET_COLUMN,
    PROBABILITY_COLUMN,
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
        if (candidate / "src").exists() and (candidate / "report").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()


@dataclass(frozen=True)
class AO1EvaluationConfig:
    """Configuration for AO1 validation evaluation outputs."""

    logistic_predictions_path: Path = Path(
        os.getenv(
            "DATACO_AO1_LOGISTIC_VALIDATION_PREDICTIONS_PATH",
            str(REPO_ROOT / "report/tables/ao1_logistic_regression_validation_predictions.csv"),
        )
    )
    xgboost_predictions_path: Path = Path(
        os.getenv(
            "DATACO_AO1_XGBOOST_VALIDATION_PREDICTIONS_PATH",
            str(REPO_ROOT / "report/tables/ao1_xgboost_validation_predictions.csv"),
        )
    )
    metrics_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_EVALUATION_METRICS_PATH",
            str(REPO_ROOT / "report/tables/ao1_model_validation_comparison.csv"),
        )
    )
    threshold_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_THRESHOLD_TRADEOFF_PATH",
            str(REPO_ROOT / "report/tables/ao1_threshold_tradeoff_grid.csv"),
        )
    )
    confusion_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_CONFUSION_MATRIX_PATH",
            str(REPO_ROOT / "report/tables/ao1_confusion_matrix_by_threshold.csv"),
        )
    )
    roc_curve_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_ROC_CURVE_PATH",
            str(REPO_ROOT / "report/tables/ao1_roc_curve_points.csv"),
        )
    )
    precision_recall_curve_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_PR_CURVE_PATH",
            str(REPO_ROOT / "report/tables/ao1_precision_recall_curve_points.csv"),
        )
    )
    calibration_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_CALIBRATION_PATH",
            str(REPO_ROOT / "report/tables/ao1_calibration_by_probability_bin.csv"),
        )
    )
    findings_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_EVALUATION_FINDINGS_PATH",
            str(REPO_ROOT / "report/tables/ao1_model_evaluation_findings.md"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_EVALUATION_METADATA_PATH",
            str(REPO_ROOT / "models/ao1_late_delivery/evaluation/ao1_evaluation_metadata.json"),
        )
    )


def configure_logging() -> logging.Logger:
    """Configure console logging for local or Databricks execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_model_evaluation")


def read_prediction_artifacts(config: AO1EvaluationConfig) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read all available AO1 validation prediction artifacts."""
    candidates = {
        "logistic_regression": config.logistic_predictions_path,
        "xgboost": config.xgboost_predictions_path,
    }
    frames: list[pd.DataFrame] = []
    available_artifacts: dict[str, str] = {}
    missing_artifacts: dict[str, str] = {}

    for model_key, path in candidates.items():
        if not path.exists():
            missing_artifacts[model_key] = str(path)
            continue
        frame = pd.read_csv(path)
        validate_prediction_contract(frame, path)
        frames.append(frame)
        available_artifacts[model_key] = str(path)

    if not frames:
        raise FileNotFoundError(
            "No AO1 validation prediction artifacts were found. Expected at least "
            f"one of: {list(missing_artifacts.values())}"
        )

    artifact_status = {
        "expected_model_artifacts": {
            model_key: str(path)
            for model_key, path in candidates.items()
        },
        "available_model_artifacts": available_artifacts,
        "missing_model_artifacts": missing_artifacts,
        "comparison_status": "complete" if not missing_artifacts else "partial",
    }
    return pd.concat(frames, ignore_index=True), artifact_status


def validate_prediction_contract(frame: pd.DataFrame, path: Path) -> None:
    """Validate the row-level prediction artifact contract."""
    missing_columns = sorted(REQUIRED_PREDICTION_COLUMNS.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"{path} is missing required columns: {missing_columns}")

    if frame.empty:
        raise ValueError(f"{path} is empty.")

    if frame[TARGET_COLUMN].isna().any():
        raise ValueError(f"{path} has missing {TARGET_COLUMN} values.")

    invalid_targets = sorted(set(frame[TARGET_COLUMN].dropna()) - {0, 1})
    if invalid_targets:
        raise ValueError(f"{path} has non-binary target values: {invalid_targets}")

    probability = frame[PROBABILITY_COLUMN]
    if probability.isna().any():
        raise ValueError(f"{path} has missing predicted probabilities.")
    if not probability.between(0.0, 1.0).all():
        raise ValueError(f"{path} has predicted probabilities outside [0, 1].")

    for slice_column in ("split_partition", "evaluation_slice"):
        if slice_column not in frame.columns:
            continue
        observed_labels = frame[slice_column].dropna().astype(str).map(normalize_label)
        final_test_labels = sorted(set(observed_labels).intersection(FINAL_TEST_LABELS))
        if final_test_labels:
            raise ValueError(
                f"{path} contains final-test rows in `{slice_column}`: {final_test_labels}. "
                "Issue #29 evaluates validation predictions only."
            )


def normalize_label(value: str) -> str:
    """Normalize slice labels for validation/test boundary checks."""
    return (
        value.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def compute_metrics_for_threshold(
    model_name: str,
    y_true: pd.Series,
    y_probability: pd.Series,
    threshold: float,
) -> dict[str, Any]:
    """Compute threshold-dependent AO1 classification metrics."""
    y_predicted = (y_probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_counts(y_true, y_predicted)
    row_count = int(len(y_true))
    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)

    return {
        "model_name": model_name,
        "threshold": float(threshold),
        "row_count": row_count,
        "positive_class_rate": float(y_true.mean()),
        "predicted_positive_rate": float(y_predicted.mean()),
        "accuracy": safe_divide(tp + tn, row_count),
        "precision": precision,
        "recall": recall,
        "f1": safe_divide(2 * precision * recall, precision + recall),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def safe_divide(numerator: float, denominator: float) -> float:
    """Return a finite division result, using 0 when the denominator is 0."""
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def confusion_counts(y_true: pd.Series, y_predicted: pd.Series) -> tuple[int, int, int, int]:
    """Return true-negative, false-positive, false-negative, and true-positive counts."""
    true_values = y_true.astype(int)
    predicted_values = y_predicted.astype(int)
    tn = int(((true_values == 0) & (predicted_values == 0)).sum())
    fp = int(((true_values == 0) & (predicted_values == 1)).sum())
    fn = int(((true_values == 1) & (predicted_values == 0)).sum())
    tp = int(((true_values == 1) & (predicted_values == 1)).sum())
    return tn, fp, fn, tp


def log_loss_binary(y_true: pd.Series, y_probability: pd.Series) -> float:
    """Compute binary log loss without requiring sklearn."""
    epsilon = 1e-15
    losses = []
    for actual, probability in zip(y_true.astype(int), y_probability.astype(float)):
        clipped = min(max(float(probability), epsilon), 1.0 - epsilon)
        if actual == 1:
            losses.append(-math.log(clipped))
        else:
            losses.append(-math.log(1.0 - clipped))
    return float(sum(losses) / len(losses))


def trapezoid_auc(x_values: list[float], y_values: list[float]) -> float:
    """Compute trapezoidal area under a curve sorted by x."""
    paired_points = sorted(zip(x_values, y_values), key=lambda item: item[0])
    area = 0.0
    for (previous_x, previous_y), (current_x, current_y) in zip(
        paired_points,
        paired_points[1:],
    ):
        area += (current_x - previous_x) * (previous_y + current_y) / 2.0
    return float(area)


def build_roc_points_for_model(
    y_true: pd.Series,
    y_probability: pd.Series,
) -> list[dict[str, float]]:
    """Build ROC points using candidate probability thresholds."""
    thresholds = [float("inf"), *sorted(set(y_probability.astype(float)), reverse=True)]
    rows = []
    for threshold in thresholds:
        y_predicted = (y_probability >= threshold).astype(int)
        tn, fp, fn, tp = confusion_counts(y_true, y_predicted)
        rows.append(
            {
                "false_positive_rate": safe_divide(fp, fp + tn),
                "true_positive_rate": safe_divide(tp, tp + fn),
                "threshold": threshold,
            }
        )
    return rows


def build_precision_recall_points_for_model(
    y_true: pd.Series,
    y_probability: pd.Series,
) -> list[dict[str, float]]:
    """Build precision-recall points using candidate probability thresholds."""
    thresholds = [float("inf"), *sorted(set(y_probability.astype(float)), reverse=True)]
    rows = []
    for threshold in thresholds:
        y_predicted = (y_probability >= threshold).astype(int)
        tn, fp, fn, tp = confusion_counts(y_true, y_predicted)
        precision = 1.0 if (tp + fp) == 0 else safe_divide(tp, tp + fp)
        rows.append(
            {
                "precision": precision,
                "recall": safe_divide(tp, tp + fn),
                "threshold": threshold,
            }
        )
    return rows


def average_precision_from_curve(pr_points: list[dict[str, float]]) -> float:
    """Compute average precision from recall-ordered precision-recall points."""
    area = 0.0
    previous_recall = 0.0
    for point in sorted(pr_points, key=lambda row: row["recall"]):
        recall = point["recall"]
        precision = point["precision"]
        area += max(recall - previous_recall, 0.0) * precision
        previous_recall = max(previous_recall, recall)
    return float(area)


def compute_model_level_metrics(model_name: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Compute ranking and default-threshold metrics for one AO1 model."""
    y_true = frame[TARGET_COLUMN].astype(int)
    y_probability = frame[PROBABILITY_COLUMN].astype(float)
    roc_points = build_roc_points_for_model(y_true, y_probability)
    pr_points = build_precision_recall_points_for_model(y_true, y_probability)
    metrics = compute_metrics_for_threshold(
        model_name,
        y_true,
        y_probability,
        DEFAULT_THRESHOLD,
    )
    metrics.update(
        {
            "roc_auc": trapezoid_auc(
                [row["false_positive_rate"] for row in roc_points],
                [row["true_positive_rate"] for row in roc_points],
            ),
            "pr_auc": average_precision_from_curve(pr_points),
            "log_loss": log_loss_binary(y_true, y_probability),
        }
    )
    return metrics


def build_threshold_grid(predictions: pd.DataFrame) -> pd.DataFrame:
    """Build threshold trade-off rows across all candidate models."""
    rows: list[dict[str, Any]] = []
    for model_name, frame in predictions.groupby(MODEL_COLUMN):
        y_true = frame[TARGET_COLUMN].astype(int)
        y_probability = frame[PROBABILITY_COLUMN].astype(float)
        for threshold in THRESHOLD_GRID:
            rows.append(
                compute_metrics_for_threshold(
                    str(model_name),
                    y_true,
                    y_probability,
                    threshold,
                )
            )
    return pd.DataFrame(rows)


def build_curve_points(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build ROC and precision-recall curve point tables."""
    roc_rows: list[dict[str, Any]] = []
    pr_rows: list[dict[str, Any]] = []

    for model_name, frame in predictions.groupby(MODEL_COLUMN):
        y_true = frame[TARGET_COLUMN].astype(int)
        y_probability = frame[PROBABILITY_COLUMN].astype(float)

        for index, point in enumerate(build_roc_points_for_model(y_true, y_probability)):
            roc_rows.append(
                {
                    "model_name": model_name,
                    "point_index": index,
                    "false_positive_rate": point["false_positive_rate"],
                    "true_positive_rate": point["true_positive_rate"],
                    "threshold": point["threshold"],
                }
            )

        for index, point in enumerate(
            build_precision_recall_points_for_model(y_true, y_probability)
        ):
            pr_rows.append(
                {
                    "model_name": model_name,
                    "point_index": index,
                    "precision": point["precision"],
                    "recall": point["recall"],
                    "threshold": point["threshold"],
                }
            )

    return pd.DataFrame(roc_rows), pd.DataFrame(pr_rows)


def build_calibration_table(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarize directional probability calibration by fixed probability bins."""
    bins = [index / 10 for index in range(11)]
    rows: list[dict[str, Any]] = []

    for model_name, frame in predictions.groupby(MODEL_COLUMN):
        model_frame = frame.copy()
        model_frame["probability_bin"] = pd.cut(
            model_frame[PROBABILITY_COLUMN],
            bins=bins,
            include_lowest=True,
            right=True,
        )
        grouped = model_frame.groupby("probability_bin", observed=False)
        for probability_bin, bin_frame in grouped:
            if bin_frame.empty:
                continue
            rows.append(
                {
                    "model_name": model_name,
                    "probability_bin": str(probability_bin),
                    "row_count": int(len(bin_frame)),
                    "average_predicted_probability": float(
                        bin_frame[PROBABILITY_COLUMN].mean()
                    ),
                    "actual_positive_rate": float(bin_frame[TARGET_COLUMN].mean()),
                }
            )

    return pd.DataFrame(rows)


def write_findings(
    metrics_df: pd.DataFrame,
    threshold_df: pd.DataFrame,
    calibration_df: pd.DataFrame,
    config: AO1EvaluationConfig,
    artifact_status: dict[str, Any],
) -> None:
    """Write a compact report-facing AO1 evaluation findings note."""
    metric_rows = metrics_df.sort_values(["roc_auc", "pr_auc"], ascending=False)
    best_row = metric_rows.iloc[0].to_dict()

    threshold_focus = threshold_df[
        threshold_df["model_name"] == best_row["model_name"]
    ].sort_values(["recall", "precision"], ascending=False)
    high_recall_row = threshold_focus.iloc[0].to_dict()

    lines = [
        "# AO1 Model Evaluation Findings",
        "",
        "Issue: `#29`",
        "",
        "## Scope",
        "",
        "This evaluation pack compares available AO1 candidate models on the validation slice only. "
        "It does not evaluate the final test partition, select the final operating threshold, or "
        "override the separate threshold-governance task.",
        "The final test partition is not used in this evaluation pack.",
        "",
        "## Candidate Model Summary",
        "",
        f"Comparison status: `{artifact_status['comparison_status']}`",
        "",
        "Expected prediction artifacts:",
        "",
    ]

    for model_key, path in artifact_status["expected_model_artifacts"].items():
        lines.append(f"- `{model_key}`: `{path}`")

    lines.extend(
        [
            "",
            "Available prediction artifacts:",
            "",
        ]
    )

    for model_key, path in artifact_status["available_model_artifacts"].items():
        lines.append(f"- `{model_key}`: `{path}`")

    if artifact_status["missing_model_artifacts"]:
        lines.extend(["", "Missing prediction artifacts:", ""])
        for model_key, path in artifact_status["missing_model_artifacts"].items():
            lines.append(f"- `{model_key}`: `{path}`")
        lines.extend(
            [
                "",
                "The H1 Logistic Regression versus XGBoost comparison is not complete until "
                "both validation prediction artifacts are available.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "The H1 Logistic Regression versus XGBoost validation comparison is complete "
                "for the available issue #29 evaluation scope.",
                "",
            ]
        )

    lines.extend(
        [
            "| Model | ROC-AUC | PR-AUC | Precision @ 0.50 | Recall @ 0.50 | F1 @ 0.50 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for _, row in metric_rows.iterrows():
        lines.append(
            "| {model_name} | {roc_auc:.4f} | {pr_auc:.4f} | {precision:.4f} | "
            "{recall:.4f} | {f1:.4f} |".format(**row.to_dict())
        )

    lines.extend(
        [
            "",
            "## Operating-Threshold Readiness",
            "",
            f"The strongest available validation ranking model is `{best_row['model_name']}`. "
            "The threshold grid should be reviewed by the team before freezing an AO1 "
            "operating threshold for AO3 and dashboard use.",
            "This findings note supports recall, precision, and threshold trade-off review; "
            "it does not select the final operational threshold.",
            "",
            "A recall-oriented candidate row for the current best model is:",
            "",
            "| Model | Threshold | Precision | Recall | Predicted Positive Rate | False Negatives | False Positives |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            (
                "| {model_name} | {threshold:.2f} | {precision:.4f} | {recall:.4f} | "
                "{predicted_positive_rate:.4f} | {false_negative} | {false_positive} |"
            ).format(**high_recall_row),
            "",
            "## Calibration Observation",
            "",
        ]
    )

    if calibration_df.empty:
        lines.append("No calibration rows were generated.")
    else:
        lines.append(
            "Calibration is summarized by fixed predicted-probability bins in "
            f"`{config.calibration_output_path}`. The table is intended as a directional "
            "check, not as a formal probability calibration model."
        )

    lines.extend(
        [
            "",
            "## Output Artifacts",
            "",
            f"- Metrics comparison: `{config.metrics_output_path}`",
            f"- Threshold grid: `{config.threshold_output_path}`",
            f"- Confusion matrices: `{config.confusion_output_path}`",
            f"- ROC curve points: `{config.roc_curve_output_path}`",
            f"- Precision-recall curve points: `{config.precision_recall_curve_output_path}`",
            f"- Calibration table: `{config.calibration_output_path}`",
            f"- Evaluation metadata: `{config.metadata_output_path}`",
        ]
    )

    config.findings_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.findings_output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Write JSON metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_ao1_model_evaluation(
    config: AO1EvaluationConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Build AO1 validation metrics, curves, threshold grids, and findings."""
    logger.info("Starting AO1 model evaluation pack.")
    predictions, artifact_status = read_prediction_artifacts(config)
    model_names = sorted(predictions[MODEL_COLUMN].astype(str).unique())
    logger.info("Loaded AO1 validation predictions for models: %s", model_names)

    metric_rows = [
        compute_model_level_metrics(str(model_name), frame)
        for model_name, frame in predictions.groupby(MODEL_COLUMN)
    ]
    metrics_df = pd.DataFrame(metric_rows).sort_values(
        ["roc_auc", "pr_auc"],
        ascending=False,
    )
    threshold_df = build_threshold_grid(predictions)
    confusion_df = threshold_df[
        [
            "model_name",
            "threshold",
            "row_count",
            "true_negative",
            "false_positive",
            "false_negative",
            "true_positive",
        ]
    ].copy()
    roc_df, pr_df = build_curve_points(predictions)
    calibration_df = build_calibration_table(predictions)

    for path, frame in (
        (config.metrics_output_path, metrics_df),
        (config.threshold_output_path, threshold_df),
        (config.confusion_output_path, confusion_df),
        (config.roc_curve_output_path, roc_df),
        (config.precision_recall_curve_output_path, pr_df),
        (config.calibration_output_path, calibration_df),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        logger.info("Wrote AO1 evaluation artifact: %s", path)

    write_findings(metrics_df, threshold_df, calibration_df, config, artifact_status)

    metadata = {
        "metadata_status": "ao1_validation_evaluation_completed",
        "issue": "#29",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_column": TARGET_COLUMN,
        "probability_column": PROBABILITY_COLUMN,
        "default_threshold": DEFAULT_THRESHOLD,
        "threshold_grid": list(THRESHOLD_GRID),
        "evaluated_models": model_names,
        "final_test_used": False,
        "comparison_status": artifact_status["comparison_status"],
        "expected_model_artifacts": artifact_status["expected_model_artifacts"],
        "available_model_artifacts": artifact_status["available_model_artifacts"],
        "missing_model_artifacts": artifact_status["missing_model_artifacts"],
        "h1_comparison_complete": artifact_status["comparison_status"] == "complete",
        "required_prediction_columns": sorted(REQUIRED_PREDICTION_COLUMNS),
        "input_prediction_paths": {
            "logistic_regression": str(config.logistic_predictions_path),
            "xgboost": str(config.xgboost_predictions_path),
        },
        "artifacts": {
            "metrics_csv": str(config.metrics_output_path),
            "threshold_tradeoff_csv": str(config.threshold_output_path),
            "confusion_matrix_csv": str(config.confusion_output_path),
            "roc_curve_csv": str(config.roc_curve_output_path),
            "precision_recall_curve_csv": str(config.precision_recall_curve_output_path),
            "calibration_csv": str(config.calibration_output_path),
            "findings_markdown": str(config.findings_output_path),
        },
    }
    write_json(metadata, config.metadata_output_path)
    logger.info("AO1 model evaluation pack completed successfully.")
    return metadata


def main() -> None:
    """Run AO1 model evaluation with default local artifact paths."""
    run_ao1_model_evaluation(AO1EvaluationConfig(), configure_logging())


if __name__ == "__main__":
    main()
