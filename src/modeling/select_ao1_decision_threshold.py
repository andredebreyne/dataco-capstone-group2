"""Select the AO1 operating threshold from validation trade-offs.

This script consumes the AO1 validation evaluation pack from issue #29 and
creates a reusable threshold policy for AO3 and dashboard logic. It never reads
or evaluates the final test partition.
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


TARGET_COLUMN = "Late_delivery_risk"
DEFAULT_MINIMUM_RECALL = 0.70
DEFAULT_MAXIMUM_ALERT_RATE = 0.65
DEFAULT_PRIMARY_MODEL_NAME = "ao1_xgboost_classifier"
PROVISIONAL_STATUS = "provisional_pending_primary_model"
READY_FOR_REVIEW_STATUS = "ready_for_team_review"

REQUIRED_THRESHOLD_COLUMNS = {
    "model_name",
    "threshold",
    "row_count",
    "positive_class_rate",
    "predicted_positive_rate",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "true_negative",
    "false_positive",
    "false_negative",
    "true_positive",
}

REQUIRED_METRIC_COLUMNS = {
    "model_name",
    "roc_auc",
    "pr_auc",
    "log_loss",
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
        if (candidate / "src").exists() and (candidate / "data").exists():
            return candidate

    return current_path


REPO_ROOT = resolve_repo_root()


@dataclass(frozen=True)
class AO1DecisionThresholdConfig:
    """Configuration for AO1 threshold policy selection."""

    threshold_grid_path: Path = Path(
        os.getenv(
            "DATACO_AO1_THRESHOLD_TRADEOFF_PATH",
            str(REPO_ROOT / "report/tables/ao1_threshold_tradeoff_grid.csv"),
        )
    )
    metrics_path: Path = Path(
        os.getenv(
            "DATACO_AO1_EVALUATION_METRICS_PATH",
            str(REPO_ROOT / "report/tables/ao1_model_validation_comparison.csv"),
        )
    )
    evaluation_metadata_path: Path = Path(
        os.getenv(
            "DATACO_AO1_EVALUATION_METADATA_PATH",
            str(REPO_ROOT / "models/ao1_late_delivery/evaluation/ao1_evaluation_metadata.json"),
        )
    )
    policy_csv_path: Path = Path(
        os.getenv(
            "DATACO_AO1_DECISION_THRESHOLD_POLICY_PATH",
            str(REPO_ROOT / "data/references/ao1_decision_threshold_policy.csv"),
        )
    )
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_DECISION_THRESHOLD_METADATA_PATH",
            str(REPO_ROOT / "models/ao1_late_delivery/threshold/ao1_decision_threshold_metadata.json"),
        )
    )
    findings_output_path: Path = Path(
        os.getenv(
            "DATACO_AO1_DECISION_THRESHOLD_FINDINGS_PATH",
            str(REPO_ROOT / "report/tables/ao1_decision_threshold_recommendation.md"),
        )
    )
    preferred_model_name: str = os.getenv(
        "DATACO_AO1_THRESHOLD_MODEL_NAME",
        DEFAULT_PRIMARY_MODEL_NAME,
    )
    minimum_recall: float = float(
        os.getenv("DATACO_AO1_THRESHOLD_MIN_RECALL", str(DEFAULT_MINIMUM_RECALL))
    )
    maximum_alert_rate: float = float(
        os.getenv("DATACO_AO1_THRESHOLD_MAX_ALERT_RATE", str(DEFAULT_MAXIMUM_ALERT_RATE))
    )


def configure_logging() -> logging.Logger:
    """Configure console logging for local or Databricks execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao1_decision_threshold")


def read_required_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    """Read a required non-empty CSV and validate required columns."""
    if not path.exists():
        raise FileNotFoundError(f"Required AO1 threshold input not found: {path}")

    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Required AO1 threshold input is empty: {path}")

    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"{path} is missing required columns: {missing_columns}")

    return frame


