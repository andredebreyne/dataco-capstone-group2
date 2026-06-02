# Table 5. AO3 Risk-Margin Matrix Policy

Source artifacts: `data/references/ao3_risk_margin_matrix_policy.csv`, `docs/ao3_risk_margin_matrix.md`, `docs/ao3_methodology_and_results.md`, `data/references/ao3_operational_recommendation_matrix.csv`.

Risk cutoff: `ao1_predicted_late_delivery_probability >= 0.35`.

Margin cutoff: `ao3_predicted_margin >= 0.0`.

| Risk band | Margin band | Segment label | Operational meaning | Recommended action | Policy status |
| --- | --- | --- | --- | --- | --- |
| High risk | High margin | `protect_high_value_at_risk` | High service risk with positive expected margin. | Prioritize pre-dispatch protection and exception handling before lower-risk work. | `approved_for_submission` |
| High risk | Low margin | `expedite_selectively` | High service risk with weak or negative expected margin. | Review selectively before committing scarce expedited capacity. | `approved_for_submission` |
| Low risk | High margin | `preserve_service` | Lower service risk with positive expected margin. | Maintain service quality and protect customer experience without unnecessary escalation. | `approved_for_submission` |
| Low risk | Low margin | `standard_process` | Lower service risk with weak or negative expected margin. | Use normal operating procedures and monitor margin drivers. | `approved_for_submission` |
| Missing AO1 or AO2 score | Not assignable | `requires_score_review` | Score inputs are missing, so the order cannot be assigned reliably. | Hold automated AO3 prioritization and review score pipeline completeness. | `approved_for_submission` |
| AO3 order value or predicted margin missing or invalid | Not assignable | `requires_margin_review` | Margin inputs are missing or invalid, so the order cannot be placed reliably on the margin axis. | Hold automated margin-based prioritization and review denominator or margin construction. | `approved_for_submission` |

Caveat: AO3 uses predicted AO1 risk and predicted AO2 profit/margin only. It does not use realized delivery or realized profit outcomes for segment assignment and does not prove realized intervention impact.
