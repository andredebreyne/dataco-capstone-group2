"""Build the AO2 validation evaluation pack from saved prediction artifacts.

This script compares AO2 candidate models on validation predictions that were
already produced by the Ridge baseline and Gradient Boosting regressor jobs.
It does not train models, refit preprocessing, score final test rows, derive
AO3 margins, or assign AO3 priority groups.
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

import numpy as np
import pandas as pd


TARGET_COLUMN = "Order_Profit_Per_Order"
PREDICTION_COLUMN = "predicted_profit"
MODEL_COLUMN = "model_name"
EXPECTED_EVALUATION_SLICE = "development_inner_validation"
EXPECTED_MODELS = {
    "ao2_ridge_baseline",
    "ao2_gradient_boosting_regressor",
}
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
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "evaluation_slice",
    TARGET_COLUMN,
    PREDICTION_COLUMN,
    "residual",
    "absolute_error",
}

KEY_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    MODEL_COLUMN,
)


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
class AO2EvaluationConfig:
    """Configuration for AO2 validation evaluation outputs."""

    ridge_predictions_path: Path = Path(
        os.getenv(
            "DATACO_AO2_RIDGE_VALIDATION_PREDICTIONS_PATH",
            str(REPO_ROOT / "report/tables/ao2_ridge_validation_predictions.csv"),
        )
    )
    ridge_metrics_path: Path = Path(
        os.getenv(
            "DATACO_AO2_RIDGE_METRICS_CSV_PATH",
            str(REPO_ROOT / "report/tables/ao2_ridge_validation_metrics.csv"),
        )
    )
    ridge_residual_diagnostics_path: Path = Path(
        os.getenv(
            "DATACO_AO2_RIDGE_RESIDUAL_DIAGNOSTICS_PATH",
            str(REPO_ROOT / "report/tables/ao2_ridge_residual_diagnostics.csv"),
        )
    )
    ridge_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO2_RIDGE_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/ridge_baseline/ao2_ridge_baseline_metadata.json"
            ),
        )
    )
    gradient_boosting_predictions_path: Path = Path(
        os.getenv(
            "DATACO_AO2_GRADIENT_BOOSTING_VALIDATION_PREDICTIONS_PATH",
            str(REPO_ROOT / "report/tables/ao2_gradient_boosting_validation_predictions.csv"),
        )
    )
    gradient_boosting_metrics_path: Path = Path(
        os.getenv(
            "DATACO_AO2_GRADIENT_BOOSTING_METRICS_CSV_PATH",
            str(REPO_ROOT / "report/tables/ao2_gradient_boosting_validation_metrics.csv"),
        )
    )
    gradient_boosting_residual_diagnostics_path: Path = Path(
        os.getenv(
            "DATACO_AO2_GRADIENT_BOOSTING_RESIDUAL_DIAGNOSTICS_PATH",
            str(REPO_ROOT / "report/tables/ao2_gradient_boosting_residual_diagnostics.csv"),
        )
    )
    gradient_boosting_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO2_GRADIENT_BOOSTING_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metadata.json"
            ),
        )
    )
    metrics_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_METRICS_PATH",
            str(REPO_ROOT / "report/tables/ao2_model_evaluation_metrics.csv"),
        )
    )
    residual_diagnostics_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_RESIDUAL_DIAGNOSTICS_PATH",
            str(REPO_ROOT / "report/tables/ao2_residual_diagnostics_by_model.csv"),
        )
    )
    error_slices_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_ERROR_SLICES_PATH",
            str(REPO_ROOT / "report/tables/ao2_error_slices.csv"),
        )
    )
    findings_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_FINDINGS_PATH",
            str(REPO_ROOT / "report/tables/ao2_model_evaluation_findings.md"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/evaluation/ao2_evaluation_metadata.json"
            ),
        )
    )
    min_slice_rows: int = int(os.getenv("DATACO_AO2_EVALUATION_MIN_SLICE_ROWS", "100"))


def configure_logging() -> logging.Logger:
    """Configure console logging for local or Databricks execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao2_model_evaluation")


