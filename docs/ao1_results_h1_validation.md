# AO1 Results and H1 Validation

Issue: `#32`

## Purpose

This document summarizes the AO1 late-delivery modeling results in a
report-ready format and states the current validation-stage conclusion for H1.
It uses validation evidence only. The final test partition remains reserved for
final AO1 quality assurance and must not be reported as already evaluated.

## Research Question and Hypothesis

AO1 asks whether order-level late-delivery risk can be predicted before
dispatch using decision-time information from the DataCo supply chain dataset.

Project hypothesis H1 states:

```text
For late-delivery prediction, an XGBoost classifier will outperform logistic
regression on held-out data, particularly in AUC-ROC and recall.
```

The current evidence supports H1 at the validation stage. XGBoost outperforms
the Logistic Regression baseline on ROC-AUC, PR-AUC, accuracy, precision,
recall, F1, and log loss on the shared chronological validation slice.

## Data and Modeling Scope

The AO1 target is `Late_delivery_risk`, where `1` represents a historical
late-delivery event and `0` represents a non-late delivery outcome under the
approved AO1 target policy.

The modeling workflow uses the leakage-safe AO1 Gold analytical table,
chronological partitions, and approved AO1 preprocessing pipeline. The current
partition structure is:

| Slice | Rows | Use |
| --- | ---: | --- |
| Development inner training | 110,569 | Preprocessing fit and model training |
| Development inner validation | 27,643 | Model comparison, threshold review, and validation metrics |
| Final test | 34,553 | Reserved for final AO1 evaluation |

The final test partition is not used for preprocessing fit, model selection,
candidate comparison, threshold selection, SHAP explainability, or H1
validation in this document.

## Model Comparison

The validation comparison uses the shared AO1 evaluation pack and the same
chronological validation slice for both models.

| Model | ROC-AUC | PR-AUC | Accuracy | Precision at 0.50 | Recall at 0.50 | F1 at 0.50 | Log loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| XGBoost classifier | 0.7753 | 0.8489 | 0.7212 | 0.8890 | 0.5840 | 0.7049 | 0.5133 |
| Logistic Regression baseline | 0.7426 | 0.8307 | 0.6856 | 0.8296 | 0.5645 | 0.6718 | 0.5723 |

XGBoost improves ROC-AUC by 0.0327 and recall by 0.0195 at the default 0.50
threshold. The improvement is directionally consistent with H1: the nonlinear
model ranks late-delivery cases better than the linear baseline and captures a
slightly larger share of late orders without sacrificing precision.

The selected XGBoost candidate is `deeper_conservative`, chosen from a small
validation-only candidate set using ROC-AUC as the primary selection metric and
recall as the secondary metric.

## Driver Patterns

The finalized Issue `#30` SHAP artifacts are the primary explainability source
for AO1 driver interpretation. SHAP values explain the selected XGBoost model
on validation rows only and are model associations, not causal effects.

| Driver family | SHAP evidence | Reporting caveat |
| --- | --- | --- |
| Shipping mode | `categorical__shipping_mode_normalized_first_class` is the dominant SHAP feature, with mean absolute SHAP `5.780122` and importance share `0.3810`. | Operationally plausible as a service-promise signal, but unusually dominant. Report as a model pattern to monitor, not as proof that First Class shipping causes lateness. |
| Scheduled service window | `numeric_continuous__scheduled_shipping_days` ranks 4 with importance share `0.0199`; `categorical__shipping_speed_tier_standard` ranks 5 with share `0.0177`. | These are pre-dispatch planning fields and support the service-promise interpretation. |
| Geography | Many top-20 SHAP features are granular order-state or order-country indicators, including `order_state_normalized_tabasco`, `order_state_normalized_murcia`, and `order_country_normalized_repblica_democrtica_del_congo`. | Geography is available at order creation, but sparse or high-cardinality one-hot effects should be interpreted cautiously. |

These patterns align with the AO1 bivariate EDA, where planned service fields
such as scheduled shipping days, shipping mode, shipping speed tier, and
standard-shipping indicators showed the strongest support-safe descriptive
variation in late-delivery rates.

The merged Issue `#31` leakage audit reviewed these SHAP outputs and found no
driver resembling the AO1 target, actual shipping duration, delivery status,
shipping completion status, realized profit, final-test labels, or another
direct post-outcome proxy.

