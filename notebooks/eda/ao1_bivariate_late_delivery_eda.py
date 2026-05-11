# Databricks notebook source
"""AO1 bivariate EDA for late-delivery correlates.

This notebook is intentionally narrow. It identifies descriptive bivariate
associations with Late_delivery_risk for pre-shipment/order-time candidate
features, while keeping leakage-sensitive, target, and dashboard-only fields
out of any recommended AO1 modeling list.
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
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


TARGET_COLUMN = "Late_delivery_risk"
MIN_SUPPORT_FRACTION = 0.005
MIN_SUPPORT_FLOOR = 100
MAX_DIRECT_CATEGORICAL_LEVELS = 75
REVIEW_SIGNAL_THRESHOLD = 0.03
DEFAULT_LOCAL_SILVER_CSV = "data/silver/dataco_orders_silver.csv"


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

SUMMARY_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_BIVARIATE_SUMMARY_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_late_delivery_bivariate_summary.csv"),
    )
)
DETAIL_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_BIVARIATE_DETAIL_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_late_delivery_bivariate_detail_by_group.csv"),
    )
)
GROUP_REVIEW_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO1_GROUP_REVIEW_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao1_late_delivery_group_validation_list.csv"),
    )
)
FIGURE_OUTPUT_DIR = Path(
    os.getenv(
        "DATACO_AO1_BIVARIATE_FIGURE_DIR",
        str(REPO_ROOT / "report" / "figures" / "eda"),
    )
)


for output_path in [
    SUMMARY_OUTPUT_PATH,
    DETAIL_OUTPUT_PATH,
    GROUP_REVIEW_OUTPUT_PATH,
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
    """Return the single approved local Silver CSV input path for this notebook."""
    configured_path = os.getenv("DATACO_AO1_EDA_INPUT_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return (REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV).resolve()


def validate_input_path(path: Path) -> None:
    """Fail fast when the notebook is pointed at raw or non-CSV data."""
    normalized_parts = {part.lower() for part in path.parts}
    if "raw" in normalized_parts or path.name == "DataCoSupplyChainDataset.csv":
        raise ValueError(
            "AO1 bivariate EDA must use a local Silver CSV clone, not raw data. "
            f"Expected {REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV}, or set "
            "DATACO_AO1_EDA_INPUT_PATH to another Silver CSV clone."
        )
    if path.suffix.lower() != ".csv":
        raise ValueError(
            "AO1 bivariate EDA expects a local Silver CSV clone. "
            f"Received non-CSV path: {path}"
        )


def load_input_dataset() -> tuple[pd.DataFrame, str, str]:
    """Load the local Silver CSV clone and return data, path, and read mode."""
    input_path = configured_input_path()
    validate_input_path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            "Local Silver CSV clone not found. Export or create the cleaned Silver table at "
            f"{REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV}, or set DATACO_AO1_EDA_INPUT_PATH "
            "to another Silver CSV clone. Do not point this notebook at data/raw."
        )

    return read_project_csv(input_path, low_memory=False), str(input_path), "local_silver_csv"


screening_df = read_project_csv(SCREENING_PATH)
availability_df = read_project_csv(AVAILABILITY_PATH)
orders_df, dataset_path, dataset_read_mode = load_input_dataset()

print(f"Loaded AO1 EDA dataset: {dataset_path}")
print(f"Read mode: {dataset_read_mode}")
print(f"Rows: {len(orders_df):,}; columns: {len(orders_df.columns):,}")


# COMMAND ----------

def canonicalize_column_name(column_name: str) -> str:
    """Match the Silver canonicalization rule used by src/data_engineering/clean_silver.py."""
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
    """Return possible data columns for raw and Silver naming conventions."""
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
    return pd.to_numeric(series, errors="coerce")


def normalize_token(series: pd.Series, remove_punctuation: bool = False) -> pd.Series:
    normalized = (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )
    if remove_punctuation:
        normalized = normalized.str.replace(r"[^a-z0-9_]", "", regex=True)
    return normalized.fillna("(missing)")


def derive_review_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive deterministic pre-shipment features used by the existing W2 feature specs."""
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

        featured["order_year"] = order_ts.dt.year.astype("Int64")
        featured["order_quarter"] = order_ts.dt.quarter.astype("Int64")
        featured["order_month"] = order_ts.dt.month.astype("Int64")
        featured["order_week_of_year"] = order_ts.dt.isocalendar().week.astype("Int64")
        featured["order_day_of_month"] = order_ts.dt.day.astype("Int64")
        featured["order_day_of_week"] = (((order_ts.dt.dayofweek + 1) % 7) + 1).astype("Int64")
        featured["order_hour"] = order_ts.dt.hour.astype("Int64")
        featured["order_is_weekend"] = order_ts.dt.dayofweek.isin([5, 6]).astype("Int64")
        featured["order_season"] = pd.cut(
            order_ts.dt.month,
            bins=[0, 2, 5, 8, 11, 12],
            labels=["winter", "spring", "summer", "fall", "winter"],
            ordered=False,
        ).astype("string")

    scheduled_col = first_available_column(
        featured,
        "Days for shipment (scheduled)",
        "Days_for_shipment_scheduled",
    )
    if scheduled_col:
        scheduled_days = as_numeric(featured[scheduled_col])
        featured["scheduled_shipping_days"] = scheduled_days
        featured["shipping_speed_tier"] = pd.Series("economy", index=featured.index, dtype="string")
        featured.loc[scheduled_days <= 3, "shipping_speed_tier"] = "standard"
        featured.loc[scheduled_days <= 1, "shipping_speed_tier"] = "expedited"
        featured.loc[scheduled_days.isna(), "shipping_speed_tier"] = pd.NA
        featured["is_same_day_or_next_day_shipping"] = (scheduled_days <= 1).astype("Int64")

    shipping_mode_col = first_available_column(featured, "Shipping Mode", "Shipping_Mode")
    if shipping_mode_col:
        shipping_mode = featured[shipping_mode_col].astype("string").str.strip()
        featured["shipping_mode_normalized"] = normalize_token(shipping_mode)
        featured["is_standard_shipping"] = (
            shipping_mode.str.lower() == "standard class"
        ).astype("Int64")

    category_id_col = first_available_column(featured, "Category Id", "Category_Id")
    category_name_col = first_available_column(featured, "Category Name", "Category_Name")
    if category_id_col and category_name_col:
        featured["product_category_key"] = (
            as_numeric(featured[category_id_col]).astype("Int64").astype("string")
            + "_"
            + normalize_token(featured[category_name_col], remove_punctuation=True)
        )

    department_id_col = first_available_column(featured, "Department Id", "Department_Id")
    department_name_col = first_available_column(featured, "Department Name", "Department_Name")
    if department_id_col and department_name_col:
        featured["product_department_key"] = (
            as_numeric(featured[department_id_col]).astype("Int64").astype("string")
            + "_"
            + normalize_token(featured[department_name_col], remove_punctuation=True)
        )

    product_card_col = first_available_column(featured, "Product Card Id", "Product_Card_Id")
    product_category_col = first_available_column(featured, "Product Category Id", "Product_Category_Id")
    item_card_col = first_available_column(featured, "Order Item Cardprod Id", "Order_Item_Cardprod_Id")
    if product_card_col and product_category_col and item_card_col:
        featured["product_catalog_key"] = (
            as_numeric(featured[product_card_col]).astype("Int64").astype("string")
            + "_"
            + as_numeric(featured[product_category_col]).astype("Int64").astype("string")
            + "_"
            + as_numeric(featured[item_card_col]).astype("Int64").astype("string")
        )

    product_name_col = first_available_column(featured, "Product Name", "Product_Name")
    if product_name_col:
        featured["product_name_normalized"] = normalize_token(
            featured[product_name_col],
            remove_punctuation=True,
        )

    source_to_engineered_numeric = {
        "Product Status": "product_status_flag",
        "Product Price": "product_list_price",
        "Order Item Quantity": "order_item_quantity",
        "Order Item Product Price": "item_unit_price",
        "Order Item Discount": "item_discount_amount",
        "Order Item Discount Rate": "item_discount_rate",
        "Order Item Total": "item_net_sales_amount",
    }
    for source_name, feature_name in source_to_engineered_numeric.items():
        source_col = first_available_column(featured, source_name, canonicalize_column_name(source_name))
        if source_col:
            featured[feature_name] = as_numeric(featured[source_col])

    if "item_unit_price" in featured.columns and "order_item_quantity" in featured.columns:
        featured["item_gross_sales_estimate"] = (
            featured["item_unit_price"] * featured["order_item_quantity"]
        ).round(2)

    if "item_discount_amount" in featured.columns and "item_gross_sales_estimate" in featured.columns:
        gross = featured["item_gross_sales_estimate"].replace(0, pd.NA)
        featured["item_discount_share_of_gross"] = (featured["item_discount_amount"] / gross).clip(
            lower=0,
            upper=1,
        )

    normalized_text_features = {
        "Customer Segment": "customer_segment_normalized",
        "Customer Country": "customer_country_normalized",
        "Customer State": "customer_state_normalized",
        "Customer City": "customer_city_normalized",
        "Market": "market_normalized",
        "Order Country": "order_country_normalized",
        "Order Region": "order_region_normalized",
        "Order State": "order_state_normalized",
        "Order City": "order_city_normalized",
    }
    for source_name, feature_name in normalized_text_features.items():
        source_col = first_available_column(featured, source_name, canonicalize_column_name(source_name))
        if source_col:
            featured[feature_name] = normalize_token(featured[source_col], remove_punctuation=True)

    customer_zip_col = first_available_column(featured, "Customer Zipcode", "Customer_Zipcode")
    if customer_zip_col:
        featured["customer_zipcode_available"] = featured[customer_zip_col].notna().astype("Int64")

    order_zip_col = first_available_column(featured, "Order Zipcode", "Order_Zipcode")
    if order_zip_col:
        featured["order_zipcode_available"] = featured[order_zip_col].notna().astype("Int64")

    if {"customer_country_normalized", "customer_state_normalized", "customer_city_normalized"}.issubset(
        featured.columns
    ):
        featured["customer_region_key"] = (
            featured["customer_country_normalized"].astype("string")
            + "_"
            + featured["customer_state_normalized"].astype("string")
            + "_"
            + featured["customer_city_normalized"].astype("string")
        )

    if {
        "order_country_normalized",
        "order_region_normalized",
        "order_state_normalized",
        "order_city_normalized",
    }.issubset(featured.columns):
        featured["order_region_key"] = (
            featured["order_country_normalized"].astype("string")
            + "_"
            + featured["order_region_normalized"].astype("string")
            + "_"
            + featured["order_state_normalized"].astype("string")
            + "_"
            + featured["order_city_normalized"].astype("string")
        )

    if {"customer_country_normalized", "order_country_normalized"}.issubset(featured.columns):
        featured["customer_order_country_match"] = (
            featured["customer_country_normalized"] == featured["order_country_normalized"]
        ).astype("Int64")

    if {"customer_state_normalized", "order_state_normalized"}.issubset(featured.columns):
        featured["customer_order_state_match"] = (
            featured["customer_state_normalized"] == featured["order_state_normalized"]
        ).astype("Int64")

    latitude_col = first_available_column(featured, "Latitude")
    longitude_col = first_available_column(featured, "Longitude")
    if latitude_col:
        featured["latitude_rounded"] = as_numeric(featured[latitude_col]).round(2)
    if longitude_col:
        featured["longitude_rounded"] = as_numeric(featured[longitude_col]).round(2)
    if latitude_col and longitude_col:
        featured["geo_coordinates_available"] = (
            as_numeric(featured[latitude_col]).notna() & as_numeric(featured[longitude_col]).notna()
        ).astype("Int64")

    return featured


