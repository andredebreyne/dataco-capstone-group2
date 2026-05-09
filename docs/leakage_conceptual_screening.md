# Conceptual Leakage Screening

Issue: `[W2][P0][#6] Leakage audit: conceptual screening of all variables`

## Purpose

This document summarizes the conceptual leakage screening artifact for raw and engineered DataCo variables. The reviewed table is stored at:

```text
data/references/leakage_conceptual_screening.csv
```

The screening table should be used before Gold table construction and before AO1 or AO2 modeling feature lists are finalized. It translates the existing decision-time feature availability map and feature-engineering documentation into a single reviewer-facing policy table.

This document does not replace the broader leakage rules in `docs/leakage_control_plan.md`, the raw-field availability map in `docs/feature_availability_map.md`, or the AO2 target policy in `docs/ao2_target_policy.md`.

## How to Use the Table

Use the table as a gate before building model-ready features:

- Include only variables marked `allowed` as direct candidates, subject to normal Gold-table review.
- Treat variables marked `conditional` as requiring group sign-off before modeling.
- Exclude variables marked `forbidden` from predictive inputs.
- Use variables marked `target` only as AO1 or AO2 targets, never predictors.
- Keep `dashboard_only` fields separate from AO1 and AO2 predictor matrices.
- Treat `restricted` dashboard fields as not approved for ordinary dashboard use because they are sensitive identifiers or low-value personal fields.

The table is conceptual. It does not run models, build Gold tables, encode variables, or apply train/test logic.

## Policy Definitions

| Policy | Meaning |
| --- | --- |
| `allowed` | Decision-time valid candidate for AO1 or AO2, with final inclusion deferred to Gold/modeling review. |
| `forbidden` | Target, post-shipment outcome, sensitive identifier, non-operational identifier, or direct target proxy that must not be used as a predictor. |
| `conditional` | Potentially valid but requires group review because of AO2 target-reconstruction risk, high cardinality, duplicate fields, stability, or privacy concerns. |
| `target` | Official target field for an analytical objective. |
| `dashboard_only` | Valid for descriptive reporting, outcome audit, or governance views, but not predictive modeling. |
| `restricted` | Not approved for ordinary dashboard use because the field is sensitive, personal, or too granular for the project outputs. |
| `not_applicable` | Policy does not apply, usually because the row is processing metadata rather than a business feature. |

## Coverage

The screening table covers:

- 53 raw DataCo fields from `data/references/feature_availability_map.csv`
- 10 order-time engineered variables from `docs/order_time_features.md`
- 19 shipping/product engineered variables from `docs/shipping_product_features.md`
- 19 customer/regional engineered variables from `docs/customer_regional_features.md`

## Key Findings

- `Late_delivery_risk` is the AO1 target and is not an AO1 predictor.
- `Order Profit Per Order` is the AO2 target and is not an AO2 predictor.
- `Benefit per order` and `Order Item Profit Ratio` remain descriptive or audit fields only because they duplicate or directly proxy realized profit.
- Delivery outcome and fulfillment fields such as `Delivery Status`, `Days for shipping (real)`, `shipping date (DateOrders)`, and `Order Status` are forbidden as predictive inputs and separated as dashboard/audit fields where appropriate.
- Order-time date features derived only from `order_date_DateOrders` are allowed candidates.
- `Sales per customer` is treated as a conditional order-value field based on the current AO2 policy. Despite its name, it should not be treated as an approved customer-history aggregate unless the team separately confirms its semantics.
- Raw `Order Item Quantity` is decision-time valid, while engineered `order_item_quantity` remains AO2-conditional because final AO2 use should be reviewed together with selected price, discount, and order-value predictors.
- AO2 commercial value features remain conditional until the team signs off on a non-reconstructive financial predictor set.
- High-cardinality product, customer, city, region-key, and coordinate features remain conditional until grouping, stability, privacy, and training-only encoding decisions are documented.

## Group Review Required

The following groups require review before modeling:

- AO2 financial/value fields and engineered value features, including sales, discounts, prices, order totals, gross-sales estimates, net-sales amounts, and discount-share features.
- Duplicate or near-duplicate commercial fields, especially `Sales per customer` versus `Order Item Total` and `Product Price` versus `Order Item Product Price`.
- Product identifiers and descriptors, including product catalog keys and normalized product names.
- Customer or destination city, postal, coordinate, and composite region-key features.
- Customer or product IDs if the team later considers time-aware historical aggregates.
- `Product Status` and `product_status_flag`, pending confirmation of business meaning.

## Limitations

This audit is a conceptual screening step only. It does not replace:

- chronological train/validation/test splitting
- fit-on-training-only preprocessing
- target exclusion checks in model pipelines
- post-model leakage review
- AO2 residual and feature-importance review for target reconstruction
- AO3 validation that risk-margin groups are assigned from predictions rather than actual outcomes
