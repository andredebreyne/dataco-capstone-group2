# AO1 Gold Analytical Table

Issue: `#22`

## Purpose

The AO1 Gold analytical table is the first model-ready dataset for predicting
late-delivery risk. It is designed for chronological split and downstream AO1
modeling while preserving decision-time integrity.

The table is produced by:

```text
src/data_engineering/build_gold_ao1_table.py
```

Default Delta output path:

```text
/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_analytical_table
```

## Input Delta Paths

The builder uses these default Delta paths unless the corresponding
`DATACO_*` environment variable overrides them:

| Table | Default path |
| --- | --- |
| Silver orders | `/Volumes/workspace/default/raw_data/silver/dataco_orders_silver` |
| Order-time features | `/Volumes/workspace/default/raw_data/silver/dataco_orders_order_time_features` |
| Shipping/product features | `/Volumes/workspace/default/raw_data/silver/dataco_shipping_product_features` |
| Customer/regional features | `/Volumes/workspace/default/raw_data/silver/dataco_customer_regional_features` |
| AO1 Gold output | `/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_analytical_table` |

## Primary Population Rule

The table applies the approved first-pass AO1 population policy from
`docs/pre_gold_modeling_decisions.md` and `docs/ao1_target_definition.md`.

Included records represent normal fulfilled or fulfillment-eligible orders.

Excluded records:

- `Delivery_Status = Shipping canceled`
- `Order_Status = CANCELED`
- `Order_Status = SUSPECTED_FRAUD`

These fields are used only to filter the primary AO1 population and are not
written to the Gold analytical table.

Primary AO1 Gold starts from 180,519 Silver rows and applies the approved
fulfilled/fulfillment-eligible population rule. The filter excludes 7,754
records associated with shipping-canceled, canceled, or suspected-fraud cases,
producing 172,765 rows in the primary AO1 Gold table. Excluded records are not
treated as normal non-late deliveries and should be retained only for audit,
sensitivity, or descriptive dashboard use.

Expected primary AO1 Gold row count:

```text
172,765
```

## Included Columns

### Lineage and Split Columns

These columns support traceability and the future chronological split. They are
not model predictors.

| Column | Purpose |
| --- | --- |
| `Order_Id` | Order-level traceability and join validation. |
| `Order_Item_Id` | Order-item traceability and join validation. |
| `order_date_DateOrders` | Chronological split and order-time lineage. |
| `_gold_ao1_processed_timestamp` | Gold processing audit timestamp. |

### Target

| Column | Purpose |
| --- | --- |
| `Late_delivery_risk` | Official AO1 binary target. |

`Late_delivery_risk` must be used only as the target and never as a predictor.

### Decision-Time Predictors

| Feature group | Included columns |
| --- | --- |
| Conditional transaction context | `Type` |
| Order-time calendar | `order_year`, `order_quarter`, `order_month`, `order_week_of_year`, `order_day_of_month`, `order_day_of_week`, `order_hour`, `order_is_weekend`, `order_season` |
| Planned shipping service | `scheduled_shipping_days`, `shipping_speed_tier`, `shipping_mode_normalized`, `is_same_day_or_next_day_shipping`, `is_standard_shipping` |
| Product mix | `product_category_key`, `product_department_key` |
| Coarse customer and regional context | `customer_segment_normalized`, `customer_country_normalized`, `customer_state_normalized`, `market_normalized`, `order_country_normalized`, `order_region_normalized`, `order_state_normalized` |
| Availability and match flags | `customer_zipcode_available`, `order_zipcode_available`, `customer_order_country_match`, `customer_order_state_match`, `geo_coordinates_available` |

The `Type` field is included under the documented team assumption that it
represents transaction or payment type known at or near order creation. It must
be reviewed during model interpretation and removed if later evidence shows it
is created after payment review, fraud review, or order processing.

## Excluded Fields

The AO1 Gold table explicitly excludes:

- AO1 target proxies and post-delivery fields:
  - `Delivery_Status`
  - `Days_for_shipping_real`
  - `shipping_date_DateOrders`
- Order exception and outcome fields:
  - `Order_Status`
- AO2 target, profit, sales, and realized margin fields:
  - `Order_Profit_Per_Order`
  - `Benefit_per_order`
  - `Order_Item_Profit_Ratio`
  - `Sales`
  - `Sales_per_customer`
  - `Order_Item_Total`
- Personal identifiers and sensitive customer fields:
  - `Customer_Email`
  - `Customer_Fname`
  - `Customer_Lname`
  - `Customer_Password`
  - `Customer_Street`
- Raw customer and order identifiers that are not needed as row keys:
  - `Customer_Id`
  - `Order_Customer_Id`
- Granular geography and precise location fields:
  - `Customer_City`
  - `Order_City`
  - `Customer_Zipcode`
  - `Order_Zipcode`
  - `Latitude`
  - `Longitude`
  - `customer_city_normalized`
  - `order_city_normalized`
  - `customer_region_key`
  - `order_region_key`
  - `latitude_rounded`
  - `longitude_rounded`
- Product identifiers, product names, and granular catalog keys:
  - `Product_Card_Id`
  - `Order_Item_Cardprod_Id`
  - `Product_Category_Id`
  - `Product_Name`
  - `product_catalog_key`
  - `product_name_normalized`
  - `product_status_flag`
- Commercial price, discount, and value fields:
  - `product_list_price`
  - `item_unit_price`
  - `item_discount_amount`
  - `item_discount_rate`
  - `item_gross_sales_estimate`
  - `item_net_sales_amount`
  - `item_discount_share_of_gross`
- Product asset or descriptive-only fields:
  - `Product_Image`
  - `Product_Description`

These exclusions follow the leakage-control plan, AO1 target definition,
feature availability map, and pre-Gold modeling decisions.

## Validation Rules

The builder and validation script enforce:

- exact expected primary AO1 row count;
- one row per `Order_Id`, `Order_Item_Id`, and `order_date_DateOrders`;
- complete AO1 target with only `0` and `1` values;
- required predictor columns present and non-null;
- forbidden leakage and deferred fields absent;
- key timestamp and feature schema types consistent with downstream modeling.

Validation script:

```text
tests/data_validation/test_gold_ao1_table.py
```

## Downstream Modeling Notes

The AO1 Gold table does not apply imputation, scaling, encoding, resampling,
class weighting, model training, threshold selection, or SHAP/explainability.

Those steps must be fit only on training data after the official chronological
split. Categorical variables in this table are intentionally left as strings so
the modeling pipeline can apply train-only encoding.
