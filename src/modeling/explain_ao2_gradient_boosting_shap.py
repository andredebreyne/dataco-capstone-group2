"""Generate AO2 Gradient Boosting SHAP explainability artifacts.

This job explains the selected AO2 Gradient Boosting profitability model from
the issue #36 metadata. If a saved fitted pipeline is available, it is loaded.
Otherwise the selected candidate specification is deterministically
reconstructed from metadata and fit on the approved training slice only. SHAP
is computed on validation rows only; the final test partition is never used.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.modeling.build_ao2_preprocessing_pipeline import (
    FEATURE_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS,
)
from src.modeling.create_ao2_chronological_partitions import (
    AO2_PARTITION_OUTPUT_PATH,
    PARTITION_COLUMN,
    TARGET_COLUMN,
    TEST_LABEL,
)
from src.modeling.train_ao2_gradient_boosting_regressor import (
    AO2GradientBoostingRegressorConfig,
    MODEL_NAME,
    assert_feature_list_is_safe,
    build_xgboost_pipeline,
)
from src.modeling.train_ao2_ridge_baseline import (
    assert_required_columns_exist,
    assert_target_contract,
    assert_unique_keys,
    determine_modeling_slices,
    get_package_version,
    read_optional_json,
    validate_volume_path,
)


RANDOM_STATE = 42
PINNED_XGBOOST_VERSION = "2.0.3"
SHAP_METHOD = "TreeExplainer"
SHAP_OUTPUT_SPACE = "raw model output in predicted profit units"
MODEL_SOURCE_SAVED = "saved_model"
MODEL_SOURCE_RECONSTRUCTED = "deterministic_reconstruction"

FORBIDDEN_FEATURE_TOKENS = {
    "actual_delivery",
    "actual_profit",
    "ao3_order_value",
    "benefit_per_order",
    "chronological_row_number",
    "days_for_shipping_real",
    "delivery_status",
    "final_test",
    "gold_ao2_processed_timestamp",
    "held_out",
    "holdout",
    "late_delivery_risk",
    "order_date_dateorders",
    "order_id",
    "order_item_discount",
    "order_item_id",
    "order_item_profit_ratio",
    "order_item_total",
    "order_profit_per_order",
    "order_status",
    "partition",
    "product_price",
    "profit_margin",
    "profit_outcome",
    "profit_ratio",
    "realized_margin",
    "realized_profit",
    "sales",
    "sales_per_customer",
    "shipping_date",
    "split_partition",
    "test_partition",
}

CAUTION_FEATURE_TOKENS = {
    "item_discount_rate",
    "item_unit_price",
    "order_item_quantity",
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
class AO2SHAPExplainabilityConfig:
    """Configuration for AO2 Gradient Boosting SHAP explainability outputs."""

    partition_input_path: str = os.getenv(
        "DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH",
        AO2_PARTITION_OUTPUT_PATH,
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
    evaluation_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/evaluation/ao2_evaluation_metadata.json"
            ),
        )
    )
    shap_importance_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_IMPORTANCE_PATH",
            str(REPO_ROOT / "report/tables/ao2_shap_feature_importance.csv"),
        )
    )
    driver_summary_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_DRIVER_SUMMARY_PATH",
            str(REPO_ROOT / "report/tables/ao2_shap_driver_summary.csv"),
        )
    )
    findings_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_FINDINGS_PATH",
            str(REPO_ROOT / "report/tables/ao2_shap_explainability_findings.md"),
        )
    )
    figure_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_TOP_FEATURES_FIGURE_PATH",
            str(REPO_ROOT / "report/figures/modeling/ao2_shap_top_features.png"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json"
            ),
        )
    )
    read_format: str = "delta"
    max_validation_sample_rows: int = int(os.getenv("DATACO_AO2_SHAP_MAX_ROWS", "5000"))
    top_n_features: int = int(os.getenv("DATACO_AO2_SHAP_TOP_N", "20"))
    random_state: int = int(os.getenv("DATACO_AO2_SHAP_RANDOM_STATE", str(RANDOM_STATE)))
    inner_validation_ratio: float = float(os.getenv("DATACO_AO2_INNER_VALIDATION_RATIO", "0.20"))


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao2_shap_explainability")


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def normalize_feature_name(feature_name: str) -> str:
    """Return normalized feature text for target-policy token checks."""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(feature_name).strip().lower())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def matched_forbidden_tokens(feature_names: pd.Series) -> list[str]:
    """Return forbidden tokens found in normalized feature names."""
    normalized_features = feature_names.astype(str).map(normalize_feature_name)
    return sorted(
        token
        for token in FORBIDDEN_FEATURE_TOKENS
        if normalized_features.str.contains(token, regex=False).any()
    )


def assert_no_forbidden_feature_tokens(frame: pd.DataFrame) -> None:
    """Fail if model or SHAP outputs contain forbidden AO2 target/proxy fields."""
    matched = matched_forbidden_tokens(frame["feature_name"])
    if matched:
        raise ValueError(
            "AO2 SHAP output contains forbidden target/proxy/leakage feature tokens: "
            f"{matched}"
        )


def read_required_metadata(path: Path, description: str) -> dict[str, Any]:
    """Read a required JSON metadata artifact."""
    metadata = read_optional_json(path)
    if metadata is None:
        raise FileNotFoundError(
            f"AO2 SHAP explainability requires {description} at {path}. "
            "Run the upstream workflow first or set the corresponding DATACO_* path override. "
            "The job will not guess model-selection evidence."
        )
    return metadata


def validate_evaluation_dependency(metadata: dict[str, Any], path: Path) -> dict[str, Any]:
    """Validate that issue #37 evaluation evidence is available and non-test."""
    if metadata.get("metadata_status") != "ao2_validation_evaluation_completed":
        raise ValueError(
            "AO2 evaluation metadata is not marked complete. Expected "
            "`metadata_status = ao2_validation_evaluation_completed` at "
            f"{path}."
        )
    if metadata.get("final_test_used") is not False:
        raise ValueError(f"AO2 evaluation metadata indicates final test use at {path}.")
    return {
        "metadata_path": str(path),
        "metadata_status": metadata.get("metadata_status"),
        "evaluation_slice": metadata.get("evaluation_slice"),
        "comparison_status": metadata.get("comparison_status"),
        "final_test_used": metadata.get("final_test_used"),
    }