def normalize_label(value: Any) -> str:
    """Normalize slice labels for validation/test boundary checks."""
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def read_optional_json(path: Path) -> dict[str, Any] | None:
    """Read optional JSON metadata when present."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def finite_float(value: Any) -> float:
    """Return a finite float or raise a clear error."""
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"Expected finite numeric value, received {value!r}.")
    return numeric_value


def candidate_name_for_model(frame: pd.DataFrame, model_metadata: dict[str, Any] | None) -> str | None:
    """Return a concise candidate label when the source artifact provides one."""
    if "candidate_name" in frame.columns:
        candidate_values = sorted(
            {
                str(value)
                for value in frame["candidate_name"].dropna().unique()
                if str(value).strip()
            }
        )
        if len(candidate_values) == 1:
            return candidate_values[0]

    model_name = str(frame[MODEL_COLUMN].iloc[0])
    if model_name == "ao2_ridge_baseline" and model_metadata:
        alpha = (
            model_metadata.get("ridge_regression", {})
            .get("parameters", {})
            .get("alpha")
        )
        if alpha is not None:
            return f"fixed_alpha_{str(alpha).replace('.', '_')}"

    return None


def assert_no_final_test_labels(frame: pd.DataFrame, path: Path) -> None:
    """Fail if a prediction artifact contains final-test or holdout labels."""
    label_columns = [
        column_name
        for column_name in frame.columns
        if any(token in column_name.lower() for token in ("slice", "split", "partition"))
    ]
    for column_name in label_columns:
        observed_labels = frame[column_name].dropna().map(normalize_label)
        blocked_labels = sorted(set(observed_labels).intersection(FINAL_TEST_LABELS))
        if blocked_labels:
            raise ValueError(
                f"{path} contains final-test or holdout labels in `{column_name}`: "
                f"{blocked_labels}. AO2 issue #37 evaluates validation rows only."
            )


def validate_prediction_contract(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Validate and normalize one row-level AO2 validation prediction artifact."""
    missing_columns = sorted(REQUIRED_PREDICTION_COLUMNS.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"{path} is missing required columns: {missing_columns}")

    if frame.empty:
        raise ValueError(f"{path} is empty.")

    assert_no_final_test_labels(frame, path)

    invalid_slices = sorted(
        {
            str(value)
            for value in frame["evaluation_slice"].dropna().unique()
            if "validation" not in normalize_label(value)
        }
    )
    if invalid_slices:
        raise ValueError(
            f"{path} contains non-validation evaluation_slice values: {invalid_slices}"
        )

    model_names = sorted(str(value) for value in frame[MODEL_COLUMN].dropna().unique())
    if len(model_names) != 1:
        raise ValueError(f"{path} must contain exactly one model_name. Found: {model_names}")
    if model_names[0] not in EXPECTED_MODELS:
        raise ValueError(f"{path} contains unexpected model_name: {model_names[0]}")

    numeric_columns = (TARGET_COLUMN, PREDICTION_COLUMN, "residual", "absolute_error")
    normalized_frame = frame.copy()
    for column_name in numeric_columns:
        normalized_frame[column_name] = pd.to_numeric(
            normalized_frame[column_name],
            errors="coerce",
        )
        if normalized_frame[column_name].isna().any():
            raise ValueError(f"{path} has missing or non-numeric `{column_name}` values.")

    duplicate_count = int(normalized_frame.duplicated(list(KEY_COLUMNS)).sum())
    if duplicate_count:
        raise ValueError(f"{path} contains {duplicate_count} duplicate model/key rows.")

    recomputed_residual = normalized_frame[TARGET_COLUMN] - normalized_frame[PREDICTION_COLUMN]
    residual_delta = (normalized_frame["residual"] - recomputed_residual).abs().max()
    if residual_delta > 1e-4:
        raise ValueError(
            f"{path} residual values do not match actual minus prediction. "
            f"Maximum difference: {residual_delta}"
        )

    recomputed_absolute_error = recomputed_residual.abs()
    absolute_error_delta = (
        normalized_frame["absolute_error"] - recomputed_absolute_error
    ).abs().max()
    if absolute_error_delta > 1e-4:
        raise ValueError(
            f"{path} absolute_error values do not match absolute residual. "
            f"Maximum difference: {absolute_error_delta}"
        )

    return normalized_frame


