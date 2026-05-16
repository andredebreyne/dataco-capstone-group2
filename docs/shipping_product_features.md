# Shipping and Product Features

Task: `[W2][P0][#4] Feature engineering: shipping and product variables`

Issue: `#13`

## Purpose

This document defines the shipping, product, and order-composition features created for the DataCo Capstone project. These features support downstream AO1 late-delivery modeling, AO2 profitability modeling, and AO3 prioritization while respecting the project decision-time and leakage-control rules.

The feature engineering job uses only fields that are expected to be known before dispatch, such as scheduled shipping days, shipping mode, product category, department, product identifiers, product price, item quantity, discounts, and order item totals.

The job does not derive features from actual shipping duration, shipping date, delivery status, late-delivery target values, order status outcomes, or profit target fields. The output table includes only traceability keys, approved lineage fields, and generated shipping/product features.

This output is a shipping/product candidate feature table, not the final AO1 or AO2 modeling matrix. Later Gold transformations must still apply the feature availability map, AO2 target-reconstruction policy, leakage-control rules, and train-only preprocessing before model training.

Finalized first-pass Gold decisions for product-level descriptors and AO2
commercial predictors are documented in `docs/pre_gold_modeling_decisions.md`.

## Input and Output

Input Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_silver
```

Output Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_shipping_product_features
```

Script:

```text
src/data_engineering/engineer_shipping_product_features.py
```

## Feature Contract

The output keeps these key and lineage columns for traceability:

| Column | Type | Purpose |
| --- | --- | --- |
| `Order_Id` | integer | Order-level join and traceability key. |
| `Order_Item_Id` | integer | Order-item-level join and traceability key. |
| `order_date_DateOrders` | timestamp | Decision-time timestamp used for chronological validation and downstream splits. |
| `_ingest_timestamp` | timestamp | Bronze ingestion lineage. |
| `_source_file` | string | Bronze source-file lineage. |
| `_silver_processed_timestamp` | timestamp | Silver processing lineage. |

Generated shipping and product features:

| Feature | Type | Source | Intended use |
| --- | --- | --- | --- |
| `scheduled_shipping_days` | integer | `Days_for_shipment_scheduled` | Planned service-level duration known before shipment. |
| `shipping_speed_tier` | string | `Days_for_shipment_scheduled` | Groups planned shipping speed into expedited, standard, and economy tiers. |
| `shipping_mode_normalized` | string | `Shipping_Mode` | Stable token for the selected shipping mode. |
| `is_same_day_or_next_day_shipping` | integer | `Days_for_shipment_scheduled` | Flags urgent fulfillment promises. |
| `is_standard_shipping` | integer | `Shipping_Mode` | Flags Standard Class orders for baseline operations comparisons. |
| `product_category_key` | string | `Category_Id`, `Category_Name` | Creates a stable category-level descriptor for analysis and later encoding review. |
| `product_department_key` | string | `Department_Id`, `Department_Name` | Creates a stable department-level descriptor for analysis and later encoding review. |
| `product_catalog_key` | string | `Product_Card_Id`, `Product_Category_Id`, `Order_Item_Cardprod_Id` | Creates a product catalog composition key for traceability and review. |
| `product_name_normalized` | string | `Product_Name` | Normalizes product names for review and possible grouping. |
| `product_status_flag` | integer | `Product_Status` | Preserves the source product status indicator with a neutral feature name. |
| `product_list_price` | double | `Product_Price` | Captures the product-level listed price. |
| `order_item_quantity` | integer | `Order_Item_Quantity` | Captures item-level order composition. |
| `item_unit_price` | double | `Order_Item_Product_Price` | Captures product price at order-item level. |
| `item_discount_amount` | double | `Order_Item_Discount` | Captures discount amount known at order time. |
| `item_discount_rate` | double | `Order_Item_Discount_Rate` | Captures discount intensity known at order time. |
| `item_gross_sales_estimate` | double | `Order_Item_Product_Price`, `Order_Item_Quantity` | Estimates pre-discount item value. |
| `item_net_sales_amount` | double | `Order_Item_Total` | Captures net item value after discount. |
| `item_discount_share_of_gross` | double | `Order_Item_Discount`, `Order_Item_Product_Price`, `Order_Item_Quantity` | Captures discount share relative to estimated gross item value. |
| `_shipping_product_features_processed_timestamp` | timestamp | processing metadata | Records when the feature table was generated. |

