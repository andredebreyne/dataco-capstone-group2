# AO2 Gradient Boosting Regressor

Issue: `#36`

## Purpose and Scope

This model is the primary nonlinear AO2 profitability model for H2. It trains
an XGBoost Gradient Boosting regressor to estimate order-level profitability
from the same leakage-safe AO2 predictors and validation discipline used by
the AO2 Ridge baseline.

This issue does not evaluate the final test partition, derive AO3 predicted
margin, assign AO3 risk-margin groups, rebuild AO2 Gold, rebuild AO2
chronological partitions, change AO2 preprocessing logic, run SHAP, or perform
broad hyperparameter tuning.

## Source Artifact

| Artifact | Path |
| --- | --- |
| AO2 partition Delta table | `/Volumes/workspace/default/raw_data/gold/ao2_profitability_chronological_partitions` |
| Training script | `src/modeling/train_ao2_gradient_boosting_regressor.py` |
| Validation script | `tests/data_validation/validate_ao2_gradient_boosting_regressor.py` |
| Metadata JSON | `models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metadata.json` |
| Metrics JSON | `models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metrics.json` |
| Validation metrics CSV | `report/tables/ao2_gradient_boosting_validation_metrics.csv` |
| Residual diagnostics CSV | `report/tables/ao2_gradient_boosting_residual_diagnostics.csv` |
| Validation predictions CSV | `report/tables/ao2_gradient_boosting_validation_predictions.csv` |
| Ridge comparison CSV | `report/tables/ao2_model_validation_comparison.csv` |
| Feature importance CSV | `report/tables/ao2_gradient_boosting_feature_importance.csv` |

The input path can be overridden with:

```text
DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH
```

## Training and Validation Split

The Databricks run used the AO2 chronological partition Delta table at:

```text
/Volumes/workspace/default/raw_data/gold/ao2_profitability_chronological_partitions
```

The observed partition labels were `development` and `test`, so the Gradient
Boosting model followed the same inner chronological validation rule used by
the Ridge baseline:

```text
ordering = order_date_DateOrders ASC, Order_Id ASC, Order_Item_Id ASC
development_inner_train = first 80% of development rows
development_inner_validation = final 20% of development rows
```

Runtime split counts:

| Slice | Rows | Date range |
| --- | ---: | --- |
| `development_inner_train` | 115,532 | 2015-01-01 00:00:00 to 2016-11-05 14:28:00 |
| `development_inner_validation` | 28,883 | 2016-11-05 14:49:00 to 2017-04-22 15:17:00 |
| final `test` partition | 36,104 | reserved, not used in this issue |

The final `test` partition is not used for training, preprocessing fit,
validation metrics, residual diagnostics, model selection, comparison, feature
importance review, or prediction export in this issue.

If future partitions contain explicit `train`, `validation`, and `test`
labels, the script trains on `train`, evaluates on `validation`, and still
leaves `test` unused.

## Target and Predictors

Target:

```text
Order_Profit_Per_Order
```

The model uses the approved AO2 preprocessing factory:

```text
src.modeling.build_ao2_preprocessing_pipeline.build_sklearn_preprocessor
```

Preprocessing is fit only on the training slice. Validation rows are
transformed using the fitted preprocessing object without refitting. The final
test partition is not transformed or scored by this model job.

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

## Model Library and Candidate Configurations

The Databricks run used:

```text
xgboost.XGBRegressor
xgboost version = 2.0.3
```

The model accepts the sparse output from the existing sklearn
`ColumnTransformer`; no dense conversion is introduced.

The tested candidate set was intentionally small:

| Candidate | Selected | n_estimators | max_depth | learning_rate | subsample | colsample_bytree | validation RMSE | validation MAE |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `conservative_baseline` | yes | 200 | 3 | 0.05 | 0.8 | 0.8 | 95.6203 | 52.6463 |
| `slightly_deeper` | no | 250 | 4 | 0.05 | 0.8 | 0.8 | 95.8084 | 52.8191 |
| `faster_learning` | no | 150 | 3 | 0.10 | 0.8 | 0.8 | 95.8639 | 52.9343 |

Common settings:

```text
objective = reg:squarederror
eval_metric = rmse
tree_method = hist
random_state = 42
```

