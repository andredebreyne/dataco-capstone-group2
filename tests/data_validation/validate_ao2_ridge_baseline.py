"""Validate AO2 Ridge baseline artifacts.

Run this script after `src/modeling/train_ao2_ridge_baseline.py` has completed.
It validates lightweight JSON/CSV artifacts and documented fit/evaluation
boundaries; it does not retrain the model.
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
MODEL_NAME = "ao2_ridge_baseline"

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
    "ridge_regression",
    "validation_metrics",
    "residual_diagnostics",
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

REQUIRED_PREDICTION_COLUMNS = {
    "model_name",
    "evaluation_slice",
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    TARGET_COLUMN,
    "predicted_profit",
    "residual",
    "absolute_error",
}

REQUIRED_COEFFICIENT_COLUMNS = {
    "model_name",
    "feature_name",
    "coefficient",
    "absolute_coefficient",
    "sign",
    "coefficient_rank",
}

REQUIRED_RIDGE_PARAMETERS = {
    "alpha",
    "fit_intercept",
    "copy_X",
    "max_iter",
    "tol",
    "solver",
    "positive",
    "random_state",
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
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "ao2_profitability" / "ridge_baseline"

METRICS_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_METRICS_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_ridge_baseline_metrics.json"),
    )
)
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao2_ridge_baseline_metadata.json"),
    )
)
METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_validation_metrics.csv"),
    )
)
RESIDUAL_DIAGNOSTICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_RESIDUAL_DIAGNOSTICS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_residual_diagnostics.csv"),
    )
)
VALIDATION_PREDICTIONS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_VALIDATION_PREDICTIONS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_validation_predictions.csv"),
    )
)
COEFFICIENTS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO2_RIDGE_COEFFICIENTS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_ridge_coefficients.csv"),
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
    assert not missing_keys, f"AO2 Ridge metadata is missing keys: {missing_keys}"
    assert metadata["metadata_status"] == "runtime_training_completed", (
        "AO2 Ridge metadata must come from a completed training run."
    )


def assert_metrics_present(metrics: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Validate required metric keys exist in both metrics and metadata artifacts."""
    missing_metrics = sorted(REQUIRED_METRICS.difference(metrics))
    assert not missing_metrics, f"AO2 Ridge metrics missing keys: {missing_metrics}"
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
    """Validate training/validation slices exclude the final test set."""
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


def assert_feature_list_is_safe(metadata: dict[str, Any]) -> None:
    """Validate target, identifiers, AO3 support, and forbidden fields are not predictors."""
    assert metadata["target_column"] == TARGET_COLUMN, (
        f"Unexpected target column: {metadata['target_column']}"
    )
    assert metadata["target_transformation"] == "none", "AO2 Ridge must use the raw target."

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
    assert preprocessing_reference["fit_scope"] == "fitted inside issue #35 on training slice only", (
        "Preprocessing fit scope must be training-slice only."
    )
    assert preprocessing_reference["test_transform_scope"] == "not transformed by this baseline job", (
        "The Ridge baseline must not transform or score the final test partition."
    )


def assert_ridge_parameters(metadata: dict[str, Any]) -> None:
    """Validate Ridge settings are documented and intentionally simple."""
    ridge = metadata["ridge_regression"]
    parameters = ridge["parameters"]
    missing_parameters = sorted(REQUIRED_RIDGE_PARAMETERS.difference(parameters))
    assert not missing_parameters, f"Ridge parameters missing from metadata: {missing_parameters}"
    assert parameters["alpha"] == 1.0, f"Unexpected Ridge alpha: {parameters['alpha']}"
    assert ridge["tuning"] == "none", "This baseline must not run hyperparameter tuning."


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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read rows from a required CSV artifact."""
    assert path.exists(), f"Missing required CSV artifact: {path}"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_metrics_csv_exists() -> None:
    """Validate report-facing metrics CSV exists and has expected columns."""
    rows = read_csv_rows(METRICS_CSV_PATH)
    assert rows, "Metrics CSV must contain rows."
    header = set(rows[0])
    assert {"metric", "value"}.issubset(header), (
        f"Metrics CSV must include metric and value columns. Header: {sorted(header)}"
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


def assert_coefficient_table_exists() -> None:
    """Validate the coefficient table exists and includes interpretability fields."""
    rows = read_csv_rows(COEFFICIENTS_CSV_PATH)
    assert rows, "Coefficient CSV must contain rows."
    header = set(rows[0])
    missing_columns = sorted(REQUIRED_COEFFICIENT_COLUMNS.difference(header))
    assert not missing_columns, f"Coefficient table missing columns: {missing_columns}"
    for row_index, row in enumerate(rows, start=2):
        assert row["model_name"] == MODEL_NAME, f"Unexpected model_name at coefficient row {row_index}."
        coefficient = float(row["coefficient"])
        absolute_coefficient = float(row["absolute_coefficient"])
        assert math.isfinite(coefficient), f"Coefficient must be finite at row {row_index}."
        assert math.isfinite(absolute_coefficient), (
            f"Absolute coefficient must be finite at row {row_index}."
        )
        assert absolute_coefficient >= 0.0, (
            f"Absolute coefficient must be non-negative at row {row_index}."
        )


def print_validation_summary(metadata: dict[str, Any], metrics: dict[str, Any]) -> None:
    """Print a concise validation report."""
    print("\nAO2 Ridge baseline validation summary:")
    print(f"- Metadata path: {METADATA_PATH}")
    print(f"- Metrics path: {METRICS_PATH}")
    print(f"- Input partition path: {metadata['input_partition_path']}")
    print(f"- Training slice: {metadata['split_metadata']['training_slice']}")
    print(f"- Validation slice: {metadata['split_metadata']['validation_slice']}")
    print("- Final test used: false")
    print(f"- RMSE: {metrics['rmse']:.6f}")
    print(f"- MAE: {metrics['mae']:.6f}")
    print(f"- R2: {metrics['r2']:.6f}")


def run_validation() -> None:
    """Run all AO2 Ridge baseline artifact validations."""
    metrics = read_json(METRICS_PATH)
    metadata = read_json(METADATA_PATH)

    assert_required_metadata(metadata)
    assert_metrics_present(metrics, metadata)
    assert_metric_ranges(metrics)
    assert_split_and_test_usage(metadata)
    assert_feature_list_is_safe(metadata)
    assert_preprocessing_policy(metadata)
    assert_ridge_parameters(metadata)
    assert_residual_diagnostics(metadata)
    assert_metrics_csv_exists()
    assert_residual_diagnostics_csv_exists()
    assert_prediction_rows(metrics, metadata)
    assert_coefficient_table_exists()

    print_validation_summary(metadata, metrics)
    print("\nAO2 Ridge baseline validation passed.")


if __name__ == "__main__":
    run_validation()
