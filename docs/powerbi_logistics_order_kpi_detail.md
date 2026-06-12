# Power BI Logistics Order KPI Detail

Issue: `#152`

Branch:

```text
feature/152-order-level-logistics-kpi-audit
```

## Purpose

`powerbi_logistics_order_kpi_detail` is an order-item-level Power BI serving table for predicted-vs-actual logistics KPI validation.

The table complements `powerbi_logistics_kpi_summary`. The summary table supports aggregated executive visuals by region, shipping mode, category, risk band, and AO3 action queue. This detail table preserves the order identifiers needed to audit whether AO1 high-risk predictions actually became late-delivery outcomes.

## Business Question

For each order item, did the model correctly identify late-delivery risk before dispatch?

## Conceptual Scope

AO1 predicts risk of late delivery. High risk means high predicted probability of missing the planned delivery or shipping window.

AO2 adds financial context.

AO3 combines late-delivery risk and financial context into operational action queues.

Do not describe AO1 high risk as generic logistics risk, freight cost risk, cancellation risk, inventory risk, or margin risk.

## Output Path

Default Delta output:

```text
/Volumes/workspace/default/raw_data/gold/powerbi_logistics_order_kpi_detail
```

Default metadata output:

```text
models/dashboard/powerbi_logistics_order_kpi_detail_metadata.json
```

## Source Inputs

| Source | Purpose |
| --- | --- |
| `dataco_orders_silver` | Actual scheduled and real shipping days, delivery status, order identifiers, and shipment dates for audit outcomes. |
| `ao3_risk_margin_segments` | Governed AO1 probability, AO1 high-risk flag, AO2 profitability estimate, AO3 margin, value, and action segment. |
| `dataco_shipping_product_features` | Shipping mode, speed tier, product category, department, quantity, and net sales amount. |
| `dataco_customer_regional_features` | Market, country, region, and state fields for geographic slicing and drill-through. |

## Serving Grain

Preferred grain:

```text
Order_Id + Order_Item_Id
```

This grain aligns the prediction, actual delivery outcome, financial context, and AO3 action queue in the same row.

If AO1 prediction grain changes, this table should use the same prediction grain and document the change explicitly.

## Supported KPI and Validation Metrics

This table supports the following logistics KPI and model-validation measures:

```text
OTD Rate
Late Delivery Rate
Expected Late Delivery Rate
Predicted OTD Exposure
Actual Late Rate by Risk Band
High-Risk Precision
High-Risk Recall
Overall Accuracy
False Positive Count
False Negative Count
Risk Lift by Risk Band
AO3 Action Queue Volume
```

## Field Groups

### Identifiers and Dates

| Field | Meaning |
| --- | --- |
| `Order_Id` | Order identifier. |
| `Order_Item_Id` | Order item identifier. |
| `order_date_DateOrders` | Original order timestamp. |
| `shipping_date_DateOrders` | Original shipping timestamp. |
| `order_month_key` | Reporting month derived from order date. |
| `order_year` | Reporting year. |
| `order_month` | Reporting month number. |

### Logistics Dimensions

| Field | Meaning |
| --- | --- |
| `market_normalized` | Normalized market. |
| `map_location_country` | Delivery country for mapping and slicing, standardized as an English display label. |
| `map_location_region` | Delivery region for mapping and slicing. |
| `map_location_state` | Delivery state for mapping and slicing. |
| `shipping_mode_normalized` | Normalized shipping mode. |
| `shipping_speed_tier` | Shipping speed classification. |
| `product_category_key` | Product category key. |
| `product_department_key` | Product department key. |

### Delivery KPI Fields

| Field | Meaning |
| --- | --- |
| `Days_for_shipment_scheduled` | Planned shipping window in days. |
| `Days_for_shipping_real` | Actual shipping duration in days. |
| `scheduled_shipping_days` | Numeric scheduled shipping days. |
| `actual_shipping_lead_time` | Numeric actual shipping days. |
| `delivery_delay_gap` | Actual shipping days minus scheduled shipping days. |
| `valid_delivery_metric_flag` | 1 when both scheduled and actual shipping days are available. |
| `actual_on_time_delivery_flag` | 1 when actual shipping days are less than or equal to scheduled shipping days. |
| `actual_late_delivery_flag` | 1 when actual shipping days are greater than scheduled shipping days. |
| `delivery_status_normalized` | Delivery status retained for audit interpretation. |

### AO1 Prediction Fields

| Field | Meaning |
| --- | --- |
| `ao1_predicted_late_delivery_probability` | Governed AO1 predicted probability of late delivery. |
| `ao1_expected_on_time_probability` | One minus AO1 predicted late-delivery probability. |
| `ao1_high_risk_flag` | 1 when AO1 marks the order item as high risk. |
| `risk_band` | Dashboard risk band derived from AO1 probability. |
| `risk_band_sort_order` | Sort order for risk bands. |

### Predicted vs Actual Classification Fields

| Field | Meaning |
| --- | --- |
| `true_positive_flag` | Predicted high risk and actually late. |
| `false_positive_flag` | Predicted high risk and actually on time. |
| `false_negative_flag` | Predicted not high risk and actually late. |
| `true_negative_flag` | Predicted not high risk and actually on time. |

### AO2 and AO3 Fields

