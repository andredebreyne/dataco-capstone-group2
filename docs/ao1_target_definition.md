# AO1 Target Definition: Late Delivery Risk

Issue: `#63`
Milestone: `W1-Initiation`
Workstream: `Methodology`
Priority: `Core`

## Purpose

This note defines the AO1 target variable before late-delivery modeling begins. The goal is to make the target semantics explicit enough that all team members can apply the same rule when preparing Silver and Gold analytical tables.

AO1 predicts whether an order is at risk of late delivery using only information available at order creation or before dispatch. The target is an observed historical outcome, but it must not be used as a predictor or reconstructed through post-shipment fields.

## Source Fields Reviewed

The following target-related fields were reviewed in the raw DataCo structured dataset and companion metadata:

- `Late_delivery_risk`
- `Delivery Status`
- `Days for shipping (real)`
- `Days for shipment (scheduled)`
- `Order Status`
- `Shipping Mode`
- `order date (DateOrders)`
- `shipping date (DateOrders)`

The companion metadata defines `Late_delivery_risk` as:

> Categorical variable that indicates if sending is late (1), it is not late (0).

## Target Encoding

Use `Late_delivery_risk` as the AO1 binary classification target.

| Value | Operational meaning |
| --- | --- |
| `1` | The order is labeled as a late delivery. |
| `0` | The order is not labeled as a late delivery. This includes on-time, advance-shipped, and shipping-canceled records in the raw dataset. |

Observed target distribution in the structured DataCo file:

| `Late_delivery_risk` | Rows | Share |
| ---: | ---: | ---: |
| `0` | 81,542 | 45.17% |
| `1` | 98,977 | 54.83% |

There were no missing values in `Late_delivery_risk` in the reviewed dataset.

## Relationship to Delivery Status

`Late_delivery_risk` is perfectly aligned with `Delivery Status = Late delivery` in the reviewed data.

| `Delivery Status` | `Late_delivery_risk = 0` | `Late_delivery_risk = 1` |
| --- | ---: | ---: |
| `Advance shipping` | 41,592 | 0 |
| `Late delivery` | 0 | 98,977 |
| `Shipping canceled` | 7,754 | 0 |
| `Shipping on time` | 32,196 | 0 |

Operational rule:

- Treat `Late_delivery_risk = 1` as the historical late-delivery event for AO1.
- Treat `Delivery Status` as a post-delivery outcome and target proxy. It must not be used as an AO1 predictor.

## Relationship to Shipping-Day Fields

The dataset contains both planned and actual shipping duration fields:

- `Days for shipment (scheduled)`: scheduled delivery days
- `Days for shipping (real)`: actual shipping days

Most records align with the intuitive rule that actual shipping days greater than scheduled shipping days imply lateness. However, this rule does not exactly define the target because canceled shipments are encoded differently.

| `Days for shipping (real) > Days for shipment (scheduled)` | `Late_delivery_risk = 0` | `Late_delivery_risk = 1` |
| --- | ---: | ---: |
| `False` | 77,119 | 0 |
| `True` | 4,423 | 98,977 |

The 4,423 records where actual days exceed scheduled days but `Late_delivery_risk = 0` are all `Shipping canceled` records with `Order Status` equal to `CANCELED` or `SUSPECTED_FRAUD`.

Operational rule:

- Do not redefine AO1 target using shipping-day arithmetic.
- Use the provided `Late_delivery_risk` label as the target.
- Exclude `Days for shipping (real)` from AO1 predictors because it is an actual fulfillment duration known only after shipment/delivery.
- Treat `Days for shipment (scheduled)` as potentially available before dispatch, subject to the feature-availability matrix.

## Cancellation and Ambiguous Logistics Records

The raw dataset includes 7,754 `Shipping canceled` records:

| `Delivery Status` | `Order Status` | Rows | `Late_delivery_risk` |
| --- | --- | ---: | ---: |
| `Shipping canceled` | `CANCELED` | 3,692 | 0 |
| `Shipping canceled` | `SUSPECTED_FRAUD` | 4,062 | 0 |

These records are not labeled as late deliveries even when actual shipping days exceed scheduled days. They represent a target-semantics edge case: cancellation/fraud outcomes are different from completed delivery timeliness outcomes.

Recommended AO1 table rule:

- Exclude `Delivery Status = Shipping canceled` records from the primary AO1 modeling table unless the team explicitly decides that canceled/fraud orders should remain in the negative class.

Rationale:

- The AO1 business question is about late-delivery risk for orders that proceed through fulfillment.
- Canceled/fraud records are not operationally equivalent to successful non-late deliveries.
- Keeping them as `0` can contaminate the negative class by mixing non-late delivered orders with orders that were never completed as normal deliveries.

If the team decides to keep canceled/fraud records, this must be documented as a modeling caveat and evaluated in a sensitivity check.

## Reschedules

No explicit reschedule flag or reschedule timestamp was found in the reviewed structured dataset fields. The dataset includes scheduled shipping days and actual shipping days, but not a separate field that identifies whether the planned service promise changed after order creation.

Operational rule:

- Do not infer rescheduling from date differences alone.
- If a future metadata review identifies reschedule-specific fields, classify them in the feature-availability matrix before using them.
- Treat any post-order revised promise date as a post-order or review-only field unless the team can prove it is available before dispatch.

## Predictor Leakage Controls

The following fields are forbidden as AO1 predictors:

| Field | Reason |
| --- | --- |
| `Late_delivery_risk` | AO1 target |
| `Delivery Status` | Direct post-delivery target proxy |
| `Days for shipping (real)` | Actual fulfillment duration known after shipment/delivery |
| `shipping date (DateOrders)` | Shipment timestamp; not available at order creation |
| `Order Status` | May encode cancellation, fraud, payment, and fulfillment outcomes after order creation |

Fields that may be considered for AO1 only after feature-availability review:

| Field | Rule |
| --- | --- |
| `Days for shipment (scheduled)` | Allowed only if treated as the planned shipping service known before dispatch. |
| `Shipping Mode` | Allowed if selected by the customer/order process before dispatch. |
| `order date (DateOrders)` | Use only derived calendar features, not raw timestamp leakage patterns. |

## Recommended Primary AO1 Definition

Primary AO1 target:

```text
Late_delivery_risk
```

Primary AO1 population:

```text
Delivery Status != "Shipping canceled"
```

Primary AO1 event definition:

```text
Late_delivery_risk = 1
```

Primary AO1 non-event definition:

```text
Late_delivery_risk = 0
```

Primary caveat:

The target identifies orders labeled as late in the historical DataCo dataset. It should be interpreted as late-delivery risk for orders proceeding through fulfillment, not as a general order-exception or cancellation-risk target.

## Sensitivity Check

Before final AO1 model sign-off, run a sensitivity check comparing:

1. Primary table excluding `Shipping canceled` records.
2. Secondary table retaining `Shipping canceled` records as `Late_delivery_risk = 0`.

The final report should state whether this choice changes class balance, model performance, feature importance, or operational interpretation.

## Sign-Off Requirement

Before AO1 Gold-table work is finalized, the team should confirm:

- `Late_delivery_risk` remains the official AO1 target.
- `Delivery Status` and `Days for shipping (real)` are forbidden predictors.
- `Shipping canceled` records are excluded from the primary AO1 modeling table or explicitly retained with a documented caveat.
- Any downstream notebook or table applies the same exclusion rule consistently.
