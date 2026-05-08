# Decision-Time Feature Availability Map

Task: `[W2][P0][#3 - #65] Create decision-time feature availability map`

Issue: `#65`

## Purpose

This document explains the DataCo decision-time feature availability map. The map is a core methodology artifact used to prevent data leakage before AO1, AO2, and AO3 modeling tables are finalized.

The versioned matrix is stored at:

```text
data/references/feature_availability_map.csv
```

The matrix classifies each structured DataCo source field by when it becomes known in the real process and how it may be used for modeling, dashboarding, or validation.

## Decision-Time Rule

The project supports pre-shipment decision making. A predictor is eligible for modeling only if it is known at order creation or can be derived from information available before dispatch.

Fields known after shipment, after delivery, or only after business outcome realization must not be used as predictive inputs.

## Matrix Columns

| Column | Meaning |
| --- | --- |
| `source_column` | Original DataCo source field name. |
| `silver_column` | Project Silver-layer column name after Delta-compatible cleaning. |
| `semantic_group` | Business grouping used for review. |
| `availability_timing` | When the field becomes known in the business process. |
| `ao1_policy` | Use policy for AO1 late-delivery modeling. |
| `ao2_policy` | Use policy for AO2 profitability modeling. |
| `dashboard_policy` | Whether the field may be used for descriptive reporting. |
| `modeling_use` | Recommended modeling treatment. |
| `rationale` | Short reason for the classification. |
| `derived_feature_guidance` | Guidance for feature engineering or exclusion. |
| `related_document` | Primary project document supporting the decision. |

## Availability Timing Values

| Value | Meaning |
| --- | --- |
| `order_creation` | Known when the order is created. |
| `before_dispatch` | Known after order creation but before shipment or dispatch. |
| `after_shipment` | Known only after shipment starts or is recorded. |
| `after_delivery` | Known only after delivery outcome is observed. |
| `after_order_review` | May encode post-order payment, cancellation, fraud, or processing outcomes. |
| `target_or_outcome` | Target, duplicate target, realized outcome, or target proxy. |
| `sensitive_identifier` | Personal, masked, or high-risk identifier. |
| `descriptive_only` | Retained for audit, metadata, or dashboard use, but not modeling. |

## Policy Values

| Value | Meaning |
| --- | --- |
| `allowed` | Eligible as a modeling candidate if downstream preprocessing is fit correctly. |
| `review` | Potentially usable, but requires a documented modeling decision. |
| `forbidden` | Must not be used as a predictor. |
| `target` | Official target field for the related analytical objective. |

## Modeling Use Values

| Value | Meaning |
| --- | --- |
| `direct_candidate` | Can be considered directly as a candidate feature after normal preprocessing. |
| `derived_only` | Use only through approved derived features, not as a raw field. |
| `training_only_aggregate` | May be used only for time-aware historical aggregates fit on training data only. |
| `join_key_only` | Use only for traceability, joins, deduplication, or validation. |
| `review` | Requires explicit feature-selection review before modeling. |
| `dashboard_only` | Use for descriptive reporting or validation, not prediction. |
| `exclude` | Exclude from modeling feature sets. |

## AO1 Controls

AO1 predicts late-delivery risk before shipment.

Forbidden AO1 predictor groups include:

- the AO1 target `Late_delivery_risk`
- delivery outcome fields such as `Delivery_Status`
- actual fulfillment duration such as `Days_for_shipping_real`
- shipment timestamp `shipping_date_DateOrders`
- order outcome/status fields that may encode cancellation, fraud, or fulfillment state

Planned shipping fields such as `Days_for_shipment_scheduled` and `Shipping_Mode` are eligible because they represent planned service information expected before dispatch.

## AO2 Controls

AO2 estimates order-level profitability before dispatch.

Forbidden AO2 predictor groups include:

- the AO2 target `Order_Profit_Per_Order`
- duplicate profit outcome `Benefit_per_order`
- realized profit ratio `Order_Item_Profit_Ratio`
- direct transformations of profit or realized margin

Order-time commercial fields such as price, quantity, discount, and order value are marked as `review` because they may be valid predictors, but the final AO2 feature set must avoid duplicate value fields and target reconstruction.

## Dashboard-Only Fields

Some fields are forbidden for prediction but still useful for validation or reporting. Examples include:

- `Delivery_Status`
- `Days_for_shipping_real`
- `shipping_date_DateOrders`
- realized profit and margin fields

These fields may support descriptive dashboards, target audits, and business interpretation, but they must not enter model predictor matrices.

## High-Cardinality and Identifier Rules

Identifiers and high-cardinality fields require conservative handling.

Rules:

- Personal identifiers are excluded.
- Raw order and order-item IDs are join keys only.
- Customer and product IDs are not direct predictors by default.
- Customer, product, region, or category historical aggregates must be computed with time-aware logic and fit on training data only.
- High-cardinality categorical fields require review before one-hot encoding, grouping, or frequency thresholding.

## Relationship to Feature Engineering Tasks

The map supports and constrains the W2 feature-engineering tasks:

- Order-time date features use `order_date_DateOrders` as `derived_only`.
- Shipping and product features use planned shipping and order-time product/commercial fields.
- Customer and regional features use customer segment, coarse geography, market, and destination fields while excluding personal identifiers and street-level detail.

Feature-engineering outputs may keep traceability keys and lineage columns, but final modeling feature matrices must still apply this availability map and the leakage-control plan.

## Update Rule

This map must be updated when:

- a new source field is introduced
- a field's business meaning changes
- a feature-engineering task adds derived predictors
- AO1 or AO2 target definitions change
- peer review identifies an ambiguous or risky field

Ambiguous fields should remain `review` until the team documents and approves a clear policy.

## Review Checklist

Before Gold analytical tables are finalized, reviewers should confirm:

- every modeling candidate is represented in the map
- target and post-outcome fields are excluded from predictor lists
- dashboard-only fields are not used in model training
- AO2 financial fields cannot reconstruct the profit target
- historical aggregates are deferred to training-only pipelines
- ambiguous fields are either resolved or explicitly marked `review`