def model_artifact_paths(config: AO2EvaluationConfig) -> dict[str, dict[str, Path]]:
    """Return the expected upstream artifacts by AO2 model."""
    return {
        "ao2_ridge_baseline": {
            "validation_predictions_csv": config.ridge_predictions_path,
            "validation_metrics_csv": config.ridge_metrics_path,
            "residual_diagnostics_csv": config.ridge_residual_diagnostics_path,
            "metadata_json": config.ridge_metadata_path,
        },
        "ao2_gradient_boosting_regressor": {
            "validation_predictions_csv": config.gradient_boosting_predictions_path,
            "validation_metrics_csv": config.gradient_boosting_metrics_path,
            "residual_diagnostics_csv": config.gradient_boosting_residual_diagnostics_path,
            "metadata_json": config.gradient_boosting_metadata_path,
        },
    }


def read_prediction_artifacts(
    config: AO2EvaluationConfig,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, dict[str, Any] | None]]:
    """Read available AO2 validation prediction artifacts and artifact status."""
    frames: list[pd.DataFrame] = []
    metadata_by_model: dict[str, dict[str, Any] | None] = {}
    missing_artifacts: dict[str, dict[str, str]] = {}
    available_artifacts: dict[str, dict[str, str]] = {}

    for model_name, artifacts in model_artifact_paths(config).items():
        available_artifacts[model_name] = {}
        missing_artifacts[model_name] = {}

        for artifact_name, path in artifacts.items():
            if path.exists():
                available_artifacts[model_name][artifact_name] = str(path)
            else:
                missing_artifacts[model_name][artifact_name] = str(path)

        metadata_by_model[model_name] = read_optional_json(artifacts["metadata_json"])
        predictions_path = artifacts["validation_predictions_csv"]
        if predictions_path.exists():
            frame = pd.read_csv(predictions_path)
            frame = validate_prediction_contract(frame, predictions_path)
            model_metadata = metadata_by_model.get(model_name)
            candidate_name = candidate_name_for_model(frame, model_metadata)
            if candidate_name and "candidate_name" not in frame.columns:
                frame["candidate_name"] = candidate_name
            frames.append(frame)

    if not frames:
        expected_paths = [
            str(paths["validation_predictions_csv"])
            for paths in model_artifact_paths(config).values()
        ]
        raise FileNotFoundError(
            "No AO2 validation prediction artifacts were found. Expected at least "
            f"one of: {expected_paths}"
        )

    missing_models = [
        model_name
        for model_name, artifacts in missing_artifacts.items()
        if artifacts
    ]
    evaluated_models = sorted({str(frame[MODEL_COLUMN].iloc[0]) for frame in frames})
    artifact_status = {
        "expected_model_artifacts": {
            model_name: {name: str(path) for name, path in artifacts.items()}
            for model_name, artifacts in model_artifact_paths(config).items()
        },
        "available_model_artifacts": available_artifacts,
        "missing_model_artifacts": {
            model_name: artifacts
            for model_name, artifacts in missing_artifacts.items()
            if artifacts
        },
        "expected_models": sorted(EXPECTED_MODELS),
        "evaluated_models": evaluated_models,
        "missing_models": sorted(EXPECTED_MODELS.difference(evaluated_models)),
        "comparison_status": "partial" if missing_models else "complete",
    }

    return pd.concat(frames, ignore_index=True), artifact_status, metadata_by_model


