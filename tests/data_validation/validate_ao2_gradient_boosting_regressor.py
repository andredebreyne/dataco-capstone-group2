"""Validate AO2 Gradient Boosting regressor artifacts.

Run this script after `src/modeling/train_ao2_gradient_boosting_regressor.py`
has completed. It validates lightweight JSON/CSV artifacts and documented
fit, validation, model-selection, and comparison boundaries; it does not
retrain the model.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any


TARGET_COLUMN = "Order_Profit_Per_Order"
TEST_LABEL = "test"
MODEL_NAME = "ao2_gradient_boosting_regressor"

IDENTIFIER_METADATA_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    "_gold_ao2_processed_timestamp",
}

FORBIDDEN_AO2_PREDICTOR_COLUMNS = {
    TARGET_COLUMN,
    "Order Profit Per Order",
    "Benefit_per_order",
    "Benefit per order",
    "Order_Item_Profit_Ratio",
    "Order Item Profit Ratio",
    "Order_Item_Total",
    "Order Item Total",
    "ao3_order_value",
    "Sales",
    "Sales_per_customer",
    "Sales per customer",
    "Order_Item_Discount",
    "Order Item Discount",
    "Product_Price",
    "Product Price",
    "Delivery_Status",
    "Delivery Status",
    "Days_for_shipping_real",
    "Days for shipping (real)",
    "shipping_date_DateOrders",
    "shipping date (DateOrders)",
    "Order_Status",
    "Order Status",
    "Late_delivery_risk",
}

REQUIRED_METADATA_KEYS = {
    "metadata_status",
    "issue",
    "input_partition_path",
    "partition_column",
    "partition_labels_observed",
    "partition_row_counts",
    "split_metadata",
    "training_slice_summary",
    "validation_slice_summary",
    "final_test_partition_status",
    "target_column",
    "target_transformation",
    "feature_columns",
    "forbidden_target_reconstruction_columns",
    "forbidden_leakage_columns",
    "ao3_order_value_excluded_as_predictor",
    "feature_count_before_preprocessing",
    "feature_count_after_preprocessing",
    "preprocessing_reference",
    "gradient_boosting_regressor",
    "candidate_results",
    "selected_candidate",
    "selection_metric",
    "validation_metrics",
    "residual_diagnostics",
    "comparison_against_ridge",
    "artifacts",
    "versions",
}

REQUIRED_METRICS = {
    "rmse",
    "mae",
    "r2",
    "median_absolute_error",
    "mean_error_bias",
    "validation_row_count",
    "target_mean",
    "target_standard_deviation",
    "prediction_mean",
    "prediction_standard_deviation",
}

NON_NEGATIVE_METRICS = {
    "rmse",
    "mae",
    "median_absolute_error",
    "target_standard_deviation",
    "prediction_standard_deviation",
}

REQUIRED_RESIDUAL_DIAGNOSTICS = {
    "residual_mean",
    "residual_standard_deviation",
    "residual_median",
    "residual_min",
    "residual_max",
    "absolute_error_mean",
    "absolute_error_median",
    "wrong_profit_sign_share",
    "residual_p10",
    "residual_p25",
    "residual_p50",
    "residual_p75",
    "residual_p90",
    "absolute_error_p10",
    "absolute_error_p25",
    "absolute_error_p50",
    "absolute_error_p75",
    "absolute_error_p90",
}

REQUIRED_XGBOOST_PARAMETERS = {
    "objective",
    "eval_metric",
    "tree_method",
    "random_state",
    "n_jobs",
    "n_estimators",
    "max_depth",
    "learning_rate",
    "subsample",
    "colsample_bytree",
}

REQUIRED_VALIDATION_METRICS_COLUMNS = {
    "model_name",
    "candidate_name",
    "selected",
    "rmse",
    "mae",
    "r2",
    "median_absolute_error",
    "mean_error_bias",
    "validation_rows",
    "parameters_json",
}

REQUIRED_PREDICTION_COLUMNS = {
    "model_name",
    "candidate_name",
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "evaluation_slice",
    TARGET_COLUMN,
    "predicted_profit",
    "residual",
    "absolute_error",
}

REQUIRED_COMPARISON_COLUMNS = {
    "model_name",
    "model_type",
    "candidate_name",
    "rmse",
    "mae",
    "r2",
    "median_absolute_error",
    "mean_error",
    "validation_rows",
    "final_test_used",
}

REQUIRED_FEATURE_IMPORTANCE_COLUMNS = {
    "model_name",
    "feature_name",
    "importance_type",
    "importance_value",
    "importance_rank",
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
        if (candidate / "models").exists() and (candidate / "src").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "ao2_profitability" / "gradient_boosting"

METRICS_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_METRICS_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_gradient_boosting_metrics.json"),
    )
)
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_gradient_boosting_metadata.json"),
    )
)
VALIDATION_METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_validation_metrics.csv"),
    )
)
RESIDUAL_DIAGNOSTICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_RESIDUAL_DIAGNOSTICS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_residual_diagnostics.csv"),
    )
)
VALIDATION_PREDICTIONS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_VALIDATION_PREDICTIONS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_validation_predictions.csv"),
    )
)
MODEL_COMPARISON_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_MODEL_VALIDATION_COMPARISON_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_model_validation_comparison.csv"),
    )
)
FEATURE_IMPORTANCE_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_FEATURE_IMPORTANCE_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_gradient_boosting_feature_importance.csv"),
    )
)


def normalize_column_name(column_name: str) -> str:
    """Return a loose normalized name for leakage-list comparisons."""
    return (
        column_name.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
    )


def read_json(path: Path) -> dict[str, Any]:
    """Read a required JSON artifact."""
    assert path.exists(), f"Missing required artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read rows from a required CSV artifact."""
    assert path.exists(), f"Missing required CSV artifact: {path}"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_required_metadata(metadata: dict[str, Any]) -> None:
    """Validate required metadata fields and completed runtime status."""
    missing_keys = sorted(REQUIRED_METADATA_KEYS.difference(metadata))
    assert not missing_keys, f"AO2 Gradient Boosting metadata is missing keys: {missing_keys}"
    assert metadata["metadata_status"] == "runtime_training_completed", (
        "AO2 Gradient Boosting metadata must come from a completed training run."
    )
    assert metadata["issue"] == "#36", f"Unexpected issue reference: {metadata['issue']}"


