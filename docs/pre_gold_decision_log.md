# Pre-Gold Methodological Decision Inventory

Draft date: 2026-05-14

## Purpose

This log resolves the methodological decisions needed before Gold analytical
table creation for AO1 late-delivery risk, AO2 order profitability, and AO3
risk-margin prioritization.

Finalized team decisions for first-pass model-ready Gold are documented in
`docs/pre_gold_modeling_decisions.md`. This file remains a preliminary decision
inventory and source review log; any unresolved or conditional statuses below
reflect the pre-finalization review stage and are superseded by the finalized
modeling decisions.

It does not implement Gold tables, train models, select thresholds, apply
resampling, create new engineered features, or approve final model feature
lists. The goal is to give the next Gold-table task a conservative policy
handoff so it does not need to guess which fields are targets, leakage risks,
dashboard-only fields, lineage fields, or conditional candidates.

## Sources Reviewed

- `docs/leakage_control_plan.md`
- `data/references/feature_availability_map.csv`
- `docs/feature_availability_map.md`
- `data/references/leakage_conceptual_screening.csv`
- `docs/leakage_conceptual_screening.md`
- `docs/ao1_target_definition.md`
- `docs/ao2_target_policy.md`
- `docs/silver_schema_data_dictionary.md`
- `data/references/silver_schema_data_dictionary.csv`
- `docs/order_time_features.md`
- `docs/shipping_product_features.md`
- `docs/customer_regional_features.md`
- `docs/ao1_bivariate_eda.md`
- `docs/ao2_bivariate_eda.md`
- `docs/ao1_class_imbalance_analysis.md`
- `report/tables/univariate_distribution_eda_findings.md`
- `report/tables/ao1_late_delivery_bivariate_findings.md`
- `report/tables/ao2_profitability_bivariate_findings.md`
- `report/tables/ao1_class_imbalance_findings.md`
- `report/tables/eda_univariate_summary.csv`
- `report/tables/ao1_late_delivery_bivariate_summary.csv`
- `report/tables/ao1_late_delivery_group_validation_list.csv`
- `report/tables/ao2_profitability_bivariate_summary.csv`
- `report/tables/ao2_profitability_group_validation_list.csv`
- `report/tables/ao1_class_imbalance_group_review_list.csv`

No external sources were used.

## Decision Categories

| Category | Meaning for Gold creation |
| --- | --- |
| `approved_for_gold_candidate` | Decision-time valid and low methodological risk. May be included as a candidate predictor or support column, subject to normal train-only preprocessing later. |
| `conditional_for_gold_with_policy` | May be included only under the stated policy, usually to avoid duplicate economic fields or target reconstruction. |
| `exclude_from_model_features` | Must not be used as an AO1 or AO2 predictor. |
| `dashboard_only` | May be retained for audit, descriptive reporting, governance, or dashboard context, but not predictive features. |
| `lineage_or_split_only` | May be retained for joins, row traceability, deduplication, chronological split, or audit, but not predictive features. |
| `defer_to_future_feature_design` | Do not include in the first model-ready Gold predictor set. Requires a later grouping, encoding, or time-aware aggregate design. |
| `needs_group_validation` | Do not include in default Gold predictor columns until the team answers the listed question. |

## Preliminary Decision Inventory

The status values in this table are historical review statuses from the
pre-finalization decision inventory. Use `docs/pre_gold_modeling_decisions.md`
for current first-pass Gold inclusion and exclusion rules.

