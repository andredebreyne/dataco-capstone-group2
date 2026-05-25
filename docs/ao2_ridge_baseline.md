# AO2 Ridge Baseline

Issue: `#35`

## Purpose and Scope

This baseline trains a leakage-safe Ridge Regression model for AO2 order-level
profitability estimation. It is the linear baseline comparator for H2, where a
future gradient boosting regressor is expected to improve RMSE and MAE.

This issue does not train the gradient boosting regressor, evaluate final test
data, derive AO3 predicted margin, assign AO3 priority groups, rebuild AO2
Gold, rebuild chronological partitions, or change AO2 preprocessing logic.

## Source Artifact

| Artifact | Path |
| --- | --- |
| AO2 partition Delta table | `/Volumes/workspace/default/raw_data/gold/ao2_profitability_chronological_partitions` |
| Training script | `src/modeling/train_ao2_ridge_baseline.py` |
| Validation script | `tests/data_validation/validate_ao2_ridge_baseline.py` |
| Metadata JSON | `models/ao2_profitability/ridge_baseline/ao2_ridge_baseline_metadata.json` |
| Metrics JSON | `models/ao2_profitability/ridge_baseline/ao2_ridge_baseline_metrics.json` |
| Validation metrics CSV | `report/tables/ao2_ridge_validation_metrics.csv` |
| Residual diagnostics CSV | `report/tables/ao2_ridge_residual_diagnostics.csv` |
| Validation predictions CSV | `report/tables/ao2_ridge_validation_predictions.csv` |
| Coefficients CSV | `report/tables/ao2_ridge_coefficients.csv` |

The input path can be overridden with:

```text
DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH
```

## Training and Validation Split

The current AO2 partition artifact contains `development` and `test` labels.
Therefore, the baseline creates an internal chronological validation split
inside `development` only:

```text
ordering = order_date_DateOrders ASC, Order_Id ASC, Order_Item_Id ASC
development_inner_train = first 80% of development rows
development_inner_validation = final 20% of development rows
```

The committed AO2 partition summary reports 144,415 development rows and
36,104 final test rows. Under the internal rule above, the expected current
inner training count is 115,532 and the expected validation count is 28,883.
The training script recomputes these counts from the Delta table at runtime.

The final `test` partition is not used for training, preprocessing fit,
validation metrics, residual diagnostics, coefficient review, model selection,
or predictions in this issue.

## Target and Predictors

Target:

```text
Order_Profit_Per_Order
```

The baseline uses the approved AO2 preprocessing factory:

```text
src.modeling.build_ao2_preprocessing_pipeline.build_sklearn_preprocessor
```

Preprocessing is fit only on the Ridge training slice. The validation slice is
transformed with the fitted preprocessing object without refitting. The final
test partition is not transformed or scored by this baseline job.

Forbidden predictor exclusions are enforced from the AO2 preprocessing policy,
including:

- `Order_Profit_Per_Order`
- `Benefit_per_order`
- `Order_Item_Profit_Ratio`
- `Order_Item_Total`
- `ao3_order_value`
- `Sales`
- `Sales_per_customer`
- `Order_Item_Discount`
- `Product_Price`
- realized margin or direct profit outcome fields
- delivery outcome and post-shipment fields
- identifier, date, partition, and lineage columns

`ao3_order_value` remains reserved for future AO3 predicted-margin
construction and is not an AO2 predictor.

## Model Configuration

Primary baseline:

```python
Ridge(alpha=1.0)
```

No grid search, alpha tuning, target encoding, target transformation, final
test scoring, or gradient boosting is performed in this issue.

Ridge is used instead of plain ordinary least squares because the approved AO2
preprocessing includes one-hot encoding and scaled numeric features, which can
introduce multicollinearity. Ridge gives a more stable linear baseline while
remaining simple and reproducible.

## Validation Results

These are validation-only results from `development_inner_validation`.
They are not final test metrics.

| Metric | Value |
| --- | ---: |
| Validation rows | 28,883 |
| RMSE | 96.8276 |
| MAE | 54.2191 |
| R2 | -0.0133 |
| Median absolute error | 32.5591 |
| Mean error / bias | 0.6453 |
| Target mean | 21.7130 |
| Target standard deviation | 96.1905 |
| Prediction mean | 21.0677 |
| Prediction standard deviation | 19.5479 |

The mean prediction is close to the validation target mean, and the mean
residual is small. However, RMSE is approximately as large as the target
standard deviation and R2 is slightly negative, so this Ridge model does not
explain validation profitability better than a mean-only benchmark on this
slice. It is still useful because it establishes a conservative linear baseline
for the future nonlinear AO2 model comparison.

## Residual Diagnostics

Residuals are defined as:

```text
actual Order_Profit_Per_Order - predicted_profit
```

| Diagnostic | Value |
| --- | ---: |
| Residual mean | 0.6453 |
| Residual median | 15.6653 |
| Residual standard deviation | 96.8271 |
| Residual minimum | -1124.2730 |
| Residual maximum | 258.5917 |
| Absolute error median | 32.5591 |
| Absolute error p90 | 112.9203 |
| Wrong profit-sign share | 0.2536 |