orders_df = derive_review_features(orders_df)
target_col = resolve_column(orders_df, TARGET_COLUMN)
if target_col is None:
    raise ValueError(f"Target column {TARGET_COLUMN} was not found in the loaded dataset.")

orders_df[target_col] = as_numeric(orders_df[target_col])
orders_df = orders_df[orders_df[target_col].isin([0, 1])].copy()

overall_late_rate = float(orders_df[target_col].mean())
min_support_count = max(MIN_SUPPORT_FLOOR, math.ceil(len(orders_df) * MIN_SUPPORT_FRACTION))

print(f"Valid AO1 target rows: {len(orders_df):,}")
print(f"Overall late-delivery rate: {overall_late_rate:.2%}")
print(f"Minimum support threshold for ranked category/bin signals: {min_support_count:,} rows")


# COMMAND ----------

def classify_policy(row: pd.Series) -> tuple[str, bool, str, str]:
    """Return recommendation, group-validation flag, decision-time status, and review result."""
    ao1_policy = str(row["ao1_policy"])
    screening_status = str(row["screening_status"])
    modeling_policy = str(row["modeling_policy"])
    availability = str(row["decision_time_availability"])

    requires_group_validation = (
        ao1_policy == "conditional"
        or screening_status == "needs_group_review"
        or "conditional" in modeling_policy
    )

    if ao1_policy == "target":
        return (
            "exclude_from_ao1_modeling",
            False,
            "target_only",
            "AO1 target field; never a predictor.",
        )

    if ao1_policy == "forbidden":
        if modeling_policy == "dashboard_only":
            return (
                "dashboard_only",
                False,
                "no",
                "Excluded from AO1 modeling because it is an outcome, post-event field, or target proxy.",
            )
        return (
            "exclude_from_ao1_modeling",
            False,
            "no",
            "Excluded from AO1 modeling by leakage screening.",
        )

    if ao1_policy == "not_applicable":
        return (
            "descriptive_context_only",
            False,
            "not_applicable",
            "Processing metadata or non-business field; not a modeling predictor.",
        )

    if requires_group_validation:
        return (
            "conditional_requires_group_review",
            True,
            "requires_group_review",
            "Decision-time plausible but not approved for AO1 modeling without group validation.",
        )

    if ao1_policy == "allowed" and modeling_policy == "candidate_feature":
        return (
            "candidate_for_gold_review",
            False,
            "yes",
            "AO1 allowed by conceptual screening; still subject to Gold/modeling review.",
        )

    return (
        "descriptive_context_only",
        requires_group_validation,
        availability,
        "Not recommended as a direct AO1 predictor by the current screening policy.",
    )


