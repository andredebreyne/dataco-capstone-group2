"""Register the DataCo feature availability map in Databricks.

This script loads the versioned CSV reference artifact from the repository,
validates its contract, copies the CSV to the project Unity Catalog Volume,
and writes a Delta version for Spark-based downstream consumption.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, lit
from pyspark.sql.types import StringType, StructField, StructType


VOLUME_ROOT = os.getenv("DATACO_VOLUME_ROOT", "/Volumes/workspace/default/raw_data").rstrip("/")

REPO_FEATURE_MAP_PATH = Path("data/references/feature_availability_map.csv")

FEATURE_MAP_INPUT_PATH = Path(
    os.getenv("DATACO_FEATURE_AVAILABILITY_MAP_INPUT_PATH", str(REPO_FEATURE_MAP_PATH))
)

FEATURE_MAP_VOLUME_CSV_PATH = Path(
    os.getenv(
        "DATACO_FEATURE_AVAILABILITY_MAP_VOLUME_CSV_PATH",
        f"{VOLUME_ROOT}/references/feature_availability_map.csv",
    )
)

FEATURE_MAP_DELTA_OUTPUT_PATH = os.getenv(
    "DATACO_FEATURE_AVAILABILITY_MAP_DELTA_OUTPUT_PATH",
    f"{VOLUME_ROOT}/references/feature_availability_map",
)

DISABLED_PUBLIC_DBFS_PREFIXES = ("dbfs:/FileStore/", "/FileStore/")
EXPECTED_ROW_COUNT = 53

EMBEDDED_FEATURE_AVAILABILITY_MAP_CSV = """source_column,silver_column,semantic_group,availability_timing,ao1_policy,ao2_policy,dashboard_policy,modeling_use,rationale,derived_feature_guidance,related_document
Type,Type,transaction,order_creation,review,review,allowed,direct_candidate,"Transaction type appears to be known at order creation, but business semantics should be confirmed before modeling.","May be used as a categorical candidate after train-only encoding.","docs/leakage_control_plan.md"
Days for shipping (real),Days_for_shipping_real,shipping_actual,after_delivery,forbidden,forbidden,allowed,dashboard_only,"Actual shipping duration is known only after fulfillment and can directly reveal late-delivery behavior.","Use only for outcome audit, descriptive dashboards, and AO1 target validation.","docs/ao1_target_definition.md"
Days for shipment (scheduled),Days_for_shipment_scheduled,shipping_planned,before_dispatch,allowed,allowed,allowed,direct_candidate,"Scheduled shipping duration is planned service information expected to be known before dispatch.","Can support planned-service features such as speed tier or urgent-service flag.","docs/leakage_control_plan.md"
Benefit per order,Benefit_per_order,financial_outcome,target_or_outcome,forbidden,forbidden,allowed,dashboard_only,"This field is an earnings/profit outcome and is documented as an exact duplicate or proxy of the AO2 target.","Use only for AO2 target audit or descriptive historical reporting.","docs/ao2_target_policy.md"
Sales per customer,Sales_per_customer,financial_order_value,order_creation,review,review,allowed,review,"This field is order-value information but may duplicate Order Item Total and should not be included redundantly.","Prefer Order Item Total if both are available; document any selected financial predictors.","docs/ao2_target_policy.md"
Delivery Status,Delivery_Status,delivery_outcome,after_delivery,forbidden,forbidden,allowed,dashboard_only,"Delivery status is a post-delivery outcome and direct proxy for AO1 late-delivery target.","Use only for descriptive reporting and target validation.","docs/ao1_target_definition.md"
Late_delivery_risk,Late_delivery_risk,target,target_or_outcome,target,forbidden,allowed,exclude,"This is the official AO1 binary target and must never be used as a predictor.","Use as AO1 target only; exclude from predictor matrices.","docs/ao1_target_definition.md"
Category Id,Category_Id,product_category,order_creation,review,review,allowed,review,"Product category code is likely known at order creation but may be high-cardinality or duplicate Product Category Id.","Use directly only after categorical review; training-only encoding required for modeling.","docs/leakage_control_plan.md"
Category Name,Category_Name,product_category,order_creation,allowed,allowed,allowed,direct_candidate,"Product category name is expected to be known at order creation and has clear business meaning.","Can be normalized or grouped deterministically before train-only encoding.","docs/leakage_control_plan.md"
Customer City,Customer_City,customer_region,order_creation,review,review,allowed,review,"Customer city is likely known at order creation but may be high-cardinality and unstable.","Use normalized city or grouped region features; avoid blind one-hot encoding.","docs/leakage_control_plan.md"
Customer Country,Customer_Country,customer_region,order_creation,allowed,allowed,allowed,direct_candidate,"Customer country is a stable geographic field expected to be known at order creation.","Can be used as a regional categorical feature after train-only encoding.","docs/leakage_control_plan.md"
Customer Email,Customer_Email,customer_identifier,sensitive_identifier,forbidden,forbidden,forbidden,exclude,"Masked or direct customer contact information is an identifier and not operationally useful for modeling.","Exclude from modeling and dashboard outputs unless explicitly needed for data-quality audit.","docs/leakage_control_plan.md"
Customer Fname,Customer_Fname,customer_identifier,sensitive_identifier,forbidden,forbidden,forbidden,exclude,"Customer first name is a personal identifier.","Exclude from modeling and reporting artifacts.","docs/leakage_control_plan.md"
Customer Id,Customer_Id,customer_identifier,order_creation,review,review,allowed,training_only_aggregate,"Customer ID may be known at order creation but should not be used directly as a high-cardinality identifier.","May support historical aggregates only if computed with time-aware train-only logic.","docs/leakage_control_plan.md"
Customer Lname,Customer_Lname,customer_identifier,sensitive_identifier,forbidden,forbidden,forbidden,exclude,"Customer last name is a personal identifier and has limited modeling value.","Exclude from modeling and reporting artifacts.","docs/leakage_control_plan.md"
Customer Password,Customer_Password,customer_identifier,sensitive_identifier,forbidden,forbidden,forbidden,exclude,"Masked customer password/key is sensitive and non-operational for modeling.","Exclude from all modeling and dashboard artifacts.","docs/leakage_control_plan.md"
Customer Segment,Customer_Segment,customer_profile,order_creation,allowed,allowed,allowed,direct_candidate,"Customer segment is expected to be known at order creation and has clear business meaning.","Can be normalized and encoded inside train-only preprocessing.","docs/leakage_control_plan.md"
Customer State,Customer_State,customer_region,order_creation,allowed,allowed,allowed,direct_candidate,"Customer state is expected to be known at order creation and supports regional analysis.","Can be normalized or grouped before train-only encoding.","docs/leakage_control_plan.md"
Customer Street,Customer_Street,customer_identifier,sensitive_identifier,forbidden,forbidden,forbidden,exclude,"Street-level address detail is high-cardinality and sensitive.","Exclude; use coarser regional fields instead.","docs/leakage_control_plan.md"
Customer Zipcode,Customer_Zipcode,customer_region,order_creation,review,review,allowed,derived_only,"Customer postal code may be known at order creation but is granular and partially missing.","Prefer availability flags or coarse geographic grouping; avoid raw zip as direct feature.","docs/customer_regional_features.md"
Department Id,Department_Id,product_department,order_creation,review,review,allowed,review,"Department code is expected to be known at order creation but may duplicate department name.","Use with documented category/department grouping decisions.","docs/leakage_control_plan.md"
Department Name,Department_Name,product_department,order_creation,allowed,allowed,allowed,direct_candidate,"Department name is expected to be known at order creation and has clear business meaning.","Can be normalized and encoded inside train-only preprocessing.","docs/leakage_control_plan.md"
Latitude,Latitude,geography,order_creation,review,review,allowed,derived_only,"Latitude appears to describe customer/store geography and is expected to be known before dispatch, but precision should be controlled.","Prefer rounded coordinates or regional grouping for modeling.","docs/customer_regional_features.md"
Longitude,Longitude,geography,order_creation,review,review,allowed,derived_only,"Longitude appears to describe customer/store geography and is expected to be known before dispatch, but precision should be controlled.","Prefer rounded coordinates or regional grouping for modeling.","docs/customer_regional_features.md"
Market,Market,order_region,order_creation,allowed,allowed,allowed,direct_candidate,"Market is an order destination operating region expected to be known before dispatch.","Can be used as a regional categorical feature after train-only encoding.","docs/leakage_control_plan.md"
Order City,Order_City,order_region,order_creation,review,review,allowed,review,"Order destination city is expected to be known before dispatch but may be high-cardinality.","Use normalized city, grouped geography, or training-only encoding with review.","docs/customer_regional_features.md"
Order Country,Order_Country,order_region,order_creation,allowed,allowed,allowed,direct_candidate,"Order destination country is expected to be known before dispatch and has clear business meaning.","Can be used as a regional categorical feature after train-only encoding.","docs/leakage_control_plan.md"
Order Customer Id,Order_Customer_Id,customer_identifier,order_creation,review,review,allowed,training_only_aggregate,"Order customer code is an identifier likely known at order creation but should not be used directly as a raw high-cardinality feature.","May support training-only historical aggregates if approved.","docs/leakage_control_plan.md"
order date (DateOrders),order_date_DateOrders,order_time,order_creation,allowed,allowed,allowed,derived_only,"Order timestamp is known at order creation and is needed for chronological split and seasonality features.","Use derived calendar features; avoid treating raw timestamp as an unconstrained model feature.","docs/order_time_features.md"
Order Id,Order_Id,order_identifier,order_creation,forbidden,forbidden,allowed,join_key_only,"Order ID is a row/order identifier, not a predictive business signal.","Use only for traceability, joins, deduplication, and validation.","docs/leakage_control_plan.md"
Order Item Cardprod Id,Order_Item_Cardprod_Id,product_identifier,order_creation,review,review,allowed,review,"Order-item product code is known at order creation but may be high-cardinality.","Use only after product grouping or train-only encoding review.","docs/shipping_product_features.md"
Order Item Discount,Order_Item_Discount,financial_order_value,order_creation,review,review,allowed,review,"Discount value is likely known at order time but must be reviewed for AO2 target-reconstruction risk.","Allowed only if documented as pre-dispatch and not used to reconstruct profit target.","docs/ao2_target_policy.md"
Order Item Discount Rate,Order_Item_Discount_Rate,financial_order_value,order_creation,review,review,allowed,review,"Discount rate is likely known at order time but must be reviewed for AO2 target-reconstruction risk.","Can support commercial structure features with AO2 review.","docs/ao2_target_policy.md"
Order Item Id,Order_Item_Id,order_identifier,order_creation,forbidden,forbidden,allowed,join_key_only,"Order item ID is a row/item identifier, not a predictive business signal.","Use only for traceability, joins, deduplication, and validation.","docs/leakage_control_plan.md"
Order Item Product Price,Order_Item_Product_Price,financial_order_value,order_creation,review,review,allowed,review,"Product price is expected to be known at order time but may duplicate Product Price.","Prefer one price field only; document AO2 financial predictor selection.","docs/ao2_target_policy.md"
Order Item Profit Ratio,Order_Item_Profit_Ratio,financial_outcome,target_or_outcome,forbidden,forbidden,allowed,dashboard_only,"Realized profit ratio can reconstruct or approximate AO2 target when combined with order value.","Use only for descriptive historical margin audit, never as main AO2 predictor.","docs/ao2_target_policy.md"
Order Item Quantity,Order_Item_Quantity,order_composition,order_creation,allowed,allowed,allowed,direct_candidate,"Item quantity is order composition information expected to be known at order creation.","Can be used directly as a numeric predictor after validation.","docs/ao2_target_policy.md"
Sales,Sales,financial_order_value,order_creation,review,review,allowed,review,"Gross sales is order-value information but may be mechanically tied to price and quantity.","Allowed only with documented AO2 financial predictor policy; avoid redundant value fields.","docs/ao2_target_policy.md"
Order Item Total,Order_Item_Total,financial_order_value,order_creation,review,review,allowed,review,"Discounted item/order value is expected to be known at order time and is recommended as AO3 denominator.","Conditionally allowed for AO2/AO3 with documented financial predictor policy.","docs/ao2_target_policy.md"
Order Profit Per Order,Order_Profit_Per_Order,financial_outcome,target_or_outcome,forbidden,target,allowed,exclude,"This is the official AO2 target and must not be used as an AO2 predictor.","Use as AO2 target only; exclude from predictor matrices.","docs/ao2_target_policy.md"
Order Region,Order_Region,order_region,order_creation,allowed,allowed,allowed,direct_candidate,"Order destination region is expected to be known before dispatch and has clear business meaning.","Can be normalized and encoded inside train-only preprocessing.","docs/leakage_control_plan.md"
Order State,Order_State,order_region,order_creation,allowed,allowed,allowed,direct_candidate,"Order destination state is expected to be known before dispatch and supports regional analysis.","Can be normalized or grouped before train-only encoding.","docs/leakage_control_plan.md"
Order Status,Order_Status,order_outcome,after_order_review,forbidden,forbidden,allowed,dashboard_only,"Order status may encode cancellation, fraud, payment review, or fulfillment outcomes after order creation.","Use only for descriptive analysis or AO1 population sensitivity decisions.","docs/ao1_target_definition.md"
Order Zipcode,Order_Zipcode,order_region,order_creation,review,review,allowed,derived_only,"Order postal code may be known before dispatch but has high missingness and granular geography.","Prefer availability flags or coarse geographic grouping; avoid raw zip as direct feature.","docs/customer_regional_features.md"
Product Card Id,Product_Card_Id,product_identifier,order_creation,review,review,allowed,review,"Product code is known at order time but may be high-cardinality.","Use only after product grouping or train-only encoding review.","docs/shipping_product_features.md"
Product Category Id,Product_Category_Id,product_category,order_creation,review,review,allowed,review,"Product category code is known at order time but may duplicate Category Id.","Use one category representation and document the choice.","docs/shipping_product_features.md"
Product Description,Product_Description,product_text,descriptive_only,forbidden,forbidden,allowed,exclude,"Product description is empty in the reviewed dataset and not useful for structured modeling.","Exclude from modeling; descriptive metadata only if populated in future data.","docs/silver_cleaning_rules.md"
Product Image,Product_Image,product_asset,descriptive_only,forbidden,forbidden,allowed,dashboard_only,"Product image URL/text asset is not part of the structured pre-shipment model.","Use only for dashboard or catalog display if needed.","docs/leakage_control_plan.md"
Product Name,Product_Name,product_descriptor,order_creation,review,review,allowed,review,"Product name is known at order time but may be high-cardinality.","Use normalized product name only after grouping or train-only encoding review.","docs/shipping_product_features.md"
Product Price,Product_Price,financial_order_value,order_creation,review,review,allowed,review,"Product list price is expected to be known at order time but may duplicate Order Item Product Price.","Prefer one price field only; document AO2 financial predictor selection.","docs/ao2_target_policy.md"
Product Status,Product_Status,product_status,order_creation,review,review,allowed,review,"Product stock/status indicator is expected to be known before dispatch but source semantics should be preserved cautiously.","Use neutral feature naming and document interpretation before modeling.","docs/shipping_product_features.md"
shipping date (DateOrders),shipping_date_DateOrders,shipping_actual,after_shipment,forbidden,forbidden,allowed,dashboard_only,"Shipment timestamp is known after order creation and may encode fulfillment timing.","Use only for operational reporting and outcome audit, not predictive features.","docs/ao1_target_definition.md"
Shipping Mode,Shipping_Mode,shipping_planned,before_dispatch,allowed,allowed,allowed,direct_candidate,"Shipping mode is selected/planned before dispatch and has clear operational meaning.","Can support shipping mode and speed-tier features.","docs/leakage_control_plan.md"
"""

EXPECTED_COLUMNS = (
    "source_column",
    "silver_column",
    "semantic_group",
    "availability_timing",
    "ao1_policy",
    "ao2_policy",
    "dashboard_policy",
    "modeling_use",
    "rationale",
    "derived_feature_guidance",
    "related_document",
)

ALLOWED_AVAILABILITY_TIMING = {
    "order_creation",
    "before_dispatch",
    "after_shipment",
    "after_delivery",
    "after_order_review",
    "target_or_outcome",
    "sensitive_identifier",
    "descriptive_only",
}

ALLOWED_POLICY_VALUES = {"allowed", "review", "forbidden", "target"}
ALLOWED_DASHBOARD_POLICY_VALUES = {"allowed", "review", "forbidden"}
ALLOWED_MODELING_USE_VALUES = {
    "direct_candidate",
    "derived_only",
    "training_only_aggregate",
    "join_key_only",
    "review",
    "dashboard_only",
    "exclude",
}


@dataclass(frozen=True)
class FeatureAvailabilityMapConfig:
    """Configuration for registering the feature availability map."""

    input_csv_path: Path = FEATURE_MAP_INPUT_PATH
    volume_csv_path: Path = FEATURE_MAP_VOLUME_CSV_PATH
    delta_output_path: str = FEATURE_MAP_DELTA_OUTPUT_PATH
    write_format: str = "delta"
    write_mode: str = "overwrite"
    expected_row_count: int = EXPECTED_ROW_COUNT


def configure_logging() -> logging.Logger:
    """Configure console logging for Databricks job output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.feature_availability_map")


