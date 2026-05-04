# Leakage-Control Plan

Task: `[W1][P0][#5] Develop the leakage-control plan`

Related issue: `#7`

## Purpose

This protocol defines the project rules for preventing data leakage in the DataCo Capstone analytics pipeline. The project objective is to support pre-shipment decisions, so modeling inputs must reflect information that would be available at order creation or before dispatch.

Leakage control applies to:

- AO1: late-delivery risk prediction
- AO2: order-level profitability estimation
- AO3: risk-margin prioritization using AO1 and AO2 outputs

## Decision-Time Rule

The primary rule is:

> A feature may be used for modeling only if it is known at order creation or can be derived using information available before shipment.

Any field generated during fulfillment, after shipment, after delivery, or as a direct transformation of the target must be excluded from predictive features.

## Target Definitions

AO1 target:

- `Late_delivery_risk`
- Binary classification target indicating whether an order was delivered late.

AO2 target:

- The AO2 target must be the verified raw order-level profit field from the official metadata.
- The preferred target is `Order Profit Per Order` if confirmed by the dataset schema and metadata.
- If the dataset uses `Benefit per order` as the equivalent raw order-level profit outcome, `Order Profit Per Order` is still preferred.
- Whichever field is selected as the AO2 target, equivalent profit fields, duplicate profit fields, profit ratios, and direct transformations of the target must be excluded from predictors.

AO3 inputs:

- AO1 predicted late-delivery risk
- AO2 predicted profitability or derived predicted margin

AO3 must use model outputs from held-out data when evaluating final test performance. It must not use actual target values to define priority groups during test evaluation.

## Forbidden Variables

The following fields are forbidden as predictive inputs because they are targets, post-shipment outcomes, direct target proxies, or non-operational identifiers.

### Always Forbidden for AO1

| Field | Reason |
| --- | --- |
| `Late_delivery_risk` | AO1 target |
| `Delivery Status` | Direct post-delivery outcome and target proxy |
| `Days for shipping (real)` | Actual shipping duration known only after shipment/delivery |
| `shipping date (DateOrders)` | Post-order fulfillment timestamp |
| `Order Status` | May encode fulfillment or cancellation outcome after order creation |

### Always Forbidden for AO2

| Field | Reason |
| --- | --- |
| `Order Profit Per Order` | AO2 target |
| `Benefit per order` | Same economic outcome as the target or direct duplicate/proxy |
| `Order Item Profit Ratio` | Direct profit-derived ratio that can reconstruct the target |
| Direct transformations of profit | Any field mathematically derived from the selected profit target would create target reconstruction risk. |

### AO2 Financial Predictor Policy

AO2 financial predictors must be classified as `Allowed`, `Forbidden`, or `Review` before modeling.

Price, quantity, discount, sales, and order-value fields may be used only if they are available at order creation or before dispatch and do not mechanically reconstruct the selected AO2 target.

Profit fields, profit ratios, duplicate profit outcomes, post-order adjustment fields, and direct target transformations are forbidden as AO2 predictors unless explicitly approved for descriptive use only.

Any financial field included in AO2 must have a short justification documenting why it is decision-time valid and why it does not directly reconstruct the selected profit target.

### Forbidden Unless Explicitly Approved for Descriptive Use Only

| Field | Reason |
| --- | --- |
| `Customer Email` | Masked identifier, not useful for modeling |
| `Customer Fname` | Personal identifier |
| `Customer Lname` | Personal identifier |
| `Customer Password` | Masked sensitive field |
| `Customer Street` | High-cardinality address detail |
| `Product Image` | URL/text asset, not part of structured pre-shipment model |
| `Product Description` | Empty in the raw dataset |

These fields may be retained in Bronze for raw traceability, but they should not enter Silver analytical modeling tables unless a documented exception is approved.

## Conditionally Allowed Variables

Some fields may be available at order time but still require review before modeling.

| Field group | Rule |
| --- | --- |
| Order date fields | Allowed only when transformed into pre-shipment date features such as year, month, week, day of week, or seasonality indicators. |
| Customer and product IDs | Allowed only if used carefully for historical aggregates fit on training data only. Raw high-cardinality IDs should not be used directly by default. |
| Geographic fields | Allowed for modeling if they are known at order time. External geographic enrichment is allowed for dashboarding only unless separately approved. |
| Discount and sales fields | Allowed for AO2 only if they are known before dispatch and do not directly encode final profit. |
| Scheduled shipping fields | Allowed if they represent planned service information known before shipment. |

