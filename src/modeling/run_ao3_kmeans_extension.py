"""Run the optional AO3 K-means clustering extension for Issue #44.

This extension consumes the completed AO3 risk-margin segment table and asks
whether a small unsupervised K-means view adds interpretable context beyond the
approved AO3 2x2 risk-margin matrix. It does not retrain AO1 or AO2, change AO3
segment logic, use target outcomes, or make clustering part of the core AO3
workflow.
"""

from __future__ import annotations

import csv
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


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")
SEGMENT_INPUT_PATH = os.getenv(
    "DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH",
    f"{VOLUME_ROOT}/gold/ao3_risk_margin_segments",
)

ISSUE_ID = "#44"
RANDOM_SEED = 42
K_CANDIDATES = (3, 4, 5)
MIN_CLUSTER_SHARE_FOR_ADOPTION = 0.01
DUPLICATION_DOMINANCE_THRESHOLD = 0.90
LOW_INTERPRETABILITY_DOMINANCE_THRESHOLD = 0.60
MIN_SILHOUETTE_FOR_OPTIONAL_ADOPTION = 0.25

CLUSTERING_FEATURES = (
    "ao1_predicted_late_delivery_probability",
    "ao3_predicted_margin",
)

PROFILE_COLUMNS = (
    "cluster_id",
    "row_count",
    "row_share",
    "mean_predicted_late_delivery_risk",
    "median_predicted_late_delivery_risk",
    "mean_expected_profit",
    "median_expected_profit",
    "mean_predicted_margin",
    "median_predicted_margin",
    "dominant_ao3_priority_segment",
    "dominant_ao3_segment_share",
    "ao3_quadrant_distribution",
    "suggested_interpretation_label",
)

QUALITY_COLUMNS = (
    "k",
    "inertia",
    "silhouette_score",
    "min_cluster_size",
    "min_cluster_share",
    "max_cluster_share",
    "cluster_size_summary",
    "meets_min_share_rule",
    "selected",
)

ASSIGNMENT_SAMPLE_COLUMNS = (
    "Order_Id",
    "Order_Item_Id",
    "split_partition",
    "ao2_split_partition",
    "ao1_predicted_late_delivery_probability",
    "ao2_predicted_order_profit",
    "ao3_predicted_margin",
    "ao3_priority_segment",
    "ao3_kmeans_cluster",
)

REQUIRED_COLUMNS = {
    "Order_Id",
    "Order_Item_Id",
    "split_partition",
    "ao2_split_partition",
    "ao1_predicted_late_delivery_probability",
    "ao2_predicted_order_profit",
    "ao3_predicted_margin",
    "ao3_priority_segment",
}

FORBIDDEN_TARGET_COLUMNS = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
}

VALID_RECOMMENDATIONS = {
    "adopt_as_optional_context",
    "document_but_do_not_use",
    "do_not_adopt",
}

OPERATIONAL_SEGMENTS = {
    "protect_high_value_at_risk",
    "expedite_selectively",
    "preserve_service",
    "standard_process",
}


@dataclass(frozen=True)
class AO3KMeansExtensionConfig:
    """Configuration for the optional AO3 K-means extension."""

    segment_input_path: str = SEGMENT_INPUT_PATH
    read_format: str = os.getenv("DATACO_AO3_KMEANS_INPUT_FORMAT", "delta")
    metadata_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_KMEANS_METADATA_PATH",
            str(
                Path.cwd()
                / "models/ao3_integration/kmeans_extension/ao3_kmeans_extension_metadata.json"
            ),
        )
    )
    quality_metrics_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_KMEANS_QUALITY_METRICS_PATH",
            str(Path.cwd() / "report/tables/ao3_kmeans_quality_metrics.csv"),
        )
    )
    cluster_profiles_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_KMEANS_CLUSTER_PROFILES_PATH",
            str(Path.cwd() / "report/tables/ao3_kmeans_cluster_profiles.csv"),
        )
    )
    assignments_sample_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_KMEANS_ASSIGNMENTS_SAMPLE_PATH",
            str(Path.cwd() / "report/tables/ao3_kmeans_cluster_assignments_sample.csv"),
        )
    )
    findings_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_KMEANS_FINDINGS_PATH",
            str(Path.cwd() / "report/tables/ao3_kmeans_extension_findings.md"),
        )
    )
    docs_output_path: Path = Path(
        os.getenv(
            "DATACO_AO3_KMEANS_DOCS_PATH",
            str(Path.cwd() / "docs/ao3_kmeans_extension.md"),
        )
    )
    random_seed: int = RANDOM_SEED
    sample_size: int = int(os.getenv("DATACO_AO3_KMEANS_ASSIGNMENT_SAMPLE_SIZE", "2000"))


