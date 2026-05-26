# AO2 Model Evaluation Findings

Issue: `#37`

## Scope

This evaluation pack compares saved AO2 validation predictions only. It does not train models, change preprocessing, score final test rows, derive AO3 margins, or assign AO3 risk-margin groups.

Final test not used: the metadata field `final_test_used` is `false`.

Target-policy caveat: AO2 evaluation relies on the previously generated leakage-safe model artifacts where direct target, duplicate profit, realized margin, sales, order-value, and post-shipment fields were excluded from the predictor set. This pack evaluates predictions and does not reopen target-policy decisions.

## Validation Metrics

### ao2_gradient_boosting_regressor

- Validation rows: 28,883
- RMSE: 95.6203
- MAE: 52.6463
- R-squared: 0.0118
- Median absolute error: 31.3954
- Wrong profit-sign share: 0.1974

### ao2_ridge_baseline

- Validation rows: 28,883
- RMSE: 96.8276
- MAE: 54.2191
- R-squared: -0.0133
- Median absolute error: 32.5591
- Wrong profit-sign share: 0.2536

## H2 Evidence

Validation evidence is consistent with H2 because the Gradient Boosting Regressor improves over the Ridge baseline on RMSE and MAE.

- RMSE improvement versus Ridge: 1.2073
- MAE improvement versus Ridge: 1.5729
- R-squared moves from -0.0133 for Ridge to 0.0118 for Gradient Boosting.

This is validation-stage H2 evidence only. It is not final H2 confirmation on test data.

## Residual Review

- `ao2_gradient_boosting_regressor` underpredicts on average by 0.9627. Residual p10/p90 are -70.2391 and 72.1999; absolute-error p90 is 110.3725. Wrong profit-sign share is 0.1974.
- `ao2_ridge_baseline` underpredicts on average by 0.6453. Residual p10/p90 are -71.2244 and 73.8960; absolute-error p90 is 112.9203. Wrong profit-sign share is 0.2536.

Both models still compress predictions toward the target mean and miss extreme-profit cases, as shown by narrow prediction standard deviations relative to the target standard deviation and large residual ranges.

## Error Slices

Generated 28 error-slice rows across actual profit bands, actual target quartiles, and model-specific absolute-error bands. Very small slices are flagged with `is_unstable_small_slice` rather than being used for strong conclusions.

Operational slices were not joined in this issue because the saved validation prediction files already provide enough evidence for a compact evaluation pack, and joining back to AO2 partitions would require additional safeguards to avoid target/proxy fields such as `ao3_order_value`, `Order_Item_Total`, `Sales`, `Benefit_per_order`, or post-shipment labels.

## Limitations

- Final test remains untouched.
- The pack evaluates saved validation predictions only and does not inspect feature matrices or fitted preprocessing objects.
- The comparison depends on issue #35 and #36 artifacts being present and valid.
- Error-slice findings are descriptive validation diagnostics, not causal explanations.
- Comparison status in metadata: `complete`.
