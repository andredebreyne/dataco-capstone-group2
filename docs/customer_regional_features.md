# Customer and Regional Features

Task: `[W2][P0][#5] Feature engineering: customer and regional variables`

Issue: `#14`

## Purpose

This document defines the customer segment and regional features created for the DataCo Capstone project. These features support downstream AO1 late-delivery modeling, AO2 profitability modeling, and AO3 prioritization while respecting the project decision-time and leakage-control rules.

The feature engineering job uses static customer segment and location fields, order destination fields, market fields, and coarse geographic coordinates that are expected to be known at order time or before dispatch.

The job does not derive features from personal identifiers, street-level addresses, delivery outcomes, shipping dates, actual shipping duration, targets, profit outcomes, or learned historical aggregates.

## Input and Output

Input Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_silver
```

Output Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_customer_regional_features
```

Script:

```text
src/data_engineering/engineer_customer_regional_features.py
```

## Output Keys and Lineage

The output keeps these columns for traceability:

| Column | Type | Purpose |
| --- | --- | --- |
| `Order_Id` | integer | Order-level join and traceability key. |
| `Order_Item_Id` | integer | Order-item-level join and traceability key. |
| `order_date_DateOrders` | timestamp | Decision-time timestamp used for chronological validation and downstream splits. |
| `_ingest_timestamp` | timestamp | Bronze ingestion lineage. |
| `_source_file` | string | Bronze source-file lineage. |
| `_silver_processed_timestamp` | timestamp | Silver processing lineage. |

## Feature Contract

| Feature | Type | Source | Intended use |
| --- | --- | --- | --- |
| `customer_segment_normalized` | string | `Customer_Segment` | Captures business customer segment. |
| `customer_country_normalized` | string | `Customer_Country` | Captures customer country as a stable token. |
| `customer_state_normalized` | string | `Customer_State` | Captures customer state as a stable token. |
| `customer_city_normalized` | string | `Customer_City` | Captures customer city as a stable token for review and possible grouping. |
| `customer_zipcode_available` | integer | `Customer_Zipcode` | Flags whether customer postal information is present without using the raw postcode directly. |
| `market_normalized` | string | `Market` | Captures market-level operating context. |
| `order_country_normalized` | string | `Order_Country` | Captures order destination country as a stable token. |
| `order_region_normalized` | string | `Order_Region` | Captures order destination region as a stable token. |
| `order_state_normalized` | string | `Order_State` | Captures order destination state as a stable token. |
| `order_city_normalized` | string | `Order_City` | Captures order destination city as a stable token for review and possible grouping. |
| `order_zipcode_available` | integer | `Order_Zipcode` | Flags whether order postal information is present without using the raw postcode directly. |
| `customer_region_key` | string | Customer country, state, city | Creates a coarse customer-region descriptor for review and later encoding decisions. |
| `order_region_key` | string | Order country, region, state, city | Creates a coarse destination-region descriptor for review and later encoding decisions. |
| `customer_order_country_match` | integer | Customer and order countries | Flags whether customer and destination countries match. |
| `customer_order_state_match` | integer | Customer and order states | Flags whether customer and destination states match. |
| `latitude_rounded` | double | `Latitude` | Captures coarse geographic latitude while reducing precision. |
| `longitude_rounded` | double | `Longitude` | Captures coarse geographic longitude while reducing precision. |
| `geo_coordinates_available` | integer | `Latitude`, `Longitude` | Flags whether geographic coordinates are available. |
| `_customer_regional_features_processed_timestamp` | timestamp | processing metadata | Records when the feature table was generated. |

## Excluded Fields

The following fields are intentionally excluded from the generated feature output:

- `Customer_Email`
- `Customer_Fname`
- `Customer_Lname`
- `Customer_Password`
- `Customer_Street`
- `Delivery_Status`
- `Late_delivery_risk`
- `Days_for_shipping_real`
- `shipping_date_DateOrders`
- `Order_Status`
- `Order_Profit_Per_Order`
- `Benefit_per_order`
- `Order_Item_Profit_Ratio`

`Customer_Id` is also not emitted as a modeling feature. It may be used later only as a controlled grouping key for training-only historical aggregates if the team approves that design.

## Leakage-Control Assessment

These features are designed to be decision-time valid because customer segment, destination geography, market, and coarse coordinates are expected to be known when the order is placed or before dispatch.

No historical performance aggregates are computed in this task. Any future customer, region, city, or market aggregates must be implemented inside a training-only preprocessing workflow and must avoid using future rows to describe earlier orders.

## High-Cardinality and Stability Review

`customer_city_normalized`, `order_city_normalized`, `customer_region_key`, and `order_region_key` may be high-cardinality fields. They are retained for review and traceability, but they should not be blindly one-hot encoded in modeling pipelines.

Before modeling, high-cardinality regional fields must be classified as:

- `Allowed`: used directly or with a documented deterministic grouping
- `Review`: requires grouping, frequency thresholding, or target-safe historical aggregation
- `Forbidden`: excluded due to instability, poor operational meaning, or leakage risk

Any learned encoding, frequency threshold, or historical aggregate must be fit on training data only.

## Validation Rules

The feature engineering job validates:

- Silver input path uses Unity Catalog Volumes
- required Silver input columns exist
- input row count matches `180,519`
- output row count matches `180,519`
- all expected output columns are present
- no unexpected original Silver columns are present in the feature output
- personal identifiers, target fields, profit fields, and post-shipment fields are not present
- required generated features do not contain null values

## Execution Order

Run the pipeline in this order:

1. `src/data_engineering/ingest_bronze.py`
2. `src/data_engineering/clean_silver.py`
3. `src/data_engineering/engineer_customer_regional_features.py`

The Silver cleaning job must complete successfully before customer and regional feature engineering runs.

## Assumptions and Limitations

- Customer segment and regional fields are treated as available at order time.
- Latitude and longitude are rounded to two decimals to reduce location precision while preserving broad geographic signal.
- Raw postal codes are not emitted as features; only availability flags are generated.
- Personal identifiers and street-level details are excluded.
- Historical aggregates are intentionally deferred to later modeling pipelines and must be fit on training data only.
