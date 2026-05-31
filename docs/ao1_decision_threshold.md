# AO1 Decision Threshold Policy

Issue: `#67`

## Purpose

The AO1 decision threshold converts a late-delivery predicted probability into
an operational high-risk flag. This policy is reused by AO3 segmentation and
dashboard logic so that the project applies one consistent definition of AO1
risk.

## Scope

This task selects the operating threshold from validation evidence only. The
final test partition must not be used for threshold selection.

The threshold decision depends on the AO1 evaluation pack from issue `#29`,
which compares candidate model validation predictions and writes the threshold
trade-off grid.

## Input Artifacts

Required inputs:

```text
report/tables/ao1_model_validation_comparison.csv
report/tables/ao1_threshold_tradeoff_grid.csv
models/ao1_late_delivery/evaluation/ao1_evaluation_metadata.json
```

The primary AO1 model from issue `#28` should publish validation predictions
before the threshold is frozen for AO3 and dashboard reuse. The current policy
artifact uses the primary XGBoost validation predictions and remains an
operational threshold recommendation, not model-selection logic.

## Threshold Selection Rule

Implementation:

```text
src/modeling/select_ao1_decision_threshold.py
```

Default operational targets:

```text
minimum_recall = 0.70
maximum_alert_rate = 0.65
preferred_model_name = ao1_xgboost_classifier
```

Selection logic:

1. Use the primary AO1 XGBoost validation rows from the evaluation pack.
2. If the primary model rows are unavailable in a future partial rerun, rerun
   the AO1 evaluation pack before freezing the AO3/dashboard threshold.
3. Select the threshold with the highest recall among rows that satisfy both:
   `recall >= minimum_recall` and
   `predicted_positive_rate <= maximum_alert_rate`.
4. If no threshold satisfies both constraints, select the highest-recall
   threshold under the alert-rate cap.
5. If no threshold satisfies the alert-rate cap, select the best F1 threshold
   and mark the result for review.

## Rationale

AO1 is used for pre-dispatch prioritization. Missed high-risk orders are costly
because the operations team loses the chance to intervene before shipment.
Recall is therefore prioritized over accuracy alone.

Precision and predicted positive rate remain important because a threshold that
flags too many orders creates an alert queue that may not be operationally
manageable.

## Output Artifacts

The threshold selector writes:

```text
data/references/ao1_decision_threshold_policy.csv
models/ao1_late_delivery/threshold/ao1_decision_threshold_metadata.json
report/tables/ao1_decision_threshold_recommendation.md
```

The policy CSV contains the selected threshold, validation trade-off metrics,
decision status, and the reusable AO3/dashboard rule:

```text
predicted_probability >= selected_threshold
```

## Decision Status Values

`ready_for_team_review`

Used when the primary AO1 model is available and the threshold selector has
generated a recommendation from the current validation trade-off grid.

`final_approved`

Reserved for the team-approved threshold after review. This status should only
be used after the team agrees that the threshold is ready for AO3 and dashboard
reuse.

## Validation

After running the threshold selector, validate the policy artifacts:

```text
tests/data_validation/validate_ao1_decision_threshold_policy.py
```

The validation checks:

- exactly one policy row exists;
- threshold and metric values are valid;
- final test is marked as unused;
- metadata matches the CSV policy;
- the AO3/dashboard reuse rule is present.

## Current Project Status

The current threshold artifact is `ready_for_team_review` and is based on the
primary XGBoost validation predictions in the AO1 evaluation pack. The threshold
supports AO3 and dashboard operational policy; it does not change AO1 model
selection and must not use the final test partition.
