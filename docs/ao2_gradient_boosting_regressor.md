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

The current AO2 partition artifact contains `development` and `test` labels.
The Gradient Boosting model therefore follows the Ridge baseline split rule:

```text
ordering = order_date_DateOrders ASC, Order_Id ASC, Order_Item_Id ASC
development_inner_train = first 80% of development rows
development_inner_validation = final 20% of development rows
```

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

The project already includes `xgboost==2.0.3`, so this issue uses:

```text
xgboost.XGBRegressor
```

The model accepts the sparse output from the existing sklearn
`ColumnTransformer`; no dense conversion is introduced.

The default candidate set is intentionally small:

| Candidate | n_estimators | max_depth | learning_rate | subsample | colsample_bytree |
| --- | ---: | ---: | ---: | ---: | ---: |
| `conservative_baseline` | 200 | 3 | 0.05 | 0.8 | 0.8 |
| `slightly_deeper` | 250 | 4 | 0.05 | 0.8 | 0.8 |
| `faster_learning` | 150 | 3 | 0.10 | 0.8 | 0.8 |

Common settings:

```text
objective = reg:squarederror
eval_metric = rmse
tree_method = hist
random_state = 42
```

The candidate count can be reduced for Databricks Community Edition runtime by
setting:

```text
DATACO_AO2_GRADIENT_BOOSTING_MAX_CANDIDATES=2
```

Any reduction should be mentioned in PR notes and final reporting.

## Selection Metric

The selected model is chosen using validation RMSE as the primary metric and
validation MAE as the secondary tie-breaker.

The final test partition is not used for selection.

## Validation Outputs

For each candidate, the training script writes validation metrics:

- RMSE
- MAE
- R2
- median absolute error
- mean error / bias
- validation row count
- target mean and standard deviation
- prediction mean and standard deviation

For the selected candidate, the script also writes row-level validation
predictions and residual diagnostics, including residual percentiles and wrong
profit-sign share.

MAPE is not used because AO2 profitability can be zero or negative.

## Ridge Baseline Comparison

The script reads:

```text
report/tables/ao2_ridge_validation_metrics.csv
```

when available and writes:

```text
report/tables/ao2_model_validation_comparison.csv
```

The comparison is validation-only. If the Gradient Boosting model improves RMSE
and MAE relative to Ridge, the appropriate wording is:

```text
validation evidence is consistent with H2
```

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

SHAP is out of scope for this issue.

## Validation Status

Run in Databricks after training:

```text
src/modeling/train_ao2_gradient_boosting_regressor.py
tests/data_validation/validate_ao2_gradient_boosting_regressor.py
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

After Databricks runtime artifacts are generated and validated, use the Ridge
comparison table and Gradient Boosting validation artifacts in the later AO2
evaluation/H2 reporting issue. Do not make final H2 claims until final-test
evaluation is explicitly run.
