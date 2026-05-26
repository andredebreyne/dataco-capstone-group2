# AO3 Segment Assignment

Issue: `#42`

## Purpose

This document defines the AO3 order-segmentation step. AO3 applies the approved
risk-margin matrix policy from Issue `#40` to the integrated AO1/AO2 held-out
score table from Issue `#41`.

This task materializes segment assignments only. It does not train AO1 or AO2
models, tune thresholds, calculate final-test performance metrics, or use actual
late-delivery or profit outcomes to assign segments.

## Dependencies

AO3 segment assignment depends on:

- Issue `#40`: `data/references/ao3_risk_margin_matrix_policy.csv`.
- Issue `#41`: `/Volumes/workspace/default/raw_data/gold/ao1_ao2_test_scores`.

The script is safe to implement before those upstream PRs are merged, but it
should only be executed after both upstream artifacts exist in the working branch
or Databricks workspace.

## Input Contract

The segmenter reads the integrated AO1/AO2 score table and expects at least:

| Column | Purpose |
| --- | --- |
| `Order_Id` | Join and dashboard traceability. |
| `Order_Item_Id` | Order-item uniqueness. |
| `order_date_DateOrders` | Chronological audit field. |
| `split_partition` | Expected AO1 split label; must be `test`. |
| `ao2_split_partition` | Expected AO2 split label; must be `test`. |
| `ao1_predicted_late_delivery_probability` | AO1 risk score. |
| `ao1_high_risk_flag` | AO1 threshold flag from Issue `#41`. |
| `ao1_decision_threshold` | Approved AO1 threshold, currently `0.35`. |
| `ao2_predicted_order_profit` | AO2 expected profit. |
| `ao3_order_value` | Positive order-value denominator. |
| `ao3_predicted_margin` | Predicted profit divided by order value. |

Actual target columns such as `Late_delivery_risk` and
`Order_Profit_Per_Order` must not be present in the scored input or AO3 output.

## Segment Rules

The segmenter reads the governed AO3 policy CSV and applies:

```text
high_risk = ao1_predicted_late_delivery_probability >= risk_cutoff
high_margin = ao3_predicted_margin >= margin_cutoff
```

The four operational segments are:

| Segment | Risk condition | Margin condition |
| --- | --- | --- |
| `protect_high_value_at_risk` | High risk | High margin |
| `expedite_selectively` | High risk | Low margin |
| `preserve_service` | Low risk | High margin |
| `standard_process` | Low risk | Low margin |

Fallback segments are reserved for incomplete scores:

| Segment | Condition |
| --- | --- |
| `requires_score_review` | AO1 probability or AO2 predicted profit is missing. |
| `requires_margin_review` | `ao3_order_value` or predicted margin is missing or invalid. |

## Output Contract

The segment table is written to:

```text
/Volumes/workspace/default/raw_data/gold/ao3_risk_margin_segments
```

The script also writes review artifacts:

```text
models/ao3_integration/risk_margin_segments/ao3_segment_assignment_metadata.json
data/references/ao3_segment_summary.csv
```

The AO3 segment table contains the upstream score fields plus:

| Column | Description |
| --- | --- |
| `ao3_policy_name` | Policy name from the AO3 policy CSV. |
| `ao3_risk_cutoff` | Risk cutoff applied. |
| `ao3_margin_cutoff` | Margin cutoff applied. |
| `ao3_high_risk_flag` | Recomputed AO3 high-risk flag. |
| `ao3_high_margin_flag` | AO3 high-margin flag. |
| `ao3_priority_segment` | Operational segment or fallback segment. |
| `ao3_segment_assignment_timestamp_utc` | Runtime timestamp for auditability. |

## Validation

Run the segmenter in Databricks after the Issue `#40` policy and Issue `#41`
score table exist:

```text
src/modeling/build_ao3_risk_margin_segments.py
```

Then run:

```text
tests/data_validation/validate_ao3_risk_margin_segments.py
```

The validation checks that the output table exists, required columns are present,
only test partitions are included, no final-test target labels are present, all
rows receive a valid AO3 segment, and summary counts match the output row count.

## Boundary

AO3 segment assignment is a decision-support materialization step. It does not
prove H3. Issue `#43` should benchmark the AO3 matrix against risk-only and
profit-only prioritization before H3 is reported as supported.
