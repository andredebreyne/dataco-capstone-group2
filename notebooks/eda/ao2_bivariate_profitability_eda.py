# Databricks notebook source
"""AO2 bivariate EDA for order profitability drivers.

This notebook is intentionally narrow. It identifies descriptive bivariate
associations with order-level profitability using the local Silver clone while
keeping AO2 target, profit-proxy, post-shipment, post-delivery, and
target-reconstruction-risk fields out of any approved modeling list.
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


PRIMARY_TARGET_SOURCE = "Order Profit Per Order"
PRIMARY_TARGET_SILVER = "Order_Profit_Per_Order"
FALLBACK_TARGET_SOURCE = "Benefit per order"
FALLBACK_TARGET_SILVER = "Benefit_per_order"
PROFIT_RATIO_SOURCE = "Order Item Profit Ratio"
PROFIT_RATIO_SILVER = "Order_Item_Profit_Ratio"

MIN_SUPPORT_FRACTION = 0.005
MIN_SUPPORT_FLOOR = 100
MAX_DIRECT_CATEGORICAL_LEVELS = 75
REVIEW_SIGNAL_THRESHOLD = 10.0
DEFAULT_LOCAL_SILVER_CSV = "data/silver/dataco_orders_silver.csv"

COMMERCIAL_REVIEW_TOKENS = (
    "sales",
    "discount",
    "price",
    "total",
    "quantity",
    "value",
    "gross",
    "net_sales",
    "amount",
)
PROFIT_PROXY_TOKENS = ("profit", "benefit", "margin")
POST_OUTCOME_TOKENS = (
    "delivery",
    "shipping_real",
    "days_for_shipping_real",
    "shipping_date",
    "order_status",
)


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
        "DATACO_AO2_BIVARIATE_SUMMARY_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_profitability_bivariate_summary.csv"),
    )
)
DETAIL_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO2_BIVARIATE_DETAIL_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_profitability_bivariate_detail_by_group.csv"),
    )
)
GROUP_REVIEW_OUTPUT_PATH = Path(
    os.getenv(
        "DATACO_AO2_GROUP_REVIEW_OUTPUT_PATH",
        str(REPO_ROOT / "report" / "tables" / "ao2_profitability_group_validation_list.csv"),
    )
)
FIGURE_OUTPUT_DIR = Path(
    os.getenv(
        "DATACO_AO2_BIVARIATE_FIGURE_DIR",
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
    configured_path = os.getenv("DATACO_AO2_EDA_INPUT_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return (REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV).resolve()


def validate_input_path(path: Path) -> None:
    """Fail fast when the notebook is pointed at raw or non-Silver data."""
    normalized_parts = {part.lower() for part in path.parts}
    lower_name = path.name.lower()
    if "raw" in normalized_parts or lower_name == "datacosupplychaindataset.csv":
        raise ValueError(
            "AO2 bivariate EDA must use a local Silver CSV clone, not raw data. "
            f"Expected {REPO_ROOT / DEFAULT_LOCAL_SILVER_CSV}, or set "
            "DATACO_AO2_EDA_INPUT_PATH to another Silver CSV clone."
        )
    if path.suffix.lower() != ".csv":
        raise ValueError(
            "AO2 bivariate EDA expects a local Silver CSV clone. "
            f"Received non-CSV path: {path}"
        )
    if "silver" not in normalized_parts and "silver" not in lower_name:
        raise ValueError(
            "DATACO_AO2_EDA_INPUT_PATH must point to another Silver CSV clone. "
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
            "notebooks/pipeline/run_medallion_pipeline.py. Do not point this notebook "
            "at data/raw or duplicate Silver cleaning logic inside the EDA notebook."
        )

    return read_project_csv(input_path, low_memory=False), str(input_path), "local_silver_csv"


screening_df = read_project_csv(SCREENING_PATH)
availability_df = read_project_csv(AVAILABILITY_PATH)
orders_df, dataset_path, dataset_read_mode = load_input_dataset()

print(f"Loaded AO2 EDA dataset: {dataset_path}")
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
    """Return possible data columns for raw, Silver, and engineered naming conventions."""
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
    """Convert a series to numeric values with invalid parsing set to missing."""
    return pd.to_numeric(series, errors="coerce")


def normalize_token(series: pd.Series, remove_punctuation: bool = False) -> pd.Series:
    """Create stable lower-case tokens for descriptive grouping."""
    normalized = (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )
    if remove_punctuation:
        normalized = normalized.str.replace(r"[^a-z0-9_]", "", regex=True)
    return normalized.fillna("(missing)")


def season_from_month(month: int | float | None) -> str | pd.NA:
    """Map month number to an interpretable calendar season."""
    if pd.isna(month):
        return pd.NA
    month_int = int(month)
    if month_int in {12, 1, 2}:
        return "winter"
    if month_int in {3, 4, 5}:
        return "spring"
    if month_int in {6, 7, 8}:
        return "summer"
    return "fall"


def derive_review_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive deterministic review features already described in W2 feature docs."""
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
        featured["order_season"] = order_ts.dt.month.map(season_from_month).astype("string")

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


# COMMAND ----------

