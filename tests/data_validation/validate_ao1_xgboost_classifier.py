"""Validate AO1 XGBoost classifier artifacts.

Run this script after `src/modeling/train_ao1_xgboost_classifier.py` has
completed. It validates lightweight JSON/CSV artifacts and the documented
fit, validation, and model-selection boundaries; it does not retrain the model.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any


TARGET_COLUMN = "Late_delivery_risk"
TEST_LABEL = "test"

IDENTIFIER_METADATA_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    "_gold_ao1_processed_timestamp",
}

FORBIDDEN_LEAKAGE_COLUMNS = {
    TARGET_COLUMN,
    "Delivery_Status",
    "Delivery Status",
    "Days_for_shipping_real",
    "Days for shipping (real)",
    "shipping_date_DateOrders",
    "shipping date (DateOrders)",
    "Order_Status",
    "Order Status",
    "Order_Profit_Per_Order",
    "Order Profit Per Order",
    "Benefit_per_order",
    "Benefit per order",
    "Order_Item_Profit_Ratio",
    "Order Item Profit Ratio",
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
    "feature_columns",
    "forbidden_leakage_columns",
    "feature_count_before_preprocessing",
    "feature_count_after_preprocessing",
    "preprocessing_reference",
    "smote",
    "xgboost_classifier",
    "candidate_results",
    "validation_metrics",
    "artifacts",
    "versions",
}

REQUIRED_METRICS = {
    "roc_auc",
    "pr_auc",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "log_loss",
    "validation_positive_class_rate",
    "validation_predicted_positive_rate_at_0_5",
    "threshold",
    "confusion_matrix",
}

UNIT_INTERVAL_METRICS = {
    "roc_auc",
    "pr_auc",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "validation_positive_class_rate",
    "validation_predicted_positive_rate_at_0_5",
    "threshold",
}

REQUIRED_CONFUSION_KEYS = {
    "true_negative",
    "false_positive",
    "false_negative",
    "true_positive",
}

REQUIRED_XGBOOST_PARAMETERS = {
    "objective",
    "eval_metric",
    "tree_method",
    "random_state",
    "n_jobs",
    "scale_pos_weight",
    "n_estimators",
    "max_depth",
    "learning_rate",
    "subsample",
    "colsample_bytree",
    "min_child_weight",
    "reg_lambda",
    "reg_alpha",
}

REQUIRED_CANDIDATE_COLUMNS = {
    "candidate_id",
    "selected",
    "roc_auc",
    "pr_auc",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "log_loss",
    "threshold",
    "parameters_json",
}

REQUIRED_FEATURE_IMPORTANCE_COLUMNS = {
    "feature_name",
    "importance_gain_proxy",
    "importance_share",
}

REQUIRED_VALIDATION_PREDICTION_COLUMNS = {
    "model_name",
    "evaluation_slice",
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    TARGET_COLUMN,
    "predicted_probability",
    "prediction_threshold",
    "predicted_label",
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
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "ao1_late_delivery" / "xgboost_classifier"

METRICS_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_METRICS_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao1_xgboost_classifier_metrics.json"),
    )
)
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao1_xgboost_classifier_metadata.json"),
    )
)
METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_classifier_validation_metrics.csv"),
    )
)
CANDIDATE_RESULTS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_CANDIDATE_RESULTS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_classifier_candidate_results.csv"),
    )
)
FEATURE_IMPORTANCE_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_FEATURE_IMPORTANCE_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_classifier_feature_importance.csv"),
    )
)
VALIDATION_PREDICTIONS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_VALIDATION_PREDICTIONS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_validation_predictions.csv"),
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


def assert_required_metadata(metadata: dict[str, Any]) -> None:
    """Validate required metadata fields and completed runtime status."""
    missing_keys = sorted(REQUIRED_METADATA_KEYS.difference(metadata))
    assert not missing_keys, f"AO1 XGBoost metadata is missing keys: {missing_keys}"
    assert metadata["metadata_status"] == "runtime_training_completed", (
        "AO1 XGBoost metadata must come from a completed training run."
    )
    assert metadata["issue"] == "#28", f"Unexpected issue reference: {metadata['issue']}"


def assert_metrics_present(metrics: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Validate required metric keys exist in both metrics and metadata artifacts."""
    missing_metrics = sorted(REQUIRED_METRICS.difference(metrics))
    assert not missing_metrics, f"AO1 XGBoost metrics missing keys: {missing_metrics}"
    assert metadata["validation_metrics"] == metrics, (
        "Metadata validation_metrics must match the standalone metrics JSON."
    )