## Leakage-Control Assessment

These features are designed to be decision-time valid because they rely on planned service details and product/order-item information expected to be known before dispatch.

Forbidden inputs for this task include:

- `Days_for_shipping_real`
- `Delivery_Status`
- `Late_delivery_risk`
- `shipping_date_DateOrders`
- `Order_Status`
- `Order_Profit_Per_Order`
- `Benefit_per_order`
- `Order_Item_Profit_Ratio`

The output intentionally does not retain all original Silver columns. This reduces the chance of accidentally carrying target, post-shipment, or direct profit-derived fields into downstream modeling. Modeling feature-selection code must still apply AO1 and AO2 leakage-control rules before training.

Financial order-composition fields in this table are candidate/review features, not automatically approved AO2 predictors. Fields such as `item_unit_price`, `item_discount_amount`, `item_discount_rate`, `item_net_sales_amount`, `item_gross_sales_estimate`, and `item_discount_share_of_gross` must still be checked against the AO2 target-reconstruction policy before final AO2 feature inclusion. See `docs/ao2_target_policy.md` and `docs/leakage_control_plan.md`.

## High-Cardinality Review

Some product fields may create high-cardinality features, especially `product_catalog_key` and `product_name_normalized`. These fields are retained for review and traceability, but they should not be blindly one-hot encoded in modeling pipelines.

The feature job logs distinct counts for `shipping_mode_normalized`, `product_category_key`, `product_department_key`, `product_catalog_key`, and `product_name_normalized` after the Databricks run. These counts are evidence for later review only; this PR does not group, encode, collapse categories, apply frequency thresholds, or build historical aggregates.

Before modeling, high-cardinality fields must be classified as:

- `Allowed`: used directly or with a documented deterministic grouping
- `Review`: requires additional grouping, frequency thresholding, or target-safe historical aggregation
- `Forbidden`: excluded from modeling due to leakage, instability, or poor operational meaning

Any learned encoding or historical aggregate must be fit on training data only.

## Validation Rules

The feature engineering job validates:

- Silver input path uses Unity Catalog Volumes
- required Silver input columns exist
- input row count matches `180,519`
- output row count matches `180,519`
- all expected feature columns are present
- no unexpected original Silver columns are present in the feature output
- required generated features do not contain null values
- generated feature ranges and domains are valid, including non-negative scheduled days, binary indicator flags, positive order-item quantity, non-negative price/sales/discount amounts, discount rates between 0 and 1, and discount share between 0 and 1 when present
- forbidden target, profit, or post-shipment fields are not present in the feature output

## Execution Order

Run the pipeline in this order:

1. `src/data_engineering/ingest_bronze.py`
2. `src/data_engineering/clean_silver.py`
3. `src/data_engineering/engineer_shipping_product_features.py`

The Silver cleaning job must complete successfully before shipping and product feature engineering runs.

## Assumptions and Limitations

- `Days_for_shipment_scheduled` is treated as planned service information known before dispatch.
- `Shipping_Mode` is treated as the selected shipping service known before dispatch.
- Product and order-item fields are treated as order-time commercial information.
- Discount and sales fields are retained for feature engineering, but AO2 modeling must still confirm that selected financial predictors do not reconstruct the profit target.
- Learned encodings, frequency thresholds, and historical aggregates are intentionally deferred to later modeling pipelines and must be fit on training data only.
