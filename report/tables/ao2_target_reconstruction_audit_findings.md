# AO2 Target-Reconstruction Audit Findings

Issue: `#73`

## Scope

This audit reviews the finalized AO2 Gradient Boosting predictor and driver evidence for target reconstruction. It does not retrain, retune, change preprocessing, change AO2 Gold, change partitions, evaluate final test, or implement AO3.

## Selected Model Reviewed

- Selected model: `ao2_gradient_boosting_regressor`.
- Selected candidate: `conservative_baseline`.
- Target column: `Order_Profit_Per_Order`.
- Final test used: `false`; final test not used for this audit or the upstream validation artifacts.

## Artifacts Reviewed

- AO2 preprocessing metadata.
- AO2 Gradient Boosting metadata.
- AO2 evaluation metadata and validation metrics.
- AO2 XGBoost feature importance.
- AO2 SHAP feature importance and driver summary.
- Existing AO2 target-policy and evaluation findings.

## Predictor Audit Result

- Forbidden feature count: `0`.
- Caution feature count: `1308`.
- Blocked features: none.
- `ao3_order_value` is reserved for later AO3 margin support and was not detected as an AO2 predictor, SHAP driver, or feature-importance driver.
- Direct profit targets, duplicate profit fields, realized profit-ratio fields, sales/order-value fields, discount amount, product price duplicates, delivery outcomes, post-shipment fields, partition labels, identifiers, and date-anchor metadata are excluded from the reviewed predictor set.

## SHAP and Feature Importance Driver Result

- The top SHAP drivers are commercially plausible validation-model associations, led by approved commercial, geography, product, and customer/location one-hot features.
- Approved commercial predictors such as `item_unit_price`, `item_discount_rate`, and `order_item_quantity` appear as drivers and are accepted with caution because AO2 target reconstruction is a known methodological risk.
- The top XGBoost feature-importance drivers include planned shipping/service, geography, product category, unit price, and quantity signals. These are plausible pre-dispatch drivers and are not formula-like under the current policy.
- Granular geography and product one-hot levels are accepted with caution because they can be sparse or unstable and should not be overgeneralized.

## Evaluation Evidence Result

- Gradient Boosting validation RMSE: `95.6203`.
- Gradient Boosting validation MAE: `52.6463`.
- Gradient Boosting validation R-squared: `0.0118`.
- Ridge validation RMSE: `96.8276`.
- Ridge validation MAE: `54.2191`.
- Ridge validation R-squared: `-0.0133`.
- RMSE improvement versus Ridge: `1.2073`.
- MAE improvement versus Ridge: `1.5729`.
- Performance strength assessment: `limited` validation explanatory power.

The modest validation improvement over Ridge and low validation R-squared reduce concern that the model is simply reconstructing the target by formula. This is supporting evidence, not proof; the stronger evidence is the explicit forbidden-feature exclusion plus SHAP and feature-importance driver review.

## Ablation or Sensitivity Status

No formal ablation rerun was performed in this issue. No existing lightweight ablation artifact was found, and the issue guardrails prohibit retraining, retuning, or model-selection changes. The audit therefore uses artifact-only sensitivity evidence: explicit forbidden-feature exclusion checks, SHAP driver review, XGBoost feature-importance review, modest validation performance, and the existing AO2 evaluation pack.

## Accepted Caveats

- `item_unit_price`, `item_discount_rate`, and `order_item_quantity` are approved commercial predictors but should be interpreted cautiously.
- Geography, product, and customer/location one-hot drivers can be sparse or unstable.
- SHAP and feature importance are associative model explanations, not causal estimates.
- Final-test evaluation remains deferred and was not used.

## Final Audit Decision

`accepted_with_caution`

Accepted with caution: no forbidden target-reconstruction fields were detected. The remaining AO2 predictor set is defensible for pre-dispatch profitability estimation, with caution notes for approved commercial predictors.

## Output Artifacts

- Forbidden feature check: `C:\Users\bruno\OneDrive - GUSCanada\data_analytics_MSc\T4-MDA-Winter_26\CPSC_620_-_Agile_-_Omid\Final_project\dataco-capstone-group2\report\tables\ao2_target_reconstruction_forbidden_feature_check.csv`
- Driver review: `C:\Users\bruno\OneDrive - GUSCanada\data_analytics_MSc\T4-MDA-Winter_26\CPSC_620_-_Agile_-_Omid\Final_project\dataco-capstone-group2\report\tables\ao2_target_reconstruction_driver_review.csv`
- Metadata: `C:\Users\bruno\OneDrive - GUSCanada\data_analytics_MSc\T4-MDA-Winter_26\CPSC_620_-_Agile_-_Omid\Final_project\dataco-capstone-group2\models\ao2_profitability\target_reconstruction_audit\ao2_target_reconstruction_audit_metadata.json`
- Documentation: `C:\Users\bruno\OneDrive - GUSCanada\data_analytics_MSc\T4-MDA-Winter_26\CPSC_620_-_Agile_-_Omid\Final_project\dataco-capstone-group2\docs\ao2_target_reconstruction_review.md`