def configure_logging() -> logging.Logger:
    """Configure console logging for the extension."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.ao3_kmeans_extension")


def resolve_repo_root() -> Path:
    """Resolve repository root for local artifact outputs."""
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


def with_repo_defaults(config: AO3KMeansExtensionConfig) -> AO3KMeansExtensionConfig:
    """Replace cwd-based output defaults with repository-root paths."""
    repo_root = resolve_repo_root()
    return AO3KMeansExtensionConfig(
        segment_input_path=config.segment_input_path,
        read_format=config.read_format,
        metadata_output_path=Path(
            os.getenv(
                "DATACO_AO3_KMEANS_METADATA_PATH",
                str(
                    repo_root
                    / "models/ao3_integration/kmeans_extension/ao3_kmeans_extension_metadata.json"
                ),
            )
        ),
        quality_metrics_output_path=Path(
            os.getenv(
                "DATACO_AO3_KMEANS_QUALITY_METRICS_PATH",
                str(repo_root / "report/tables/ao3_kmeans_quality_metrics.csv"),
            )
        ),
        cluster_profiles_output_path=Path(
            os.getenv(
                "DATACO_AO3_KMEANS_CLUSTER_PROFILES_PATH",
                str(repo_root / "report/tables/ao3_kmeans_cluster_profiles.csv"),
            )
        ),
        assignments_sample_output_path=Path(
            os.getenv(
                "DATACO_AO3_KMEANS_ASSIGNMENTS_SAMPLE_PATH",
                str(repo_root / "report/tables/ao3_kmeans_cluster_assignments_sample.csv"),
            )
        ),
        findings_output_path=Path(
            os.getenv(
                "DATACO_AO3_KMEANS_FINDINGS_PATH",
                str(repo_root / "report/tables/ao3_kmeans_extension_findings.md"),
            )
        ),
        docs_output_path=Path(
            os.getenv(
                "DATACO_AO3_KMEANS_DOCS_PATH",
                str(repo_root / "docs/ao3_kmeans_extension.md"),
            )
        ),
        random_seed=config.random_seed,
        sample_size=config.sample_size,
    )


def read_ao3_segment_input(config: AO3KMeansExtensionConfig) -> pd.DataFrame:
    """Read the AO3 segment artifact into pandas."""
    read_format = config.read_format.lower()
    if read_format == "csv":
        return pd.read_csv(config.segment_input_path)
    if read_format == "parquet":
        return pd.read_parquet(config.segment_input_path)
    if read_format != "delta":
        raise ValueError(f"Unsupported AO3 K-means input format: {config.read_format}")

    try:
        from pyspark.sql import SparkSession
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pyspark is required to read the default AO3 Delta segment table. "
            "Run this extension in Databricks or set DATACO_AO3_KMEANS_INPUT_FORMAT=csv "
            "with DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH pointing to a local extract."
        ) from exc

    spark = SparkSession.builder.getOrCreate()
    return spark.read.format("delta").load(config.segment_input_path).toPandas()


def normalized_column_name(column_name: str) -> str:
    """Normalize a column name for conservative leakage matching."""
    return column_name.lower().replace(" ", "_").replace("-", "_")


def json_default(value: Any) -> Any:
    """Convert numpy and pandas scalar values into JSON-safe Python scalars."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def validate_input_contract(df: pd.DataFrame) -> None:
    """Validate AO3 source columns and leakage exclusions before clustering."""
    if df.empty:
        raise ValueError("AO3 K-means input contains no rows.")

    missing_columns = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(f"AO3 K-means input missing columns: {missing_columns}")

    forbidden_columns = sorted(FORBIDDEN_TARGET_COLUMNS.intersection(df.columns))
    if forbidden_columns:
        raise ValueError(f"AO3 K-means input contains target/outcome columns: {forbidden_columns}")

    forbidden_normalized = {normalized_column_name(column) for column in FORBIDDEN_TARGET_COLUMNS}
    feature_leakage = sorted(
        feature
        for feature in CLUSTERING_FEATURES
        if normalized_column_name(feature) in forbidden_normalized
    )
    if feature_leakage:
        raise ValueError(f"Forbidden clustering features selected: {feature_leakage}")

    non_test_rows = df[
        (df["split_partition"].astype(str) != "test")
        | (df["ao2_split_partition"].astype(str) != "test")
    ]
    if not non_test_rows.empty:
        raise ValueError(f"AO3 K-means input contains non-test rows: {len(non_test_rows)}")

    if len(df) <= max(K_CANDIDATES):
        raise ValueError(
            f"AO3 K-means input needs more than {max(K_CANDIDATES)} rows; found {len(df)}."
        )

    for feature in CLUSTERING_FEATURES:
        non_null_count = int(pd.to_numeric(df[feature], errors="coerce").notna().sum())
        if non_null_count == 0:
            raise ValueError(f"Clustering feature has no numeric values: {feature}")


