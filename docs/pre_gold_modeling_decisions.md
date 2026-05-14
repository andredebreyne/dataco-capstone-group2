# Pre-Gold Modeling Decisions

This document records the team decisions required before freezing the first
model-ready Gold tables for AO1, AO2, and AO3.

These decisions prioritize leakage safety, decision-time validity,
interpretability, and a conservative first-pass Gold design. Where dataset
metadata is ambiguous, the team documents explicit working assumptions. These
assumptions should be revisited if later evidence contradicts them.

This document supersedes earlier pending-decision notes for first-pass Gold
modeling policy. It does not implement Gold tables, train models, change
feature engineering logic, set thresholds, or apply resampling.

## Decision 1 - AO1 Population

**Decision:** Primary AO1 Gold excludes canceled, suspected-fraud, and
shipping-canceled records from the main AO1 modeling population.

**Gold action:** Exclude records such as:

- `Delivery_Status = Shipping canceled`
- `Order_Status = CANCELED`
- `Order_Status = SUSPECTED_FRAUD`

These records may be retained in separate audit, sensitivity, or descriptive
dashboard outputs.

**Rationale:** AO1 is intended to predict late-delivery risk for orders that
enter the normal fulfillment process. Shipping-canceled or fraud-related records
are not normal completed delivery outcomes. Even if these records are labeled
`Late_delivery_risk = 0`, they should not be treated as standard non-late
deliveries because they represent a different operational event.

Including them in the primary negative class could cause the model to learn
cancellation or fraud patterns instead of true late-delivery risk.

**Final status:** Approved for first-pass Gold.

## Decision 2 - `Type`

**Decision:** `Type` is approved as a conditional order-creation candidate
feature for AO1 and AO2 in first-pass Gold, based on the team's documented
business assumption.

**Team assumption:** The team assumes that `Type` represents the payment
transaction type selected or recorded at order creation. The assumed meanings
are:

- `TRANSFER`: direct bank transfer
- `DEBIT`: debit card payment
- `CASH`: cash-on-hand payment
- `PAYMENT`: other payment types, primarily credit-based payments

Under this assumption, `Type` is considered known at or near order creation and
therefore available before dispatch. This is a team assumption because the
dataset metadata is not fully explicit.

**Gold action:** Include `Type` as a candidate feature in first-pass Gold, with
these caveats:

- Treat it as payment-method or transaction-type context.
- Do not interpret it as a delivery outcome.
- Do not use it as a proxy for fraud or cancellation status.
- Review unusually strong model effects during model interpretation.
- Remove or reclassify it if later evidence shows it is generated after payment
  review, fraud review, or order processing.

**Rationale:** With the team assumption that `Type` is a payment transaction
type known at order creation, it is decision-time valid. It may reasonably
influence operational prioritization or profitability because payment type can
relate to order processing, commercial behavior, or payment risk. However,
because the original dataset metadata does not fully explain the field, the
assumption must remain documented.

**Final status:** Conditionally approved for first-pass Gold based on documented
team assumption.

## Decision 3 - `Order_Item_Total`

**Decision:** `Order_Item_Total` will be used as the AO3 denominator for
predicted margin, but it will not be used as a primary AO2 predictor in
first-pass Gold.

**Gold action:** Use `Order_Item_Total` as the denominator for AO3 predicted
margin or risk-margin segmentation.

Exclude from first-pass AO2 predictors:

- `Order_Item_Total`

It may be revisited later in an AO2 sensitivity model.

**Rationale:** `Order_Item_Total` is commercially meaningful and useful for
calculating predicted margin in AO3. However, it is closely related to price,
quantity, discount, sales, and profit. Including it directly as an AO2 predictor
could increase target-reconstruction risk and make AO2 behave like an
accounting formula rather than a predictive profitability model.

**Final status:** Approved as AO3 denominator only. Excluded from primary AO2
predictors.

## Decision 4 - First-Pass AO2 Commercial Feature Set

**Decision:** First-pass AO2 Gold will use a minimal, non-duplicative commercial
feature set.

**Approved AO2 commercial candidate predictors:**

- `Order_Item_Product_Price`
- `Order_Item_Discount_Rate`
- `Order_Item_Quantity`

**Excluded from primary AO2 predictors:**

- `Order_Item_Total`
- `Sales`
- `Sales_per_customer`
- `Order_Item_Discount`
- `Product_Price`
- `Order_Item_Profit_Ratio`
- `Benefit_per_order`
- `Order_Profit_Per_Order`

**Gold action:** Use one price field, one discount-rate field, and one quantity
field for first-pass AO2 commercial context.

Do not include multiple sales, order-value, absolute-discount, duplicate-price,
or profit-ratio fields in the same first-pass AO2 predictor set.

**Rationale:** Many DataCo commercial fields are valid at order time, but they
are mathematically or economically related. Including all of them would increase
multicollinearity and target-reconstruction risk. The approved first-pass set
gives AO2 useful commercial context while keeping the model defensible.

**Final status:** Approved for first-pass Gold.

## Decision 5 - Product-Level Descriptors

**Decision:** Direct product-level descriptors and product IDs remain excluded
from first-pass Gold.

**Gold action:** Use first-pass product-mix features such as:

- product category
- product department

Exclude first-pass direct product-level fields such as:

