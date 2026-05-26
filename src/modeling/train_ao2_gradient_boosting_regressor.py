"""Train the AO2 Gradient Boosting validation model.

This job consumes the official AO2 chronological partition table, creates the
same time-preserving validation slice used by the AO2 Ridge baseline when
needed, fits the approved AO2 preprocessing pipeline only on the training
slice, and evaluates a small set of XGBoost regressor configurations on
validation only. The final test partition is never used for fitting, model
selection, residual review, or validation metrics here.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.modeling.build_ao2_preprocessing_pipeline import (
    FEATURE_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS,
    build_sklearn_preprocessor,
)
from src.modeling.create_ao2_chronological_partitions import (
    AO2_PARTITION_OUTPUT_PATH,
    JOIN_KEY_COLUMNS,
    PARTITION_COLUMN,
    ROW_NUMBER_COLUMN,
    TARGET_COLUMN,
    TEST_LABEL,
)
from src.modeling.train_ao2_ridge_baseline import (
    EXCLUDED_IDENTIFIER_METADATA_COLUMNS,
    assert_required_columns_exist,
    assert_target_contract,
    assert_unique_keys,
    collect_partition_counts,
    collect_partition_labels,
    date_range_summary,
    determine_modeling_slices,
    normalize_column_name,
    read_optional_json,
    save_json,
    save_model_artifact,
    validate_volume_path,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

MODEL_NAME = "ao2_gradient_boosting_regressor"
RANDOM_STATE = 42
PRIMARY_SELECTION_METRIC = "rmse"
SECONDARY_SELECTION_METRIC = "mae"


def resolve_repo_root() -> Path:
    """Resolve repository root for local and Databricks notebook execution."""
    configured_root = os.getenv("DATACO_REPO_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    if "__file__" in globals():
        return Path(__file__).resolve().parents[2]

    current_path = Path.cwd().resolve()
    for candidate in (current_path, *current_path.parents):
        if (candidate / "src").exists() and (candidate / "models").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()

DEFAULT_OUTPUT_DIR = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_OUTPUT_DIR",
        str(REPO_ROOT / "models" / "ao2_profitability" / "gradient_boosting"),
    )
)

DEFAULT_METRICS_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_METRICS_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_gradient_boosting_metrics.json"),
    )
)

DEFAULT_METADATA_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_gradient_boosting_metadata.json"),
    )
)

DEFAULT_VALIDATION_METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_validation_metrics.csv"),
    )
)

DEFAULT_RESIDUAL_DIAGNOSTICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_RESIDUAL_DIAGNOSTICS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_residual_diagnostics.csv"),
    )
)

DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_VALIDATION_PREDICTIONS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_validation_predictions.csv"),
    )
)

DEFAULT_MODEL_COMPARISON_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_MODEL_VALIDATION_COMPARISON_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_model_validation_comparison.csv"),
    )
)

DEFAULT_FEATURE_IMPORTANCE_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_FEATURE_IMPORTANCE_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_feature_importance.csv"),
    )
)

DEFAULT_RIDGE_VALIDATION_METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_validation_metrics.csv"),
    )
)

DEFAULT_PREPROCESSING_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_PREPROCESSING_METADATA_PATH",
        str(
            REPO_ROOT
            / "models"
            / "ao2_profitability"
            / "preprocessing"
            / "ao2_preprocessing_metadata.json"
        ),
    )
)

DEFAULT_MODEL_ARTIFACT_PATH = os.getenv(
    "DATACO_AO2_GRADIENT_BOOSTING_MODEL_ARTIFACT_PATH",
    f"{VOLUME_ROOT}/models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_pipeline.joblib",
)


@dataclass(frozen=True)
class AO2GradientBoostingRegressorConfig:
    """Configuration for AO2 Gradient Boosting model training."""

    partition_input_path: str = os.getenv(
        "DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO2_PARTITION_OUTPUT_PATH,
    )
    preprocessing_metadata_path: Path = DEFAULT_PREPROCESSING_METADATA_PATH
    metrics_json_path: Path = DEFAULT_METRICS_JSON_PATH
    metadata_json_path: Path = DEFAULT_METADATA_JSON_PATH
    validation_metrics_csv_path: Path = DEFAULT_VALIDATION_METRICS_CSV_PATH
    residual_diagnostics_csv_path: Path = DEFAULT_RESIDUAL_DIAGNOSTICS_CSV_PATH
    validation_predictions_csv_path: Path = DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH
    model_comparison_csv_path: Path = DEFAULT_MODEL_COMPARISON_CSV_PATH
    feature_importance_csv_path: Path = DEFAULT_FEATURE_IMPORTANCE_CSV_PATH
    ridge_validation_metrics_csv_path: Path = DEFAULT_RIDGE_VALIDATION_METRICS_CSV_PATH
    model_artifact_path: str = DEFAULT_MODEL_ARTIFACT_PATH
    save_fitted_model: bool = (
        os.getenv("DATACO_AO2_SAVE_GRADIENT_BOOSTING_MODEL", "false").strip().lower()
        == "true"
    )
    read_format: str = "delta"
    inner_validation_ratio: float = float(os.getenv("DATACO_AO2_INNER_VALIDATION_RATIO", "0.20"))
    random_state: int = int(os.getenv("DATACO_AO2_GRADIENT_BOOSTING_RANDOM_STATE", str(RANDOM_STATE)))
    candidate_limit: int = int(os.getenv("DATACO_AO2_GRADIENT_BOOSTING_MAX_CANDIDATES", "3"))


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao2_gradient_boosting")


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def get_package_version(package_name: str) -> str | None:
    """Return an installed package version if available."""
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def assert_feature_list_is_safe() -> None:
    """Validate target, identifiers, AO3 support, and forbidden fields are excluded."""
    feature_columns = set(FEATURE_COLUMNS)

    if TARGET_COLUMN in feature_columns:
        raise ValueError("AO2 target is present in feature columns.")

    if "ao3_order_value" in feature_columns:
        raise ValueError("ao3_order_value is an AO3 support denominator, not an AO2 predictor.")

    identifier_overlap = sorted(feature_columns.intersection(EXCLUDED_IDENTIFIER_METADATA_COLUMNS))
    if identifier_overlap:
        raise ValueError(
            f"Identifier, partition, or metadata columns found in features: {identifier_overlap}"
        )

    forbidden_columns = set(FORBIDDEN_LEAKAGE_COLUMNS).union(FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS)
    forbidden_normalized = {normalize_column_name(column_name) for column_name in forbidden_columns}
    feature_normalized = {normalize_column_name(column_name) for column_name in feature_columns}
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    if forbidden_overlap:
        raise ValueError(f"Forbidden AO2 target/proxy/leakage columns found in features: {forbidden_overlap}")


def build_candidate_parameter_sets(config: AO2GradientBoostingRegressorConfig) -> list[dict[str, Any]]:
    """Return a small validation-tuning grid for AO2 Gradient Boosting."""
    base_parameters = {
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "tree_method": os.getenv("DATACO_AO2_GRADIENT_BOOSTING_TREE_METHOD", "hist"),
        "random_state": config.random_state,
        "n_jobs": int(os.getenv("DATACO_AO2_GRADIENT_BOOSTING_N_JOBS", "-1")),
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "importance_type": "gain",
    }

    candidates = [
        {
            "candidate_id": "conservative_baseline",
            **base_parameters,
            "n_estimators": 200,
            "max_depth": 3,
            "learning_rate": 0.05,
        },
        {
            "candidate_id": "slightly_deeper",
            **base_parameters,
            "n_estimators": 250,
            "max_depth": 4,
            "learning_rate": 0.05,
        },
        {
            "candidate_id": "faster_learning",
            **base_parameters,
            "n_estimators": 150,
            "max_depth": 3,
            "learning_rate": 0.10,
        },
    ]

    candidate_limit = max(1, min(config.candidate_limit, len(candidates)))
    return candidates[:candidate_limit]


def build_xgboost_pipeline(candidate_parameters: dict[str, Any]) -> Any:
    """Build the approved preprocessing plus one XGBoost regressor candidate."""
    from sklearn.pipeline import Pipeline

    try:
        from xgboost import XGBRegressor
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency: xgboost. In Databricks, run "
            "`%pip install -r requirements.txt` or `%pip install xgboost`, "
            "then restart Python. See docs/databricks_setup.md."
        ) from exc

    model_parameters = {
        key: value
        for key, value in candidate_parameters.items()
        if key != "candidate_id"
    }
    model = XGBRegressor(**model_parameters)

    return Pipeline(
        steps=[
            ("preprocessor", build_sklearn_preprocessor()),
            ("model", model),
        ]
    )


def evaluate_validation_predictions(y_true: pd.Series, y_predicted: np.ndarray) -> dict[str, Any]:
    """Compute validation-only AO2 regression metrics."""
    from sklearn.metrics import (
        mean_absolute_error,
        mean_squared_error,
        median_absolute_error,
        r2_score,
    )

    residuals = y_true.to_numpy(dtype=float) - y_predicted
    absolute_errors = np.abs(residuals)

    return {
        "rmse": float(mean_squared_error(y_true, y_predicted, squared=False)),
        "mae": float(mean_absolute_error(y_true, y_predicted)),
        "r2": float(r2_score(y_true, y_predicted)),
        "median_absolute_error": float(median_absolute_error(y_true, y_predicted)),
        "mean_error_bias": float(np.mean(residuals)),
        "validation_row_count": int(len(y_true)),
        "target_mean": float(np.mean(y_true)),
        "target_standard_deviation": float(np.std(y_true, ddof=1)) if len(y_true) > 1 else 0.0,
        "prediction_mean": float(np.mean(y_predicted)),
        "prediction_standard_deviation": float(np.std(y_predicted, ddof=1)) if len(y_predicted) > 1 else 0.0,
        "absolute_error_p50": float(np.percentile(absolute_errors, 50)),
        "absolute_error_p90": float(np.percentile(absolute_errors, 90)),
    }


def build_residual_diagnostics(y_true: pd.Series, y_predicted: np.ndarray) -> dict[str, Any]:
    """Build residual diagnostics for validation predictions."""
    residuals = y_true.to_numpy(dtype=float) - y_predicted
    absolute_errors = np.abs(residuals)
    sign_mismatch = np.sign(y_true.to_numpy(dtype=float)) != np.sign(y_predicted)

    diagnostics: dict[str, Any] = {
        "residual_mean": float(np.mean(residuals)),
        "residual_standard_deviation": float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0,
        "residual_median": float(np.median(residuals)),
        "residual_min": float(np.min(residuals)),
        "residual_max": float(np.max(residuals)),
        "absolute_error_mean": float(np.mean(absolute_errors)),
        "absolute_error_median": float(np.median(absolute_errors)),
        "wrong_profit_sign_share": float(np.mean(sign_mismatch)),
    }
    for percentile in (10, 25, 50, 75, 90):
        diagnostics[f"residual_p{percentile}"] = float(np.percentile(residuals, percentile))
        diagnostics[f"absolute_error_p{percentile}"] = float(np.percentile(absolute_errors, percentile))

    return diagnostics


def select_best_candidate(candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the validation-best candidate using RMSE, then MAE."""
    if not candidate_results:
        raise ValueError("No AO2 Gradient Boosting candidate results were generated.")

    return sorted(
        candidate_results,
        key=lambda result: (
            result["validation_metrics"][PRIMARY_SELECTION_METRIC],
            result["validation_metrics"][SECONDARY_SELECTION_METRIC],
            result["candidate_rank_input_order"],
        ),
    )[0]