The selected candidate was `conservative_baseline`, chosen using validation
RMSE as the primary metric and validation MAE as the secondary metric. Final
selected parameters:

```text
n_estimators = 200
max_depth = 3
learning_rate = 0.05
subsample = 0.8
colsample_bytree = 0.8
objective = reg:squarederror
eval_metric = rmse
tree_method = hist
random_state = 42
```

The final test partition was not used for selection.

## Validation Results

These are validation-only results for `development_inner_validation`. They are
not final test metrics.

| Metric | Value |
| --- | ---: |
| Validation rows | 28,883 |
| RMSE | 95.6203 |
| MAE | 52.6463 |
| R2 | 0.0118 |
| Median absolute error | 31.3954 |
| Mean error / bias | 0.9627 |
| Target mean | 21.7130 |
| Target standard deviation | 96.1905 |
| Prediction mean | 20.7502 |
| Prediction standard deviation | 11.9159 |
| Absolute error p50 | 31.3954 |
| Absolute error p90 | 110.3725 |

MAPE is not used because AO2 profitability can be zero or negative.

The model improves over Ridge on RMSE, MAE, median absolute error, R2, and
wrong profit-sign share. However, prediction standard deviation is still much
smaller than the target standard deviation, so predictions remain compressed
toward the mean. This is a meaningful limitation for high-variance profit and
loss-making orders.

## Residual Diagnostics

Residuals are defined as:

```text
actual Order_Profit_Per_Order - predicted_profit
```

| Diagnostic | Value |
| --- | ---: |
| Residual mean | 0.9627 |
| Residual median | 15.3847 |
| Residual standard deviation | 95.6171 |
| Residual minimum | -1122.6160 |
| Residual maximum | 221.7182 |
| Residual p10 | -70.2391 |
| Residual p25 | -7.4009 |
| Residual p50 | 15.3847 |
| Residual p75 | 42.4727 |
| Residual p90 | 72.1999 |
| Absolute error median | 31.3954 |
| Absolute error p90 | 110.3725 |
| Wrong profit-sign share | 0.1974 |

The positive residual mean indicates slight average underprediction: actual
profit is about 0.96 higher than predicted on average. The positive residual
median indicates more typical underprediction of about 15.38. The extreme
negative residual minimum shows that very large overpredictions still occur on
some loss-making or low-profit orders, so the model should not be interpreted
as fully handling extreme profitability outcomes.

Compared with Ridge, Gradient Boosting lowers residual spread slightly and
reduces the wrong profit-sign share from 25.36% to 19.74%. The selected model
therefore captures more structure than the linear baseline, but the prediction
spread remains narrow relative to the target.

## Ridge Baseline Comparison

The script reads:

```text
report/tables/ao2_ridge_validation_metrics.csv
```

and wrote:

```text
report/tables/ao2_model_validation_comparison.csv
```

The comparison is validation-only:

| Model | RMSE | MAE | R2 | Median absolute error | Mean error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gradient Boosting Regressor | 95.6203 | 52.6463 | 0.0118 | 31.3954 | 0.9627 |
| Ridge baseline | 96.8276 | 54.2191 | -0.0133 | 32.5591 | 0.6453 |

Gradient Boosting improves validation RMSE by 1.2073 and validation MAE by
1.5729 relative to Ridge. It also moves validation R2 from slightly negative
to slightly positive and reduces median absolute error.

Validation evidence is consistent with H2 because the Gradient Boosting
Regressor improves over the Ridge baseline on the primary AO2 metrics, RMSE
and MAE. This is not final H2 confirmation because final test evaluation is
deferred to a later AO2 evaluation/reporting issue.

Final H2 confirmation is deferred until the later AO2 evaluation/reporting
issue that uses the held-out test partition.

If Ridge metrics are missing, the Gradient Boosting artifacts are still valid,
but metadata marks the comparison incomplete.

## Feature Importance

The feature-importance artifact is intentionally simple and model-specific:

```text
report/tables/ao2_gradient_boosting_feature_importance.csv
```

It contains preprocessed feature names, normalized XGBoost gain importance,
and ranks. These importances are associative, not causal. One-hot encoded
categorical levels may appear as granular individual features.

The top validation-model importances were:

