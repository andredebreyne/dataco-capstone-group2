# Databricks notebook source
"""Univariate EDA for distribution, missingness, and review notes.

This notebook/script profiles variables marked for review in the conceptual
leakage screening artifact. It uses only the local Silver CSV clone and does
not approve final AO1 or AO2 predictors, build Gold tables, or train models.
"""

# COMMAND ----------

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


DEFAULT_LOCAL_SILVER_CSV = "data/silver/dataco_orders_silver.csv"
REVIEW_SCREENING_STATUSES = ("needs_group_review", "conditional_review")

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 120


def find_repo_root() -> Path:
    """Find the repository root from Databricks, local execution, or an env var."""
    env_root = os.getenv("DATACO_REPO_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    candidate_roots: list[Path] = []
    try:
        candidate_roots.append(Path(__file__).resolve().parent)
    except NameError:
        pass
    candidate_roots.append(Path.cwd().resolve())

    for starting_point in candidate_roots:
        for candidate in [starting_point, *starting_point.parents]:
            if (candidate / "data" / "references" / "leakage_conceptual_screening.csv").exists():
                return candidate

    raise FileNotFoundError(
        "Could not find repo root. Set DATACO_REPO_ROOT to the repository checkout path."
    )


REPO_ROOT = find_repo_root()
REFERENCE_DIR = REPO_ROOT / "data" / "references"
LEAKAGE_SCREENING_PATH = REFERENCE_DIR / "leakage_conceptual_screening.csv"
SILVER_SCHEMA_PATH = REFERENCE_DIR / "silver_schema_data_dictionary.csv"

SUMMARY_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_UNIVARIATE_SUMMARY_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "eda_univariate_summary.csv"),
    )
)
FIGURE_OUTPUT_DIR = Path(
    os.getenv(
        "DATACO_UNIVARIATE_FIGURE_DIR",
        str(REPO_ROOT / "report" / "figures" / "eda"),
    )
)

for output_path in [SUMMARY_OUTPUT_PATH, FIGURE_OUTPUT_DIR / ".keep"]:
    output_path.parent.mkdir(parents=True, exist_ok=True)


# COMMAND ----------


def read_project_csv(path: Path | str, **kwargs: Any) -> pd.DataFrame:
    """Read a project CSV with common encodings."""
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return pd.read_csv(path, **kwargs)


def configured_input_path() -> Path:
    """Return the approved local Silver CSV input path."""
    configured_path = os.getenv("DATACO_UNIVARIATE_EDA_INPUT_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return (REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV).resolve()


def validate_input_path(path: Path) -> None:
    """Fail fast when pointed at raw data or a non-Silver clone."""
    normalized_parts = {part.lower() for part in path.parts}
    lower_name = path.name.lower()
    if "raw" in normalized_parts or lower_name == "datacosupplychaindataset.csv":
        raise ValueError(
            "Univariate EDA must use a local Silver CSV clone, not raw data. "
            f"Expected {REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV}, or set "
            "DATACO_UNIVARIATE_EDA_INPUT_PATH to another Silver CSV clone."
        )
    if path.suffix.lower() != ".csv":
        raise ValueError(
            "Univariate EDA expects a local Silver CSV clone. "
            f"Received non-CSV path: {path}"
        )
    if "silver" not in normalized_parts and "silver" not in lower_name:
        raise ValueError(
            "DATACO_UNIVARIATE_EDA_INPUT_PATH must point to another Silver CSV clone. "
            f"Received path without a Silver marker: {path}"
        )


def load_input_dataset() -> tuple[pd.DataFrame, str, str]:
    """Load the local Silver CSV clone and return data, path, and read mode."""
    input_path = configured_input_path()
    validate_input_path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            "Local Silver CSV clone not found. Create the cleaned Silver table at "
            f"{REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV} by running "
            "notebooks/pipeline/run_project_workflow.py. Do not point this EDA "
            "at data/raw and do not duplicate Silver cleaning logic here."
        )

    return read_project_csv(input_path, low_memory=False), str(input_path), "local_silver_csv"