- `Product_Name`
- `product_name_normalized`
- product IDs
- product catalog keys
- direct product-level identifiers

**Rationale:** Product names, product IDs, and catalog keys may contain useful
product-mix information, but they are higher-cardinality and potentially
unstable. Including them directly in first-pass Gold could increase overfitting
risk and reduce interpretability.

Category and department provide a more stable and interpretable first-pass
representation of product mix.

**Future action:** Grouped product features may be considered later using
documented rules such as top-N grouping, frequency thresholds, or category
hierarchy. Any such design should be implemented after the first-pass Gold and
baseline modeling workflow are stable.

**Final status:** Excluded from first-pass Gold. Deferred to future
grouped-feature design.

## Decision 6 - Granular Geography

**Decision:** Granular geography remains excluded from first-pass Gold.

**Gold action:** Use coarse geographic fields such as:

- `Market`
- `Order_Region`
- `Order_Country`
- `Customer_Country`
- `Customer_Segment`

Exclude first-pass granular geography fields such as:

- `Customer_City`
- `Order_City`
- postal codes
- precise coordinates
- granular region keys
- city-region composite keys

**Rationale:** Granular geography fields may be decision-time available, but
they are often high-cardinality, missing-heavy, unstable, or too granular for a
conservative first-pass model. They may also increase overfitting risk and
complicate interpretation.

Coarse market, region, and country fields provide interpretable regional context
while keeping the first Gold design simpler and more stable.

**Future action:** Granular geography may be revisited later through documented
grouping, binning, or top-N rules. These rules should be designed before
inclusion and should respect train-only preprocessing requirements where
applicable.

**Final status:** Excluded from first-pass Gold. Coarse geography approved.

## Decision 7 - Historical Aggregate Features

**Decision:** Historical customer, product, city, region, and category
aggregates are in scope for a future issue, but not for first-pass Gold.

**Gold action:** Do not include historical aggregates in the first model-ready
Gold tables.

Examples of deferred historical aggregates include:

- customer historical late-delivery rate
- product historical late-delivery rate
- category historical profitability
- region historical delay rate
- customer historical average profit
- market-level historical discount or profitability behavior

**Rationale:** Historical aggregates could be useful, but they create high
leakage risk if computed using future records or the full dataset before
splitting. They require strict time-aware and train-only computation. Adding
them before the first-pass Gold tables would increase complexity and risk.

**Future action:** Create a separate future feature-engineering issue for
time-aware historical aggregates. Acceptance criteria should require:

- chronological split awareness
- training-only fitting
- no future information leakage
- clear handling of test-period records
- documentation of smoothing, missing history, and frequency thresholds

**Final status:** Deferred to future issue. Excluded from first-pass Gold.

## Final First-Pass Gold Policy

### AO1 Primary Population

Primary AO1 Gold includes normal fulfilled or fulfillment-eligible orders.

Primary AO1 Gold excludes:

- shipping-canceled records
- canceled orders
- suspected-fraud records
- post-shipment outcomes
- post-delivery outcomes
- actual shipping duration fields
- delivery status fields
- shipping date fields

Excluded records may be retained for audit, sensitivity analysis, or descriptive
dashboard outputs.

### AO1 Primary Feature Policy

Approved or conditionally approved first-pass AO1 feature groups include:

- order-time date features
- scheduled shipping duration
- shipping mode or shipping speed tier
- coarse market, region, and country fields
- customer segment
- product category and department
- `Type`, conditionally approved as a team-assumed payment transaction type

Excluded or deferred AO1 feature groups include:

- delivery outcomes
- actual fulfillment duration
- shipping date
- direct product IDs or product names
- granular city, postal code, and coordinate fields
- historical aggregates

### AO2 Target Policy

Primary AO2 target:

- `Order_Profit_Per_Order`

If unavailable, `Benefit_per_order` may be used only if documented as the
equivalent raw order-level profit target.

AO2 target and target-equivalent fields must never be used as predictors.

### AO2 Primary Commercial Predictor Policy

Approved first-pass AO2 commercial predictors:

- `Order_Item_Product_Price`
- `Order_Item_Discount_Rate`
- `Order_Item_Quantity`

Excluded from primary AO2 predictors:

- `Order_Item_Total`
- `Sales`
- `Sales_per_customer`
- `Order_Item_Discount`
- `Product_Price`
- `Order_Item_Profit_Ratio`
- `Benefit_per_order`
- `Order_Profit_Per_Order`

### AO3 Policy

AO3 uses:

- predicted AO1 late-delivery risk
- predicted AO2 profitability
- `Order_Item_Total` as the denominator for predicted margin

`Order_Item_Total` is approved for AO3 margin construction but remains excluded
from the primary AO2 predictor set.

## Remaining Validation Notes

The following decisions are approved for first-pass Gold but should be revisited
during model interpretation or sensitivity analysis:

1. `Type` is included based on a team assumption that it represents
   order-creation payment transaction type. If later evidence suggests it is
   generated after payment review, fraud review, or order processing, it should
   be removed from predictive modeling.
2. Commercial AO2 fields are intentionally limited to avoid target
   reconstruction. Alternative commercial specifications may be tested later,
   but the first-pass model should remain conservative.
3. Direct product-level, granular geographic, and historical aggregate features
   are deferred, not permanently rejected. They may be added later only with
   documented grouping or time-aware train-only logic.