| Rank | Feature | Importance |
| ---: | --- | ---: |
| 1 | `categorical__shipping_speed_tier_standard` | 0.0170 |
| 2 | `categorical__order_state_normalized_cork` | 0.0162 |
| 3 | `categorical__product_category_key_45_fishing` | 0.0159 |
| 4 | `numeric_continuous__item_unit_price` | 0.0151 |
| 5 | `categorical__order_state_normalized_copperbelt` | 0.0145 |
| 6 | `numeric_continuous__order_item_quantity` | 0.0140 |
| 7 | `categorical__order_state_normalized_veracruz` | 0.0138 |
| 8 | `categorical__order_state_normalized_baha` | 0.0136 |
| 9 | `categorical__shipping_mode_normalized_second_class` | 0.0125 |
| 10 | `categorical__customer_state_normalized_md` | 0.0124 |

These drivers are plausible for profitability prediction because planned
shipping service, product category, item price, quantity, and order geography
can all be associated with commercial mix, service cost, or regional demand
patterns. The dominance of one-hot encoded geography levels should be treated
carefully because individual levels may be sparse and model-specific.

A scan of the feature-importance artifact found no forbidden target or proxy
fields such as `Order_Profit_Per_Order`, `Benefit_per_order`,
`Order_Item_Profit_Ratio`, `Order_Item_Total`, `Sales`, `Sales_per_customer`,
`Product_Price`, delivery outcome fields, or `ao3_order_value`.

SHAP is out of scope for this issue.

## Target-Policy and Leakage Safeguards

The runtime metadata confirms:

- `Order_Profit_Per_Order` was used as the target only.
- `Benefit_per_order`, `Order_Item_Profit_Ratio`, `Order_Item_Total`, `Sales`,
  `Sales_per_customer`, `Order_Item_Discount`, `Product_Price`, and other
  target/proxy or near-formula fields were excluded from predictors.
- `ao3_order_value` was excluded from AO2 predictors and remains reserved only
  for future AO3 predicted-margin construction.
- Delivery outcome and post-shipment fields were excluded.
- Identifier, date, partition, and lineage columns were excluded from the
  feature matrix.
- Preprocessing was fit only on `development_inner_train`.
- Validation was used only for candidate selection and validation evaluation.
- The final `test` partition was not used.

## Strengths and Weaknesses

Gradient Boosting improves over Ridge on the primary validation metrics and
reduces wrong profit-sign assignments. This suggests the nonlinear model is
capturing some structured profitability variation beyond the linear/additive
baseline.

The improvement is useful but modest. RMSE remains close to the validation
target standard deviation, residual spread remains high, and large errors
remain on extreme loss-making or high-profit orders. The model also relies on a
large one-hot encoded feature space, so category-level importances should be
reviewed cautiously and not treated as causal explanations.

## Validation Status

After Databricks artifact generation, the validation script passed:

```text
python tests/data_validation/validate_ao2_gradient_boosting_regressor.py
```

The validator checks required artifacts, metrics, residual diagnostics,
prediction row counts, candidate documentation, selected candidate metadata,
final-test non-use, and AO2 target-policy exclusions.

## Assumptions and Limitations

- AO2 Gold and AO2 chronological partitions already enforce the approved
  leakage-safe feature policy.
- The target remains raw `Order_Profit_Per_Order`; no log transform is applied.
- Validation is chronological and internal to development when only
  `development` and `test` labels exist.
- The final test set remains untouched for future final AO2 evaluation.
- The model excludes `ao3_order_value` and target-reconstruction fields from
  AO2 predictors.
- The candidate set is deliberately small and is not an exhaustive tuning run.
- No large fitted binary model artifact is committed. If a fitted model is
  saved, it should be written to a Databricks Volume and referenced in
  metadata.

## Run Order

In Databricks, run:

```text
src/modeling/train_ao2_gradient_boosting_regressor.py
tests/data_validation/validate_ao2_gradient_boosting_regressor.py
```

The project orchestrator exposes disabled-by-default flags:

```python
RUN_AO2_GRADIENT_BOOSTING_REGRESSOR = False
RUN_AO2_GRADIENT_BOOSTING_REGRESSOR_VALIDATION = False
```

## Next Step

Use the Ridge comparison table and Gradient Boosting validation artifacts in
the later AO2 evaluation/H2 reporting issue. Do not make final H2 claims until
final-test evaluation is explicitly run.