def selected_candidate_id(metadata: dict[str, Any], path: Path) -> str:
    """Return the selected AO2 Gradient Boosting candidate id from metadata."""
    candidate_id = (
        metadata.get("gradient_boosting_regressor", {}).get("selected_candidate_id")
        or metadata.get("selected_candidate")
    )
    if not candidate_id:
        raise ValueError(
            "AO2 Gradient Boosting metadata does not contain a selected candidate. "
            "Expected `gradient_boosting_regressor.selected_candidate_id` or "
            f"`selected_candidate` at {path}."
        )
    return str(candidate_id)


def selected_candidate_parameters(
    metadata: dict[str, Any],
    candidate_id: str,
    path: Path,
) -> dict[str, Any]:
    """Return selected candidate parameters without changing model selection."""
    candidate_results = metadata.get("candidate_results", [])
    matching = next(
        (
            candidate
            for candidate in candidate_results
            if candidate.get("candidate_id") == candidate_id and candidate.get("selected") is True
        ),
        None,
    )
    if matching is None:
        matching = next(
            (
                candidate
                for candidate in candidate_results
                if candidate.get("candidate_id") == candidate_id
            ),
            None,
        )
    if matching is None or not matching.get("model_parameters"):
        raise ValueError(
            f"Selected AO2 Gradient Boosting candidate `{candidate_id}` was not found "
            f"with model parameters in {path}. SHAP will not fall back to another candidate."
        )
    return {"candidate_id": candidate_id, **dict(matching["model_parameters"])}


def validate_selected_model_metadata(
    metadata: dict[str, Any],
    config: AO2SHAPExplainabilityConfig,
) -> None:
    """Validate selected-model metadata before explainability work starts."""
    if metadata.get("metadata_status") != "runtime_training_completed":
        raise ValueError(
            "AO2 Gradient Boosting metadata is not marked as a completed training run. "
            f"Path: {config.gradient_boosting_metadata_path}"
        )
    if metadata.get("target_column") != TARGET_COLUMN:
        raise ValueError(
            f"Expected AO2 target `{TARGET_COLUMN}` in selected model metadata; "
            f"found `{metadata.get('target_column')}`."
        )
    if metadata.get("split_metadata", {}).get("final_test_used") is not False:
        raise ValueError("Selected AO2 Gradient Boosting metadata indicates final test use.")
    if metadata.get("final_test_partition_status", {}).get("used_for_training") is not False:
        raise ValueError("Selected AO2 metadata does not confirm final-test training exclusion.")
    if metadata.get("ao3_order_value_excluded_as_predictor") is not True:
        raise ValueError("Selected AO2 metadata does not confirm ao3_order_value predictor exclusion.")


