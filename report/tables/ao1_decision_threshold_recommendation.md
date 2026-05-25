# AO1 Decision Threshold Recommendation

Issue: `#67`

## Decision Status

`ready_for_team_review`

The primary AO1 model is available and the recommendation is ready for team review.

## Recommended Operating Rule

Use threshold `0.35` for `ao1_xgboost_classifier`.

An order should be classified as AO1 high-risk when:

```text
predicted_probability >= selected_threshold
```

## Validation Trade-Off

| Metric | Value |
| --- | ---: |
| Precision | 0.8469 |
| Recall | 0.6171 |
| F1 | 0.7140 |
| Predicted positive rate | 0.4154 |
| False negatives | 6035 |
| False positives | 1758 |

## Rationale

AO1 supports pre-dispatch prioritization. The selected rule prioritizes recall because missed high-risk orders reduce operational value, while also applying an alert-rate cap so the resulting queue remains actionable.

## Reusable Policy Artifact

The reusable policy is stored at `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/data/references/ao1_decision_threshold_policy.csv`.