def assert_metric_ranges(metrics: dict[str, Any]) -> None:
    """Validate metric values are numeric and in expected ranges."""
    for metric_name in UNIT_INTERVAL_METRICS:
        value = metrics[metric_name]
        assert isinstance(value, (int, float)) and math.isfinite(value), (
            f"{metric_name} must be a finite numeric value. Found: {value}"
        )
        assert 0.0 <= value <= 1.0, f"{metric_name} must be between 0 and 1. Found: {value}"

    log_loss_value = metrics["log_loss"]
    assert isinstance(log_loss_value, (int, float)) and math.isfinite(log_loss_value), (
        f"log_loss must be finite numeric. Found: {log_loss_value}"
    )
    assert log_loss_value >= 0.0, f"log_loss must be non-negative. Found: {log_loss_value}"

    confusion_matrix = metrics["confusion_matrix"]
    missing_confusion_keys = sorted(REQUIRED_CONFUSION_KEYS.difference(confusion_matrix))
    assert not missing_confusion_keys, f"Confusion matrix missing keys: {missing_confusion_keys}"
    for key in REQUIRED_CONFUSION_KEYS:
        value = confusion_matrix[key]
        assert isinstance(value, int) and value >= 0, (
            f"Confusion matrix value `{key}` must be a non-negative integer. Found: {value}"
        )


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
    assert final_test_status["used_for_model_selection"] is False, (
        "Final test was used for model selection."
    )
    assert final_test_status["used_for_threshold_selection"] is False, (
        "Final test was used for threshold selection."
    )


def assert_feature_list_is_safe(metadata: dict[str, Any]) -> None:
    """Validate target, identifiers, and forbidden leakage columns are not predictors."""
    assert metadata["target_column"] == TARGET_COLUMN, (
        f"Unexpected target column: {metadata['target_column']}"
    )

    feature_columns = set(metadata["feature_columns"])
    assert TARGET_COLUMN not in feature_columns, "Target column is present in feature list."

    identifier_overlap = sorted(feature_columns.intersection(IDENTIFIER_METADATA_COLUMNS))
    assert not identifier_overlap, (
        f"Identifier, partition, or metadata columns found in features: {identifier_overlap}"
    )

    forbidden_columns = set(FORBIDDEN_LEAKAGE_COLUMNS).union(metadata["forbidden_leakage_columns"])
    forbidden_normalized = {
        normalize_column_name(column_name)
        for column_name in forbidden_columns
    }
    feature_normalized = {
        normalize_column_name(column_name)
        for column_name in feature_columns
    }
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    assert not forbidden_overlap, f"Forbidden leakage columns found in features: {forbidden_overlap}"

    assert metadata["feature_count_before_preprocessing"] == len(feature_columns), (
        "Feature count before preprocessing does not match the documented feature list."
    )
    assert metadata["feature_count_after_preprocessing"] >= metadata["feature_count_before_preprocessing"], (
        "Preprocessed feature count should be at least the original approved feature count."
    )


def assert_preprocessing_and_smote_policy(metadata: dict[str, Any]) -> None:
    """Validate preprocessing reference and class-imbalance treatment."""
    preprocessing_reference = metadata["preprocessing_reference"]
    assert "build_sklearn_preprocessor" in preprocessing_reference["factory"], (
        "Metadata must reference the approved AO1 preprocessing factory."
    )
    assert preprocessing_reference["fit_scope"] == "fitted inside issue #28 on training slice only", (
        "Preprocessing fit scope must be training-slice only for issue #28."
    )

    smote = metadata["smote"]
    assert smote["used"] is False, "SMOTE should not be used for this XGBoost model."
    assert smote["validation_resampling_allowed"] is False, "SMOTE must not be allowed on validation."
    assert smote["test_resampling_allowed"] is False, "SMOTE must not be allowed on test."
    assert smote["training_only"] is True, "SMOTE policy must remain training-only."


