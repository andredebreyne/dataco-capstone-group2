# AO1 SHAP Explainability

Issue: `#30`

## Scope

This memo explains the selected AO1 XGBoost validation model using SHAP values computed on the validation slice only. The final test partition is not used.

## Method

- Selected XGBoost candidate: `deeper_conservative`.
- Validation rows explained: `5000`.
- SHAP values are computed after the approved AO1 preprocessing pipeline.
- Model source: `deterministic_reconstruction` from `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_metadata.json`.
- SHAP method: `TreeExplainer` for the positive class `Late_delivery_risk = 1`.
- SHAP output space: `raw margin / log-odds`.
- Interpretations are model associations, not causal effects.

## Dominant Late-Delivery Drivers

| Rank | Feature | Mean Abs SHAP | Importance Share | Direction Note |
| ---: | --- | ---: | ---: | --- |
| 1 | `categorical__shipping_mode_normalized_first_class` | 5.780122 | 0.3810 | positive average contribution to late-delivery risk |
| 2 | `categorical__order_state_normalized_tabasco` | 0.312278 | 0.0206 | negative average contribution to late-delivery risk |
| 3 | `categorical__order_state_normalized_murcia` | 0.309529 | 0.0204 | positive average contribution to late-delivery risk |
| 4 | `numeric_continuous__scheduled_shipping_days` | 0.302371 | 0.0199 | positive average contribution to late-delivery risk |
| 5 | `categorical__shipping_speed_tier_standard` | 0.268366 | 0.0177 | negative average contribution to late-delivery risk |
| 6 | `categorical__order_country_normalized_repblica_democrtica_del_congo` | 0.239810 | 0.0158 | positive average contribution to late-delivery risk |
| 7 | `categorical__order_state_normalized_duarte` | 0.229900 | 0.0152 | positive average contribution to late-delivery risk |
| 8 | `categorical__order_state_normalized_manawatuwanganui` | 0.204806 | 0.0135 | positive average contribution to late-delivery risk |
| 9 | `categorical__order_state_normalized_jrkov` | 0.183516 | 0.0121 | positive average contribution to late-delivery risk |
| 10 | `categorical__order_state_normalized_atlntida` | 0.172925 | 0.0114 | positive average contribution to late-delivery risk |
| 11 | `categorical__order_state_normalized_limburgo` | 0.161463 | 0.0106 | positive average contribution to late-delivery risk |
| 12 | `categorical__order_country_normalized_suecia` | 0.160949 | 0.0106 | positive average contribution to late-delivery risk |
| 13 | `categorical__order_state_normalized_matanzas` | 0.160918 | 0.0106 | negative average contribution to late-delivery risk |
| 14 | `categorical__order_state_normalized_ontario` | 0.158871 | 0.0105 | negative average contribution to late-delivery risk |
| 15 | `categorical__order_state_normalized_mazovia` | 0.158827 | 0.0105 | negative average contribution to late-delivery risk |
| 16 | `categorical__order_state_normalized_marche` | 0.156439 | 0.0103 | negative average contribution to late-delivery risk |
| 17 | `categorical__order_state_normalized_flanders_oriental` | 0.152088 | 0.0100 | positive average contribution to late-delivery risk |
| 18 | `categorical__order_state_normalized_dar_es_salaam` | 0.141989 | 0.0094 | negative average contribution to late-delivery risk |
| 19 | `categorical__order_state_normalized_delhi` | 0.136049 | 0.0090 | negative average contribution to late-delivery risk |
| 20 | `categorical__order_state_normalized_ginebra` | 0.130987 | 0.0086 | positive average contribution to late-delivery risk |

## Business Plausibility Check

The leading SHAP drivers are operationally plausible for pre-dispatch late-delivery risk because they emphasize the shipping promise, scheduled shipping window, and geographic fulfillment context available before dispatch. The dominant driver in this run is `categorical__shipping_mode_normalized_first_class`; if this effect remains much larger than the others, the team should review it as a possible service-level or data-pattern concentration before final H1 reporting. Geography and shipping-speed drivers should be described as model associations that support prioritization and monitoring, not as proof that changing a single field will causally reduce late deliveries.

Top-driver interpretation for report reuse:

- Shipping mode and shipping-speed features indicate that the promised fulfillment service level is central to the model's late-risk ranking.
- Scheduled shipping days captures the planned order-to-dispatch window and is a plausible pre-shipment timing signal.
- Geography features can reflect route complexity, regional operations, or market-specific patterns, but should be reviewed for sparse one-hot categories before broad conclusions.
- SHAP explains the selected model behavior for `Late_delivery_risk = 1` in raw margin / log-odds space; values are directional model explanations, not causal effects.

## Artifacts

- SHAP feature importance: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_shap_feature_importance.csv`
- Driver summary: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_shap_driver_summary.csv`
- Top-feature plot: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/figures/ao1_shap_top_features.png`
- Metadata: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/models/ao1_late_delivery/explainability/ao1_shap_explainability_metadata.json`
