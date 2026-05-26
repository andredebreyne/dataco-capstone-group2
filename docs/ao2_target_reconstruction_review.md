# AO2 Target-Reconstruction Review

Issue: `#73`

## Purpose and Scope

This note documents the AO2 target-reconstruction review for the finalized Gradient Boosting profitability model. It confirms whether the selected predictor set and dominant drivers are defensible for pre-dispatch profitability estimation rather than formula-like target reconstruction.

The review is audit-only. It does not retrain or retune AO2, change the selected model, change preprocessing, change AO2 Gold or partitions, evaluate final test, change target policy, or implement AO3.

## Why AO2 Needs This Audit

`Order_Profit_Per_Order` can be duplicated or approximated by near-formula commercial fields such as duplicate profit, realized profit ratio, order value, sales, discount amount, and product price fields. A profitability model can look strong while reconstructing accounting outcomes. The audit checks raw predictors and transformed drivers against the frozen target-policy rules.

## Selected Model Reviewed

- Selected model: `ao2_gradient_boosting_regressor`.
- Selected candidate: `conservative_baseline`.
- Target: `Order_Profit_Per_Order`.
- Review slice: validation artifacts only.
- Final test not used.

## Target-Policy Rules Reviewed

Forbidden AO2 predictors and drivers include the target, duplicate profit fields, realized profit-ratio or margin fields, `Order_Item_Total`, `ao3_order_value`, `Sales`, `Sales_per_customer`, `Order_Item_Discount`, `Product_Price`, delivery outcome fields, post-shipment fields, final-test or holdout labels, identifiers, partition labels, date anchors, and lineage metadata.

Approved commercial predictors such as `item_unit_price`, `item_discount_rate`, `order_item_quantity`, planned shipping features, product/category descriptors, and customer/geography descriptors are allowed but carry caution labels for interpretation.

## Artifacts Reviewed

- `models/ao2_profitability/preprocessing/ao2_preprocessing_metadata.json`
- `models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metadata.json`
- `models/ao2_profitability/evaluation/ao2_evaluation_metadata.json`
- `models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json`
- `report/tables/ao2_model_evaluation_metrics.csv`
- `report/tables/ao2_model_validation_comparison.csv`
- `report/tables/ao2_gradient_boosting_feature_importance.csv`
- `report/tables/ao2_shap_feature_importance.csv`
- `report/tables/ao2_shap_driver_summary.csv`
- `report/tables/ao2_model_evaluation_findings.md`
- `report/tables/ao2_shap_explainability_findings.md`

## Predictor-Set Audit Result

The audit found `0` forbidden predictor or driver rows and `1308` caution-status reviewed features. Because no forbidden feature was detected, the predictor set is not blocked by target-reconstruction policy.

`ao3_order_value` was not detected as an AO2 predictor, SHAP driver, or feature-importance driver. It remains reserved for later AO3 predicted-margin support only.

## SHAP and Feature-Importance Result

The top SHAP and XGBoost importance drivers are commercially plausible pre-dispatch signals: unit price, discount rate, quantity, planned shipping/service, geography, product category, and customer/location one-hot features. These drivers do not show direct target, duplicate target, realized margin, order-value, sales, post-shipment, partition, identifier, or final-test fields.

Commercial predictors are accepted with caution because they sit near the commercial formula context. Granular geography and product one-hot drivers are also accepted with caution because support counts and stability should be reviewed before broad business claims.

## Evaluation Evidence Result

Gradient Boosting validation RMSE/MAE/R-squared were `95.6203`, `52.6463`, and `0.0118`. Ridge validation RMSE/MAE/R-squared were `96.8276`, `54.2191`, and `-0.0133`.

The improvement over Ridge is useful but modest, and validation R-squared remains limited. This reduces concern that the model is formula-reconstructing the target, but it does not prove absence of leakage by itself.

## Ablation or Sensitivity Status

No formal ablation rerun was performed. No existing lightweight ablation artifact was available, and this issue intentionally avoids retraining or feature-elimination experiments. The compensating evidence is the explicit forbidden-feature audit, SHAP driver review, feature-importance review, modest validation performance, and upstream evaluation pack.

## Final Decision

`accepted_with_caution`

Accepted with caution: no forbidden target-reconstruction fields were detected. The remaining AO2 predictor set is defensible for pre-dispatch profitability estimation, with caution notes for approved commercial predictors.

## Limitations

- This audit reviews existing artifacts; it does not generate new model evidence.
- SHAP and feature importance are associative, not causal.
- One-hot driver sparsity is not re-estimated here.
- Final-test evaluation remains untouched.

## Output Artifacts

- Forbidden feature check: `report/tables/ao2_target_reconstruction_forbidden_feature_check.csv`
- Driver review: `report/tables/ao2_target_reconstruction_driver_review.csv`
- Findings note: `report/tables/ao2_target_reconstruction_audit_findings.md`
- Metadata: `models/ao2_profitability/target_reconstruction_audit/ao2_target_reconstruction_audit_metadata.json`
