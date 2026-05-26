"""Score the held-out test set with frozen AO1 and AO2 model outputs.

This job trains the selected AO1 and AO2 model configurations on the approved
development partitions only, applies them to the untouched test partitions,
and writes the integrated AO1/AO2 score table required for AO3. It does not
fit on test data, tune thresholds, select models, calculate final-test
performance, or assign AO3 risk-margin segments.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.modeling.build_ao1_preprocessing_pipeline import (
    FEATURE_COLUMNS as AO1_FEATURE_COLUMNS,
)
from src.modeling.build_ao2_preprocessing_pipeline import (
    FEATURE_COLUMNS as AO2_FEATURE_COLUMNS,
)
from src.modeling.create_ao1_chronological_partitions import (
    AO1_PARTITION_OUTPUT_PATH,
    DEVELOPMENT_LABEL as AO1_DEVELOPMENT_LABEL,
    JOIN_KEY_COLUMNS as AO1_JOIN_KEY_COLUMNS,
    PARTITION_COLUMN as AO1_PARTITION_COLUMN,
    ROW_NUMBER_COLUMN as AO1_ROW_NUMBER_COLUMN,
    TARGET_COLUMN as AO1_TARGET_COLUMN,
    TEST_LABEL as AO1_TEST_LABEL,
)
from src.modeling.create_ao2_chronological_partitions import (
    AO2_PARTITION_OUTPUT_PATH,
    DEVELOPMENT_LABEL as AO2_DEVELOPMENT_LABEL,
    JOIN_KEY_COLUMNS as AO2_JOIN_KEY_COLUMNS,
    PARTITION_COLUMN as AO2_PARTITION_COLUMN,
    ROW_NUMBER_COLUMN as AO2_ROW_NUMBER_COLUMN,
    TARGET_COLUMN as AO2_TARGET_COLUMN,
    TEST_LABEL as AO2_TEST_LABEL,
)
from src.modeling.train_ao1_xgboost_classifier import (
    AO1XGBoostClassifierConfig,
    build_candidate_parameter_sets as build_ao1_candidate_parameter_sets,
    build_xgboost_pipeline as build_ao1_xgboost_pipeline,
)
from src.modeling.train_ao1_logistic_regression_baseline import (
    read_optional_json,
    save_json,
    validate_volume_path,
)
from src.modeling.train_ao2_gradient_boosting_regressor import (
    AO2GradientBoostingRegressorConfig,
    MODEL_NAME as AO2_MODEL_NAME,
    build_candidate_parameter_sets as build_ao2_candidate_parameter_sets,
    build_xgboost_pipeline as build_ao2_xgboost_pipeline,
)


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

OUTPUT_PATH = os.getenv(
    "DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao1_ao2_test_scores",
)

AO3_ORDER_VALUE_COLUMN = "ao3_order_value"
AO1_MODEL_NAME = "ao1_xgboost_classifier"
SCORING_MODE = "development_refit_test_score"


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
        "DATACO_AO1_AO2_TEST_SCORE_ARTIFACT_DIR",
        str(REPO_ROOT / "models" / "ao3_integration" / "ao1_ao2_test_scores"),
    )
)

DEFAULT_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_AO2_TEST_SCORE_METADATA_PATH",
        str(DEFAULT_OUTPUT_DIR / "ao1_ao2_test_score_metadata.json"),
    )
)

DEFAULT_SUMMARY_PATH = Path(
    os.getenv(
        "DATACO_AO1_AO2_TEST_SCORE_SUMMARY_PATH",
        str(REPO_ROOT / "data" / "references" / "ao1_ao2_test_score_summary.csv"),
    )
)

DEFAULT_AO1_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO1_XGBOOST_METADATA_PATH",
        str(
            REPO_ROOT
            / "models"
            / "ao1_late_delivery"
            / "xgboost_classifier"
            / "ao1_xgboost_classifier_metadata.json"
        ),
    )
)

DEFAULT_AO2_METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO2_GRADIENT_BOOSTING_METADATA_PATH",
        str(
            REPO_ROOT
            / "models"
            / "ao2_profitability"
            / "gradient_boosting"
            / "ao2_gradient_boosting_metadata.json"
        ),
    )
)

DEFAULT_AO1_THRESHOLD_POLICY_PATH = Path(
    os.getenv(
        "DATACO_AO1_DECISION_THRESHOLD_POLICY_PATH",
        str(REPO_ROOT / "data" / "references" / "ao1_decision_threshold_policy.csv"),
    )
)


@dataclass(frozen=True)
class AO1AO2TestScoringConfig:
    """Configuration for integrated AO1/AO2 test scoring."""

    ao1_partition_input_path: str = os.getenv(
        "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO1_PARTITION_OUTPUT_PATH,
    )
    ao2_partition_input_path: str = os.getenv(
        "DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO2_PARTITION_OUTPUT_PATH,
    )
    output_path: str = OUTPUT_PATH
    ao1_metadata_path: Path = DEFAULT_AO1_METADATA_PATH
    ao2_metadata_path: Path = DEFAULT_AO2_METADATA_PATH
    ao1_threshold_policy_path: Path = DEFAULT_AO1_THRESHOLD_POLICY_PATH
    metadata_output_path: Path = DEFAULT_METADATA_PATH
    summary_output_path: Path = DEFAULT_SUMMARY_PATH
    read_format: str = "delta"
    write_format: str = "delta"
    write_mode: str = "overwrite"


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_ao2_test_scoring")


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def read_selected_threshold(path: Path) -> float:
    """Read the approved AO1 decision threshold policy."""
    if not path.exists():
        raise FileNotFoundError(f"Missing AO1 decision threshold policy: {path}")

    threshold_df = pd.read_csv(path)
    if len(threshold_df) != 1:
        raise ValueError("AO1 decision threshold policy must contain exactly one row.")

    row = threshold_df.iloc[0]
    if str(row["final_test_used"]).lower() != "false":
        raise ValueError("AO1 threshold policy must not be selected using final test data.")
    if row["model_name"] != AO1_MODEL_NAME:
        raise ValueError(f"Unexpected AO1 threshold model: {row['model_name']}")

    return float(row["selected_threshold"])


def get_selected_candidate_id(metadata: dict[str, Any], section: str) -> str:
    """Read a selected candidate id from a prior model metadata file."""
    candidate_id = metadata.get(section, {}).get("selected_candidate_id")
    if not candidate_id:
        raise ValueError(f"Missing selected candidate id in metadata section: {section}")
    return str(candidate_id)


def select_candidate_parameters(
    candidate_parameters: list[dict[str, Any]],
    selected_candidate_id: str,
) -> dict[str, Any]:
    """Return candidate parameters matching the frozen selected candidate id."""
    for parameters in candidate_parameters:
        if parameters["candidate_id"] == selected_candidate_id:
            return parameters
    raise ValueError(f"Selected candidate not found: {selected_candidate_id}")


def validate_input_contracts(ao1_df: Any, ao2_df: Any) -> None:
    """Validate required columns for AO1/AO2 scoring."""
    ao1_required_columns = set(AO1_JOIN_KEY_COLUMNS).union(
        {AO1_TARGET_COLUMN, AO1_PARTITION_COLUMN, AO1_ROW_NUMBER_COLUMN, *AO1_FEATURE_COLUMNS}
    )
    ao2_required_columns = set(AO2_JOIN_KEY_COLUMNS).union(
        {
            AO2_TARGET_COLUMN,
            AO2_PARTITION_COLUMN,
            AO2_ROW_NUMBER_COLUMN,
            AO3_ORDER_VALUE_COLUMN,
            *AO2_FEATURE_COLUMNS,
        }
    )

    missing_ao1 = sorted(ao1_required_columns.difference(ao1_df.columns))
    missing_ao2 = sorted(ao2_required_columns.difference(ao2_df.columns))
    if missing_ao1:
        raise ValueError(f"AO1 partition table is missing required columns: {missing_ao1}")
    if missing_ao2:
        raise ValueError(f"AO2 partition table is missing required columns: {missing_ao2}")


def collect_partition_pdf(df: Any, partition_column: str, partition_label: str) -> pd.DataFrame:
    """Collect one partition to pandas for sklearn/xgboost scoring."""
    return df.filter(df[partition_column] == partition_label).toPandas()


def assert_partition_available(pdf: pd.DataFrame, partition_name: str) -> None:
    """Validate a collected partition contains rows."""
    if pdf.empty:
        raise ValueError(f"{partition_name} partition contains no rows.")


def score_ao1_test_set(
    development_pdf: pd.DataFrame,
    test_pdf: pd.DataFrame,
    selected_candidate_id: str,
    threshold: float,
) -> pd.DataFrame:
    """Fit the selected AO1 candidate on development and score AO1 test rows."""
    config = AO1XGBoostClassifierConfig()
    x_development = development_pdf.loc[:, list(AO1_FEATURE_COLUMNS)]
    y_development = development_pdf[AO1_TARGET_COLUMN].astype(int)
    x_test = test_pdf.loc[:, list(AO1_FEATURE_COLUMNS)]

    candidate_parameters = build_ao1_candidate_parameter_sets(config, y_development)
    selected_parameters = select_candidate_parameters(candidate_parameters, selected_candidate_id)
    pipeline = build_ao1_xgboost_pipeline(selected_parameters)
    pipeline.fit(x_development, y_development)

    predicted_probability = pipeline.predict_proba(x_test)[:, 1]
    score_df = test_pdf.loc[
        :,
        [
            "Order_Id",
            "Order_Item_Id",
            "order_date_DateOrders",
            AO1_ROW_NUMBER_COLUMN,
            AO1_PARTITION_COLUMN,
        ],
    ].copy()
    score_df["ao1_model_name"] = AO1_MODEL_NAME
    score_df["ao1_selected_candidate"] = selected_candidate_id
    score_df["ao1_scoring_mode"] = SCORING_MODE
    score_df["ao1_predicted_late_delivery_probability"] = predicted_probability
    score_df["ao1_decision_threshold"] = threshold
    score_df["ao1_high_risk_flag"] = (
        score_df["ao1_predicted_late_delivery_probability"] >= threshold
    )
    return score_df


def score_ao2_test_set(
    development_pdf: pd.DataFrame,
    test_pdf: pd.DataFrame,
    selected_candidate_id: str,
) -> pd.DataFrame:
    """Fit the selected AO2 candidate on development and score AO2 test rows."""
    config = AO2GradientBoostingRegressorConfig()
    x_development = development_pdf.loc[:, list(AO2_FEATURE_COLUMNS)]
    y_development = development_pdf[AO2_TARGET_COLUMN].astype(float)
    x_test = test_pdf.loc[:, list(AO2_FEATURE_COLUMNS)]

    candidate_parameters = build_ao2_candidate_parameter_sets(config)
    selected_parameters = select_candidate_parameters(candidate_parameters, selected_candidate_id)
    pipeline = build_ao2_xgboost_pipeline(selected_parameters)
    pipeline.fit(x_development, y_development)

    predicted_profit = pipeline.predict(x_test)
    score_df = test_pdf.loc[
        :,
        [
            "Order_Id",
            "Order_Item_Id",
            "order_date_DateOrders",
            AO2_ROW_NUMBER_COLUMN,
            AO2_PARTITION_COLUMN,
            AO3_ORDER_VALUE_COLUMN,
        ],
    ].copy()
    score_df["ao2_model_name"] = AO2_MODEL_NAME
    score_df["ao2_selected_candidate"] = selected_candidate_id
    score_df["ao2_scoring_mode"] = SCORING_MODE
    score_df["ao2_predicted_order_profit"] = predicted_profit
    score_df = score_df.rename(
        columns={
            AO2_ROW_NUMBER_COLUMN: "ao2_chronological_row_number",
            AO2_PARTITION_COLUMN: "ao2_split_partition",
        }
    )
    return score_df


def build_integrated_scores(ao1_scores: pd.DataFrame, ao2_scores: pd.DataFrame) -> pd.DataFrame:
    """Join AO1 and AO2 test scores for AO3 downstream use."""
    join_keys = ["Order_Id", "Order_Item_Id", "order_date_DateOrders"]
    integrated_df = ao1_scores.merge(
        ao2_scores,
        how="left",
        on=join_keys,
        validate="one_to_one",
    )

    missing_ao2_count = int(integrated_df["ao2_predicted_order_profit"].isna().sum())
    if missing_ao2_count:
        raise ValueError(
            "AO2 predictions are missing for AO1 scored rows. "
            f"Missing count: {missing_ao2_count}"
        )

    integrated_df["ao3_predicted_margin"] = integrated_df["ao2_predicted_order_profit"] / integrated_df[
        AO3_ORDER_VALUE_COLUMN
    ]
    integrated_df.loc[
        integrated_df[AO3_ORDER_VALUE_COLUMN].isna()
        | (integrated_df[AO3_ORDER_VALUE_COLUMN] <= 0),
        "ao3_predicted_margin",
    ] = float("nan")
    integrated_df["scoring_timestamp_utc"] = datetime.now(timezone.utc).isoformat()

    output_columns = [
        "Order_Id",
        "Order_Item_Id",
        "order_date_DateOrders",
        AO1_ROW_NUMBER_COLUMN,
        AO1_PARTITION_COLUMN,
        "ao2_chronological_row_number",
        "ao2_split_partition",
        "ao1_model_name",
        "ao1_selected_candidate",
        "ao1_scoring_mode",
        "ao1_predicted_late_delivery_probability",
        "ao1_decision_threshold",
        "ao1_high_risk_flag",
        "ao2_model_name",
        "ao2_selected_candidate",
        "ao2_scoring_mode",
        "ao2_predicted_order_profit",
        AO3_ORDER_VALUE_COLUMN,
        "ao3_predicted_margin",
        "scoring_timestamp_utc",
    ]
    return integrated_df.loc[:, output_columns]


def write_summary_csv(summary: dict[str, Any], path: Path) -> None:
    """Write one-row scoring summary CSV for project traceability."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(path, index=False)