def infer_variable_type(df: pd.DataFrame, column_name: str | None) -> str:
    if column_name is None:
        return "unavailable"
    series = df[column_name]
    non_missing = series.dropna()
    if non_missing.empty:
        return "unknown"
    if is_datetime64_any_dtype(non_missing):
        return "datetime"
    numeric_values = pd.to_numeric(non_missing, errors="coerce")
    numeric_share = numeric_values.notna().mean()
    if is_numeric_dtype(non_missing) or numeric_share >= 0.95:
        distinct_count = int(numeric_values.nunique(dropna=True))
        if distinct_count <= 2:
            return "binary"
        if distinct_count <= 30 and variable_looks_discrete(column_name):
            return "categorical"
        return "numeric"
    return "categorical"


def variable_looks_discrete(variable_name: str | None) -> bool:
    if not variable_name:
        return False
    lower_name = variable_name.lower()
    return any(
        token in lower_name
        for token in [
            "year",
            "quarter",
            "month",
            "week",
            "day",
            "hour",
            "status",
            "quantity",
            "scheduled",
            "zipcode_available",
            "_match",
            "_flag",
            "is_",
        ]
    )


def direct_bivariate_is_inappropriate(variable_name: str) -> tuple[bool, str]:
    """Identify fields where direct bivariate ranking would be misleading."""
    lower_name = variable_name.lower()
    identifier_tokens = [
        "customer id",
        "order customer id",
        "order item cardprod id",
        "product card id",
        "product_catalog_key",
    ]
    if any(token in lower_name for token in identifier_tokens):
        return (
            True,
            "Identifier/key field; do not interpret direct category or numeric bins as AO1 signal.",
        )
    if "zipcode" in lower_name and "zipcode_available" not in lower_name:
        return (
            True,
            "Raw postal code is granular geography; use availability flags or approved coarse grouping instead.",
        )
    return False, ""


