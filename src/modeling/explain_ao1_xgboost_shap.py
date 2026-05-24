"""Generate AO1 XGBoost SHAP explainability artifacts.

This job retrains the selected AO1 XGBoost validation configuration on the
approved training slice only, computes SHAP values on the validation slice, and
writes report-facing feature-driver artifacts. The final test partition is not
used for fitting, model selection, threshold tuning, or explainability.
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

import numpy as np
import pandas as pd

from src.modeling.build_ao1_preprocessing_pipeline import FEATURE_COLUMNS
from src.modeling.create_ao1_chronological_partitions import (
    AO1_PARTITION_OUTPUT_PATH,
    TARGET_COLUMN,
)
from src.modeling.train_ao1_logistic_regression_baseline import (
    determine_modeling_slices,
    read_optional_json,
    validate_volume_path,
)
from src.modeling.train_ao1_xgboost_classifier import (
    AO1XGBoostClassifierConfig,
    build_candidate_parameter_sets,
    build_xgboost_pipeline,
)


RANDOM_STATE = 620
DEFAULT_SELECTED_CANDIDATE_ID = "deeper_conservative"


def resolve_repo_root() -> Path:
    """Resolve repository root for local and Databricks notebook execution."""
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
class AO1SHAPExplainabilityConfig:
    """Configuration for AO1 XGBoost SHAP explainability outputs."""

    partition_input_path: str = os.getenv(
        "DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO1_PARTITION_OUTPUT_PATH,
    )
    xgboost_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO1_XGBOOST_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_metadata.json"
            ),
        )
    )
    shap_importance_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_SHAP_IMPORTANCE_PATH",
            str(REPO_ROOT / "report/tables/ao1_shap_feature_importance.csv"),
        )
    )
    driver_summary_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_SHAP_DRIVER_SUMMARY_PATH",
            str(REPO_ROOT / "report/tables/ao1_shap_driver_summary.csv"),
        )
    )
    figure_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_SHAP_TOP_FEATURES_FIGURE_PATH",
            str(REPO_ROOT / "report/figures/ao1_shap_top_features.png"),
        )
    )
    findings_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_SHAP_FINDINGS_PATH",
            str(REPO_ROOT / "report/tables/ao1_shap_explainability_findings.md"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_SHAP_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao1_late_delivery/explainability/ao1_shap_explainability_metadata.json"
            ),
        )
    )
    read_format: str = "delta"
    max_validation_sample_rows: int = int(os.getenv("DATACO_AO1_SHAP_MAX_ROWS", "5000"))
    top_n_features: int = int(os.getenv("DATACO_AO1_SHAP_TOP_N", "20"))
    random_state: int = RANDOM_STATE


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_shap_explainability")


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def selected_candidate_id(config: AO1SHAPExplainabilityConfig) -> str:
    """Return selected XGBoost candidate id from metadata when available."""
    metadata = read_optional_json(config.xgboost_metadata_path)
    candidate_id = (
        metadata.get("xgboost_classifier", {}).get("selected_candidate_id")
        if metadata
        else None
    )
    if candidate_id:
        return str(candidate_id)
    return DEFAULT_SELECTED_CANDIDATE_ID


def select_candidate_parameters(
    candidates: list[dict[str, Any]],
    candidate_id: str,
) -> dict[str, Any]:
    """Select the XGBoost parameter set used for SHAP explanations."""
    for candidate in candidates:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise ValueError(
        f"Selected AO1 XGBoost candidate '{candidate_id}' was not found in the "
        f"available candidate set: {[candidate['candidate_id'] for candidate in candidates]}"
    )


def sample_validation_frame(
    validation_pdf: pd.DataFrame,
    max_rows: int,
    random_state: int,
) -> pd.DataFrame:
    """Return a deterministic validation sample for explainability."""
    if len(validation_pdf) <= max_rows:
        return validation_pdf.copy()
    return validation_pdf.sample(n=max_rows, random_state=random_state).sort_index()


def to_dense_array(matrix: Any) -> np.ndarray:
    """Return dense numpy array from sparse or dense preprocessing output."""
    if hasattr(matrix, "toarray"):
        return matrix.toarray()
    return np.asarray(matrix)


def compute_shap_importance(
    pipeline: Any,
    x_validation_sample: pd.DataFrame,
) -> pd.DataFrame:
    """Compute mean absolute SHAP importance for the selected validation rows."""
    try:
        import shap
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency: shap. In Databricks, run "
            "`%pip install -r requirements.txt` or `%pip install shap`, then restart Python."
        ) from exc

    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    transformed_validation = to_dense_array(preprocessor.transform(x_validation_sample))
    feature_names = preprocessor.get_feature_names_out()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(transformed_validation)
    if isinstance(shap_values, list):
        shap_array = np.asarray(shap_values[-1])
    else:
        shap_array = np.asarray(shap_values)

    if shap_array.ndim == 3:
        shap_array = shap_array[:, :, -1]

    mean_abs_shap = np.abs(shap_array).mean(axis=0)
    mean_signed_shap = shap_array.mean(axis=0)
    importance_df = pd.DataFrame(
        {
            "feature_name": feature_names,
            "mean_abs_shap": mean_abs_shap,
            "mean_signed_shap": mean_signed_shap,
        }
    )
    total_importance = float(importance_df["mean_abs_shap"].sum())
    importance_df["importance_share"] = (
        importance_df["mean_abs_shap"] / total_importance if total_importance else 0.0
    )
    importance_df["rank"] = (
        importance_df["mean_abs_shap"].rank(method="first", ascending=False).astype(int)
    )
    return importance_df.sort_values(["rank", "feature_name"])


def build_driver_summary(importance_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Create a compact report-facing summary of the dominant SHAP drivers."""
    top_features = importance_df.head(top_n).copy()
    top_features["driver_direction_note"] = np.where(
        top_features["mean_signed_shap"] >= 0,
        "positive average contribution to late-delivery risk",
        "negative average contribution to late-delivery risk",
    )
    return top_features[
        [
            "rank",
            "feature_name",
            "mean_abs_shap",
            "importance_share",
            "mean_signed_shap",
            "driver_direction_note",
        ]
    ]


