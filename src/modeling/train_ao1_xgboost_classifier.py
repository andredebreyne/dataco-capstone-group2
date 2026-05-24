"""Train the AO1 XGBoost classifier validation model.

This job consumes the official AO1 chronological partition table, creates a
time-preserving validation slice inside development when needed, fits the
approved AO1 preprocessing pipeline only on the training slice, and evaluates
candidate XGBoost configurations on validation only. The final test partition
is never used for fitting, model selection, threshold tuning, or validation
metrics here.
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

import pandas as pd

from src.modeling.build_ao1_preprocessing_pipeline import (
    FEATURE_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    build_sklearn_preprocessor,
)
from src.modeling.create_ao1_chronological_partitions import (
    AO1_PARTITION_OUTPUT_PATH,
    JOIN_KEY_COLUMNS,
    PARTITION_COLUMN,
    ROW_NUMBER_COLUMN,
    TARGET_COLUMN,
    TEST_LABEL,
)
from src.modeling.train_ao1_logistic_regression_baseline import (
    EXCLUDED_IDENTIFIER_METADATA_COLUMNS,
    class_distribution,
    collect_partition_counts,
    collect_partition_labels,
    date_range_summary,
    determine_modeling_slices,
    evaluate_validation_predictions,
    read_optional_json,
    save_json,
    save_metrics_csv,
    save_model_artifact,
    validate_volume_path,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

DEFAULT_THRESHOLD = 0.5
RANDOM_STATE = 620
PRIMARY_SELECTION_METRIC = "roc_auc"
SECONDARY_SELECTION_METRIC = "recall"

REQUIRED_INPUT_COLUMNS = (
    *JOIN_KEY_COLUMNS,
    TARGET_COLUMN,
    PARTITION_COLUMN,
    ROW_NUMBER_COLUMN,
)


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
        "DATACO_AO1_XGBOOST_OUTPUT_DIR",
        str(REPO_ROOT / "models" / "ao1_late_delivery" / "xgboost_classifier"),
    )
)

DEFAULT_METRICS_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_METRICS_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao1_xgboost_classifier_metrics.json"),
    )
)

DEFAULT_METADATA_JSON_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao1_xgboost_classifier_metadata.json"),
    )
)

DEFAULT_METRICS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_METRICS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_classifier_validation_metrics.csv"),
    )
)

DEFAULT_CANDIDATE_RESULTS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_CANDIDATE_RESULTS_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_classifier_candidate_results.csv"),
    )
)

DEFAULT_FEATURE_IMPORTANCE_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_FEATURE_IMPORTANCE_CSV_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_classifier_feature_importance.csv"),
    )
)

DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_VALIDATION_PREDICTIONS_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_xgboost_validation_predictions.csv"),
    )
)

DEFAULT_PREPROCESSING_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_PREPROCESSING_METADATA_PATH",
        str(REPO_ROOT / "models" / "ao1_late_delivery" / "preprocessing" / "ao1_preprocessing_metadata.json"),
    )
)

DEFAULT_MODEL_ARTIFACT_PATH = os.getenv(
    "DATACO_AO1_XGBOOST_MODEL_ARTIFACT_PATH",
    f"{VOLUME_ROOT}/models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_pipeline.joblib",
)


@dataclass(frozen=True)
class AO1XGBoostClassifierConfig:
    """Configuration for AO1 XGBoost classifier training."""

    partition_input_path: str = os.getenv(
        "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO1_PARTITION_OUTPUT_PATH,
    )
    preprocessing_metadata_path: Path = DEFAULT_PREPROCESSING_METADATA_PATH
    metrics_json_path: Path = DEFAULT_METRICS_JSON_PATH
    metadata_json_path: Path = DEFAULT_METADATA_JSON_PATH
    metrics_csv_path: Path = DEFAULT_METRICS_CSV_PATH
    candidate_results_csv_path: Path = DEFAULT_CANDIDATE_RESULTS_CSV_PATH
    feature_importance_csv_path: Path = DEFAULT_FEATURE_IMPORTANCE_CSV_PATH
    validation_predictions_csv_path: Path = DEFAULT_VALIDATION_PREDICTIONS_CSV_PATH
    model_artifact_path: str = DEFAULT_MODEL_ARTIFACT_PATH
    save_fitted_model: bool = (
        os.getenv("DATACO_AO1_SAVE_XGBOOST_MODEL", "false").strip().lower()
        == "true"
    )
    read_format: str = "delta"
    inner_validation_ratio: float = 0.20
    threshold: float = DEFAULT_THRESHOLD
    random_state: int = RANDOM_STATE


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_xgboost_classifier")


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


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


def get_package_version(package_name: str) -> str | None:
    """Return an installed package version if available."""
    try:
        return importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def assert_required_columns_exist(df: Any) -> None:
    """Validate required identifiers, target, partition columns, and predictors."""
    required_columns = (*REQUIRED_INPUT_COLUMNS, *FEATURE_COLUMNS)
    missing_columns = sorted(column_name for column_name in required_columns if column_name not in df.columns)
    if missing_columns:
        raise ValueError(f"AO1 partition table is missing required columns: {missing_columns}")


def assert_feature_list_is_safe() -> None:
    """Validate target, identifiers, partitions, and leakage fields are excluded."""
    feature_columns = set(FEATURE_COLUMNS)

    if TARGET_COLUMN in feature_columns:
        raise ValueError("AO1 target is present in feature columns.")

    identifier_overlap = sorted(feature_columns.intersection(EXCLUDED_IDENTIFIER_METADATA_COLUMNS))
    if identifier_overlap:
        raise ValueError(
            f"Identifier, partition, or metadata columns found in features: {identifier_overlap}"
        )

    forbidden_normalized = {
        normalize_column_name(column_name)
        for column_name in FORBIDDEN_LEAKAGE_COLUMNS
    }
    feature_normalized = {
        normalize_column_name(column_name)
        for column_name in feature_columns
    }
    forbidden_overlap = sorted(feature_normalized.intersection(forbidden_normalized))
    if forbidden_overlap:
        raise ValueError(f"Forbidden leakage columns found in AO1 features: {forbidden_overlap}")


def assert_target_contract(df: Any) -> None:
    """Validate AO1 target is complete and binary in the partition input."""
    from pyspark.sql.functions import col, sum as spark_sum, when

    target_summary = df.select(
        spark_sum(when(col(TARGET_COLUMN).isNull(), 1).otherwise(0)).alias("missing_count"),
        spark_sum(when(~col(TARGET_COLUMN).isin(0, 1), 1).otherwise(0)).alias("invalid_count"),
    ).collect()[0].asDict()

    if target_summary["missing_count"] != 0 or target_summary["invalid_count"] != 0:
        raise ValueError(
            "AO1 target must be complete and binary before modeling. "
            f"Summary: {target_summary}"
        )


def assert_slice_has_both_classes(y: pd.Series, slice_name: str) -> None:
    """Validate a modeling slice contains both binary target classes."""
    observed_classes = set(y.dropna().astype(int).unique())
    if observed_classes != {0, 1}:
        raise ValueError(
            f"{slice_name} must contain both AO1 target classes for training "
            f"and validation. Observed classes: {sorted(observed_classes)}."
        )


def build_candidate_parameter_sets(
    config: AO1XGBoostClassifierConfig,
    y_train: pd.Series,
) -> list[dict[str, Any]]:
    """Return a small, disciplined validation-tuning grid for AO1 XGBoost."""
    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())
    scale_pos_weight = negative_count / positive_count if positive_count else 1.0

    base_parameters = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "tree_method": os.getenv("DATACO_AO1_XGBOOST_TREE_METHOD", "hist"),
        "random_state": config.random_state,
        "n_jobs": int(os.getenv("DATACO_AO1_XGBOOST_N_JOBS", "-1")),
        "scale_pos_weight": scale_pos_weight,
    }

    return [
        {
            "candidate_id": "balanced_reference",
            **base_parameters,
            "n_estimators": 200,
            "max_depth": 3,
            "learning_rate": 0.05,
            "subsample": 0.90,
            "colsample_bytree": 0.90,
            "min_child_weight": 1,
            "reg_lambda": 1.0,
            "reg_alpha": 0.0,
        },
        {
            "candidate_id": "shallower_regularized",
            **base_parameters,
            "n_estimators": 250,
            "max_depth": 2,
            "learning_rate": 0.04,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "min_child_weight": 3,
            "reg_lambda": 2.0,
            "reg_alpha": 0.1,
        },
        {
            "candidate_id": "deeper_conservative",
            **base_parameters,
            "n_estimators": 150,
            "max_depth": 4,
            "learning_rate": 0.06,
            "subsample": 0.90,
            "colsample_bytree": 0.90,
            "min_child_weight": 2,
            "reg_lambda": 1.5,
            "reg_alpha": 0.0,
        },
    ]


def build_xgboost_pipeline(candidate_parameters: dict[str, Any]) -> Any:
    """Build the approved preprocessing plus one XGBoost candidate model."""
    from sklearn.pipeline import Pipeline

    try:
        from xgboost import XGBClassifier
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
    model = XGBClassifier(**model_parameters)

    return Pipeline(
        steps=[
            ("preprocessor", build_sklearn_preprocessor()),
            ("model", model),
        ]
    )


def select_best_candidate(candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the validation-best candidate using the documented metric order."""
    if not candidate_results:
        raise ValueError("No AO1 XGBoost candidate results were generated.")

    return sorted(
        candidate_results,
        key=lambda result: (
            result["validation_metrics"][PRIMARY_SELECTION_METRIC],
            result["validation_metrics"][SECONDARY_SELECTION_METRIC],
            -result["candidate_rank_input_order"],
        ),
        reverse=True,
    )[0]