The model is only slightly low-biased on average: actual profit exceeds
predicted profit by about 0.65 on average. The positive residual median shows a
more typical low prediction of about 15.67, while the large negative residual
minimum indicates at least one severe overprediction on an extreme low-profit
or loss-making order. The prediction standard deviation is much smaller than
the target standard deviation, which means the Ridge baseline compresses
predictions toward the mean and struggles with high-variance or extreme-profit
orders.

Errors are large relative to the target scale. The median absolute error is
32.56, the 90th percentile absolute error is 112.92, and about 25.36% of
validation rows have the wrong predicted profit sign. This is a clear weakness
for a profitability model because sign errors can change whether an order looks
profitable or loss-making.

## Baseline Interpretation for H2

Ridge is the AO2 linear baseline for H2. It provides a credible benchmark
because it uses the approved AO2 preprocessing pipeline, respects the
chronological validation design, excludes target-reconstruction fields, and
keeps the final test set untouched.

The current validation results also show why a nonlinear model is worth testing:
the Ridge baseline captures the broad target mean but underfits the spread of
profitability outcomes. H2 should not be evaluated yet; that requires the
future gradient boosting regressor to be trained and compared against this
baseline on the same validation design.

## Where Ridge Performs Reasonably

- The prediction mean is close to the validation target mean.
- The mean error is small, suggesting little average directional bias.
- Ridge provides a stable, reproducible baseline under a high-dimensional
  one-hot encoded feature space.
- The median absolute error is lower than RMSE, indicating many ordinary
  validation rows have moderate errors even though larger misses inflate RMSE.

## Where Ridge Falls Short

- R2 is slightly negative on validation, so the baseline does not improve on a
  mean-only benchmark for this slice.
- The model has a linear/additive structure and is not designed to capture
  nonlinear pricing, discount, product, geography, and fulfillment-service
  interactions.
- Predictions are compressed toward the mean, as shown by prediction standard
  deviation of 19.55 versus target standard deviation of 96.19.
- Extreme-profit and loss-making orders appear difficult for the model, as
  shown by the large residual range and high RMSE.
- About one quarter of validation rows have the wrong predicted profit sign.

## Coefficient Interpretation

The coefficient artifact contains the top 100 transformed features by absolute
coefficient magnitude from a 1,306-feature preprocessed space. The largest
coefficients are dominated by one-hot encoded geography fields, especially
`order_state_normalized` levels. Examples include:

| Feature | Coefficient |
| --- | ---: |
| `categorical__order_state_normalized_kandahar` | -178.5716 |
| `categorical__order_state_normalized_diana` | -153.0425 |
| `categorical__order_state_normalized_mie` | -146.4498 |
| `categorical__order_state_normalized_jeju` | -143.0345 |
| `categorical__order_state_normalized_kabarole` | -134.8577 |
| `categorical__order_state_normalized_oriental` | 91.6901 |
| `categorical__order_country_normalized_nepal` | 84.7405 |
| `categorical__order_state_normalized_lusaka` | 76.9818 |

These coefficients should be treated as associative screening evidence only.
They are affected by standard scaling, one-hot encoding, category frequency,
and correlations among region, market, product, and shipping fields. They do
not support causal claims. The dominance of geographic dummies is a useful
review signal for future model interpretation, but individual coefficients
should not be over-interpreted.

## Target-Policy Confirmation

The runtime metadata confirms:

- `Order_Profit_Per_Order` was used as the target only.
- `Benefit_per_order`, `Order_Item_Profit_Ratio`, `Order_Item_Total`, `Sales`,
  `Sales_per_customer`, `Order_Item_Discount`, `Product_Price`, and other
  target/proxy or post-shipment fields were excluded from predictors.
- `ao3_order_value` was excluded from AO2 predictors.
- preprocessing was fit only on `development_inner_train`.
- validation rows were transformed with the training-fitted preprocessing
  object.
- the final `test` partition was not used for training, preprocessing fit,
  validation metrics, residual diagnostics, model selection, or predictions.

## Validation Status

After Databricks artifact generation,
`tests/data_validation/validate_ao2_ridge_baseline.py` passed. The script
confirmed required artifacts, metric fields, residual diagnostics, prediction
row counts, Ridge parameters, target-policy exclusions, and final-test non-use.

## Assumptions and Limitations

- AO2 Gold and AO2 chronological partitions already enforce the approved
  leakage-safe feature policy.
- The raw target remains `Order_Profit_Per_Order`; no log transform is applied
  because profit can be zero or negative.
- Validation is chronological and internal to development only.
- The final test set remains untouched for future final AO2 evaluation.
- No large fitted binary model artifact is committed. If a fitted model is
  saved, it should be written to a Databricks Volume and referenced in metadata.

## Run Order

In Databricks, run:

```text
src/modeling/train_ao2_ridge_baseline.py
tests/data_validation/validate_ao2_ridge_baseline.py
```

The project orchestrator exposes disabled-by-default flags:

```python
RUN_AO2_RIDGE_BASELINE = False
RUN_AO2_RIDGE_BASELINE_VALIDATION = False
```

## Next Step

The next AO2 modeling issue should train the gradient boosting regressor and
compare it against this Ridge validation baseline for H2. The comparison should
remain validation-only until the final AO2 model is selected.
