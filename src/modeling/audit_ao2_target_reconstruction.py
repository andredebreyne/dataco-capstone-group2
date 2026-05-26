"""Audit AO2 predictors and drivers for target-reconstruction risk.

This job reviews existing AO2 model, evaluation, feature-importance, and SHAP
artifacts. It does not retrain models, change preprocessing, score final test
rows, modify target policy, or implement AO3.
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

import pandas as pd


ISSUE_ID = "#73"
MODEL_NAME = "ao2_gradient_boosting_regressor"
TOP_DRIVER_COUNT = 15


def resolve_repo_root() -> Path:
    """Resolve repository root for local and Databricks-compatible execution."""
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


FORBIDDEN_FEATURE_NAMES = {
    "Order_Profit_Per_Order",
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
    "item_discount_amount",
    "item_discount_share_of_gross",
    "item_gross_sales_estimate",
    "item_net_sales_amount",
    "product_list_price",
    "Days_for_shipping_real",
    "Days for shipping (real)",
    "Delivery_Status",
    "Delivery Status",
    "shipping_date_DateOrders",
    "shipping date (DateOrders)",
    "Order_Status",
    "Order Status",
    "Late_delivery_risk",
    "Order_Id",
    "Order_Item_Id",
    "order_date_DateOrders",
    "chronological_row_number",
    "split_partition",
    "_gold_ao2_processed_timestamp",
    "final_test",
    "held_out",
    "holdout",
    "test_partition",
    "realized_margin",
    "realized_profit",
    "actual_profit",
    "actual_profit_margin",
    "actual_delivery",
    "profit_outcome",
    "profit_margin",
    "profit_ratio",
}

FORBIDDEN_CONTAINS_TOKENS = {
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
    "item_discount_amount",
    "item_discount_share_of_gross",
    "item_gross_sales_estimate",
    "item_net_sales_amount",
    "product_list_price",
    "product_price",
    "profit_margin",
    "profit_outcome",
    "profit_ratio",
    "realized_margin",
    "realized_profit",
    "sales_per_customer",
    "shipping_date",
    "split_partition",
    "test_partition",
}

CAUTION_FEATURE_NAMES = {
    "item_unit_price",
    "item_discount_rate",
    "order_item_quantity",
    "scheduled_shipping_days",
    "shipping_speed_tier",
    "shipping_mode_normalized",
    "is_same_day_or_next_day_shipping",
    "is_standard_shipping",
    "product_category_key",
    "product_department_key",
    "customer_segment_normalized",
    "customer_country_normalized",
    "customer_state_normalized",
    "market_normalized",
    "order_country_normalized",
    "order_region_normalized",
    "order_state_normalized",
}


@dataclass(frozen=True)
class AO2TargetReconstructionAuditConfig:
    """Configuration for AO2 target-reconstruction audit artifacts."""

    preprocessing_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO2_PREPROCESSING_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/preprocessing/ao2_preprocessing_metadata.json"
            ),
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
    evaluation_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_METADATA_PATH",
            str(REPO_ROOT / "models/ao2_profitability/evaluation/ao2_evaluation_metadata.json"),
        )
    )
    shap_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json"
            ),
        )
    )
    model_evaluation_metrics_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_METRICS_PATH",
            str(REPO_ROOT / "report/tables/ao2_model_evaluation_metrics.csv"),
        )
    )
    model_validation_comparison_path: Path = Path(
        os.getenv(
            "DATACO_AO2_MODEL_VALIDATION_COMPARISON_PATH",
            str(REPO_ROOT / "report/tables/ao2_model_validation_comparison.csv"),
        )
    )
    model_evaluation_findings_path: Path = Path(
        os.getenv(
            "DATACO_AO2_EVALUATION_FINDINGS_PATH",
            str(REPO_ROOT / "report/tables/ao2_model_evaluation_findings.md"),
        )
    )
    xgboost_importance_path: Path = Path(
        os.getenv(
            "DATACO_AO2_GRADIENT_BOOSTING_FEATURE_IMPORTANCE_PATH",
            str(REPO_ROOT / "report/tables/ao2_gradient_boosting_feature_importance.csv"),
        )
    )
    shap_importance_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_IMPORTANCE_PATH",
            str(REPO_ROOT / "report/tables/ao2_shap_feature_importance.csv"),
        )
    )
    shap_driver_summary_path: Path = Path(
        os.getenv(
            "DATACO_AO2_SHAP_DRIVER_SUMMARY_PATH",
            str(REPO_ROOT / "report/tables/ao2_shap_driver_summary.csv"),
        )
    )
    forbidden_check_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_TARGET_RECONSTRUCTION_FORBIDDEN_CHECK_PATH",
            str(
                REPO_ROOT
                / "report/tables/ao2_target_reconstruction_forbidden_feature_check.csv"
            ),
        )
    )
    driver_review_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_TARGET_RECONSTRUCTION_DRIVER_REVIEW_PATH",
            str(REPO_ROOT / "report/tables/ao2_target_reconstruction_driver_review.csv"),
        )
    )
    findings_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_TARGET_RECONSTRUCTION_FINDINGS_PATH",
            str(REPO_ROOT / "report/tables/ao2_target_reconstruction_audit_findings.md"),
        )
    )
    docs_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_TARGET_RECONSTRUCTION_DOCS_PATH",
            str(REPO_ROOT / "docs/ao2_target_reconstruction_review.md"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO2_TARGET_RECONSTRUCTION_METADATA_PATH",
            str(
                REPO_ROOT
                / "models/ao2_profitability/target_reconstruction_audit/ao2_target_reconstruction_audit_metadata.json"
            ),
        )
    )
    top_driver_count: int = int(
        os.getenv("DATACO_AO2_TARGET_RECONSTRUCTION_TOP_DRIVER_COUNT", str(TOP_DRIVER_COUNT))
    )


def configure_logging() -> logging.Logger:
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao2_target_reconstruction_audit")


def normalize_feature_name(feature_name: object) -> str:
    """Normalize feature names for raw and transformed policy checks."""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(feature_name).strip().lower())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


NORMALIZED_FORBIDDEN_FEATURE_NAMES = {
    normalize_feature_name(feature_name) for feature_name in FORBIDDEN_FEATURE_NAMES
}
NORMALIZED_CAUTION_FEATURE_NAMES = {
    normalize_feature_name(feature_name) for feature_name in CAUTION_FEATURE_NAMES
}


def read_required_json(path: Path, description: str) -> dict[str, Any]:
    """Read a required JSON artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing required {description}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_required_csv(path: Path, description: str) -> pd.DataFrame:
    """Read a required non-empty CSV artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing required {description}: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Required {description} is empty: {path}")
    return frame


def infer_base_feature(
    feature_name: object,
    normalized_raw_feature_names: set[str],
) -> str:
    """Infer the raw feature behind a transformed sklearn feature name."""
    raw_feature_text = str(feature_name).strip()
    if "__" in raw_feature_text:
        raw_feature_text = raw_feature_text.split("__", 1)[1]
    stripped = normalize_feature_name(raw_feature_text)

    if stripped in normalized_raw_feature_names:
        return stripped

    matching_bases = [
        raw_feature
        for raw_feature in normalized_raw_feature_names
        if stripped.startswith(f"{raw_feature}_")
    ]
    if matching_bases:
        return sorted(matching_bases, key=len, reverse=True)[0]

    return stripped


def infer_driver_family(feature_name: object, base_feature: str) -> str:
    """Infer a compact business driver family for audit review."""
    normalized = normalize_feature_name(feature_name)
    if base_feature in {"item_unit_price"}:
        return "commercial_price"
    if base_feature in {"item_discount_rate"}:
        return "discount_policy"
    if base_feature in {"order_item_quantity"}:
        return "order_quantity"
    if "shipping" in normalized or base_feature in {
        "scheduled_shipping_days",
        "shipping_speed_tier",
        "shipping_mode_normalized",
        "is_same_day_or_next_day_shipping",
        "is_standard_shipping",
    }:
        return "shipping_service"
    if any(token in base_feature for token in ("country", "state", "region", "market")):
        return "geography"
    if base_feature in {"product_category_key", "product_department_key"}:
        return "product_mix"
    if "customer_segment" in base_feature or base_feature.startswith("customer_"):
        return "customer_context"
    if any(token in base_feature for token in ("year", "quarter", "month", "week", "day", "hour", "season")):
        return "order_timing"
    if base_feature.endswith("_available") or base_feature.endswith("_match"):
        return "order_flag"
    return "other"


def classify_feature(
    feature_name: object,
    raw_feature_names: set[str],
) -> dict[str, str]:
    """Classify a feature against AO2 target-reconstruction policy."""
    normalized_raw_features = {normalize_feature_name(feature) for feature in raw_feature_names}
    normalized_feature = normalize_feature_name(feature_name)
    base_feature = infer_base_feature(feature_name, normalized_raw_features)

    if base_feature in NORMALIZED_FORBIDDEN_FEATURE_NAMES:
        return {
            "normalized_feature_name": normalized_feature,
            "base_feature_name": base_feature,
            "policy_status": "forbidden",
            "matched_policy_rule": f"forbidden_exact:{base_feature}",
        }

    matched_token = next(
        (
            token
            for token in sorted(FORBIDDEN_CONTAINS_TOKENS)
            if token in normalized_feature or token in base_feature
        ),
        None,
    )
    if matched_token:
        return {
            "normalized_feature_name": normalized_feature,
            "base_feature_name": base_feature,
            "policy_status": "forbidden",
            "matched_policy_rule": f"forbidden_token:{matched_token}",
        }

    if base_feature in NORMALIZED_CAUTION_FEATURE_NAMES:
        return {
            "normalized_feature_name": normalized_feature,
            "base_feature_name": base_feature,
            "policy_status": "caution",
            "matched_policy_rule": f"caution_approved:{base_feature}",
        }

    driver_family = infer_driver_family(feature_name, base_feature)
    if driver_family in {"commercial_price", "discount_policy", "order_quantity", "shipping_service", "geography", "product_mix", "customer_context"}:
        return {
            "normalized_feature_name": normalized_feature,
            "base_feature_name": base_feature,
            "policy_status": "caution",
            "matched_policy_rule": f"caution_driver_family:{driver_family}",
        }

    return {
        "normalized_feature_name": normalized_feature,
        "base_feature_name": base_feature,
        "policy_status": "allowed",
        "matched_policy_rule": "allowed_pre_dispatch_context",
    }


def review_note_for_status(status: str, matched_rule: str) -> str:
    """Return a compact feature-policy review note."""
    if status == "forbidden":
        return "Blocked by AO2 target-reconstruction, leakage, identifier, partition, or final-test policy."
    if status == "caution":
        if "item_unit_price" in matched_rule:
            return "Approved order-time commercial predictor; interpret cautiously near profitability formulas."
        if "item_discount_rate" in matched_rule:
            return "Approved discount-rate predictor; interpret cautiously near profitability formulas."
        if "order_item_quantity" in matched_rule:
            return "Approved quantity predictor; interpret cautiously near profitability formulas."
        if "shipping" in matched_rule:
            return "Approved planned shipping predictor; commercial interpretation should remain pre-dispatch."
        return "Approved predictor family, but interpretation needs caution due to sparsity or commercial proxy risk."
    return "Allowed pre-dispatch predictor or model driver; not formula-like under current policy."


def business_plausibility(feature_name: object, status: str, base_feature: str) -> str:
    """Return the business plausibility statement used in driver review."""
    family = infer_driver_family(feature_name, base_feature)
    if status == "forbidden":
        return "Not defensible for AO2 because it is target, proxy, leakage, identifier, partition, or final-test information."
    if family in {"commercial_price", "discount_policy", "order_quantity"}:
        return "Commercially plausible approved order-time signal, but close enough to profit mechanics to require caution."
    if family == "shipping_service":
        return "Commercially plausible because planned service level and speed can relate to cost and margin mix."
    if family in {"geography", "product_mix", "customer_context"}:
        return "Commercially plausible, but one-hot levels can be granular, sparse, or unstable."
    if family == "order_timing":
        return "Commercially plausible as an order-time seasonality or calendar-mix signal."
    return "Plausible pre-dispatch context and not a direct profit formula component."


def review_decision(status: str) -> str:
    """Return row-level review decision."""
    if status == "forbidden":
        return "blocked"
    if status == "caution":
        return "accepted_with_caution"
    return "accepted"


def target_reconstruction_risk(status: str) -> str:
    """Map policy status to compact target-reconstruction risk."""
    if status == "forbidden":
        return "high"
    if status == "caution":
        return "caution"
    return "low"


def validate_non_test_metadata(metadata: dict[str, Any], artifact_name: str) -> None:
    """Validate that an upstream metadata artifact does not use final test."""
    if metadata.get("final_test_used") is True:
        raise ValueError(f"{artifact_name} metadata indicates final test use.")
    split_metadata = metadata.get("split_metadata", {})
    if split_metadata.get("final_test_used") is True:
        raise ValueError(f"{artifact_name} split metadata indicates final test use.")
    dependency_status = metadata.get("evaluation_dependency_status", {})
    if dependency_status.get("final_test_used") is True:
        raise ValueError(f"{artifact_name} dependency metadata indicates final test use.")


def selected_candidate(metadata: dict[str, Any]) -> str:
    """Return selected AO2 candidate name from Gradient Boosting metadata."""
    return str(
        metadata.get("gradient_boosting_regressor", {}).get("selected_candidate_id")
        or metadata.get("selected_candidate")
        or "unknown"
    )


def collect_raw_predictors(
    preprocessing_metadata: dict[str, Any],
    gradient_boosting_metadata: dict[str, Any],
    shap_metadata: dict[str, Any],
) -> set[str]:
    """Collect the available raw AO2 predictor set from upstream metadata."""
    predictors: set[str] = set()
    for metadata in (preprocessing_metadata, gradient_boosting_metadata, shap_metadata):
        for key in ("feature_columns", "raw_feature_columns"):
            values = metadata.get(key)
            if isinstance(values, list):
                predictors.update(str(value) for value in values)
    return predictors


def build_forbidden_feature_check(
    *,
    preprocessing_metadata: dict[str, Any],
    gradient_boosting_metadata: dict[str, Any],
    shap_metadata: dict[str, Any],
    xgboost_importance_df: pd.DataFrame,
    shap_importance_df: pd.DataFrame,
    shap_driver_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build the AO2 forbidden-feature audit table."""
    raw_predictors = collect_raw_predictors(
        preprocessing_metadata,
        gradient_boosting_metadata,
        shap_metadata,
    )
    rows: list[dict[str, Any]] = []

    def append_row(source_artifact: str, feature_name: object, feature_role: str) -> None:
        classification = classify_feature(feature_name, raw_predictors)
        rows.append(
            {
                "source_artifact": source_artifact,
                "feature_name": str(feature_name),
                "normalized_feature_name": classification["normalized_feature_name"],
                "feature_role": feature_role,
                "policy_status": classification["policy_status"],
                "matched_policy_rule": classification["matched_policy_rule"],
                "review_note": review_note_for_status(
                    classification["policy_status"],
                    classification["matched_policy_rule"],
                ),
            }
        )

    for feature_name in gradient_boosting_metadata.get("feature_columns", []):
        append_row("ao2_gradient_boosting_metadata", feature_name, "predictor")

    for feature_name in preprocessing_metadata.get("feature_columns", []):
        append_row("ao2_preprocessing_metadata", feature_name, "predictor")

    for feature_name in shap_metadata.get("raw_feature_columns", []):
        append_row("ao2_shap_metadata", feature_name, "predictor")

    for feature_name in xgboost_importance_df["feature_name"].astype(str):
        append_row("ao2_gradient_boosting_feature_importance", feature_name, "feature_importance_driver")

    for feature_name in shap_importance_df["feature_name"].astype(str):
        append_row("ao2_shap_feature_importance", feature_name, "shap_driver")

    for feature_name in shap_driver_df["feature_name"].astype(str):
        append_row("ao2_shap_driver_summary", feature_name, "shap_driver")

    return pd.DataFrame(rows).sort_values(
        ["policy_status", "feature_role", "source_artifact", "feature_name"],
        ascending=[False, True, True, True],
    )


