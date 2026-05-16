# Silver Schema Data Dictionary

Issue: `[W2][P1][#7] Document the Silver schema with a data dictionary #16`

## Purpose

The Silver schema data dictionary documents the cleaned DataCo order fields produced by `src/data_engineering/clean_silver.py`. It gives reviewers one lightweight reference for Silver column names, data types, source lineage, cleaning notes, business meaning, approved usage notes, leakage restrictions, target relevance, and quality caveats.

The structured artifact is stored at:

```text
data/references/silver_schema_data_dictionary.csv
```

## Relationship to Silver Cleaning Rules

The dictionary describes the output schema from `docs/silver_cleaning_rules.md`. Silver applies deterministic cleaning only:

- canonicalized Bronze column names
- blank-string normalization to null
- string trimming and whitespace cleanup
- integer, double, and timestamp casting
- preservation of Bronze lineage columns
- addition of `_silver_processed_timestamp`

Silver does not perform fitted preprocessing, imputation, encoding, resampling, feature selection, Gold feature engineering, or model training.

## Relationship to Leakage Screening

The dictionary aligns each non-lineage Silver field with `data/references/leakage_conceptual_screening.csv` where possible. Usage columns in the dictionary are intentionally conservative:

- `allowed` fields are still subject to final Gold selection and train-only preprocessing.
- `conditional` fields require documented review before AO1 or AO2 modeling use.
- `forbidden` fields must not be used as predictive inputs.
- `target` fields are target-only and must never be predictors.
- `dashboard_only` and `restricted` fields must stay separate from predictive modeling matrices.

The dictionary does not replace `docs/leakage_control_plan.md`, `docs/feature_availability_map.md`, `docs/ao1_target_definition.md`, or `docs/ao2_target_policy.md`.

Finalized first-pass Gold modeling decisions are documented in
`docs/pre_gold_modeling_decisions.md`.

## How to Use Before Gold and Modeling

Before building Gold analytical tables or AO1/AO2 feature matrices, reviewers should use the dictionary to confirm:

- every Silver column has a documented source and type
- AO1 target and post-delivery fields are excluded from AO1 predictors
- AO2 profit targets, profit proxies, and reconstruction-risk fields are excluded or explicitly reviewed
- dashboard-only fields are not mixed into predictive inputs
- lineage fields are retained for audit only

The Silver layer is not a final AO1 or AO2 modeling matrix. It is a cleaned, typed source layer that still contains targets, outcomes, identifiers, dashboard-only fields, and fields requiring Gold-stage review.

## Validation

The lightweight validator is stored at:

```text
tests/data_validation/validate_silver_schema_dictionary.py
```

Run it from the repository root. In a Databricks notebook, set `DATACO_REPO_ROOT` first if the notebook's current working directory is not the repo checkout.

## Key Field Groups

Identifiers and keys:
`Order_Id`, `Order_Item_Id`, customer IDs, product IDs, category IDs, and department IDs support traceability or reviewed grouping decisions. Raw order and item IDs are not predictive inputs.

Dates and timestamps:
`order_date_DateOrders` is available at order creation and supports chronological splitting or derived calendar features. `shipping_date_DateOrders` is post-shipment and dashboard/audit only.

Customer and geography fields:
Customer segment, country, state, market, order country, order region, and order state are generally Gold candidates. City, postal code, coordinates, and customer identifiers require review because of cardinality, privacy, stability, or grouping concerns.

Shipping and delivery fields:
`Days_for_shipment_scheduled` and `Shipping_Mode` are planned-service fields available before dispatch. `Days_for_shipping_real` and `Delivery_Status` are post-delivery outcome fields and must not be AO1 or AO2 predictors.

Product and order item fields:
Category, department, product name, product IDs, quantity, and product status describe order composition or catalog context. High-cardinality product fields and duplicate category fields require Gold-stage review.

Financial and profit fields:
Sales, discounts, prices, and order totals are order-time commercial fields but remain conditional for AO2 because they can be redundant or contribute to target reconstruction. `Order_Profit_Per_Order` is the AO2 target. `Benefit_per_order` and `Order_Item_Profit_Ratio` are profit outcome/proxy fields for audit or descriptive use only.

Target and outcome fields:
`Late_delivery_risk` is the AO1 target. `Order_Profit_Per_Order` is the AO2 target. Delivery outcomes, actual shipping duration, shipment timestamp, order status, and profit proxies are not predictive inputs.

Lineage fields:
`_ingest_timestamp`, `_source_file`, and `_silver_processed_timestamp` are retained for reproducibility, rerun checks, and audit traceability only.

## Assumptions and Limitations

- Business meanings are based on the local DataCo metadata file and existing leakage/availability artifacts.
- Fields absent from the leakage conceptual screening should not be silently approved in future updates.
- Conditional fields remain unresolved until Gold/modeling review documents the intended use.
- The dictionary documents Silver schema policy; it does not create Gold features, train models, select thresholds, or certify model-ready feature lists.
