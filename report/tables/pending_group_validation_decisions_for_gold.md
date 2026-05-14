# Pending Group Validation Decisions For Gold Table Creation

Draft date: 2026-05-14

Purpose: summarize the remaining team decisions needed to finalize variable
screening and unblock Gold table creation for AO1, AO2, and later AO3.

This is a temporary coordination note, not the final variable policy. The
formal pre-Gold policy handoff is now documented in
`docs/pre_gold_decision_log.md`, with the machine-readable companion at
`data/references/pre_gold_decision_log.csv`. Issue 18
univariate EDA has been reviewed from the remote branch
`origin/18-w3p11-univariate-eda-distributions-and-outliers`, but it is not yet
merged into this branch. Treat the issue 18 findings as distribution and
cardinality evidence that must be reconciled with the stricter leakage and
methodology decisions from issues 19-21.

## Source Artifacts Reviewed

- Issue 18: Univariate EDA distributions and outliers
  - remote branch:
    `origin/18-w3p11-univariate-eda-distributions-and-outliers`
  - `notebooks/eda_univariate_summary.csv`
  - `notebooks/eda_univariate_distribution_analysis.ipynb`
- Issue 19: AO1 bivariate late-delivery EDA
  - `docs/ao1_bivariate_eda.md`
  - `report/tables/ao1_late_delivery_bivariate_summary.csv`
  - `report/tables/ao1_late_delivery_group_validation_list.csv`
- Issue 20: AO2 bivariate profitability EDA
  - `docs/ao2_bivariate_eda.md`
  - `report/tables/ao2_profitability_bivariate_findings.md`
  - `report/tables/ao2_profitability_group_validation_list.csv`
- Issue 21: AO1 class imbalance analysis
  - `docs/ao1_class_imbalance_analysis.md`
  - `report/tables/ao1_class_imbalance_findings.md`
  - `report/tables/ao1_class_imbalance_group_review_list.csv`

## Issue 18 Univariate Findings Evaluated

Issue 18 reviewed 41 variables marked `conditional_review` or
`needs_group_review` in the conceptual screening artifact.

| Finding | Implication for Gold decisions |
| --- | --- |
| 28 reviewed variables were marked `approved_for_gold` by univariate checks, and 13 remained `needs_group_review`. | This is useful quality evidence, but `approved_for_gold` in issue 18 should not override leakage, target-reconstruction, identifier, or high-cardinality policy from issues 19-21. |
| `Type` has 4 categories and no missingness. | Univariate EDA supports feasibility, but business semantics still need group approval because issue 19 found a meaningful AO1 rate spread. |
| `Customer City` has 563 values and `Order City` has 3,597 values. | City fields remain high-cardinality and should not enter the first model-ready Gold table without grouping or encoding rules. |
| `Product Name` and `product_name_normalized` have 118 values. | Product-name fields remain review-needed; prefer category/department until the team approves product-level grouping. |
| `Order Zipcode` has about 86.24% missingness. | Exclude raw order zipcode from model-ready Gold; at most consider an availability flag if separately approved. |
| `Customer Zipcode` has 995 values with near-zero missingness. | Despite issue 18 marking it feasible numerically, it remains granular geography and should stay out of model-ready Gold unless the team approves coarse grouping. |
| `Product Status` and `product_status_flag` have one observed value. | Exclude from model-ready Gold because they provide no useful variation in the current data. |
| Several engineered/review variables were missing from the issue 18 input, including `product_catalog_key`, `product_list_price`, `item_unit_price`, `item_discount_amount`, `item_discount_share_of_gross`, and `customer_region_key`. | Do not assume these are unavailable conceptually; confirm whether they are derived only in later EDA scripts or should be generated in Gold. |
| Commercial fields such as sales, order value, price, discount, and quantity were mostly complete and often low-to-moderate outlier rate. | Data quality is adequate, but AO2 target-reconstruction and duplicate-field decisions remain the gating issue. |

## Decisions To Lock Immediately

