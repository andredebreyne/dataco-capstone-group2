# AO1/AO2 Held-Out Test Scoring

Issue: `#41`

## Purpose

This document defines the reproducible scoring step that creates the integrated
AO1 and AO2 held-out test outputs required by AO3. The implementation lives in
`src/modeling/score_ao1_ao2_test_set.py`.

The job applies the frozen AO1 and AO2 modeling decisions to the held-out test
partitions. It produces predicted late-delivery risk and predicted order profit
in one Delta table for downstream AO3 segmentation.

## Methodological Boundary

The scoring job is intentionally limited to prediction generation:

- It trains the selected AO1 and AO2 configurations on the approved
  `development` partitions only.
- It applies those fitted pipelines to the `test` partitions for prediction.
- It uses the approved AO1 threshold policy from
  `data/references/ao1_decision_threshold_policy.csv`.
- It does not use final-test labels for fitting, model selection, threshold
  selection, or performance metrics.
- It does not assign AO3 risk-margin segments. Segment assignment belongs to a
  later AO3 materialization task.

This means the final test set is touched for prediction only, not for model
evaluation or policy tuning.

## Inputs

| Input | Default path | Purpose |
| --- | --- | --- |
| AO1 chronological partitions | `/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_chronological_partitions` | AO1 development and test rows. |
| AO2 chronological partitions | `/Volumes/workspace/default/raw_data/gold/ao2_profitability_chronological_partitions` | AO2 development and test rows. |
| AO1 XGBoost metadata | `models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_metadata.json` | Frozen selected AO1 candidate id. |
| AO2 Gradient Boosting metadata | `models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metadata.json` | Frozen selected AO2 candidate id. |
| AO1 threshold policy | `data/references/ao1_decision_threshold_policy.csv` | Approved AO1 high-risk threshold. |

## Output

The integrated Delta table is written to:

```text
/Volumes/workspace/default/raw_data/gold/ao1_ao2_test_scores
```

The job also writes lightweight review artifacts:

```text
models/ao3_integration/ao1_ao2_test_scores/ao1_ao2_test_score_metadata.json
data/references/ao1_ao2_test_score_summary.csv
```

## Output Contract

The score table contains:

| Column | Description |
| --- | --- |
| `Order_Id` | Order identifier. |
| `Order_Item_Id` | Order-item identifier. |
| `order_date_DateOrders` | Chronological join and audit field. |
| `chronological_row_number` | AO1 chronological row number. |
| `split_partition` | AO1 split label; expected value is `test`. |
| `ao2_chronological_row_number` | AO2 chronological row number. |
| `ao2_split_partition` | AO2 split label; expected value is `test`. |
| `ao1_model_name` | AO1 model identifier. |
| `ao1_selected_candidate` | Selected AO1 XGBoost candidate. |
| `ao1_predicted_late_delivery_probability` | AO1 predicted late-delivery risk. |
| `ao1_decision_threshold` | Approved AO1 threshold, currently `0.35`. |
| `ao1_high_risk_flag` | Boolean threshold flag for AO3 reuse. |
| `ao2_model_name` | AO2 model identifier. |
| `ao2_selected_candidate` | Selected AO2 Gradient Boosting candidate. |
| `ao2_predicted_order_profit` | AO2 predicted order-level profit. |
| `ao3_order_value` | AO3 support denominator from the AO2 Gold table. |
| `ao3_predicted_margin` | Predicted profit divided by `ao3_order_value`. |
| `scoring_timestamp_utc` | Runtime timestamp for auditability. |

Actual target columns such as `Late_delivery_risk` and
`Order_Profit_Per_Order` are intentionally excluded from the scored output.

## Validation

Run the scoring job in Databricks after AO1/AO2 partitions and model metadata
exist:

```text
src/modeling/score_ao1_ao2_test_set.py
```

Then run:

```text
tests/data_validation/validate_ao1_ao2_test_scores.py
```

The validation checks that the score table exists, contains required columns,
uses only `test` partitions, has valid AO1 probabilities, uses threshold
`0.35`, contains no final-test target labels, and matches the generated
metadata row count.

## Limitations

- The job refits selected model configurations on the full development
  partitions because persisted fitted model artifacts are not committed to the
  repository.
- The final-test labels remain outside the scored output and should be reserved
  for the later final evaluation workflow.
- The integrated AO3 scoring population is anchored on AO1 test rows and
  requires matching AO2 predictions for the same order keys.
