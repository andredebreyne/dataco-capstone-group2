# AO1 Bivariate Late-Delivery EDA Findings

## Purpose

This report-facing note summarizes the AO1 bivariate EDA findings for correlates
of `Late_delivery_risk`. It is based on the generated AO1 EDA outputs and is
intended to support later Gold/modeling review.

This note does not train AO1 models, finalize Gold tables, approve conditional
variables, or make causal claims.

## Dataset And Target Audit

The EDA used the local Silver clone:

```text
data/silver/dataco_orders_silver.csv
```

Target:

```text
Late_delivery_risk
```

Target audit summary:

| Item | Result |
| --- | ---: |
| Valid target rows | 180,519 |
| Overall late-delivery rate | 54.83% |
| Minimum support threshold for ranked group/bin signals | 903 rows |

The target was treated as a binary AO1 outcome. The EDA used support thresholds
to avoid overinterpreting small categories or bins.

## Screening Coverage

The AO1 EDA reviewed 101 rows from the conceptual leakage screening artifact.

| Modeling recommendation | Variable count |
| --- | ---: |
| `candidate_for_gold_review` | 40 |
| `conditional_requires_group_review` | 41 |
| `dashboard_only` | 7 |
| `exclude_from_ao1_modeling` | 10 |
| `descriptive_context_only` | 3 |

Only variables marked `candidate_for_gold_review` are treated as recommended
AO1 candidate signals for later Gold review. Conditional variables are kept in a
separate group-validation list and are not approved for modeling in this EDA.

## Main Descriptive Findings

The strongest support-safe AO1 associations came from planned shipping service
fields. These fields are pre-dispatch candidates under the current screening
policy, but final feature inclusion still belongs to Gold/modeling review.

| Candidate signal | Support-safe pattern |
| --- | --- |
| `Days for shipment (scheduled)` / `scheduled_shipping_days` | One scheduled day had a 95.32% late-delivery rate, compared with 38.07% for four scheduled days. |
| `Shipping Mode` / `shipping_mode_normalized` | `First Class` had a 95.32% late-delivery rate, while `Standard Class` had 38.07%. |
| `shipping_speed_tier` | `expedited` orders had an 82.47% late-delivery rate, while `economy` orders had 38.07%. |
| `is_same_day_or_next_day_shipping` | Same-day or next-day planned service had an 82.47% late-delivery rate, compared with 47.57% for other planned service. |
| `is_standard_shipping` | Non-standard shipping had a 79.64% late-delivery rate, while standard shipping had 38.07%. |

Secondary candidate patterns were materially smaller:

| Candidate signal | Support-safe pattern |
| --- | --- |
| `Order Region` / `order_region_normalized` | Central Africa had a 57.96% late-delivery rate, while Canada had 48.80%. |
| `Customer State` / `customer_state_normalized` | NM had a 60.27% late-delivery rate, while CO had 50.68%. |
| `order_hour` | The highest supported hour was 12 with a 59.50% late-delivery rate; the lowest was 8 with 50.87%. |
| `Category Name` / `product_category_key` | Accessories had a 56.97% late-delivery rate, while Men's Footwear had 54.49%. Many category groups were below the support threshold. |

These findings indicate useful descriptive variation for AO1 review, especially
around planned service level. They do not establish causality and should not be
interpreted as final feature-selection decisions.

Existing reusable figures are available under:

```text
report/figures/eda/
```

## Conditional And Group-Review Variables

The group-validation list contains 41 variables. One variable, `Type`, was
flagged as `higher_signal_review`: `PAYMENT` had a 57.53% late-delivery rate,
while `TRANSFER` had 48.54%. It still requires group validation because the
business semantics of transaction type must be confirmed before AO1 modeling.

Other conditional variables require review for policy reasons rather than strong
AO1 bivariate signal:

- Commercial/order-value fields such as `Sales per customer`, `Sales`,
  `Order Item Total`, prices, discounts, and engineered value features require
  semantic and redundancy review before modeling.
- High-cardinality identifiers and keys such as customer IDs, product IDs,
  catalog keys, and region keys should not be used directly.
- Granular geography such as city, postal code, latitude, longitude, and rounded
  coordinates requires privacy, stability, and grouping review.
- Product name and product status fields require cardinality or business-status
  interpretation before modeling.
- Raw `order date (DateOrders)` should be replaced by approved derived calendar
  features rather than used directly.

No conditional or `needs_group_review` variable is approved for AO1 modeling by
this findings note.

## Excluded Leakage And Outcome Fields

The EDA explicitly excludes target, post-shipment, post-delivery, outcome,
profit-proxy, and sensitive identifier fields from AO1 predictor recommendations.

Important exclusions include:

- `Late_delivery_risk`: AO1 target only.
- `Delivery Status`: post-delivery outcome and target proxy.
- `Days for shipping (real)`: actual fulfillment duration known after delivery.
- `shipping date (DateOrders)`: post-order shipment timestamp.
- `Order Status`: may encode post-order or fulfillment outcome.
- `Benefit per order`, `Order Profit Per Order`, and
  `Order Item Profit Ratio`: profit outcome/proxy fields.
- Sensitive or non-operational identifiers such as customer email, names,
  password, street address, order IDs, and order item IDs.

Some excluded fields may remain useful for descriptive dashboard or audit
purposes, but they must not enter AO1 predictor matrices.

## Group Decisions Needed Before AO1 Modeling

Before AO1 Gold/modeling work, the team should validate:

- Whether `Type` is known at order creation and has an operationally valid
  interpretation for AO1 modeling.
- Whether planned shipping service fields should remain AO1 candidates despite
  their strong association with late delivery.
- Which high-cardinality geography, product, and region-key variables should be
  grouped, excluded, or deferred.
- Whether raw IDs should remain excluded except for explicitly approved,
  time-aware training-only aggregates.
- Whether raw order timestamp should remain split/lineage context only, with
  modeling limited to deterministic derived order-time features.
- Whether any commercial fields are needed for AO1 context or should remain
  descriptive/AO2-focused only.

## Caveats

- Bivariate EDA identifies associations, not causal effects.
- Small groups below the support threshold should not be overinterpreted.
- Post-shipment, post-delivery, target, and outcome fields must not be used as
  AO1 predictors.
- Conditional or `needs_group_review` variables require team validation before
  modeling.
- Final AO1 features must still be selected later using the leakage-control
  rules, chronological split policy, and train-only preprocessing.