def get_spark_session() -> SparkSession:
    """Return the active Databricks Spark session."""
    return SparkSession.builder.getOrCreate()


def validate_volume_path(path: str, field_name: str) -> None:
    """Validate that a target path uses Unity Catalog Volumes."""
    if path.startswith(DISABLED_PUBLIC_DBFS_PREFIXES):
        raise ValueError(
            f"{field_name} points to the disabled public DBFS root: {path}. "
            "Use Unity Catalog Volumes under /Volumes/workspace/default/raw_data/."
        )

    if not path.startswith("/Volumes/"):
        raise ValueError(
            f"{field_name} must use a Unity Catalog Volume path. Received: {path}"
        )


def validate_paths(config: FeatureAvailabilityMapConfig) -> None:
    """Validate configured source and target paths."""
    validate_volume_path(str(config.volume_csv_path), "volume_csv_path")
    validate_volume_path(config.delta_output_path, "delta_output_path")


def get_feature_map_csv_text(config: FeatureAvailabilityMapConfig) -> str:
    """Return the feature map CSV text from the repo file or embedded fallback."""
    if config.input_csv_path.exists():
        return config.input_csv_path.read_text(encoding="utf-8")

    return EMBEDDED_FEATURE_AVAILABILITY_MAP_CSV


def read_feature_map_rows(csv_text: str) -> list[dict[str, str]]:
    """Read the feature availability map CSV text as dictionaries."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    return rows


def validate_feature_map_rows(
    rows: list[dict[str, str]],
    config: FeatureAvailabilityMapConfig,
) -> None:
    """Validate the feature availability map schema and controlled values."""
    if len(rows) != config.expected_row_count:
        raise ValueError(
            f"Unexpected feature map row count. Expected {config.expected_row_count}, "
            f"found {len(rows)}."
        )

    if not rows:
        raise ValueError("Feature availability map is empty.")

    actual_columns = tuple(rows[0].keys())
    if actual_columns != EXPECTED_COLUMNS:
        raise ValueError(
            f"Unexpected feature map columns. Expected {EXPECTED_COLUMNS}, "
            f"found {actual_columns}."
        )

    source_columns = [row["source_column"] for row in rows]
    if len(set(source_columns)) != len(source_columns):
        duplicate_columns = sorted(
            {
                source_column
                for source_column in source_columns
                if source_columns.count(source_column) > 1
            }
        )
        raise ValueError(f"Duplicate source columns found: {duplicate_columns}")

    rows_with_blank_cells = [
        index
        for index, row in enumerate(rows, start=2)
        if any(value is None or value == "" for value in row.values())
    ]
    if rows_with_blank_cells:
        raise ValueError(
            "Feature availability map contains blank cells on CSV rows: "
            f"{rows_with_blank_cells}"
        )

    invalid_values: list[tuple[str, str, str]] = []

    for row in rows:
        source_column = row["source_column"]

        if row["availability_timing"] not in ALLOWED_AVAILABILITY_TIMING:
            invalid_values.append(
                (source_column, "availability_timing", row["availability_timing"])
            )

        if row["ao1_policy"] not in ALLOWED_POLICY_VALUES:
            invalid_values.append((source_column, "ao1_policy", row["ao1_policy"]))

        if row["ao2_policy"] not in ALLOWED_POLICY_VALUES:
            invalid_values.append((source_column, "ao2_policy", row["ao2_policy"]))

        if row["dashboard_policy"] not in ALLOWED_DASHBOARD_POLICY_VALUES:
            invalid_values.append(
                (source_column, "dashboard_policy", row["dashboard_policy"])
            )

        if row["modeling_use"] not in ALLOWED_MODELING_USE_VALUES:
            invalid_values.append((source_column, "modeling_use", row["modeling_use"]))

    if invalid_values:
        raise ValueError(f"Invalid controlled values found: {invalid_values}")


def write_csv_to_volume(csv_text: str, config: FeatureAvailabilityMapConfig) -> None:
    """Write the reference CSV to the project Databricks Volume."""
    config.volume_csv_path.parent.mkdir(parents=True, exist_ok=True)
    config.volume_csv_path.write_text(csv_text, encoding="utf-8", newline="")


def create_feature_map_dataframe(
    spark: SparkSession,
    rows: list[dict[str, str]],
    config: FeatureAvailabilityMapConfig,
) -> DataFrame:
    """Create a Spark DataFrame from validated feature map rows."""
    schema = StructType(
        [StructField(column_name, StringType(), nullable=False) for column_name in EXPECTED_COLUMNS]
    )

    ordered_rows = [
        tuple(row[column_name] for column_name in EXPECTED_COLUMNS)
        for row in rows
    ]

    return (
        spark.createDataFrame(ordered_rows, schema=schema)
        .withColumn("_registered_timestamp", current_timestamp())
        .withColumn("_source_file", lit(str(config.volume_csv_path)))
    )


def write_delta(df: DataFrame, config: FeatureAvailabilityMapConfig) -> None:
    """Write the feature availability map as a Delta reference table."""
    (
        df.write.format(config.write_format)
        .mode(config.write_mode)
        .option("overwriteSchema", "true")
        .save(config.delta_output_path)
    )


def validate_delta_output(
    spark: SparkSession,
    config: FeatureAvailabilityMapConfig,
) -> None:
    """Validate the written Delta feature availability map."""
    feature_map_df = spark.read.format(config.write_format).load(config.delta_output_path)
    row_count = feature_map_df.count()

    if row_count != config.expected_row_count:
        raise ValueError(
            f"Unexpected Delta feature map row count. "
            f"Expected {config.expected_row_count}, found {row_count}."
        )

    required_columns = set(EXPECTED_COLUMNS + ("_registered_timestamp", "_source_file"))
    missing_columns = sorted(required_columns.difference(feature_map_df.columns))

    if missing_columns:
        raise ValueError(
            f"Missing columns in Delta feature availability map: {missing_columns}"
        )


def run_feature_availability_map_registration(
    config: FeatureAvailabilityMapConfig,
    logger: logging.Logger,
) -> None:
    """Register the feature availability map CSV and Delta reference outputs."""
    spark = get_spark_session()

    logger.info("Starting feature availability map registration.")
    logger.info("Input CSV path: %s", config.input_csv_path)
    logger.info("Volume CSV path: %s", config.volume_csv_path)
    logger.info("Delta output path: %s", config.delta_output_path)

    try:
        validate_paths(config)
        logger.info("Path validation completed successfully.")

        csv_text = get_feature_map_csv_text(config)
        rows = read_feature_map_rows(csv_text)
        validate_feature_map_rows(rows, config)
        logger.info("Feature availability map CSV validation completed successfully.")

        write_csv_to_volume(csv_text, config)
        logger.info("Feature availability map CSV written to Volume successfully.")

        feature_map_df = create_feature_map_dataframe(spark, rows, config)
        write_delta(feature_map_df, config)
        logger.info("Feature availability map Delta write completed successfully.")

        validate_delta_output(spark, config)
        logger.info("Feature availability map Delta validation completed successfully.")
        logger.info("Feature availability map registration completed successfully.")

    except Exception:
        logger.exception("Feature availability map registration failed.")
        raise


def main() -> None:
    """Run the feature availability map registration with default configuration."""
    logger = configure_logging()
    config = FeatureAvailabilityMapConfig()
    run_feature_availability_map_registration(config, logger)


if __name__ == "__main__":
    main()