def normalize_column_name(name: str) -> str:
    """Normalize a raw or Silver column name for resilient matching."""
    text = str(name).strip().lower()
    text = re.sub(r"[\s_\-()]+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    return text


def resolve_column(raw_name: str, column_lookup: dict[str, str]) -> str | None:
    """Resolve a review variable to the matching loaded dataset column."""
    normalized = normalize_column_name(raw_name)
    if normalized in column_lookup:
        return column_lookup[normalized]

    substring_matches = [
        target for target in column_lookup if normalized in target or target in normalized
    ]
    if len(substring_matches) == 1:
        return column_lookup[substring_matches[0]]
    return None


def infer_datetime(series: pd.Series) -> bool:
    """Return whether a series appears to contain datetime values."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series):
        return False

    non_null = series.dropna().astype(str)
    non_null = non_null[non_null.str.strip() != ""]
    if len(non_null) < 10:
        return False

    sample = non_null.head(1000)
    coerced = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
    valid_ratio = coerced.notna().mean()
    if valid_ratio < 0.9:
        return False

    parsed = coerced[coerced.notna()]
    min_year = parsed.dt.year.min()
    max_year = parsed.dt.year.max()
    if pd.isna(min_year) or min_year < 1900 or max_year > 2100:
        return False

    return True


def safe_filename(name: str) -> str:
    """Return a filesystem-safe figure stem."""
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", name)
    return cleaned.strip("_").lower()


def numeric_outlier_stats(series: pd.Series) -> dict[str, float | int]:
    """Return IQR-based outlier stats for a numeric series."""
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outlier_mask = series.lt(lower) | series.gt(upper)
    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_fence": lower,
        "upper_fence": upper,
        "outlier_count": int(outlier_mask.sum()),
        "outlier_rate": float(outlier_mask.mean()),
    }


def missing_row(variable_name: str) -> dict[str, object]:
    """Return the summary row for a review variable absent from the input."""
    return {
        "variable_name": variable_name,
        "dataset_column": None,
        "status": "missing_in_dataset",
        "missing_rate": None,
        "unique_values": None,
        "decision": "needs_group_review",
        "notes": (
            "Review variable not found in the dataset. Confirm the source schema "
            "or column naming."
        ),
    }


def datetime_row(
    variable_name: str,
    dataset_col: str,
    series: pd.Series,
    missing_rate: float,
    unique_values: int,
    figure_path: Path,
) -> dict[str, object]:
    """Profile and plot a datetime-like review field."""
    dt_series = pd.to_datetime(series, errors="coerce")
    missing_rate = float(dt_series.isna().mean())
    date_counts = dt_series.dt.to_period("M").value_counts().sort_index()
    notes = [
        "Datetime-like field; reviewed by month.",
        (
            "Univariate quality checks only; keep pending group review until "
            "leakage screening and Gold policy are signed off."
        ),
    ]

    fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
    date_counts.plot(kind="bar", ax=ax, color="tab:green")
    ax.set_title(f"Date distribution: {dataset_col}")
    ax.set_xlabel("Period")
    ax.set_ylabel("Count")
    fig.savefig(figure_path)
    plt.close(fig)

    return {
        "variable_name": variable_name,
        "dataset_column": dataset_col,
        "status": "datetime",
        "missing_rate": missing_rate,
        "unique_values": unique_values,
        "decision": "needs_group_review",
        "notes": " ".join(notes),
        "summary_min": dt_series.min(),
        "summary_q1": None,
        "summary_median": None,
        "summary_q3": None,
        "summary_max": dt_series.max(),
        "outlier_count": None,
    }


def numeric_row(
    variable_name: str,
    dataset_col: str,
    series: pd.Series,
    missing_rate: float,
    unique_values: int,
    figure_path: Path,
) -> dict[str, object]:
    """Profile and plot a numeric review field."""
    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    stats = numeric_series.describe(
        percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    ).to_dict()
    outlier_info = (
        numeric_outlier_stats(numeric_series)
        if not numeric_series.empty
        else {"outlier_count": 0, "outlier_rate": 0.0}
    )

    notes = [
        f"Numeric field, {unique_values} distinct non-null values.",
        (
            f"Outlier rate by IQR: {outlier_info['outlier_rate']:.2%} "
            f"({outlier_info['outlier_count']} outliers)."
        ),
    ]
    if outlier_info["outlier_rate"] > 0.05:
        notes.append("High outlier rate; review for data quality, transformation, or leakage.")
    notes.append(
        "Univariate quality checks only; keep pending group review until leakage "
        "screening and Gold policy are signed off."
    )
    if unique_values == 1:
        notes.append(
            "Constant or single-value field; exclude or keep pending review because "
            "it has no modeling signal."
        )

    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(12, 4), constrained_layout=True)
    if not numeric_series.empty:
        sns.histplot(numeric_series, ax=axes[0], bins=40, color="tab:blue")
        axes[0].set_title(f"Histogram: {dataset_col}")
        sns.boxplot(x=numeric_series, ax=axes[1], color="tab:orange")
        axes[1].set_title(f"Boxplot: {dataset_col}")
    else:
        axes[0].text(0.5, 0.5, "No numeric data", ha="center", va="center")
        axes[1].text(0.5, 0.5, "No numeric data", ha="center", va="center")
    fig.savefig(figure_path)
    plt.close(fig)

    return {
        "variable_name": variable_name,
        "dataset_column": dataset_col,
        "status": "numeric",
        "missing_rate": missing_rate,
        "unique_values": unique_values,
        "decision": "needs_group_review",
        "notes": " ".join(notes),
        "summary_min": stats.get("min"),
        "summary_q1": stats.get("25%"),
        "summary_median": stats.get("50%"),
        "summary_q3": stats.get("75%"),
        "summary_max": stats.get("max"),
        "outlier_count": outlier_info["outlier_count"],
    }


def categorical_row(
    variable_name: str,
    dataset_col: str,
    series: pd.Series,
    missing_rate: float,
    unique_values: int,
    figure_path: Path,
) -> dict[str, object]:
    """Profile and plot a categorical review field."""
    categorical = series.fillna("NULL").astype(str)
    top_categories = categorical.value_counts(dropna=False).head(20)
    notes = [f"Categorical field with cardinality {unique_values}."]
    if unique_values > 100:
        notes.append("High cardinality; consider grouping, hashing, or train-only encoding.")
    if missing_rate > 0.1:
        notes.append("High missingness; review imputation or exclusion strategy.")
    notes.append(
        "Univariate quality checks only; keep pending group review until leakage "
        "screening and Gold policy are signed off."
    )
    if unique_values == 1:
        notes.append(
            "Constant or single-value field; exclude or keep pending review because "
            "it has no modeling signal."
        )

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    sns.barplot(x=top_categories.values, y=top_categories.index, ax=ax, palette="crest")
    ax.set_title(f"Top categories: {dataset_col}")
    ax.set_xlabel("Count")
    fig.savefig(figure_path)
    plt.close(fig)

    return {
        "variable_name": variable_name,
        "dataset_column": dataset_col,
        "status": "categorical",
        "missing_rate": missing_rate,
        "unique_values": unique_values,
        "decision": "needs_group_review",
        "notes": " ".join(notes),
        "summary_min": None,
        "summary_q1": None,
        "summary_median": None,
        "summary_q3": None,
        "summary_max": None,
        "outlier_count": None,
    }


def profile_variable(
    variable_name: str,
    orders_df: pd.DataFrame,
    column_lookup: dict[str, str],
) -> dict[str, object]:
    """Profile one review variable from the loaded Silver clone."""
    dataset_col = resolve_column(variable_name, column_lookup)
    if dataset_col is None:
        return missing_row(variable_name)

    series = orders_df[dataset_col]
    missing_rate = float(series.isna().mean())
    unique_values = int(series.nunique(dropna=True))
    figure_path = FIGURE_OUTPUT_DIR / f"{safe_filename(dataset_col)}.png"

    if infer_datetime(series):
        return datetime_row(
            variable_name,
            dataset_col,
            series,
            missing_rate,
            unique_values,
            figure_path,
        )

    numeric_series = pd.to_numeric(series, errors="coerce")
    numeric_ratio = float(numeric_series.notna().mean())
    if pd.api.types.is_numeric_dtype(series) or numeric_ratio >= 0.8:
        return numeric_row(
            variable_name,
            dataset_col,
            series,
            missing_rate,
            unique_values,
            figure_path,
        )

    return categorical_row(
        variable_name,
        dataset_col,
        series,
        missing_rate,
        unique_values,
        figure_path,
    )


# COMMAND ----------


def main() -> None:
    """Run the univariate EDA workflow."""
    leakage_df = read_project_csv(LEAKAGE_SCREENING_PATH)
    schema_df = read_project_csv(SILVER_SCHEMA_PATH)
    orders_df, dataset_path, dataset_read_mode = load_input_dataset()

    review_vars = sorted(
        leakage_df.loc[
            leakage_df["screening_status"].isin(REVIEW_SCREENING_STATUSES),
            "variable_name",
        ].unique()
    )
    review_schema = schema_df[schema_df["silver_column_name"].isin(review_vars)].copy()

    print(f"Loaded univariate EDA dataset: {dataset_path}")
    print(f"Read mode: {dataset_read_mode}")
    print(f"Rows: {len(orders_df):,}; columns: {len(orders_df.columns):,}")
    print(f"Review variables identified: {len(review_vars)}")
    if not review_schema.empty:
        print(
            review_schema[
                [
                    "silver_column_name",
                    "silver_data_type",
                    "review_status",
                    "leakage_restriction",
                ]
            ].head(25)
        )

    column_lookup = {normalize_column_name(column): column for column in orders_df.columns}
    matched = []
    unmatched = []
    for variable_name in review_vars:
        resolved = resolve_column(variable_name, column_lookup)
        if resolved is None:
            unmatched.append(variable_name)
        else:
            matched.append((variable_name, resolved))

    print(f"Variables matched to dataset columns: {len(matched)}")
    print(f"Variables unmatched: {len(unmatched)}")
    if unmatched:
        for variable_name in unmatched:
            print("-", variable_name)

    summary_rows = [
        profile_variable(variable_name, orders_df, column_lookup)
        for variable_name in review_vars
    ]
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)

    print("Saved summary to", SUMMARY_OUTPUT_PATH)
    print("Saved figures to", FIGURE_OUTPUT_DIR)
    print(summary_df.head(25).to_string(index=False))
    print("Decision counts:")
    print(summary_df["decision"].value_counts(dropna=False))
    print("")
    print("Top review notes:")
    print(
        summary_df[
            [
                "variable_name",
                "dataset_column",
                "decision",
                "missing_rate",
                "unique_values",
                "notes",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()

