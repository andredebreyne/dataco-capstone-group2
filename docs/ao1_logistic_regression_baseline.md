# AO1 Logistic Regression Baseline

Issue: `#27`

## Purpose and Scope

The AO1 Logistic Regression baseline provides the interpretable benchmark for
late-delivery risk prediction. It anchors H1 by giving the future XGBoost model
a simple, reproducible validation comparator.

This issue trains only Logistic Regression. It does not train XGBoost, tune a
final operating threshold, evaluate the final test partition, change AO1 Gold,
change AO1 partitions, or change the approved preprocessing rules.

## Input Partition Table

The training script consumes the AO1 chronological partition output from issue
`#25`:

```text
/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_chronological_partitions
```

Override path:

```text
DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH
```

Required columns:

- `Order_Id`
- `Order_Item_Id`
- `order_date_DateOrders`
- `chronological_row_number`
- `split_partition`
- `Late_delivery_risk`
- all approved AO1 predictor columns from the preprocessing pipeline

The script validates that `Late_delivery_risk` is complete and binary before
training.

## Training and Validation Split

The current AO1 partition artifact is documented as:

- `development`
- `test`

Because no materialized validation partition exists, the baseline creates an
internal chronological validation slice inside `development` only:

```text
ordering = order_date_DateOrders ASC, Order_Id ASC, Order_Item_Id ASC
inner training = first 80% of development rows
validation = final 20% of development rows
```

The final `test` partition is reserved for final AO1 evaluation and is not used
for preprocessing fit, model training, validation metrics, threshold selection,
or model selection in this issue.

If a future partition artifact contains explicit `train`, `validation`, and
`test` labels, the script trains on `train` and evaluates on `validation`.

## Preprocessing

The baseline uses the approved issue `#26` preprocessing factory:

```text
src.modeling.build_ao1_preprocessing_pipeline.build_sklearn_preprocessor
```

Preprocessing is fit inside the model pipeline on the training slice only.
The fitted preprocessing object then transforms validation without refitting.

The target, identifiers, date anchor, row number, partition label, lineage
columns, and forbidden leakage fields are excluded from predictors.

## SMOTE and Class Imbalance

SMOTE is not used for this baseline.

Rationale:

- issue `#26` marks SMOTE as deferred;
- the AO1 class imbalance analysis describes mild imbalance;
- a single interpretable baseline specification is preferred here.

The baseline uses:

```text
class_weight="balanced"
```

No resampling is applied to validation or test data.

## Model Configuration

Implementation:

```text
src/modeling/train_ao1_logistic_regression_baseline.py
```

Baseline estimator:

```python
LogisticRegression(
    max_iter=1000,
    solver="lbfgs",
    class_weight="balanced",
    penalty="l2",
    random_state=620,
)
```

No grid search or hyperparameter tuning is performed. Classification metrics
use the default validation threshold of `0.5`.

## Validation Metrics

The training script writes validation-only metrics to:

```text
models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_metrics.json
report/tables/ao1_logistic_regression_validation_metrics.csv
report/tables/ao1_logistic_regression_validation_predictions.csv
report/tables/ao1_logistic_regression_validation_findings.md
```

Required metrics:

- ROC-AUC
- PR-AUC
- accuracy
- precision
- recall
- F1
- log loss
- confusion matrix
- validation positive class rate
- predicted positive rate at threshold `0.5`

Do not copy placeholder values into this document. Report-facing values should
come from the generated metrics artifacts after the Databricks training run.
Narrative result comments belong in
`report/tables/ao1_logistic_regression_validation_findings.md` so this document
remains the methodology and runbook reference.

## Interpretability Outputs

The coefficient table is written to:

```text
report/tables/ao1_logistic_regression_coefficients.csv
```

Columns:

- `feature_name`
- `coefficient`
- `absolute_coefficient`
- `odds_ratio`
- `direction`

Interpretation cautions:

- coefficients are based on the preprocessed feature space;
- numeric features are standardized;
- categorical values are one-hot encoded;
- coefficients are associative and not causal;
- correlated predictors can make individual coefficients unstable.

## Strengths

- Fast and reproducible.
- Interpretable baseline for H1.
- Uses the same approved preprocessing contract as later AO1 models.
- Useful benchmark for comparing against XGBoost.

## Weaknesses

- Assumes a linear relationship in log-odds.
- May miss nonlinear effects and feature interactions.
- Sensitive to correlated predictors.
- May underperform tree-based models such as XGBoost.

## Artifacts

Training outputs:

```text
models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_metrics.json
models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_metadata.json
report/tables/ao1_logistic_regression_validation_metrics.csv
report/tables/ao1_logistic_regression_coefficients.csv
report/tables/ao1_logistic_regression_validation_predictions.csv
report/tables/ao1_logistic_regression_validation_findings.md
```

Optional fitted model artifact:

```text
/Volumes/workspace/default/raw_data/models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_pipeline.joblib
```

The fitted binary artifact is not saved by default. To save it to a Databricks
Volume, set:

```text
DATACO_AO1_SAVE_LOGISTIC_MODEL=true
```

## Validation Script

After training, run:

```text
tests/data_validation/validate_ao1_logistic_regression_baseline.py
```

The validation script checks:

- metrics and metadata JSON files exist;
- required metrics are present and numeric;
- metric ranges are valid;
- final test is marked as not used;
- training and validation slices are not final test;
- target is not listed as a feature;
- forbidden leakage fields are not predictors;
- Logistic Regression parameters are documented;
- SMOTE is not used;
- report-facing metrics and coefficient CSV files exist.

## Assumptions and Limitations

- The AO1 chronological partition table already exists in Databricks.
- The current partition structure is `development` and `test`.
- The internal validation rule is a deterministic chronological split inside
  `development`.
- The final test partition remains untouched for final AO1 model evaluation.
- No final decision threshold is selected in this issue.
- No XGBoost comparison is performed in this issue.

## Next Step

The AO1 XGBoost classifier uses the same validation design and should be
compared against this Logistic Regression baseline for H1. See
`docs/ao1_xgboost_classifier.md`.