def save_candidate_results_csv(
    candidate_results: list[dict[str, Any]],
    path: Path,
) -> None:
    """Write one row per XGBoost candidate validation result."""
    rows = []
    for result in candidate_results:
        metrics = result["validation_metrics"]
        rows.append(
            {
                "candidate_id": result["candidate_id"],
                "selected": result["selected"],
                "roc_auc": metrics["roc_auc"],
                "pr_auc": metrics["pr_auc"],
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "log_loss": metrics["log_loss"],
                "threshold": metrics["threshold"],
                "parameters_json": json.dumps(result["model_parameters"], sort_keys=True),
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def save_validation_predictions(
    validation_pdf: pd.DataFrame,
    y_probability: Any,
    threshold: float,
    evaluation_slice: str,
    path: Path,
) -> None:
    """Write selected XGBoost validation predictions for downstream evaluation."""
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
    prediction_df["model_name"] = "ao1_xgboost_classifier"
    prediction_df["evaluation_slice"] = evaluation_slice
    prediction_df["predicted_probability"] = y_probability
    prediction_df["prediction_threshold"] = threshold
    prediction_df["predicted_label"] = (
        prediction_df["predicted_probability"] >= threshold
    ).astype(int)

    output_columns = [
        "model_name",
        "evaluation_slice",
        "Order_Id",
        "Order_Item_Id",
        "order_date_DateOrders",
        ROW_NUMBER_COLUMN,
        PARTITION_COLUMN,
        TARGET_COLUMN,
        "predicted_probability",
        "prediction_threshold",
        "predicted_label",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    prediction_df.to_csv(path, index=False, columns=output_columns)


def extract_feature_importance(pipeline: Any) -> pd.DataFrame:
    """Extract feature-importance rows from the selected XGBoost pipeline."""
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    feature_names = preprocessor.get_feature_names_out()
    importances = model.feature_importances_

    importance_df = pd.DataFrame(
        {
            "feature_name": feature_names,
            "importance_gain_proxy": importances,
        }
    )
    total_importance = float(importance_df["importance_gain_proxy"].sum())
    importance_df["importance_share"] = (
        importance_df["importance_gain_proxy"] / total_importance
        if total_importance
        else 0.0
    )

    return importance_df.sort_values(
        ["importance_gain_proxy", "feature_name"],
        ascending=[False, True],
    )


def build_metadata(
    config: AO1XGBoostClassifierConfig,
    preprocessing_metadata: dict[str, Any] | None,
    partition_labels: set[str],
    partition_counts: dict[str, int],
    split_metadata: dict[str, Any],
    train_pdf: pd.DataFrame,
    validation_pdf: pd.DataFrame,
    candidate_results: list[dict[str, Any]],
    selected_candidate: dict[str, Any],
    selected_pipeline: Any,
    model_artifact_saved: bool,
) -> dict[str, Any]:
    """Build reproducibility metadata for the AO1 XGBoost validation model."""
    preprocessor = selected_pipeline.named_steps["preprocessor"]
    model = selected_pipeline.named_steps["model"]

    return {
        "metadata_status": "runtime_training_completed",
        "issue": "#28",
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
            "used_for_model_selection": False,
            "used_for_threshold_selection": False,
            "treatment": "reserved for final AO1 model evaluation; not touched by issue #28",
        },
        "target_column": TARGET_COLUMN,
        "feature_columns": list(FEATURE_COLUMNS),
        "excluded_identifier_metadata_columns": list(EXCLUDED_IDENTIFIER_METADATA_COLUMNS),
        "forbidden_leakage_columns": list(FORBIDDEN_LEAKAGE_COLUMNS),
        "feature_count_before_preprocessing": len(FEATURE_COLUMNS),
        "feature_count_after_preprocessing": int(len(preprocessor.get_feature_names_out())),
        "preprocessing_reference": {
            "factory": "src.modeling.build_ao1_preprocessing_pipeline.build_sklearn_preprocessor",
            "metadata_path": str(config.preprocessing_metadata_path),
            "metadata_status": (
                preprocessing_metadata.get("metadata_status") if preprocessing_metadata else None
            ),
            "fit_scope": "fitted inside issue #28 on training slice only",
        },
        "smote": {
            "used": False,
            "decision": "not used for this XGBoost validation model",
            "rationale": (
                "Issue #26 marks SMOTE as deferred and AO1 imbalance as mild. "
                "This XGBoost model uses scale_pos_weight from the training slice "
                "instead of resampling."
            ),
            "training_only": True,
            "validation_resampling_allowed": False,
            "test_resampling_allowed": False,
            "class_distribution_before_resampling": {
                "training": class_distribution(train_pdf[TARGET_COLUMN].astype(int)),
                "validation": class_distribution(validation_pdf[TARGET_COLUMN].astype(int)),
            },
            "class_distribution_after_resampling": {
                "training": class_distribution(train_pdf[TARGET_COLUMN].astype(int)),
                "validation": class_distribution(validation_pdf[TARGET_COLUMN].astype(int)),
            },
        },
        "xgboost_classifier": {
            "library": "xgboost.XGBClassifier",
            "candidate_count": len(candidate_results),
            "candidate_ids": [result["candidate_id"] for result in candidate_results],
            "selection_metric_order": [
                PRIMARY_SELECTION_METRIC,
                SECONDARY_SELECTION_METRIC,
            ],
            "selected_candidate_id": selected_candidate["candidate_id"],
            "selected_parameters": model.get_params(deep=False),
            "baseline_threshold": config.threshold,
            "threshold_tuning": "none",
            "tuning_scope": "small validation-only candidate comparison inside development",
        },
        "candidate_results": candidate_results,
        "validation_metrics": selected_candidate["validation_metrics"],
        "artifacts": {
            "metrics_json": str(config.metrics_json_path),
            "metadata_json": str(config.metadata_json_path),
            "metrics_csv": str(config.metrics_csv_path),
            "candidate_results_csv": str(config.candidate_results_csv_path),
            "feature_importance_csv": str(config.feature_importance_csv_path),
            "validation_predictions_csv": str(config.validation_predictions_csv_path),
            "model_artifact_saved": model_artifact_saved,
            "model_artifact_path": config.model_artifact_path if model_artifact_saved else None,
        },
        "interpretability_notes": {
            "feature_importance_scope": "importances are from the preprocessed feature space",
            "importance_note": (
                "XGBoost feature importances are model-derived associations and should not "
                "be interpreted as causal effects."
            ),
        },
        "versions": {
            "python": sys.version.split()[0],
            "pandas": get_package_version("pandas"),
            "sklearn": get_package_version("scikit-learn"),
            "pyspark": get_package_version("pyspark"),
            "joblib": get_package_version("joblib"),
            "xgboost": get_package_version("xgboost"),
        },
    }


def run_ao1_xgboost_classifier(
    config: AO1XGBoostClassifierConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Train and validate the AO1 XGBoost classifier."""
    logger.info("Starting AO1 XGBoost classifier training.")
    logger.info("AO1 partition input path: %s", config.partition_input_path)
    logger.info("Metrics output path: %s", config.metrics_json_path)
    logger.info("Metadata output path: %s", config.metadata_json_path)

    validate_volume_path(config.partition_input_path, "partition_input_path")
    assert_feature_list_is_safe()

    spark = get_spark_session()
    partitioned_df = spark.read.format(config.read_format).load(config.partition_input_path)
    assert_required_columns_exist(partitioned_df)
    assert_target_contract(partitioned_df)

    partition_labels = collect_partition_labels(partitioned_df)
    partition_counts = collect_partition_counts(partitioned_df)
    train_pdf, validation_pdf, split_metadata = determine_modeling_slices(partitioned_df, config)
    preprocessing_metadata = read_optional_json(config.preprocessing_metadata_path)

    x_train = train_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_train = train_pdf[TARGET_COLUMN].astype(int)
    x_validation = validation_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_validation = validation_pdf[TARGET_COLUMN].astype(int)
    assert_slice_has_both_classes(y_train, "AO1 XGBoost training slice")
    assert_slice_has_both_classes(y_validation, "AO1 XGBoost validation slice")

    candidate_parameters = build_candidate_parameter_sets(config, y_train)
    candidate_results: list[dict[str, Any]] = []
    candidate_pipelines: dict[str, Any] = {}
    for rank, parameters in enumerate(candidate_parameters, start=1):
        candidate_id = parameters["candidate_id"]
        logger.info("Training AO1 XGBoost candidate: %s", candidate_id)
        pipeline = build_xgboost_pipeline(parameters)
        pipeline.fit(x_train, y_train)

        y_validation_probability = pipeline.predict_proba(x_validation)[:, 1]
        metrics = evaluate_validation_predictions(
            y_validation,
            y_validation_probability,
            config.threshold,
        )
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
        logger.info(
            "Candidate %s validation ROC-AUC: %.6f; recall: %.6f",
            candidate_id,
            metrics["roc_auc"],
            metrics["recall"],
        )

    selected_candidate = select_best_candidate(candidate_results)
    selected_candidate["selected"] = True
    selected_pipeline = candidate_pipelines[selected_candidate["candidate_id"]]
    logger.info("Selected AO1 XGBoost candidate: %s", selected_candidate["candidate_id"])
    selected_validation_probability = selected_pipeline.predict_proba(x_validation)[:, 1]

    feature_importance_df = extract_feature_importance(selected_pipeline)
    config.feature_importance_csv_path.parent.mkdir(parents=True, exist_ok=True)
    feature_importance_df.to_csv(config.feature_importance_csv_path, index=False)

    save_validation_predictions(
        validation_pdf,
        selected_validation_probability,
        config.threshold,
        split_metadata["validation_slice"],
        config.validation_predictions_csv_path,
    )
    save_metrics_csv(selected_candidate["validation_metrics"], config.metrics_csv_path)
    save_candidate_results_csv(candidate_results, config.candidate_results_csv_path)
    save_json(selected_candidate["validation_metrics"], config.metrics_json_path)

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
        model_artifact_saved,
    )
    save_json(metadata, config.metadata_json_path)

    metrics = selected_candidate["validation_metrics"]
    logger.info("AO1 XGBoost validation ROC-AUC: %.6f", metrics["roc_auc"])
    logger.info("AO1 XGBoost validation recall: %.6f", metrics["recall"])
    logger.info("AO1 XGBoost classifier training completed successfully.")
    return metadata


def main() -> None:
    """Run AO1 XGBoost classifier training with default configuration."""
    run_ao1_xgboost_classifier(
        AO1XGBoostClassifierConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
