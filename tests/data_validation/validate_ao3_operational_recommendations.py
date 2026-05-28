"""Validate AO3 operational recommendation matrix for Issue #45."""

from __future__ import annotations

import csv
import os
from pathlib import Path


EXPECTED_SEGMENTS = {
    "protect_high_value_at_risk",
    "expedite_selectively",
    "preserve_service",
    "standard_process",
    "requires_score_review",
    "requires_margin_review",
}

REQUIRED_COLUMNS = {
    "ao3_priority_segment",
    "segment_interpretation",
    "recommended_action",
    "logistics_attention",
    "pricing_or_margin_attention",
    "monitoring_focus",
    "dashboard_use",
    "evidence_basis",
    "limitations",
}

OVERSTATED_TERMS = (
    "guarantee",
    "guaranteed",
    "prove improvement",
    "proves improvement",
    "maximize profit",
    "will improve",
    "will reduce",
    "causal impact",
)

AUTOMATED_ACTION_TERMS = (
    "automatically expedite",
    "automatic expedite",
    "auto-expedite",
    "automatic operational action",
)


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
RECOMMENDATION_PATH = Path(
    os.getenv(
        "DATACO_AO3_RECOMMENDATION_MATRIX_PATH",
        str(REPO_ROOT / "data/references/ao3_operational_recommendation_matrix.csv"),
    )
)
BENCHMARK_SUMMARY_PATH = REPO_ROOT / "data/references/ao3_risk_margin_benchmark_segment_summary.csv"
BENCHMARK_INSIGHT_PATH = REPO_ROOT / "data/references/ao3_risk_margin_benchmark_insights.csv"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read CSV rows as dictionaries."""
    with path.open("r", encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def normalize(value: str | None) -> str:
    """Normalize text for validation checks."""
    return str(value or "").strip()


def combined_row_text(row: dict[str, str]) -> str:
    """Return lowercase text for all row fields."""
    return " ".join(normalize(value).lower() for value in row.values())


def main() -> None:
    """Run AO3 operational recommendation matrix validation."""
    assert RECOMMENDATION_PATH.exists(), f"Missing AO3 recommendation matrix: {RECOMMENDATION_PATH}"
    assert BENCHMARK_SUMMARY_PATH.exists(), f"Missing AO3 benchmark summary: {BENCHMARK_SUMMARY_PATH}"
    assert BENCHMARK_INSIGHT_PATH.exists(), f"Missing AO3 benchmark insights: {BENCHMARK_INSIGHT_PATH}"

    rows = read_csv_rows(RECOMMENDATION_PATH)
    assert rows, "AO3 recommendation matrix must contain rows."

    missing_columns = sorted(REQUIRED_COLUMNS.difference(rows[0]))
    assert not missing_columns, f"AO3 recommendation matrix missing columns: {missing_columns}"

    segments = {normalize(row["ao3_priority_segment"]) for row in rows}
    assert segments == EXPECTED_SEGMENTS, (
        "AO3 recommendation matrix must cover exactly the expected segments; "
        f"found {sorted(segments)}."
    )
    assert len(rows) == len(EXPECTED_SEGMENTS), "AO3 recommendation matrix has duplicate segment rows."

    benchmark_rows = read_csv_rows(BENCHMARK_SUMMARY_PATH)
    benchmark_segments = {
        normalize(row["ao3_priority_segment"]) for row in benchmark_rows
    }

    assert EXPECTED_SEGMENTS.issubset(benchmark_segments), (
        "AO3 benchmark summary does not cover every recommendation segment."
    )

    benchmark_counts = {
        normalize(row["ao3_priority_segment"]): int(float(row["row_count"]))
        for row in benchmark_rows
    }

    for row in rows:
        segment = normalize(row["ao3_priority_segment"])
        basis = normalize(row["evidence_basis"]).lower()

        expected_count = str(benchmark_counts.get(segment, ""))

        if expected_count and expected_count != "0":
            assert expected_count in basis, (
                f"{segment} evidence_basis cites stale count; expected {expected_count}"
            )

    for row in rows:
        segment = normalize(row["ao3_priority_segment"])
        for column in REQUIRED_COLUMNS.difference({"ao3_priority_segment"}):
            assert normalize(row[column]), f"{segment} has empty recommendation field: {column}"

        row_text = combined_row_text(row)
        overstated_matches = [term for term in OVERSTATED_TERMS if term in row_text]
        assert not overstated_matches, (
            f"{segment} uses overstated recommendation language: {overstated_matches}"
        )

        assert "benchmark" in row_text or "predicted" in row_text, (
            f"{segment} recommendation must be tied to benchmark or predicted-score evidence."
        )
        assert "not prove" in row_text or "limits" in row_text or "limited" in row_text, (
            f"{segment} recommendation must document an assumption or limitation."
        )

        if segment.startswith("requires_"):
            automated_matches = [term for term in AUTOMATED_ACTION_TERMS if term in row_text]
            assert not automated_matches, (
                f"{segment} fallback must not recommend automatic operational action: {automated_matches}"
            )
            assert "data" in row_text and "review" in row_text, (
                f"{segment} fallback must be framed as a data-review category."
            )

    insight_text = "\n".join(combined_row_text(row) for row in read_csv_rows(BENCHMARK_INSIGHT_PATH))
    assert "h3_support_statement" in insight_text, "AO3 benchmark insights must include H3 support statement."
    assert "without overstating" in insight_text, "AO3 recommendations depend on benchmark caveats."

    print("AO3 operational recommendation matrix validation passed.")


if __name__ == "__main__":
    main()