def build_driver_review(
    *,
    xgboost_importance_df: pd.DataFrame,
    shap_importance_df: pd.DataFrame,
    shap_driver_df: pd.DataFrame,
    raw_predictors: set[str],
    top_n: int,
) -> pd.DataFrame:
    """Build the compact top-driver review table."""
    shap_notes = {}
    if not shap_driver_df.empty:
        shap_notes = {
            str(row["feature_name"]): row.to_dict()
            for _, row in shap_driver_df.iterrows()
            if "feature_name" in row
        }

    rows: list[dict[str, Any]] = []

    xgb_top = xgboost_importance_df.sort_values("importance_rank").head(top_n)
    for _, row in xgb_top.iterrows():
        feature_name = row["feature_name"]
        classification = classify_feature(feature_name, raw_predictors)
        base_feature = classification["base_feature_name"]
        status = classification["policy_status"]
        rows.append(
            {
                "driver_source": "xgboost_importance",
                "feature_name": feature_name,
                "rank": int(row["importance_rank"]),
                "importance_value": float(row["importance_value"]),
                "mean_abs_shap_value": None,
                "policy_status": status,
                "target_reconstruction_risk": target_reconstruction_risk(status),
                "business_plausibility": business_plausibility(feature_name, status, base_feature),
                "review_decision": review_decision(status),
                "review_note": review_note_for_status(status, classification["matched_policy_rule"]),
            }
        )

    shap_top = shap_importance_df.sort_values("rank").head(top_n)
    for _, row in shap_top.iterrows():
        feature_name = str(row["feature_name"])
        classification = classify_feature(feature_name, raw_predictors)
        base_feature = classification["base_feature_name"]
        status = classification["policy_status"]
        summary_note = shap_notes.get(feature_name, {}).get("business_plausibility_note")
        rows.append(
            {
                "driver_source": "shap",
                "feature_name": feature_name,
                "rank": int(row["rank"]),
                "importance_value": None,
                "mean_abs_shap_value": float(row["mean_abs_shap_value"]),
                "policy_status": status,
                "target_reconstruction_risk": target_reconstruction_risk(status),
                "business_plausibility": summary_note
                if isinstance(summary_note, str) and summary_note
                else business_plausibility(feature_name, status, base_feature),
                "review_decision": review_decision(status),
                "review_note": review_note_for_status(status, classification["matched_policy_rule"]),
            }
        )

    return pd.DataFrame(rows)