| Decision area | Proposed team decision | Reason |
| --- | --- | --- |
| AO1 target | Keep `Late_delivery_risk` as the AO1 target only. | Confirmed binary and non-missing in issue 21. It must never be a predictor or grouping feature. |
| AO2 target | Keep `Order_Profit_Per_Order` as the AO2 target. | Issue 20 confirmed it is present; no fallback target was used. |
| Duplicate profit outcome | Exclude `Benefit_per_order` from predictors. | Issue 20 found it matches `Order_Profit_Per_Order` exactly in the Silver clone. |
| Profit proxy | Exclude `Order_Item_Profit_Ratio` from predictors. | It is a realized profit-ratio/proxy field and creates target reconstruction risk. |
| Delivery outcomes | Exclude `Delivery_Status`, `Days_for_shipping_real`, `shipping_date_DateOrders`, and `Order_Status` from predictors. | They are post-shipment, post-delivery, or outcome/status fields. |
| Raw resampling | Do not include resampling in Gold table creation. | Issue 21 confirms no resampling during EDA; any future SMOTE, undersampling, or class weighting must happen training-fold-only after chronological splitting. |

## Candidate Fields That Can Move Toward Gold Review

These fields appear decision-time valid and were not the main source of pending
review risk after combining issues 18-21. Final inclusion should still be
confirmed against the issue 18 summary before Gold code is frozen.

| Field family | Candidate fields | Proposed Gold treatment |
| --- | --- | --- |
| Planned shipping service | `Shipping_Mode`, `Days_for_shipment_scheduled`, `scheduled_shipping_days`, `shipping_speed_tier`, `is_same_day_or_next_day_shipping`, `is_standard_shipping` | Include as AO1/AO2 candidate features after confirming univariate quality. Issue 21 found shipping service slices have the strongest AO1 class-rate differences. |
| Order calendar derivatives | `order_year`, `order_quarter`, `order_month`, `order_week_of_year`, `order_day_of_month`, `order_day_of_week`, `order_hour`, `order_is_weekend`, `order_season` | Include derived fields only. Do not use raw `order_date_DateOrders` directly as a model input. |
| Coarse market and destination geography | `Market`, `Order_Region`, `Order_Country`, `Order_State`, normalized market/order region/order country/order state fields | Include as coarse geography candidates. Keep city, zip, coordinate, and composite region keys pending review. |
| Customer profile and coarse origin geography | `Customer_Segment`, `Customer_Country`, `Customer_State`, normalized customer segment/country/state fields | Include as candidates after confirming issue 18 or later univariate checks show acceptable missingness/cardinality. |
| Product mix | `Category_Name`, `Department_Name`, `product_category_key`, `product_department_key` | Include as candidates, but keep product names and product IDs separate. Issue 20 found product/department mix had strong descriptive profitability differences. |

## Group Decisions Needed Before Gold Is Finalized

