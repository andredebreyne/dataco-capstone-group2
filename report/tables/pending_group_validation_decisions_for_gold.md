# Pending Group Validation Decisions For Gold Table Creation

Draft date: 2026-05-12

Purpose: summarize the remaining team decisions needed to finalize variable
screening and unblock Gold table creation for AO1, AO2, and later AO3.

This is a temporary coordination note, not the final variable policy. Issue 18
for univariate EDA is still in progress, so these recommendations should be
treated as provisional until univariate missingness, distribution, and
cardinality checks are reviewed.

## Source Artifacts Reviewed

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
review risk in issues 19-21. Final inclusion should still wait for issue 18
univariate checks.

| Field family | Candidate fields | Proposed Gold treatment |
| --- | --- | --- |
| Planned shipping service | `Shipping_Mode`, `Days_for_shipment_scheduled`, `scheduled_shipping_days`, `shipping_speed_tier`, `is_same_day_or_next_day_shipping`, `is_standard_shipping` | Include as AO1/AO2 candidate features after confirming univariate quality. Issue 21 found shipping service slices have the strongest AO1 class-rate differences. |
| Order calendar derivatives | `order_year`, `order_quarter`, `order_month`, `order_week_of_year`, `order_day_of_month`, `order_day_of_week`, `order_hour`, `order_is_weekend`, `order_season` | Include derived fields only. Do not use raw `order_date_DateOrders` directly as a model input. |
| Coarse market and destination geography | `Market`, `Order_Region`, `Order_Country`, `Order_State`, normalized market/order region/order country/order state fields | Include as coarse geography candidates. Keep city, zip, coordinate, and composite region keys pending review. |
| Customer profile and coarse origin geography | `Customer_Segment`, `Customer_Country`, `Customer_State`, normalized customer segment/country/state fields | Include as candidates if issue 18 confirms acceptable missingness/cardinality. |
| Product mix | `Category_Name`, `Department_Name`, `product_category_key`, `product_department_key` | Include as candidates after univariate cardinality review. Issue 20 found product/department mix had strong descriptive profitability differences. |

## Group Decisions Needed Before Gold Is Finalized

| Topic | Variables affected | Evidence from issues 19-21 | Decision needed |
| --- | --- | --- | --- |
| Transaction type semantics | `Type` | Issue 19 found AO1 rates from `PAYMENT` 57.53% to `TRANSFER` 48.54%. Issue 20 found small AO2 profit differences by type. It is still `needs_group_review`. | Decide whether `Type` is a valid order-creation operational field for modeling, descriptive-only context, or excluded. |
| Single order-value field for AO2/AO3 | `Order_Item_Total`, `Sales_per_customer`, `Sales`, `item_net_sales_amount`, `item_gross_sales_estimate` | Issue 20 found profit increases across order-value bins, but these fields may duplicate one another and contribute to target reconstruction. | Choose one primary order-value field if needed. Proposed default: use `Order_Item_Total` as the AO3 denominator and exclude `Sales_per_customer` as duplicate unless metadata review says otherwise. |
| Price-field duplication | `Product_Price`, `Order_Item_Product_Price`, `product_list_price`, `item_unit_price` | Issue 20 found price bins align with profit, but product price fields likely duplicate each other. | Choose at most one price representation for AO2 Gold, or exclude price from the main model if reconstruction risk is judged too high. |
| Discount field policy | `Order_Item_Discount`, `Order_Item_Discount_Rate`, `item_discount_amount`, `item_discount_rate`, `item_discount_share_of_gross` | Issue 20 found discount fields show descriptive profit patterns; issue 19 shows weak AO1 patterns. They remain commercial review fields. | Decide whether discount amount/rate are pre-dispatch and acceptable for AO2, and which duplicate engineered/raw versions to keep. |
| Quantity field policy | `Order_Item_Quantity`, `order_item_quantity` | Quantity is decision-time valid but part of the AO2 commercial feature family. | Decide whether quantity is acceptable for AO2 without enabling formula reconstruction when paired with price/order-value fields. |
| Product identifiers and names | `Product_Card_Id`, `Product_Category_Id`, `Order_Item_Cardprod_Id`, `Product_Name`, `product_catalog_key`, `product_name_normalized` | Issues 19-21 treat these as high-cardinality or duplicate product descriptors. | Decide whether to exclude direct use and rely on category/department only, or approve grouped/frequency-thresholded product features. |
| Category and department IDs | `Category_Id`, `Department_Id` | Names are clearer candidates; IDs may duplicate names or act as keys. | Prefer `Category_Name` and `Department_Name`; decide whether IDs are retained only for traceability or excluded from model-ready Gold. |
| Customer and order identifiers | `Customer_Id`, `Order_Customer_Id`, `Order_Id`, `Order_Item_Id` | Direct ID use is not meaningful and can overfit. | Exclude raw IDs from model features. Use only as join/traceability keys unless a future time-aware historical aggregate design is explicitly approved. |
| Granular geography | `Customer_City`, `Order_City`, `Customer_Zipcode`, `Order_Zipcode`, `Latitude`, `Longitude`, normalized city fields, rounded coordinates, region keys | Issues 19-21 flag high cardinality, privacy/stability, and grouping risk. | Decide whether Gold should include only coarse geography now, with city/zip/coordinates excluded or parked for a future grouped feature design. |
| Product status | `Product_Status`, `product_status_flag` | Issue 21 found one distinct observed value in the current Silver clone; semantics still unclear. | Exclude unless issue 18 or metadata review shows useful variation and confirms business meaning. |
| Raw order timestamp | `order_date_DateOrders`, source `order date (DateOrders)` | Needed for chronological split and derived calendar features; raw timestamp is high-cardinality. | Use raw timestamp for split/lineage only. Use approved calendar derivatives for modeling review. |

## Proposed Gold Table Policy

To keep Gold creation moving without silently approving risky variables:

1. Create the model-ready Gold feature set with approved candidate fields only.
2. Keep forbidden target, outcome, post-shipment, post-delivery, profit-proxy,
   and sensitive identifier fields out of predictor columns.
3. Store raw IDs and raw order timestamp only as lineage/split/join fields when
   needed, not as model features.
4. Put conditional fields into a separate review list or excluded-field log
   rather than the default model feature set.
5. Revisit commercial, granular geography, and high-cardinality product/customer
   fields after issue 18 univariate EDA is complete.

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
7. Review issue 18 univariate EDA before freezing final Gold inclusion rules.

## Suggested Meeting Output

After review, the team should mark each pending family as one of:

- `approved_for_gold_candidate`
- `descriptive_only`
- `lineage_or_split_only`
- `exclude_from_model_features`
- `defer_to_future_feature_design`

Those labels can then be reflected in the final variable screening policy and
used to build the first leakage-safe Gold table.
