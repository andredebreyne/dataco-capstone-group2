# AO2 Bivariate Profitability EDA Findings

Issue: `[W3][P1][#3] Bivariate EDA: profitability drivers #20`

## Purpose

This report note summarizes the focused AO2 bivariate EDA results produced from
the local Silver clone. It is intended for review and later report drafting. It
does not approve final AO2 modeling predictors, train models, or finalize Gold
tables.

Related artifacts:

- `notebooks/eda/ao2_bivariate_profitability_eda.py`
- `docs/ao2_bivariate_eda.md`
- `report/tables/ao2_profitability_bivariate_summary.csv`
- `report/tables/ao2_profitability_bivariate_detail_by_group.csv`
- `report/tables/ao2_profitability_group_validation_list.csv`

## Dataset And Target Audit

The EDA used:

```text
data/silver/dataco_orders_silver.csv
```

The loaded Silver clone contains 180,519 rows and 53 columns. The AO2 target is
`Order_Profit_Per_Order`; no fallback target was used.

Target summary:

| Statistic | Value |
| --- | ---: |
| Valid rows | 180,519 |
| Missing target rows | 0 |
| Mean profit | 21.97 |
| Median profit | 31.52 |
| Standard deviation | 104.43 |
| Minimum | -4,274.98 |
| Maximum | 911.80 |
| 1st percentile | -415.60 |
| 5th percentile | -139.25 |
| 25th percentile | 7.00 |
| 75th percentile | 64.80 |
| 95th percentile | 132.29 |
| 99th percentile | 184.23 |
| Skewness | -4.742 |
| IQR outlier count | 18,942 |

`Benefit_per_order` matches `Order_Profit_Per_Order` exactly in the local Silver
clone and is therefore treated as a duplicate profit outcome, not a predictor.
`Order_Item_Profit_Ratio` exists and is excluded from predictors as a realized
profit-ratio/proxy field.

## Screening Coverage

The EDA reviewed 101 variables from the conceptual leakage screening table and
derived review features. Recommended actions were:

| Recommended action | Count |
| --- | ---: |
| `candidate_for_gold_review` | 39 |
| `conditional_requires_group_review` | 42 |
| `dashboard_only` | 5 |
| `target_or_proxy_excluded` | 3 |
| `exclude_from_ao2_modeling` | 9 |
| `descriptive_context_only` | 3 |

The output includes 286 detailed group/bin rows and 45 group-validation rows.
The group-validation list includes conditional variables plus relevant
financial, commercial, and profit-policy fields.

## Main Descriptive Findings

Department and category mix show the strongest support-safe descriptive
profitability differences among non-outcome fields.

| Variable | Review status | Pattern |
| --- | --- | --- |
| `Department Name` | Candidate for Gold review | Technology had the highest supported mean profit at 77.25; Discs Shop had the lowest at 11.94. |
| `product_department_key` | Candidate for Gold review | Mirrors the department pattern; strongest supported difference from overall mean profit was 55.27. |
| `Category Name` | Candidate for Gold review | Fishing had the highest supported mean profit at 43.65; Golf Balls had the lowest at 5.66. |
| `product_category_key` | Candidate for Gold review | Mirrors the category pattern; strongest supported difference from overall mean profit was 21.67. |

These product-mix signals are plausible AO2 candidates for later Gold review,
but the bivariate results should not be interpreted causally. Final modeling
still needs chronological splits and train-only preprocessing.

## Commercial And Financial Patterns

Several commercial fields show clear descriptive gradients with historical
profit. These are useful for review, but they remain conditional because they may
contribute to target reconstruction or duplicate one another.

| Variable | Current treatment | Pattern |
| --- | --- | --- |
| `Sales` | Conditional group review | Mean profit increased across supported bins; highest bin mean was 46.27 and lowest bin mean was 7.41. |
| `item_gross_sales_estimate` | Conditional group review | Mirrors the gross-sales pattern and requires review before modeling. |
| `Order Item Total` | Conditional group review | Mean profit increased across supported bins; highest bin mean was 42.81 and lowest bin mean was 6.89. |
| `Sales per customer` | Descriptive only or exclude duplicate pending group decision | Matches the order-value pattern and may duplicate `Order Item Total`. |
| `item_net_sales_amount` | Conditional group review | Mirrors the net order-value pattern and requires duplicate-field review. |
| `Product Price` | Descriptive only or exclude duplicate pending group decision | Mean profit increased across supported price bins. |
| `Order Item Product Price` | Descriptive only or exclude duplicate pending group decision | Duplicates or closely overlaps product price information. |
| `Order Item Discount` | Conditional group review | Shows a nonlinear or uneven profit pattern across discount-amount bins. |
| `Order Item Discount Rate` | Conditional group review | Useful for discount-intensity review, but not approved as a predictor in this issue. |
| `Order Item Quantity` | Conditional group review | Treated conservatively as commercial order-composition information. |

The EDA prepares these variables for group validation. It does not approve them
as AO2 modeling predictors.

## Excluded Target, Proxy, And Outcome Fields

The following fields are excluded from AO2 predictor use because they are the
target, duplicate target/profit outcomes, or direct profit proxies:

- `Order Profit Per Order`
- `Benefit per order`
- `Order Item Profit Ratio`

The following post-outcome or dashboard-only fields are also kept out of AO2
predictor review:

- `Days for shipping (real)`
- `Delivery Status`
- `shipping date (DateOrders)`
- `Order Status`
- `Late_delivery_risk`

Sensitive identifiers and low-value personal fields remain excluded from
modeling, including customer email, first name, last name, password, street, and
raw order identifiers.

## Group Decisions Needed Before AO2 Modeling

Before AO2 Gold/modeling work, the project owner or team should decide:

1. Whether `Order Item Total` is the single approved order-value field for AO2
   review and AO3 margin denominator logic.
2. Whether `Sales per customer` should remain descriptive-only because it may
   duplicate `Order Item Total`.
3. Whether `Sales`, gross-sales estimates, price fields, quantity fields, and
   discount fields are known before dispatch and acceptable for modeling without
   mechanically reconstructing profit.
4. Which duplicate commercial fields should be excluded so the AO2 model does
   not receive the same economic quantity under multiple names.
5. Whether high-cardinality product, city, regional-key, or identifier-like
   fields require grouping, frequency thresholds, or train-only historical
   aggregate designs before modeling.

## Caveats

- Bivariate EDA identifies associations, not causal effects.
- Profit is skewed and outlier-sensitive; mean and median patterns should both
  be reviewed.
- Commercial and order-value fields may be descriptively useful but remain
  vulnerable to target-reconstruction risk.
- Conditional or `needs_group_review` variables require team validation before
  modeling.
- Final AO2 features must still be selected later using leakage controls,
  chronological split rules, and train-only preprocessing.