def build_metadata(
    config: AO1AO2TestScoringConfig,
    ao1_metadata: dict[str, Any] | None,
    ao2_metadata: dict[str, Any] | None,
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Build scoring metadata for review and reproducibility."""
    return {
        "metadata_status": "runtime_scoring_completed",
        "issue": "#41",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scoring_mode": SCORING_MODE,
        "ao1_partition_input_path": config.ao1_partition_input_path,
        "ao2_partition_input_path": config.ao2_partition_input_path,
        "output_path": config.output_path,
        "summary_output_path": str(config.summary_output_path),
        "ao1_model_reference": {
            "model_name": AO1_MODEL_NAME,
            "metadata_path": str(config.ao1_metadata_path),
            "selected_candidate_id": summary["ao1_selected_candidate"],
            "source_issue": ao1_metadata.get("issue") if ao1_metadata else None,
        },
        "ao2_model_reference": {
            "model_name": AO2_MODEL_NAME,
            "metadata_path": str(config.ao2_metadata_path),
            "selected_candidate_id": summary["ao2_selected_candidate"],
            "source_issue": ao2_metadata.get("issue") if ao2_metadata else None,
        },
        "ao1_threshold_reference": {
            "policy_path": str(config.ao1_threshold_policy_path),
            "selected_threshold": summary["ao1_decision_threshold"],
            "final_test_used_for_threshold_selection": False,
        },
        "test_set_usage": {
            "used_for_prediction_only": True,
            "used_for_model_selection": False,
            "used_for_threshold_selection": False,
            "used_for_training": False,
            "used_for_performance_metrics": False,
        },
        "summary": summary,
        "limitations": [
            "The integrated table is the AO1/AO2 scoring input for AO3 and does not assign final AO3 segments.",
            "Final-test labels remain excluded from the scored output and are not used for performance metrics.",
            "The AO3 scoring population is anchored on AO1 test rows and requires matching AO2 scores.",
        ],
    }


def run_ao1_ao2_test_scoring(
    config: AO1AO2TestScoringConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Run integrated AO1/AO2 scoring for the held-out test set."""
    logger.info("Starting AO1/AO2 held-out test scoring.")
    logger.info("AO1 partition input path: %s", config.ao1_partition_input_path)
    logger.info("AO2 partition input path: %s", config.ao2_partition_input_path)
    logger.info("Integrated score output path: %s", config.output_path)

    validate_volume_path(config.ao1_partition_input_path, "ao1_partition_input_path")
    validate_volume_path(config.ao2_partition_input_path, "ao2_partition_input_path")
    validate_volume_path(config.output_path, "output_path")

    ao1_metadata = read_optional_json(config.ao1_metadata_path)
    ao2_metadata = read_optional_json(config.ao2_metadata_path)
    if ao1_metadata is None:
        raise FileNotFoundError(f"Missing AO1 metadata: {config.ao1_metadata_path}")
    if ao2_metadata is None:
        raise FileNotFoundError(f"Missing AO2 metadata: {config.ao2_metadata_path}")

    ao1_selected_candidate = get_selected_candidate_id(ao1_metadata, "xgboost_classifier")
    ao2_selected_candidate = get_selected_candidate_id(ao2_metadata, "gradient_boosting_regressor")
    ao1_threshold = read_selected_threshold(config.ao1_threshold_policy_path)

    spark = get_spark_session()
    ao1_df = spark.read.format(config.read_format).load(config.ao1_partition_input_path)
    ao2_df = spark.read.format(config.read_format).load(config.ao2_partition_input_path)
    validate_input_contracts(ao1_df, ao2_df)

    ao1_development_pdf = collect_partition_pdf(ao1_df, AO1_PARTITION_COLUMN, AO1_DEVELOPMENT_LABEL)
    ao1_test_pdf = collect_partition_pdf(ao1_df, AO1_PARTITION_COLUMN, AO1_TEST_LABEL)
    ao2_development_pdf = collect_partition_pdf(ao2_df, AO2_PARTITION_COLUMN, AO2_DEVELOPMENT_LABEL)
    ao2_test_pdf = collect_partition_pdf(ao2_df, AO2_PARTITION_COLUMN, AO2_TEST_LABEL)

    assert_partition_available(ao1_development_pdf, "AO1 development")
    assert_partition_available(ao1_test_pdf, "AO1 test")
    assert_partition_available(ao2_development_pdf, "AO2 development")
    assert_partition_available(ao2_test_pdf, "AO2 test")

    logger.info("Fitting selected AO1 candidate on development: %s", ao1_selected_candidate)
    ao1_scores = score_ao1_test_set(
        ao1_development_pdf,
        ao1_test_pdf,
        ao1_selected_candidate,
        ao1_threshold,
    )
    logger.info("Fitting selected AO2 candidate on development: %s", ao2_selected_candidate)
    ao2_scores = score_ao2_test_set(
        ao2_development_pdf,
        ao2_test_pdf,
        ao2_selected_candidate,
    )

    integrated_scores = build_integrated_scores(ao1_scores, ao2_scores)
    spark.createDataFrame(integrated_scores).write.format(config.write_format).mode(
        config.write_mode
    ).save(config.output_path)

    summary = {
        "issue": "#41",
        "scoring_mode": SCORING_MODE,
        "ao1_selected_candidate": ao1_selected_candidate,
        "ao2_selected_candidate": ao2_selected_candidate,
        "ao1_decision_threshold": ao1_threshold,
        "ao1_development_rows": int(len(ao1_development_pdf)),
        "ao1_test_rows": int(len(ao1_test_pdf)),
        "ao2_development_rows": int(len(ao2_development_pdf)),
        "ao2_test_rows": int(len(ao2_test_pdf)),
        "integrated_scored_rows": int(len(integrated_scores)),
        "ao1_high_risk_count": int(integrated_scores["ao1_high_risk_flag"].sum()),
        "ao3_margin_missing_count": int(integrated_scores["ao3_predicted_margin"].isna().sum()),
        "output_path": config.output_path,
        "final_test_used_for_training": False,
        "final_test_used_for_model_selection": False,
        "final_test_used_for_threshold_selection": False,
        "final_test_metrics_calculated": False,
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_summary_csv(summary, config.summary_output_path)

    metadata = build_metadata(config, ao1_metadata, ao2_metadata, summary)
    save_json(metadata, config.metadata_output_path)

    logger.info("AO1/AO2 integrated scored rows: %s", summary["integrated_scored_rows"])
    logger.info("AO1/AO2 held-out test scoring completed successfully.")
    return metadata


def main() -> None:
    """Run AO1/AO2 test scoring with default configuration."""
    run_ao1_ao2_test_scoring(
        AO1AO2TestScoringConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