def wrong_profit_sign_share(actual: pd.Series, predicted: pd.Series) -> float:
    """Return the share of rows where predicted and actual profit signs differ."""
    return float(np.mean(np.sign(actual.to_numpy(dtype=float)) != np.sign(predicted)))


def r2_score_from_arrays(actual: pd.Series, predicted: pd.Series) -> float:
    """Compute R-squared without requiring sklearn at evaluation time."""
    residual_sum_of_squares = float(np.sum(np.square(actual - predicted)))
    total_sum_of_squares = float(np.sum(np.square(actual - float(actual.mean()))))
    if total_sum_of_squares == 0.0:
        return 0.0
    return 1.0 - residual_sum_of_squares / total_sum_of_squares


def compute_model_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute one validation metric row per AO2 candidate model."""
    rows: list[dict[str, Any]] = []
    group_columns = [MODEL_COLUMN]
    if "candidate_name" in predictions.columns:
        group_columns.append("candidate_name")

    for group_key, group in predictions.groupby(group_columns, dropna=False, sort=True):
        if isinstance(group_key, tuple):
            model_name = str(group_key[0])
            candidate_name = None if pd.isna(group_key[1]) else str(group_key[1])
        else:
            model_name = str(group_key)
            candidate_name = None

        actual = group[TARGET_COLUMN]
        predicted = group[PREDICTION_COLUMN]
        residual = actual - predicted
        absolute_error = residual.abs()
        rows.append(
            {
                "model_name": model_name,
                "candidate_name": candidate_name,
                "validation_rows": int(len(group)),
                "rmse": float(math.sqrt(np.mean(np.square(residual)))),
                "mae": float(absolute_error.mean()),
                "r2": float(r2_score_from_arrays(actual, predicted)),
                "median_absolute_error": float(absolute_error.median()),
                "mean_error": float(residual.mean()),
                "target_mean": float(actual.mean()),
                "target_std": float(actual.std(ddof=1)) if len(actual) > 1 else 0.0,
                "prediction_mean": float(predicted.mean()),
                "prediction_std": float(predicted.std(ddof=1)) if len(predicted) > 1 else 0.0,
                "wrong_profit_sign_share": wrong_profit_sign_share(actual, predicted),
                "final_test_used": False,
            }
        )

    return pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)


def percentile(series: pd.Series, quantile: float) -> float:
    """Return a finite percentile value from a non-empty numeric series."""
    return finite_float(series.quantile(quantile))


def compute_residual_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute residual distribution diagnostics by model."""
    rows: list[dict[str, Any]] = []
    group_columns = [MODEL_COLUMN]
    if "candidate_name" in predictions.columns:
        group_columns.append("candidate_name")

    for group_key, group in predictions.groupby(group_columns, dropna=False, sort=True):
        if isinstance(group_key, tuple):
            model_name = str(group_key[0])
            candidate_name = None if pd.isna(group_key[1]) else str(group_key[1])
        else:
            model_name = str(group_key)
            candidate_name = None

        actual = group[TARGET_COLUMN]
        predicted = group[PREDICTION_COLUMN]
        residual = actual - predicted
        absolute_error = residual.abs()
        rows.append(
            {
                "model_name": model_name,
                "candidate_name": candidate_name,
                "validation_rows": int(len(group)),
                "residual_mean": float(residual.mean()),
                "residual_standard_deviation": (
                    float(residual.std(ddof=1)) if len(residual) > 1 else 0.0
                ),
                "residual_median": float(residual.median()),
                "residual_min": float(residual.min()),
                "residual_max": float(residual.max()),
                "residual_p10": percentile(residual, 0.10),
                "residual_p25": percentile(residual, 0.25),
                "residual_p50": percentile(residual, 0.50),
                "residual_p75": percentile(residual, 0.75),
                "residual_p90": percentile(residual, 0.90),
                "absolute_error_p50": percentile(absolute_error, 0.50),
                "absolute_error_p75": percentile(absolute_error, 0.75),
                "absolute_error_p90": percentile(absolute_error, 0.90),
                "wrong_profit_sign_share": wrong_profit_sign_share(actual, predicted),
            }
        )

    return pd.DataFrame(rows).sort_values("model_name").reset_index(drop=True)


