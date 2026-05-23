# AO1 Logistic Regression Validation Findings

Issue: `#27`

## Purpose

This report-facing note summarizes the validation results from the AO1 Logistic
Regression baseline. The methodology and run instructions remain in
`docs/ao1_logistic_regression_baseline.md`.

## Run Context

| Item | Value |
| --- | --- |
| Generated timestamp | `2026-05-22T22:08:07.143080+00:00` |
| Input partition path | `/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_chronological_partitions` |
| Partition structure | `development` / `test` |
| Development rows | `138,212` |
| Final test rows | `34,553` |
| Training slice | `development_inner_train` |
| Training rows | `110,569` |
| Training date range | `2015-01-01T00:00:00` to `2016-11-05T05:42:00` |
| Validation slice | `development_inner_validation` |
| Validation rows | `27,643` |
| Validation date range | `2016-11-05T05:42:00` to `2017-04-22T03:43:00` |
| Final test use | Not used |
| Feature count before preprocessing | `29` |
| Feature count after preprocessing | `1,290` |

The validation split was chronological inside the development partition. The
final test partition remained untouched and is reserved for final AO1 model
evaluation.

## Model Configuration

The baseline used the approved AO1 preprocessing factory and:

```text
LogisticRegression(
    solver="lbfgs",
    max_iter=1000,
    penalty="l2",
    class_weight="balanced",
    random_state=620
)
```

SMOTE was not used. Class distributions before and after resampling are
therefore identical.

## Validation Metrics

| Metric | Value |
| --- | ---: |
| ROC-AUC | `0.7426` |
| PR-AUC | `0.8307` |
| Accuracy | `0.6856` |
| Precision at 0.5 | `0.8296` |
| Recall at 0.5 | `0.5645` |
| F1 at 0.5 | `0.6718` |
| Log loss | `0.5723` |
| Validation positive class rate | `0.5702` |
| Predicted positive rate at 0.5 | `0.3880` |

Confusion matrix at the default `0.5` threshold:

| Actual / Predicted | Predicted non-late | Predicted late |
| --- | ---: | ---: |
| Actual non-late | `10,054` | `1,828` |
| Actual late | `6,864` | `8,897` |

## Interpretation

The baseline shows moderate discrimination. ROC-AUC of `0.7426` indicates the
model ranks late-delivery cases meaningfully better than chance, and PR-AUC of
`0.8307` is strong relative to the validation positive rate of `0.5702`.

At the default `0.5` threshold, the classifier is conservative in assigning the
late-delivery class. Precision is high at `0.8296`, but recall is only `0.5645`.
This means the baseline avoids many false alarms, but misses `6,864` late
orders in validation. For the AO1 use case, where missing high-risk orders is
operationally costly, this recall level should be treated as a benchmark rather
than a final operating policy.

No threshold tuning was performed in this issue. Any future threshold choice
should be selected on validation data only and must still leave the final test
partition untouched until final evaluation.

## Coefficient Notes

The coefficient artifact contains `1,290` preprocessed features:

```text
report/tables/ao1_logistic_regression_coefficients.csv
```

Largest positive coefficients included:

| Feature | Coefficient | Odds ratio |
| --- | ---: | ---: |
| `categorical__shipping_mode_normalized_first_class` | `4.7335` | `113.6943` |
| `categorical__order_state_normalized_lugansk` | `1.8366` | `6.2751` |
| `categorical__order_state_normalized_corrientes` | `1.8210` | `6.1780` |
| `categorical__order_state_normalized_bihor` | `1.8208` | `6.1769` |
| `categorical__order_state_normalized_bushehr` | `1.7815` | `5.9385` |

Largest negative coefficients included:

| Feature | Coefficient | Odds ratio |
| --- | ---: | ---: |
| `categorical__shipping_mode_normalized_same_day` | `-3.5651` | `0.0283` |
| `categorical__order_state_normalized_marche` | `-2.2774` | `0.1025` |
| `categorical__order_state_normalized_ancash` | `-2.1056` | `0.1218` |
| `categorical__order_state_normalized_ningxia_hui` | `-1.8596` | `0.1557` |
| `categorical__order_state_normalized_al_jawf` | `-1.8011` | `0.1651` |

Among numeric and binary features, the largest absolute coefficients were:

| Feature | Coefficient | Odds ratio |
| --- | ---: | ---: |
| `binary_flags__is_same_day_or_next_day_shipping` | `1.1685` | `3.2170` |
| `binary_flags__is_standard_shipping` | `-0.8543` | `0.4256` |
| `numeric_continuous__scheduled_shipping_days` | `0.3577` | `1.4301` |
| `binary_flags__geo_coordinates_available` | `0.2113` | `1.2353` |
| `binary_flags__customer_zipcode_available` | `0.2113` | `1.2353` |

Coefficient interpretation must be cautious. Numeric predictors are scaled,
categorical predictors are one-hot encoded, and several large coefficients come
from granular `order_state_normalized` categories that may be sparse or
correlated with other geography and shipping features. These coefficients are
associative model signals, not causal effects.

## Implications for H1

This Logistic Regression result is a defensible baseline for H1. It is
interpretable and reproducible, but its default-threshold recall leaves room for
an XGBoost classifier to improve operational usefulness if it can raise recall
and maintain or improve ROC-AUC without leakage.

The next AO1 model comparison should use the same validation design and should
compare at least:

- ROC-AUC;
- PR-AUC;
- recall at the documented threshold policy;
- precision and false-positive tradeoff;
- confusion matrix;
- post-model leakage review of top signals.

## Artifact References

| Artifact | Path |
| --- | --- |
| Metrics JSON | `models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_metrics.json` |
| Metadata JSON | `models/ao1_late_delivery/logistic_regression/ao1_logistic_regression_metadata.json` |
| Metrics CSV | `report/tables/ao1_logistic_regression_validation_metrics.csv` |
| Coefficients CSV | `report/tables/ao1_logistic_regression_coefficients.csv` |

No fitted model artifact was saved in the repository.