def assert_xgboost_selection(metadata: dict[str, Any]) -> None:
    """Validate XGBoost candidate comparison and selected configuration metadata."""
    xgboost = metadata["xgboost_classifier"]
    assert xgboost["library"] == "xgboost.XGBClassifier", (
        f"Unexpected model library: {xgboost['library']}"
    )
    assert xgboost["candidate_count"] == len(metadata["candidate_results"]), (
        "Candidate count does not match candidate_results length."
    )
    assert xgboost["candidate_count"] >= 1, "At least one XGBoost candidate is required."
    assert xgboost["selection_metric_order"] == ["roc_auc", "recall"], (
        "Selection metric order must remain ROC-AUC followed by recall."
    )
    assert xgboost["threshold_tuning"] == "none", "Issue #28 must not tune thresholds."
    assert "validation-only" in xgboost["tuning_scope"], (
        "XGBoost tuning scope must be validation-only inside development."
    )

    selected_candidate_id = xgboost["selected_candidate_id"]
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

    parameters = xgboost["selected_parameters"]
    missing_parameters = sorted(REQUIRED_XGBOOST_PARAMETERS.difference(parameters))
    assert not missing_parameters, f"Selected XGBoost parameters missing: {missing_parameters}"
    assert parameters["objective"] == "binary:logistic", (
        f"Unexpected objective: {parameters['objective']}"
    )
    assert parameters["eval_metric"] == "logloss", (
        f"Unexpected eval_metric: {parameters['eval_metric']}"
    )
    assert parameters["random_state"] == 620, (
        f"Unexpected random_state: {parameters['random_state']}"
    )

    for candidate in metadata["candidate_results"]:
        assert "validation_metrics" in candidate, (
            f"Candidate {candidate['candidate_id']} is missing validation metrics."
        )
        assert "model_parameters" in candidate, (
            f"Candidate {candidate['candidate_id']} is missing model parameters."
        )
        assert_metric_ranges(candidate["validation_metrics"])