def save_validation_metrics_csv(candidate_results: list[dict[str, Any]], path: Path) -> None:
    """Write one row per candidate validation result."""
    rows = []
    for result in candidate_results:
        metrics = result["validation_metrics"]
        rows.append(
            {
                "model_name": MODEL_NAME,
                "candidate_name": result["candidate_id"],
                "selected": result["selected"],
                "rmse": metrics["rmse"],
                "mae": metrics["mae"],
                "r2": metrics["r2"],
                "median_absolute_error": metrics["median_absolute_error"],
                "mean_error_bias": metrics["mean_error_bias"],
                "validation_rows": metrics["validation_row_count"],
                "target_mean": metrics["target_mean"],
                "target_standard_deviation": metrics["target_standard_deviation"],
                "prediction_mean": metrics["prediction_mean"],
                "prediction_standard_deviation": metrics["prediction_standard_deviation"],
                "absolute_error_p50": metrics["absolute_error_p50"],
                "absolute_error_p90": metrics["absolute_error_p90"],
                "parameters_json": json.dumps(result["model_parameters"], sort_keys=True),
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def save_residual_diagnostics_csv(diagnostics: dict[str, Any], path: Path) -> None:
    """Write residual diagnostics in a compact report-friendly CSV format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"diagnostic": diagnostic_name, "value": diagnostic_value} for diagnostic_name, diagnostic_value in diagnostics.items()]
    ).to_csv(path, index=False)


def save_validation_predictions(
    validation_pdf: pd.DataFrame,
    y_predicted: np.ndarray,
    candidate_name: str,
    evaluation_slice: str,
    path: Path,
) -> None:
    """Write selected validation prediction records for downstream AO2 comparison."""
    prediction_df = validation_pdf.loc[
        :,
        [
            "Order_Id",
            "Order_Item_Id",
            "order_date_DateOrders",
            ROW_NUMBER_COLUMN,
            PARTITION_COLUMN,
            TARGET_COLUMN,
        ],
    ].copy()
    prediction_df["model_name"] = MODEL_NAME
    prediction_df["candidate_name"] = candidate_name
    prediction_df["evaluation_slice"] = evaluation_slice
    prediction_df["predicted_profit"] = y_predicted
    prediction_df["residual"] = prediction_df[TARGET_COLUMN] - prediction_df["predicted_profit"]
    prediction_df["absolute_error"] = prediction_df["residual"].abs()

    output_columns = [
        "model_name",
        "candidate_name",
        "Order_Id",
        "Order_Item_Id",
        "order_date_DateOrders",
        "evaluation_slice",
        ROW_NUMBER_COLUMN,
        PARTITION_COLUMN,
        TARGET_COLUMN,
        "predicted_profit",
        "residual",
        "absolute_error",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    prediction_df.to_csv(path, index=False, columns=output_columns)


def extract_feature_importance(pipeline: Any) -> pd.DataFrame:
    """Extract model-specific feature importances for the selected XGBoost model."""
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    importance_df = pd.DataFrame(
        {
            "model_name": MODEL_NAME,
            "feature_name": preprocessor.get_feature_names_out(),
            "importance_type": "gain_normalized",
            "importance_value": model.feature_importances_,
        }
    )
    importance_df = importance_df.sort_values(
        ["importance_value", "feature_name"],
        ascending=[False, True],
    ).reset_index(drop=True)
    importance_df["importance_rank"] = importance_df.index + 1
    return importance_df


def read_ridge_metrics(path: Path) -> dict[str, float] | None:
    """Read Ridge validation metrics when the baseline artifact is available."""
    if not path.exists():
        return None

    ridge_df = pd.read_csv(path)
    if not {"metric", "value"}.issubset(ridge_df.columns):
        return None

    metrics: dict[str, float] = {}
    for _, row in ridge_df.iterrows():
        metric_name = str(row["metric"])
        try:
            metrics[metric_name] = float(row["value"])
        except (TypeError, ValueError):
            continue
    return metrics


def build_model_comparison(
    selected_candidate: dict[str, Any],
    config: AO2GradientBoostingRegressorConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build a compact validation-only comparison against Ridge if available."""
    selected_metrics = selected_candidate["validation_metrics"]
    comparison_rows = [
        {
            "model_name": MODEL_NAME,
            "model_type": "xgboost.XGBRegressor",
            "candidate_name": selected_candidate["candidate_id"],
            "rmse": selected_metrics["rmse"],
            "mae": selected_metrics["mae"],
            "r2": selected_metrics["r2"],
            "median_absolute_error": selected_metrics["median_absolute_error"],
            "mean_error": selected_metrics["mean_error_bias"],
            "validation_rows": selected_metrics["validation_row_count"],
            "final_test_used": False,
        }
    ]

    ridge_metrics = read_ridge_metrics(config.ridge_validation_metrics_csv_path)
    comparison_metadata: dict[str, Any] = {
        "ridge_metrics_path": str(config.ridge_validation_metrics_csv_path),
        "ridge_metrics_available": ridge_metrics is not None,
        "comparison_complete": False,
        "h2_language_boundary": (
            "Validation comparison can be described as evidence consistent or not consistent "
            "with H2, but final H2 confirmation is deferred to later final-test evaluation."
        ),
    }

    if ridge_metrics is not None:
        comparison_rows.append(
            {
                "model_name": "ao2_ridge_baseline",
                "model_type": "sklearn.linear_model.Ridge",
                "candidate_name": "fixed_alpha_1_0",
                "rmse": ridge_metrics.get("rmse"),
                "mae": ridge_metrics.get("mae"),
                "r2": ridge_metrics.get("r2"),
                "median_absolute_error": ridge_metrics.get("median_absolute_error"),
                "mean_error": ridge_metrics.get("mean_error_bias"),
                "validation_rows": int(ridge_metrics.get("validation_row_count", 0)),
                "final_test_used": False,
            }
        )
        comparison_metadata.update(
            {
                "comparison_complete": True,
                "ridge_rmse": ridge_metrics.get("rmse"),
                "ridge_mae": ridge_metrics.get("mae"),
                "gradient_boosting_rmse": selected_metrics["rmse"],
                "gradient_boosting_mae": selected_metrics["mae"],
                "rmse_improvement_vs_ridge": (
                    ridge_metrics["rmse"] - selected_metrics["rmse"]
                    if "rmse" in ridge_metrics
                    else None
                ),
                "mae_improvement_vs_ridge": (
                    ridge_metrics["mae"] - selected_metrics["mae"]
                    if "mae" in ridge_metrics
                    else None
                ),
                "validation_evidence_consistent_with_h2": (
                    selected_metrics["rmse"] < ridge_metrics.get("rmse", float("inf"))
                    and selected_metrics["mae"] < ridge_metrics.get("mae", float("inf"))
                ),
            }
        )

    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df = comparison_df.sort_values(["rmse", "mae", "model_name"], ascending=[True, True, True])
    return comparison_df, comparison_metadata


def build_metadata(
    config: AO2GradientBoostingRegressorConfig,
    preprocessing_metadata: dict[str, Any] | None,
    partition_labels: set[str],
    partition_counts: dict[str, int],
    split_metadata: dict[str, Any],
    train_pdf: pd.DataFrame,
    validation_pdf: pd.DataFrame,
    candidate_results: list[dict[str, Any]],
    selected_candidate: dict[str, Any],
    selected_pipeline: Any,
    residual_diagnostics: dict[str, Any],
    comparison_metadata: dict[str, Any],
    model_artifact_saved: bool,
    feature_importance_created: bool,
) -> dict[str, Any]:
    """Build reproducibility metadata for AO2 Gradient Boosting."""
    preprocessor = selected_pipeline.named_steps["preprocessor"]
    model = selected_pipeline.named_steps["model"]

    return {
        "metadata_status": "runtime_training_completed",
        "issue": "#36",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_partition_path": config.partition_input_path,
        "input_partition_read_format": config.read_format,
        "partition_column": PARTITION_COLUMN,
        "partition_labels_observed": sorted(partition_labels),
        "partition_row_counts": partition_counts,
        "split_metadata": split_metadata,
        "training_slice_summary": date_range_summary(train_pdf),
        "validation_slice_summary": date_range_summary(validation_pdf),
        "final_test_partition_status": {
            "label": TEST_LABEL,
            "used_for_training": False,
            "used_for_preprocessing_fit": False,
            "used_for_validation_metrics": False,
            "used_for_residual_diagnostics": False,
            "used_for_model_selection": False,
            "used_for_predictions": False,
            "treatment": "reserved for final AO2 model evaluation; not touched by issue #36",
        },
        "target_column": TARGET_COLUMN,
        "target_transformation": "none",
        "feature_columns": list(FEATURE_COLUMNS),
        "excluded_identifier_metadata_columns": list(EXCLUDED_IDENTIFIER_METADATA_COLUMNS),
        "forbidden_target_reconstruction_columns": list(FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS),
        "forbidden_leakage_columns": list(FORBIDDEN_LEAKAGE_COLUMNS),
        "ao3_order_value_excluded_as_predictor": "ao3_order_value" not in FEATURE_COLUMNS,
        "feature_count_before_preprocessing": len(FEATURE_COLUMNS),
        "feature_count_after_preprocessing": int(len(preprocessor.get_feature_names_out())),
        "preprocessing_reference": {
            "factory": "src.modeling.build_ao2_preprocessing_pipeline.build_sklearn_preprocessor",
            "metadata_path": str(config.preprocessing_metadata_path),
            "metadata_status": (
                preprocessing_metadata.get("metadata_status") if preprocessing_metadata else None
            ),
            "fit_scope": "fitted inside issue #36 on training slice only",
            "validation_transform_scope": "validation transformed with training-fitted preprocessing only",
            "test_transform_scope": "not transformed by this Gradient Boosting job",
        },
        "gradient_boosting_regressor": {
            "library": "xgboost.XGBRegressor",
            "library_version": get_package_version("xgboost"),
            "candidate_count": len(candidate_results),
            "candidate_ids": [result["candidate_id"] for result in candidate_results],
            "candidate_configurations": [
                {
                    "candidate_id": result["candidate_id"],
                    "parameters": result["model_parameters"],
                }
                for result in candidate_results
            ],
            "selection_metric_order": [
                PRIMARY_SELECTION_METRIC,
                SECONDARY_SELECTION_METRIC,
            ],
            "selection_metric": PRIMARY_SELECTION_METRIC,
            "secondary_selection_metric": SECONDARY_SELECTION_METRIC,
            "selected_candidate_id": selected_candidate["candidate_id"],
            "selected_parameters": model.get_params(deep=False),
            "tuning_scope": "small validation-only candidate comparison inside development",
            "broad_hyperparameter_tuning": False,
        },
        "candidate_results": candidate_results,
        "selected_candidate": selected_candidate["candidate_id"],
        "selection_metric": PRIMARY_SELECTION_METRIC,
        "validation_metrics": selected_candidate["validation_metrics"],
        "residual_diagnostics": residual_diagnostics,
        "comparison_against_ridge": comparison_metadata,
        "artifacts": {
            "metrics_json": str(config.metrics_json_path),
            "metadata_json": str(config.metadata_json_path),
            "validation_metrics_csv": str(config.validation_metrics_csv_path),
            "residual_diagnostics_csv": str(config.residual_diagnostics_csv_path),
            "validation_predictions_csv": str(config.validation_predictions_csv_path),
            "model_comparison_csv": str(config.model_comparison_csv_path),
            "feature_importance_csv": str(config.feature_importance_csv_path)
            if feature_importance_created
            else None,
            "feature_importance_created": feature_importance_created,
            "model_artifact_saved": model_artifact_saved,
            "model_artifact_path": config.model_artifact_path if model_artifact_saved else None,
        },
        "interpretability_notes": [
            "Feature importances are model-specific and computed in the preprocessed feature space.",
            "One-hot encoded categorical feature importances may be granular.",
            "XGBoost importances are associative and should not be interpreted causally.",
            "SHAP and broader explainability are intentionally outside issue #36.",
        ],
        "limitations": [
            "The final test partition is not used.",
            "The target remains raw Order_Profit_Per_Order; no log transform is applied.",
            "The model excludes ao3_order_value and target-reconstruction fields from AO2 predictors.",
            "Only a small validation-only candidate set is compared; this is not exhaustive optimization.",
            "No AO3 margin scoring or risk-margin segmentation is implemented in this issue.",
        ],
        "versions": {
            "python": sys.version.split()[0],
            "numpy": get_package_version("numpy"),
            "pandas": get_package_version("pandas"),
            "sklearn": get_package_version("scikit-learn"),
            "pyspark": get_package_version("pyspark"),
            "joblib": get_package_version("joblib"),
            "xgboost": get_package_version("xgboost"),
        },
    }


def run_ao2_gradient_boosting_regressor(
    config: AO2GradientBoostingRegressorConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Train and validate the AO2 Gradient Boosting regressor."""
    logger.info("Starting AO2 Gradient Boosting training.")
    logger.info("AO2 partition input path: %s", config.partition_input_path)
    logger.info("Metrics output path: %s", config.metrics_json_path)
    logger.info("Metadata output path: %s", config.metadata_json_path)

    validate_volume_path(config.partition_input_path, "partition_input_path")
    assert_feature_list_is_safe()

    spark = get_spark_session()
    partitioned_df = spark.read.format(config.read_format).load(config.partition_input_path)
    assert_required_columns_exist(partitioned_df)
    assert_target_contract(partitioned_df)
    assert_unique_keys(partitioned_df)

    partition_labels = collect_partition_labels(partitioned_df)
    partition_counts = collect_partition_counts(partitioned_df)
    train_pdf, validation_pdf, split_metadata = determine_modeling_slices(partitioned_df, config)
    preprocessing_metadata = read_optional_json(config.preprocessing_metadata_path)

    x_train = train_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_train = train_pdf[TARGET_COLUMN].astype(float)
    x_validation = validation_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_validation = validation_pdf[TARGET_COLUMN].astype(float)

    candidate_parameters = build_candidate_parameter_sets(config)
    candidate_results: list[dict[str, Any]] = []
    candidate_pipelines: dict[str, Any] = {}
    candidate_predictions: dict[str, np.ndarray] = {}

    for rank, parameters in enumerate(candidate_parameters, start=1):
        candidate_id = parameters["candidate_id"]
        logger.info("Training AO2 Gradient Boosting candidate: %s", candidate_id)
        pipeline = build_xgboost_pipeline(parameters)
        pipeline.fit(x_train, y_train)

        y_validation_predicted = pipeline.predict(x_validation)
        metrics = evaluate_validation_predictions(y_validation, y_validation_predicted)
        candidate_results.append(
            {
                "candidate_id": candidate_id,
                "candidate_rank_input_order": rank,
                "selected": False,
                "model_parameters": {
                    key: value
                    for key, value in parameters.items()
                    if key != "candidate_id"
                },
                "validation_metrics": metrics,
            }
        )
        candidate_pipelines[candidate_id] = pipeline
        candidate_predictions[candidate_id] = y_validation_predicted
        logger.info(
            "Candidate %s validation RMSE: %.6f; MAE: %.6f",
            candidate_id,
            metrics["rmse"],
            metrics["mae"],
        )

    selected_candidate = select_best_candidate(candidate_results)
    selected_candidate["selected"] = True
    selected_candidate_id = selected_candidate["candidate_id"]
    selected_pipeline = candidate_pipelines[selected_candidate_id]
    selected_predictions = candidate_predictions[selected_candidate_id]
    logger.info("Selected AO2 Gradient Boosting candidate: %s", selected_candidate_id)

    residual_diagnostics = build_residual_diagnostics(y_validation, selected_predictions)

    feature_importance_df = extract_feature_importance(selected_pipeline)
    config.feature_importance_csv_path.parent.mkdir(parents=True, exist_ok=True)
    feature_importance_df.to_csv(config.feature_importance_csv_path, index=False)
    feature_importance_created = True

    save_validation_predictions(
        validation_pdf,
        selected_predictions,
        selected_candidate_id,
        str(split_metadata["validation_slice"]),
        config.validation_predictions_csv_path,
    )
    save_validation_metrics_csv(candidate_results, config.validation_metrics_csv_path)
    save_residual_diagnostics_csv(residual_diagnostics, config.residual_diagnostics_csv_path)
    save_json(selected_candidate["validation_metrics"], config.metrics_json_path)

    comparison_df, comparison_metadata = build_model_comparison(selected_candidate, config)
    config.model_comparison_csv_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(config.model_comparison_csv_path, index=False)

    model_artifact_saved = False
    if config.save_fitted_model:
        save_model_artifact(selected_pipeline, config.model_artifact_path)
        model_artifact_saved = True

    metadata = build_metadata(
        config,
        preprocessing_metadata,
        partition_labels,
        partition_counts,
        split_metadata,
        train_pdf,
        validation_pdf,
        candidate_results,
        selected_candidate,
        selected_pipeline,
        residual_diagnostics,
        comparison_metadata,
        model_artifact_saved,
        feature_importance_created,
    )
    save_json(metadata, config.metadata_json_path)

    metrics = selected_candidate["validation_metrics"]
    logger.info("AO2 Gradient Boosting validation RMSE: %.6f", metrics["rmse"])
    logger.info("AO2 Gradient Boosting validation MAE: %.6f", metrics["mae"])
    logger.info("AO2 Gradient Boosting validation R2: %.6f", metrics["r2"])
    logger.info("AO2 Gradient Boosting training completed successfully.")
    return metadata


def main() -> None:
    """Run AO2 Gradient Boosting training with default configuration."""
    run_ao2_gradient_boosting_regressor(
        AO2GradientBoostingRegressorConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