def validate_xgboost_version(metadata: dict[str, Any]) -> str:
    """Ensure the Databricks-stable XGBoost dependency is used when installed."""
    installed_version = get_package_version("xgboost")
    if installed_version and installed_version != PINNED_XGBOOST_VERSION:
        raise RuntimeError(
            "AO2 SHAP explainability is pinned to xgboost=="
            f"{PINNED_XGBOOST_VERSION} for Databricks reproducibility. "
            f"Detected xgboost=={installed_version}. Install dependencies from requirements.txt "
            "and restart Python before regenerating SHAP artifacts."
        )
    metadata_version = (
        metadata.get("gradient_boosting_regressor", {}).get("library_version")
        or metadata.get("versions", {}).get("xgboost")
    )
    return installed_version or metadata_version or PINNED_XGBOOST_VERSION


def shap_version() -> str | None:
    """Return installed SHAP version when available."""
    return get_package_version("shap")


def databricks_path_exists(path_value: str) -> bool:
    """Return whether a local or Databricks Volume path appears to exist."""
    try:
        if Path(path_value).exists():
            return True
    except OSError:
        pass

    databricks_utils = globals().get("dbutils")
    if databricks_utils is None:
        return False

    try:
        databricks_utils.fs.ls(path_value)
        return True
    except Exception:
        return False


def load_saved_pipeline_if_available(metadata: dict[str, Any]) -> tuple[Any | None, str]:
    """Load a saved fitted pipeline only when metadata records one."""
    artifacts = metadata.get("artifacts", {})
    saved = bool(artifacts.get("model_artifact_saved"))
    artifact_path = artifacts.get("model_artifact_path")
    if not saved:
        return None, MODEL_SOURCE_RECONSTRUCTED
    if not artifact_path:
        raise ValueError("AO2 metadata says a model artifact was saved, but no path is recorded.")
    if not databricks_path_exists(str(artifact_path)):
        raise FileNotFoundError(
            "AO2 metadata records a saved fitted model, but the artifact was not found: "
            f"{artifact_path}. Either restore the artifact or regenerate SHAP with metadata "
            "that accurately records deterministic reconstruction."
        )

    from joblib import load

    return load(str(artifact_path)), MODEL_SOURCE_SAVED


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
    *,
    model_name: str,
    input_slice: str,
    sample_size: int,
) -> pd.DataFrame:
    """Compute mean absolute SHAP importance for selected validation rows."""
    try:
        import shap
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency: shap. In Databricks, run "
            "`%pip install -r requirements.txt`, then restart Python."
        ) from exc

    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    transformed_validation = to_dense_array(preprocessor.transform(x_validation_sample))
    feature_names = preprocessor.get_feature_names_out()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(transformed_validation)
    shap_array = np.asarray(shap_values)
    if shap_array.ndim == 3:
        shap_array = shap_array[:, :, 0]

    mean_abs_shap = np.abs(shap_array).mean(axis=0)
    mean_signed_shap = shap_array.mean(axis=0)
    importance_df = pd.DataFrame(
        {
            "model_name": model_name,
            "feature_name": feature_names,
            "mean_abs_shap_value": mean_abs_shap,
            "mean_signed_shap_value": mean_signed_shap,
            "input_slice": input_slice,
            "sample_size": int(sample_size),
            "final_test_used": False,
        }
    )
    total_importance = float(importance_df["mean_abs_shap_value"].sum())
    importance_df["importance_share"] = (
        importance_df["mean_abs_shap_value"] / total_importance if total_importance else 0.0
    )
    importance_df["rank"] = (
        importance_df["mean_abs_shap_value"].rank(method="first", ascending=False).astype(int)
    )
    importance_df = importance_df.sort_values(["rank", "feature_name"]).reset_index(drop=True)
    assert_no_forbidden_feature_tokens(importance_df)
    return importance_df