def resolve_target_column(df: pd.DataFrame) -> tuple[str, str, bool]:
    """Resolve the AO2 target, using Benefit only as an explicit flagged fallback."""
    primary_col = first_available_column(df, PRIMARY_TARGET_SOURCE, PRIMARY_TARGET_SILVER)
    if primary_col:
        return primary_col, PRIMARY_TARGET_SOURCE, False

    fallback_col = first_available_column(df, FALLBACK_TARGET_SOURCE, FALLBACK_TARGET_SILVER)
    if fallback_col:
        print(
            "WARNING: Order_Profit_Per_Order was not found. Using Benefit_per_order as an "
            "explicit fallback target for audit only; this requires group review before modeling."
        )
        return fallback_col, FALLBACK_TARGET_SOURCE, True

    raise ValueError(
        "AO2 target not found. Expected Order_Profit_Per_Order in the Silver clone. "
        "Benefit_per_order was also unavailable, so this notebook cannot run."
    )


target_col, target_source_name, target_fallback_used = resolve_target_column(orders_df)
raw_target_values = as_numeric(orders_df[target_col])
target_missing_count = int(raw_target_values.isna().sum())
target_missing_rate = float(raw_target_values.isna().mean())
orders_df[target_col] = raw_target_values
orders_df = orders_df[orders_df[target_col].notna()].copy()
target_series = orders_df[target_col]

overall_mean_profit = float(target_series.mean())
overall_median_profit = float(target_series.median())
target_std_profit = float(target_series.std())
target_min_profit = float(target_series.min())
target_max_profit = float(target_series.max())
min_support_count = max(MIN_SUPPORT_FLOOR, math.ceil(len(orders_df) * MIN_SUPPORT_FRACTION))

benefit_col = first_available_column(orders_df, FALLBACK_TARGET_SOURCE, FALLBACK_TARGET_SILVER)
profit_ratio_col = first_available_column(orders_df, PROFIT_RATIO_SOURCE, PROFIT_RATIO_SILVER)

target_percentiles = target_series.quantile([0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
q1 = float(target_percentiles.loc[0.25])
q3 = float(target_percentiles.loc[0.75])
iqr = q3 - q1
lower_fence = q1 - 1.5 * iqr
upper_fence = q3 + 1.5 * iqr
outlier_count = int(((target_series < lower_fence) | (target_series > upper_fence)).sum())
target_skewness = float(target_series.skew())

benefit_audit = "Benefit_per_order column not present."
if benefit_col:
    benefit_values = as_numeric(orders_df[benefit_col])
    comparable = pd.DataFrame({"target": target_series, "benefit": benefit_values}).dropna()
    if not comparable.empty:
        diff = comparable["target"] - comparable["benefit"]
        exact_match_rate = float((diff.abs() <= 1e-9).mean())
        max_abs_diff = float(diff.abs().max())
        benefit_audit = (
            f"{benefit_col} compared with {target_col}: exact match rate "
            f"{exact_match_rate:.2%}; max absolute difference {max_abs_diff:.6f}."
        )

profit_ratio_audit = (
    f"{profit_ratio_col} exists and is excluded from predictors as a realized profit ratio."
    if profit_ratio_col
    else "Order_Item_Profit_Ratio column not present."
)

print(f"AO2 target column: {target_col}")
print(f"AO2 target source label: {target_source_name}")
print(f"Target fallback used: {target_fallback_used}")
print(f"Valid AO2 target rows: {len(orders_df):,}")
print(f"AO2 target missing rows before filtering: {target_missing_count:,} ({target_missing_rate:.2%})")
print(f"Overall mean profit: {overall_mean_profit:.2f}")
print(f"Overall median profit: {overall_median_profit:.2f}")
print(f"Target standard deviation: {target_std_profit:.2f}")
print(f"Target min/max: {target_min_profit:.2f} / {target_max_profit:.2f}")
print(
    "Target percentiles: "
    + "; ".join(
        f"p{int(percentile * 100):02d}={value:.2f}"
        for percentile, value in target_percentiles.items()
    )
)
print(f"Target skewness: {target_skewness:.3f}; IQR outlier count: {outlier_count:,}")
print(benefit_audit)
print(profit_ratio_audit)
print(f"Minimum support threshold for ranked category/bin signals: {min_support_count:,} rows")


# COMMAND ----------

def normalized_name(variable_name: str) -> str:
    return canonicalize_column_name(variable_name).lower()


def is_commercial_field(variable_name: str) -> bool:
    lower_name = normalized_name(variable_name)
    return any(token in lower_name for token in COMMERCIAL_REVIEW_TOKENS)


def is_profit_proxy_field(variable_name: str) -> bool:
    lower_name = normalized_name(variable_name)
    if lower_name in {
        normalized_name(PRIMARY_TARGET_SOURCE),
        normalized_name(PRIMARY_TARGET_SILVER),
        normalized_name(FALLBACK_TARGET_SOURCE),
        normalized_name(FALLBACK_TARGET_SILVER),
        normalized_name(PROFIT_RATIO_SOURCE),
        normalized_name(PROFIT_RATIO_SILVER),
    }:
        return True
    return any(token in lower_name for token in PROFIT_PROXY_TOKENS)


def is_post_outcome_field(variable_name: str, availability: str) -> bool:
    lower_name = normalized_name(variable_name)
    lower_availability = str(availability).lower()
    return any(token in lower_name for token in POST_OUTCOME_TOKENS) or any(
        token in lower_availability
        for token in ["after_shipment", "after_delivery", "target_or_outcome"]
    )


def target_reconstruction_risk(row: pd.Series) -> str:
    """Classify AO2 target-reconstruction risk conservatively."""
    variable_name = str(row["variable_name"])
    ao2_policy = str(row["ao2_policy"])
    modeling_policy = str(row["modeling_policy"])
    availability = str(row["decision_time_availability"])

    if is_profit_proxy_field(variable_name):
        return "high_target_or_profit_proxy"
    if ao2_policy == "target":
        return "high_target_or_profit_proxy"
    if is_post_outcome_field(variable_name, availability):
        return "post_outcome_or_leakage_risk"
    if is_commercial_field(variable_name):
        return "commercial_formula_review_required"
    if "conditional" in modeling_policy or ao2_policy == "conditional":
        return "policy_or_stability_review_required"
    return "low_known_direct_risk"


def classify_policy(row: pd.Series) -> tuple[str, str, bool, str, str]:
    """Return modeling recommendation, action, group flag, decision-time status, and review note."""
    variable_name = str(row["variable_name"])
    ao2_policy = str(row["ao2_policy"])
    screening_status = str(row["screening_status"])
    modeling_policy = str(row["modeling_policy"])
    dashboard_policy = str(row["dashboard_policy"])
    availability = str(row["decision_time_availability"])

    requires_group_validation = (
        ao2_policy == "conditional"
        or screening_status == "needs_group_review"
        or "conditional" in modeling_policy
    )

    if ao2_policy == "target" or is_profit_proxy_field(variable_name):
        return (
            "target_or_proxy_excluded",
            "target_or_proxy_excluded",
            False,
            "target_or_proxy",
            "Excluded from AO2 predictors because it is the target, duplicate profit, realized margin, or direct profit proxy.",
        )

    if ao2_policy == "forbidden":
        if dashboard_policy == "dashboard_only" or modeling_policy == "dashboard_only":
            return (
                "dashboard_only",
                "dashboard_only",
                False,
                "no",
                "Excluded from AO2 modeling; retained only for descriptive audit or dashboard context.",
            )
        return (
            "exclude_from_ao2_modeling",
            "exclude_from_ao2_modeling",
            False,
            "no",
            "Excluded from AO2 modeling by leakage screening.",
        )

    if ao2_policy == "not_applicable":
        return (
            "descriptive_context_only",
            "descriptive_context_only",
            False,
            "not_applicable",
            "Processing metadata or non-business field; not a modeling predictor.",
        )

    if is_commercial_field(variable_name):
        return (
            "conditional_requires_group_review",
            "conditional_requires_group_review",
            True,
            "requires_group_review",
            "Commercial or order-value field; not approved for AO2 modeling without group validation of target-reconstruction risk.",
        )

    if requires_group_validation:
        return (
            "conditional_requires_group_review",
            "conditional_requires_group_review",
            True,
            "requires_group_review",
            "Decision-time plausible, but not approved for AO2 modeling without group validation.",
        )

    if ao2_policy == "allowed" and modeling_policy == "candidate_feature":
        return (
            "candidate_for_gold_review",
            "candidate_for_gold_review",
            False,
            "yes",
            "AO2 allowed by conceptual screening; still subject to Gold/modeling review.",
        )

    if dashboard_policy == "dashboard_only" or modeling_policy == "dashboard_only":
        return (
            "dashboard_only",
            "dashboard_only",
            False,
            "no",
            "Kept separate from AO2 predictor matrices as dashboard or audit context.",
        )

    return (
        "descriptive_context_only",
        "descriptive_context_only",
        requires_group_validation,
        availability,
        "Not recommended as a direct AO2 predictor by the current screening policy.",
    )


def infer_variable_type(df: pd.DataFrame, column_name: str | None) -> str:
    """Classify a column for focused EDA summarization."""
    if column_name is None:
        return "unavailable"
    series = df[column_name]
    non_missing = series.dropna()
    if non_missing.empty:
        return "empty"
    if is_datetime64_any_dtype(series):
        return "datetime"
    if is_numeric_dtype(series):
        distinct_count = int(non_missing.nunique())
        numeric_values = as_numeric(non_missing)
        integer_like = bool(((numeric_values.dropna() % 1).abs() < 1e-9).all())
        if distinct_count <= 12 and integer_like:
            return "categorical_numeric"
        return "numeric"
    return "categorical"


def format_currency(value: float | int | pd.NA) -> str:
    if pd.isna(value):
        return "n/a"
    return f"${float(value):,.2f}"


def format_difference(value: float | int | pd.NA) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value):+,.2f}"


