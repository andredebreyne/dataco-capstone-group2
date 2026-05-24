# AO1 SHAP Explainability

Issue: `#30`

## Scope

This memo explains the selected AO1 XGBoost validation model using SHAP values computed on the validation slice only. The final test partition is not used.

## Method

- Selected XGBoost candidate: `deeper_conservative`.
- Validation rows explained: `5000`.
- SHAP values are computed after the approved AO1 preprocessing pipeline.
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

The top drivers should be reviewed as operational signals related to order timing, shipping promise, geography, customer segment, and product/channel context. Any feature that appears to encode post-shipment outcomes must be treated as a leakage candidate and escalated before H1 is finalized.

## Artifacts

- SHAP feature importance: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_shap_feature_importance.csv`
- Driver summary: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_shap_driver_summary.csv`
- Top-feature plot: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/figures/ao1_shap_top_features.png`
- Metadata: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/models/ao1_late_delivery/explainability/ao1_shap_explainability_metadata.json`
