# Power BI Logistics KPI Risk Exposure

Issue: `#150`

## Purpose

`powerbi_logistics_kpi_summary` is a Power BI serving table that connects historical logistics performance with predictive pre-dispatch exposure from AO1, AO2, and AO3.

The page supported by this table is:

```text
P05 Logistics KPI Risk Exposure
```

Suggested subtitle:

```text
Connecting historical fulfillment performance with pre-dispatch predictive risk and operational action queues.
```

## Business Question

Which logistics KPIs are exposed to deterioration based on current pre-dispatch risk signals, and where should operations focus first?

## Core Interpretation

Historical logistics KPIs show what happened. AO1 estimates what may happen before dispatch. AO2 adds economic context. AO3 converts that exposure into operational action queues.

This page should communicate expected KPI exposure, not causal impact.

Recommended governance statement:

```text
Expected KPI exposure is derived from predicted late-delivery probabilities. It should be interpreted as pre-dispatch risk exposure, not as a causal estimate of intervention impact.
```

## Output Path

Default Delta output:

```text
/Volumes/workspace/default/raw_data/gold/powerbi_logistics_kpi_summary
```

Default metadata output:

```text
models/dashboard/powerbi_logistics_kpi_summary_metadata.json
```

## Source Inputs

| Source | Purpose |
| --- | --- |
| `dataco_orders_silver` | Historical delivery outcome fields for descriptive KPI reporting. |
| `ao3_risk_margin_segments` | Governed AO1/AO2/AO3 predictive outputs. |
| `dataco_shipping_product_features` | Shipping mode, scheduled shipping days, product category, department, quantity, and sales fields. |
| `dataco_customer_regional_features` | Market, country, region, and state fields for geographic slicing. |

## Serving Grain

The table is aggregated by:

```text
order month / market / country / region / state / shipping mode / shipping speed tier / category / department / AO3 segment / risk band
```

This grain supports logistics KPI analysis by time, geography, service mode, product grouping, risk band, and AO3 action queue.

`map_location_country` is standardized as an English display label in the Power BI serving layer. The source `order_country_normalized` feature remains unchanged upstream.

## Historical KPI Fields

Historical fields use actual delivery outcomes for descriptive dashboard reporting. They are not used to retrain AO1, AO2, or AO3.

| Field | Meaning |
| --- | --- |
| `valid_delivery_metric_count` | Count of rows with both scheduled and actual shipping days available. |
| `historical_on_time_count` | Rows where actual shipping days are less than or equal to scheduled shipping days. |
| `historical_late_count` | Rows where actual shipping days are greater than scheduled shipping days. |
| `historical_otd_rate` | Historical on-time delivery rate. |
| `historical_late_delivery_rate` | Historical late-delivery rate. |
| `avg_scheduled_shipping_days` | Average planned service window. |
| `avg_actual_shipping_days` | Average actual shipping duration. |
| `avg_delivery_delay_gap` | Average difference between actual and scheduled shipping days. |

## Predictive Exposure Fields

Predictive fields are derived from governed AO1/AO2/AO3 outputs.

| Field | Meaning |
| --- | --- |
| `expected_late_delivery_rate` | Average AO1 predicted late-delivery probability. |
| `expected_otd_rate` | One minus expected late-delivery rate. |
| `expected_otd_exposure_pp` | Historical OTD rate minus expected OTD rate, expressed as a proportion. |
| `expected_late_order_equivalent_count` | Sum of predicted late-delivery probabilities. |
| `expected_on_time_order_equivalent_count` | Sum of one minus predicted late-delivery probabilities. |
| `high_risk_order_count` | Count of orders flagged as high risk by AO1. |
| `high_risk_delivery_exposure_rate` | High-risk orders divided by total scored order items. |
| `service_protection_queue_count` | AO3 protect-first cases. |
| `selective_expedite_review_count` | AO3 selective-expedite review cases. |
| `intervention_required_count` | Protect-first plus selective-expedite cases. |
| `intervention_load_rate` | Intervention-required count divided by total scored order items. |

## Risk Bands

The serving table uses AO1 predicted late-delivery probability to create dashboard risk bands:

```text
Low Risk: probability < 0.35
Medium Risk: probability >= 0.35 and < 0.65
High Risk: probability >= 0.65
```

These bands are for dashboard interpretation and do not redefine AO1 or AO3.

## AO3 Action Queue Labels