def infer_driver_category(feature_name: str) -> str:
    """Infer a compact business category from a transformed feature name."""
    normalized = normalize_feature_name(feature_name)
    if "shipping" in normalized or "same_day" in normalized or "standard_shipping" in normalized:
        return "shipping_service"
    if "country" in normalized or "state" in normalized or "region" in normalized or "market" in normalized or "geo" in normalized:
        return "geography"
    if "product_category" in normalized or "product_department" in normalized:
        return "product_mix"
    if "customer_segment" in normalized or "customer_" in normalized:
        return "customer_context"
    if "discount" in normalized:
        return "discount_policy"
    if "quantity" in normalized:
        return "order_quantity"
    if "price" in normalized:
        return "commercial_price"
    if "order_year" in normalized or "order_month" in normalized or "order_day" in normalized or "order_hour" in normalized or "season" in normalized or "week" in normalized:
        return "order_timing"
    if normalized.startswith("binary_flags"):
        return "order_flag"
    return "other"


def target_policy_status(feature_name: str) -> str:
    """Classify a SHAP feature against the focused AO2 target-policy guardrail."""
    normalized = normalize_feature_name(feature_name)
    if any(token in normalized for token in FORBIDDEN_FEATURE_TOKENS):
        return "forbidden"
    if any(token in normalized for token in CAUTION_FEATURE_TOKENS):
        return "caution"
    if infer_driver_category(feature_name) in {"geography", "product_mix"}:
        return "caution"
    return "allowed"


def interpretation_note(feature_name: str) -> str:
    """Return a compact interpretation note for a transformed SHAP feature."""
    category = infer_driver_category(feature_name)
    notes = {
        "shipping_service": "Shipping promise or planned service level can reflect fulfillment cost and service mix.",
        "geography": "Geographic one-hot levels may capture regional commercial patterns; review sparsity before broad claims.",
        "product_mix": "Product category or department can reflect assortment-level margin differences.",
        "customer_context": "Customer segment or location context can reflect demand and service-cost patterns.",
        "discount_policy": "Discount-rate features are approved predictors but need caution because AO2 target reconstruction is a known risk.",
        "order_quantity": "Quantity is an approved commercial predictor but should be interpreted cautiously near profitability formulas.",
        "commercial_price": "Unit price is an approved commercial predictor but should be interpreted cautiously near profitability formulas.",
        "order_timing": "Order-time features may capture seasonality or time-varying commercial mix.",
        "order_flag": "Order-level flags may summarize pre-shipment operational context.",
        "other": "Driver is model-specific and should be interpreted as an association.",
    }
    return notes[category]


def business_plausibility_note(feature_name: str) -> str:
    """Return a business plausibility note for report-facing driver review."""
    status = target_policy_status(feature_name)
    category = infer_driver_category(feature_name)
    if status == "forbidden":
        return "Fails AO2 target-policy review and should not be present."
    if status == "caution" and category in {"commercial_price", "discount_policy", "order_quantity"}:
        return (
            "Commercially plausible and approved, but interpret cautiously because "
            "profitability prediction is vulnerable to target reconstruction."
        )
    if status == "caution":
        return (
            "Commercially plausible, but granular one-hot levels can be sparse or unstable "
            "and should not be overgeneralized."
        )
    return "Commercially plausible pre-shipment predictor family."


