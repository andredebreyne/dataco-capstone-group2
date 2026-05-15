# Databricks notebook source
"""AO1 class imbalance analysis for late-delivery risk.

This notebook/script measures the distribution of Late_delivery_risk overall
and across leakage-safe operational slices. It uses only the local Silver CSV
clone and does not train models, build Gold tables, optimize thresholds, or
apply resampling.
"""

# COMMAND ----------

from __future__ import annotations

import html
import math
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd


TARGET_COLUMN = "Late_delivery_risk"
DEFAULT_LOCAL_SILVER_CSV = "data/silver/dataco_orders_silver.csv"
MIN_SUPPORT_FRACTION = 0.005
MIN_SUPPORT_FLOOR = 100

NO_RESAMPLING_STATEMENT = (
    "No resampling is applied during EDA. If resampling such as SMOTE, "
    "undersampling, or class weighting is considered later, it must be applied "
    "only inside the training fold or training data after the chronological "
    "split, never before splitting and never on the full dataset."
)

APPROVED_GROUPING_CANDIDATES = [
    "Shipping Mode",
    "shipping_speed_tier",
    "Market",
    "Order Region",
    "Order Country",
    "Customer Segment",
    "Category Name",
    "Department Name",
    "order_month",
    "order_day_of_week",
    "order_is_weekend",
]


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
SCREENING_PATH = REPO_ROOT / "data" / "references" / "leakage_conceptual_screening.csv"
AVAILABILITY_PATH = REPO_ROOT / "data" / "references" / "feature_availability_map.csv"

OVERALL_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_IMBALANCE_OVERALL_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_class_imbalance_overall.csv"),
    )
)
SLICE_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_IMBALANCE_SLICE_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_class_imbalance_by_slice.csv"),
    )
)
GROUP_REVIEW_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_IMBALANCE_GROUP_REVIEW_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_class_imbalance_group_review_list.csv"),
    )
)
FINDINGS_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_IMBALANCE_FINDINGS_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_class_imbalance_findings.md"),
    )
)
FIGURE_OUTPUT_DIR = Path(
    os.getenv(
        "DATACO_AO1_IMBALANCE_FIGURE_DIR",
        str(REPO_ROOT / "report" / "figures" / "eda"),
    )
)