def format_rate(value: float | int | pd.NA) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value):.1%}"


def direct_bivariate_is_inappropriate(variable_name: str) -> tuple[bool, str]:
    """Skip direct ranking for raw identifiers, precise locations, and raw timestamps."""
    lower_name = normalized_name(variable_name)
    if lower_name in {
        "order_id",
        "order_item_id",
        "customer_id",
        "order_customer_id",
        "product_card_id",
        "product_category_id",
        "order_item_cardprod_id",
        "category_id",
        "department_id",
    }:
        return True, "Identifier or numeric key; direct bivariate ranking is not a modeling signal."
    if any(token in lower_name for token in ["email", "fname", "lname", "password", "street"]):
        return True, "Sensitive or personal identifier; excluded from AO2 modeling."
    if any(token in lower_name for token in ["zipcode", "latitude", "longitude"]):
        return True, "Granular location field; use only approved coarse grouping or availability flags."
    if lower_name in {"order_date_dateorders", "shipping_date_dateorders"}:
        return True, "Raw timestamp should be replaced by approved derived features for modeling review."
    if lower_name in {"product_catalog_key", "product_name_normalized", "customer_region_key", "order_region_key"}:
        return True, "High-cardinality descriptor; grouping or train-only aggregate design is needed first."
    return False, ""


