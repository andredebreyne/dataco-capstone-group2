# Silver Cleaning Rules

Task: `[W2][P0][#2] Silver: clean missing values, data types, and encoding`

Issue: `#11`

## Purpose

This document defines the deterministic Silver-layer cleaning rules for the DataCo structured supply-chain dataset. The Silver layer prepares typed, standardized, analysis-ready records while preserving methodological controls required for later modeling.

Silver cleaning must not perform model-training preprocessing such as statistical imputation, scaling, resampling, target encoding, one-hot encoding, or fitted categorical encoding. Those steps must be fit on training data only in downstream modeling pipelines.

## Inputs and Outputs

Input Delta path:

```text
/Volumes/workspace/default/raw_data/bronze/dataco_supply_chain
```

Silver output Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_silver
```

Silver quality report Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_silver_quality_report
```

Script:

```text
src/data_engineering/clean_silver.py
```

## Cleaning Rules

The Silver job applies only deterministic, non-fitted transformations:

- canonicalize Bronze column names for downstream compatibility
- trim string fields
- convert blank strings to null
- collapse repeated whitespace in categorical fields
- cast integer-like fields to integer
- cast decimal-like fields to double
- parse `order_date_DateOrders` and `shipping_date_DateOrders` as timestamps
- preserve Bronze lineage columns
- append `_silver_processed_timestamp`

No rows are intentionally dropped in this Silver step. If future rules require row exclusions, the exclusion rule and row count must be documented in the related pull request.

## Missing Values

Silver converts blank strings to null but does not fill missing values with learned or statistical values.

Known missing-value patterns from source verification include:

- `Product_Description`: blank for all rows
- `Order_Zipcode`: high missingness
- `Customer_Lname`: limited missingness
- `Customer_Zipcode`: limited missingness

These fields remain available for analysis, but modeling pipelines must decide whether to exclude, impute, flag, or otherwise handle them using training-only preprocessing.

## Type Rules

The Bronze layer stores source fields as strings. Silver applies approved analytical types:

- IDs, counts, binary flags, quantities, and scheduled/actual day counts become integers.
- Financial fields, discounts, rates, prices, sales, profit, latitude, and longitude become doubles.
- DataCo order and shipping date fields become timestamps.
- Categorical and descriptive fields remain strings.

## Encoding Boundary

Silver does not perform fitted encoding.

Allowed in Silver:

- string normalization
- deterministic type casting
- timestamp parsing
- null standardization

Not allowed in Silver:

- one-hot encoding
- label/index encoding
- target encoding
- scaling
- SMOTE or other resampling
- model-specific imputers

These modeling transformations must be implemented later with train/validation/test separation.

## Leakage-Control Boundary

Silver may retain outcome and post-shipment fields as cleaned columns for validation and descriptive auditing, but modeling feature sets must follow:

- `docs/leakage_control_plan.md`
- `docs/ao1_target_definition.md`
- `docs/ao2_target_policy.md`

Forbidden predictor fields must not enter AO1 or AO2 feature matrices, even if they exist in the Silver table.

## Validation

The Silver job validates:

- required Bronze columns exist
- output row count matches the verified source row count
- lineage columns are present
- quality metrics are written to the quality-report Delta path

The quality report records:

- Bronze row count
- Silver row count
- dropped row count
- missing-value counts for important fields
- integer cast failures
- decimal cast failures
- timestamp parse failures
- final Silver column count

## Execution Order

Run the pipeline in this order:

1. `src/data_engineering/ingest_bronze.py`
2. `src/data_engineering/clean_silver.py`

The Bronze ingestion must complete successfully before Silver cleaning runs.