| Decision area | Variable or feature group | Related AO | Decision | Rationale | Main source artifacts | Leakage risk | Target-reconstruction risk | Action required before Gold | Group validation needed | Final status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AO1 target | `Late_delivery_risk` | AO1 | `exclude_from_model_features` | Official binary AO1 target. It is target-only and must never be used as a predictor or grouping signal for model features. | `docs/ao1_target_definition.md`; `data/references/feature_availability_map.csv`; `data/references/leakage_conceptual_screening.csv`; `report/tables/ao1_class_imbalance_findings.md` | High if used as predictor | Low | Keep as AO1 target column only. Exclude from all predictor matrices. | No | Resolved |
| AO1 primary population | `Delivery_Status = Shipping canceled`; `Order_Status` values `CANCELED` and `SUSPECTED_FRAUD` | AO1 | `needs_group_validation` | The target note recommends excluding canceled/fraud shipments from the primary AO1 table because they are not normal completed deliveries, but this affects the modeling population and should be signed off before AO1 Gold is frozen. | `docs/ao1_target_definition.md`; `docs/pre_gold_modeling_decisions.md` | Medium if canceled records are treated as normal non-late deliveries | Low | Default proposal: primary AO1 Gold excludes `Delivery_Status = Shipping canceled`; optionally retain a sensitivity/audit flag outside predictors. | Yes | Unresolved group validation |
| Delivery outcome leakage fields | `Delivery_Status`; `Days_for_shipping_real`; `shipping_date_DateOrders`; `Order_Status` | AO1, AO2, dashboard | `dashboard_only` | These fields are post-shipment, post-delivery, or post-order status fields and may directly encode delivery or fulfillment outcomes. | `docs/leakage_control_plan.md`; `docs/ao1_target_definition.md`; `docs/feature_availability_map.md`; `report/tables/ao1_late_delivery_bivariate_findings.md`; `report/tables/ao2_profitability_bivariate_findings.md` | High | Low | Keep out of AO1 and AO2 predictors. Retain only in audit/dashboard outputs or AO1 population sensitivity logic. | No | Resolved |
| AO2 target | `Order_Profit_Per_Order` | AO2 | `exclude_from_model_features` | Official AO2 target and target-only field. | `docs/ao2_target_policy.md`; `data/references/feature_availability_map.csv`; `report/tables/ao2_profitability_bivariate_findings.md` | Low | High if used as predictor | Keep as AO2 target column only. Exclude from AO1 and AO2 predictor matrices. | No | Resolved |
| AO2 profit duplicates and realized margin proxies | `Benefit_per_order`; `Order_Item_Profit_Ratio`; direct profit transformations; realized margin fields | AO2, dashboard | `dashboard_only` | `Benefit_per_order` exactly matches `Order_Profit_Per_Order` in the reviewed Silver clone. `Order_Item_Profit_Ratio` is a realized profit-ratio/proxy that can reconstruct profit with order value. | `docs/ao2_target_policy.md`; `docs/leakage_control_plan.md`; `report/tables/ao2_profitability_bivariate_findings.md` | Medium | High | Exclude from model predictors. Use only for target audit, descriptive historical margin, governance, or dashboard caveats. | No | Resolved |
| AO3 order-value denominator | `Order_Item_Total`; engineered duplicate `item_net_sales_amount`; duplicate `Sales_per_customer` | AO2, AO3 | `conditional_for_gold_with_policy` | `Order_Item_Total` is the selected AO3 predicted-margin denominator. `Sales_per_customer` is documented as an exact duplicate or near-duplicate of `Order_Item_Total`; `item_net_sales_amount` is the engineered copy. | `docs/ao2_target_policy.md`; `report/tables/ao2_profitability_bivariate_findings.md`; `report/tables/univariate_distribution_eda_findings.md` | Low | Medium | Retain one denominator for AO3 support: prefer `Order_Item_Total`. Do not include `Sales_per_customer` or `item_net_sales_amount` redundantly in the same AO2 predictor matrix. | No for denominator; yes before AO2 predictor use | Resolved for AO3 denominator; conditional for AO2 predictors |
| Gross sales fields | `Sales`; `item_gross_sales_estimate` | AO2, AO3 | `needs_group_validation` | Gross sales is order-time commercial information but duplicates or overlaps price times quantity and may combine with other fields to reconstruct economic value structure. | `docs/ao2_target_policy.md`; `report/tables/ao2_profitability_bivariate_findings.md`; `report/tables/eda_univariate_summary.csv` | Low | Medium | Keep out of the default AO2 predictor set until the team decides whether gross value is needed in addition to the selected denominator. | Yes | Unresolved group validation |
| Price fields | `Order_Item_Product_Price`; `item_unit_price`; `Product_Price`; `product_list_price` | AO2 | `conditional_for_gold_with_policy` | Price is decision-time valid but duplicate representations exist. Including multiple price fields creates redundant economic inputs and can strengthen formula reconstruction when paired with quantity, discount, and order value. | `docs/ao2_target_policy.md`; `docs/shipping_product_features.md`; `report/tables/ao2_profitability_bivariate_findings.md`; `report/tables/univariate_distribution_eda_findings.md` | Low | Medium | If price is approved, choose one item-level representation only, preferably `Order_Item_Product_Price` or its engineered copy `item_unit_price`, not both. Exclude `Product_Price` and `product_list_price` as duplicates unless metadata review justifies otherwise. | Yes before predictor inclusion | Conditional |
| Discount fields | `Order_Item_Discount`; `item_discount_amount`; `Order_Item_Discount_Rate`; `item_discount_rate`; `item_discount_share_of_gross` | AO2 | `conditional_for_gold_with_policy` | Discounts are likely order-time fields but remain commercial-policy fields. Amount, rate, and share fields duplicate related concepts and can interact with value fields. | `docs/ao2_target_policy.md`; `docs/shipping_product_features.md`; `report/tables/ao2_profitability_bivariate_findings.md`; `report/tables/eda_univariate_summary.csv` | Low | Medium | If discount is approved, prefer one rate representation (`Order_Item_Discount_Rate` or `item_discount_rate`). Use amount only if explicitly justified. Defer `item_discount_share_of_gross` unless the team approves derived commercial ratios. | Yes before predictor inclusion | Conditional |
| Quantity fields | `Order_Item_Quantity`; `order_item_quantity` | AO1, AO2 | `conditional_for_gold_with_policy` | Quantity is decision-time valid and low-cardinality, but AO2 use should be reviewed with the commercial-field set because price, quantity, discount, and value fields are mechanically related. | `data/references/feature_availability_map.csv`; `docs/ao2_target_policy.md`; `report/tables/ao2_profitability_group_validation_list.csv`; `report/tables/eda_univariate_summary.csv` | Low | Medium when paired with price/value/discount fields | Use only one representation. It may be kept as an order-composition candidate, but AO2 predictor use must be documented with the selected commercial field policy. | Yes before AO2 predictor inclusion | Conditional |
| Transaction type | `Type` | AO1, AO2 | `needs_group_validation` | Low cardinality and no missingness, but business semantics are not fully validated. AO1 EDA found a meaningful late-rate spread by type. | `data/references/feature_availability_map.csv`; `report/tables/ao1_late_delivery_bivariate_findings.md`; `report/tables/ao2_profitability_bivariate_findings.md`; `report/tables/eda_univariate_summary.csv` | Low to medium depending on semantics | Low | Do not include by default. Team must confirm whether `Type` is known at order creation and operationally valid, or should be descriptive-only. | Yes | Unresolved group validation |
| Planned shipping/service fields | `Days_for_shipment_scheduled`; `Shipping_Mode`; `scheduled_shipping_days`; `shipping_speed_tier`; `shipping_mode_normalized`; `is_same_day_or_next_day_shipping`; `is_standard_shipping` | AO1, AO2 | `approved_for_gold_candidate` | Planned service information is expected before dispatch and has strong AO1 descriptive signal. It is not post-shipment leakage when sourced from scheduled days and selected shipping mode. | `docs/leakage_control_plan.md`; `docs/shipping_product_features.md`; `report/tables/ao1_late_delivery_bivariate_findings.md`; `report/tables/ao1_class_imbalance_findings.md` | Low | Low | Include as Gold candidate features. Avoid keeping raw and engineered duplicates in the same final model matrix unless the modeling design intentionally compares representations. | No | Resolved |
| Raw order timestamp | `order_date_DateOrders`; source `order date (DateOrders)` | AO1, AO2, general Gold | `lineage_or_split_only` | The raw timestamp is needed for chronological split and lineage, but has high cardinality and should not be used as an unconstrained model feature. | `docs/leakage_control_plan.md`; `docs/order_time_features.md`; `report/tables/univariate_distribution_eda_findings.md`; `report/tables/ao1_late_delivery_bivariate_findings.md` | Medium if used raw | Low | Retain for chronological split, lineage, and validation. Use derived calendar fields for modeling candidates. | No | Resolved |
| Derived order-time calendar features | `order_year`; `order_quarter`; `order_month`; `order_week_of_year`; `order_day_of_month`; `order_day_of_week`; `order_hour`; `order_is_weekend`; `order_season` | AO1, AO2 | `approved_for_gold_candidate` | Deterministic features derived only from order creation timestamp. No shipment, delivery, or outcome fields are used. | `docs/order_time_features.md`; `data/references/leakage_conceptual_screening.csv`; `report/tables/ao1_late_delivery_bivariate_findings.md`; `report/tables/ao2_profitability_bivariate_findings.md` | Low | Low | Include as Gold candidate features. Any later scaling/encoding remains training-only. | No | Resolved |
| Product category and department descriptors | `Category_Name`; `Department_Name`; `product_category_key`; `product_department_key` | AO1, AO2 | `approved_for_gold_candidate` | Category and department names/keys are order-time product mix descriptors with clear business meaning and support-safe EDA patterns. | `docs/feature_availability_map.md`; `docs/shipping_product_features.md`; `report/tables/ao2_profitability_bivariate_findings.md` | Low | Low | Include as candidate product mix features. Prefer names or stable engineered keys over raw numeric IDs. | No | Resolved |
| Category and department raw IDs | `Category_Id`; `Product_Category_Id`; `Department_Id` | AO1, AO2 | `lineage_or_split_only` | Numeric codes duplicate clearer category/department descriptors and may be treated incorrectly as numeric signal. | `data/references/feature_availability_map.csv`; `report/tables/eda_univariate_summary.csv`; `docs/pre_gold_modeling_decisions.md` | Low | Low | Do not use as direct predictors in first Gold model matrices. Keep only if needed to build stable category/department keys or for traceability. | No | Resolved |
| Product IDs, product names, and catalog keys | `Product_Card_Id`; `Order_Item_Cardprod_Id`; `Product_Name`; `product_catalog_key`; `product_name_normalized` | AO1, AO2 | `defer_to_future_feature_design` | Product-level identifiers and names are high-cardinality or key-like. Direct use risks overfitting and unstable catalog shortcuts. | `docs/shipping_product_features.md`; `report/tables/univariate_distribution_eda_findings.md`; `report/tables/ao1_late_delivery_bivariate_findings.md`; `report/tables/ao2_profitability_bivariate_findings.md` | Medium | Low to medium | Exclude from first model-ready predictor set. Revisit only with grouped product features, frequency thresholds, or time-aware aggregate design. | Yes for future design | Deferred |
| Product status | `Product_Status`; `product_status_flag` | AO1, AO2 | `exclude_from_model_features` | Current EDA found one observed value, so it provides no useful variation. Semantics also remain unclear. | `report/tables/univariate_distribution_eda_findings.md`; `report/tables/ao1_class_imbalance_group_review_list.csv`; `docs/shipping_product_features.md` | Low | Low | Exclude from first Gold model predictors. Retain only as descriptive metadata if needed. | No | Resolved |
| Coarse customer and destination geography | `Customer_Segment`; `Customer_Country`; `Customer_State`; `Market`; `Order_Country`; `Order_Region`; `Order_State`; normalized equivalents | AO1, AO2 | `approved_for_gold_candidate` | Coarse geography and segment fields are known at order creation and are supported by the availability map. | `docs/feature_availability_map.md`; `docs/customer_regional_features.md`; `report/tables/ao1_late_delivery_bivariate_findings.md`; `report/tables/ao2_profitability_bivariate_findings.md` | Low | Low | Include as candidate features, with later encoding fit on training data only. Review cardinality during Gold construction, especially for country/state fields. | No | Resolved |
| Geography availability and match flags | `customer_zipcode_available`; `order_zipcode_available`; `geo_coordinates_available`; `customer_order_country_match`; `customer_order_state_match` | AO1, AO2 | `approved_for_gold_candidate` | These are deterministic order-time flags that avoid exposing raw postal codes or precise coordinates. | `docs/customer_regional_features.md`; `data/references/leakage_conceptual_screening.csv`; `report/tables/ao1_late_delivery_bivariate_summary.csv`; `report/tables/ao2_profitability_bivariate_summary.csv` | Low | Low | Include as candidate features if generated by the existing customer/regional feature job. | No | Resolved |
| Granular geography | `Customer_City`; `Order_City`; `Customer_Zipcode`; `Order_Zipcode`; `Latitude`; `Longitude`; `customer_city_normalized`; `order_city_normalized`; `customer_region_key`; `order_region_key`; `latitude_rounded`; `longitude_rounded` | AO1, AO2 | `defer_to_future_feature_design` | These fields are granular, high-cardinality, privacy/stability-sensitive, or heavily missing (`Order_Zipcode`). Rounded coordinates still showed high cardinality. | `docs/customer_regional_features.md`; `report/tables/univariate_distribution_eda_findings.md`; `report/tables/ao1_late_delivery_group_validation_list.csv`; `report/tables/ao2_profitability_group_validation_list.csv` | Medium | Low | Exclude direct use from first model-ready Gold predictors. Revisit only with approved grouping, coarse bins, or training-only aggregate design. | Yes for future design | Deferred |
| Customer identifiers and historical aggregates | `Customer_Id`; `Order_Customer_Id`; any customer-history aggregate | AO1, AO2 | `defer_to_future_feature_design` | Raw customer IDs have 20,652 distinct values and should not be direct predictors. Historical aggregates would require time-aware train-only logic, which is out of scope for pre-Gold documentation. | `docs/leakage_control_plan.md`; `docs/feature_availability_map.md`; `report/tables/univariate_distribution_eda_findings.md` | Medium | Low | Keep raw customer IDs out of predictor matrices. Use only for joins if needed. Do not build customer historical aggregates in first Gold scope. | Yes for future design | Deferred |
| Order and item identifiers | `Order_Id`; `Order_Item_Id` | General Gold | `lineage_or_split_only` | Row/order identifiers are not predictive business signals. | `docs/leakage_control_plan.md`; `data/references/feature_availability_map.csv`; `docs/silver_schema_data_dictionary.md` | Low | Low | Retain only for joins, deduplication, traceability, and validation. | No | Resolved |
| Technical lineage metadata | `_ingest_timestamp`; `_source_file`; `_silver_processed_timestamp`; feature processed timestamp columns | General Gold, dashboard | `lineage_or_split_only` | Technical metadata supports reproducibility and troubleshooting, not predictive modeling. | `docs/silver_schema_data_dictionary.md`; `docs/order_time_features.md`; `docs/shipping_product_features.md`; `docs/customer_regional_features.md` | Low | Low | Retain only in audit or lineage views. Exclude from AO1 and AO2 predictors. | No | Resolved |
| Sensitive personal identifiers | `Customer_Email`; `Customer_Fname`; `Customer_Lname`; `Customer_Password`; `Customer_Street` | General Gold, dashboard | `exclude_from_model_features` | Personal or sensitive identifiers are not operational modeling signals and should not appear in ordinary dashboard outputs. | `docs/leakage_control_plan.md`; `docs/feature_availability_map.md`; `docs/silver_schema_data_dictionary.md` | Medium | Low | Exclude from predictive Gold and ordinary dashboards. Retain only in Bronze/Silver raw traceability if already present. | No | Resolved |
| Product asset/text fields | `Product_Image`; `Product_Description` | Dashboard | `dashboard_only` | Product image is a catalog/display asset. Product description is empty in the reviewed dataset and not useful for structured modeling. | `docs/feature_availability_map.md`; `docs/silver_schema_data_dictionary.md` | Low | Low | Exclude from model predictors. Use only for dashboard/catalog display or metadata audit if needed. | No | Resolved |
| Engineered features missing from issue 18 input | `product_catalog_key`; `product_list_price`; `item_unit_price`; `item_discount_amount`; `item_discount_share_of_gross`; `customer_region_key` | General Gold | `conditional_for_gold_with_policy` | These were missing from some univariate inputs because they are generated by later feature scripts, not because they are conceptually invalid. Their policy follows their feature family: commercial, product high-cardinality, or geography key. | `report/tables/univariate_distribution_eda_findings.md`; `docs/shipping_product_features.md`; `docs/customer_regional_features.md`; `data/references/leakage_conceptual_screening.csv` | Varies by family | Varies by family | Do not create new features in this task. Gold may consume existing feature-engineering outputs, but each missing-from-EDA feature keeps its family-specific conditional/deferred policy. | Depends on feature family | Resolved as policy mapping |
| Chronological split | `order_date_DateOrders` sorted split | General Gold, AO1, AO2, AO3 | `lineage_or_split_only` | Official split policy is earliest 80% development and most recent 20% held-out test by order date. Random final train/test split is not approved for official results. | `docs/leakage_control_plan.md`; `docs/silver_schema_data_dictionary.md` | Medium if ignored | Low | Gold tables must retain `order_date_DateOrders` for split assignment or reproducibility. Do not fit preprocessing or select thresholds on held-out test data. | No | Resolved |
| Dashboard-only and predictor separation | Targets, outcomes, actual shipping fields, profit audit fields, images/assets, status fields | Dashboard, general Gold | `dashboard_only` | Dashboard/governance fields can support interpretation but must not bleed into model matrices. | `docs/leakage_control_plan.md`; `docs/feature_availability_map.md`; `docs/leakage_conceptual_screening.md` | High if mixed into predictors | High for profit fields | Build separate dashboard/audit outputs or clearly marked non-predictor columns. Predictor lists must be explicit. | No | Resolved |
| AO1 resampling and class weighting | SMOTE; undersampling; oversampling; class weights | AO1 | `defer_to_future_feature_design` | AO1 imbalance is mild in the full Silver clone, and resampling decisions depend on chronological train/validation distributions and model choice. | `docs/ao1_class_imbalance_analysis.md`; `report/tables/ao1_class_imbalance_findings.md`; `docs/leakage_control_plan.md` | High if applied before split | Low | Do not apply in Gold. Defer to modeling, training fold only, after chronological split. | No | Deferred to modeling |
| AO1 operating threshold | Classification threshold; recall/precision tradeoff | AO1, AO3 | `defer_to_future_feature_design` | Thresholds must be selected using validation data after model training. Gold creation should not optimize thresholds. | `docs/leakage_control_plan.md`; `report/tables/ao1_class_imbalance_findings.md` | Medium if tuned on test data | Low | Do not set thresholds in Gold. Document that threshold selection is a modeling issue. | No | Deferred to modeling |
| AO3 risk-margin grouping and evaluation | Risk cutoff; margin cutoff; 2x2 priority groups; risk-only/profit-only comparison | AO3 | `defer_to_future_feature_design` | AO3 groups must use AO1 and AO2 predictions, not actual targets, and thresholds must be chosen from training/validation data. | `docs/leakage_control_plan.md`; `docs/ao2_target_policy.md` | High if actual outcomes define test groups | Medium if actual profit is used instead of prediction | Gold may prepare support columns such as identifiers, split date, predicted-margin denominator, and later prediction joins. Do not assign AO3 groups before modeling. | No | Deferred to modeling |

