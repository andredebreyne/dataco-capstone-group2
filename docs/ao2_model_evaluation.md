# AO2 Model Evaluation

Issue: `#37`

## Purpose and Scope

This evaluation pack organizes the validation-slice evidence for the AO2
profitability models. It compares the existing Ridge baseline and Gradient
Boosting Regressor artifacts, reviews residual behavior, creates compact error
slices, and records the evidence needed to report H2 honestly at the validation
stage.

This issue does not train or retrain AO2 models, change preprocessing, change
AO2 Gold, evaluate final test rows, derive AO3 predicted margin, or assign AO3
risk-margin groups.

## Evaluated Models

| Model | Source issue | Candidate |
| --- | --- | --- |
| `ao2_ridge_baseline` | `#35` | `fixed_alpha_1_0` |
| `ao2_gradient_boosting_regressor` | `#36` | `conservative_baseline` |

Both models are evaluated from saved validation predictions only.

## Validation Slice

Evaluation slice:

```text
development_inner_validation
```

The current AO2 chronological partition artifact contains `development` and
`test` labels. The upstream model jobs created a chronological validation slice
inside `development` and left final `test` untouched.

Final test exclusion:

```text
final_test_used = false
```

Rows labelled as `test`, `final_test`, `holdout`, or `held_out` are rejected by
the evaluator and are not used for metrics, residual diagnostics, error slices,
findings, H2 evidence, or model comparison.

## Target Column

AO2 target:

```text
Order_Profit_Per_Order
```

The evaluator validates that the target and `predicted_profit` are numeric,
non-null, and available in each prediction artifact. It also checks residuals,
absolute errors, positive row counts, validation-only slice labels, and duplicate
model/key rows.

## Metric Definitions

Primary comparison metrics:

- RMSE: square-root average squared validation error; penalizes large misses.
- MAE: average absolute validation error; interpretable in profit units.
- R-squared: validation variance explained relative to a mean-only benchmark.

Supporting diagnostics include median absolute error, mean error, target and
prediction means and standard deviations, residual percentiles, and wrong
profit-sign share.

## Model Comparison

| Model | Validation rows | RMSE | MAE | R-squared | Median absolute error | Wrong profit-sign share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gradient Boosting Regressor | 28,883 | 95.6203 | 52.6463 | 0.0118 | 31.3954 | 0.1974 |
| Ridge baseline | 28,883 | 96.8276 | 54.2191 | -0.0133 | 32.5591 | 0.2536 |

Gradient Boosting improves validation RMSE by 1.2073 and validation MAE by
1.5729 relative to Ridge. R-squared moves from slightly negative for Ridge to
slightly positive for Gradient Boosting.

## Residual Review Summary

Both models underpredict on average, but the mean bias is small relative to the
target spread:

- Gradient Boosting mean residual: 0.9627.
- Ridge mean residual: 0.6453.

Gradient Boosting lowers absolute-error p90 from 112.9203 to 110.3725 and
reduces wrong profit-sign share from 0.2536 to 0.1974. However, both models
still compress predictions toward the mean. The validation target standard
deviation is 96.1905, while prediction standard deviation is 11.9159 for
Gradient Boosting and 19.5479 for Ridge. This indicates both models still miss
extreme-profit and severe loss cases.

## Error-Slice Summary

The error-slice table covers:

- actual profit bands, including negative/loss, low positive, medium positive,
  high positive, and extreme profit cases;
- actual target quartiles;
- model-specific absolute-error bands.

Very small slices are flagged through `is_unstable_small_slice`. No operational
join was used in this compact pack, so forbidden target/proxy fields were not
introduced as slice dimensions.

Forbidden slice dimensions not used:

- `ao3_order_value`
- `Order_Item_Total`
- `Sales`
- `Sales_per_customer`
- `Benefit_per_order`
- `Order_Item_Profit_Ratio`
- post-shipment fields
- final-test labels

## H2 Validation-Stage Interpretation

Validation evidence is consistent with H2 because the Gradient Boosting
Regressor improves over the Ridge baseline on RMSE and MAE.

This is validation-stage evidence only. It is not final H2 confirmation because
final test evaluation is outside issue `#37`.

## Target-Policy Safeguards

The evaluation pack depends on the upstream AO2 model artifacts where
target-reconstruction and leakage controls were already enforced. Those
controls exclude direct target, duplicate profit, realized margin, sales,
order-value, and post-shipment fields from the model predictor set.

Issue `#37` evaluates saved validation predictions. It does not change the AO2
target policy or inspect feature matrices as a substitute for the earlier
preprocessing and model-artifact validations.

## Assumptions and Limitations

- Both candidate prediction artifacts represent the same validation slice.
- Metrics are recomputed from saved validation predictions rather than copied
  from model-training output.
- Final test rows remain untouched.
- Residual and error-slice findings are descriptive diagnostics, not causal
  explanations.
- Operational slices are deferred until a future task can join safe descriptive
  fields without introducing target/proxy or post-shipment fields.

## Artifact Paths

| Artifact | Path |
| --- | --- |
| Evaluation script | `src/modeling/evaluate_ao2_models.py` |
| Validation script | `tests/data_validation/validate_ao2_evaluation_pack.py` |
| Metadata | `models/ao2_profitability/evaluation/ao2_evaluation_metadata.json` |
| Metrics table | `report/tables/ao2_model_evaluation_metrics.csv` |
| Residual diagnostics | `report/tables/ao2_residual_diagnostics_by_model.csv` |
| Error slices | `report/tables/ao2_error_slices.csv` |
| Findings note | `report/tables/ao2_model_evaluation_findings.md` |
| Ridge validation predictions | `report/tables/ao2_ridge_validation_predictions.csv` |
| Gradient Boosting validation predictions | `report/tables/ao2_gradient_boosting_validation_predictions.csv` |