| Field | Meaning |
| --- | --- |
| `ao2_predicted_order_profit` | Governed AO2 predicted order profit. |
| `ao3_predicted_margin` | AO3 margin context. |
| `ao3_order_value` | AO3 order value context. |
| `ao3_priority_segment` | Governed AO3 priority segment. |
| `ao3_action_queue_label` | Display label for AO3 action queue. |
| `ao3_action_queue_sort_order` | Sort order for AO3 action queues. |
| `intervention_required_flag` | 1 when the AO3 segment requires active review. |

## DAX Measure Guidance

### Base Measures

```DAX
Total Order Items =
COUNTROWS('powerbi_logistics_order_kpi_detail')

Valid Delivery Metric Count =
SUM('powerbi_logistics_order_kpi_detail'[valid_delivery_metric_flag])

Actual On-Time Count =
SUM('powerbi_logistics_order_kpi_detail'[actual_on_time_delivery_flag])

Actual Late Count =
SUM('powerbi_logistics_order_kpi_detail'[actual_late_delivery_flag])

Expected Late Count =
SUM('powerbi_logistics_order_kpi_detail'[ao1_predicted_late_delivery_probability])

Expected On-Time Count =
SUM('powerbi_logistics_order_kpi_detail'[ao1_expected_on_time_probability])

High-Risk Count =
SUM('powerbi_logistics_order_kpi_detail'[ao1_high_risk_flag])
```

### Logistics KPI Measures

```DAX
OTD Rate =
DIVIDE([Actual On-Time Count], [Valid Delivery Metric Count])

Late Delivery Rate =
DIVIDE([Actual Late Count], [Valid Delivery Metric Count])

Expected Late Delivery Rate =
DIVIDE([Expected Late Count], [Total Order Items])

Expected OTD Rate =
DIVIDE([Expected On-Time Count], [Total Order Items])

Predicted OTD Exposure =
[OTD Rate] - [Expected OTD Rate]
```

### Model Validation Measures

```DAX
True Positive Count =
SUM('powerbi_logistics_order_kpi_detail'[true_positive_flag])

False Positive Count =
SUM('powerbi_logistics_order_kpi_detail'[false_positive_flag])

False Negative Count =
SUM('powerbi_logistics_order_kpi_detail'[false_negative_flag])

True Negative Count =
SUM('powerbi_logistics_order_kpi_detail'[true_negative_flag])

High-Risk Precision =
DIVIDE([True Positive Count], [True Positive Count] + [False Positive Count])

High-Risk Recall =
DIVIDE([True Positive Count], [True Positive Count] + [False Negative Count])

Overall Accuracy =
DIVIDE([True Positive Count] + [True Negative Count], [Valid Delivery Metric Count])

Actual Late Rate by Risk Band =
DIVIDE([Actual Late Count], [Valid Delivery Metric Count])

Risk Lift by Risk Band =
DIVIDE([Actual Late Rate by Risk Band], CALCULATE([Late Delivery Rate], ALL('powerbi_logistics_order_kpi_detail'[risk_band])))
```

Important interpretation:

```text
If 100 order items are classified as high risk and 90 actually become late, that is High-Risk Precision of 90%, not overall accuracy.
```

## Recommended Dashboard Usage

### Page: Q06 | Logistics KPI Risk Exposure

Use `powerbi_logistics_kpi_summary` for fast aggregated executive visuals where appropriate.

Use `powerbi_logistics_order_kpi_detail` for:

- predicted-vs-actual validation;
- order-level or order-item-level drill-through;
- high-risk precision and recall;
- actual late rate by risk band;
- false positive and false negative review;
- AO3 action queue audit.

### Suggested Visuals

#### 1. Actual Late Rate by Risk Band

Type: bar chart.

```text
Axis: risk_band
Value: Actual Late Rate by Risk Band
Sort: risk_band_sort_order
```

Purpose: confirm whether high-risk segments actually show higher realized late-delivery rates.

#### 2. High-Risk Prediction Audit

Type: KPI cards or matrix.

```text
Values:
High-Risk Precision
High-Risk Recall
False Positive Count
False Negative Count
Overall Accuracy
```

Purpose: evaluate whether AO1 high-risk predictions match actual delivery outcomes.

#### 3. Order-Level Drill-Through Table

Type: table.

```text
Order_Id
Order_Item_Id
ao1_predicted_late_delivery_probability
risk_band
ao1_high_risk_flag
actual_late_delivery_flag
true_positive_flag
false_positive_flag
false_negative_flag
true_negative_flag
ao3_action_queue_label
```

Purpose: allow direct inspection of predictions and actual outcomes.

#### 4. AO3 Action Queue Audit

Type: matrix.

```text
Rows: ao3_action_queue_label, risk_band
Values: Total Order Items, Actual Late Count, Expected Late Count, High-Risk Precision, High-Risk Recall
```

Purpose: show whether AO3 action queues concentrate actual late-delivery failures and high-value operational exposure.

## Governance Rules

- Actual outcome fields are exposed only for KPI reporting, audit, and validation.
- Actual outcome fields must not be used as model predictors.
- This table does not retrain AO1, AO2, or AO3.
- This table does not redefine AO3 policy.
- Do not claim causal intervention impact.
- Do not describe expected exposure as proven operational improvement.
- Do not add freight cost, transportation cost, or cost-to-serve KPIs unless a real source field exists.

## Final Interpretation

This table makes the logistics KPI module auditable. It shows not only aggregated delivery-risk exposure, but also whether AO1 high-risk predictions actually correspond to late-delivery outcomes at the order-item level.
