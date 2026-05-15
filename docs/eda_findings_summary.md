# EDA Findings Summary

Issue: `[W3][P0][#5] Document EDA findings and validate with the group #24`

## Purpose and Scope

This document summarizes the most important EDA findings before Gold table
creation and AO1/AO2/AO3 modeling. It is a synthesis of prior EDA artifacts,
not a new full EDA run.

The findings are descriptive. They should inform feature selection, leakage
review, chronological split design, metric choice, and modeling priorities, but
they do not establish causality, train models, set thresholds, or freeze Gold
tables.

## Data and Artifact Sources

The synthesis is based on the local Silver EDA outputs that reference:

```text
data/silver/dataco_orders_silver.csv
```

Main artifacts reviewed:

- `docs/ao1_bivariate_eda.md`
- `docs/ao2_bivariate_eda.md`
- `docs/ao1_class_imbalance_analysis.md`
- `docs/pre_gold_modeling_decisions.md`
- `docs/leakage_conceptual_screening.md`
- `docs/feature_availability_map.md`
- `docs/leakage_control_plan.md`
- `report/tables/ao1_late_delivery_bivariate_findings.md`
- `report/tables/ao2_profitability_bivariate_findings.md`
- `report/tables/ao1_class_imbalance_findings.md`
- `report/tables/univariate_distribution_eda_findings.md`
- group-validation CSVs under `report/tables/`
- focused EDA figures under `report/figures/eda/`

Detailed bivariate and group-review tables are not duplicated here. This
summary uses the leakage screening and pre-Gold decisions to interpret which
patterns are modeling candidates, which are descriptive only, and which require
deferment or confirmation.

## AO1 Late-Delivery Findings

AO1 uses `Late_delivery_risk` as the binary target. The reviewed Silver clone
contains 180,519 valid target rows:

| Class | Count | Rate |
| --- | ---: | ---: |
| Late = 1 | 98,977 | 54.83% |
| Not late = 0 | 81,542 | 45.17% |

The majority-to-minority ratio is approximately 1.214:1. This is a mild class
imbalance, with late orders as the majority class. Accuracy should still not be
the primary AO1 metric because missing high-risk orders has operational cost.

The strongest leakage-safe AO1 descriptive patterns are planned shipping
service fields:

- `Days_for_shipment_scheduled` / `scheduled_shipping_days`: one scheduled day
  had a 95.32% late-delivery rate, compared with 38.07% for four scheduled
  days.
- `Shipping_Mode` / `shipping_mode_normalized`: `First Class` had a 95.32%
  late-delivery rate, while `Standard Class` had 38.07%.
- `shipping_speed_tier`: `expedited` orders had an 82.47% late-delivery rate,
  while `economy` orders had 38.07%.
- Same-day or next-day planned service had an 82.47% late-delivery rate,
  compared with 47.57% for other planned service.
- Non-standard shipping had a 79.64% late-delivery rate, while standard
  shipping had 38.07%.

Secondary leakage-safe patterns were smaller. Examples include regional
variation (`Central Africa` at 57.96% and `Canada` at 48.80%), order-hour
variation, and product/category differences. Some category groups were below
the support threshold and should not be overinterpreted.

AO1 EDA explicitly excludes target, post-shipment, post-delivery, and outcome
fields from predictor discussion. Examples include `Delivery_Status`,
`Days_for_shipping_real`, `shipping_date_DateOrders`, `Order_Status`, actual
delivery outcomes, profit outcomes, profit proxies, and dashboard-only fields.

Modeling implications:

- Report recall, precision, F1, confusion matrix, AUC-ROC, and PR-AUC if
  imbalance remains meaningful after chronological splitting.
- Prioritize recall and operational usefulness rather than accuracy alone.
- Select operating thresholds using validation data only.
- Do not apply SMOTE, undersampling, oversampling, or class weighting during
  EDA. If used later, resampling must occur inside the training fold or
  training data only after the chronological split.

## AO2 Profitability Findings

AO2 uses `Order_Profit_Per_Order` as the primary profitability target. No
fallback target was used in the reviewed Silver clone. `Benefit_per_order`
matched `Order_Profit_Per_Order` exactly and is treated as a duplicate profit
outcome, not a predictor. `Order_Item_Profit_Ratio` is excluded as a realized
profit-ratio/proxy field.

The target distribution is skewed and outlier-sensitive:

| Statistic | Value |
| --- | ---: |
| Valid rows | 180,519 |
| Mean profit | 21.97 |
| Median profit | 31.52 |
| Standard deviation | 104.43 |
| Minimum | -4,274.98 |
| Maximum | 911.80 |
| Skewness | -4.742 |
| IQR outlier count | 18,942 |

Product mix shows support-safe descriptive profitability differences:

- `Department_Name`: Technology had the highest supported mean profit at
  77.25; Discs Shop had the lowest at 11.94.
- `Category_Name`: Fishing had the highest supported mean profit at 43.65;
  Golf Balls had the lowest at 5.66.

Commercial fields also show meaningful descriptive gradients, especially order
value, price, discount, and quantity fields. These fields are useful for review
but require target-reconstruction discipline because many are economically or
mathematically related.