def assert_metrics_present(metrics: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Validate required metric keys exist in both metrics and metadata artifacts."""
    missing_metrics = sorted(REQUIRED_METRICS.difference(metrics))
    assert not missing_metrics, f"AO2 Gradient Boosting metrics missing keys: {missing_metrics}"
    assert metadata["validation_metrics"] == metrics, (
        "Metadata validation_metrics must match the standalone metrics JSON."
    )


def assert_metric_ranges(metrics: dict[str, Any]) -> None:
    """Validate regression metric values are numeric and in expected ranges."""
    for metric_name in REQUIRED_METRICS:
        value = metrics[metric_name]
        assert isinstance(value, (int, float)) and math.isfinite(value), (
            f"{metric_name} must be finite numeric. Found: {value}"
        )

    for metric_name in NON_NEGATIVE_METRICS:
        assert metrics[metric_name] >= 0.0, (
            f"{metric_name} must be non-negative. Found: {metrics[metric_name]}"
        )

    assert isinstance(metrics["validation_row_count"], int), "validation_row_count must be an integer."
    assert metrics["validation_row_count"] > 0, "validation_row_count must be positive."


def assert_split_and_test_usage(metadata: dict[str, Any]) -> None:
    """Validate training, validation, and model-selection slices exclude final test."""
    partition_labels = set(metadata["partition_labels_observed"])
    assert TEST_LABEL in partition_labels, "Final test partition label is not documented."

    split_metadata = metadata["split_metadata"]
    assert split_metadata["final_test_used"] is False, "Split metadata says final test was used."
    assert split_metadata["training_slice"] != TEST_LABEL, "Training slice must not be final test."
    assert split_metadata["validation_slice"] != TEST_LABEL, "Validation slice must not be final test."

    final_test_status = metadata["final_test_partition_status"]
    assert final_test_status["label"] == TEST_LABEL, "Final test status must document the test label."
    assert final_test_status["used_for_training"] is False, "Final test was used for training."
    assert final_test_status["used_for_preprocessing_fit"] is False, (
        "Final test was used for preprocessing fit."
    )
    assert final_test_status["used_for_validation_metrics"] is False, (
        "Final test was used for validation metrics."
    )
    assert final_test_status["used_for_residual_diagnostics"] is False, (
        "Final test was used for residual diagnostics."
    )
    assert final_test_status["used_for_model_selection"] is False, (
        "Final test was used for model selection."
    )
    assert final_test_status["used_for_predictions"] is False, (
        "Final test was used for prediction export."
    )


def assert_feature_list_is_safe(metadata: dict[str, Any]) -> None:
    """Validate target, identifiers, AO3 support, and forbidden fields are not predictors."""
    assert metadata["target_column"] == TARGET_COLUMN, (
        f"Unexpected target column: {metadata['target_column']}"
    )
    assert metadata["target_transformation"] == "none", "AO2 model must use the raw target."

    feature_columns = set(metadata["feature_columns"])
    assert TARGET_COLUMN not in feature_columns, "Target column is present in feature list."
    assert "ao3_order_value" not in feature_columns, (
        "ao3_order_value is an AO3 support denominator and must not be an AO2 predictor."
    )
    assert metadata["ao3_order_value_excluded_as_predictor"] is True, (
        "Metadata must confirm ao3_order_value is excluded as a predictor."
    )

    identifier_overlap = sorted(feature_columns.intersection(IDENTIFIER_METADATA_COLUMNS))
    assert not identifier_overlap, (
        f"Identifier, partition, or metadata columns found in features: {identifier_overlap}"
    )

    forbidden_columns = (
        FORBIDDEN_AO2_PREDICTOR_COLUMNS
        .union(metadata["forbidden_target_reconstruction_columns"])
        .union(metadata["forbidden_leakage_columns"])
    )
    forbidden_normalized = {normalize_column_name(column_name) for column_name in forbidden_columns}
    feature_normalized = {normalize_column_name(column_name) for column_name in feature_columns}
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    assert not forbidden_overlap, f"Forbidden AO2 predictor columns found in features: {forbidden_overlap}"

    assert metadata["feature_count_before_preprocessing"] == len(feature_columns), (
        "Feature count before preprocessing does not match the documented feature list."
    )
    assert metadata["feature_count_after_preprocessing"] >= metadata["feature_count_before_preprocessing"], (
        "Preprocessed feature count should be at least the original approved feature count."
    )


def assert_preprocessing_policy(metadata: dict[str, Any]) -> None:
    """Validate preprocessing reference and fit scope."""
    preprocessing_reference = metadata["preprocessing_reference"]
    assert "build_sklearn_preprocessor" in preprocessing_reference["factory"], (
        "Metadata must reference the approved AO2 preprocessing factory."
    )
    assert preprocessing_reference["fit_scope"] == "fitted inside issue #36 on training slice only", (
        "Preprocessing fit scope must be training-slice only."
    )
    assert preprocessing_reference["test_transform_scope"] == "not transformed by this Gradient Boosting job", (
        "The Gradient Boosting job must not transform or score the final test partition."
    )


def assert_xgboost_selection(metadata: dict[str, Any]) -> None:
    """Validate XGBoost candidate comparison and selected configuration metadata."""
    model_metadata = metadata["gradient_boosting_regressor"]
    assert model_metadata["library"] == "xgboost.XGBRegressor", (
        f"Unexpected model library: {model_metadata['library']}"
    )
    assert model_metadata["candidate_count"] == len(metadata["candidate_results"]), (
        "Candidate count does not match candidate_results length."
    )
    assert model_metadata["candidate_count"] >= 1, "At least one candidate is required."
    assert model_metadata["selection_metric_order"] == ["rmse", "mae"], (
        "Selection metric order must remain RMSE followed by MAE."
    )
    assert model_metadata["selection_metric"] == "rmse", "Primary selection metric must be RMSE."
    assert metadata["selection_metric"] == "rmse", "Top-level selection metric must be RMSE."
    assert "validation-only" in model_metadata["tuning_scope"], (
        "Gradient Boosting tuning scope must be validation-only inside development."
    )
    assert model_metadata["broad_hyperparameter_tuning"] is False, (
        "Issue #36 must not run broad hyperparameter tuning."
    )

    selected_candidate_id = model_metadata["selected_candidate_id"]
    assert metadata["selected_candidate"] == selected_candidate_id, (
        "Top-level selected_candidate does not match model metadata."
    )

    candidate_ids = [candidate["candidate_id"] for candidate in metadata["candidate_results"]]
    assert selected_candidate_id in candidate_ids, (
        f"Selected candidate {selected_candidate_id} is absent from candidate_results."
    )

    selected_candidates = [
        candidate for candidate in metadata["candidate_results"] if candidate["selected"] is True
    ]
    assert len(selected_candidates) == 1, (
        f"Exactly one candidate must be selected. Found: {len(selected_candidates)}"
    )
    assert selected_candidates[0]["candidate_id"] == selected_candidate_id, (
        "Selected candidate flag does not match selected_candidate_id."
    )

    assert model_metadata["candidate_configurations"], "Candidate configurations must be documented."
    for candidate in metadata["candidate_results"]:
        assert "validation_metrics" in candidate, (
            f"Candidate {candidate['candidate_id']} is missing validation metrics."
        )
        assert "model_parameters" in candidate, (
            f"Candidate {candidate['candidate_id']} is missing model parameters."
        )
        assert_metric_ranges(candidate["validation_metrics"])
        parameters = candidate["model_parameters"]
        missing_parameters = sorted(REQUIRED_XGBOOST_PARAMETERS.difference(parameters))
        assert not missing_parameters, (
            f"Candidate {candidate['candidate_id']} parameters missing: {missing_parameters}"
        )
        assert parameters["objective"] == "reg:squarederror", (
            f"Unexpected objective: {parameters['objective']}"
        )
        assert parameters["eval_metric"] == "rmse", (
            f"Unexpected eval_metric: {parameters['eval_metric']}"
        )
        assert parameters["random_state"] == 42, (
            f"Unexpected random_state: {parameters['random_state']}"
        )


def assert_residual_diagnostics(metadata: dict[str, Any]) -> None:
    """Validate residual diagnostics are present and numeric."""
    diagnostics = metadata["residual_diagnostics"]
    missing = sorted(REQUIRED_RESIDUAL_DIAGNOSTICS.difference(diagnostics))
    assert not missing, f"Residual diagnostics missing keys: {missing}"
    for diagnostic_name in REQUIRED_RESIDUAL_DIAGNOSTICS:
        value = diagnostics[diagnostic_name]
        assert isinstance(value, (int, float)) and math.isfinite(value), (
            f"{diagnostic_name} must be finite numeric. Found: {value}"
        )
    assert 0.0 <= diagnostics["wrong_profit_sign_share"] <= 1.0, (
        "wrong_profit_sign_share must be between 0 and 1."
    )


def assert_validation_metrics_csv(metadata: dict[str, Any]) -> None:
    """Validate candidate validation metrics table."""
    rows = read_csv_rows(VALIDATION_METRICS_CSV_PATH)
    assert rows, "Validation metrics CSV must contain rows."
    header = set(rows[0])
    missing_columns = sorted(REQUIRED_VALIDATION_METRICS_COLUMNS.difference(header))
    assert not missing_columns, f"Validation metrics table missing columns: {missing_columns}"
    assert len(rows) == metadata["gradient_boosting_regressor"]["candidate_count"], (
        "Validation metrics row count must match candidate count."
    )
    selected_rows = [row for row in rows if row["selected"].strip().lower() == "true"]
    assert len(selected_rows) == 1, (
        f"Validation metrics CSV must have exactly one selected row. Found: {len(selected_rows)}"
    )
    assert selected_rows[0]["candidate_name"] == metadata["selected_candidate"], (
        "Validation metrics selected row does not match metadata."
    )


def assert_residual_diagnostics_csv_exists() -> None:
    """Validate report-facing residual diagnostics CSV exists."""
    rows = read_csv_rows(RESIDUAL_DIAGNOSTICS_CSV_PATH)
    assert rows, "Residual diagnostics CSV must contain rows."
    header = set(rows[0])
    assert {"diagnostic", "value"}.issubset(header), (
        "Residual diagnostics CSV must include diagnostic and value columns."
    )


def assert_prediction_rows(metrics: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Validate validation prediction rows, numeric fields, and row counts."""
    rows = read_csv_rows(VALIDATION_PREDICTIONS_CSV_PATH)
    assert rows, "Validation predictions CSV must contain rows."

    header = set(rows[0])
    missing_columns = sorted(REQUIRED_PREDICTION_COLUMNS.difference(header))
    assert not missing_columns, f"Validation predictions missing columns: {missing_columns}"

    evaluation_slices = {row["evaluation_slice"] for row in rows}
    assert TEST_LABEL not in evaluation_slices, "Validation predictions include final test rows."

    for row_index, row in enumerate(rows, start=2):
        assert row["model_name"] == MODEL_NAME, f"Unexpected model_name at CSV row {row_index}."
        assert row["candidate_name"] == metadata["selected_candidate"], (
            f"Unexpected candidate_name at CSV row {row_index}."
        )
        for column_name in (TARGET_COLUMN, "predicted_profit", "residual", "absolute_error"):
            value = row[column_name]
            assert value != "", f"{column_name} must be non-null at CSV row {row_index}."
            numeric_value = float(value)
            assert math.isfinite(numeric_value), (
                f"{column_name} must be finite numeric at CSV row {row_index}. Found: {value}"
            )

    prediction_row_count = len(rows)
    assert prediction_row_count == metrics["validation_row_count"], (
        "Prediction row count must match metrics validation_row_count. "
        f"Predictions: {prediction_row_count}; metrics: {metrics['validation_row_count']}."
    )
    assert prediction_row_count == metadata["validation_slice_summary"]["row_count"], (
        "Prediction row count must match metadata validation slice row count."
    )


def assert_model_comparison(metadata: dict[str, Any]) -> None:
    """Validate Ridge comparison table or documented incomplete comparison state."""
    comparison_metadata = metadata["comparison_against_ridge"]
    assert "ridge_metrics_available" in comparison_metadata, (
        "Metadata must state whether Ridge metrics were available."
    )
    assert "comparison_complete" in comparison_metadata, (
        "Metadata must state whether the Ridge comparison is complete."
    )

    rows = read_csv_rows(MODEL_COMPARISON_CSV_PATH)
    assert rows, "AO2 model comparison CSV must contain at least the Gradient Boosting row."
    header = set(rows[0])
    missing_columns = sorted(REQUIRED_COMPARISON_COLUMNS.difference(header))
    assert not missing_columns, f"AO2 model comparison table missing columns: {missing_columns}"

    model_names = {row["model_name"] for row in rows}
    assert MODEL_NAME in model_names, "Comparison table must include Gradient Boosting."
    if comparison_metadata["ridge_metrics_available"]:
        assert comparison_metadata["comparison_complete"] is True, (
            "Comparison must be complete when Ridge metrics are available."
        )
        assert "ao2_ridge_baseline" in model_names, "Comparison table must include Ridge baseline."
        assert "validation_evidence_consistent_with_h2" in comparison_metadata, (
            "Completed comparison must document whether validation evidence is consistent with H2."
        )
    else:
        assert comparison_metadata["comparison_complete"] is False, (
            "Comparison must be marked incomplete when Ridge metrics are unavailable."
        )

    for row_index, row in enumerate(rows, start=2):
        assert row["final_test_used"].strip().lower() == "false", (
            f"Final test use must be false in comparison row {row_index}."
        )
        for column_name in ("rmse", "mae", "r2", "median_absolute_error", "mean_error"):
            numeric_value = float(row[column_name])
            assert math.isfinite(numeric_value), (
                f"{column_name} must be finite numeric in comparison row {row_index}."
            )


def assert_feature_importance(metadata: dict[str, Any]) -> None:
    """Validate feature-importance artifact when metadata says it was created."""
    artifacts = metadata["artifacts"]
    if not artifacts["feature_importance_created"]:
        return

    rows = read_csv_rows(FEATURE_IMPORTANCE_CSV_PATH)
    assert rows, "Feature-importance table must contain rows."
    header = set(rows[0])
    missing_columns = sorted(REQUIRED_FEATURE_IMPORTANCE_COLUMNS.difference(header))
    assert not missing_columns, f"Feature-importance table missing columns: {missing_columns}"
    assert len(rows) == metadata["feature_count_after_preprocessing"], (
        "Feature-importance row count must match preprocessed feature count."
    )

    previous_rank = 0
    for row_index, row in enumerate(rows, start=2):
        assert row["model_name"] == MODEL_NAME, f"Unexpected model_name at feature row {row_index}."
        importance_value = float(row["importance_value"])
        importance_rank = int(float(row["importance_rank"]))
        assert math.isfinite(importance_value), (
            f"importance_value must be finite at feature row {row_index}."
        )
        assert importance_value >= 0.0, (
            f"importance_value must be non-negative at feature row {row_index}."
        )
        assert importance_rank == previous_rank + 1, (
            f"importance_rank must be sequential at feature row {row_index}."
        )
        previous_rank = importance_rank


def print_validation_summary(metadata: dict[str, Any], metrics: dict[str, Any]) -> None:
    """Print a concise validation report."""
    print("\nAO2 Gradient Boosting validation summary:")
    print(f"- Metadata path: {METADATA_PATH}")
    print(f"- Metrics path: {METRICS_PATH}")
    print(f"- Input partition path: {metadata['input_partition_path']}")
    print(f"- Training slice: {metadata['split_metadata']['training_slice']}")
    print(f"- Validation slice: {metadata['split_metadata']['validation_slice']}")
    print("- Final test used: false")
    print(f"- Selected candidate: {metadata['selected_candidate']}")
    print(f"- RMSE: {metrics['rmse']:.6f}")
    print(f"- MAE: {metrics['mae']:.6f}")
    print(f"- R2: {metrics['r2']:.6f}")


def run_validation() -> None:
    """Run all AO2 Gradient Boosting artifact validations."""
    metrics = read_json(METRICS_PATH)
    metadata = read_json(METADATA_PATH)

    assert_required_metadata(metadata)
    assert_metrics_present(metrics, metadata)
    assert_metric_ranges(metrics)
    assert_split_and_test_usage(metadata)
    assert_feature_list_is_safe(metadata)
    assert_preprocessing_policy(metadata)
    assert_xgboost_selection(metadata)
    assert_residual_diagnostics(metadata)
    assert_validation_metrics_csv(metadata)
    assert_residual_diagnostics_csv_exists()
    assert_prediction_rows(metrics, metadata)
    assert_model_comparison(metadata)
    assert_feature_importance(metadata)

    print_validation_summary(metadata, metrics)
    print("\nAO2 Gradient Boosting validation passed.")


if __name__ == "__main__":
    run_validation()
