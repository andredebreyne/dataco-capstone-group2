# AO2 Results and H2 Findings

Issue: `#39`

## AO2 Methods Summary

AO2 estimates expected order-level profitability before dispatch using the
target `Order_Profit_Per_Order`. The model output is an expected profitability
estimate, not a guaranteed known profit at dispatch time.

The synthesis uses existing AO2 artifacts only. It does not retrain models,
rerun SHAP, change predictors, change preprocessing, change target policy,
evaluate final test, or implement AO3.

AO2 predictor policy excludes direct target, duplicate profit, realized margin,
near-formula commercial, delivery outcome, and post-shipment fields. Excluded
fields include `Benefit_per_order`, `Order_Item_Profit_Ratio`,
`Order_Item_Total`, `ao3_order_value`, `Sales`, `Sales_per_customer`,
`Product_Price`, and `Order_Item_Discount`. `ao3_order_value` is reserved only
as possible AO3 support later.

Evidence slice: `development_inner_validation`. Final test not used:
`final_test_used = false`.

## Model Comparison

| Model | Validation rows | RMSE | MAE | R-squared (R2) | Median absolute error | Mean error | Wrong profit-sign share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ridge baseline | 28,883 | 96.8276 | 54.2191 | -0.0133 | 32.5591 | 0.6453 | 0.2536 |
| Gradient Boosting Regressor | 28,883 | 95.6203 | 52.6463 | 0.0118 | 31.3954 | 0.9627 | 0.1974 |

Gradient Boosting improves validation RMSE by `1.2073` and MAE by `1.5729`
relative to Ridge. R-squared improves from `-0.0133` to `0.0118`.

## Residual Review

Both models slightly underpredict on average. Gradient Boosting mean residual
is `0.9627`; Ridge mean residual is `0.6453`. Gradient Boosting reduces
absolute-error p90 from `112.9203` to `110.3725` and wrong profit-sign share
from `0.2536` to `0.1974`.

Both models still compress predictions toward the mean. The validation target
standard deviation is `96.1905`, while prediction standard deviation is
`11.9159` for Gradient Boosting and `19.5479` for Ridge. Both models still miss
some extreme-profit and severe-loss cases.

## Explainability Summary

SHAP explains the selected Gradient Boosting model on validation rows only and
should be read as model behavior, not causal impact. The top driver families
include item unit price, granular geography one-hot levels, product-category
one-hot levels, item discount rate, and order item quantity.

Approved commercial predictors such as `item_unit_price`,
`item_discount_rate`, and `order_item_quantity` are plausible but require
caution because AO2 target reconstruction is a known risk. Granular geography,
product, and customer one-hot drivers may be sparse or unstable and should not
be overgeneralized.

## Target-Reconstruction Audit Summary

Issue `#73` concluded `accepted_with_caution`.

| Audit item | Result |
| --- | --- |
| Forbidden feature count | `0` |
| Caution feature count | `1308` |
| Predictor audit | `passed` |
| SHAP driver audit | `passed` |
| Feature-importance audit | `passed` |
| `ao3_order_value` detected | no |
| Final test used | `false` |

No forbidden target-reconstruction fields were detected. The caution status
means AO2 is defensible for pre-dispatch expected-profitability estimation, but
it should not be interpreted as a formula-like profit calculation.

## H2 Conclusion

H2 is supported on the held-out validation slice because the Gradient Boosting
Regressor outperforms the Ridge baseline on the primary AO2 metrics, RMSE and
MAE, and also improves R-squared from negative to slightly positive. However,
the support is modest, and the model remains limited by residual error,
compressed predictions, and target-policy caveats.

This is not a final-test conclusion.

## Business Interpretation and Limitations

AO2 can support pre-dispatch prioritization by estimating expected
profitability before shipment. The Gradient Boosting model adds some predictive
value over Ridge, suggesting nonlinear interactions among order, shipping,
geography, product, and commercial context. The improvement is modest, so AO2
should be used as a decision-support input rather than a standalone operational
rule.

Limitations: final test remains untouched; profitability is estimated rather
than known at dispatch; residual errors remain large; predictions are
compressed toward the mean; SHAP and feature importance are associative and not
causal; approved commercial predictors require target-policy caution.