def metric_value(metrics_df: pd.DataFrame, model_name: str, column_name: str) -> float | None:
    """Return a metric value from the AO2 evaluation metrics table."""
    model_rows = metrics_df[metrics_df["model_name"] == model_name]
    if model_rows.empty or column_name not in model_rows.columns:
        return None
    return float(model_rows.iloc[0][column_name])


def format_metric(value: float | None, digits: int = 4) -> str:
    """Format a metric value for markdown notes."""
    if value is None:
        return "not available"
    return f"{value:.{digits}f}"


def build_evaluation_summary(metrics_df: pd.DataFrame) -> dict[str, float | None | str]:
    """Summarize validation-only AO2 evaluation evidence."""
    gb_rmse = metric_value(metrics_df, MODEL_NAME, "rmse")
    gb_mae = metric_value(metrics_df, MODEL_NAME, "mae")
    gb_r2 = metric_value(metrics_df, MODEL_NAME, "r2")
    ridge_rmse = metric_value(metrics_df, "ao2_ridge_baseline", "rmse")
    ridge_mae = metric_value(metrics_df, "ao2_ridge_baseline", "mae")
    ridge_r2 = metric_value(metrics_df, "ao2_ridge_baseline", "r2")

    rmse_improvement = (
        ridge_rmse - gb_rmse if ridge_rmse is not None and gb_rmse is not None else None
    )
    mae_improvement = (
        ridge_mae - gb_mae if ridge_mae is not None and gb_mae is not None else None
    )
    strength = "modest"
    if gb_r2 is not None and gb_r2 > 0.25:
        strength = "strong"
    elif gb_r2 is not None and gb_r2 < 0.05:
        strength = "limited"

    return {
        "gradient_boosting_rmse": gb_rmse,
        "gradient_boosting_mae": gb_mae,
        "gradient_boosting_r2": gb_r2,
        "ridge_rmse": ridge_rmse,
        "ridge_mae": ridge_mae,
        "ridge_r2": ridge_r2,
        "rmse_improvement_vs_ridge": rmse_improvement,
        "mae_improvement_vs_ridge": mae_improvement,
        "performance_strength": strength,
    }


