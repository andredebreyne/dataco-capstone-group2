# AO1 Model Evaluation Findings

Issue: `#29`

## Scope

This evaluation pack compares available AO1 candidate models on the validation slice only. It does not evaluate the final test partition, select the final operating threshold, or override the separate threshold-governance task.
The final test partition is not used in this evaluation pack.

## Candidate Model Summary

Comparison status: `complete`

Expected prediction artifacts:

- `logistic_regression`: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_logistic_regression_validation_predictions.csv`
- `xgboost`: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_xgboost_validation_predictions.csv`

Available prediction artifacts:

- `logistic_regression`: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_logistic_regression_validation_predictions.csv`
- `xgboost`: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_xgboost_validation_predictions.csv`

The H1 Logistic Regression versus XGBoost validation comparison is complete for the available issue #29 evaluation scope.

| Model | ROC-AUC | PR-AUC | Precision @ 0.50 | Recall @ 0.50 | F1 @ 0.50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ao1_xgboost_classifier | 0.7753 | 0.8489 | 0.8890 | 0.5840 | 0.7049 |
| ao1_logistic_regression_baseline | 0.7426 | 0.8307 | 0.8296 | 0.5645 | 0.6718 |

## Operating-Threshold Readiness

The strongest available validation ranking model is `ao1_xgboost_classifier`. The threshold grid should be reviewed by the team before freezing an AO1 operating threshold for AO3 and dashboard use.
This findings note supports recall, precision, and threshold trade-off review; it does not select the final operational threshold.

A recall-oriented candidate row for the current best model is:

| Model | Threshold | Precision | Recall | Predicted Positive Rate | False Negatives | False Positives |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ao1_xgboost_classifier | 0.30 | 0.5937 | 0.9802 | 0.9414 | 312 | 10574 |

## Calibration Observation

Calibration is summarized by fixed predicted-probability bins in `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_calibration_by_probability_bin.csv`. The table is intended as a directional check, not as a formal probability calibration model.

## Output Artifacts

- Metrics comparison: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_model_validation_comparison.csv`
- Threshold grid: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_threshold_tradeoff_grid.csv`
- Confusion matrices: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_confusion_matrix_by_threshold.csv`
- ROC curve points: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_roc_curve_points.csv`
- Precision-recall curve points: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_precision_recall_curve_points.csv`
- Calibration table: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao1_calibration_by_probability_bin.csv`
- Evaluation metadata: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/models/ao1_late_delivery/evaluation/ao1_evaluation_metadata.json`
