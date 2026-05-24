# AO1 Model Evaluation Pack

Issue: `#29`

## Purpose

The AO1 evaluation pack compares late-delivery candidate models on the
validation slice using consistent metrics, curve artifacts, confusion matrices,
and threshold trade-off tables. It supports the next decision task: choosing an
operational AO1 threshold for pre-dispatch prioritization.

This task does not choose the final threshold. The final threshold is governed
by the separate threshold-selection task and must use this evaluation evidence.

## Evaluation Boundary

The evaluation pack uses validation predictions only. The final test partition
must remain untouched until final model evaluation is explicitly approved.

Required boundary rules:

- fit preprocessing on training data only;
- train candidate models on the approved training slice only;
- score validation for model comparison and threshold trade-off analysis;
- reserve test for final reporting;
- do not tune, calibrate, or select thresholds on test.

## Prediction Artifact Contract

Each AO1 candidate model must write row-level validation predictions with at
least these columns:

```text
model_name
Late_delivery_risk
predicted_probability
```

Recommended columns:

```text
evaluation_slice
Order_Id
Order_Item_Id
order_date_DateOrders
chronological_row_number
split_partition
prediction_threshold
predicted_label
```

The Logistic Regression baseline writes:

```text
report/tables/ao1_logistic_regression_validation_predictions.csv
```

The primary XGBoost classifier should write:

```text
report/tables/ao1_xgboost_validation_predictions.csv
```

## Evaluation Script

Implementation:

```text
src/modeling/evaluate_ao1_models.py
```

The script reads any available candidate prediction artifacts and writes:

```text
report/tables/ao1_model_validation_comparison.csv
report/tables/ao1_threshold_tradeoff_grid.csv
report/tables/ao1_confusion_matrix_by_threshold.csv
report/tables/ao1_roc_curve_points.csv
report/tables/ao1_precision_recall_curve_points.csv
report/tables/ao1_calibration_by_probability_bin.csv
report/tables/ao1_model_evaluation_findings.md
models/ao1_late_delivery/evaluation/ao1_evaluation_metadata.json
```

## Metrics

The model comparison table reports:

- ROC-AUC;
- PR-AUC;
- log loss;
- accuracy at threshold `0.50`;
- precision at threshold `0.50`;
- recall at threshold `0.50`;
- F1 at threshold `0.50`;
- confusion matrix values at threshold `0.50`.

The threshold grid reports the same threshold-dependent metrics for:

```text
0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70
```

## Operational Interpretation

AO1 supports pre-dispatch prioritization. Recall deserves explicit attention
because a missed high-risk order reduces operational value. Precision still
matters because a threshold that flags too many orders is difficult to action.

The threshold grid therefore gives reviewers a managerial trade-off table:

- lower thresholds usually increase recall but increase false positives;
- higher thresholds usually improve precision but increase false negatives;
- the selected threshold should keep the alert volume operationally plausible.

## Calibration Review

The calibration table groups validation predictions into fixed probability
bins. This is a directional check only. If probabilities are poorly calibrated,
the team may still use the model for ranking but should be cautious when
communicating probability values as literal risk estimates.

## Validation

After running the evaluation script, validate the generated artifacts:

```text
tests/data_validation/validate_ao1_evaluation_pack.py
```

The validation script checks that:

- metadata marks the final test set as unused;
- model names are consistent across outputs;
- metrics and threshold values are within valid ranges;
- confusion-matrix counts are non-negative;
- curve, threshold, calibration, and findings artifacts exist.

## Dependencies

This pack can run once at least one candidate model has written validation
predictions. It becomes the complete AO1 comparison pack when both the Logistic
Regression baseline and the primary XGBoost classifier publish prediction
artifacts using the shared contract.