def interpretation_caveat(variable_name: str, recommendation: str, risk: str) -> str:
    """Return a concise caveat for detail rows."""
    if recommendation == "conditional_requires_group_review":
        if is_commercial_field(variable_name):
            return "Commercial field: descriptive signal only until AO2 target-reconstruction review is signed off."
        return "Conditional field: direct modeling use requires group validation."
    if recommendation == "candidate_for_gold_review":
        return "Allowed candidate for later Gold review; bivariate association is not causal."
    if risk == "high_target_or_profit_proxy":
        return "Profit target or proxy: excluded from AO2 predictors."
    return "Descriptive context only under current AO2 policy."


def categorical_bivariate(
    df: pd.DataFrame,
    variable_name: str,
    column_name: str,
    recommendation: str,
    risk: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Summarize profit by category with minimum support controls."""
    series = df[column_name].astype("string").fillna("(missing)").str.strip()
    distinct_count = int(series.nunique(dropna=False))
    grouped = (
        pd.DataFrame({"group_or_bin": series, "profit": df[target_col]})
        .groupby("group_or_bin", dropna=False)["profit"]
        .agg(row_count="count", mean_profit="mean", median_profit="median")
        .reset_index()
    )
    grouped["profit_difference_from_overall_mean"] = grouped["mean_profit"] - overall_mean_profit
    grouped["profit_difference_from_overall_median"] = grouped["median_profit"] - overall_median_profit
    grouped["sample_size_flag"] = grouped["row_count"].apply(
        lambda count: "support_ok" if count >= min_support_count else "below_min_support"
    )
    grouped["abs_mean_difference"] = grouped["profit_difference_from_overall_mean"].abs()

    if distinct_count > MAX_DIRECT_CATEGORICAL_LEVELS:
        return (
            {
                "eda_summary": (
                    f"Skipped direct category ranking: {distinct_count} distinct values exceeds "
                    f"the focused EDA limit of {MAX_DIRECT_CATEGORICAL_LEVELS}."
                ),
                "notable_pattern": "High-cardinality field; review grouping before modeling.",
                "profit_difference_from_overall": pd.NA,
                "sample_size_caveat": (
                    f"High-cardinality direct use not reviewed; minimum support was {min_support_count:,}."
                ),
            },
            [],
        )

    supported = grouped[grouped["sample_size_flag"] == "support_ok"].copy()
    unsupported_count = int((grouped["sample_size_flag"] == "below_min_support").sum())
    if supported.empty:
        return (
            {
                "eda_summary": (
                    f"Categorical field with {distinct_count} groups, but no group met the "
                    f"{min_support_count:,}-row support threshold."
                ),
                "notable_pattern": "No support-safe categorical profit pattern identified.",
                "profit_difference_from_overall": pd.NA,
                "sample_size_caveat": f"{unsupported_count} groups below minimum support.",
            },
            [],
        )

    ranked = supported.sort_values("abs_mean_difference", ascending=False)
    strongest = ranked.iloc[0]
    highest = supported.sort_values("mean_profit", ascending=False).iloc[0]
    lowest = supported.sort_values("mean_profit", ascending=True).iloc[0]

    summary = {
        "eda_summary": (
            f"Categorical: {distinct_count} groups; {len(supported)} met support. "
            f"Strongest supported group '{strongest['group_or_bin']}' had mean profit "
            f"{format_currency(strongest['mean_profit'])} "
            f"({format_difference(strongest['profit_difference_from_overall_mean'])} vs overall)."
        ),
        "notable_pattern": (
            f"Highest supported mean: '{highest['group_or_bin']}' "
            f"{format_currency(highest['mean_profit'])}; lowest: '{lowest['group_or_bin']}' "
            f"{format_currency(lowest['mean_profit'])}."
        ),
        "profit_difference_from_overall": round(float(strongest["profit_difference_from_overall_mean"]), 4),
        "sample_size_caveat": (
            f"Minimum support {min_support_count:,}; {unsupported_count} groups below threshold."
        ),
    }

    detail_rows = []
    for _, detail in ranked.head(15).iterrows():
        detail_rows.append(
            {
                "variable_name": variable_name,
                "group_or_bin": str(detail["group_or_bin"]),
                "row_count": int(detail["row_count"]),
                "mean_profit": round(float(detail["mean_profit"]), 6),
                "median_profit": round(float(detail["median_profit"]), 6),
                "profit_difference_from_overall_mean": round(
                    float(detail["profit_difference_from_overall_mean"]),
                    6,
                ),
                "profit_difference_from_overall_median": round(
                    float(detail["profit_difference_from_overall_median"]),
                    6,
                ),
                "sample_size_flag": str(detail["sample_size_flag"]),
                "interpretation_caveat": interpretation_caveat(variable_name, recommendation, risk),
            }
        )
    return summary, detail_rows


def monotonic_pattern_label(grouped: pd.DataFrame) -> str:
    """Classify a small ordered-bin pattern for readable EDA notes."""
    if len(grouped) < 3:
        return "too few bins for monotonicity comment"
    mean_values = grouped["mean_profit"].astype(float).to_list()
    differences = [later - earlier for earlier, later in zip(mean_values, mean_values[1:], strict=False)]
    if all(diff >= 0 for diff in differences) and any(diff > 0 for diff in differences):
        return "mean profit increases across supported bins"
    if all(diff <= 0 for diff in differences) and any(diff < 0 for diff in differences):
        return "mean profit decreases across supported bins"
    return "nonlinear or uneven bin pattern"


def numeric_bivariate(
    df: pd.DataFrame,
    variable_name: str,
    column_name: str,
    recommendation: str,
    risk: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Summarize profit by quantile bins for numeric variables."""
    values = as_numeric(df[column_name])
    missing_rate = float(values.isna().mean())
    valid = pd.DataFrame({"value": values, "profit": df[target_col]}).dropna()

    if valid.empty or valid["value"].nunique() <= 1:
        return (
            {
                "eda_summary": "Numeric field has too few non-missing or distinct values for EDA.",
                "notable_pattern": "No numeric profit pattern identified.",
                "profit_difference_from_overall": pd.NA,
                "sample_size_caveat": f"Missing rate {format_rate(missing_rate)}.",
            },
            [],
        )

    bin_count = min(5, int(valid["value"].nunique()))
    try:
        valid["bin"] = pd.qcut(valid["value"], q=bin_count, duplicates="drop")
    except ValueError:
        valid["bin"] = pd.cut(valid["value"], bins=bin_count, duplicates="drop")

    grouped = (
        valid.groupby("bin", observed=True)["profit"]
        .agg(row_count="count", mean_profit="mean", median_profit="median")
        .reset_index()
    )
    grouped["group_or_bin"] = grouped["bin"].astype("string")
    grouped["profit_difference_from_overall_mean"] = grouped["mean_profit"] - overall_mean_profit
    grouped["profit_difference_from_overall_median"] = grouped["median_profit"] - overall_median_profit
    grouped["sample_size_flag"] = grouped["row_count"].apply(
        lambda count: "support_ok" if count >= min_support_count else "below_min_support"
    )

    supported = grouped[grouped["sample_size_flag"] == "support_ok"].copy()
    if supported.empty:
        return (
            {
                "eda_summary": (
                    f"Numeric field binned into {len(grouped)} groups, but no bin met "
                    f"the {min_support_count:,}-row support threshold."
                ),
                "notable_pattern": "No support-safe numeric bin pattern identified.",
                "profit_difference_from_overall": pd.NA,
                "sample_size_caveat": f"Missing rate {format_rate(missing_rate)}.",
            },
            [],
        )

    supported["_bin_order"] = range(len(supported))
    highest = supported.sort_values("mean_profit", ascending=False).iloc[0]
    lowest = supported.sort_values("mean_profit", ascending=True).iloc[0]
    strongest = supported.assign(
        abs_mean_difference=supported["profit_difference_from_overall_mean"].abs()
    ).sort_values("abs_mean_difference", ascending=False).iloc[0]
    monotonic_label = monotonic_pattern_label(supported.sort_values("_bin_order"))

    summary = {
        "eda_summary": (
            f"Numeric: {len(supported)} supported quantile bins; missing rate "
            f"{format_rate(missing_rate)}. Strongest supported bin {strongest['group_or_bin']} "
            f"had mean profit {format_currency(strongest['mean_profit'])} "
            f"({format_difference(strongest['profit_difference_from_overall_mean'])} vs overall)."
        ),
        "notable_pattern": (
            f"{monotonic_label}; highest supported bin {highest['group_or_bin']} "
            f"{format_currency(highest['mean_profit'])}; lowest bin {lowest['group_or_bin']} "
            f"{format_currency(lowest['mean_profit'])}."
        ),
        "profit_difference_from_overall": round(
            float(strongest["profit_difference_from_overall_mean"]),
            4,
        ),
        "sample_size_caveat": (
            f"Minimum support {min_support_count:,}; missing rate {format_rate(missing_rate)}."
        ),
    }

    detail_rows = []
    for _, detail in supported.iterrows():
        detail_rows.append(
            {
                "variable_name": variable_name,
                "group_or_bin": str(detail["group_or_bin"]),
                "row_count": int(detail["row_count"]),
                "mean_profit": round(float(detail["mean_profit"]), 6),
                "median_profit": round(float(detail["median_profit"]), 6),
                "profit_difference_from_overall_mean": round(
                    float(detail["profit_difference_from_overall_mean"]),
                    6,
                ),
                "profit_difference_from_overall_median": round(
                    float(detail["profit_difference_from_overall_median"]),
                    6,
                ),
                "sample_size_flag": str(detail["sample_size_flag"]),
                "interpretation_caveat": interpretation_caveat(variable_name, recommendation, risk),
            }
        )
    return summary, detail_rows


def bivariate_for_variable(
    df: pd.DataFrame,
    variable_name: str,
    column_name: str | None,
    variable_type: str,
    recommendation: str,
    risk: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return focused AO2 bivariate summaries for eligible fields."""
    if recommendation in {
        "target_or_proxy_excluded",
        "exclude_from_ao2_modeling",
        "dashboard_only",
        "descriptive_context_only",
    }:
        return (
            {
                "eda_summary": "Not analyzed as an AO2 candidate under the current leakage or target policy.",
                "notable_pattern": "Excluded from candidate modeling review.",
                "profit_difference_from_overall": pd.NA,
                "sample_size_caveat": "Not applicable.",
            },
            [],
        )

    if column_name is None:
        return (
            {
                "eda_summary": "Column not present in the loaded Silver dataset or derived review features.",
                "notable_pattern": "No EDA produced for unavailable field.",
                "profit_difference_from_overall": pd.NA,
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
                "profit_difference_from_overall": pd.NA,
                "sample_size_caveat": "Requires approved grouping or train-only aggregate design before modeling.",
            },
            [],
        )

    if variable_type == "numeric":
        return numeric_bivariate(df, variable_name, column_name, recommendation, risk)
    return categorical_bivariate(df, variable_name, column_name, recommendation, risk)


# COMMAND ----------

summary_rows: list[dict[str, Any]] = []
detail_rows: list[dict[str, Any]] = []

for _, screen_row in screening_df.iterrows():
    variable_name = str(screen_row["variable_name"])
    recommendation, recommended_action, requires_group_validation, decision_time_valid, leakage_review_result = (
        classify_policy(screen_row)
    )
    risk = target_reconstruction_risk(screen_row)
    resolved_column = resolve_column(orders_df, variable_name)
    variable_type = infer_variable_type(orders_df, resolved_column)
    financial_review_flag = is_commercial_field(variable_name) or is_profit_proxy_field(variable_name)
    eda_result, details = bivariate_for_variable(
        orders_df,
        variable_name,
        resolved_column,
        variable_type,
        recommendation,
        risk,
    )
    detail_rows.extend(details)

    if recommendation == "candidate_for_gold_review":
        modeling_recommendation = (
            "Candidate for later AO2 Gold/modeling review; do not infer causality or final feature approval."
        )
    elif recommendation == "conditional_requires_group_review":
        modeling_recommendation = (
            "Prepare for group validation; do not approve as an AO2 modeling predictor in this issue."
        )
    elif recommendation == "target_or_proxy_excluded":
        modeling_recommendation = "Exclude from AO2 predictors as target, duplicate profit, or realized profit proxy."
    elif recommendation == "dashboard_only":
        modeling_recommendation = "Use only for descriptive audit, dashboard, or governance context."
    elif recommendation == "exclude_from_ao2_modeling":
        modeling_recommendation = "Exclude from AO2 predictor lists."
    else:
        modeling_recommendation = "Use only as descriptive context unless policy changes."

    summary_rows.append(
        {
            "variable_name": variable_name,
            "analysis_column": resolved_column or "",
            "variable_origin": screen_row["variable_origin"],
            "variable_type": variable_type,
            "ao2_policy": screen_row["ao2_policy"],
            "screening_status": screen_row["screening_status"],
            "decision_time_valid": decision_time_valid,
            "target_reconstruction_risk": risk,
            "eda_summary": eda_result["eda_summary"],
            "notable_pattern": eda_result["notable_pattern"],
            "profit_difference_from_overall": eda_result["profit_difference_from_overall"],
            "sample_size_caveat": eda_result["sample_size_caveat"],
            "leakage_review_result": leakage_review_result,
            "modeling_recommendation": modeling_recommendation,
            "requires_group_validation": requires_group_validation,
            "recommended_action": recommended_action,
            "financial_or_commercial_review_field": financial_review_flag,
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

def why_may_be_useful(row: pd.Series) -> str:
    variable_name = str(row["variable_name"])
    lower_name = normalized_name(variable_name)
    if row["recommended_action"] == "target_or_proxy_excluded":
        return "Useful only for validating the AO2 target/proxy policy and historical profitability context."
    if any(token in lower_name for token in ["discount", "price", "quantity", "sales", "total", "gross", "net"]):
        return "May describe order value, discount intensity, price tier, or order composition before dispatch."
    if any(token in lower_name for token in ["category", "department", "product"]):
        return "May describe product mix differences in historical profitability."
    if any(token in lower_name for token in ["market", "region", "country", "state", "city"]):
        return "May describe geographic or operating-market differences in historical profitability."
    if any(token in lower_name for token in ["shipping", "shipment"]):
        return "May describe planned service-level differences in historical profitability."
    return str(row["notable_pattern"])


def why_risky(row: pd.Series) -> str:
    variable_name = str(row["variable_name"])
    lower_name = normalized_name(variable_name)
    risk = str(row["target_reconstruction_risk"])
    if risk == "high_target_or_profit_proxy":
        return "It is the AO2 target, duplicate profit outcome, realized margin, or a direct profit proxy."
    if risk == "commercial_formula_review_required":
        return "It may be mathematically tied to realized profit through revenue, price, quantity, discount, or order-value formulas."
    if any(token in lower_name for token in ["id", "key", "catalog"]):
        return "It may be a high-cardinality identifier and can overfit if used directly."
    if any(token in lower_name for token in ["city", "zipcode", "latitude", "longitude"]):
        return "It may be granular, unstable, or privacy-sensitive; grouping must be approved."
    if "status" in lower_name:
        return "Business status semantics need validation so post-order outcomes are not encoded."
    return "It is conditional or needs group review under the conceptual screening artifact."


def proposed_decision(row: pd.Series) -> str:
    variable_name = str(row["variable_name"])
    lower_name = normalized_name(variable_name)
    action = str(row["recommended_action"])
    if action == "target_or_proxy_excluded":
        return "exclude"
    if action == "dashboard_only":
        return "descriptive only"
    if action == "conditional_requires_group_review":
        if any(token in lower_name for token in ["sales_per_customer", "product_price"]):
            return "descriptive only or exclude duplicate pending group decision"
        if is_commercial_field(variable_name):
            return "conditional candidate pending group decision"
        return "requires group decision"
    return action.replace("_", " ")


def validation_question(row: pd.Series) -> str:
    variable_name = str(row["variable_name"])
    lower_name = normalized_name(variable_name)
    action = str(row["recommended_action"])
    if action == "target_or_proxy_excluded":
        return f"Confirm `{variable_name}` remains excluded from AO2 predictors and is used only for target audit or descriptive reporting."
    if any(token in lower_name for token in ["sales_per_customer", "order_item_total", "item_net_sales_amount"]):
        return (
            f"Can `{variable_name}` be used as the single reviewed order-value field, or should it stay descriptive only "
            "to avoid duplicate value fields and target reconstruction?"
        )
    if any(token in lower_name for token in ["sales", "discount", "price", "quantity", "gross", "net"]):
        return (
            f"Is `{variable_name}` known before dispatch, non-duplicative, and acceptable for AO2 modeling without "
            "mechanically reconstructing profit?"
        )
    if any(token in lower_name for token in ["id", "key", "city", "zipcode", "latitude", "longitude"]):
        return f"What approved grouping or train-only encoding, if any, is acceptable for `{variable_name}`?"
    return f"Should `{variable_name}` be excluded, descriptive only, or conditionally approved for later AO2 Gold/modeling review?"


review_mask = (
    summary_df["requires_group_validation"]
    | summary_df["financial_or_commercial_review_field"]
    | summary_df["target_reconstruction_risk"].isin(
        ["high_target_or_profit_proxy", "commercial_formula_review_required"]
    )
)
review_candidates = summary_df[review_mask].copy()

review_candidates["observed_eda_pattern"] = review_candidates["notable_pattern"]
review_candidates["why_it_may_be_useful"] = review_candidates.apply(why_may_be_useful, axis=1)
review_candidates["why_it_may_be_risky"] = review_candidates.apply(why_risky, axis=1)
review_candidates["target_reconstruction_concern"] = review_candidates["target_reconstruction_risk"]
review_candidates["proposed_decision"] = review_candidates.apply(proposed_decision, axis=1)
review_candidates["question_for_group_validation"] = review_candidates.apply(validation_question, axis=1)
review_candidates["validation_priority"] = (
    pd.to_numeric(review_candidates["profit_difference_from_overall"], errors="coerce")
    .abs()
    .fillna(0)
    .ge(REVIEW_SIGNAL_THRESHOLD)
    .map({True: "higher_signal_review", False: "standard_policy_review"})
)

group_review_columns = [
    "variable_name",
    "variable_origin",
    "variable_type",
    "ao2_policy",
    "screening_status",
    "observed_eda_pattern",
    "why_it_may_be_useful",
    "why_it_may_be_risky",
    "target_reconstruction_concern",
    "proposed_decision",
    "question_for_group_validation",
    "validation_priority",
    "recommended_action",
]

group_review_df = review_candidates[group_review_columns].copy()
group_review_df.to_csv(GROUP_REVIEW_OUTPUT_PATH, index=False)

print(f"Wrote group-validation list: {GROUP_REVIEW_OUTPUT_PATH}")
print(f"Group-review or AO2 commercial-policy variables listed: {len(group_review_df):,}")


# COMMAND ----------

def sanitize_svg_text(value: Any) -> str:
    return html.escape(str(value))


def svg_profit_bar_chart(
    rows: pd.DataFrame,
    title: str,
    output_path: Path,
    max_rows: int = 10,
    policy_note: str = "",
) -> None:
    """Write a lightweight SVG horizontal bar chart for mean and median profit."""
    plot_rows = rows.head(max_rows).copy()
    if plot_rows.empty:
        return

    width = 1040
    row_height = 38
    left = 330
    top = 70
    bar_width = 520
    height = top + row_height * len(plot_rows) + 56
    values = plot_rows["mean_profit"].astype(float).to_list()
    min_value = min(min(values), overall_mean_profit, 0.0)
    max_value = max(max(values), overall_mean_profit, 0.0)
    spread = max(max_value - min_value, 1.0)

    def x_for_value(value: float) -> int:
        return left + int(((value - min_value) / spread) * bar_width)

    zero_x = x_for_value(0.0)
    overall_x = x_for_value(overall_mean_profit)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="20" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="700">{sanitize_svg_text(title)}</text>',
    ]
    if policy_note:
        parts.append(
            f'<text x="20" y="52" font-family="Arial, sans-serif" font-size="12" fill="#555">{sanitize_svg_text(policy_note)}</text>'
        )
    parts.extend(
        [
            f'<line x1="{zero_x}" x2="{zero_x}" y1="{top - 8}" y2="{height - 32}" stroke="#777" stroke-width="1"/>',
            f'<line x1="{overall_x}" x2="{overall_x}" y1="{top - 8}" y2="{height - 32}" stroke="#a33" stroke-width="2" stroke-dasharray="5,4"/>',
        ]
    )

    for index, (_, row) in enumerate(plot_rows.iterrows()):
        y = top + index * row_height
        label = str(row["group_or_bin"])
        count = int(row["row_count"])
        mean_value = float(row["mean_profit"])
        median_value = float(row["median_profit"])
        value_x = x_for_value(mean_value)
        median_x = x_for_value(median_value)
        bar_x = min(zero_x, value_x)
        length = max(2, abs(value_x - zero_x))
        color = "#2f6f73" if mean_value >= 0 else "#9b4a3f"
        parts.extend(
            [
                f'<text x="20" y="{y + 20}" font-family="Arial, sans-serif" font-size="13">{sanitize_svg_text(label[:44])}</text>',
                f'<rect x="{bar_x}" y="{y}" width="{length}" height="22" rx="2" fill="{color}"/>',
                f'<line x1="{median_x}" x2="{median_x}" y1="{y - 2}" y2="{y + 24}" stroke="#222" stroke-width="2"/>',
                f'<text x="{left + bar_width + 16}" y="{y + 16}" font-family="Arial, sans-serif" font-size="12">mean {format_currency(mean_value)}; median {format_currency(median_value)}; n={count:,}</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="{overall_x + 6}" y="{height - 14}" font-family="Arial, sans-serif" font-size="12" fill="#a33">overall mean {format_currency(overall_mean_profit)}</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(parts), encoding="utf-8")


def svg_profit_distribution(output_path: Path) -> None:
    """Write a focused SVG histogram for the AO2 target distribution."""
    clipped = target_series.clip(
        lower=float(target_series.quantile(0.01)),
        upper=float(target_series.quantile(0.99)),
    )
    bins = pd.cut(clipped, bins=24, duplicates="drop")
    counts = bins.value_counts(sort=False)
    if counts.empty:
        return

    width = 980
    height = 420
    left = 70
    top = 62
    plot_width = 860
    plot_height = 280
    max_count = max(int(counts.max()), 1)
    bar_gap = 2
    bar_width = max(4, int(plot_width / len(counts)) - bar_gap)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="20" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="700">AO2 Target Distribution: Order Profit Per Order</text>',
        f'<text x="20" y="52" font-family="Arial, sans-serif" font-size="12" fill="#555">Clipped to 1st-99th percentile for readability; target remains unchanged in tables. Skewness {target_skewness:.2f}.</text>',
    ]

    for index, (interval, count) in enumerate(counts.items()):
        count_int = int(count)
        bar_height = int((count_int / max_count) * plot_height)
        x = left + index * (bar_width + bar_gap)
        y = top + plot_height - bar_height
        parts.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#2f6f73"/>')
        if index in {0, len(counts) - 1}:
            parts.append(
                f'<text x="{x}" y="{top + plot_height + 22}" font-family="Arial, sans-serif" font-size="11" transform="rotate(35 {x},{top + plot_height + 22})">{sanitize_svg_text(interval)}</text>'
            )

    parts.extend(
        [
            f'<line x1="{left}" x2="{left + plot_width}" y1="{top + plot_height}" y2="{top + plot_height}" stroke="#333"/>',
            f'<text x="20" y="{height - 20}" font-family="Arial, sans-serif" font-size="12">Mean {format_currency(overall_mean_profit)}; median {format_currency(overall_median_profit)}; IQR outliers {outlier_count:,}</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(parts), encoding="utf-8")


def figure_rows_for(variable_name: str) -> pd.DataFrame:
    rows = detail_df[detail_df["variable_name"] == variable_name].copy()
    if rows.empty:
        return rows
    rows["_abs_diff"] = rows["profit_difference_from_overall_mean"].abs()
    return rows.sort_values("_abs_diff", ascending=False)


saved_figures: list[str] = []
distribution_path = FIGURE_OUTPUT_DIR / "ao2_profit_distribution.svg"
svg_profit_distribution(distribution_path)
saved_figures.append(str(distribution_path))

figure_specs = [
    (
        "Shipping Mode",
        "ao2_profit_by_shipping_mode.svg",
        "AO2 Mean Profit by Shipping Mode",
        "Allowed pre-dispatch service field; descriptive association only.",
    ),
    (
        "Market",
        "ao2_profit_by_market.svg",
        "AO2 Mean Profit by Market",
        "Allowed order-time market field; descriptive association only.",
    ),
    (
        "Order Item Discount Rate",
        "ao2_profit_by_discount_rate_bin.svg",
        "AO2 Mean Profit by Discount Rate Bin",
        "Conditional commercial field; requires AO2 group validation before modeling.",
    ),
    (
        "Category Name",
        "ao2_profit_by_category_name.svg",
        "AO2 Mean Profit by Product Category",
        "Allowed product category field; descriptive association only.",
    ),
]

for variable_name, file_name, title, note in figure_specs:
    rows = figure_rows_for(variable_name)
    if rows.empty:
        continue
    figure_path = FIGURE_OUTPUT_DIR / file_name
    svg_profit_bar_chart(rows, title, figure_path, policy_note=note)
    saved_figures.append(str(figure_path))

print("Saved lightweight SVG figures:")
for figure_path in saved_figures:
    print(f"- {figure_path}")


# COMMAND ----------

recommended_candidates = summary_df[
    summary_df["recommended_action"] == "candidate_for_gold_review"
].copy()
conditional_review = summary_df[
    summary_df["recommended_action"] == "conditional_requires_group_review"
].copy()
target_or_proxy_excluded = summary_df[
    summary_df["recommended_action"] == "target_or_proxy_excluded"
].copy()
excluded_or_dashboard = summary_df[
    summary_df["recommended_action"].isin(["exclude_from_ao2_modeling", "dashboard_only"])
].copy()
commercial_review = summary_df[
    summary_df["financial_or_commercial_review_field"]
].copy()

top_supported_patterns = summary_df[
    summary_df["recommended_action"].isin(
        ["candidate_for_gold_review", "conditional_requires_group_review"]
    )
].copy()
top_supported_patterns["_abs_diff"] = (
    pd.to_numeric(top_supported_patterns["profit_difference_from_overall"], errors="coerce")
    .abs()
    .fillna(0)
)
top_supported_patterns = top_supported_patterns.sort_values("_abs_diff", ascending=False).head(12)

print("AO2-safe allowed candidate variables reviewed:", len(recommended_candidates))
print("Conditional or needs_group_review variables reviewed:", len(conditional_review))
print("Financial/commercial/profit-policy variables documented:", len(commercial_review))
print("Target/profit-proxy variables excluded:", len(target_or_proxy_excluded))
print("Excluded/dashboard-only variables documented:", len(excluded_or_dashboard))
print("")
print("Top support-safe bivariate profitability patterns:")
for _, row in top_supported_patterns.iterrows():
    diff = row["profit_difference_from_overall"]
    diff_text = "n/a" if pd.isna(diff) else format_difference(float(diff))
    print(f"- {row['variable_name']}: {diff_text}; {row['notable_pattern']}")


# COMMAND ----------

try:
    display(summary_df.head(25))  # type: ignore[name-defined]
except NameError:
    print(summary_df.head(25).to_string(index=False))