def build_driver_summary(importance_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Create a compact report-facing summary of dominant AO2 SHAP drivers."""
    top_features = importance_df.head(top_n).copy()
    top_features["driver_category"] = top_features["feature_name"].map(infer_driver_category)
    top_features["interpretation_note"] = top_features["feature_name"].map(interpretation_note)
    top_features["target_policy_status"] = top_features["feature_name"].map(target_policy_status)
    top_features["business_plausibility_note"] = top_features["feature_name"].map(
        business_plausibility_note
    )
    forbidden_rows = top_features[top_features["target_policy_status"] == "forbidden"]
    if not forbidden_rows.empty:
        raise ValueError(
            "Top AO2 SHAP drivers include forbidden target-policy fields: "
            f"{forbidden_rows['feature_name'].tolist()}"
        )
    return top_features[
        [
            "feature_name",
            "rank",
            "mean_abs_shap_value",
            "importance_share",
            "mean_signed_shap_value",
            "driver_category",
            "interpretation_note",
            "target_policy_status",
            "business_plausibility_note",
            "model_name",
            "input_slice",
            "sample_size",
            "final_test_used",
        ]
    ]


def write_feature_plot(driver_summary_df: pd.DataFrame, output_path: Path) -> None:
    """Write a horizontal top-feature SHAP importance plot."""
    import matplotlib.pyplot as plt

    plot_df = driver_summary_df.sort_values("mean_abs_shap_value", ascending=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(plot_df["feature_name"], plot_df["mean_abs_shap_value"], color="#256f7a")
    ax.set_title("AO2 Gradient Boosting SHAP Feature Importance")
    ax.set_xlabel("Mean absolute SHAP value")
    ax.set_ylabel("Feature")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_findings(
    driver_summary_df: pd.DataFrame,
    config: AO2SHAPExplainabilityConfig,
    *,
    selected_candidate: str,
    model_source: str,
    input_slice: str,
    sample_size: int,
) -> None:
    """Write the AO2 SHAP findings memo for report reuse."""
    top_feature_names = driver_summary_df["feature_name"].astype(str).head(5).tolist()
    top_driver_text = ", ".join(f"`{feature}`" for feature in top_feature_names)
    caution_features = driver_summary_df[
        driver_summary_df["target_policy_status"] == "caution"
    ]["feature_name"].astype(str).tolist()
    caution_text = (
        ", ".join(f"`{feature}`" for feature in caution_features[:8])
        if caution_features
        else "none among the top drivers"
    )

    lines = [
        "# AO2 SHAP Explainability Findings",
        "",
        "Issue: `#38`",
        "",
        "## Scope",
        "",
        "This memo explains the selected AO2 Gradient Boosting profitability model using SHAP values computed on validation rows only. The final test partition is not used for fitting, SHAP calculation, plots, findings, or validation.",
        "",
        "## Method",
        "",
        f"- Selected model: `{MODEL_NAME}`.",
        f"- Selected candidate: `{selected_candidate}`.",
        f"- Model source: `{model_source}`.",
        f"- Input slice: `{input_slice}`.",
        f"- Validation rows explained: `{sample_size}`.",
        f"- SHAP method: `{SHAP_METHOD}`.",
        f"- SHAP output space: `{SHAP_OUTPUT_SPACE}`.",
        "- Preprocessing is the approved AO2 preprocessing pipeline, fit on the selected model training slice only.",
        "- Interpretations are model explanations and associations, not causal effects.",
        "- Changing a SHAP driver should not be interpreted as guaranteed to change order profitability.",
        "",
        "## Top Drivers",
        "",
        "| Rank | Feature | Mean Abs SHAP | Importance Share | Target Policy | Business Note |",
        "| ---: | --- | ---: | ---: | --- | --- |",
    ]

    for _, row in driver_summary_df.iterrows():
        lines.append(
            "| {rank} | `{feature_name}` | {mean_abs_shap_value:.6f} | {importance_share:.4f} | {target_policy_status} | {business_plausibility_note} |".format(
                **row.to_dict()
            )
        )

    lines.extend(
        [
            "",
            "## Business Plausibility Review",
            "",
            f"The dominant AO2 SHAP drivers in this run are {top_driver_text}. These drivers are commercially plausible when they represent shipping service, geography, product mix, customer context, timing, discount rate, unit price, or quantity. Granular one-hot features should be interpreted as model-specific category associations and not broad structural conclusions unless the team reviews support counts.",
            "",
            "If `item_unit_price`, `item_discount_rate`, or `order_item_quantity` appear as top drivers, they are approved commercial predictors but require caution because AO2 target reconstruction is a known methodological risk.",
            "",
            "## Target-Policy Review",
            "",
            "The SHAP artifact generation checks both approved raw feature names and transformed feature names for AO2 target/proxy, leakage, identifier, partition, lineage, and final-test tokens. The top-driver target-policy statuses are recorded in the driver summary.",
            "",
            f"Caution-status top drivers: {caution_text}.",
            "",
            "Forbidden target/proxy fields such as `Order_Profit_Per_Order`, `Benefit_per_order`, `Order_Item_Profit_Ratio`, `Order_Item_Total`, `ao3_order_value`, `Sales`, `Sales_per_customer`, `Order_Item_Discount`, `Product_Price`, delivery outcome fields, post-shipment fields, partition labels, and identifiers must not appear as SHAP drivers.",
            "",
            "## Caveats",
            "",
            "- SHAP values explain the selected model behavior on validation rows only.",
            "- SHAP values are associations, not causal effects.",
            "- One-hot encoded levels may be sparse, granular, or unstable.",
            "- The final test partition was not used.",
            "- This explainability step does not change AO2 model selection, target policy, preprocessing, AO3 margin scoring, or H2 final-test conclusions.",
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


def run_ao2_shap_explainability(
    config: AO2SHAPExplainabilityConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Generate validation-only SHAP artifacts for the selected AO2 model."""
    logger.info("Starting AO2 Gradient Boosting SHAP explainability.")
    logger.info("AO2 partition input path: %s", config.partition_input_path)

    validate_volume_path(config.partition_input_path, "partition_input_path")
    assert_feature_list_is_safe()

    gradient_boosting_metadata = read_required_metadata(
        config.gradient_boosting_metadata_path,
        "selected AO2 Gradient Boosting metadata",
    )
    validate_selected_model_metadata(gradient_boosting_metadata, config)
    evaluation_dependency = validate_evaluation_dependency(
        read_required_metadata(config.evaluation_metadata_path, "AO2 evaluation metadata"),
        config.evaluation_metadata_path,
    )
    xgboost_version = validate_xgboost_version(gradient_boosting_metadata)

    selected_candidate = selected_candidate_id(
        gradient_boosting_metadata,
        config.gradient_boosting_metadata_path,
    )
    selected_parameters = selected_candidate_parameters(
        gradient_boosting_metadata,
        selected_candidate,
        config.gradient_boosting_metadata_path,
    )

    spark = get_spark_session()
    partitioned_df = spark.read.format(config.read_format).load(config.partition_input_path)
    assert_required_columns_exist(partitioned_df)
    assert_target_contract(partitioned_df)
    assert_unique_keys(partitioned_df)

    training_config = AO2GradientBoostingRegressorConfig(
        partition_input_path=config.partition_input_path,
        read_format=config.read_format,
        inner_validation_ratio=config.inner_validation_ratio,
        random_state=config.random_state,
    )
    train_pdf, validation_pdf, split_metadata = determine_modeling_slices(
        partitioned_df,
        training_config,
    )
    if split_metadata.get("final_test_used") is not False:
        raise ValueError("AO2 SHAP split metadata indicates final test use.")
    input_slice = str(split_metadata["validation_slice"])
    if input_slice.lower() in {TEST_LABEL, "final_test", "holdout", "held_out"}:
        raise ValueError(f"AO2 SHAP input slice cannot be final test: {input_slice}")

    pipeline, model_source = load_saved_pipeline_if_available(gradient_boosting_metadata)
    if pipeline is None:
        logger.info(
            "No saved selected AO2 Gradient Boosting model artifact is recorded; "
            "reconstructing selected candidate %s deterministically.",
            selected_candidate,
        )
        x_train = train_pdf.loc[:, list(FEATURE_COLUMNS)]
        y_train = train_pdf[TARGET_COLUMN].astype(float)
        pipeline = build_xgboost_pipeline(selected_parameters)
        pipeline.fit(x_train, y_train)

    x_validation_sample = sample_validation_frame(
        validation_pdf.loc[:, list(FEATURE_COLUMNS)],
        config.max_validation_sample_rows,
        config.random_state,
    )

    shap_importance_df = compute_shap_importance(
        pipeline,
        x_validation_sample,
        model_name=MODEL_NAME,
        input_slice=input_slice,
        sample_size=len(x_validation_sample),
    )
    driver_summary_df = build_driver_summary(shap_importance_df, config.top_n_features)

    config.shap_importance_output_path.parent.mkdir(parents=True, exist_ok=True)
    shap_importance_df.to_csv(config.shap_importance_output_path, index=False)
    config.driver_summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    driver_summary_df.to_csv(config.driver_summary_output_path, index=False)
    write_feature_plot(driver_summary_df.head(15), config.figure_output_path)
    write_findings(
        driver_summary_df,
        config,
        selected_candidate=selected_candidate,
        model_source=model_source,
        input_slice=input_slice,
        sample_size=len(x_validation_sample),
    )

    forbidden_tokens_found = matched_forbidden_tokens(shap_importance_df["feature_name"])
    target_policy_status_value = "passed" if not forbidden_tokens_found else "failed"
    metadata = {
        "metadata_status": "ao2_shap_explainability_completed",
        "issue": "#38",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "selected_model_name": MODEL_NAME,
        "selected_candidate_name": selected_candidate,
        "selected_candidate_id": selected_candidate,
        "selected_model_parameters": {
            key: value
            for key, value in selected_parameters.items()
            if key != "candidate_id"
        },
        "model_source": model_source,
        "model_source_detail": {
            "saved_model_available": model_source == MODEL_SOURCE_SAVED,
            "deterministic_reconstruction_used": model_source == MODEL_SOURCE_RECONSTRUCTED,
            "explanation": (
                "SHAP explains the saved selected pipeline when available; otherwise it explains "
                "the deterministically reconstructed selected-model specification from issue #36 metadata."
            ),
            "no_new_model_selection": True,
        },
        "selected_model_metadata_path": str(config.gradient_boosting_metadata_path),
        "input_partition_path": config.partition_input_path,
        "input_slice": input_slice,
        "training_slice": split_metadata.get("training_slice"),
        "validation_slice": split_metadata.get("validation_slice"),
        "final_test_used": False,
        "target_column": TARGET_COLUMN,
        "preprocessing_reference": gradient_boosting_metadata.get("preprocessing_reference"),
        "shap_method": SHAP_METHOD,
        "model_output_space": SHAP_OUTPUT_SPACE,
        "sample_size": int(len(x_validation_sample)),
        "sampling": {
            "strategy": "validation_slice_full_or_fixed_random_sample",
            "max_validation_sample_rows": int(config.max_validation_sample_rows),
            "validation_rows_available": int(len(validation_pdf)),
            "sampled_from_final_test": False,
        },
        "random_state": int(config.random_state),
        "xgboost_version": xgboost_version,
        "shap_version": shap_version(),
        "feature_count": int(len(shap_importance_df)),
        "top_driver_count": int(len(driver_summary_df)),
        "top_n_features": int(config.top_n_features),
        "forbidden_feature_check_status": target_policy_status_value,
        "forbidden_feature_tokens_found": forbidden_tokens_found,
        "raw_feature_check_status": "passed",
        "target_policy_check_status": target_policy_status_value,
        "evaluation_dependency_status": evaluation_dependency,
        "selected_model_split_metadata": gradient_boosting_metadata.get("split_metadata"),
        "selected_model_final_test_partition_status": gradient_boosting_metadata.get(
            "final_test_partition_status"
        ),
        "raw_feature_count": int(len(FEATURE_COLUMNS)),
        "raw_feature_columns": list(FEATURE_COLUMNS),
        "forbidden_target_reconstruction_columns": list(FORBIDDEN_TARGET_RECONSTRUCTION_COLUMNS),
        "forbidden_leakage_columns": list(FORBIDDEN_LEAKAGE_COLUMNS),
        "output_artifact_paths": {
            "shap_feature_importance_csv": str(config.shap_importance_output_path),
            "shap_driver_summary_csv": str(config.driver_summary_output_path),
            "shap_findings_markdown": str(config.findings_output_path),
            "shap_top_features_figure": str(config.figure_output_path),
            "metadata_json": str(config.metadata_output_path),
        },
        "artifacts": {
            "shap_feature_importance_csv": str(config.shap_importance_output_path),
            "shap_driver_summary_csv": str(config.driver_summary_output_path),
            "shap_findings_markdown": str(config.findings_output_path),
            "shap_top_features_figure": str(config.figure_output_path),
            "metadata_json": str(config.metadata_output_path),
        },
        "limitations": [
            "SHAP values explain model behavior on validation rows only.",
            "SHAP values are model explanations and associations, not causal effects.",
            "One-hot encoded categorical levels can be granular, sparse, or unstable.",
            "Approved commercial predictors such as unit price, discount rate, and quantity should still be interpreted cautiously for AO2.",
            "The final test partition is not used.",
            "This workflow does not change AO2 model selection, target policy, preprocessing, AO3 margin scoring, or H2 final-test conclusions.",
        ],
    }
    write_json(metadata, config.metadata_output_path)

    logger.info("AO2 SHAP feature importance written: %s", config.shap_importance_output_path)
    logger.info("AO2 Gradient Boosting SHAP explainability completed successfully.")
    return metadata


def main() -> None:
    """Run AO2 Gradient Boosting SHAP explainability with default paths."""
    run_ao2_shap_explainability(
        AO2SHAPExplainabilityConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