## Train/Test and Validation Protocol

The split strategy must reflect the project objective of predicting future orders from historical orders.

Required split:

- Sort by `order date (DateOrders)`.
- Reserve the most recent 20% of observations as the final held-out test set.
- Use the earlier 80% as the development sample for training, validation, and limited hyperparameter tuning.

No random final train/test split should be used for the official project results.

## Fit-on-Training-Only Rule

All learned preprocessing must be fit on training data only and then applied unchanged to validation and test data.

This includes:

- Missing-value imputers
- Encoders
- Scalers
- SMOTE or other resampling methods
- Feature selectors
- Hyperparameter tuning
- Historical aggregates
- Customer, product, region, or category performance summaries

For historical aggregates, the aggregation logic must avoid using future rows to describe earlier rows. If row-level historical aggregates are added, they must be computed with time-aware logic.

## AO1-Specific Controls

AO1 predicts late-delivery risk before shipment.

Required controls:

- Exclude all actual fulfillment duration and delivery outcome fields.
- Evaluate class imbalance before choosing resampling.
- Apply SMOTE or comparable resampling only inside the training fold.
- Review unusually high performance as a potential leakage signal.
- Inspect top feature importances for post-event proxies.

## AO2-Specific Controls

AO2 estimates profitability before dispatch.

Required controls:

- Exclude the target and direct profit-derived ratios from feature inputs.
- Avoid features that mathematically reconstruct `Order Profit Per Order`.
- Document any financial fields included as predictors and explain why they are available before dispatch.
- Review residuals and feature importance for signs of target reconstruction.

## AO3-Specific Controls

AO3 combines AO1 predicted late-delivery risk and AO2 predicted profitability or derived predicted margin into a risk–margin prioritization framework.

Required controls:

- AO3 priority groups must be created from model predictions, not actual target values, during validation or final test evaluation.
- AO3 thresholds must be defined using training or validation data only, not the final held-out test set.
- The combined risk–margin framework must be compared against single-signal prioritization views:
  - late-delivery-risk-only prioritization
  - expected-profitability-only prioritization
  - combined risk–margin prioritization
- This comparison is required to support H3 and demonstrate whether the combined framework adds decision value beyond either signal alone.

## Conceptual Leakage Audit

Before modeling, every candidate feature must be classified into one of these categories:

- `Allowed`: available at order creation or before dispatch.
- `Forbidden`: target, post-event outcome, identifier, or direct proxy.
- `Review`: potentially available but requires justification.

The Silver-layer analytical table should include only `Allowed` fields and explicitly approved `Review` fields.

## Post-Model Leakage Audit

After modeling, the team must run a second leakage review.

Review triggers:

- Near-perfect or implausibly high model performance.
- Feature importance dominated by outcome-like variables.
- Features derived from dates or statuses that may encode fulfillment completion.
- AO2 performance suggesting profit reconstruction instead of estimation.
- Large validation/test performance gap inconsistent with normal model variance.

If leakage is suspected, the model must be rerun after removing the suspect field or transformation.

## Documentation Requirements

Each modeling PR must document:

- Target variable used.
- Final feature list or feature-generation logic.
- Forbidden fields removed.
- Split method.
- Preprocessing objects fit only on training data.
- Any approved exceptions.
- Validation and test metrics.
- For AO3, comparison of combined risk–margin prioritization against risk-only and profit-only prioritization.
  
## Peer Review Checklist

Before moving leakage-sensitive tasks to `Done`, at least one reviewer should confirm:

- The target is not included in the feature matrix.
- Forbidden post-shipment variables are excluded.
- The final test set is chronological and held out.
- Preprocessing is fit on training data only.
- Resampling, if used, is applied only to training data.
- AO2 predictors cannot reconstruct the target.
- AO3 priority groups are based on predictions and are compared against risk-only and profit-only prioritization.
- Assumptions and exceptions are documented.

## Known Assumptions and Limitations

- The dataset is public, anonymized, and partially synthetic.
- The project is an academic decision-support prototype, not a production deployment.
- Some fields may be ambiguous without business-system documentation; ambiguous fields must be treated conservatively.
- Bronze data remains raw and unchanged. Leakage controls are enforced in Silver and Gold transformations.
- External geographic enrichment, if used, is for dashboard mapping only unless the team approves a modeling use case separately.
