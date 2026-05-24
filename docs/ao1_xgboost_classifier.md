# AO1 XGBoost Classifier

Issue: `#28`

## Purpose and Scope

The AO1 XGBoost classifier is the primary model candidate for late-delivery
risk prediction. It is designed to test H1 against the Logistic Regression
baseline while preserving the same leakage-safe AO1 Gold, chronological
partition, and preprocessing contracts.

This issue trains and validates only the AO1 XGBoost classifier. It does not
evaluate the final test partition, choose a final operating threshold, change
AO1 Gold, change AO1 partitions, change preprocessing rules, score AO3, or
build dashboard outputs.

## Input Partition Table

The training script consumes the AO1 chronological partition output:

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

Because no materialized validation partition exists, this model creates an
internal chronological validation slice inside `development` only:

```text
ordering = order_date_DateOrders ASC, Order_Id ASC, Order_Item_Id ASC
inner training = first 80% of development rows
validation = final 20% of development rows
```

The final `test` partition is reserved for final AO1 evaluation and is not used
for preprocessing fit, model training, validation metrics, model selection,
threshold selection, or hyperparameter selection in this issue.

If a future partition artifact contains explicit `train`, `validation`, and
`test` labels, the script trains on `train` and evaluates on `validation`.

## Preprocessing

The XGBoost script uses the approved issue `#26` preprocessing factory:

```text
src.modeling.build_ao1_preprocessing_pipeline.build_sklearn_preprocessor
```

Preprocessing is fit inside the model pipeline on the training slice only. The
fitted preprocessing object then transforms validation without refitting.

The target, identifiers, date anchor, row number, partition label, lineage
columns, and forbidden leakage fields are excluded from predictors.

## Class Imbalance

SMOTE is not used for this XGBoost model.

Rationale:

- issue `#26` marks SMOTE as deferred;
- the AO1 class imbalance analysis describes mild imbalance;
- this issue keeps candidate comparison disciplined and reproducible.

The XGBoost candidates use `scale_pos_weight` calculated from the training
slice only. No resampling is applied to validation or test data.

## Model Configuration

Implementation:

```text
src/modeling/train_ao1_xgboost_classifier.py
```

Estimator:

```text
xgboost.XGBClassifier
```

The script compares a small validation-only candidate set:

- `balanced_reference`
- `shallower_regularized`
- `deeper_conservative`

Selection uses:

```text
primary metric = roc_auc
secondary metric = recall
```

The default validation threshold is `0.5`. Threshold tuning is not performed in
this issue.

## Validation Metrics

The training script writes validation-only metrics to:

```text
models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_metrics.json
report/tables/ao1_xgboost_classifier_validation_metrics.csv
report/tables/ao1_xgboost_validation_predictions.csv
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
come from generated metrics artifacts after the Databricks training run.

## Feature Importance Output

The feature-importance table is written to:

```text
report/tables/ao1_xgboost_classifier_feature_importance.csv
```

Columns:

- `feature_name`
- `importance_gain_proxy`
- `importance_share`

Interpretation cautions:

- importances are based on the preprocessed feature space;
- categorical features are one-hot encoded;
- importances are associative and not causal;
- correlated predictors can split importance across related columns.

## Validation Prediction Output

The selected XGBoost candidate writes row-level validation predictions to:

```text
report/tables/ao1_xgboost_validation_predictions.csv
```

Columns:

- `model_name`
- `evaluation_slice`
- `Order_Id`
- `Order_Item_Id`
- `order_date_DateOrders`
- `chronological_row_number`
- `split_partition`
- `Late_delivery_risk`
- `predicted_probability`
- `prediction_threshold`
- `predicted_label`

This file is required by the AO1 evaluation pack and threshold-selection
workflow so Logistic Regression and XGBoost can be compared using a shared
validation-prediction contract.

## Artifacts

Training outputs:

```text
models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_metrics.json
models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_metadata.json
report/tables/ao1_xgboost_classifier_validation_metrics.csv
report/tables/ao1_xgboost_classifier_candidate_results.csv
report/tables/ao1_xgboost_classifier_feature_importance.csv
report/tables/ao1_xgboost_validation_predictions.csv
```

Optional fitted model artifact:

```text
/Volumes/workspace/default/raw_data/models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_pipeline.joblib
```

The fitted binary artifact is not saved by default. To save it to a Databricks
Volume, set:

```text
DATACO_AO1_SAVE_XGBOOST_MODEL=true
```

## Validation Script

After training, run:

```text
tests/data_validation/validate_ao1_xgboost_classifier.py
```

The validation script checks:

- metrics and metadata JSON files exist;
- required metrics are present and numeric;
- metric ranges are valid;
- final test is marked as not used;
- training and validation slices are not final test;
- target is not listed as a feature;
- forbidden leakage fields are not predictors;
- preprocessing fit scope is training-slice only;
- SMOTE is not used;
- exactly one XGBoost candidate is selected;
- selected parameters are documented;
- report-facing metrics, candidate-comparison, feature-importance, and validation-prediction CSV files exist.

## Assumptions and Limitations

- The AO1 chronological partition table already exists in Databricks.
- The current partition structure is `development` and `test`.
- The internal validation rule is a deterministic chronological split inside
  `development`.
- The final test partition remains untouched for final AO1 model evaluation.
- Candidate comparison is intentionally small to avoid over-tuning.
- No final decision threshold is selected in this issue.

## Review Checkpoint

Before final AO1 evaluation is locked, reviewers should inspect:

- selected candidate configuration;
- validation metrics compared with the Logistic Regression baseline;
- feature-importance output for leakage or unexpected dominant signals;
- confirmation that final test remains unused.
