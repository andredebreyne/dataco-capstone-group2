# AO2 Target and Predictor Policy

Issue: `#64`
Milestone: `W1-Initiation`
Workstream: `Methodology`
Priority: `Core`

## Purpose

This policy freezes the AO2 target definition and predictor rules before profitability preprocessing and modeling begin. AO2 estimates expected order-level profitability before dispatch, so the model must avoid target reconstruction from duplicate profit fields, realized profit ratios, or direct transformations of the target.

The goal is to keep AO2 useful for the AO3 risk-margin prioritization framework while preserving methodological defensibility.

## Primary AO2 Target

Use `Order Profit Per Order` as the primary AO2 regression target.

Metadata definition:

| Field | Metadata description | AO2 role |
| --- | --- | --- |
| `Order Profit Per Order` | Order Profit Per Order | Primary target |
| `Benefit per order` | Earnings per order placed | Duplicate/proxy profit outcome; forbidden as predictor |

Observed audit result:

- `Benefit per order` is exactly equal to `Order Profit Per Order` in the reviewed raw dataset.
- Therefore, `Benefit per order` must not be used as an AO2 predictor.

Primary target rule:

```text
ao2_target = "Order Profit Per Order"
```

Do not replace this target unless the team documents and approves a justified alternative before AO2 preprocessing is built.

## Why AO2 Needs a Strict Predictor Policy

AO2 is methodologically fragile because several financial fields are mechanically related to revenue, discount, margin, or profit. A model that uses duplicate profit fields or realized profit ratios may report strong metrics while only reconstructing an accounting formula.

The main AO2 model should estimate expected profit from order-time information. It should not use realized profit, duplicate profit, or realized margin fields as predictors.

## Forbidden Predictors for Main AO2 Model

These fields must be excluded from the main AO2 feature matrix.

| Field | Policy | Reason |
| --- | --- | --- |
| `Order Profit Per Order` | Forbidden | AO2 target. |
| `Benefit per order` | Forbidden | Exact duplicate of the AO2 target in the reviewed dataset. |
| `Order Item Profit Ratio` | Forbidden | Realized profit-margin field; can reconstruct or closely approximate target when combined with order value. |
| Any direct transformation of `Order Profit Per Order` | Forbidden | Direct target leakage. |
| Any direct transformation of `Benefit per order` | Forbidden | Duplicate target leakage. |
| Any realized profit-margin feature | Forbidden | Encodes realized profit relationship rather than order-time expectation. |

Observed audit result:

- `Order Profit Per Order = Benefit per order` exactly.
- `Order Item Profit Ratio` is effectively realized profit divided by `Order Item Total`, with small rounding differences.
- Including `Order Item Profit Ratio` would allow target reconstruction when combined with order value.

## Descriptive-Only Fields

The following fields may be used for descriptive analysis, data validation, target audit, and reporting caveats, but not as predictors in the main AO2 model.

| Field | Allowed descriptive use | Predictor use |
| --- | --- | --- |
| `Benefit per order` | Validate duplicate target semantics; compare metadata definitions. | Forbidden |
| `Order Item Profit Ratio` | Describe realized historical margin; validate AO3 margin logic after prediction. | Forbidden |
| Realized actual profit margin | Report historical outcomes only. | Forbidden |

If these fields appear in notebooks, tables, or dashboards, their use must be clearly labeled as descriptive or outcome-based.

## Conditionally Allowed Order-Time Financial Predictors

The following fields may be considered for AO2 predictors if the feature-availability matrix confirms they are known at order creation or before dispatch.

| Field | Policy | Notes |
| --- | --- | --- |
| `Order Item Total` | Review / conditionally allowed | Discounted order item value. Candidate AO3 denominator. Do not include alongside exact duplicate `Sales per customer`. |
| `Sales per customer` | Review / conditionally allowed | Exact duplicate of `Order Item Total` in the reviewed dataset. Prefer `Order Item Total` for clarity. |
| `Sales` | Review / conditionally allowed | Gross sales before discount; mechanically tied to price and quantity, not direct profit. |
| `Order Item Discount` | Review / conditionally allowed | Discount value; order-time availability must be confirmed. |
| `Order Item Discount Rate` | Review / conditionally allowed | Discount percentage; order-time availability must be confirmed. |
| `Order Item Product Price` | Review / conditionally allowed | Product price before discount; exact duplicate of `Product Price` in the reviewed dataset. |
| `Product Price` | Review / conditionally allowed | Duplicate of `Order Item Product Price`; prefer one field only. |
| `Order Item Quantity` | Review / conditionally allowed | Order quantity; order-time commercial input. |