def format_rate(rate: float | None) -> str:
    if rate is None or pd.isna(rate):
        return "not available"
    return f"{rate:.2%}"


def format_pp(diff: float | None) -> str:
    if diff is None or pd.isna(diff):
        return "not available"
    return f"{diff * 100:+.2f} pp"


def categorical_bivariate(
    df: pd.DataFrame,
    variable_name: str,
    column_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    values = (
        df[column_name]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
        .fillna("(missing)")
    )
    grouped = (
        pd.DataFrame({"level": values, "target": df[target_col]})
        .groupby("level", dropna=False)["target"]
        .agg(["count", "mean"])
        .reset_index()
        .rename(columns={"mean": "late_delivery_rate"})
    )
    grouped["late_delivery_rate_difference"] = grouped["late_delivery_rate"] - overall_late_rate
    grouped["supported"] = grouped["count"] >= min_support_count
    grouped["abs_difference"] = grouped["late_delivery_rate_difference"].abs()

    distinct_count = int(grouped.shape[0])
    if distinct_count > MAX_DIRECT_CATEGORICAL_LEVELS:
        return (
            {
                "eda_summary": (
                    f"Skipped direct category ranking: {distinct_count} distinct values exceeds "
                    f"the focused EDA limit of {MAX_DIRECT_CATEGORICAL_LEVELS}."
                ),
                "notable_pattern": "High-cardinality field; review grouping before modeling.",
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": (
                    f"High-cardinality direct use not reviewed; minimum support was {min_support_count:,}."
                ),
            },
            [],
        )

    supported = grouped[grouped["supported"]].copy()
    unsupported_count = int((~grouped["supported"]).sum())
    if supported.empty:
        return (
            {
                "eda_summary": (
                    f"Categorical field with {distinct_count} groups, but no group met the "
                    f"{min_support_count:,}-row support threshold."
                ),
                "notable_pattern": "No support-safe categorical signal identified.",
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": f"{unsupported_count} groups below minimum support.",
            },
            [],
        )

    ranked = supported.sort_values("abs_difference", ascending=False)
    strongest = ranked.iloc[0]
    highest = supported.sort_values("late_delivery_rate", ascending=False).iloc[0]
    lowest = supported.sort_values("late_delivery_rate", ascending=True).iloc[0]

    summary = {
        "eda_summary": (
            f"Categorical: {distinct_count} groups; {len(supported)} met support. "
            f"Strongest supported group '{strongest['level']}' had late rate "
            f"{format_rate(float(strongest['late_delivery_rate']))} "
            f"({format_pp(float(strongest['late_delivery_rate_difference']))} vs overall)."
        ),
        "notable_pattern": (
            f"Highest supported rate: '{highest['level']}' {format_rate(float(highest['late_delivery_rate']))}; "
            f"lowest: '{lowest['level']}' {format_rate(float(lowest['late_delivery_rate']))}."
        ),
        "late_delivery_rate_difference": round(float(strongest["late_delivery_rate_difference"]), 4),
        "sample_size_caveat": (
            f"Minimum support {min_support_count:,}; {unsupported_count} groups below threshold."
        ),
    }

    detail_rows = []
    for _, detail in ranked.head(15).iterrows():
        detail_rows.append(
            {
                "variable_name": variable_name,
                "level_or_bin": str(detail["level"]),
                "count": int(detail["count"]),
                "late_delivery_rate": round(float(detail["late_delivery_rate"]), 6),
                "late_delivery_rate_difference": round(
                    float(detail["late_delivery_rate_difference"]),
                    6,
                ),
                "supported": bool(detail["supported"]),
            }
        )
    return summary, detail_rows