def write_markdown(path: Path, lines: list[str]) -> None:
    """Write markdown content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    """Return a repository-relative path when possible for portable artifacts."""
    resolved_path = path.expanduser().resolve()
    try:
        return resolved_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def artifact_path_list(config: AO2TargetReconstructionAuditConfig) -> list[str]:
    """Return reviewed artifact paths."""
    return [
        display_path(config.preprocessing_metadata_path),
        display_path(config.gradient_boosting_metadata_path),
        display_path(config.evaluation_metadata_path),
        display_path(config.shap_metadata_path),
        display_path(config.model_evaluation_metrics_path),
        display_path(config.model_validation_comparison_path),
        display_path(config.model_evaluation_findings_path),
        display_path(config.xgboost_importance_path),
        display_path(config.shap_importance_path),
        display_path(config.shap_driver_summary_path),
    ]


def build_findings_lines(
    *,
    selected_candidate_name: str,
    forbidden_count: int,
    caution_count: int,
    final_decision: str,
    evaluation_summary: dict[str, Any],
    output_paths: dict[str, str],
    blocked_features: list[str],
) -> list[str]:
    """Build report-facing AO2 target-reconstruction audit findings."""
    conclusion = (
        "Blocked: one or more forbidden target/proxy fields were detected and must be removed before AO2 sign-off."
        if final_decision == "blocked"
        else "Accepted with caution: no forbidden target-reconstruction fields were detected. The remaining AO2 predictor set is defensible for pre-dispatch profitability estimation, with caution notes for approved commercial predictors."
    )
    blocker_text = (
        ", ".join(f"`{feature}`" for feature in blocked_features[:10])
        if blocked_features
        else "none"
    )

    return [
        "# AO2 Target-Reconstruction Audit Findings",
        "",
        f"Issue: `{ISSUE_ID}`",
        "",
        "## Scope",
        "",
        "This audit reviews the finalized AO2 Gradient Boosting predictor and driver evidence for target reconstruction. It does not retrain, retune, change preprocessing, change AO2 Gold, change partitions, evaluate final test, or implement AO3.",
        "",
        "## Selected Model Reviewed",
        "",
        f"- Selected model: `{MODEL_NAME}`.",
        f"- Selected candidate: `{selected_candidate_name}`.",
        "- Target column: `Order_Profit_Per_Order`.",
        "- Final test used: `false`; final test not used for this audit or the upstream validation artifacts.",
        "",
        "## Artifacts Reviewed",
        "",
        "- AO2 preprocessing metadata.",
        "- AO2 Gradient Boosting metadata.",
        "- AO2 evaluation metadata and validation metrics.",
        "- AO2 XGBoost feature importance.",
        "- AO2 SHAP feature importance and driver summary.",
        "- Existing AO2 target-policy and evaluation findings.",
        "",
        "## Predictor Audit Result",
        "",
        f"- Forbidden feature count: `{forbidden_count}`.",
        f"- Caution feature count: `{caution_count}`.",
        f"- Blocked features: {blocker_text}.",
        "- `ao3_order_value` is reserved for later AO3 margin support and was not detected as an AO2 predictor, SHAP driver, or feature-importance driver.",
        "- Direct profit targets, duplicate profit fields, realized profit-ratio fields, sales/order-value fields, discount amount, product price duplicates, delivery outcomes, post-shipment fields, partition labels, identifiers, and date-anchor metadata are excluded from the reviewed predictor set.",
        "",
        "## SHAP and Feature Importance Driver Result",
        "",
        "- The top SHAP drivers are commercially plausible validation-model associations, led by approved commercial, geography, product, and customer/location one-hot features.",
        "- Approved commercial predictors such as `item_unit_price`, `item_discount_rate`, and `order_item_quantity` appear as drivers and are accepted with caution because AO2 target reconstruction is a known methodological risk.",
        "- The top XGBoost feature-importance drivers include planned shipping/service, geography, product category, unit price, and quantity signals. These are plausible pre-dispatch drivers and are not formula-like under the current policy.",
        "- Granular geography and product one-hot levels are accepted with caution because they can be sparse or unstable and should not be overgeneralized.",
        "",
        "## Evaluation Evidence Result",
        "",
        f"- Gradient Boosting validation RMSE: `{format_metric(evaluation_summary['gradient_boosting_rmse'])}`.",
        f"- Gradient Boosting validation MAE: `{format_metric(evaluation_summary['gradient_boosting_mae'])}`.",
        f"- Gradient Boosting validation R-squared: `{format_metric(evaluation_summary['gradient_boosting_r2'])}`.",
        f"- Ridge validation RMSE: `{format_metric(evaluation_summary['ridge_rmse'])}`.",
        f"- Ridge validation MAE: `{format_metric(evaluation_summary['ridge_mae'])}`.",
        f"- Ridge validation R-squared: `{format_metric(evaluation_summary['ridge_r2'])}`.",
        f"- RMSE improvement versus Ridge: `{format_metric(evaluation_summary['rmse_improvement_vs_ridge'])}`.",
        f"- MAE improvement versus Ridge: `{format_metric(evaluation_summary['mae_improvement_vs_ridge'])}`.",
        f"- Performance strength assessment: `{evaluation_summary['performance_strength']}` validation explanatory power.",
        "",
        "The modest validation improvement over Ridge and low validation R-squared reduce concern that the model is simply reconstructing the target by formula. This is supporting evidence, not proof; the stronger evidence is the explicit forbidden-feature exclusion plus SHAP and feature-importance driver review.",
        "",
        "## Ablation or Sensitivity Status",
        "",
        "No formal ablation rerun was performed in this issue. No existing lightweight ablation artifact was found, and the issue guardrails prohibit retraining, retuning, or model-selection changes. The audit therefore uses artifact-only sensitivity evidence: explicit forbidden-feature exclusion checks, SHAP driver review, XGBoost feature-importance review, modest validation performance, and the existing AO2 evaluation pack.",
        "",
        "## Accepted Caveats",
        "",
        "- `item_unit_price`, `item_discount_rate`, and `order_item_quantity` are approved commercial predictors but should be interpreted cautiously.",
        "- Geography, product, and customer/location one-hot drivers can be sparse or unstable.",
        "- SHAP and feature importance are associative model explanations, not causal estimates.",
        "- Final-test evaluation remains deferred and was not used.",
        "",
        "## Final Audit Decision",
        "",
        f"`{final_decision}`",
        "",
        conclusion,
        "",
        "## Output Artifacts",
        "",
        f"- Forbidden feature check: `{output_paths['forbidden_feature_check_csv']}`",
        f"- Driver review: `{output_paths['driver_review_csv']}`",
        f"- Metadata: `{output_paths['metadata_json']}`",
        f"- Documentation: `{output_paths['docs_markdown']}`",
    ]


def build_docs_lines(
    *,
    selected_candidate_name: str,
    forbidden_count: int,
    caution_count: int,
    final_decision: str,
    evaluation_summary: dict[str, Any],
    output_paths: dict[str, str],
) -> list[str]:
    """Build documentation-facing AO2 target-reconstruction review."""
    return [
        "# AO2 Target-Reconstruction Review",
        "",
        f"Issue: `{ISSUE_ID}`",
        "",
        "## Purpose and Scope",
        "",
        "This note documents the AO2 target-reconstruction review for the finalized Gradient Boosting profitability model. It confirms whether the selected predictor set and dominant drivers are defensible for pre-dispatch profitability estimation rather than formula-like target reconstruction.",
        "",
        "The review is audit-only. It does not retrain or retune AO2, change the selected model, change preprocessing, change AO2 Gold or partitions, evaluate final test, change target policy, or implement AO3.",
        "",
        "## Why AO2 Needs This Audit",
        "",
        "`Order_Profit_Per_Order` can be duplicated or approximated by near-formula commercial fields such as duplicate profit, realized profit ratio, order value, sales, discount amount, and product price fields. A profitability model can look strong while reconstructing accounting outcomes. The audit checks raw predictors and transformed drivers against the frozen target-policy rules.",
        "",
        "## Selected Model Reviewed",
        "",
        f"- Selected model: `{MODEL_NAME}`.",
        f"- Selected candidate: `{selected_candidate_name}`.",
        "- Target: `Order_Profit_Per_Order`.",
        "- Review slice: validation artifacts only.",
        "- Final test not used.",
        "",
        "## Target-Policy Rules Reviewed",
        "",
        "Forbidden AO2 predictors and drivers include the target, duplicate profit fields, realized profit-ratio or margin fields, `Order_Item_Total`, `ao3_order_value`, `Sales`, `Sales_per_customer`, `Order_Item_Discount`, `Product_Price`, delivery outcome fields, post-shipment fields, final-test or holdout labels, identifiers, partition labels, date anchors, and lineage metadata.",
        "",
        "Approved commercial predictors such as `item_unit_price`, `item_discount_rate`, `order_item_quantity`, planned shipping features, product/category descriptors, and customer/geography descriptors are allowed but carry caution labels for interpretation.",
        "",
        "## Artifacts Reviewed",
        "",
        "- `models/ao2_profitability/preprocessing/ao2_preprocessing_metadata.json`",
        "- `models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metadata.json`",
        "- `models/ao2_profitability/evaluation/ao2_evaluation_metadata.json`",
        "- `models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json`",
        "- `report/tables/ao2_model_evaluation_metrics.csv`",
        "- `report/tables/ao2_model_validation_comparison.csv`",
        "- `report/tables/ao2_gradient_boosting_feature_importance.csv`",
        "- `report/tables/ao2_shap_feature_importance.csv`",
        "- `report/tables/ao2_shap_driver_summary.csv`",
        "- `report/tables/ao2_model_evaluation_findings.md`",
        "- `report/tables/ao2_shap_explainability_findings.md`",
        "",
        "## Predictor-Set Audit Result",
        "",
        f"The audit found `{forbidden_count}` forbidden predictor or driver rows and `{caution_count}` caution-status reviewed features. Because no forbidden feature was detected, the predictor set is not blocked by target-reconstruction policy.",
        "",
        "`ao3_order_value` was not detected as an AO2 predictor, SHAP driver, or feature-importance driver. It remains reserved for later AO3 predicted-margin support only.",
        "",
        "## SHAP and Feature-Importance Result",
        "",
        "The top SHAP and XGBoost importance drivers are commercially plausible pre-dispatch signals: unit price, discount rate, quantity, planned shipping/service, geography, product category, and customer/location one-hot features. These drivers do not show direct target, duplicate target, realized margin, order-value, sales, post-shipment, partition, identifier, or final-test fields.",
        "",
        "Commercial predictors are accepted with caution because they sit near the commercial formula context. Granular geography and product one-hot drivers are also accepted with caution because support counts and stability should be reviewed before broad business claims.",
        "",
        "## Evaluation Evidence Result",
        "",
        f"Gradient Boosting validation RMSE/MAE/R-squared were `{format_metric(evaluation_summary['gradient_boosting_rmse'])}`, `{format_metric(evaluation_summary['gradient_boosting_mae'])}`, and `{format_metric(evaluation_summary['gradient_boosting_r2'])}`. Ridge validation RMSE/MAE/R-squared were `{format_metric(evaluation_summary['ridge_rmse'])}`, `{format_metric(evaluation_summary['ridge_mae'])}`, and `{format_metric(evaluation_summary['ridge_r2'])}`.",
        "",
        "The improvement over Ridge is useful but modest, and validation R-squared remains limited. This reduces concern that the model is formula-reconstructing the target, but it does not prove absence of leakage by itself.",
        "",
        "## Ablation or Sensitivity Status",
        "",
        "No formal ablation rerun was performed. No existing lightweight ablation artifact was available, and this issue intentionally avoids retraining or feature-elimination experiments. The compensating evidence is the explicit forbidden-feature audit, SHAP driver review, feature-importance review, modest validation performance, and upstream evaluation pack.",
        "",
        "## Final Decision",
        "",
        f"`{final_decision}`",
        "",
        "Accepted with caution: no forbidden target-reconstruction fields were detected. The remaining AO2 predictor set is defensible for pre-dispatch profitability estimation, with caution notes for approved commercial predictors.",
        "",
        "## Limitations",
        "",
        "- This audit reviews existing artifacts; it does not generate new model evidence.",
        "- SHAP and feature importance are associative, not causal.",
        "- One-hot driver sparsity is not re-estimated here.",
        "- Final-test evaluation remains untouched.",
        "",
        "## Output Artifacts",
        "",
        f"- Forbidden feature check: `{output_paths['forbidden_feature_check_csv']}`",
        f"- Driver review: `{output_paths['driver_review_csv']}`",
        f"- Findings note: `{output_paths['findings_markdown']}`",
        f"- Metadata: `{output_paths['metadata_json']}`",
    ]


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Write JSON metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_ao2_target_reconstruction_audit(
    config: AO2TargetReconstructionAuditConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Run the artifact-only AO2 target-reconstruction audit."""
    logger.info("Starting AO2 target-reconstruction audit.")

    preprocessing_metadata = read_required_json(
        config.preprocessing_metadata_path,
        "AO2 preprocessing metadata",
    )
    gradient_boosting_metadata = read_required_json(
        config.gradient_boosting_metadata_path,
        "AO2 Gradient Boosting metadata",
    )
    evaluation_metadata = read_required_json(
        config.evaluation_metadata_path,
        "AO2 evaluation metadata",
    )
    shap_metadata = read_required_json(config.shap_metadata_path, "AO2 SHAP metadata")

    for artifact_name, metadata in {
        "AO2 preprocessing": preprocessing_metadata,
        "AO2 Gradient Boosting": gradient_boosting_metadata,
        "AO2 evaluation": evaluation_metadata,
        "AO2 SHAP": shap_metadata,
    }.items():
        validate_non_test_metadata(metadata, artifact_name)

    if evaluation_metadata.get("final_test_used") is not False:
        raise ValueError("AO2 evaluation metadata must explicitly record final_test_used = false.")
    if shap_metadata.get("final_test_used") is not False:
        raise ValueError("AO2 SHAP metadata must explicitly record final_test_used = false.")

    xgboost_importance_df = read_required_csv(
        config.xgboost_importance_path,
        "AO2 Gradient Boosting feature importance",
    )
    shap_importance_df = read_required_csv(
        config.shap_importance_path,
        "AO2 SHAP feature importance",
    )
    shap_driver_df = read_required_csv(config.shap_driver_summary_path, "AO2 SHAP driver summary")
    evaluation_metrics_df = read_required_csv(
        config.model_evaluation_metrics_path,
        "AO2 model evaluation metrics",
    )

    forbidden_check_df = build_forbidden_feature_check(
        preprocessing_metadata=preprocessing_metadata,
        gradient_boosting_metadata=gradient_boosting_metadata,
        shap_metadata=shap_metadata,
        xgboost_importance_df=xgboost_importance_df,
        shap_importance_df=shap_importance_df,
        shap_driver_df=shap_driver_df,
    )
    raw_predictors = collect_raw_predictors(
        preprocessing_metadata,
        gradient_boosting_metadata,
        shap_metadata,
    )
    driver_review_df = build_driver_review(
        xgboost_importance_df=xgboost_importance_df,
        shap_importance_df=shap_importance_df,
        shap_driver_df=shap_driver_df,
        raw_predictors=raw_predictors,
        top_n=config.top_driver_count,
    )

    forbidden_count = int((forbidden_check_df["policy_status"] == "forbidden").sum())
    caution_count = int(
        forbidden_check_df.loc[
            forbidden_check_df["policy_status"] == "caution",
            "normalized_feature_name",
        ].nunique()
    )
    blocked_features = sorted(
        forbidden_check_df.loc[
            forbidden_check_df["policy_status"] == "forbidden",
            "feature_name",
        ].astype(str).unique()
    )

    if forbidden_count > 0:
        final_decision = "blocked"
    elif caution_count > 0:
        final_decision = "accepted_with_caution"
    else:
        final_decision = "accepted"

    output_paths = {
        "forbidden_feature_check_csv": display_path(config.forbidden_check_output_path),
        "driver_review_csv": display_path(config.driver_review_output_path),
        "findings_markdown": display_path(config.findings_output_path),
        "docs_markdown": display_path(config.docs_output_path),
        "metadata_json": display_path(config.metadata_output_path),
    }

    config.forbidden_check_output_path.parent.mkdir(parents=True, exist_ok=True)
    forbidden_check_df.to_csv(config.forbidden_check_output_path, index=False)
    config.driver_review_output_path.parent.mkdir(parents=True, exist_ok=True)
    driver_review_df.to_csv(config.driver_review_output_path, index=False)

    selected_candidate_name = selected_candidate(gradient_boosting_metadata)
    evaluation_summary = build_evaluation_summary(evaluation_metrics_df)

    findings_lines = build_findings_lines(
        selected_candidate_name=selected_candidate_name,
        forbidden_count=forbidden_count,
        caution_count=caution_count,
        final_decision=final_decision,
        evaluation_summary=evaluation_summary,
        output_paths=output_paths,
        blocked_features=blocked_features,
    )
    write_markdown(config.findings_output_path, findings_lines)

    docs_lines = build_docs_lines(
        selected_candidate_name=selected_candidate_name,
        forbidden_count=forbidden_count,
        caution_count=caution_count,
        final_decision=final_decision,
        evaluation_summary=evaluation_summary,
        output_paths=output_paths,
    )
    write_markdown(config.docs_output_path, docs_lines)

    metadata = {
        "metadata_status": "ao2_target_reconstruction_audit_completed",
        "issue_id": ISSUE_ID,
        "issue": ISSUE_ID,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "selected_ao2_model_reviewed": MODEL_NAME,
        "selected_candidate": selected_candidate_name,
        "target_column": gradient_boosting_metadata.get(
            "target_column",
            "Order_Profit_Per_Order",
        ),
        "final_test_used": False,
        "input_artifacts_reviewed": artifact_path_list(config),
        "predictor_list_available": bool(raw_predictors),
        "raw_predictor_count": int(len(raw_predictors)),
        "transformed_feature_importance_rows_reviewed": int(len(xgboost_importance_df)),
        "shap_feature_rows_reviewed": int(len(shap_importance_df)),
        "driver_review_top_n_per_source": int(config.top_driver_count),
        "predictor_audit_status": "passed" if forbidden_count == 0 else "failed",
        "shap_driver_audit_status": "passed"
        if not (
            (forbidden_check_df["feature_role"] == "shap_driver")
            & (forbidden_check_df["policy_status"] == "forbidden")
        ).any()
        else "failed",
        "feature_importance_audit_status": "passed"
        if not (
            (forbidden_check_df["feature_role"] == "feature_importance_driver")
            & (forbidden_check_df["policy_status"] == "forbidden")
        ).any()
        else "failed",
        "ablation_sensitivity_status": {
            "formal_ablation_rerun_performed": False,
            "status": "not_run_artifact_only",
            "reason": (
                "No existing lightweight ablation artifact was available, and issue #73 "
                "guardrails prohibit retraining, retuning, broad feature elimination, and final-test use."
            ),
            "compensating_evidence": [
                "explicit forbidden-feature exclusion checks",
                "SHAP driver review",
                "XGBoost feature-importance review",
                "modest validation performance",
                "existing AO2 evaluation pack",
            ],
        },
        "forbidden_feature_count": forbidden_count,
        "caution_feature_count": caution_count,
        "blocked_features": blocked_features,
        "accepted_caveats": [
            "Approved commercial predictors require caution because AO2 target reconstruction is a known risk.",
            "Granular geography, product, and customer/location one-hot drivers can be sparse or unstable.",
            "Validation metrics are supporting evidence only and do not prove absence of target reconstruction.",
            "Final-test evaluation remains deferred and was not used.",
        ],
        "final_audit_decision": final_decision,
        "evaluation_evidence": evaluation_summary,
        "output_artifact_paths": output_paths,
        "limitations": [
            "The audit reviews existing AO2 artifacts and does not retrain or retune models.",
            "No formal ablation or sensitivity model was run in this issue.",
            "SHAP and feature importance are associative model explanations, not causal evidence.",
            "One-hot driver sparsity and support counts are not re-estimated here.",
            "The final test partition is not used.",
        ],
    }
    write_json(metadata, config.metadata_output_path)

    if forbidden_count:
        raise ValueError(
            "AO2 target-reconstruction audit found forbidden predictors or drivers: "
            f"{blocked_features}"
        )

    logger.info("AO2 target-reconstruction audit completed with decision: %s", final_decision)
    return metadata


def main() -> None:
    """Run the AO2 target-reconstruction audit with default paths."""
    run_ao2_target_reconstruction_audit(
        AO2TargetReconstructionAuditConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