| Topic | Variables affected | Evidence from issues 19-21 | Decision needed |
| --- | --- | --- | --- |
| Transaction type semantics | `Type` | Issue 18 found 4 categories and no missingness. Issue 19 found AO1 rates from `PAYMENT` 57.53% to `TRANSFER` 48.54%. Issue 20 found small AO2 profit differences by type. | Decide whether `Type` is a valid order-creation operational field for modeling, descriptive-only context, or excluded. Issue 18 supports feasibility but does not resolve semantics. |
| Single order-value field for AO2/AO3 | `Order_Item_Total`, `Sales_per_customer`, `Sales`, `item_net_sales_amount`, `item_gross_sales_estimate` | Issue 18 found these fields mostly complete with usable numeric distributions. Issue 20 found profit increases across order-value bins, but these fields may duplicate one another and contribute to target reconstruction. | Choose one primary order-value field if needed. Proposed default: use `Order_Item_Total` as the AO3 denominator and exclude `Sales_per_customer` as duplicate unless metadata review says otherwise. |
| Price-field duplication | `Product_Price`, `Order_Item_Product_Price`, `product_list_price`, `item_unit_price` | Issue 18 found raw price fields complete with 75 values and about 1.13% IQR outliers. Issue 20 found price bins align with profit, but product price fields likely duplicate each other. | Choose at most one price representation for AO2 Gold, or exclude price from the main model if reconstruction risk is judged too high. Confirm whether derived price fields missing in issue 18 are generated later or should be created in Gold. |
| Discount field policy | `Order_Item_Discount`, `Order_Item_Discount_Rate`, `item_discount_amount`, `item_discount_rate`, `item_discount_share_of_gross` | Issue 18 found discount amount complete with 1,017 values and 4.18% IQR outliers; discount rate has 18 values and no IQR outliers. Issue 20 found descriptive profit patterns. | Decide whether discount amount/rate are pre-dispatch and acceptable for AO2, and which duplicate engineered/raw versions to keep. Confirm whether missing engineered discount fields should be generated in Gold. |
| Quantity field policy | `Order_Item_Quantity`, `order_item_quantity` | Issue 18 found quantity complete with 5 values and no IQR outliers. Quantity is decision-time valid but part of the AO2 commercial feature family. | Decide whether quantity is acceptable for AO2 without enabling formula reconstruction when paired with price/order-value fields. |
| Product identifiers and names | `Product_Card_Id`, `Product_Category_Id`, `Order_Item_Cardprod_Id`, `Product_Name`, `product_catalog_key`, `product_name_normalized` | Issue 18 found product identifiers complete but numeric/key-like; product names have 118 values and remain high-cardinality review. Issues 19-21 treat these as high-cardinality or duplicate product descriptors. | Exclude direct product IDs and product names from the first model-ready Gold table unless the team approves grouped/frequency-thresholded product features. Prefer category/department first. |
| Category and department IDs | `Category_Id`, `Department_Id` | Issue 18 found `Category_Id` has 51 values and `Department_Id` has 11 values. Names are clearer candidates; IDs may duplicate names or act as keys. | Prefer `Category_Name` and `Department_Name`; decide whether IDs are retained only for traceability or excluded from model-ready Gold. |
| Customer and order identifiers | `Customer_Id`, `Order_Customer_Id`, `Order_Id`, `Order_Item_Id` | Issue 18 marked `Customer_Id` and `Order_Customer_Id` feasible numerically, but both have 20,652 distinct values. Direct ID use is not meaningful and can overfit. | Exclude raw IDs from model features. Use only as join/traceability keys unless a future time-aware historical aggregate design is explicitly approved. |
| Granular geography | `Customer_City`, `Order_City`, `Customer_Zipcode`, `Order_Zipcode`, `Latitude`, `Longitude`, normalized city fields, rounded coordinates, region keys | Issue 18 found `Customer_City` has 563 values, `Order_City` has 3,597 values, `Customer_Zipcode` has 995 values, and `Order_Zipcode` has about 86.24% missingness. Issues 19-21 also flag high cardinality, privacy/stability, and grouping risk. | Keep only coarse geography in the first model-ready Gold table. Exclude raw city, zip, coordinates, and composite region keys unless a grouped or availability-flag design is explicitly approved. |
| Product status | `Product_Status`, `product_status_flag` | Issue 18 and issue 21 found one observed value. Semantics still unclear and the field has no useful variation. | Exclude from model-ready Gold unless later metadata review shows meaningful variation in another extract. |
| Raw order timestamp | `order_date_DateOrders`, source `order date (DateOrders)` | Issue 18 found 65,752 distinct timestamp values. The timestamp is needed for chronological split and derived calendar features. | Use raw timestamp for split/lineage only. Use approved calendar derivatives for modeling review. |

## Proposed Gold Table Policy

To keep Gold creation moving without silently approving risky variables:

1. Create the model-ready Gold feature set with approved candidate fields only.
2. Keep forbidden target, outcome, post-shipment, post-delivery, profit-proxy,
   and sensitive identifier fields out of predictor columns.
3. Store raw IDs and raw order timestamp only as lineage/split/join fields when
   needed, not as model features.
4. Put conditional fields into a separate review list or excluded-field log
   rather than the default model feature set.
5. Use issue 18 distribution/cardinality findings as quality evidence, but do
   not let them override leakage, target-reconstruction, or high-cardinality
   policy from issues 19-21.

## Minimum Team Decisions Needed To Proceed

1. Confirm target and forbidden-field locks for AO1 and AO2.
2. Decide whether `Type` is approved, descriptive-only, or excluded.
3. Choose the AO2/AO3 order-value policy, especially `Order_Item_Total` versus
   `Sales_per_customer` and other sales/value fields.
4. Choose one price/discount/quantity treatment that avoids duplicate economic
   fields and profit target reconstruction.
5. Confirm that raw IDs, city/zip/coordinate fields, product names, and product
   catalog keys are excluded from the first Gold model-ready table unless a
   grouped or train-only aggregate design is separately approved.
6. Confirm raw order timestamp is split/lineage only, with derived calendar
   fields used for modeling review.
7. Reconcile issue 18 `approved_for_gold` labels with the stricter policy
   categories above before freezing final Gold inclusion rules.

## Suggested Meeting Output

After review, the team should mark each pending family as one of:

- `approved_for_gold_candidate`
- `descriptive_only`
- `lineage_or_split_only`
- `exclude_from_model_features`
- `defer_to_future_feature_design`

Those labels can then be reflected in the final variable screening policy and
used to build the first leakage-safe Gold table.