def numeric_bivariate(
    df: pd.DataFrame,
    variable_name: str,
    column_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    values = as_numeric(df[column_name])
    missing_rate = float(values.isna().mean())
    valid = pd.DataFrame({"value": values, "target": df[target_col]}).dropna()

    if valid.empty or valid["value"].nunique() <= 1:
        return (
            {
                "eda_summary": "Numeric field has too few non-missing or distinct values for EDA.",
                "notable_pattern": "No numeric signal identified.",
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": f"Missing rate {format_rate(missing_rate)}.",
            },
            [],
        )

    by_target = valid.groupby("target")["value"].agg(["count", "mean", "median"]).to_dict("index")
    bin_count = min(5, int(valid["value"].nunique()))
    try:
        valid["bin"] = pd.qcut(valid["value"], q=bin_count, duplicates="drop")
    except ValueError:
        valid["bin"] = pd.cut(valid["value"], bins=bin_count, duplicates="drop")

    grouped = (
        valid.groupby("bin", observed=True)["target"]
        .agg(["count", "mean"])
        .reset_index()
        .rename(columns={"mean": "late_delivery_rate"})
    )
    grouped["level_or_bin"] = grouped["bin"].astype("string")
    grouped["supported"] = grouped["count"] >= min_support_count
    grouped = grouped[grouped["supported"]].copy()

    if grouped.empty:
        return (
            {
                "eda_summary": (
                    f"Numeric field binned into {bin_count} groups, but no bin met "
                    f"the {min_support_count:,}-row support threshold."
                ),
                "notable_pattern": "No support-safe numeric bin signal identified.",
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": f"Missing rate {format_rate(missing_rate)}.",
            },
            [],
        )

    highest = grouped.sort_values("late_delivery_rate", ascending=False).iloc[0]
    lowest = grouped.sort_values("late_delivery_rate", ascending=True).iloc[0]
    range_difference = float(highest["late_delivery_rate"] - lowest["late_delivery_rate"])

    target_zero = by_target.get(0.0, by_target.get(0, {}))
    target_one = by_target.get(1.0, by_target.get(1, {}))
    summary = {
        "eda_summary": (
            "Numeric: "
            f"late class median {target_one.get('median', pd.NA):.3f}; "
            f"on-time class median {target_zero.get('median', pd.NA):.3f}; "
            f"missing rate {format_rate(missing_rate)}."
        ),
        "notable_pattern": (
            f"Highest supported bin {highest['level_or_bin']} had late rate "
            f"{format_rate(float(highest['late_delivery_rate']))}; lowest bin "
            f"{lowest['level_or_bin']} had {format_rate(float(lowest['late_delivery_rate']))}."
        ),
        "late_delivery_rate_difference": round(range_difference, 4),
        "sample_size_caveat": (
            f"Minimum support {min_support_count:,}; missing rate {format_rate(missing_rate)}."
        ),
    }

    detail_rows = []
    for _, detail in grouped.sort_values("late_delivery_rate", ascending=False).iterrows():
        detail_rows.append(
            {
                "variable_name": variable_name,
                "level_or_bin": str(detail["level_or_bin"]),
                "count": int(detail["count"]),
                "late_delivery_rate": round(float(detail["late_delivery_rate"]), 6),
                "late_delivery_rate_difference": round(
                    float(detail["late_delivery_rate"] - overall_late_rate),
                    6,
                ),
                "supported": True,
            }
        )
    return summary, detail_rows


DIRECT_TIMESTAMP_VARIABLES = {"order date (DateOrders)", "order_date_DateOrders"}


def bivariate_for_variable(
    df: pd.DataFrame,
    variable_name: str,
    column_name: str | None,
    variable_type: str,
    recommendation: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if recommendation in {"exclude_from_ao1_modeling", "dashboard_only", "descriptive_context_only"}:
        return (
            {
                "eda_summary": "Not analyzed as an AO1 candidate under the current leakage policy.",
                "notable_pattern": "Excluded from candidate modeling review.",
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": "Not applicable.",
            },
            [],
        )

    if column_name is None:
        return (
            {
                "eda_summary": "Column not present in the loaded dataset/table.",
                "notable_pattern": "No EDA produced for unavailable field.",
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": "Unavailable in input dataset.",
            },
            [],
        )

    skip_direct, skip_reason = direct_bivariate_is_inappropriate(variable_name)
    if skip_direct:
        return (
            {
                "eda_summary": "Direct bivariate ranking skipped for this review-sensitive field.",
                "notable_pattern": skip_reason,
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": "Requires approved grouping or train-only aggregate design before modeling.",
            },
            [],
        )

    if variable_name in DIRECT_TIMESTAMP_VARIABLES:
        return (
            {
                "eda_summary": "Raw order timestamp retained for chronological split and derived calendar features.",
                "notable_pattern": "Use derived order-time features, not the raw timestamp, for modeling review.",
                "late_delivery_rate_difference": pd.NA,
                "sample_size_caveat": "Direct timestamp modeling requires explicit group review.",
            },
            [],
        )

    if variable_type in {"numeric"}:
        return numeric_bivariate(df, variable_name, column_name)
    return categorical_bivariate(df, variable_name, column_name)


# COMMAND ----------

summary_rows: list[dict[str, Any]] = []
detail_rows: list[dict[str, Any]] = []

for _, screen_row in screening_df.iterrows():
    variable_name = str(screen_row["variable_name"])
    recommendation, requires_group_validation, decision_time_valid, leakage_review_result = (
        classify_policy(screen_row)
    )
    resolved_column = resolve_column(orders_df, variable_name)
    variable_type = infer_variable_type(orders_df, resolved_column)
    eda_result, details = bivariate_for_variable(
        orders_df,
        variable_name,
        resolved_column,
        variable_type,
        recommendation,
    )
    detail_rows.extend(details)

    if recommendation == "candidate_for_gold_review":
        recommended_action = "Keep as an AO1 candidate for Gold feature review; do not treat EDA as causal."
    elif recommendation == "conditional_requires_group_review":
        recommended_action = "Keep in the group-validation list; do not approve for AO1 modeling yet."
    elif recommendation == "dashboard_only":
        recommended_action = "Use only for descriptive dashboard, target audit, or governance context."
    elif recommendation == "exclude_from_ao1_modeling":
        recommended_action = "Exclude from AO1 predictor lists."
    else:
        recommended_action = "Use only as descriptive context unless policy changes."

    summary_rows.append(
        {
            "variable_name": variable_name,
            "analysis_column": resolved_column or "",
            "variable_origin": screen_row["variable_origin"],
            "variable_type": variable_type,
            "ao1_policy": screen_row["ao1_policy"],
            "screening_status": screen_row["screening_status"],
            "decision_time_valid": decision_time_valid,
            "eda_summary": eda_result["eda_summary"],
            "notable_pattern": eda_result["notable_pattern"],
            "late_delivery_rate_difference": eda_result["late_delivery_rate_difference"],
            "sample_size_caveat": eda_result["sample_size_caveat"],
            "leakage_review_result": leakage_review_result,
            "modeling_recommendation": recommendation,
            "requires_group_validation": requires_group_validation,
            "recommended_action": recommended_action,
            "source_rationale": screen_row["rationale"],
            "required_action_from_screening": screen_row["required_action"],
        }
    )


summary_df = pd.DataFrame(summary_rows)
detail_df = pd.DataFrame(detail_rows)

summary_df.to_csv(SUMMARY_OUTPUT_PATH, index=False)
detail_df.to_csv(DETAIL_OUTPUT_PATH, index=False)

print(f"Wrote summary table: {SUMMARY_OUTPUT_PATH}")
print(f"Wrote detail table: {DETAIL_OUTPUT_PATH}")


# COMMAND ----------

def validation_reason(row: pd.Series) -> str:
    lower_name = row["variable_name"].lower()
    rationale = row["source_rationale"]
    if "id" in lower_name or "key" in lower_name or "catalog" in lower_name:
        return "Potential high-cardinality identifier or key; direct modeling use needs grouping or train-only aggregate approval."
    if any(token in lower_name for token in ["sales", "price", "discount", "total", "quantity"]):
        return "Commercial/order-value field; confirm order-time semantics and redundancy before modeling."
    if "dateorders" in lower_name or row["variable_name"] == "order date (DateOrders)":
        return "Raw timestamp should be replaced by approved derived calendar features for modeling review."
    if any(token in lower_name for token in ["city", "zipcode", "latitude", "longitude", "region_key"]):
        return "Granular geography may be high-cardinality, unstable, or privacy-sensitive."
    if "status" in lower_name:
        return "Status semantics need confirmation so no post-order state is encoded."
    return str(rationale)


review_candidates = summary_df[summary_df["requires_group_validation"]].copy()

review_candidates["why_it_may_be_useful"] = review_candidates["notable_pattern"]
review_candidates["why_requires_validation"] = review_candidates.apply(validation_reason, axis=1)
review_candidates["validation_priority"] = (
    pd.to_numeric(review_candidates["late_delivery_rate_difference"], errors="coerce")
    .abs()
    .fillna(0)
    .ge(REVIEW_SIGNAL_THRESHOLD)
    .map({True: "higher_signal_review", False: "standard_policy_review"})
)
review_candidates["proposed_decision"] = review_candidates["variable_name"].apply(
    lambda name: "use_derived_calendar_features_only"
    if name == "order date (DateOrders)"
    else "defer_pending_group_validation"
)

group_review_columns = [
    "variable_name",
    "variable_origin",
    "variable_type",
    "ao1_policy",
    "screening_status",
    "observed_eda_pattern",
    "why_it_may_be_useful",
    "why_requires_validation",
    "validation_priority",
    "proposed_decision",
    "recommended_action",
]

if review_candidates.empty:
    group_review_df = pd.DataFrame(columns=group_review_columns)
else:
    group_review_df = review_candidates.rename(
        columns={"notable_pattern": "observed_eda_pattern"}
    )[group_review_columns]

group_review_df.to_csv(GROUP_REVIEW_OUTPUT_PATH, index=False)

print(f"Wrote group-validation list: {GROUP_REVIEW_OUTPUT_PATH}")
print(f"Group-review variables listed: {len(group_review_df):,}")


# COMMAND ----------

def svg_bar_chart(
    rows: pd.DataFrame,
    title: str,
    output_path: Path,
    label_column: str = "level_or_bin",
    value_column: str = "late_delivery_rate",
    max_rows: int = 10,
) -> None:
    """Write a lightweight SVG horizontal bar chart without external plotting deps."""
    plot_rows = rows.head(max_rows).copy()
    if plot_rows.empty:
        return

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
        label = str(row[label_column])
        count = int(row.get("count", 0))
        rate = float(row[value_column])
        diff = float(row.get("late_delivery_rate_difference", rate - overall_late_rate))
        length = max(2, int(bar_width * min(max(rate, 0.0), 1.0)))
        parts.extend(
            [
                f'<text x="20" y="{y + 18}" font-family="Arial, sans-serif" font-size="13">{html.escape(label[:42])}</text>',
                f'<rect x="{left}" y="{y}" width="{length}" height="22" rx="2" fill="#2f6f73"/>',
                f'<text x="{left + length + 8}" y="{y + 16}" font-family="Arial, sans-serif" font-size="12">{rate:.1%} ({diff * 100:+.1f} pp, n={count:,})</text>',
            ]
        )

    overall_x = left + int(bar_width * overall_late_rate)
    parts.extend(
        [
            f'<line x1="{overall_x}" x2="{overall_x}" y1="{top - 6}" y2="{height - 24}" stroke="#b33" stroke-width="2" stroke-dasharray="5,4"/>',
            f'<text x="{overall_x + 6}" y="{height - 12}" font-family="Arial, sans-serif" font-size="12" fill="#b33">overall {overall_late_rate:.1%}</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(parts), encoding="utf-8")


figure_specs = [
    ("Shipping Mode", "late_delivery_rate_by_shipping_mode.svg", "Late-delivery Rate by Shipping Mode"),
    ("order_month", "late_delivery_rate_by_order_month.svg", "Late-delivery Rate by Order Month"),
    ("Market", "late_delivery_rate_by_market.svg", "Late-delivery Rate by Market"),
    ("Category Name", "late_delivery_rate_by_category_name.svg", "Late-delivery Rate by Product Category"),
]

saved_figures: list[str] = []
for variable_name, file_name, title in figure_specs:
    figure_rows = detail_df[detail_df["variable_name"] == variable_name].copy()
    if figure_rows.empty:
        continue
    if variable_name == "order_month":
        figure_rows["_sort"] = pd.to_numeric(figure_rows["level_or_bin"], errors="coerce")
        figure_rows = figure_rows.sort_values("_sort")
    else:
        figure_rows = figure_rows.sort_values(
            "late_delivery_rate_difference",
            key=lambda value: value.abs(),
            ascending=False,
        )
    figure_path = FIGURE_OUTPUT_DIR / file_name
    svg_bar_chart(figure_rows, title, figure_path)
    saved_figures.append(str(figure_path))

print("Saved lightweight SVG figures:")
for figure_path in saved_figures:
    print(f"- {figure_path}")


# COMMAND ----------

recommended_candidates = summary_df[
    summary_df["modeling_recommendation"] == "candidate_for_gold_review"
].copy()
review_only_candidates = summary_df[
    summary_df["modeling_recommendation"] == "conditional_requires_group_review"
].copy()
excluded_variables = summary_df[
    summary_df["modeling_recommendation"].isin(["exclude_from_ao1_modeling", "dashboard_only"])
].copy()

top_supported_patterns = recommended_candidates.copy()
top_supported_patterns["_abs_diff"] = (
    pd.to_numeric(top_supported_patterns["late_delivery_rate_difference"], errors="coerce")
    .abs()
    .fillna(0)
)
top_supported_patterns = top_supported_patterns.sort_values("_abs_diff", ascending=False).head(12)

print("AO1-safe recommended candidate variables reviewed:", len(recommended_candidates))
print("Conditional or needs_group_review variables reviewed:", len(review_only_candidates))
print("Excluded/dashboard-only variables documented:", len(excluded_variables))
print("")
print("Top support-safe recommended candidate patterns:")
for _, row in top_supported_patterns.iterrows():
    diff = row["late_delivery_rate_difference"]
    diff_text = "n/a" if pd.isna(diff) else format_pp(float(diff))
    print(f"- {row['variable_name']}: {diff_text}; {row['notable_pattern']}")


# COMMAND ----------

try:
    display(summary_df.head(25))  # type: ignore[name-defined]
except NameError:
    print(summary_df.head(25).to_string(index=False))