## Approved Candidate Groups For First Gold Review

The following groups are approved as candidate features or support columns for
Gold construction, subject to explicit predictor lists and train-only
preprocessing later:

- Planned shipping/service: `Days_for_shipment_scheduled`, `Shipping_Mode`,
  `scheduled_shipping_days`, `shipping_speed_tier`,
  `shipping_mode_normalized`, `is_same_day_or_next_day_shipping`,
  `is_standard_shipping`.
- Derived order-time calendar: `order_year`, `order_quarter`, `order_month`,
  `order_week_of_year`, `order_day_of_month`, `order_day_of_week`,
  `order_hour`, `order_is_weekend`, `order_season`.
- Product mix at category/department level: `Category_Name`,
  `Department_Name`, `product_category_key`, `product_department_key`.
- Coarse customer and destination context: `Customer_Segment`,
  `Customer_Country`, `Customer_State`, `Market`, `Order_Country`,
  `Order_Region`, `Order_State`, and normalized equivalents.
- Geographic availability/match flags: `customer_zipcode_available`,
  `order_zipcode_available`, `geo_coordinates_available`,
  `customer_order_country_match`, `customer_order_state_match`.
- AO3 support denominator: `Order_Item_Total` as the selected order value for
  `predicted_profit_margin = predicted_order_profit / Order_Item_Total`.