The approved first-pass AO2 commercial predictor set from
`docs/pre_gold_modeling_decisions.md` is:

- `Order_Item_Product_Price`
- `Order_Item_Discount_Rate`
- `Order_Item_Quantity`

The following must remain excluded from primary AO2 predictors:

- `Order_Profit_Per_Order`
- `Benefit_per_order`
- `Order_Item_Profit_Ratio`
- duplicate profit fields
- direct profit transformations or realized margin fields
- `Order_Item_Total`
- `Sales`
- `Sales_per_customer`
- `Order_Item_Discount`
- `Product_Price`

`Order_Item_Total` is approved for AO3 denominator use only, not as a primary
AO2 predictor. This supports later margin construction while reducing AO2
target-reconstruction risk.

## AO3 Prioritization Implications

The EDA supports the need to evaluate service risk and economic value together:

- AO1 should estimate order-level late-delivery risk before dispatch.
- AO2 should estimate expected order-level profitability before dispatch.
- AO3 should combine predicted late-delivery risk with predicted profitability
  or predicted margin.

The eventual risk-margin framework should compare combined prioritization
against risk-only and profit-only views. AO3 segmentation should not be created
from actual outcomes or descriptive EDA results; it should be assigned later
from model predictions using thresholds selected on training or validation data.

## Gold Feature-Selection Implications

First-pass Gold should remain conservative and leakage-safe:

- Use order-time date features derived from `order_date_DateOrders`.
- Use planned shipping and shipping mode features.
- Use category and department rather than direct product IDs or product names.
- Use coarse geography such as market, region, country, state, and customer
  segment rather than city, postal code, coordinates, or composite region keys.
- Use `Type` only under the documented team assumption that it represents
  payment transaction type available at order creation.
- Exclude canceled, suspected-fraud, and shipping-canceled records from the
  primary AO1 population.
- Defer direct product-level descriptors, granular geography, and historical
  aggregates to future issues.
- Document that historical customer, product, region, city, or category
  aggregates require time-aware, train-only computation.

## Modeling Design Implications

Chronological splitting remains required. The most recent 20% of orders should
be held out as the final test set, with the earlier 80% used for development,
validation, and tuning.

All preprocessing must be fit on training data only, including imputation,
encoding, scaling, resampling, feature selection, threshold tuning, and any
future historical aggregate logic.

Metric alignment:

- AO1: AUC-ROC, recall, precision, F1, confusion matrix, and PR-AUC if the
  chronological split shows meaningful imbalance.
- AO2: RMSE, MAE, R2, and residual inspection.
- AO3: compare combined risk-margin prioritization against risk-only and
  profit-only prioritization.

AO2 model comparison should include baseline and advanced models while checking
feature importance, residuals, and predictor lists for target-reconstruction
risk.

## Group Validation Before Modeling

Before Gold/modeling moves forward, the group should confirm:

- `Type` represents payment transaction type known at order creation:
  `TRANSFER` = direct bank transfer, `DEBIT` = debit card payment, `CASH` =
  cash-on-hand payment, and `PAYMENT` = other payment types, primarily
  credit-based payments.
- Canceled, suspected-fraud, and shipping-canceled records are excluded from
  the primary AO1 Gold population.
- The first-pass AO2 commercial predictor set is limited to
  `Order_Item_Product_Price`, `Order_Item_Discount_Rate`, and
  `Order_Item_Quantity`.
- `Order_Item_Total` is used as the AO3 denominator only, not as a primary AO2
  predictor.
- Direct product descriptors and product IDs remain excluded or deferred.
- Granular geography remains excluded or deferred.
- Historical aggregates are future-issue features only.
- Any `conditional` or `needs_group_review` variables in the AO1/AO2/class
  imbalance group-validation tables are either resolved by
  `docs/pre_gold_modeling_decisions.md` or remain deferred until a separate
  feature-design issue.

The older group-validation CSVs identify important review topics, especially
`Type`, commercial-field redundancy, product-level descriptors, granular
geography, and historical aggregates. The finalized first-pass policy in
`docs/pre_gold_modeling_decisions.md` supersedes the preliminary EDA review
status where the two differ.

## Assumptions and Limitations

- EDA findings are descriptive, not causal.
- Observed patterns may change after applying the primary AO1 population
  filtering policy.
- Small groups and bins below support thresholds should not be overinterpreted.
- Some fields are excluded despite apparent signal because of leakage,
  target-reconstruction, high-cardinality, privacy, or stability concerns.
- Some decisions rely on documented team assumptions rather than fully explicit
  dataset metadata.
- Final model performance, calibration, residual behavior, and feature
  importance must be evaluated on validation and held-out test data.

## Reusable References

- `docs/leakage_control_plan.md`
- `docs/leakage_conceptual_screening.md`
- `docs/feature_availability_map.md`
- `docs/pre_gold_modeling_decisions.md`
- `docs/order_time_features.md`
- `docs/shipping_product_features.md`
- `docs/customer_regional_features.md`
- `report/tables/ao1_late_delivery_bivariate_findings.md`
- `report/tables/ao2_profitability_bivariate_findings.md`
- `report/tables/ao1_class_imbalance_findings.md`
- `report/tables/univariate_distribution_eda_findings.md`
