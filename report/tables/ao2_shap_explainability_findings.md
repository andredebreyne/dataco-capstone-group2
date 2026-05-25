# AO2 SHAP Explainability Findings

Issue: `#38`

## Scope

This memo explains the selected AO2 Gradient Boosting profitability model using SHAP values computed on validation rows only. The final test partition is not used for fitting, SHAP calculation, plots, findings, or validation.

## Method

- Selected model: `ao2_gradient_boosting_regressor`.
- Selected candidate: `conservative_baseline`.
- Model source: `deterministic_reconstruction`.
- Input slice: `development_inner_validation`.
- Validation rows explained: `5000`.
- SHAP method: `TreeExplainer`.
- SHAP output space: `raw model output in predicted profit units`.
- Preprocessing is the approved AO2 preprocessing pipeline, fit on the selected model training slice only.
- Interpretations are model explanations and associations, not causal effects.
- Changing a SHAP driver should not be interpreted as guaranteed to change order profitability.

## Top Drivers

| Rank | Feature | Mean Abs SHAP | Importance Share | Target Policy | Business Note |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `numeric_continuous__item_unit_price` | 106.216347 | 0.0684 | caution | Commercially plausible and approved, but interpret cautiously because profitability prediction is vulnerable to target reconstruction. |
| 2 | `categorical__order_state_normalized_kandahar` | 84.092453 | 0.0542 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 3 | `categorical__order_state_normalized_tadlaazilal` | 82.867599 | 0.0534 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 4 | `categorical__product_category_key_9_cardio_equipment` | 75.785034 | 0.0488 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 5 | `categorical__order_state_normalized_jeju` | 75.646225 | 0.0487 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 6 | `categorical__order_state_normalized_diana` | 52.950886 | 0.0341 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 7 | `categorical__order_state_normalized_nyanza` | 48.861282 | 0.0315 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 8 | `categorical__order_state_normalized_surjandarn` | 43.794174 | 0.0282 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 9 | `categorical__order_country_normalized_taiwn` | 40.522274 | 0.0261 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 10 | `categorical__order_state_normalized_yaroslavl` | 38.622509 | 0.0249 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 11 | `categorical__order_state_normalized_drenthe` | 37.939751 | 0.0244 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 12 | `categorical__order_state_normalized_stvropol` | 36.407619 | 0.0234 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 13 | `categorical__order_state_normalized_mequineztafilalet` | 31.921362 | 0.0206 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 14 | `categorical__order_state_normalized_zhytmyr` | 30.858191 | 0.0199 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 15 | `numeric_continuous__item_discount_rate` | 29.924955 | 0.0193 | caution | Commercially plausible and approved, but interpret cautiously because profitability prediction is vulnerable to target reconstruction. |
| 16 | `categorical__product_category_key_45_fishing` | 27.852291 | 0.0179 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 17 | `categorical__customer_state_normalized_in` | 26.737391 | 0.0172 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 18 | `categorical__order_state_normalized_tripura` | 24.843273 | 0.0160 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 19 | `categorical__order_state_normalized_gansu` | 24.207069 | 0.0156 | caution | Commercially plausible, but granular one-hot levels can be sparse or unstable and should not be overgeneralized. |
| 20 | `numeric_continuous__order_item_quantity` | 21.086575 | 0.0136 | caution | Commercially plausible and approved, but interpret cautiously because profitability prediction is vulnerable to target reconstruction. |

## Business Plausibility Review

The dominant AO2 SHAP drivers in this run are `numeric_continuous__item_unit_price`, `categorical__order_state_normalized_kandahar`, `categorical__order_state_normalized_tadlaazilal`, `categorical__product_category_key_9_cardio_equipment`, `categorical__order_state_normalized_jeju`. These drivers are commercially plausible when they represent shipping service, geography, product mix, customer context, timing, discount rate, unit price, or quantity. Granular one-hot features should be interpreted as model-specific category associations and not broad structural conclusions unless the team reviews support counts.

If `item_unit_price`, `item_discount_rate`, or `order_item_quantity` appear as top drivers, they are approved commercial predictors but require caution because AO2 target reconstruction is a known methodological risk.

## Target-Policy Review

The SHAP artifact generation checks both approved raw feature names and transformed feature names for AO2 target/proxy, leakage, identifier, partition, lineage, and final-test tokens. The top-driver target-policy statuses are recorded in the driver summary.

Caution-status top drivers: `numeric_continuous__item_unit_price`, `categorical__order_state_normalized_kandahar`, `categorical__order_state_normalized_tadlaazilal`, `categorical__product_category_key_9_cardio_equipment`, `categorical__order_state_normalized_jeju`, `categorical__order_state_normalized_diana`, `categorical__order_state_normalized_nyanza`, `categorical__order_state_normalized_surjandarn`.

Forbidden target/proxy fields such as `Order_Profit_Per_Order`, `Benefit_per_order`, `Order_Item_Profit_Ratio`, `Order_Item_Total`, `ao3_order_value`, `Sales`, `Sales_per_customer`, `Order_Item_Discount`, `Product_Price`, delivery outcome fields, post-shipment fields, partition labels, and identifiers must not appear as SHAP drivers.

## Caveats

- SHAP values explain the selected model behavior on validation rows only.
- SHAP values are associations, not causal effects.
- One-hot encoded levels may be sparse, granular, or unstable.
- The final test partition was not used.
- This explainability step does not change AO2 model selection, target policy, preprocessing, AO3 margin scoring, or H2 final-test conclusions.

## Artifacts

- SHAP feature importance: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao2_shap_feature_importance.csv`
- Driver summary: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao2_shap_driver_summary.csv`
- Top-feature plot: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/figures/modeling/ao2_shap_top_features.png`
- Metadata: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json`
