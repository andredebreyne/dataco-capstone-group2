# Order-Time Date Features

Task: `[W2][P0][#3] Feature engineering: order-time date variables`

Issue: `#12`

## Purpose

This document defines the order-time date features created for the DataCo Capstone project. These features support AO1 late-delivery modeling, AO2 profitability modeling, and later AO3 risk-margin prioritization while respecting the project decision-time and leakage-control rules.

The feature engineering job uses only:

```text
order_date_DateOrders
```

It does not use shipping dates, delivery status, actual shipping duration, late-delivery outcomes, profitability targets, or post-order fulfillment information.

## Input and Output

Input Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_silver
```

Output Delta path:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_order_time_features
```

Output note: this is a feature-enriched Silver dataset, or Gold-ready intermediate
dataset, not a final leakage-safe AO1/AO2 modeling table. Downstream Gold
transformations must still apply the feature availability map and leakage-control
rules before creating model feature matrices. See `docs/leakage_control_plan.md`
and the finalized first-pass Gold decisions in
`docs/pre_gold_modeling_decisions.md`.

Script:

```text
src/data_engineering/engineer_order_time_features.py
```

## Feature Contract

| Feature | Type | Source | Intended use |
| --- | --- | --- | --- |
| `order_year` | integer | `order_date_DateOrders` | Captures yearly trend and long-term operational changes. |
| `order_quarter` | integer | `order_date_DateOrders` | Captures quarterly seasonality and planning cycles. |
| `order_month` | integer | `order_date_DateOrders` | Captures monthly seasonality in demand, fulfillment load, and profitability. |
| `order_week_of_year` | integer | `order_date_DateOrders` | Captures weekly seasonality and calendar-cycle effects. |
| `order_day_of_month` | integer | `order_date_DateOrders` | Captures within-month ordering behavior. |
| `order_day_of_week` | integer | `order_date_DateOrders` | Captures weekday/weekend operating patterns. Spark encodes Sunday as `1` and Saturday as `7`. |
| `order_hour` | integer | `order_date_DateOrders` | Captures intraday ordering patterns. |
| `order_is_weekend` | integer | `order_date_DateOrders` | Flags orders placed on Saturday or Sunday. |
| `order_season` | string | `order_date_DateOrders` | Provides an interpretable seasonality proxy for EDA and modeling review. |
| `_order_time_features_processed_timestamp` | timestamp | processing metadata | Records when the feature table was generated. |

## Leakage-Control Assessment

These features are decision-time valid because the order timestamp is known when the order is created. The transformation derives only calendar attributes from the order timestamp and does not inspect future fulfillment events.

Forbidden inputs for this task include:

- `shipping_date_DateOrders`
- `Delivery_Status`
- `Days_for_shipping_real`
- `Late_delivery_risk`
- `Order_Status`
- profit targets or direct profit-derived fields

The output retains existing Silver columns for traceability, but modeling feature-selection code must still apply AO1 and AO2 leakage-control rules before training.

## Validation Rules

The feature engineering job validates:

- Silver input path uses Unity Catalog Volumes
- `order_date_DateOrders` exists
- `order_date_DateOrders` is a Spark `timestamp`
- input row count matches `180,519`
- output row count matches `180,519`
- all expected feature columns are present
- generated feature columns use the expected Spark data types
- generated order-time feature columns do not contain null values
- generated calendar feature values stay within expected deterministic ranges
- `order_season` contains only approved season labels

## Execution Order

Run the pipeline in this order:

1. `src/data_engineering/ingest_bronze.py`
2. `src/data_engineering/clean_silver.py`
3. `src/data_engineering/engineer_order_time_features.py`

The Silver cleaning job must complete successfully before order-time feature engineering runs.

## Assumptions and Limitations

- `order_date_DateOrders` is treated as the order creation timestamp.
- Calendar features are deterministic and do not require training-data fitting.
- `order_season` is intentionally interpretable rather than statistically learned.
  It is a simple calendar seasonality proxy based on month buckets and, because
  DataCo is global, should not be interpreted as a geographically accurate local
  climate season for every market.
- Cyclical encodings such as sine/cosine month or day-of-week transformations may be added later inside model pipelines if needed, but fitted preprocessing and model-specific feature selection must remain training-only.