def write_feature_plot(driver_summary_df: pd.DataFrame, output_path: Path) -> None:
    """Write a horizontal top-feature SHAP importance plot."""
    import matplotlib.pyplot as plt

    plot_df = driver_summary_df.sort_values("mean_abs_shap", ascending=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(plot_df["feature_name"], plot_df["mean_abs_shap"], color="#2f6f73")
    ax.set_title("AO1 XGBoost SHAP Feature Importance")
    ax.set_xlabel("Mean absolute SHAP value")
    ax.set_ylabel("Feature")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_findings(
    driver_summary_df: pd.DataFrame,
    config: AO1SHAPExplainabilityConfig,
    selected_candidate: str,
    sample_row_count: int,
) -> None:
    """Write the AO1 SHAP findings memo for report reuse."""
    lines = [
        "# AO1 SHAP Explainability",
        "",
        "Issue: `#30`",
        "",
        "## Scope",
        "",
        "This memo explains the selected AO1 XGBoost validation model using SHAP values "
        "computed on the validation slice only. The final test partition is not used.",
        "",
        "## Method",
        "",
        f"- Selected XGBoost candidate: `{selected_candidate}`.",
        f"- Validation rows explained: `{sample_row_count}`.",
        "- SHAP values are computed after the approved AO1 preprocessing pipeline.",
        "- Interpretations are model associations, not causal effects.",
        "",
        "## Dominant Late-Delivery Drivers",
        "",
        "| Rank | Feature | Mean Abs SHAP | Importance Share | Direction Note |",
        "| ---: | --- | ---: | ---: | --- |",
    ]

    for _, row in driver_summary_df.iterrows():
        lines.append(
            "| {rank} | `{feature_name}` | {mean_abs_shap:.6f} | {importance_share:.4f} | {driver_direction_note} |".format(
                **row.to_dict()
            )
        )

    lines.extend(
        [
            "",
            "## Business Plausibility Check",
            "",
            "The top drivers should be reviewed as operational signals related to order timing, "
            "shipping promise, geography, customer segment, and product/channel context. Any "
            "feature that appears to encode post-shipment outcomes must be treated as a leakage "
            "candidate and escalated before H1 is finalized.",
            "",
            "## Artifacts",
            "",
            f"- SHAP feature importance: `{config.shap_importance_output_path}`",
            f"- Driver summary: `{config.driver_summary_output_path}`",
            f"- Top-feature plot: `{config.figure_output_path}`",
            f"- Metadata: `{config.metadata_output_path}`",
        ]
    )

    config.findings_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.findings_output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Write JSON metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_ao1_shap_explainability(
    config: AO1SHAPExplainabilityConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Train selected XGBoost candidate and generate validation SHAP artifacts."""
    logger.info("Starting AO1 XGBoost SHAP explainability.")
    logger.info("AO1 partition input path: %s", config.partition_input_path)

    validate_volume_path(config.partition_input_path, "partition_input_path")
    spark = get_spark_session()
    partitioned_df = spark.read.format(config.read_format).load(config.partition_input_path)

    xgb_config = AO1XGBoostClassifierConfig(
        partition_input_path=config.partition_input_path,
        random_state=config.random_state,
    )
    train_pdf, validation_pdf, split_metadata = determine_modeling_slices(
        partitioned_df,
        xgb_config,
    )
    x_train = train_pdf.loc[:, list(FEATURE_COLUMNS)]
    y_train = train_pdf[TARGET_COLUMN].astype(int)
    x_validation_sample = sample_validation_frame(
        validation_pdf.loc[:, list(FEATURE_COLUMNS)],
        config.max_validation_sample_rows,
        config.random_state,
    )

    candidate_id = selected_candidate_id(config)
    candidate_parameters = select_candidate_parameters(
        build_candidate_parameter_sets(xgb_config, y_train),
        candidate_id,
    )
    pipeline = build_xgboost_pipeline(candidate_parameters)
    pipeline.fit(x_train, y_train)

    shap_importance_df = compute_shap_importance(pipeline, x_validation_sample)
    driver_summary_df = build_driver_summary(
        shap_importance_df,
        config.top_n_features,
    )

    config.shap_importance_output_path.parent.mkdir(parents=True, exist_ok=True)
    shap_importance_df.to_csv(config.shap_importance_output_path, index=False)
    config.driver_summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    driver_summary_df.to_csv(config.driver_summary_output_path, index=False)
    write_feature_plot(driver_summary_df, config.figure_output_path)
    write_findings(
        driver_summary_df,
        config,
        candidate_id,
        len(x_validation_sample),
    )

    metadata = {
        "metadata_status": "ao1_shap_explainability_completed",
        "issue": "#30",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "selected_model": "ao1_xgboost_classifier",
        "selected_candidate_id": candidate_id,
        "final_test_used": False,
        "training_slice": split_metadata["training_slice"],
        "validation_slice": split_metadata["validation_slice"],
        "sample_row_count": int(len(x_validation_sample)),
        "top_n_features": int(config.top_n_features),
        "target_column": TARGET_COLUMN,
        "artifacts": {
            "shap_importance_csv": str(config.shap_importance_output_path),
            "driver_summary_csv": str(config.driver_summary_output_path),
            "top_features_figure": str(config.figure_output_path),
            "findings_markdown": str(config.findings_output_path),
            "metadata_json": str(config.metadata_output_path),
        },
        "interpretation_limits": [
            "SHAP values explain model behavior on validation rows only.",
            "SHAP values are not causal effects.",
            "Preprocessed one-hot features may split one business concept across multiple rows.",
        ],
    }
    write_json(metadata, config.metadata_output_path)

    logger.info("AO1 SHAP feature importance written: %s", config.shap_importance_output_path)
    logger.info("AO1 XGBoost SHAP explainability completed successfully.")
    return metadata


def main() -> None:
    """Run AO1 XGBoost SHAP explainability with default paths."""
    run_ao1_shap_explainability(
        AO1SHAPExplainabilityConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
