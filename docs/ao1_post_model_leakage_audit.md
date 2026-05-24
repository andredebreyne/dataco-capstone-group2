# AO1 Post-Model Leakage Audit

Issue: `#31`

## Purpose

This audit reviews the AO1 late-delivery modeling workflow after model training
and validation. The objective is to confirm that the selected AO1 modeling
evidence is defensible for reporting and does not show signs of hidden leakage,
outcome proxies, or invalid test-set use.

## Scope

The audit covers the current AO1 validation workflow:

- AO1 chronological partitioning;
- AO1 preprocessing;
- Logistic Regression baseline;
- XGBoost classifier;
- AO1 model evaluation pack;
- AO1 decision-threshold policy;
- AO1 SHAP explainability workflow.

The final test partition remains reserved for final QA and reporting. This
audit does not score the final test partition and does not replace the final
leakage audit planned for W8.

## Evidence Reviewed

| Evidence Area | Source | Audit Result |
| --- | --- | --- |
| Chronological split boundary | `docs/chronological_split_policy.md`; AO1 partition metadata | Development and test are separated chronologically. Test is not used for model selection. |
| Preprocessing fit scope | `src/modeling/build_ao1_preprocessing_pipeline.py`; `docs/ao1_preprocessing_pipeline.md` | Imputation, encoding, and scaling are fit on the approved fitting/training slice only. |
| Logistic baseline scope | `src/modeling/train_ao1_logistic_regression_baseline.py`; baseline metadata | Trained on the training slice and evaluated on validation only. |
| XGBoost scope | `src/modeling/train_ao1_xgboost_classifier.py`; XGBoost metadata | Candidate comparison uses validation only; final test is not used. |
| Evaluation pack | `src/modeling/evaluate_ao1_models.py`; evaluation metadata | Compares validation predictions only and records complete/partial comparison status. |
| Threshold policy | `src/modeling/select_ao1_decision_threshold.py`; threshold metadata | Threshold selection uses validation trade-offs only. |
| Explainability | `src/modeling/explain_ao1_xgboost_shap.py`; SHAP metadata | Explains validation rows only; SHAP results are interpreted as model behavior, not causality. |

## Performance Plausibility Review

The validated AO1 metrics are directionally strong but not implausibly perfect.
The XGBoost classifier improves over the Logistic Regression baseline while
remaining within a realistic range for a pre-dispatch operational prediction
task.

Known validation results:

| Model | ROC-AUC | PR-AUC | Recall at 0.50 | Audit Interpretation |
| --- | ---: | ---: | ---: | --- |
| Logistic Regression baseline | 0.742996 | 0.831239 | 0.563924 | Plausible baseline performance; no obvious sign of target leakage. |
| XGBoost classifier | 0.775279 | 0.848912 | 0.583973 | Plausible improvement over baseline; not suspiciously high. |

The performance level does not by itself indicate leakage. If a future model
shows near-perfect validation or test performance, this audit must be reopened.

## Feature and Proxy Review

The approved AO1 predictors are designed to represent decision-time information:

- order-time calendar features;
- scheduled shipping/service fields;
- shipping mode and speed tier;
- product and department context;
- customer segment and region/order geography context;
- availability and match flags.

The following fields remain forbidden as AO1 predictors because they are targets,
post-shipment outcomes, or outcome proxies:

- `Late_delivery_risk`;
- `Delivery_Status`;
- `Days_for_shipping_real`;
- `shipping_date_DateOrders`;
- `Order_Status`;
- direct profit outcomes such as `Order_Profit_Per_Order`, `Benefit_per_order`,
  and `Order_Item_Profit_Ratio`.

The current modeling scripts explicitly exclude these fields from the feature
matrix. The SHAP workflow also validates against obvious leakage-like feature
tokens before the explainability output is accepted.

## Training-Only Transformation Review

The AO1 preprocessing and modeling workflow follows the train-only fitting rule:

- imputers, encoders, and scalers are fit on the training/fitting slice only;
- validation rows are transformed using fitted training objects;
- candidate model selection is based on validation metrics only;
- threshold selection is based on validation trade-offs only;
- final test rows are not used for training, model selection, threshold tuning,
  calibration review, or SHAP explainability.

SMOTE is not used in the current AO1 model workflow. XGBoost uses
`scale_pos_weight` calculated from the training slice rather than resampling.

## Explainability Plausibility Review

SHAP outputs must be reviewed for business plausibility before H1 is finalized.
The expected dominant drivers should align with operationally available factors,
such as shipping promise, service level, order timing, product/category context,
and geography. Any SHAP feature that resembles an actual delivery outcome,
shipping completion status, or realized profit field must trigger corrective
action before final reporting.

The current audit status is conditional on successful execution of:

```text
src/modeling/explain_ao1_xgboost_shap.py
tests/data_validation/validate_ao1_shap_explainability.py
```

## Corrective Actions

No corrective action is required for the current AO1 validation model evidence.

Required follow-up before H1 is finalized:

- attach or reference the validated SHAP driver summary from Issue `#30`;
- confirm the top SHAP features are business-plausible;
- keep final test metrics out of this audit until the W8 final QA task.

## Audit Conclusion

AO1 is acceptable to continue toward reporting, threshold review, and AO3
integration under a provisional leakage-safe status. The status becomes fully
ready for H1 write-up after the SHAP explainability PR is validated and reviewed.