Duplicate-field rule:

- Do not include duplicate fields that carry the same value under different names.
- Prefer business-readable order-level names where possible.
- Document the final selected financial predictors before model training.

Recommended initial AO2 financial predictor set, subject to team sign-off:

Primary AO2 value predictor:
- Order Item Total

Optional revenue-structure predictors for robustness:
- Order Item Discount Rate
- Order Item Quantity
- Order Item Product Price

Rule:
Do not treat the revenue-structure fields as profit predictors by themselves, and compare model results with and without them.

Do not include `Sales per customer` if `Order Item Total` is used. Do not include `Product Price` if `Order Item Product Price` is used.

## Non-Financial Predictor Policy

Non-financial order-time fields may be used for AO2 if they pass the feature-availability and leakage audits.

Examples of potentially valid predictors:

- `Type`
- `Category Name`
- `Customer Segment`
- `Market`
- `Order Region`
- `Order Country`
- `Order State`
- `Shipping Mode`
- derived order-date features from `order date (DateOrders)`
- product/category identifiers only if handled consistently and not used as high-cardinality leakage shortcuts

Fields that are post-shipment or post-order outcome fields remain forbidden under the general leakage-control plan.

## AO3 Expected Margin Rule

AO3 combines predicted late-delivery risk from AO1 with expected profitability from AO2. AO3 should use predicted profit, not actual profit, when assigning priority groups on validation or test data.

Define predicted profit margin as:

```text
predicted_profit_margin = predicted_order_profit / order_value
```

Use `Order Item Total` as the primary `order_value` denominator.

Rationale:

- `Order Item Total` is the discounted order item value.
- It is nonzero and positive in the reviewed dataset.
- It is exactly equal to `Sales per customer` in the reviewed dataset, but the name is clearer for order-level margin.
- It is more appropriate for margin than gross `Sales`, because gross sales excludes discount effects.

Implementation rule:

```text
ao3_order_value = "Order Item Total"
predicted_profit_margin = ao2_predicted_order_profit / ao3_order_value
```

Guardrail:

- If `Order Item Total <= 0` appears in future data, margin should be set to missing and the row should be flagged for review instead of dividing by zero or a nonpositive value.

## Viability and Fallback Rule

The current project should retain `Order Profit Per Order` as the AO2 target unless the team finds that AO2 remains a formula-reconstruction exercise even after excluding the forbidden fields.

If AO2 is not viable, the team may consider an alternative such as customer value, customer historical value, or contribution-margin classification. That would require a separate scope decision because it introduces additional complexity:

- time-aware customer history features
- risk of future customer behavior leakage
- a revised AO2 research objective
- revised AO3 business interpretation

Therefore, customer value should be treated as a fallback option, not the default target for issue `#64`.

## Required Review Checkpoint

Before AO2 preprocessing is built, the team should sign off on:

- `Order Profit Per Order` as the primary AO2 target.
- `Benefit per order` as a forbidden duplicate target field.
- `Order Item Profit Ratio` as a forbidden realized margin field.
- The selected order-time financial predictors.
- `Order Item Total` as the AO3 predicted-margin denominator.
- The fallback rule if AO2 is later judged not viable.

## Summary Policy

Primary AO2 target:

```text
Order Profit Per Order
```

Main forbidden AO2 predictors:

```text
Order Profit Per Order
Benefit per order
Order Item Profit Ratio
direct profit transformations
realized profit-margin fields
```

AO3 expected margin:

```text
predicted_profit_margin = predicted_order_profit / Order Item Total
```

The main AO2 model remains viable under the current project plan if duplicate profit fields and realized margin fields are excluded.