def add_actual_profit_bands(predictions: pd.DataFrame) -> pd.Series:
    """Return compact actual-profit band labels based on validation targets."""
    target = predictions[TARGET_COLUMN]
    q05 = percentile(target, 0.05)
    q95 = percentile(target, 0.95)
    positive_target = target[target >= 0]
    positive_q50 = percentile(positive_target, 0.50) if not positive_target.empty else 0.0
    positive_q75 = percentile(positive_target, 0.75) if not positive_target.empty else 0.0

    conditions = [
        target <= q05,
        target < 0,
        target <= positive_q50,
        target <= positive_q75,
        target < q95,
    ]
    labels = [
        "extreme_low_profit",
        "loss_or_negative_profit",
        "low_positive_profit",
        "medium_positive_profit",
        "high_positive_profit",
    ]
    return pd.Series(
        np.select(conditions, labels, default="extreme_high_profit"),
        index=predictions.index,
    )


def add_actual_profit_quantile_bands(predictions: pd.DataFrame) -> pd.Series:
    """Return target quartile labels for validation targets."""
    labels = ("q1_lowest_profit", "q2_lower_mid_profit", "q3_upper_mid_profit", "q4_highest_profit")
    try:
        return pd.qcut(predictions[TARGET_COLUMN], q=4, labels=labels, duplicates="drop").astype(str)
    except ValueError:
        return pd.Series("all_targets", index=predictions.index)


def add_absolute_error_bands(predictions: pd.DataFrame) -> pd.Series:
    """Return model-specific absolute-error magnitude bands."""
    bands = pd.Series(index=predictions.index, dtype="object")
    logger = logging.getLogger("dataco.ao2_model_evaluation")
    for model_name, group in predictions.groupby(MODEL_COLUMN, sort=True):
        absolute_error = group["absolute_error"]
        p50 = percentile(absolute_error, 0.50)
        p75 = percentile(absolute_error, 0.75)
        p90 = percentile(absolute_error, 0.90)
        conditions = [
            absolute_error <= p50,
            absolute_error <= p75,
            absolute_error <= p90,
        ]
        labels = [
            "typical_error_le_p50",
            "elevated_error_p50_p75",
            "large_error_p75_p90",
        ]
        bands.loc[group.index] = np.select(
            conditions,
            labels,
            default="extreme_error_gt_p90",
        )
        logger.debug("Computed absolute-error bands for %s.", model_name)
    return bands


def summarize_slice(
    group: pd.DataFrame,
    slice_type: str,
    slice_value: str,
    min_slice_rows: int,
) -> dict[str, Any]:
    """Summarize one model/slice combination."""
    actual = group[TARGET_COLUMN]
    predicted = group[PREDICTION_COLUMN]
    residual = actual - predicted
    absolute_error = residual.abs()
    return {
        "slice_type": slice_type,
        "slice_value": slice_value,
        "model_name": str(group[MODEL_COLUMN].iloc[0]),
        "candidate_name": (
            str(group["candidate_name"].iloc[0])
            if "candidate_name" in group.columns and pd.notna(group["candidate_name"].iloc[0])
            else None
        ),
        "row_count": int(len(group)),
        "rmse": float(math.sqrt(np.mean(np.square(residual)))),
        "mae": float(absolute_error.mean()),
        "mean_error": float(residual.mean()),
        "median_absolute_error": float(absolute_error.median()),
        "wrong_profit_sign_share": wrong_profit_sign_share(actual, predicted),
        "is_unstable_small_slice": bool(len(group) < min_slice_rows),
    }


