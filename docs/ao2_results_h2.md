# AO2 Results and H2 Validation

Issue: `#39`

## 1. Purpose and Scope

This document synthesizes the existing AO2 profitability artifacts into a
report-ready validation-stage result section for H2. It does not train or
retrain models, rerun SHAP, change preprocessing, change AO2 Gold, alter
target policy, implement AO3, or evaluate the final test partition.

The evidence base is limited to saved AO2 validation artifacts from the Ridge
baseline, the selected XGBoost Gradient Boosting Regressor, the AO2 evaluation
pack, the AO2 SHAP explainability pack, and the AO2 target-reconstruction
audit.

## 2. AO2 Target Definition

AO2 estimates expected order-level profitability before dispatch. The target is:

```text
Order_Profit_Per_Order
```

The model output should be interpreted as an expected profitability estimate,
not as a guaranteed known profit at dispatch time. AO2 supports operational
prioritization and later AO3 risk-margin analysis, but it remains subject to
target-policy caveats because realized profit can be partly approximated by
near-formula commercial fields.

## 3. Target-Policy Framing

The AO2 predictor policy intentionally excludes target, proxy, duplicate,
post-shipment, and near-formula commercial fields. The reviewed artifacts
confirm exclusion of fields including:

- `Benefit_per_order`
- `Order_Item_Profit_Ratio`
- `Order_Item_Total`
- `ao3_order_value`
- `Sales`
- `Sales_per_customer`
- `Product_Price`
- `Order_Item_Discount`
- realized margin, profit-ratio, and direct profit outcome fields
- delivery outcome and post-shipment fields

`ao3_order_value` is excluded from AO2 predictors and reserved only as possible
AO3 support, such as a future predicted-margin denominator. Approved commercial
predictors such as `item_unit_price`, `item_discount_rate`, and
`order_item_quantity` are useful pre-dispatch signals, but they require cautious
interpretation because AO2 target reconstruction is a known methodological
risk.

## 4. Data Split and Validation Evidence

AO2 follows the project chronological split discipline. The source partition
contains an earliest 80% `development` set and a most recent 20% final `test`
set. Model comparison uses an inner chronological validation split inside the
development set:

| Slice | Rows | Use |
| --- | ---: | --- |
| `development_inner_train` | 115,532 | preprocessing fit and model training |
| `development_inner_validation` | 28,883 | model comparison, residual review, SHAP explanation, and H2 validation evidence |
| final `test` partition | 36,104 | reserved for future final AO2 evaluation |

All H2 statements in this document are based on held-out validation-slice
evidence. The final test partition was not used for training, preprocessing fit,
model selection, validation metrics, residual diagnostics, SHAP explainability,
target-reconstruction audit, or H2 conclusion. The generated metadata records:

```text
final_test_used = false
```

## 5. Models Compared

The AO2 comparison uses two existing models:

| Role | Model | Candidate |
| --- | --- | --- |
| Baseline | Ridge Regression | `fixed_alpha_1_0` |
| Primary model | XGBoost Gradient Boosting Regressor | `conservative_baseline` |

Both models use the approved AO2 preprocessing pipeline, which is fit only on
the training slice and applied unchanged to the validation slice.

## 6. Results Table

| Metric | Ridge baseline | Gradient Boosting Regressor | Improvement |
| --- | ---: | ---: | ---: |
| Validation rows | 28,883 | 28,883 | - |
| RMSE | 96.8276 | 95.6203 | 1.2073 lower |
| MAE | 54.2191 | 52.6463 | 1.5729 lower |
| R-squared (R2) | -0.0133 | 0.0118 | 0.0251 higher |
| Median absolute error | 32.5591 | 31.3954 | 1.1637 lower |
| Mean error / bias | 0.6453 | 0.9627 | slightly more underprediction |
| Wrong profit-sign share | 0.2536 | 0.1974 | 0.0562 lower |

The Gradient Boosting Regressor improves the primary AO2 metrics, RMSE and MAE,
relative to Ridge on the shared chronological validation slice. R-squared also
moves from slightly negative to slightly positive, although the absolute
explanatory power remains limited.

## 7. Residual Review

Residuals are defined as:

```text
actual Order_Profit_Per_Order - predicted_profit
```

Both models slightly underpredict on average, with mean residuals of `0.6453`
for Ridge and `0.9627` for Gradient Boosting. The bias is small relative to the
validation target standard deviation of `96.1905`, but the positive residual
medians show more typical underprediction of roughly `15` profit units.

Gradient Boosting reduces high-end absolute error: absolute-error p90 decreases
from `112.9203` for Ridge to `110.3725`. It also lowers the wrong profit-sign
share from `0.2536` to `0.1974`. This is useful for decision support because
profit-sign errors can change whether an order appears profitable or
loss-making.

The residual review still shows meaningful limitations. Both models compress
predictions toward the mean: the validation target standard deviation is
`96.1905`, while prediction standard deviation is `19.5479` for Ridge and
`11.9159` for Gradient Boosting. Both models still miss some extreme-profit
and severe-loss cases, with residual minima near `-1120`.

## 8. Explainability Summary