def read_evaluation_metadata(path: Path) -> dict[str, Any]:
    """Read optional AO1 evaluation metadata."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def choose_model_name(
    metrics_df: pd.DataFrame,
    preferred_model_name: str,
) -> tuple[str, bool]:
    """Choose the model to threshold, preferring the primary model when available."""
    available_models = set(metrics_df["model_name"].astype(str))
    if preferred_model_name in available_models:
        return preferred_model_name, True

    ranked = metrics_df.sort_values(
        ["roc_auc", "pr_auc"],
        ascending=False,
    )
    return str(ranked.iloc[0]["model_name"]), False


def select_threshold_row(
    threshold_df: pd.DataFrame,
    model_name: str,
    minimum_recall: float,
    maximum_alert_rate: float,
) -> tuple[pd.Series, str]:
    """Select a threshold row using recall-first operational constraints."""
    model_rows = threshold_df[threshold_df["model_name"].astype(str) == model_name].copy()
    if model_rows.empty:
        raise ValueError(f"No threshold rows found for model: {model_name}")

    constrained = model_rows[
        (model_rows["recall"] >= minimum_recall)
        & (model_rows["predicted_positive_rate"] <= maximum_alert_rate)
    ].copy()

    if not constrained.empty:
        selected = constrained.sort_values(
            ["recall", "precision", "f1", "threshold"],
            ascending=[False, False, False, False],
        ).iloc[0]
        return selected, "meets_recall_and_alert_rate_constraints"

    alert_constrained = model_rows[
        model_rows["predicted_positive_rate"] <= maximum_alert_rate
    ].copy()
    if not alert_constrained.empty:
        selected = alert_constrained.sort_values(
            ["recall", "precision", "f1", "threshold"],
            ascending=[False, False, False, False],
        ).iloc[0]
        return selected, "fallback_max_recall_under_alert_rate_cap"

    selected = model_rows.sort_values(
        ["f1", "recall", "precision", "threshold"],
        ascending=[False, False, False, False],
    ).iloc[0]
    return selected, "fallback_best_f1_no_alert_rate_constraint_met"


def build_policy_row(
    selected_row: pd.Series,
    selection_reason: str,
    primary_model_available: bool,
    config: AO1DecisionThresholdConfig,
) -> dict[str, Any]:
    """Build the reusable AO1 decision-threshold policy row."""
    decision_status = READY_FOR_REVIEW_STATUS if primary_model_available else PROVISIONAL_STATUS
    return {
        "policy_name": "ao1_late_delivery_operating_threshold",
        "issue": "#67",
        "decision_status": decision_status,
        "model_name": selected_row["model_name"],
        "selected_threshold": float(selected_row["threshold"]),
        "selection_reason": selection_reason,
        "minimum_recall_target": config.minimum_recall,
        "maximum_alert_rate_target": config.maximum_alert_rate,
        "validation_row_count": int(selected_row["row_count"]),
        "validation_positive_class_rate": float(selected_row["positive_class_rate"]),
        "validation_predicted_positive_rate": float(selected_row["predicted_positive_rate"]),
        "validation_precision": float(selected_row["precision"]),
        "validation_recall": float(selected_row["recall"]),
        "validation_f1": float(selected_row["f1"]),
        "validation_true_negative": int(selected_row["true_negative"]),
        "validation_false_positive": int(selected_row["false_positive"]),
        "validation_false_negative": int(selected_row["false_negative"]),
        "validation_true_positive": int(selected_row["true_positive"]),
        "final_test_used": False,
        "ao3_dashboard_reuse_rule": (
            "Classify AO1 high-risk orders when predicted_probability is greater than "
            "or equal to selected_threshold."
        ),
    }


def write_policy(policy_row: dict[str, Any], config: AO1DecisionThresholdConfig) -> None:
    """Write CSV, JSON metadata, and report-facing recommendation artifacts."""
    config.policy_csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([policy_row]).to_csv(config.policy_csv_path, index=False)

    metadata = {
        "metadata_status": policy_row["decision_status"],
        "issue": "#67",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_column": TARGET_COLUMN,
        "threshold_grid_path": str(config.threshold_grid_path),
        "metrics_path": str(config.metrics_path),
        "evaluation_metadata_path": str(config.evaluation_metadata_path),
        "policy_csv_path": str(config.policy_csv_path),
        "findings_output_path": str(config.findings_output_path),
        "minimum_recall_target": config.minimum_recall,
        "maximum_alert_rate_target": config.maximum_alert_rate,
        "preferred_model_name": config.preferred_model_name,
        "selected_policy": policy_row,
    }
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.metadata_output_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    write_findings(policy_row, config)


def write_findings(policy_row: dict[str, Any], config: AO1DecisionThresholdConfig) -> None:
    """Write a managerial threshold recommendation note."""
    status_note = (
        "The primary AO1 model is available and the recommendation is ready for team review."
        if policy_row["decision_status"] == READY_FOR_REVIEW_STATUS
        else (
            "This recommendation is provisional because the primary AO1 XGBoost prediction "
            "artifact is not yet available. Re-run this script after issue #28 publishes "
            "the required validation predictions."
        )
    )

    lines = [
        "# AO1 Decision Threshold Recommendation",
        "",
        "Issue: `#67`",
        "",
        "## Decision Status",
        "",
        f"`{policy_row['decision_status']}`",
        "",
        status_note,
        "",
        "## Recommended Operating Rule",
        "",
        (
            f"Use threshold `{policy_row['selected_threshold']:.2f}` for "
            f"`{policy_row['model_name']}`."
        ),
        "",
        "An order should be classified as AO1 high-risk when:",
        "",
        "```text",
        "predicted_probability >= selected_threshold",
        "```",
        "",
        "## Validation Trade-Off",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Precision | {policy_row['validation_precision']:.4f} |",
        f"| Recall | {policy_row['validation_recall']:.4f} |",
        f"| F1 | {policy_row['validation_f1']:.4f} |",
        f"| Predicted positive rate | {policy_row['validation_predicted_positive_rate']:.4f} |",
        f"| False negatives | {policy_row['validation_false_negative']} |",
        f"| False positives | {policy_row['validation_false_positive']} |",
        "",
        "## Rationale",
        "",
        "AO1 supports pre-dispatch prioritization. The selected rule prioritizes recall "
        "because missed high-risk orders reduce operational value, while also applying "
        "an alert-rate cap so the resulting queue remains actionable.",
        "",
        "## Reusable Policy Artifact",
        "",
        f"The reusable policy is stored at `{config.policy_csv_path}`.",
    ]

    config.findings_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.findings_output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ao1_decision_threshold_selection(
    config: AO1DecisionThresholdConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Select and persist the AO1 operating threshold policy."""
    logger.info("Starting AO1 decision threshold selection.")
    threshold_df = read_required_csv(config.threshold_grid_path, REQUIRED_THRESHOLD_COLUMNS)
    metrics_df = read_required_csv(config.metrics_path, REQUIRED_METRIC_COLUMNS)
    evaluation_metadata = read_evaluation_metadata(config.evaluation_metadata_path)

    model_name, primary_model_available = choose_model_name(
        metrics_df,
        config.preferred_model_name,
    )
    selected_row, selection_reason = select_threshold_row(
        threshold_df,
        model_name,
        config.minimum_recall,
        config.maximum_alert_rate,
    )
    policy_row = build_policy_row(
        selected_row,
        selection_reason,
        primary_model_available,
        config,
    )

    if evaluation_metadata.get("final_test_used") is not False:
        logger.warning(
            "AO1 evaluation metadata is missing or does not explicitly mark final_test_used=False."
        )

    write_policy(policy_row, config)
    logger.info("AO1 decision threshold policy written: %s", config.policy_csv_path)
    logger.info("AO1 decision threshold selection completed successfully.")
    return policy_row


def main() -> None:
    """Run AO1 threshold selection with default artifact paths."""
    run_ao1_decision_threshold_selection(
        AO1DecisionThresholdConfig(),
        configure_logging(),
    )


if __name__ == "__main__":
    main()
