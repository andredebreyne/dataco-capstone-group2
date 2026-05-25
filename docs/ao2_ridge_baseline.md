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

## Validation Outputs

The training script writes validation-only metrics:

- RMSE
- MAE
- R2
- median absolute error
- mean error / bias
- validation row count
- target mean and standard deviation
- prediction mean and standard deviation

Residual diagnostics include:

- residual mean, standard deviation, median, min, and max
- residual percentiles p10, p25, p50, p75, and p90
- absolute-error percentiles p10, p25, p50, p75, and p90
- share of predictions with the wrong profit sign

This local workspace does not contain the mounted Databricks Delta partition
path, so runtime metrics are not fabricated in this document. After running the
script in Databricks, use the JSON/CSV artifacts above as the source of truth.

## Interpretation Notes

The coefficient table saves the largest coefficients by absolute magnitude.
Coefficient interpretation has important caveats:

- coefficients are from scaled and one-hot encoded features;
- coefficient signs and magnitudes are associative, not causal;
- correlated predictors can make individual coefficients unstable;
- Ridge shrinks coefficients for stability;
- the baseline may underfit nonlinear profitability patterns.

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