| AO3 segment | Display label |
| --- | --- |
| `protect_high_value_at_risk` | Protect First |
| `expedite_selectively` | Review Selective Expedite |
| `preserve_service` | Preserve Service |
| `standard_process` | Standard Process |
| `requires_score_review` / `requires_margin_review` | Review Score or Margin |

## Recommended P05 KPIs

Top KPI strip:

```text
Historical OTD Rate
Expected OTD Rate
Expected OTD Exposure
Historical Late Delivery Rate
Expected Late Delivery Rate
Intervention Load Rate
```

Secondary KPI cards or tooltips:

```text
High-Risk Delivery Exposure
Service Protection Queue
Selective Expedite Review
Average Delivery Delay Gap
Order Volume
Units Ordered
Total Order Value
```

## KPI Aggregation Rules

When aggregating this serving table in Power BI, avoid averaging precomputed
rate columns across rows. Use the provided numerators and denominators:

| KPI | Recommended aggregate formula |
| --- | --- |
| Historical OTD Rate | `SUM(historical_on_time_count) / SUM(valid_delivery_metric_count)` |
| Historical Late Delivery Rate | `SUM(historical_late_count) / SUM(valid_delivery_metric_count)` |
| Expected Late Delivery Rate | `SUM(expected_late_order_equivalent_count) / SUM(order_item_count)` |
| Expected OTD Rate | `SUM(expected_on_time_order_equivalent_count) / SUM(order_item_count)` |
| High-Risk Delivery Exposure | `SUM(high_risk_order_count) / SUM(order_item_count)` |
| Intervention Load Rate | `SUM(intervention_required_count) / SUM(order_item_count)` |

The row-level rate fields are retained for sliced visuals at the published
serving grain. Executive cards should use the weighted aggregate formulas above.

## Recommended Visuals

### 1. Historical OTD Trend

Type: line chart.

```text
X-axis: order_month_key
Y-axis: historical_otd_rate
```

Purpose: show historical fulfillment performance over time.

### 2. Historical vs Expected OTD by Shipping Mode

Type: clustered bar chart.

```text
X-axis: shipping_mode_normalized
Values: historical_otd_rate, expected_otd_rate
```

Purpose: compare observed service performance with current predictive exposure by shipping mode.

### 3. Expected Late-Risk Contribution by Risk Band

Type: stacked bar chart or waterfall.

```text
Axis: risk_band
Value: expected_late_order_equivalent_count
```

Purpose: show how much expected late-delivery exposure comes from low, medium, or high-risk orders.

### 4. Expected OTD Exposure by Region

Type: bar chart or map.

```text
Axis: map_location_region
Value: expected_otd_exposure_pp
```

Purpose: identify where predicted risk creates the largest expected KPI exposure.

### 5. Operational Action Queue

Type: matrix.

Suggested columns:

```text
Region
Shipping Mode
Category
Historical OTD Rate
Expected OTD Rate
Expected OTD Exposure
High-Risk Orders
Service Protection Queue
Selective Expedite Review
Intervention Load Rate
AO3 Action Queue
```

Purpose: turn historical KPI context and predictive exposure into operational review priorities.

## Governance Rules

- Historical KPI fields may use post-delivery outcomes for descriptive dashboard reporting.
- Post-delivery outcome fields must not be used as predictors.
- Predictive exposure fields must be derived from governed AO1/AO2/AO3 outputs.
- Do not claim causal intervention impact.
- Do not redefine AO1, AO2, or AO3.
- Clearly distinguish historical performance from expected pre-dispatch KPI exposure.

## Interpretation Examples

Recommended wording:

```text
Historical OTD shows how fulfillment performance has behaved in the selected segment. Expected OTD uses AO1 predicted late-delivery probabilities to estimate pre-dispatch KPI exposure for the current scored population.
```

```text
Intervention Load Rate translates AO3 prioritization into operational workload, showing how much of the selected population requires active review before dispatch.
```

Avoid wording such as:

```text
The model proves that intervention will improve OTD by X percentage points.
```

Use instead:

```text
The model estimates an expected OTD exposure of X percentage points if the predicted late-delivery risks materialize.
```

## Dashboard Value

This layer strengthens the project by connecting descriptive, diagnostic, predictive, and decision-support analytics:

```text
Historical logistics KPI monitoring
+
AO1 expected late-delivery exposure
+
AO2 economic context
+
AO3 action queue prioritization
```

It shows that the model is not only a prediction artifact. It is a pre-dispatch logistics decision-support layer.
