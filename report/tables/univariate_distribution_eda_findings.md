# Univariate Distribution EDA Findings

Issue: `[W3][P1][#1] Univariate EDA: distributions and outliers #18`

## Purpose

This report note summarizes the univariate EDA results from branch
`origin/18-w3p11-univariate-eda-distributions-and-outliers`. It is intended for
review and later Gold-table variable screening. It documents missingness,
cardinality, numeric ranges, IQR outliers, and review status for variables
marked `conditional_review` or `needs_group_review` in the conceptual leakage
screening artifact.

This note does not approve final AO1 or AO2 modeling predictors. The issue 18
`approved_for_gold` label should be interpreted as univariate data-quality
evidence only and must still be reconciled with leakage, target-reconstruction,
identifier, and high-cardinality policies from issues 19, 20, and 21.

Current workflow artifacts:

- `notebooks/eda/eda_univariate_distribution_analysis.py`
- `report/tables/eda_univariate_summary.csv`
- `report/figures/eda/*.png`

Historical issue 18 notebook artifacts:

- `notebooks/eda/eda_univariate_distribution_analysis_exploratory.ipynb`
- `notebooks/eda_univariate_summary.csv`
- `notebooks/figures/*.png`

## Dataset And Scope

The notebook output shows the source data was loaded from:

```text
data/bronze/dataco/DataCoSupplyChainDataset.csv
```

The loaded dataset contained 180,519 rows and 53 columns. The review set
contained 41 variables from `data/references/leakage_conceptual_screening.csv`
where `screening_status` was `conditional_review` or `needs_group_review`.

Review coverage:

| Status from summary | Count |
| --- | ---: |
| `numeric` | 26 |
| `categorical` | 8 |
| `datetime` | 1 |
| `missing_in_dataset` | 6 |

Recommendation counts:

| Issue 18 decision | Count |
| --- | ---: |
| `approved_for_gold` | 28 |
| `needs_group_review` | 13 |

## Variables Marked Approved By Univariate Checks

Issue 18 marked these variables `approved_for_gold` based on univariate
availability, missingness, cardinality, and outlier checks:

```text
Category Id
Customer Id
Customer Zipcode
Department Id
item_discount_rate
item_gross_sales_estimate
item_net_sales_amount
Latitude
latitude_rounded
Longitude
longitude_rounded
Order Customer Id
order date (DateOrders)
Order Item Cardprod Id
Order Item Discount
Order Item Discount Rate
Order Item Product Price
Order Item Total
order_item_quantity
order_region_key
Product Card Id
Product Category Id
Product Price
Product Status
product_status_flag
Sales
Sales per customer
Type
```

Important interpretation: some of these remain risky for modeling even if their
univariate distribution is usable. In particular, raw IDs, granular geography,
commercial fields, raw order timestamp, and product status still require
methodological approval before inclusion in model-ready Gold tables.

## Variables Still Needing Group Review

Issue 18 kept these variables as `needs_group_review`:

```text
Customer City
customer_city_normalized
customer_region_key
item_discount_amount
item_discount_share_of_gross
item_unit_price
Order City
Order Zipcode
order_city_normalized
Product Name
product_catalog_key
product_list_price
product_name_normalized
```

The main reasons were high cardinality, high missingness, or missing engineered
variables in the notebook input.

## Missingness Findings

Most reviewed variables had zero missingness in the issue 18 summary. The main
exceptions were:

| Variable | Missingness | Decision impact |
| --- | ---: | --- |
| `Order Zipcode` | 86.24% | Keep out of model-ready Gold unless the team approves an availability flag or a narrow descriptive use. |
| `Customer Zipcode` | near zero | Still granular geography; univariate feasibility does not remove privacy, stability, or cardinality concerns. |

Six engineered or review variables were not found in the notebook input:

```text
customer_region_key
item_discount_amount
item_discount_share_of_gross
item_unit_price
product_catalog_key
product_list_price
```

These should not be treated as conceptually invalid. The team should decide
whether they are derived only in later EDA scripts, should be generated in Gold,
or should remain deferred.

## Cardinality Findings

High-cardinality fields remain the main univariate screening concern:

| Variable | Unique values | Implication |
| --- | ---: | --- |
| `order date (DateOrders)` | 65,752 | Use for chronological split and lineage only; use derived calendar features for modeling. |
| `Customer Id` / `Order Customer Id` | 20,652 | Exclude raw IDs from model features unless future time-aware aggregate design is approved. |
| `Latitude` / `latitude_rounded` | 11,250 | Too granular for first Gold model-ready features without approved geographic grouping. |
| `Longitude` / `longitude_rounded` | 4,487 | Too granular for first Gold model-ready features without approved geographic grouping. |
| `Order City` / `order_city_normalized` | 3,597 | High-cardinality categorical geography; requires grouping or exclusion. |
| `Customer Zipcode` | 995 | Granular geography despite low missingness. |
| `Order Zipcode` | 609 | Also high missingness. |
| `Customer City` / `customer_city_normalized` | 563 | High-cardinality categorical geography; requires grouping or exclusion. |
| `Product Name` / `product_name_normalized` | 118 | Product-level descriptor should be grouped or deferred; category/department are safer first. |