def build_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Impute and scale the small AO3 decision-signal feature matrix."""
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "scikit-learn is required for the AO3 K-means extension. Install "
            "requirements.txt in Databricks before enabling RUN_AO3_KMEANS_EXTENSION."
        ) from exc

    feature_df = df.loc[:, CLUSTERING_FEATURES].apply(pd.to_numeric, errors="coerce")
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    imputed = imputer.fit_transform(feature_df)
    return scaler.fit_transform(imputed)


def fit_kmeans_candidates(
    feature_matrix: np.ndarray,
    random_seed: int,
) -> tuple[pd.DataFrame, dict[int, np.ndarray]]:
    """Fit K-means candidates and return quality metrics plus assignments."""
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "scikit-learn is required for the AO3 K-means extension. Install "
            "requirements.txt in Databricks before enabling RUN_AO3_KMEANS_EXTENSION."
        ) from exc

    metric_rows: list[dict[str, Any]] = []
    labels_by_k: dict[int, np.ndarray] = {}
    total_rows = feature_matrix.shape[0]

    for candidate_k in K_CANDIDATES:
        model = KMeans(n_clusters=candidate_k, random_state=random_seed, n_init=10)
        labels = model.fit_predict(feature_matrix)
        labels_by_k[candidate_k] = labels

        counts = pd.Series(labels).value_counts().sort_index()
        min_cluster_size = int(counts.min())
        max_cluster_size = int(counts.max())
        min_cluster_share = min_cluster_size / total_rows
        max_cluster_share = max_cluster_size / total_rows

        metric_rows.append(
            {
                "k": candidate_k,
                "inertia": float(model.inertia_),
                "silhouette_score": float(silhouette_score(feature_matrix, labels)),
                "min_cluster_size": min_cluster_size,
                "min_cluster_share": min_cluster_share,
                "max_cluster_share": max_cluster_share,
                "cluster_size_summary": json.dumps(
                    {str(int(cluster)): int(count) for cluster, count in counts.items()},
                    sort_keys=True,
                ),
                "meets_min_share_rule": min_cluster_share >= MIN_CLUSTER_SHARE_FOR_ADOPTION,
                "selected": False,
            }
        )

    metrics_df = pd.DataFrame(metric_rows)
    selected_k = select_preferred_k(metrics_df)
    metrics_df.loc[metrics_df["k"] == selected_k, "selected"] = True
    return metrics_df, labels_by_k


def select_preferred_k(metrics_df: pd.DataFrame) -> int:
    """Select the preferred K using silhouette and minimum usable cluster size."""
    eligible = metrics_df[metrics_df["meets_min_share_rule"]].copy()
    if eligible.empty:
        eligible = metrics_df.copy()
    selected = eligible.sort_values(
        ["silhouette_score", "min_cluster_share"],
        ascending=[False, False],
    ).iloc[0]
    return int(selected["k"])


def get_cutoffs(df: pd.DataFrame) -> tuple[float, float]:
    """Read AO3 cutoffs from the source table when present."""
    risk_cutoff = 0.35
    margin_cutoff = 0.0
    if "ao3_risk_cutoff" in df.columns and df["ao3_risk_cutoff"].notna().any():
        risk_cutoff = float(pd.to_numeric(df["ao3_risk_cutoff"], errors="coerce").dropna().iloc[0])
    if "ao3_margin_cutoff" in df.columns and df["ao3_margin_cutoff"].notna().any():
        margin_cutoff = float(pd.to_numeric(df["ao3_margin_cutoff"], errors="coerce").dropna().iloc[0])
    return risk_cutoff, margin_cutoff


def interpretation_label(row: pd.Series, risk_cutoff: float, margin_cutoff: float) -> str:
    """Create a conservative cluster interpretation label from profile means."""
    if float(row["dominant_ao3_segment_share"]) < LOW_INTERPRETABILITY_DOMINANCE_THRESHOLD:
        return "mixed / unclear"

    risk_label = (
        "high risk"
        if float(row["mean_predicted_late_delivery_risk"]) >= risk_cutoff
        else "low risk"
    )
    margin_label = "high margin" if float(row["mean_predicted_margin"]) >= margin_cutoff else "low margin"
    return f"{risk_label} / {margin_label}"


def build_cluster_profiles(df: pd.DataFrame, selected_labels: np.ndarray) -> pd.DataFrame:
    """Build cluster profile rows for the selected K."""
    working_df = df.copy()
    working_df["ao3_kmeans_cluster"] = selected_labels
    total_rows = len(working_df)
    risk_cutoff, margin_cutoff = get_cutoffs(working_df)
    profile_rows: list[dict[str, Any]] = []

    for cluster_id, cluster_df in working_df.groupby("ao3_kmeans_cluster", sort=True):
        segment_counts = cluster_df["ao3_priority_segment"].astype(str).value_counts()
        dominant_segment = str(segment_counts.index[0])
        dominant_share = float(segment_counts.iloc[0] / len(cluster_df))
        distribution = {
            str(segment): round(float(count / len(cluster_df)), 6)
            for segment, count in segment_counts.items()
        }

        profile_rows.append(
            {
                "cluster_id": int(cluster_id),
                "row_count": int(len(cluster_df)),
                "row_share": float(len(cluster_df) / total_rows),
                "mean_predicted_late_delivery_risk": float(
                    pd.to_numeric(
                        cluster_df["ao1_predicted_late_delivery_probability"],
                        errors="coerce",
                    ).mean()
                ),
                "median_predicted_late_delivery_risk": float(
                    pd.to_numeric(
                        cluster_df["ao1_predicted_late_delivery_probability"],
                        errors="coerce",
                    ).median()
                ),
                "mean_expected_profit": float(
                    pd.to_numeric(cluster_df["ao2_predicted_order_profit"], errors="coerce").mean()
                ),
                "median_expected_profit": float(
                    pd.to_numeric(
                        cluster_df["ao2_predicted_order_profit"],
                        errors="coerce",
                    ).median()
                ),
                "mean_predicted_margin": float(
                    pd.to_numeric(cluster_df["ao3_predicted_margin"], errors="coerce").mean()
                ),
                "median_predicted_margin": float(
                    pd.to_numeric(cluster_df["ao3_predicted_margin"], errors="coerce").median()
                ),
                "dominant_ao3_priority_segment": dominant_segment,
                "dominant_ao3_segment_share": dominant_share,
                "ao3_quadrant_distribution": json.dumps(distribution, sort_keys=True),
                "suggested_interpretation_label": "",
            }
        )

    profiles_df = pd.DataFrame(profile_rows).sort_values("cluster_id")
    profiles_df["suggested_interpretation_label"] = profiles_df.apply(
        lambda row: interpretation_label(row, risk_cutoff, margin_cutoff),
        axis=1,
    )
    return profiles_df.loc[:, PROFILE_COLUMNS]


def build_comparison_summary(df: pd.DataFrame, selected_labels: np.ndarray) -> dict[str, Any]:
    """Compare selected clusters against AO3 2x2 risk-margin segments."""
    working_df = df.copy()
    working_df["ao3_kmeans_cluster"] = selected_labels
    total_rows = len(working_df)

    cluster_segment_counts = (
        working_df.groupby(["ao3_kmeans_cluster", "ao3_priority_segment"])
        .size()
        .rename("row_count")
        .reset_index()
    )
    dominant_counts = cluster_segment_counts.sort_values(
        ["ao3_kmeans_cluster", "row_count"],
        ascending=[True, False],
    ).drop_duplicates("ao3_kmeans_cluster")
    weighted_dominant_share = float(dominant_counts["row_count"].sum() / total_rows)

    segment_split_rows = []
    for segment, segment_df in working_df.groupby("ao3_priority_segment"):
        if str(segment) not in OPERATIONAL_SEGMENTS:
            continue
        segment_cluster_counts = segment_df["ao3_kmeans_cluster"].value_counts()
        meaningful_clusters = int(
            (segment_cluster_counts / len(segment_df) >= 0.10).sum()
        )
        if meaningful_clusters >= 2:
            segment_split_rows.append(
                {
                    "ao3_priority_segment": str(segment),
                    "segment_row_count": int(len(segment_df)),
                    "meaningful_cluster_count": meaningful_clusters,
                }
            )

    return {
        "weighted_dominant_ao3_segment_share": weighted_dominant_share,
        "segments_split_into_meaningful_clusters": segment_split_rows,
        "mostly_duplicates_ao3_2x2": weighted_dominant_share >= DUPLICATION_DOMINANCE_THRESHOLD,
        "hard_to_explain": weighted_dominant_share < LOW_INTERPRETABILITY_DOMINANCE_THRESHOLD,
        "crosswalk": cluster_segment_counts.to_dict(orient="records"),
    }


def decide_recommendation(
    metrics_df: pd.DataFrame,
    comparison: dict[str, Any],
) -> tuple[str, str, bool]:
    """Decide whether the clustering extension adds interpretive value."""
    selected_metric = metrics_df.loc[metrics_df["selected"]].iloc[0]
    selected_k = int(selected_metric["k"])
    silhouette = float(selected_metric["silhouette_score"])
    min_share = float(selected_metric["min_cluster_share"])

    if min_share < MIN_CLUSTER_SHARE_FOR_ADOPTION:
        return (
            "do_not_adopt",
            (
                f"K={selected_k} produces a smallest cluster share of {min_share:.4f}, "
                "below the usability threshold for an operational extension."
            ),
            False,
        )

    if comparison["mostly_duplicates_ao3_2x2"]:
        return (
            "do_not_adopt",
            (
                "Selected clusters mostly duplicate existing AO3 risk-margin matrix segments "
                f"(weighted dominant segment share {comparison['weighted_dominant_ao3_segment_share']:.3f})."
            ),
            False,
        )

    if comparison["hard_to_explain"]:
        return (
            "document_but_do_not_use",
            (
                "Selected clusters are too mixed against AO3 segments to explain cleanly "
                f"(weighted dominant segment share {comparison['weighted_dominant_ao3_segment_share']:.3f})."
            ),
            False,
        )

    if not comparison["segments_split_into_meaningful_clusters"]:
        return (
            "document_but_do_not_use",
            "No AO3 quadrant is split into multiple sizeable clusters with clear interpretive value.",
            False,
        )

    if silhouette < MIN_SILHOUETTE_FOR_OPTIONAL_ADOPTION:
        return (
            "document_but_do_not_use",
            f"K={selected_k} has a weak silhouette score ({silhouette:.3f}) for optional adoption.",
            False,
        )

    return (
        "adopt_as_optional_context",
        (
            "Selected clusters provide optional context by splitting at least one AO3 quadrant "
            "into sizeable, interpretable subgroups without replacing the 2x2 matrix."
        ),
        True,
    )


def write_csv_file(rows: list[dict[str, Any]], fieldnames: tuple[str, ...], output_path: Path) -> None:
    """Write rows to CSV with a stable schema."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_assignments_sample(
    df: pd.DataFrame,
    selected_labels: np.ndarray,
    output_path: Path,
    sample_size: int,
    random_seed: int,
) -> None:
    """Write a compact sample of cluster assignments for review."""
    working_df = df.copy()
    working_df["ao3_kmeans_cluster"] = selected_labels
    sample_rows = min(sample_size, len(working_df))
    sample_df = working_df.loc[:, ASSIGNMENT_SAMPLE_COLUMNS].sample(
        n=sample_rows,
        random_state=random_seed,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_df.to_csv(output_path, index=False)


def markdown_table_from_rows(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> str:
    """Create a small GitHub-flavored markdown table without extra dependencies."""
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def build_findings_markdown(
    *,
    config: AO3KMeansExtensionConfig,
    metrics_df: pd.DataFrame,
    profiles_df: pd.DataFrame,
    selected_k: int,
    recommendation: str,
    rationale: str,
    adds_value: bool,
    comparison: dict[str, Any],
    row_count: int,
) -> str:
    """Build the run-specific findings markdown."""
    metrics_rows = metrics_df.to_dict(orient="records")
    profile_rows = profiles_df.to_dict(orient="records")
    selected_metric = metrics_df.loc[metrics_df["selected"]].iloc[0].to_dict()
    split_segments = comparison["segments_split_into_meaningful_clusters"]
    split_summary = (
        ", ".join(
            f"{row['ao3_priority_segment']} ({row['meaningful_cluster_count']} clusters)"
            for row in split_segments
        )
        if split_segments
        else "No AO3 quadrant had multiple sizeable cluster subgroups."
    )

    return f"""# AO3 K-means Extension Findings

Issue: `{ISSUE_ID}`

## Input Used

- AO3 input artifact: `{config.segment_input_path}`
- Evidence slice: held-out AO3 scored segment table with `split_partition = test` and `ao2_split_partition = test`
- Row count: `{row_count}`
- Final test used: yes, for AO3 decision signals only, matching the existing AO3 segment artifact
- Final target/outcome fields used: no

## K-means Setup

- Clustering method: K-means with median imputation and standard scaling
- Random seed: `{config.random_seed}`
- Clustering features: `{', '.join(CLUSTERING_FEATURES)}`
- K candidates tested: `{', '.join(str(k) for k in K_CANDIDATES)}`
- Selected K for profiling: `{selected_k}`
- Selected K silhouette score: `{float(selected_metric['silhouette_score']):.4f}`

## Quality Metrics

{markdown_table_from_rows(metrics_rows, QUALITY_COLUMNS)}

## Cluster Profile Summary

{markdown_table_from_rows(profile_rows, PROFILE_COLUMNS)}

## Comparison Against AO3 2x2 Risk-Margin Matrix

- Weighted dominant AO3 segment share across clusters: `{comparison['weighted_dominant_ao3_segment_share']:.4f}`
- Mostly duplicates existing AO3 2x2 matrix: `{comparison['mostly_duplicates_ao3_2x2']}`
- Hard to explain against AO3 matrix: `{comparison['hard_to_explain']}`
- Meaningful AO3 quadrant splits: {split_summary}
- Do clusters add value beyond 2x2: `{adds_value}`

The AO3 2x2 risk-margin matrix remains the primary decision-support framework.
K-means is only considered as optional context if it clearly splits a major AO3
quadrant into interpretable subgroups without creating unstable or tiny groups.

## Recommendation

Recommendation: `{recommendation}`

Reason: {rationale}

## Limitations

- K-means is sensitive to scaling and assumes roughly spherical clusters.
- The extension uses only AO3 decision-time prediction signals, not realized outcomes.
- Cluster stability is not formally tested in this lightweight extension.
- Final-test target labels are not used, so this is not an outcome-performance evaluation.
- Clusters should not replace the governed AO3 risk-margin matrix or H3 benchmark.
"""


def build_docs_markdown(
    *,
    config: AO3KMeansExtensionConfig,
    recommendation: str,
    rationale: str,
    selected_k: int,
    row_count: int,
) -> str:
    """Build the documentation page updated by a completed run."""
    return f"""# AO3 K-means Extension

Issue: `{ISSUE_ID}`

## Purpose And Scope

This page documents the optional AO3 K-means clustering extension. The extension
asks whether unsupervised clusters add interpretive value beyond the approved AO3
2x2 risk-margin matrix. It is not part of the core AO3 decision framework and it
must not replace the H3 benchmark against risk-only and margin-only views.

## Optional Status

The primary AO3 tool remains the governed 2x2 risk-margin matrix:

- high risk / high margin
- high risk / low margin
- low risk / high margin
- low risk / low margin

K-means is retained only as optional context if the generated findings show a
clear interpretive benefit. The current generated recommendation is
`{recommendation}`.

## Input AO3 Artifact

- Input artifact: `{config.segment_input_path}`
- Evidence slice: held-out AO3 scored segment table
- Row count used by the latest run: `{row_count}`
- Final-test scope: AO3 decision signals only; target/outcome fields are not used

## Clustering Features

The extension clusters only on the small AO3 decision-signal feature set:

- `ao1_predicted_late_delivery_probability`
- `ao3_predicted_margin`

`ao2_predicted_order_profit` is used for cluster profiling only. Identifiers,
true late-delivery labels, realized profit fields, post-shipment fields, and
AO2 target-reconstruction risk fields are excluded from clustering.

## Method

- Algorithm: scikit-learn `KMeans`
- Preprocessing: median imputation and standard scaling
- Random seed: `{config.random_seed}`
- K candidates: `{', '.join(str(k) for k in K_CANDIDATES)}`
- Selected K for profiling: `{selected_k}`

## Outputs

- Quality metrics: `{config.quality_metrics_output_path}`
- Cluster profiles: `{config.cluster_profiles_output_path}`
- Assignment sample: `{config.assignments_sample_output_path}`
- Findings note: `{config.findings_output_path}`
- Metadata: `{config.metadata_output_path}`

## Business Interpretation

The extension compares each cluster against the existing AO3 risk-margin
segments. It checks whether clusters mostly duplicate the 2x2 matrix, split an
important quadrant into useful subgroups, or create mixed groups that would
confuse dashboard interpretation.

## Final Recommendation

Recommendation: `{recommendation}`

Reason: {rationale}

The AO3 2x2 risk-margin matrix remains the decision tool for the dashboard and
report unless a reviewed future issue explicitly adopts the clustering view.

## Limitations

- K-means can be sensitive to scaling and outliers.
- Cluster stability is not formally tested.
- The extension does not use realized late-delivery or profit outcomes.
- The extension does not estimate operational impact.
- The findings should be treated as optional interpretation, not policy.
"""


def write_metadata(
    *,
    config: AO3KMeansExtensionConfig,
    metrics_df: pd.DataFrame,
    profiles_df: pd.DataFrame,
    selected_k: int,
    recommendation: str,
    rationale: str,
    adds_value: bool,
    comparison: dict[str, Any],
    row_count: int,
) -> None:
    """Write metadata for the completed optional K-means extension."""
    output_paths = {
        "metadata": str(config.metadata_output_path),
        "quality_metrics": str(config.quality_metrics_output_path),
        "cluster_profiles": str(config.cluster_profiles_output_path),
        "assignments_sample": str(config.assignments_sample_output_path),
        "findings": str(config.findings_output_path),
        "documentation": str(config.docs_output_path),
    }
    selected_metric = metrics_df.loc[metrics_df["selected"]].iloc[0].to_dict()
    cluster_size_summary = {
        str(int(row["cluster_id"])): {
            "row_count": int(row["row_count"]),
            "row_share": float(row["row_share"]),
            "dominant_ao3_priority_segment": row["dominant_ao3_priority_segment"],
        }
        for row in profiles_df.to_dict(orient="records")
    }
    metadata = {
        "issue": ISSUE_ID,
        "workflow": "ao3_kmeans_extension",
        "metadata_status": "ao3_kmeans_extension_completed",
        "input_artifact_path": config.segment_input_path,
        "input_source": "Issue #42 AO3 risk-margin segment table",
        "evidence_slice": "held_out_test_ao3_segment_table",
        "final_test_used": True,
        "final_test_use_scope": "AO3 decision signals only; no target/outcome fields used",
        "final_test_targets_used": False,
        "clustering_features": list(CLUSTERING_FEATURES),
        "profiling_only_fields": [
            "Order_Id",
            "Order_Item_Id",
            "ao2_predicted_order_profit",
            "ao3_priority_segment",
        ],
        "preprocessing_steps": ["median_imputation", "standard_scaling"],
        "k_candidates": list(K_CANDIDATES),
        "selected_k": selected_k,
        "selection_rationale": (
            "Selected highest-silhouette candidate after applying the minimum cluster share "
            "screen where possible."
        ),
        "quality_metrics": metrics_df.to_dict(orient="records"),
        "selected_quality_metric": selected_metric,
        "row_count": row_count,
        "cluster_size_summary": cluster_size_summary,
        "comparison_to_ao3_result": {
            "weighted_dominant_ao3_segment_share": comparison[
                "weighted_dominant_ao3_segment_share"
            ],
            "mostly_duplicates_ao3_2x2": comparison["mostly_duplicates_ao3_2x2"],
            "hard_to_explain": comparison["hard_to_explain"],
            "segments_split_into_meaningful_clusters": comparison[
                "segments_split_into_meaningful_clusters"
            ],
            "clusters_add_value_beyond_2x2": adds_value,
        },
        "recommendation": recommendation,
        "recommendation_reason": rationale,
        "output_artifact_paths": output_paths,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "K-means is sensitive to scaling and outliers.",
            "Cluster stability is not formally tested in this lightweight extension.",
            "No target or outcome fields are used.",
            "The AO3 2x2 risk-margin matrix remains the primary decision tool.",
        ],
    }
    config.metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.metadata_output_path.write_text(
        json.dumps(metadata, indent=2, default=json_default),
        encoding="utf-8",
    )


def run_ao3_kmeans_extension(
    config: AO3KMeansExtensionConfig,
    logger: logging.Logger,
) -> None:
    """Execute the optional AO3 K-means extension."""
    config = with_repo_defaults(config)
    logger.info("Starting AO3 K-means extension.")
    logger.info("AO3 input path: %s", config.segment_input_path)

    ao3_df = read_ao3_segment_input(config)
    validate_input_contract(ao3_df)
    row_count = len(ao3_df)

    feature_matrix = build_feature_matrix(ao3_df)
    metrics_df, labels_by_k = fit_kmeans_candidates(feature_matrix, config.random_seed)
    selected_k = int(metrics_df.loc[metrics_df["selected"], "k"].iloc[0])
    selected_labels = labels_by_k[selected_k]

    profiles_df = build_cluster_profiles(ao3_df, selected_labels)
    comparison = build_comparison_summary(ao3_df, selected_labels)
    recommendation, rationale, adds_value = decide_recommendation(metrics_df, comparison)
    if recommendation not in VALID_RECOMMENDATIONS:
        raise ValueError(f"Unexpected AO3 K-means recommendation: {recommendation}")

    config.quality_metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.loc[:, QUALITY_COLUMNS].to_csv(config.quality_metrics_output_path, index=False)
    config.cluster_profiles_output_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_df.to_csv(config.cluster_profiles_output_path, index=False)
    write_assignments_sample(
        ao3_df,
        selected_labels,
        config.assignments_sample_output_path,
        config.sample_size,
        config.random_seed,
    )

    findings_text = build_findings_markdown(
        config=config,
        metrics_df=metrics_df,
        profiles_df=profiles_df,
        selected_k=selected_k,
        recommendation=recommendation,
        rationale=rationale,
        adds_value=adds_value,
        comparison=comparison,
        row_count=row_count,
    )
    config.findings_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.findings_output_path.write_text(findings_text, encoding="utf-8")

    docs_text = build_docs_markdown(
        config=config,
        recommendation=recommendation,
        rationale=rationale,
        selected_k=selected_k,
        row_count=row_count,
    )
    config.docs_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.docs_output_path.write_text(docs_text, encoding="utf-8")

    write_metadata(
        config=config,
        metrics_df=metrics_df,
        profiles_df=profiles_df,
        selected_k=selected_k,
        recommendation=recommendation,
        rationale=rationale,
        adds_value=adds_value,
        comparison=comparison,
        row_count=row_count,
    )

    logger.info(
        "AO3 K-means extension completed with recommendation: %s",
        recommendation,
    )


def main() -> None:
    """Run the optional AO3 K-means extension with default configuration."""
    run_ao3_kmeans_extension(AO3KMeansExtensionConfig(), configure_logging())


if __name__ == "__main__":
    main()