Gold construction should still avoid including both raw and engineered duplicate
representations in the same final model matrix unless the model task explicitly
documents why both are needed.

## Excluded, Dashboard-Only, Or Lineage-Only Groups

These decisions are locked for the first model-ready Gold design:

- Exclude from model predictors: `Late_delivery_risk`,
  `Order_Profit_Per_Order`, `Benefit_per_order`, `Order_Item_Profit_Ratio`,
  direct profit transformations, realized margin fields,
  `Delivery_Status`, `Days_for_shipping_real`, `shipping_date_DateOrders`,
  `Order_Status`, sensitive customer identifiers, product status fields, and
  product description.
- Dashboard/audit only: delivery status, actual shipping duration, shipment
  timestamp, order status, duplicate profit/profit-ratio fields, product image,
  and historical outcome fields.
- Lineage/split/join only: `Order_Id`, `Order_Item_Id`,
  `order_date_DateOrders`, `_ingest_timestamp`, `_source_file`,
  `_silver_processed_timestamp`, and feature processed timestamp columns.
- Defer direct modeling use: raw customer IDs, product IDs, product names,
  product catalog keys, raw city, raw postal code, raw/rounded coordinates, and
  region-key composites.

## Finalization Status

The former group-validation questions in this preliminary inventory have been
answered by the team. Use `docs/pre_gold_modeling_decisions.md` as the
source-of-truth for first-pass Gold modeling policy.

## Recommended Next Gold Task Scope

Create the first leakage-safe Gold analytical tables for AO1, AO2, and AO3
support using `docs/pre_gold_modeling_decisions.md` as the finalized gating
policy. The next task should:

- build explicit target, predictor candidate, dashboard-only, and lineage-only
  column lists;
- retain `order_date_DateOrders` for chronological split assignment;
- apply the locked target/proxy/post-shipment exclusions;
- include approved candidate groups only;
- place conditional commercial, product-level, and granular geography fields in
  an excluded/review log rather than default predictors;
- not train models, resample, or select thresholds.