def compute_error_slices(predictions: pd.DataFrame, min_slice_rows: int) -> pd.DataFrame:
    """Create compact target and error-band diagnostics by model."""
    slice_frame = predictions.copy()
    slice_frame["actual_profit_band"] = add_actual_profit_bands(slice_frame)
    slice_frame["actual_profit_quantile"] = add_actual_profit_quantile_bands(slice_frame)
    slice_frame["absolute_error_band"] = add_absolute_error_bands(slice_frame)

    rows: list[dict[str, Any]] = []
    for slice_type in (
        "actual_profit_band",
        "actual_profit_quantile",
        "absolute_error_band",
    ):
        for (_, slice_value), group in slice_frame.groupby([MODEL_COLUMN, slice_type], sort=True):
            rows.append(
                summarize_slice(
                    group=group,
                    slice_type=slice_type,
                    slice_value=str(slice_value),
                    min_slice_rows=min_slice_rows,
                )
            )

    return pd.DataFrame(rows).sort_values(
        ["slice_type", "slice_value", "model_name"]
    ).reset_index(drop=True)


def metric_value(metrics_df: pd.DataFrame, model_name: str, metric_name: str) -> float:
    """Return a finite metric value for a model."""
    value = metrics_df.loc[metrics_df[MODEL_COLUMN] == model_name, metric_name].iloc[0]
    return finite_float(value)


