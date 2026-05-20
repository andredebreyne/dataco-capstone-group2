# AO2 Gold Analytical Table

Issue: `#23`

## Purpose

The AO2 Gold analytical table is the first model-ready dataset for predicting
order profitability. It is designed for chronological split and downstream AO2
regression modeling while avoiding target reconstruction from duplicate profit,
realized margin, sales, and order-value fields.

The table is produced by:

```text
src/data_engineering/build_gold_ao2_table.py
```

Default Delta output path:

```text
/Volumes/workspace/default/raw_data/gold/ao2_profitability_analytical_table
```

## Target

| Column | Purpose |
| --- | --- |
| `Order_Profit_Per_Order` | Official AO2 regression target. |

`Order_Profit_Per_Order` must be used only as the target and never as a
predictor. Direct transformations of the target are also forbidden.

## Included Columns

### Lineage and Split Columns

These columns support traceability and the future chronological split. They are
not model predictors.

| Column | Purpose |
| --- | --- |
| `Order_Id` | Order-level traceability and join validation. |
| `Order_Item_Id` | Order-item traceability and join validation. |
| `order_date_DateOrders` | Chronological split and order-time lineage. |
| `_gold_ao2_processed_timestamp` | Gold processing audit timestamp. |

### Decision-Time Predictors

| Feature group | Included columns |
| --- | --- |
| Conditional transaction context | `Type` |
| Order-time calendar | `order_year`, `order_quarter`, `order_month`, `order_week_of_year`, `order_day_of_month`, `order_day_of_week`, `order_hour`, `order_is_weekend`, `order_season` |
| Planned shipping service | `scheduled_shipping_days`, `shipping_speed_tier`, `shipping_mode_normalized`, `is_same_day_or_next_day_shipping`, `is_standard_shipping` |
| Product mix | `product_category_key`, `product_department_key` |
| Conservative commercial predictors | `item_unit_price`, `item_discount_rate`, `order_item_quantity` |
| Coarse customer and regional context | `customer_segment_normalized`, `customer_country_normalized`, `customer_state_normalized`, `market_normalized`, `order_country_normalized`, `order_region_normalized`, `order_state_normalized` |
| Availability and match flags | `customer_zipcode_available`, `order_zipcode_available`, `customer_order_country_match`, `customer_order_state_match`, `geo_coordinates_available` |

The commercial predictor set follows `docs/ao2_target_policy.md` and
`docs/pre_gold_modeling_decisions.md`: use one item-level price representation,
one discount-rate representation, and one quantity representation.

### AO3 Support Column

| Column | Purpose |
| --- | --- |
| `ao3_order_value` | Support denominator for future AO3 predicted margin construction. |

`ao3_order_value` is derived from `Order_Item_Total` and retained only as an
AO3 support field. It is not part of the AO2 predictor set.

## Excluded Fields

The AO2 Gold table explicitly excludes:

- AO2 duplicate target and realized margin fields:
  - `Benefit_per_order`
  - `Order_Item_Profit_Ratio`
- Raw sales, duplicate value, and total fields:
  - `Sales`
  - `Sales_per_customer`
  - `Order_Item_Total`
- Duplicate price, discount, and derived commercial fields:
  - `Product_Price`
  - `product_list_price`
  - `item_discount_amount`
  - `item_gross_sales_estimate`
  - `item_net_sales_amount`
  - `item_discount_share_of_gross`
- Delivery outcome and post-shipment fields:
  - `Delivery_Status`
  - `Days_for_shipping_real`
  - `shipping_date_DateOrders`
  - `Order_Status`
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
- Product asset or descriptive-only fields:
  - `Product_Image`
  - `Product_Description`

These exclusions follow the AO2 target policy, leakage-control plan, feature
availability map, and pre-Gold modeling decisions.

## Validation Rules

The builder and validation script enforce:

- exact expected AO2 row count;
- one row per `Order_Id`, `Order_Item_Id`, and `order_date_DateOrders`;
- complete AO2 target;
- required predictor and AO3 support columns present and non-null;
- forbidden leakage, duplicate, and deferred fields absent;
- positive `ao3_order_value`;
- key timestamp and feature schema types consistent with downstream modeling.

Unlike AO1 Gold, AO2 Gold uses the full valid Silver population of 180,519 rows
and does not apply AO1-specific exclusions for shipping-canceled, canceled, or
suspected-fraud records, because AO2 models order-level profitability rather
than completed-delivery lateness.

Validation script:

```text
tests/data_validation/test_gold_ao2_table.py
```

## Downstream Modeling Notes

The AO2 Gold table does not apply imputation, scaling, encoding, feature
selection, model training, thresholding, or SHAP/explainability.

Those steps must be fit only on training data after the official chronological
split. Categorical variables remain as strings so the modeling pipeline can
apply train-only encoding.