for output_path in [
    OVERALL_OUTPUT_PATH,
    SLICE_OUTPUT_PATH,
    GROUP_REVIEW_OUTPUT_PATH,
    FINDINGS_OUTPUT_PATH,
    FIGURE_OUTPUT_DIR / ".keep",
]:
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
    configured_path = os.getenv("DATACO_AO1_IMBALANCE_INPUT_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return (REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV).resolve()


def validate_input_path(path: Path) -> None:
    """Fail fast when pointed at raw data or a non-Silver clone."""
    normalized_parts = {part.lower() for part in path.parts}
    lower_name = path.name.lower()
    if "raw" in normalized_parts or lower_name == "datacosupplychaindataset.csv":
        raise ValueError(
            "AO1 class imbalance analysis must use a local Silver CSV clone, not raw data. "
            f"Expected {REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV}, or set "
            "DATACO_AO1_IMBALANCE_INPUT_PATH to another Silver CSV clone."
        )
    if path.suffix.lower() != ".csv":
        raise ValueError(
            "AO1 class imbalance analysis expects a local Silver CSV clone. "
            f"Received non-CSV path: {path}"
        )
    if "silver" not in normalized_parts and "silver" not in lower_name:
        raise ValueError(
            "DATACO_AO1_IMBALANCE_INPUT_PATH must point to another Silver CSV clone. "
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


screening_df = read_project_csv(SCREENING_PATH)
availability_df = read_project_csv(AVAILABILITY_PATH)
orders_df, dataset_path, dataset_read_mode = load_input_dataset()
loaded_column_count = len(orders_df.columns)

print(f"Loaded AO1 imbalance dataset: {dataset_path}")
print(f"Read mode: {dataset_read_mode}")
print(f"Rows: {len(orders_df):,}; columns: {loaded_column_count:,}")


# COMMAND ----------

def canonicalize_column_name(column_name: str) -> str:
    """Match the Silver canonicalization rule used by the project pipeline."""
    canonical_name = column_name.strip()
    canonical_name = re.sub(r"[ ,;{}()\n\t=]", "_", canonical_name)
    canonical_name = re.sub(r"_+", "_", canonical_name)
    if column_name.startswith("_"):
        return canonical_name
    return canonical_name.strip("_")


source_to_silver = dict(
    zip(availability_df["source_column"], availability_df["silver_column"], strict=False)
)


def column_candidates(variable_name: str) -> list[str]:
    """Return possible raw, Silver, and canonical names for a field."""
    candidates = [
        variable_name,
        source_to_silver.get(variable_name),
        canonicalize_column_name(variable_name),
    ]
    return [candidate for candidate in dict.fromkeys(candidates) if candidate]


def resolve_column(df: pd.DataFrame, variable_name: str) -> str | None:
    """Resolve a screening variable to the loaded data frame column name."""
    for candidate in column_candidates(variable_name):
        if candidate in df.columns:
            return candidate
    return None


def first_available_column(df: pd.DataFrame, *names: str) -> str | None:
    """Return the first available source or Silver column from several alternatives."""
    for name in names:
        resolved = resolve_column(df, name)
        if resolved:
            return resolved
        if name in df.columns:
            return name
    return None


def as_numeric(series: pd.Series) -> pd.Series:
    """Coerce a Series to numeric values."""
    return pd.to_numeric(series, errors="coerce")


def derive_approved_grouping_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive deterministic pre-shipment grouping features approved in screening."""
    featured = df.copy()

    order_ts_col = first_available_column(featured, "order date (DateOrders)", "order_date_DateOrders")
    if order_ts_col:
        order_ts = pd.to_datetime(
            featured[order_ts_col],
            format="%m/%d/%Y %H:%M",
            errors="coerce",
        )
        if order_ts.isna().all():
            order_ts = pd.to_datetime(featured[order_ts_col], errors="coerce")

        featured["order_month"] = order_ts.dt.month.astype("Int64")
        featured["order_day_of_week"] = (((order_ts.dt.dayofweek + 1) % 7) + 1).astype("Int64")
        featured["order_is_weekend"] = order_ts.dt.dayofweek.isin([5, 6]).astype("Int64")

    scheduled_col = first_available_column(
        featured,
        "Days for shipment (scheduled)",
        "Days_for_shipment_scheduled",
    )
    if scheduled_col:
        scheduled_days = as_numeric(featured[scheduled_col])
        featured["shipping_speed_tier"] = pd.Series("economy", index=featured.index, dtype="string")
        featured.loc[scheduled_days <= 3, "shipping_speed_tier"] = "standard"
        featured.loc[scheduled_days <= 1, "shipping_speed_tier"] = "expedited"
        featured.loc[scheduled_days.isna(), "shipping_speed_tier"] = pd.NA

    return featured


orders_df = derive_approved_grouping_features(orders_df)


# COMMAND ----------

target_col = resolve_column(orders_df, TARGET_COLUMN)
if target_col is None:
    raise ValueError(f"Target column {TARGET_COLUMN} was not found in the loaded Silver dataset.")

target_numeric = as_numeric(orders_df[target_col])
missing_target_count = int(target_numeric.isna().sum())
valid_binary_mask = target_numeric.isin([0, 1])
invalid_target_count = int((target_numeric.notna() & ~valid_binary_mask).sum())

if invalid_target_count:
    invalid_values = sorted(target_numeric[target_numeric.notna() & ~valid_binary_mask].unique())
    raise ValueError(
        f"{TARGET_COLUMN} must be binary or safely interpretable as binary. "
        f"Found invalid values: {invalid_values[:10]}"
    )
if not valid_binary_mask.any():
    raise ValueError(f"{TARGET_COLUMN} has no valid binary 0/1 rows.")

analysis_df = orders_df.loc[valid_binary_mask].copy()
analysis_df[target_col] = target_numeric.loc[valid_binary_mask].astype("int8")

total_rows = len(orders_df)
valid_target_rows = len(analysis_df)
late_count = int((analysis_df[target_col] == 1).sum())
not_late_count = int((analysis_df[target_col] == 0).sum())
late_rate = late_count / valid_target_rows
not_late_rate = not_late_count / valid_target_rows
majority_class = "late_1" if late_count >= not_late_count else "not_late_0"
minority_class = "not_late_0" if majority_class == "late_1" else "late_1"
majority_count = max(late_count, not_late_count)
minority_count = min(late_count, not_late_count)
majority_minority_ratio = majority_count / minority_count if minority_count else math.inf
positive_class_role = "majority" if late_count > not_late_count else "minority"

if majority_minority_ratio < 1.5:
    imbalance_severity = "mild"
elif majority_minority_ratio < 3.0:
    imbalance_severity = "moderate"
else:
    imbalance_severity = "severe"

min_support_count = max(MIN_SUPPORT_FLOOR, math.ceil(valid_target_rows * MIN_SUPPORT_FRACTION))

print(f"Valid AO1 target rows: {valid_target_rows:,}")
print(f"Missing target rows: {missing_target_count:,}")
print(f"Late-delivery rows: {late_count:,} ({late_rate:.2%})")
print(f"Not-late rows: {not_late_count:,} ({not_late_rate:.2%})")
print(f"Imbalance severity: {imbalance_severity}; ratio {majority_minority_ratio:.3f}:1")
print(NO_RESAMPLING_STATEMENT)


# COMMAND ----------

def format_rate(value: float) -> str:
    return f"{value:.2%}"


def format_ratio(value: float) -> str:
    return "infinite" if math.isinf(value) else f"{value:.3f}:1"


def display_path_for_outputs(path_string: str) -> str:
    """Use repo-relative paths in committed outputs when possible."""
    path = Path(path_string)
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


overall_rows = [
    {
        "metric": "dataset_path",
        "value": display_path_for_outputs(dataset_path),
        "interpretation": "Local Silver CSV clone used for this EDA.",
    },
    {
        "metric": "dataset_read_mode",
        "value": dataset_read_mode,
        "interpretation": "No raw-data fallback is allowed for this analysis.",
    },
    {
        "metric": "target_column",
        "value": target_col,
        "interpretation": "AO1 binary late-delivery target.",
    },
    {
        "metric": "total_rows",
        "value": total_rows,
        "interpretation": "Rows loaded from the local Silver clone.",
    },
    {
        "metric": "rows_with_valid_binary_target",
        "value": valid_target_rows,
        "interpretation": "Rows retained for class imbalance calculations.",
    },
    {
        "metric": "missing_target_count",
        "value": missing_target_count,
        "interpretation": "Missing AO1 target rows are excluded from rate calculations.",
    },
    {
        "metric": "invalid_target_count",
        "value": invalid_target_count,
        "interpretation": "Non-missing target values outside 0/1 would fail this notebook.",
    },
    {
        "metric": "count_late_1",
        "value": late_count,
        "interpretation": "Positive AO1 class.",
    },
    {
        "metric": "count_not_late_0",
        "value": not_late_count,
        "interpretation": "Negative AO1 class.",
    },
    {
        "metric": "late_delivery_rate",
        "value": round(late_rate, 6),
        "interpretation": f"{format_rate(late_rate)} of valid rows are late deliveries.",
    },
    {
        "metric": "not_late_rate",
        "value": round(not_late_rate, 6),
        "interpretation": f"{format_rate(not_late_rate)} of valid rows are not late.",
    },
    {
        "metric": "majority_class",
        "value": majority_class,
        "interpretation": "Class with the larger count in the current Silver clone.",
    },
    {
        "metric": "minority_class",
        "value": minority_class,
        "interpretation": "Class with the smaller count in the current Silver clone.",
    },
    {
        "metric": "majority_minority_class_ratio",
        "value": round(majority_minority_ratio, 6),
        "interpretation": f"Majority-to-minority ratio is {format_ratio(majority_minority_ratio)}.",
    },
    {
        "metric": "imbalance_severity",
        "value": imbalance_severity,
        "interpretation": (
            f"Class imbalance is {imbalance_severity}; the positive late class is the "
            f"{positive_class_role} class."
        ),
    },
    {
        "metric": "minimum_slice_support",
        "value": min_support_count,
        "interpretation": "Slice rows below this threshold are flagged to avoid overinterpretation.",
    },
    {
        "metric": "metric_implication",
        "value": "accuracy_not_sufficient",
        "interpretation": (
            "AO1 should report recall, precision, F1, confusion matrix, AUC-ROC, "
            "and PR-AUC if imbalance remains meaningful after split."
        ),
    },
    {
        "metric": "threshold_implication",
        "value": "validation_data_required",
        "interpretation": (
            "Operational thresholds should be selected later on validation data, "
            "not from the final test set."
        ),
    },
    {
        "metric": "resampling_statement",
        "value": "no_resampling_in_eda",
        "interpretation": NO_RESAMPLING_STATEMENT,
    },
]

overall_df = pd.DataFrame(overall_rows)
overall_df.to_csv(OVERALL_OUTPUT_PATH, index=False)
print(f"Wrote overall table: {OVERALL_OUTPUT_PATH}")


# COMMAND ----------

screening_by_variable = {
    str(row["variable_name"]): row for _, row in screening_df.iterrows()
}


def is_approved_grouping_variable(variable_name: str) -> tuple[bool, str]:
    """Return whether a variable is safe for this EDA slice and why."""
    row = screening_by_variable.get(variable_name)
    if row is None:
        return False, "not_found_in_leakage_conceptual_screening"

    ao1_policy = str(row["ao1_policy"])
    screening_status = str(row["screening_status"])
    modeling_policy = str(row["modeling_policy"])
    timing = str(row["decision_time_availability"])

    if ao1_policy != "allowed":
        return False, f"excluded_by_ao1_policy_{ao1_policy}"
    if screening_status == "needs_group_review" or "conditional" in modeling_policy:
        return False, "requires_group_review_not_approved_for_this_slice"
    if modeling_policy != "candidate_feature":
        return False, f"not_a_candidate_feature_{modeling_policy}"
    if "post" in timing or "after_" in timing or timing == "target_or_outcome":
        return False, f"not_decision_time_safe_{timing}"
    return True, (
        "approved_by_leakage_conceptual_screening: "
        f"ao1_policy={ao1_policy}; screening_status={screening_status}; "
        f"decision_time_availability={timing}"
    )


def display_group_value(variable_name: str, value: Any) -> str:
    """Format grouping values for report tables."""
    if pd.isna(value):
        return "(missing)"
    value_text = str(value)
    if variable_name == "order_is_weekend":
        return "weekend" if value_text in {"1", "1.0", "True", "true"} else "weekday"
    if variable_name == "order_day_of_week":
        day_map = {
            "1": "1_sunday",
            "2": "2_monday",
            "3": "3_tuesday",
            "4": "4_wednesday",
            "5": "5_thursday",
            "6": "6_friday",
            "7": "7_saturday",
        }
        return day_map.get(value_text.replace(".0", ""), value_text)
    if variable_name == "order_month":
        month_map = {
            "1": "01_january",
            "2": "02_february",
            "3": "03_march",
            "4": "04_april",
            "5": "05_may",
            "6": "06_june",
            "7": "07_july",
            "8": "08_august",
            "9": "09_september",
            "10": "10_october",
            "11": "11_november",
            "12": "12_december",
        }
        return month_map.get(value_text.replace(".0", ""), value_text)
    return value_text.strip() or "(blank)"


def build_slice_rows(variable_name: str, column_name: str, review_result: str) -> list[dict[str, Any]]:
    """Build class imbalance rows for a single approved grouping variable."""
    grouped_input = pd.DataFrame(
        {
            "group_value": analysis_df[column_name].map(
                lambda value: display_group_value(variable_name, value)
            ),
            "target": analysis_df[target_col],
        }
    )
    grouped = (
        grouped_input.groupby("group_value", dropna=False)["target"]
        .agg(row_count="count", late_count="sum")
        .reset_index()
    )
    grouped["late_count"] = grouped["late_count"].astype(int)
    grouped["not_late_count"] = grouped["row_count"] - grouped["late_count"]
    grouped["late_delivery_rate"] = grouped["late_count"] / grouped["row_count"]
    grouped["difference_from_overall_rate"] = grouped["late_delivery_rate"] - late_rate
    grouped = grouped.sort_values(["row_count", "group_value"], ascending=[False, True])

    rows = []
    for _, row in grouped.iterrows():
        support_flag = (
            "meets_min_support"
            if int(row["row_count"]) >= min_support_count
            else f"below_min_support_{min_support_count}_rows"
        )
        rows.append(
            {
                "grouping_variable": variable_name,
                "group_value": row["group_value"],
                "row_count": int(row["row_count"]),
                "late_count": int(row["late_count"]),
                "not_late_count": int(row["not_late_count"]),
                "late_delivery_rate": round(float(row["late_delivery_rate"]), 6),
                "difference_from_overall_rate": round(
                    float(row["difference_from_overall_rate"]),
                    6,
                ),
                "sample_size_flag": support_flag,
                "leakage_review_result": review_result,
                "eda_usage_note": (
                    "Safe for descriptive AO1 class imbalance and modeling design "
                    "discussion; not final feature approval."
                ),
            }
        )
    return rows


approved_groupings: list[dict[str, str]] = []
excluded_requested_groupings: list[dict[str, str]] = []
slice_rows: list[dict[str, Any]] = []

for grouping_variable in APPROVED_GROUPING_CANDIDATES:
    approved, review_result = is_approved_grouping_variable(grouping_variable)
    resolved_column = resolve_column(analysis_df, grouping_variable)
    if approved and resolved_column:
        approved_groupings.append(
            {
                "grouping_variable": grouping_variable,
                "analysis_column": resolved_column,
                "leakage_review_result": review_result,
            }
        )
        slice_rows.extend(build_slice_rows(grouping_variable, resolved_column, review_result))
    else:
        excluded_requested_groupings.append(
            {
                "grouping_variable": grouping_variable,
                "analysis_column": resolved_column or "",
                "reason": review_result if not approved else "column_not_available_in_silver_or_derived_features",
            }
        )

slice_df = pd.DataFrame(slice_rows)
slice_df.to_csv(SLICE_OUTPUT_PATH, index=False)

print(f"Wrote slice table: {SLICE_OUTPUT_PATH}")
print("Approved grouping fields:")
for grouping in approved_groupings:
    print(f"- {grouping['grouping_variable']} -> {grouping['analysis_column']}")
if excluded_requested_groupings:
    print("Requested grouping candidates excluded from this EDA:")
    for grouping in excluded_requested_groupings:
        print(f"- {grouping['grouping_variable']}: {grouping['reason']}")


# COMMAND ----------

def potential_slice_value(variable_name: str) -> str:
    """Describe whether a review-needed field is available without approving it."""
    column_name = resolve_column(analysis_df, variable_name)
    if column_name is None:
        return "not present or not derived in this focused EDA input"

    series = analysis_df[column_name]
    non_missing = series.dropna()
    if non_missing.empty:
        return "available but fully missing in current Silver clone"

    unique_count = int(non_missing.nunique(dropna=True))
    top_value = non_missing.astype("string").value_counts(dropna=True).head(1)
    if top_value.empty:
        return f"available; {unique_count} non-missing values"
    top_label = str(top_value.index[0])
    top_count = int(top_value.iloc[0])
    if unique_count > 50:
        return (
            f"available; {unique_count} distinct values; high-cardinality review required "
            f"before slicing; top value {top_label} has {top_count:,} rows"
        )
    return f"available; {unique_count} distinct values; top value {top_label} has {top_count:,} rows"


def recommended_treatment(row: pd.Series) -> str:
    """Recommend how to handle a conditional or review-needed field."""
    variable_name = str(row["variable_name"])
    lower_name = variable_name.lower()
    modeling_policy = str(row["modeling_policy"])
    if variable_name == "order date (DateOrders)":
        return "Use approved derived order calendar fields; do not use raw timestamp directly."
    if any(token in lower_name for token in ["profit", "benefit", "sales", "price", "discount", "total"]):
        return "Exclude from AO1 imbalance slices unless the team separately approves descriptive use."
    if any(token in lower_name for token in ["id", "key", "name", "city", "zipcode", "latitude", "longitude"]):
        return "Defer until grouping, privacy, cardinality, and stability are reviewed."
    if "conditional" in modeling_policy:
        return "Do not use as an approved modeling slice until group validation is complete."
    return "Defer pending group validation."


review_mask = (
    (screening_df["ao1_policy"].astype(str) == "conditional")
    | (screening_df["screening_status"].astype(str) == "needs_group_review")
    | (screening_df["modeling_policy"].astype(str).str.contains("conditional", na=False))
)
review_candidates = screening_df.loc[review_mask].copy()

review_rows = []
for _, row in review_candidates.iterrows():
    variable_name = str(row["variable_name"])
    review_rows.append(
        {
            "variable_name": variable_name,
            "screening_status": row["screening_status"],
            "ao1_policy": row["ao1_policy"],
            "reason_for_review": f"{row['rationale']} Required action: {row['required_action']}",
            "potential_slice_value": potential_slice_value(variable_name),
            "recommended_treatment": recommended_treatment(row),
            "group_decision_needed": (
                "Decide whether this field can be used for AO1 modeling design, "
                "descriptive EDA only, or should remain excluded."
            ),
        }
    )

group_review_df = pd.DataFrame(review_rows)
group_review_df.to_csv(GROUP_REVIEW_OUTPUT_PATH, index=False)

print(f"Wrote group review list: {GROUP_REVIEW_OUTPUT_PATH}")
print(f"Conditional or needs_group_review variables listed: {len(group_review_df):,}")


# COMMAND ----------

def svg_overall_distribution(output_path: Path) -> None:
    """Write a focused SVG chart for the overall class distribution."""
    width = 760
    height = 270
    left = 170
    top = 70
    bar_width = 420
    row_height = 58
    rows = [
        ("late_1", late_count, late_rate, "#2f6f73"),
        ("not_late_0", not_late_count, not_late_rate, "#7a8a99"),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="20" y="34" font-family="Arial, sans-serif" font-size="20" font-weight="700">AO1 Overall Class Distribution</text>',
    ]
    for index, (label, count, rate, color) in enumerate(rows):
        y = top + index * row_height
        length = max(2, int(bar_width * rate))
        parts.extend(
            [
                f'<text x="20" y="{y + 20}" font-family="Arial, sans-serif" font-size="14">{html.escape(label)}</text>',
                f'<rect x="{left}" y="{y}" width="{length}" height="28" rx="2" fill="{color}"/>',
                f'<text x="{left + length + 10}" y="{y + 20}" font-family="Arial, sans-serif" font-size="13">{count:,} ({rate:.1%})</text>',
            ]
        )
    parts.extend(
        [
            f'<text x="20" y="{height - 24}" font-family="Arial, sans-serif" font-size="12" fill="#555">Severity: {imbalance_severity}; majority/minority ratio {format_ratio(majority_minority_ratio)}</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(parts), encoding="utf-8")


def svg_rate_by_group(
    rows: pd.DataFrame,
    title: str,
    output_path: Path,
    max_rows: int = 10,
    sort_by_abs_diff: bool = True,
) -> None:
    """Write a lightweight SVG horizontal bar chart for late-delivery rates."""
    plot_rows = rows[rows["sample_size_flag"] == "meets_min_support"].copy()
    if plot_rows.empty:
        return
    if sort_by_abs_diff:
        plot_rows["_sort"] = plot_rows["difference_from_overall_rate"].abs()
        plot_rows = plot_rows.sort_values("_sort", ascending=False)
    else:
        plot_rows = plot_rows.sort_values("group_value")
    plot_rows = plot_rows.head(max_rows)

    width = 980
    row_height = 34
    left = 300
    top = 58
    bar_width = 520
    height = top + row_height * len(plot_rows) + 42

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="20" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{left}" y="50" font-family="Arial, sans-serif" font-size="12" fill="#555">Late-delivery rate</text>',
    ]

    for index, (_, row) in enumerate(plot_rows.iterrows()):
        y = top + index * row_height
        label = str(row["group_value"])
        count = int(row["row_count"])
        rate = float(row["late_delivery_rate"])
        diff = float(row["difference_from_overall_rate"])
        length = max(2, int(bar_width * min(max(rate, 0.0), 1.0)))
        parts.extend(
            [
                f'<text x="20" y="{y + 18}" font-family="Arial, sans-serif" font-size="13">{html.escape(label[:42])}</text>',
                f'<rect x="{left}" y="{y}" width="{length}" height="22" rx="2" fill="#2f6f73"/>',
                f'<text x="{left + length + 8}" y="{y + 16}" font-family="Arial, sans-serif" font-size="12">{rate:.1%} ({diff * 100:+.1f} pp, n={count:,})</text>',
            ]
        )

    overall_x = left + int(bar_width * late_rate)
    parts.extend(
        [
            f'<line x1="{overall_x}" x2="{overall_x}" y1="{top - 6}" y2="{height - 24}" stroke="#b33" stroke-width="2" stroke-dasharray="5,4"/>',
            f'<text x="{overall_x + 6}" y="{height - 12}" font-family="Arial, sans-serif" font-size="12" fill="#b33">overall {late_rate:.1%}</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(parts), encoding="utf-8")


saved_figures: list[Path] = []
overall_figure = FIGURE_OUTPUT_DIR / "ao1_class_imbalance_overall.svg"
svg_overall_distribution(overall_figure)
saved_figures.append(overall_figure)

figure_specs = [
    (
        "Shipping Mode",
        "ao1_class_imbalance_late_rate_by_shipping_mode.svg",
        "AO1 Late-Delivery Rate by Shipping Mode",
        True,
    ),
    (
        "Market",
        "ao1_class_imbalance_late_rate_by_market.svg",
        "AO1 Late-Delivery Rate by Market",
        True,
    ),
    (
        "order_month",
        "ao1_class_imbalance_late_rate_by_order_month.svg",
        "AO1 Late-Delivery Rate by Order Month",
        False,
    ),
]

for variable_name, file_name, title, sort_by_abs_diff in figure_specs:
    figure_rows = slice_df[slice_df["grouping_variable"] == variable_name].copy()
    if figure_rows.empty:
        continue
    figure_path = FIGURE_OUTPUT_DIR / file_name
    svg_rate_by_group(figure_rows, title, figure_path, sort_by_abs_diff=sort_by_abs_diff)
    if figure_path.exists():
        saved_figures.append(figure_path)

print("Saved focused SVG figures:")
for figure_path in saved_figures:
    print(f"- {figure_path}")


# COMMAND ----------

top_slice_patterns = (
    slice_df[slice_df["sample_size_flag"] == "meets_min_support"]
    .assign(abs_difference=lambda df: df["difference_from_overall_rate"].abs())
    .sort_values("abs_difference", ascending=False)
    .head(12)
)

print("")
print("Top supported slice differences from the overall late-delivery rate:")
for _, row in top_slice_patterns.iterrows():
    print(
        "- "
        f"{row['grouping_variable']} = {row['group_value']}: "
        f"{row['late_delivery_rate']:.2%} "
        f"({row['difference_from_overall_rate'] * 100:+.2f} pp, "
        f"n={int(row['row_count']):,})"
    )


def markdown_path(path: Path) -> str:
    """Format a repo-relative path for Markdown report notes."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def markdown_table(rows: list[dict[str, str]]) -> str:
    """Build a compact Markdown table from string dictionaries."""
    if not rows:
        return ""
    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(lines)


top_pattern_rows = []
for _, row in top_slice_patterns.head(8).iterrows():
    top_pattern_rows.append(
        {
            "Slice": f"`{row['grouping_variable']} = {row['group_value']}`",
            "Late-delivery rate": f"{float(row['late_delivery_rate']):.2%}",
            "Difference from overall": f"{float(row['difference_from_overall_rate']) * 100:+.2f} pp",
            "Rows": f"{int(row['row_count']):,}",
        }
    )

approved_grouping_rows = [
    {
        "Grouping field": f"`{grouping['grouping_variable']}`",
        "Analysis column": f"`{grouping['analysis_column']}`",
    }
    for grouping in approved_groupings
]

findings_note = f"""# AO1 Class Imbalance Analysis Findings

Issue: `[W3][P1][#4] Class imbalance analysis for AO1 #21`

## Purpose

This report note summarizes the focused AO1 class imbalance analysis for
`Late_delivery_risk`. It is intended for review and later report/modeling
design. It does not train AO1 models, finalize Gold tables, apply resampling,
or set operating thresholds.

Related artifacts:

- `{markdown_path(REPO_ROOT / "notebooks" / "eda" / "ao1_class_imbalance_analysis.py")}`
- `{markdown_path(REPO_ROOT / "docs" / "ao1_class_imbalance_analysis.md")}`
- `{markdown_path(OVERALL_OUTPUT_PATH)}`
- `{markdown_path(SLICE_OUTPUT_PATH)}`
- `{markdown_path(GROUP_REVIEW_OUTPUT_PATH)}`

## Dataset And Target Audit

The EDA used:

```text
{display_path_for_outputs(dataset_path)}
```

The loaded Silver clone contains {total_rows:,} rows and {loaded_column_count:,}
columns. The target is `{target_col}` and is binary in the current Silver clone.

| Class | Count | Rate |
| --- | ---: | ---: |
| Late = 1 | {late_count:,} | {late_rate:.2%} |
| Not late = 0 | {not_late_count:,} | {not_late_rate:.2%} |

Missing target rows: {missing_target_count:,}. Invalid non-binary target rows:
{invalid_target_count:,}. The majority-to-minority ratio is
{format_ratio(majority_minority_ratio)}, so the overall imbalance is
**{imbalance_severity}** and the positive late-delivery class is the
{positive_class_role} class.

## Leakage-Safe Grouping Review

Grouping fields were approved only when
`data/references/leakage_conceptual_screening.csv` marked them as AO1 `allowed`,
`candidate_feature`, not `needs_group_review`, and not `conditional_review`.

Approved grouping fields:

{markdown_table(approved_grouping_rows)}

Forbidden, dashboard-only, target, post-shipment, post-delivery, actual-duration,
shipping-date, profit-outcome, profit-proxy, conditional, and `needs_group_review`
fields were not used as approved grouping slices.

## Main Descriptive Findings

Overall class imbalance is mild. Accuracy alone should still not be the main
AO1 metric because missing high-risk orders has operational cost, but the full
Silver clone does not show an extreme rare-event target.

The largest supported slice differences are:

{markdown_table(top_pattern_rows)}

Planned service fields show the strongest descriptive differences. Market-level
late-delivery rates are close to the overall rate in this Silver clone. These
patterns are descriptive and should not be interpreted causally.

## Modeling Implications

AO1 should report recall, precision, F1, confusion matrix, AUC-ROC, and PR-AUC
if imbalance remains meaningful after chronological splitting. Threshold choice
should be evaluated later using validation data, not the final test set.

{NO_RESAMPLING_STATEMENT}

## Group Validation Needed

The group review list contains {len(group_review_df):,} conditional or
`needs_group_review` variables. The team should decide whether each can be used
for AO1 modeling design, descriptive EDA only, or should remain excluded before
AO1 preprocessing is locked.
"""

FINDINGS_OUTPUT_PATH.write_text(findings_note, encoding="utf-8")
print(f"Wrote findings note: {FINDINGS_OUTPUT_PATH}")


def arrow_safe_preview(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display-only copy that avoids mixed object columns in Databricks."""
    preview = df.copy()
    for column in preview.columns:
        if preview[column].dtype == "object" or pd.api.types.is_string_dtype(preview[column]):
            preview[column] = preview[column].astype("string").fillna("")
    return preview


def display_or_print_preview(df: pd.DataFrame) -> None:
    """Use Databricks display when available, otherwise print a text preview."""
    preview = arrow_safe_preview(df)
    try:
        display(preview)  # type: ignore[name-defined]
    except NameError:
        print(preview.to_string(index=False))
    except Exception as exc:
        print(f"Databricks display preview failed; printing text preview instead. Error: {exc}")
        print(preview.to_string(index=False))


display_or_print_preview(overall_df)
display_or_print_preview(slice_df.head(25))
display_or_print_preview(group_review_df.head(25))