def read_csv_header(path: Path) -> list[str]:
    """Read a CSV header from a required artifact."""
    assert path.exists(), f"Missing required CSV artifact: {path}"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read required CSV artifact rows."""
    assert path.exists(), f"Missing required CSV artifact: {path}"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_metrics_csv_exists() -> None:
    """Validate the report-facing metrics CSV exists and has expected columns."""
    header = set(read_csv_header(METRICS_CSV_PATH))
    assert {"metric", "value"}.issubset(header), (
        f"Metrics CSV must include metric and value columns. Header: {sorted(header)}"
    )


def assert_candidate_results_table_exists(metadata: dict[str, Any]) -> None:
    """Validate candidate-comparison table exists and aligns with metadata."""
    header = set(read_csv_header(CANDIDATE_RESULTS_CSV_PATH))
    missing_columns = sorted(REQUIRED_CANDIDATE_COLUMNS.difference(header))
    assert not missing_columns, f"Candidate results table missing columns: {missing_columns}"

    rows = read_csv_rows(CANDIDATE_RESULTS_CSV_PATH)
    assert len(rows) == metadata["xgboost_classifier"]["candidate_count"], (
        "Candidate results CSV row count does not match metadata candidate count."
    )
    selected_rows = [row for row in rows if row["selected"].strip().lower() == "true"]
    assert len(selected_rows) == 1, (
        f"Candidate results CSV must have exactly one selected row. Found: {len(selected_rows)}"
    )
    assert selected_rows[0]["candidate_id"] == metadata["xgboost_classifier"]["selected_candidate_id"], (
        "Candidate results CSV selected row does not match metadata selected candidate."
    )


def assert_feature_importance_table_exists(metadata: dict[str, Any]) -> None:
    """Validate feature-importance table exists and includes expected fields."""
    header = set(read_csv_header(FEATURE_IMPORTANCE_CSV_PATH))
    missing_columns = sorted(REQUIRED_FEATURE_IMPORTANCE_COLUMNS.difference(header))
    assert not missing_columns, f"Feature-importance table missing columns: {missing_columns}"

    rows = read_csv_rows(FEATURE_IMPORTANCE_CSV_PATH)
    assert rows, "Feature-importance table must contain at least one row."
    assert len(rows) == metadata["feature_count_after_preprocessing"], (
        "Feature-importance row count must match preprocessed feature count."
    )


def assert_validation_predictions_table_exists(metadata: dict[str, Any]) -> None:
    """Validate selected XGBoost validation predictions for downstream evaluation."""
    header = set(read_csv_header(VALIDATION_PREDICTIONS_CSV_PATH))
    missing_columns = sorted(REQUIRED_VALIDATION_PREDICTION_COLUMNS.difference(header))
    assert not missing_columns, (
        f"Validation predictions table missing columns: {missing_columns}"
    )

    rows = read_csv_rows(VALIDATION_PREDICTIONS_CSV_PATH)
    assert rows, "Validation predictions table must contain at least one row."
    assert len(rows) == metadata["validation_slice_summary"]["row_count"], (
        "Validation predictions row count must match validation slice row count."
    )

    validation_slice = metadata["split_metadata"]["validation_slice"]
    for row in rows:
        assert row["model_name"] == "ao1_xgboost_classifier", (
            f"Unexpected model_name in validation predictions: {row['model_name']}"
        )
        assert row["evaluation_slice"] == validation_slice, (
            "Validation prediction evaluation_slice does not match metadata."
        )
        probability = float(row["predicted_probability"])
        threshold = float(row["prediction_threshold"])
        predicted_label = int(float(row["predicted_label"]))
        target_value = int(float(row[TARGET_COLUMN]))

        assert 0.0 <= probability <= 1.0, (
            f"Predicted probability outside [0, 1]: {probability}"
        )
        assert 0.0 <= threshold <= 1.0, f"Prediction threshold outside [0, 1]: {threshold}"
        assert predicted_label in {0, 1}, f"Invalid predicted label: {predicted_label}"
        assert target_value in {0, 1}, f"Invalid target value: {target_value}"
        assert predicted_label == int(probability >= threshold), (
            "Predicted label does not match probability-threshold rule."
        )


def assert_artifact_paths_match(metadata: dict[str, Any]) -> None:
    """Validate metadata artifact path fields match the validator expectations."""
    artifacts = metadata["artifacts"]
    expected_paths = {
        "metrics_json": METRICS_PATH,
        "metadata_json": METADATA_PATH,
        "metrics_csv": METRICS_CSV_PATH,
        "candidate_results_csv": CANDIDATE_RESULTS_CSV_PATH,
        "feature_importance_csv": FEATURE_IMPORTANCE_CSV_PATH,
        "validation_predictions_csv": VALIDATION_PREDICTIONS_CSV_PATH,
    }

    for artifact_key, expected_path in expected_paths.items():
        assert Path(artifacts[artifact_key]) == expected_path, (
            f"Metadata artifact path for {artifact_key} does not match. "
            f"Expected: {expected_path}; found: {artifacts[artifact_key]}"
        )


def print_validation_summary(metadata: dict[str, Any], metrics: dict[str, Any]) -> None:
    """Print a concise validation report."""
    print("\nAO1 XGBoost classifier validation summary:")
    print(f"- Metadata path: {METADATA_PATH}")
    print(f"- Metrics path: {METRICS_PATH}")
    print(f"- Input partition path: {metadata['input_partition_path']}")
    print(f"- Training slice: {metadata['split_metadata']['training_slice']}")
    print(f"- Validation slice: {metadata['split_metadata']['validation_slice']}")
    print("- Final test used: false")
    print(f"- Selected candidate: {metadata['xgboost_classifier']['selected_candidate_id']}")
    print(f"- ROC-AUC: {metrics['roc_auc']:.6f}")
    print(f"- PR-AUC: {metrics['pr_auc']:.6f}")
    print(f"- Recall at 0.5: {metrics['recall']:.6f}")


def run_validation() -> None:
    """Run all AO1 XGBoost classifier artifact validations."""
    metrics = read_json(METRICS_PATH)
    metadata = read_json(METADATA_PATH)

    assert_required_metadata(metadata)
    assert_metrics_present(metrics, metadata)
    assert_metric_ranges(metrics)
    assert_split_and_test_usage(metadata)
    assert_feature_list_is_safe(metadata)
    assert_preprocessing_and_smote_policy(metadata)
    assert_xgboost_selection(metadata)
    assert_artifact_paths_match(metadata)
    assert_metrics_csv_exists()
    assert_candidate_results_table_exists(metadata)
    assert_feature_importance_table_exists(metadata)
    assert_validation_predictions_table_exists(metadata)

    print_validation_summary(metadata, metrics)
    print("\nAO1 XGBoost classifier validation passed.")


if __name__ == "__main__":
    run_validation()
