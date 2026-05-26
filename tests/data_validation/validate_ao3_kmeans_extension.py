"""Validate AO3 K-means extension artifacts for Issue #44."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


ISSUE_ID = "#44"
VALID_RECOMMENDATIONS = {
    "adopt_as_optional_context",
    "document_but_do_not_use",
    "do_not_adopt",
}

FORBIDDEN_TARGET_FEATURES = {
    "Late_delivery_risk",
    "Order_Profit_Per_Order",
    "Delivery_Status",
    "Days_for_shipping_real",
    "Order_Item_Profit_Ratio",
    "Benefit_per_order",
    "ao3_order_value",
}

REQUIRED_QUALITY_COLUMNS = {
    "k",
    "inertia",
    "silhouette_score",
    "min_cluster_size",
    "min_cluster_share",
    "max_cluster_share",
    "cluster_size_summary",
    "meets_min_share_rule",
    "selected",
}

REQUIRED_PROFILE_COLUMNS = {
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
}

REQUIRED_FINDINGS_TERMS = {
    "k-means",
    "ao3",
    "risk-margin matrix",
    "beyond 2x2",
    "recommendation",
    "limitations",
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
METADATA_PATH = Path(
    os.getenv(
        "DATACO_AO3_KMEANS_METADATA_PATH",
        str(
            REPO_ROOT
            / "models/ao3_integration/kmeans_extension/ao3_kmeans_extension_metadata.json"
        ),
    )
)


def normalized_name(value: str) -> str:
    """Normalize a column or feature name for conservative matching."""
    return value.lower().replace(" ", "_").replace("-", "_")


def assert_path_exists(path_value: str | Path, description: str) -> Path:
    """Assert an expected artifact path exists and return it."""
    path = Path(path_value)
    assert path.exists(), f"Missing {description}: {path}"
    return path


def assert_findings_coverage(findings_path: Path) -> None:
    """Validate that the findings note contains the required review language."""
    findings_text = findings_path.read_text(encoding="utf-8").lower()
    missing_terms = sorted(term for term in REQUIRED_FINDINGS_TERMS if term not in findings_text)
    assert not missing_terms, f"AO3 K-means findings missing terms: {missing_terms}"
    assert "do clusters add value" in findings_text or "clusters_add_value" in findings_text, (
        "Findings must explicitly state whether clusters add value beyond the AO3 2x2 matrix."
    )


def main() -> None:
    """Run AO3 K-means extension artifact validation."""
    assert_path_exists(METADATA_PATH, "AO3 K-means metadata JSON")
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert metadata["issue"] == ISSUE_ID
    assert metadata["workflow"] == "ao3_kmeans_extension"
    assert metadata.get("recommendation") in VALID_RECOMMENDATIONS
    assert metadata.get("input_artifact_path"), "Input artifact path must be recorded."
    assert "final_test_used" in metadata, "final_test_used status must be recorded."
    assert metadata.get("final_test_targets_used") is False, "K-means must not use target outcomes."

    clustering_features = metadata.get("clustering_features")
    assert isinstance(clustering_features, list) and clustering_features, (
        "Clustering features must be listed."
    )
    forbidden_normalized = {normalized_name(feature) for feature in FORBIDDEN_TARGET_FEATURES}
    forbidden_used = sorted(
        feature
        for feature in clustering_features
        if normalized_name(str(feature)) in forbidden_normalized
    )
    assert not forbidden_used, f"Forbidden target/outcome/support features used: {forbidden_used}"

    k_candidates = metadata.get("k_candidates")
    assert isinstance(k_candidates, list) and k_candidates, "K candidates must be listed."
    assert set(k_candidates) == {3, 4, 5}, f"Unexpected K candidates: {k_candidates}"
    assert metadata.get("selected_k") in k_candidates, "Selected K must come from K candidates."

    output_paths = metadata.get("output_artifact_paths", {})
    quality_path = assert_path_exists(
        output_paths.get("quality_metrics", ""),
        "AO3 K-means quality metrics CSV",
    )
    profile_path = assert_path_exists(
        output_paths.get("cluster_profiles", ""),
        "AO3 K-means cluster profile CSV",
    )
    findings_path = assert_path_exists(
        output_paths.get("findings", ""),
        "AO3 K-means findings markdown",
    )

    quality_df = pd.read_csv(quality_path)
    profile_df = pd.read_csv(profile_path)
    assert not quality_df.empty, "AO3 K-means quality metrics must not be empty."
    assert not profile_df.empty, "AO3 K-means cluster profiles must not be empty."

    missing_quality_columns = sorted(REQUIRED_QUALITY_COLUMNS.difference(quality_df.columns))
    assert not missing_quality_columns, (
        f"AO3 K-means quality metrics missing columns: {missing_quality_columns}"
    )
    missing_profile_columns = sorted(REQUIRED_PROFILE_COLUMNS.difference(profile_df.columns))
    assert not missing_profile_columns, (
        f"AO3 K-means cluster profiles missing columns: {missing_profile_columns}"
    )

    selected_rows = quality_df[quality_df["selected"].astype(str).str.lower().isin({"true", "1"})]
    assert len(selected_rows) == 1, "Exactly one K candidate must be marked selected."

    assert (profile_df["row_count"] > 0).all(), "Cluster counts must be positive."
    row_share_sum = float(profile_df["row_share"].sum())
    assert abs(row_share_sum - 1.0) <= 0.01, (
        f"Cluster row shares must sum approximately to 1; found {row_share_sum}."
    )

    metadata_row_count = int(metadata["row_count"])
    profile_row_count = int(profile_df["row_count"].sum())
    assert profile_row_count == metadata_row_count, (
        "Cluster profile row count does not match metadata row count."
    )

    comparison = metadata.get("comparison_to_ao3_result", {})
    assert "clusters_add_value_beyond_2x2" in comparison, (
        "Metadata must record whether clusters add value beyond AO3 2x2."
    )
    assert metadata["recommendation"] != "adopt_as_optional_context" or comparison[
        "clusters_add_value_beyond_2x2"
    ] is True, "Adoption requires documented value beyond AO3 2x2."

    assert_findings_coverage(findings_path)
    print("AO3 K-means extension validation passed.")


if __name__ == "__main__":
    main()