The AO2 SHAP explainability pack explains the selected Gradient Boosting model
on a 5,000-row sample from `development_inner_validation`. SHAP values explain
model behavior in predicted-profit units. They are model associations, not
causal effects.

The top SHAP driver families are:

| Driver family | Evidence | Interpretation caveat |
| --- | --- | --- |
| Commercial price | `numeric_continuous__item_unit_price` ranks first by mean absolute SHAP value. | Approved AO2 predictor, but close to commercial calculation context and should be interpreted cautiously. |
| Geography | Many top drivers are granular order-state, order-country, and customer-state one-hot levels. | Plausible market or fulfillment-context associations, but possibly sparse or unstable. |
| Product mix | Product category one-hot levels such as cardio equipment and fishing appear among top drivers. | Useful model signal, not a causal product-margin claim. |
| Discount and quantity | `item_discount_rate` and `order_item_quantity` appear in the top 20. | Approved commercial predictors, but carry target-policy caution. |

No SHAP conclusion should be written as a causal profitability lever. The
drivers are useful for business interpretation and leakage review, but the
model does not prove that changing a driver would change profit.

## 9. Target-Reconstruction Audit

Issue `#73` reviewed the selected AO2 Gradient Boosting predictor set, XGBoost
feature importance, SHAP drivers, and validation evidence for target
reconstruction risk.

| Audit item | Result |
| --- | --- |
| Final audit decision | `accepted_with_caution` |
| Forbidden feature count | `0` |
| Caution feature count | `1308` |
| Predictor audit status | `passed` |
| SHAP driver audit status | `passed` |
| Feature-importance audit status | `passed` |
| `ao3_order_value` detected as AO2 predictor or driver | no |
| Final test used | `false` |

The audit found no forbidden target-reconstruction fields in the reviewed AO2
predictors or dominant drivers. The `accepted_with_caution` decision means AO2
is defensible for pre-dispatch expected-profitability estimation, but it should
not be presented as a formula-like profit calculation. Caution-status drivers
require careful interpretation and do not automatically indicate leakage.

## 10. H2 Conclusion

H2 states:

```text
For order-profitability estimation, a gradient boosting regressor will
outperform linear or ridge regression on held-out data, particularly in RMSE
and MAE.
```

H2 is supported on the held-out validation slice because the Gradient Boosting
Regressor outperforms the Ridge baseline on the primary AO2 metrics, RMSE and
MAE, and also improves R-squared from negative to slightly positive. However,
the support is modest, and the model remains limited by residual error,
compressed predictions, and target-policy caveats.

This is validation-slice evidence only. H2 is not confirmed on the final test
partition in this issue.

## 11. Business Interpretation

AO2 can support pre-dispatch prioritization by estimating which orders are
expected to be more or less profitable before shipment. The Gradient Boosting
model adds some predictive value over the Ridge baseline, suggesting nonlinear
interactions among order timing, planned shipping, geography, product mix,
price, discount rate, and quantity.

The improvement is modest. Profitability remains difficult to predict precisely,
especially for extreme high-profit or loss-making orders. AO2 should therefore
be used as one input to decision support, not as a standalone rule for
operational intervention. Later AO3 work should combine expected profitability
with predicted late-delivery risk and should avoid using actual profit or
delivery outcomes to form priority groups.

## 12. Limitations

- Evidence is validation-stage only; final test evaluation remains reserved.
- AO2 estimates expected profitability and does not make profit fully known at
  dispatch time.
- The Gradient Boosting improvement over Ridge is directionally supportive but
  modest.
- Both models compress predictions toward the mean and miss some extreme
  outcomes.
- SHAP and feature importance describe model behavior, not causal effects.
- Approved commercial predictors and granular one-hot drivers require caution
  because AO2 target reconstruction and sparsity are known risks.
- No formal ablation or sensitivity rerun was performed in the
  target-reconstruction audit because issue guardrails prohibited retraining.

## 13. Artifact References

| Evidence | Path |
| --- | --- |
| AO2 preprocessing pipeline | `docs/ao2_preprocessing_pipeline.md` |
| Ridge baseline | `docs/ao2_ridge_baseline.md` |
| Gradient Boosting Regressor | `docs/ao2_gradient_boosting_regressor.md` |
| AO2 model evaluation | `docs/ao2_model_evaluation.md` |
| AO2 SHAP explainability | `docs/ao2_shap_explainability.md` |
| AO2 target-reconstruction review | `docs/ao2_target_reconstruction_review.md` |
| Evaluation metrics | `report/tables/ao2_model_evaluation_metrics.csv` |
| Residual diagnostics | `report/tables/ao2_residual_diagnostics_by_model.csv` |
| SHAP driver summary | `report/tables/ao2_shap_driver_summary.csv` |
| Target-reconstruction audit findings | `report/tables/ao2_target_reconstruction_audit_findings.md` |
| H2 summary table | `report/tables/ao2_results_h2_summary.csv` |
| H2 findings note | `report/tables/ao2_results_h2_findings.md` |
| H2 metadata | `models/ao2_profitability/results/ao2_results_h2_metadata.json` |