## Threshold Choice and AO3 Implications

AO1 prioritization should not depend only on the default 0.50 probability
threshold. The documented threshold policy prioritizes recall while keeping the
predicted positive rate operationally manageable.

Using the current threshold grid for the XGBoost classifier, no evaluated
threshold satisfies both:

```text
recall >= 0.70
predicted_positive_rate <= 0.65
```

The policy therefore falls back to the highest-recall threshold under the alert
rate cap. The current validation recommendation is:

| Model | Threshold | Precision | Recall | Predicted positive rate | False negatives | False positives |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| XGBoost classifier | 0.35 | 0.8469 | 0.6171 | 0.4154 | 6,035 | 1,758 |

Operational implication for AO3:

```text
Classify an order as AO1 high-risk when predicted_probability >= 0.35.
```

This threshold creates a materially larger intervention queue than the default
0.50 threshold, but it reduces missed late-delivery cases while keeping the
alert rate below the 65% cap. AO3 should combine this predicted late-delivery
risk flag with predicted profitability, not actual profit or actual delivery
outcomes.

## Leakage and Validity Controls

The AO1 result is currently defensible because the workflow applies the project
leakage-control rules:

- target and post-delivery fields are excluded from predictors;
- `Delivery_Status`, `Days_for_shipping_real`, `shipping_date_DateOrders`, and
  `Order_Status` are not used as AO1 model features;
- preprocessing is fit on the training slice only;
- validation is chronological and separate from the fitting slice;
- final test data is reserved for final evaluation;
- threshold selection uses validation trade-offs only;
- SMOTE is not used in the current AO1 workflow.

The merged post-model leakage audit considers AO1 leakage-safe enough to report
with caveats. The reviewed artifacts show no evidence of post-outcome leakage in
AO1 validation modeling, but this does not prove leakage is impossible. The
documented caveats are the unusually dominant First Class shipping-mode SHAP
effect, sparse or high-cardinality geography indicators, and the untouched
final-test boundary.

## H1 Conclusion

H1 is supported at the validation stage.

The XGBoost classifier outperforms Logistic Regression on the shared held-out
validation slice, including ROC-AUC and recall, while preserving the
leakage-control boundary and final-test holdout. The strongest predictive
patterns are also business-plausible because they center on planned shipping
service, scheduled shipping duration, order timing, and geography rather than
post-delivery outcome fields.

The conclusion should be worded carefully in the final report:

```text
Validation evidence supports H1: the XGBoost classifier achieved stronger
held-out validation performance than Logistic Regression for AO1 late-delivery
prediction, particularly in ROC-AUC and recall. Final confirmation remains
subject to the reserved test-set evaluation, and driver interpretation should
carry the reviewed SHAP and leakage-audit caveats.
```

## Limitations

- The current H1 conclusion is based on validation evidence, not final test
  results.
- Recall remains moderate at operationally manageable thresholds, so AO1 should
  be positioned as a prioritization aid rather than a complete late-delivery
  detection solution.
- SHAP and leakage-audit caveats should remain visible in the academic report,
  especially the dominant First Class shipping-mode effect and granular
  geography stability.
- Threshold choice reflects a business trade-off between missed late deliveries
  and operational alert volume.

## Source Artifacts

| Evidence | Path |
| --- | --- |
| Project proposal summary | `docs/proposal/proposal_summary.md` |
| AO1 target definition | `docs/ao1_target_definition.md` |
| AO1 model evaluation pack | `docs/ao1_model_evaluation.md` |
| AO1 validation comparison | `report/tables/ao1_model_validation_comparison.csv` |
| AO1 threshold grid | `report/tables/ao1_threshold_tradeoff_grid.csv` |
| AO1 XGBoost feature importance | `report/tables/ao1_xgboost_classifier_feature_importance.csv` |
| AO1 SHAP workflow | `docs/ao1_shap_explainability.md` |
| AO1 SHAP driver summary | `report/tables/ao1_shap_driver_summary.csv` |
| AO1 threshold policy | `docs/ao1_decision_threshold.md` |
| AO1 post-model leakage audit | `docs/ao1_post_model_leakage_audit.md` |
