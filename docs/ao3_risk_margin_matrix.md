# AO3 Risk-Margin Matrix Logic

Issue: `#40`

## Purpose

This document defines the reusable AO3 2x2 risk-margin matrix logic for the
DataCo Capstone project. AO3 combines AO1 predicted late-delivery risk with AO2
predicted profitability to create operational priority groups for pre-dispatch
decision support.

This task defines the design only. It does not score the final test set,
materialize order-level AO3 segments, build dashboard pages, retrain AO1 or
AO2 models, change thresholds, or evaluate final test outcomes.

## Input Signals

AO3 uses frozen model outputs and support fields from prior work:

| Signal | Source | AO3 role |
| --- | --- | --- |
| `ao1_predicted_late_delivery_probability` | AO1 XGBoost classifier output | Risk score |
| `ao2_predicted_order_profit` | AO2 Gradient Boosting regressor output | Expected profit |
| `ao3_order_value` | AO2 Gold support field from `Order_Item_Total` | Margin denominator |

AO3 must use model predictions, not realized outcomes, when assigning priority
groups. It must not use `Late_delivery_risk`, `Delivery_Status`,
`Days_for_shipping_real`, `Order_Profit_Per_Order`, realized profit ratios, or
other target/outcome fields to define operational quadrants.

## Risk Cutoff

High AO1 risk is defined using the approved AO1 operating threshold:

```text
high_risk = ao1_predicted_late_delivery_probability >= 0.35
```

The threshold comes from `data/references/ao1_decision_threshold_policy.csv`.
The policy is validation-based, has `final_test_used = false`, and currently
uses:

| Policy item | Value |
| --- | --- |
| Model | `ao1_xgboost_classifier` |
| Selected threshold | `0.35` |
| Decision status | `ready_for_team_review` |
| Selection reason | `fallback_max_recall_under_alert_rate_cap` |

This threshold is reused by AO3 and dashboard logic. It must not be retuned
using final test data.

## Margin Signal

AO3 uses predicted margin rather than actual profit margin:

```text
ao3_predicted_margin = ao2_predicted_order_profit / ao3_order_value
```

`ao3_order_value` is the committed support denominator derived from
`Order_Item_Total`. It is excluded from AO2 predictors and reserved for AO3
support. If `ao3_order_value <= 0` or is missing in future data, the predicted
margin should be set to missing and the row should be flagged for review rather
than divided by zero or by a nonpositive value.

## Margin Cutoff

The first-pass AO3 design uses a break-even margin cutoff:

```text
high_margin = ao3_predicted_margin >= 0.00
```

Rationale:

- It is simple enough for managers to understand.
- It is reproducible across validation, test, dashboard, and future scoring.
- It avoids choosing a profitability percentile from final test outcomes.
- It aligns with the operational distinction between expected profit and
  expected loss.

The team may add sensitivity views later, such as percentile-based margin tiers,
but the official first-pass AO3 matrix should use the break-even cutoff unless
a later reviewed issue changes the policy.

## Quadrant Definitions

| AO3 segment | Risk condition | Margin condition | Managerial meaning | Default action theme |
| --- | --- | --- | --- | --- |
| `protect_high_value_at_risk` | High risk | High margin | Orders expected to be profitable but likely late. | Prioritize proactive delivery intervention. |
| `expedite_selectively` | High risk | Low margin | Orders likely late but low or negative expected margin. | Intervene selectively; avoid expensive blanket remediation. |
| `preserve_service` | Low risk | High margin | Profitable orders with lower delivery risk. | Maintain service quality and monitor. |
| `standard_process` | Low risk | Low margin | Lower risk and lower expected margin. | Use standard handling unless other business rules apply. |

## Fallback Rules

The later scoring task should apply these fallback rules:

1. If AO1 probability is missing, set the AO3 segment to
   `requires_score_review`.
2. If AO2 predicted profit is missing, set the AO3 segment to
   `requires_score_review`.
3. If `ao3_order_value` is missing, zero, or negative, set predicted margin to
   missing and segment to `requires_margin_review`.
4. If both risk and margin values are valid, assign exactly one of the four
   operational segments.
5. Do not fill missing predictions using actual targets or future outcomes.

## H3 Interpretation

H3 states that combining predicted late-delivery risk and expected order
profitability in a risk-margin framework will identify pre-dispatch priority
groups that are not evident from either signal alone.

The AO3 design supports H3 by creating four groups from two independent
prediction signals:

- AO1 identifies delivery-risk exposure.
- AO2 identifies expected economic value.
- AO3 combines both into operationally distinct actions.

Issue `#43` should later benchmark the combined matrix against risk-only and
profit-only prioritization. Issue `#42` should materialize segment assignments
using this policy. Issue `#41` should produce the AO1 and AO2 score inputs
needed by the segmenter.

## Leakage Controls

AO3 assignments must obey these controls:

- Use predicted AO1 risk, not actual `Late_delivery_risk`.
- Use predicted AO2 profit, not actual `Order_Profit_Per_Order`.
- Use `ao3_order_value` only as the predicted-margin denominator.
- Do not select risk or margin cutoffs from final test outcomes.
- Keep final test labels reserved for later final QA and evaluation.
- Preserve row-level identifiers and split metadata for auditability.

## Output Contract For Future Scoring

Future AO3 scoring should produce at least:

| Column | Description |
| --- | --- |
| `Order_Id` | Order identifier for joins and dashboard traceability. |
| `Order_Item_Id` | Order item identifier for uniqueness. |
| `split_partition` | Chronological split label. |
| `ao1_predicted_late_delivery_probability` | AO1 predicted risk score. |
| `ao1_high_risk_flag` | Boolean risk flag based on the 0.35 threshold. |
| `ao2_predicted_order_profit` | AO2 predicted order profit. |
| `ao3_order_value` | Positive order-value denominator. |
| `ao3_predicted_margin` | Predicted profit divided by order value. |
| `ao3_high_margin_flag` | Boolean margin flag based on break-even cutoff. |
| `ao3_priority_segment` | One of the four AO3 operational segments or a review fallback. |

## References

- `data/references/ao1_decision_threshold_policy.csv`
- `docs/ao1_decision_threshold.md`
- `docs/ao2_target_policy.md`
- `docs/ao2_results_h2.md`
- `docs/ao2_target_reconstruction_review.md`
- `docs/pre_gold_modeling_decisions.md`
- `docs/proposal/proposal_summary.md`
