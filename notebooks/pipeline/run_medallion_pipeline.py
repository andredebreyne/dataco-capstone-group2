# Databricks notebook source
"""Run the DataCo medallion pipeline in Databricks.

This notebook is intentionally thin. Reusable cleaning and feature engineering
logic lives in /src; this notebook only orchestrates the existing jobs in the
expected order and exports a local Silver CSV clone for local EDA notebooks.
"""

# COMMAND ----------

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any


# Keep these switches simple for Databricks review runs.
RUN_REFERENCE_REGISTRATION = True
RUN_BRONZE_INGESTION = True
RUN_SILVER_CLEANING = True
RUN_ORDER_TIME_FEATURES = True
RUN_SHIPPING_PRODUCT_FEATURES = True
RUN_CUSTOMER_REGIONAL_FEATURES = True
EXPORT_LOCAL_SILVER_CSV = True

LOCAL_SILVER_CSV_RELATIVE_PATH = Path("data/silver/dataco_orders_silver.csv")


def find_repo_root() -> Path:
    """Find the repo root from Databricks Repos, local execution, or an env var."""
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
            if (candidate / "data" / "references" / "feature_availability_map.csv").exists():
                return candidate

    raise FileNotFoundError(
        "Could not find repo root. Set DATACO_REPO_ROOT to the repository checkout path."
    )


REPO_ROOT = find_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print(f"Repo root: {REPO_ROOT}")


# COMMAND ----------

from src.data_engineering.clean_silver import (  # noqa: E402
    SilverCleaningConfig,
    configure_logging as configure_silver_logging,
    run_silver_cleaning,
)
from src.data_engineering.engineer_customer_regional_features import (  # noqa: E402
    CustomerRegionalFeatureConfig,
    configure_logging as configure_customer_regional_logging,
    run_customer_regional_feature_engineering,
)
from src.data_engineering.engineer_order_time_features import (  # noqa: E402
    OrderTimeFeatureConfig,
    configure_logging as configure_order_time_logging,
    run_order_time_feature_engineering,
)
from src.data_engineering.engineer_shipping_product_features import (  # noqa: E402
    ShippingProductFeatureConfig,
    configure_logging as configure_shipping_product_logging,
    run_shipping_product_feature_engineering,
)
from src.data_engineering.ingest_bronze import (  # noqa: E402
    BronzeIngestionConfig,
    configure_logging as configure_bronze_logging,
    run_bronze_ingestion,
)
from src.data_engineering.register_feature_availability_map import (  # noqa: E402
    FeatureAvailabilityMapConfig,
    configure_logging as configure_feature_map_logging,
    run_feature_availability_map_registration,
)


def pipeline_logger() -> logging.Logger:
    """Return a small orchestration logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("dataco.medallion_pipeline")


def get_spark_session() -> Any:
    """Return the active Databricks Spark session."""
    active_spark = globals().get("spark")
    if active_spark is not None:
        return active_spark

    from pyspark.sql import SparkSession

    return SparkSession.builder.getOrCreate()


def export_silver_delta_to_local_csv(
    silver_delta_path: str,
    output_csv_path: Path,
) -> None:
    """Export the Silver Delta table to the gitignored local CSV clone path.

    This is for local EDA/review convenience only. The Delta Silver output
    remains the pipeline source of truth.
    """
    spark_session = get_spark_session()
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    silver_df = spark_session.read.format("delta").load(silver_delta_path)
    row_count = silver_df.count()

    if output_csv_path.exists():
        output_csv_path.unlink()

    silver_df.toPandas().to_csv(output_csv_path, index=False)
    print(f"Exported {row_count:,} Silver rows to {output_csv_path}")


# COMMAND ----------

logger = pipeline_logger()

if RUN_REFERENCE_REGISTRATION:
    logger.info("Registering feature availability map.")
    run_feature_availability_map_registration(
        FeatureAvailabilityMapConfig(input_csv_path=REPO_ROOT / "data/references/feature_availability_map.csv"),
        configure_feature_map_logging(),
    )

if RUN_BRONZE_INGESTION:
    logger.info("Running Bronze ingestion.")
    run_bronze_ingestion(BronzeIngestionConfig(), configure_bronze_logging())

if RUN_SILVER_CLEANING:
    logger.info("Running Silver cleaning.")
    run_silver_cleaning(SilverCleaningConfig(), configure_silver_logging())

if RUN_ORDER_TIME_FEATURES:
    logger.info("Running order-time feature engineering.")
    run_order_time_feature_engineering(OrderTimeFeatureConfig(), configure_order_time_logging())

if RUN_SHIPPING_PRODUCT_FEATURES:
    logger.info("Running shipping/product feature engineering.")
    run_shipping_product_feature_engineering(
        ShippingProductFeatureConfig(),
        configure_shipping_product_logging(),
    )

if RUN_CUSTOMER_REGIONAL_FEATURES:
    logger.info("Running customer/regional feature engineering.")
    run_customer_regional_feature_engineering(
        CustomerRegionalFeatureConfig(),
        configure_customer_regional_logging(),
    )

if EXPORT_LOCAL_SILVER_CSV:
    logger.info("Exporting local Silver CSV clone.")
    export_silver_delta_to_local_csv(
        SilverCleaningConfig().silver_output_path,
        REPO_ROOT / LOCAL_SILVER_CSV_RELATIVE_PATH,
    )

logger.info("DataCo medallion pipeline notebook completed.")

