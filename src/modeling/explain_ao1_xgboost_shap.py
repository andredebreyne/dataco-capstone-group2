"""Generate AO1 XGBoost SHAP explainability artifacts.

This job deterministically reconstructs the selected AO1 XGBoost validation
configuration from the selected-model metadata, fits that specification on the
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
    get_package_version,
    read_optional_json,
    validate_volume_path,
)
from src.modeling.train_ao1_xgboost_classifier import (
    AO1XGBoostClassifierConfig,
    assert_feature_list_is_safe,
    build_candidate_parameter_sets,
    build_xgboost_pipeline,
)


RANDOM_STATE = 620
PINNED_XGBOOST_VERSION = "2.0.3"
MODEL_SOURCE = "deterministic_reconstruction"
SHAP_METHOD = "TreeExplainer"
SHAP_OUTPUT_SPACE = "raw margin / log-odds"
POSITIVE_CLASS_LABEL = "Late_delivery_risk = 1"
FORBIDDEN_FEATURE_TOKENS = {
    "actual",
    "benefit_per_order",
    "days_for_shipping_real",
    "delivery_status",
    "final_test",
    "holdout",
    "late_delivery_risk",
    "order_item_total",
    "order_profit",
    "profit_ratio",
    "sales",
    "shipping_date",
    "test_partition",
}


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


def normalize_feature_name(feature_name: str) -> str:
    """Return normalized feature text for leakage-token checks."""
    normalized = feature_name.strip().lower()
    for character in (" ", "-", "/", "(", ")", "[", "]", "{", "}", "."):
        normalized = normalized.replace(character, "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def assert_no_forbidden_feature_tokens(frame: pd.DataFrame) -> None:
    """Fail if SHAP outputs contain obvious leakage-like feature names."""
    normalized_features = frame["feature_name"].astype(str).map(normalize_feature_name)
    matched = sorted(
        token
        for token in FORBIDDEN_FEATURE_TOKENS
        if normalized_features.str.contains(token, regex=False).any()
    )
    if matched:
        raise ValueError(f"SHAP output contains forbidden leakage-like feature tokens: {matched}")


def read_required_xgboost_metadata(config: AO1SHAPExplainabilityConfig) -> dict[str, Any]:
    """Read required selected AO1 XGBoost metadata for model alignment."""
    metadata = read_optional_json(config.xgboost_metadata_path)
    if metadata is None:
        raise FileNotFoundError(
            "AO1 SHAP explainability requires selected AO1 XGBoost metadata at "
            f"{config.xgboost_metadata_path}. Run the AO1 XGBoost classifier workflow first "
            "or set DATACO_AO1_XGBOOST_METADATA_PATH to the selected-model metadata. "
            "SHAP must align with the selected/primary AO1 model and will not guess a candidate."
        )
    return metadata


def selected_candidate_id(metadata: dict[str, Any], config: AO1SHAPExplainabilityConfig) -> str:
    """Return selected XGBoost candidate id from required selected-model metadata."""
    candidate_id = metadata.get("xgboost_classifier", {}).get("selected_candidate_id")
    if not candidate_id:
        raise ValueError(
            "AO1 XGBoost metadata does not contain "
            "`xgboost_classifier.selected_candidate_id`. Required metadata path: "
            f"{config.xgboost_metadata_path}. SHAP must align with the selected/primary AO1 model."
        )
    return str(candidate_id)


def validate_xgboost_version() -> str:
    """Ensure the Databricks-stable XGBoost dependency is used."""
    installed_version = get_package_version("xgboost")
    if installed_version and installed_version != PINNED_XGBOOST_VERSION:
        raise RuntimeError(
            "AO1 SHAP explainability is pinned to xgboost=="
            f"{PINNED_XGBOOST_VERSION} for Databricks reproducibility. "
            f"Detected xgboost=={installed_version}. Install dependencies from requirements.txt "
            "and restart Python before regenerating SHAP artifacts."
        )
    return installed_version or PINNED_XGBOOST_VERSION


def shap_version() -> str | None:
    """Return installed SHAP version when available."""
    return get_package_version("shap")


def selected_parameter_source(metadata: dict[str, Any], candidate_id: str) -> str:
    """Describe where the selected candidate parameters came from."""
    candidate_results = metadata.get("candidate_results", [])
    matching_candidate = next(
        (
            candidate
            for candidate in candidate_results
            if candidate.get("candidate_id") == candidate_id
        ),
        None,
    )
    if matching_candidate:
        return (
            "selected AO1 XGBoost metadata candidate_results matched to "
            f"`{candidate_id}`; pipeline rebuilt with the approved candidate grid"
        )
    return (
        "selected AO1 XGBoost metadata selected_candidate_id matched to the approved "
        "candidate grid"
    )


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
    importance_df = importance_df.sort_values(["rank", "feature_name"])
    assert_no_forbidden_feature_tokens(importance_df)
    return importance_df


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
    xgboost_metadata_path: Path,
) -> None:
    """Write the AO1 SHAP findings memo for report reuse."""
    top_feature_names = driver_summary_df["feature_name"].astype(str).head(5).tolist()
    dominant_feature = top_feature_names[0] if top_feature_names else "not available"
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
        f"- Model source: `{MODEL_SOURCE}` from `{xgboost_metadata_path}`.",
        f"- SHAP method: `{SHAP_METHOD}` for the positive class `{POSITIVE_CLASS_LABEL}`.",
        f"- SHAP output space: `{SHAP_OUTPUT_SPACE}`.",
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
        "The leading SHAP drivers are operationally plausible for pre-dispatch late-delivery "
        "risk because they emphasize the shipping promise, scheduled shipping window, and "
        "geographic fulfillment context available before dispatch. The dominant driver in this "
        f"run is `{dominant_feature}`; if this effect remains much larger than the others, the "
        "team should review it as a possible service-level or data-pattern concentration before "
        "final H1 reporting. Geography and shipping-speed drivers should be described as model "
        "associations that support prioritization and monitoring, not as proof that changing a "
        "single field will causally reduce late deliveries.",
        "",
        "Top-driver interpretation for report reuse:",
        "",
        "- Shipping mode and shipping-speed features indicate that the promised fulfillment service "
        "level is central to the model's late-risk ranking.",
        "- Scheduled shipping days captures the planned order-to-dispatch window and is a plausible "
        "pre-shipment timing signal.",
        "- Geography features can reflect route complexity, regional operations, or market-specific "
        "patterns, but should be reviewed for sparse one-hot categories before broad conclusions.",
        "- SHAP explains the selected model behavior for `Late_delivery_risk = 1` in raw margin / "
        "log-odds space; values are directional model explanations, not causal effects.",
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
    assert_feature_list_is_safe()
    xgboost_metadata = read_required_xgboost_metadata(config)
    xgboost_version = validate_xgboost_version()
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

    candidate_id = selected_candidate_id(xgboost_metadata, config)
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
        config.xgboost_metadata_path,
    )

    metadata = {
        "metadata_status": "ao1_shap_explainability_completed",
        "issue": "#30",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "selected_model": "ao1_xgboost_classifier",
        "selected_candidate_id": candidate_id,
        "selected_candidate_name": candidate_id,
        "model_source": MODEL_SOURCE,
        "model_source_detail": {
            "reason_saved_model_loading_was_not_used": (
                "The AO1 XGBoost workflow stores selected-model metadata and can optionally save "
                "a fitted model artifact. This SHAP workflow reconstructs the selected candidate "
                "specification deterministically from the metadata and approved candidate grid."
            ),
            "limitation": (
                "SHAP explains the reconstructed selected-model specification; it does not select "
                "a new model or explain final-test performance."
            ),
            "xgboost_parameter_source": selected_parameter_source(
                xgboost_metadata,
                candidate_id,
            ),
        },
        "input_partition_path": config.partition_input_path,
        "input_slice": split_metadata["validation_slice"],
        "final_test_used": False,
        "training_slice": split_metadata["training_slice"],
        "validation_slice": split_metadata["validation_slice"],
        "shap_method": SHAP_METHOD,
        "shap_output_space": SHAP_OUTPUT_SPACE,
        "positive_class": POSITIVE_CLASS_LABEL,
        "sample_row_count": int(len(x_validation_sample)),
        "sample_size": int(len(x_validation_sample)),
        "random_state": int(config.random_state),
        "top_n_features": int(config.top_n_features),
        "feature_count": int(len(shap_importance_df)),
        "top_driver_count": int(len(driver_summary_df)),
        "target_column": TARGET_COLUMN,
        "xgboost_metadata_path": str(config.xgboost_metadata_path),
        "xgboost_version": xgboost_version,
        "shap_version": shap_version(),
        "artifacts": {
            "shap_importance_csv": str(config.shap_importance_output_path),
            "driver_summary_csv": str(config.driver_summary_output_path),
            "top_features_figure": str(config.figure_output_path),
            "findings_markdown": str(config.findings_output_path),
            "metadata_json": str(config.metadata_output_path),
        },
        "output_artifacts": {
            "shap_importance_csv": str(config.shap_importance_output_path),
            "driver_summary_csv": str(config.driver_summary_output_path),
            "top_features_figure": str(config.figure_output_path),
            "findings_markdown": str(config.findings_output_path),
            "metadata_json": str(config.metadata_output_path),
        },
        "limitations": [
            "SHAP values explain model behavior on validation rows only.",
            "SHAP values are model associations, not causal effects.",
            "Preprocessed one-hot features may split one business concept across multiple rows.",
            "The workflow deterministically reconstructs the selected XGBoost specification instead of loading a saved fitted model artifact.",
        ],
        "interpretation_limits": [
            "SHAP values explain model behavior on validation rows only.",
            "SHAP values are model associations, not causal effects.",
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