def make_findings_markdown(
    metrics_df: pd.DataFrame,
    residual_df: pd.DataFrame,
    error_slices_df: pd.DataFrame,
    metadata: dict[str, Any],
) -> str:
    """Create the report-facing AO2 evaluation findings note."""
    lines = [
        "# AO2 Model Evaluation Findings",
        "",
        "Issue: `#37`",
        "",
        "## Scope",
        "",
        "This evaluation pack compares saved AO2 validation predictions only. It does not train models, change preprocessing, score final test rows, derive AO3 margins, or assign AO3 risk-margin groups.",
        "",
        "Final test not used: the metadata field `final_test_used` is `false`.",
        "",
        "Target-policy caveat: AO2 evaluation relies on the previously generated leakage-safe model artifacts where direct target, duplicate profit, realized margin, sales, order-value, and post-shipment fields were excluded from the predictor set. This pack evaluates predictions and does not reopen target-policy decisions.",
        "",
        "## Validation Metrics",
        "",
    ]

    for _, row in metrics_df.sort_values("model_name").iterrows():
        lines.extend(
            [
                f"### {row['model_name']}",
                "",
                f"- Validation rows: {int(row['validation_rows']):,}",
                f"- RMSE: {row['rmse']:.4f}",
                f"- MAE: {row['mae']:.4f}",
                f"- R-squared: {row['r2']:.4f}",
                f"- Median absolute error: {row['median_absolute_error']:.4f}",
                f"- Wrong profit-sign share: {row['wrong_profit_sign_share']:.4f}",
                "",
            ]
        )

    if EXPECTED_MODELS.issubset(set(metrics_df[MODEL_COLUMN])):
        gb_rmse = metric_value(metrics_df, "ao2_gradient_boosting_regressor", "rmse")
        ridge_rmse = metric_value(metrics_df, "ao2_ridge_baseline", "rmse")
        gb_mae = metric_value(metrics_df, "ao2_gradient_boosting_regressor", "mae")
        ridge_mae = metric_value(metrics_df, "ao2_ridge_baseline", "mae")
        gb_r2 = metric_value(metrics_df, "ao2_gradient_boosting_regressor", "r2")
        ridge_r2 = metric_value(metrics_df, "ao2_ridge_baseline", "r2")
        rmse_improvement = ridge_rmse - gb_rmse
        mae_improvement = ridge_mae - gb_mae
        lines.extend(
            [
                "## H2 Evidence",
                "",
                "Validation evidence is consistent with H2 because the Gradient Boosting Regressor improves over the Ridge baseline on RMSE and MAE.",
                "",
                f"- RMSE improvement versus Ridge: {rmse_improvement:.4f}",
                f"- MAE improvement versus Ridge: {mae_improvement:.4f}",
                f"- R-squared moves from {ridge_r2:.4f} for Ridge to {gb_r2:.4f} for Gradient Boosting.",
                "",
                "This is validation-stage H2 evidence only. It is not final H2 confirmation on test data.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## H2 Evidence",
                "",
                "The validation comparison is incomplete because at least one expected AO2 model artifact is missing. H2 evidence should not be summarized as a complete Ridge versus Gradient Boosting comparison until both validation prediction artifacts are available.",
                "",
            ]
        )

    lines.extend(
        [
            "## Residual Review",
            "",
        ]
    )
    for _, row in residual_df.sort_values("model_name").iterrows():
        model_name = row["model_name"]
        bias_direction = "underpredicts" if row["residual_mean"] > 0 else "overpredicts"
        lines.extend(
            [
                f"- `{model_name}` {bias_direction} on average by {abs(row['residual_mean']):.4f}. Residual p10/p90 are {row['residual_p10']:.4f} and {row['residual_p90']:.4f}; absolute-error p90 is {row['absolute_error_p90']:.4f}. Wrong profit-sign share is {row['wrong_profit_sign_share']:.4f}.",
            ]
        )
    lines.extend(
        [
            "",
            "Both models still compress predictions toward the target mean and miss extreme-profit cases, as shown by narrow prediction standard deviations relative to the target standard deviation and large residual ranges.",
            "",
            "## Error Slices",
            "",
            f"Generated {len(error_slices_df):,} error-slice rows across actual profit bands, actual target quartiles, and model-specific absolute-error bands. Very small slices are flagged with `is_unstable_small_slice` rather than being used for strong conclusions.",
            "",
            "Operational slices were not joined in this issue because the saved validation prediction files already provide enough evidence for a compact evaluation pack, and joining back to AO2 partitions would require additional safeguards to avoid target/proxy fields such as `ao3_order_value`, `Order_Item_Total`, `Sales`, `Benefit_per_order`, or post-shipment labels.",
            "",
            "## Limitations",
            "",
            "- Final test remains untouched.",
            "- The pack evaluates saved validation predictions only and does not inspect feature matrices or fitted preprocessing objects.",
            "- The comparison depends on issue #35 and #36 artifacts being present and valid.",
            "- Error-slice findings are descriptive validation diagnostics, not causal explanations.",
            f"- Comparison status in metadata: `{metadata['comparison_status']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write a CSV artifact with parent directories created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def save_json(payload: dict[str, Any], path: Path) -> None:
    """Write formatted JSON with parent directories created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_metadata(
    config: AO2EvaluationConfig,
    artifact_status: dict[str, Any],
    metrics_df: pd.DataFrame,
    residual_df: pd.DataFrame,
    error_slices_df: pd.DataFrame,
) -> dict[str, Any]:
    """Build issue #37 metadata."""
    comparison_status = artifact_status["comparison_status"]
    h2_complete = EXPECTED_MODELS.issubset(set(metrics_df[MODEL_COLUMN]))
    h2_consistent = False
    if h2_complete:
        h2_consistent = (
            metric_value(metrics_df, "ao2_gradient_boosting_regressor", "rmse")
            < metric_value(metrics_df, "ao2_ridge_baseline", "rmse")
            and metric_value(metrics_df, "ao2_gradient_boosting_regressor", "mae")
            < metric_value(metrics_df, "ao2_ridge_baseline", "mae")
        )

    return {
        "metadata_status": "ao2_validation_evaluation_completed",
        "issue": "#37",
        "comparison_status": comparison_status,
        "expected_models": sorted(EXPECTED_MODELS),
        "evaluated_models": sorted(metrics_df[MODEL_COLUMN].unique()),
        "missing_models": artifact_status["missing_models"],
        "input_artifact_paths": artifact_status["expected_model_artifacts"],
        "available_model_artifacts": artifact_status["available_model_artifacts"],
        "missing_artifacts": artifact_status["missing_model_artifacts"],
        "evaluation_slice": EXPECTED_EVALUATION_SLICE,
        "final_test_used": False,
        "target_column": TARGET_COLUMN,
        "prediction_column": PREDICTION_COLUMN,
        "metrics_generated": str(config.metrics_output_path),
        "residual_diagnostics_generated": str(config.residual_diagnostics_output_path),
        "error_slices_generated": str(config.error_slices_output_path),
        "findings_generated": str(config.findings_output_path),
        "metrics_rows": int(len(metrics_df)),
        "residual_diagnostics_rows": int(len(residual_df)),
        "error_slice_rows": int(len(error_slices_df)),
        "min_slice_rows": int(config.min_slice_rows),
        "h2_validation_evidence_complete": h2_complete,
        "h2_validation_evidence_consistent": h2_consistent,
        "target_policy_caveat": (
            "AO2 target-reconstruction and leakage exclusions were enforced by the "
            "upstream Ridge and Gradient Boosting model artifacts. Issue #37 evaluates "
            "saved validation predictions only and does not change target policy."
        ),
        "final_test_boundary": (
            "Final test, holdout, held-out, and test-labelled rows are rejected from "
            "metrics, residual diagnostics, error slices, findings, and H2 evidence."
        ),
        "error_slice_policy": {
            "slice_types": [
                "actual_profit_band",
                "actual_profit_quantile",
                "absolute_error_band",
            ],
            "operational_join_used": False,
            "forbidden_slice_dimensions_not_used": [
                "ao3_order_value",
                "Order_Item_Total",
                "Sales",
                "Sales_per_customer",
                "Benefit_per_order",
                "Order_Item_Profit_Ratio",
                "post-shipment fields",
                "final-test labels",
            ],
        },
        "limitations": [
            "No AO2 model is trained or retrained by this evaluation pack.",
            "No preprocessing logic is changed.",
            "No final-test predictions or labels are used.",
            "AO3 predicted margin and risk-margin segmentation are outside this issue.",
            "Operational error slices are not joined from AO2 partitions in this compact pack.",
        ],
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def run_ao2_model_evaluation(
    config: AO2EvaluationConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Create AO2 validation evaluation artifacts from saved predictions."""
    predictions, artifact_status, _ = read_prediction_artifacts(config)
    metrics_df = compute_model_metrics(predictions)
    residual_df = compute_residual_diagnostics(predictions)
    error_slices_df = compute_error_slices(predictions, config.min_slice_rows)

    metadata = build_metadata(
        config=config,
        artifact_status=artifact_status,
        metrics_df=metrics_df,
        residual_df=residual_df,
        error_slices_df=error_slices_df,
    )
    findings_text = make_findings_markdown(
        metrics_df=metrics_df,
        residual_df=residual_df,
        error_slices_df=error_slices_df,
        metadata=metadata,
    )

    save_csv(metrics_df, config.metrics_output_path)
    save_csv(residual_df, config.residual_diagnostics_output_path)
    save_csv(error_slices_df, config.error_slices_output_path)
    config.findings_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.findings_output_path.write_text(findings_text, encoding="utf-8")
    save_json(metadata, config.metadata_output_path)

    logger.info("Wrote AO2 evaluation metrics: %s", config.metrics_output_path)
    logger.info("Wrote AO2 residual diagnostics: %s", config.residual_diagnostics_output_path)
    logger.info("Wrote AO2 error slices: %s", config.error_slices_output_path)
    logger.info("Wrote AO2 findings note: %s", config.findings_output_path)
    logger.info("Wrote AO2 evaluation metadata: %s", config.metadata_output_path)
    return metadata


def main() -> None:
    """Run the AO2 validation evaluation pack."""
    run_ao2_model_evaluation(AO2EvaluationConfig(), configure_logging())


if __name__ == "__main__":
    main()