Low-cardinality fields with feasible univariate profiles include `Type` with 4
categories, `Order Item Quantity` with 5 values, `Department Id` with 11 values,
and `Order Item Discount Rate` with 18 values. These still need policy review
when they overlap with transaction semantics or AO2 commercial-field design.

## Outlier Findings

The largest IQR outlier counts were concentrated in commercial/order-value and
coordinate fields:

| Variable | Outlier count | Approximate rate | Notes |
| --- | ---: | ---: | --- |
| `Order Item Discount` | 7,537 | 4.18% | Complete numeric field; discount policy still needs AO2 reconstruction review. |
| `Order Item Product Price` | 2,048 | 1.13% | Duplicates or overlaps `Product Price`. |
| `Product Price` | 2,048 | 1.13% | Duplicates or overlaps item product price. |
| `Order Item Total` | 1,943 | 1.08% | Candidate AO3 denominator, but commercial-field duplication must be resolved. |
| `Sales per customer` | 1,943 | 1.08% | May duplicate `Order Item Total`. |
| `Longitude` / `longitude_rounded` | 1,414 | 0.78% | Granular coordinate feature; grouping/privacy review required. |
| `Customer Id` / `Order Customer Id` | 1,198 | 0.66% | Identifier values should not be interpreted as numeric model signal. |
| `Sales`, `item_gross_sales_estimate`, `item_net_sales_amount` | 488 each | 0.27% | Commercial fields require duplicate and reconstruction review. |
| `Department Id` | 362 | 0.20% | Prefer department name for interpretability. |
| `Latitude` / `latitude_rounded` | 9 each | near zero | Still too granular without geographic grouping. |

These outliers do not automatically imply exclusion. They mainly indicate where
later preprocessing, winsorization decisions, robust modeling, or descriptive
caveats may be needed after final feature approval.

## Figure Outputs

The current executable workflow writes PNG figures under `report/figures/eda/`.
The issue 18 branch also included PNG figures under `notebooks/figures/` for
reviewed variables that were present in the notebook input. Figure coverage
includes:

```text
category_id.png
customer_city.png
customer_id.png
customer_zipcode.png
department_id.png
latitude.png
longitude.png
order_city.png
order_customer_id.png
order_date_dateorders.png
order_item_cardprod_id.png
order_item_discount.png
order_item_discount_rate.png
order_item_product_price.png
order_item_quantity.png
order_item_total.png
order_region.png
order_zipcode.png
product_card_id.png
product_category_id.png
product_name.png
product_price.png
product_status.png
sales.png
sales_per_customer.png
type.png
```

No figures were available for variables missing from the issue 18 notebook
input, such as `product_catalog_key`, `product_list_price`, `item_unit_price`,
`item_discount_amount`, `item_discount_share_of_gross`, and
`customer_region_key`.

## Implications For Gold Table Creation

Issue 18 supports moving low-risk, decision-time valid fields toward Gold review
when they also pass leakage policy. It also strengthens the case for excluding
or deferring raw high-cardinality fields.

Recommended interpretation:

- Use issue 18 to confirm missingness, cardinality, outliers, and basic
  feasibility.
- Do not use issue 18 alone to approve predictors for AO1 or AO2 modeling.
- Keep target, outcome, post-shipment, post-delivery, profit-proxy, sensitive,
  identifier, and high-cardinality fields subject to the stricter policy in
  `docs/leakage_control_plan.md` and the issue 19-21 findings.
- Treat commercial fields as data-quality feasible but policy-sensitive for AO2
  because they can duplicate one another or help reconstruct profit.
- Keep raw IDs and raw timestamps as lineage, join, or split fields only unless
  a separate design approves time-aware aggregates or derived calendar features.

## Follow-Up Decisions

Before freezing the first model-ready Gold table, the team should decide:

1. Whether `Type` is approved for modeling or descriptive use only.
2. Whether `Order Item Total` is the single approved order-value field for AO2
   review and AO3 denominator logic.
3. Which price, quantity, discount, and sales fields are allowed without
   creating AO2 target-reconstruction risk.
4. Whether raw city, zip, coordinate, product-name, and product-ID fields are
   excluded from first-pass Gold or transformed into approved grouped features.
5. Whether missing engineered review features should be generated in Gold or
   deferred to later feature-design work.
