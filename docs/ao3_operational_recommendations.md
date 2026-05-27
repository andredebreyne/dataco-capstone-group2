# AO3 Operational Recommendations

Issue: `#45`

## Purpose

This document translates the AO3 risk-margin framework into practical
pre-dispatch recommendations for managers. It uses the governed AO3 segment
definitions, the held-out AO3 benchmark, and the operational caveats documented
for H3.

These recommendations are decision-support guidance. They do not claim causal
impact, realized profit improvement, or final-test outcome performance.

## Evidence Base

The recommendations are tied to the AO3 benchmark outputs:

```text
data/references/ao3_risk_margin_benchmark_segment_summary.csv
data/references/ao3_risk_margin_benchmark_insights.csv
```

The benchmark population contains `34,467` held-out scored orders. The main
segment distribution is:

| AO3 segment | Count | Share | Average risk | Average predicted margin |
| --- | ---: | ---: | ---: | ---: |
| `protect_high_value_at_risk` | 13,752 | 39.9% | 0.832 | 0.126 |
| `preserve_service` | 20,603 | 59.8% | 0.319 | 0.126 |
| `expedite_selectively` | 52 | 0.15% | 0.811 | -0.127 |
| `standard_process` | 60 | 0.17% | 0.298 | -0.293 |
| `requires_score_review` | 0 | 0.0% | n/a | n/a |
| `requires_margin_review` | 0 | 0.0% | n/a | n/a |

The strongest benchmark evidence for H3 is that margin-only prioritization would
mix high-margin orders requiring risk protection with high-margin orders that can
remain under preserve-service handling. Risk-only differentiation is weaker in
this held-out sample because nearly all high-risk orders are also high-margin.

## Action Matrix

The governed recommendation matrix is versioned at:

```text
data/references/ao3_operational_recommendation_matrix.csv
```

| AO3 segment | Managerial interpretation | Recommended action | Main caution |
| --- | --- | --- | --- |
| `protect_high_value_at_risk` | High predicted late-delivery risk and high predicted margin. | Prioritize pre-dispatch protection and exception handling. | Use targeted intervention rather than blanket premium-cost expediting. |
| `preserve_service` | Low predicted late-delivery risk and high predicted margin. | Maintain service quality and monitor for risk drift. | Do not over-service solely because margin is high. |
| `expedite_selectively` | High predicted late-delivery risk and low predicted margin. | Review case by case before using scarce expedited capacity. | Segment size is small and predicted economics are weak. |
| `standard_process` | Low predicted late-delivery risk and low predicted margin. | Use normal operating procedures. | Monitor pricing or cost drivers because predicted margin is negative. |
| `requires_score_review` | Missing AO1 or AO2 score input. | Hold AO3 prioritization and review scoring completeness. | Treat as a data-quality exception, not an action segment. |
| `requires_margin_review` | Missing or invalid AO3 margin input. | Hold margin-based prioritization and review denominator/margin construction. | Treat as a data-quality exception before business action. |

## Managerial Use

The AO3 action matrix should be used as a lightweight triage layer:

- `protect_high_value_at_risk` should drive the primary intervention queue.
- `preserve_service` should help managers protect high-value service quality
  without unnecessary escalation.
- `expedite_selectively` should be reviewed carefully because service risk is
  high but expected economics do not support automatic premium intervention.
- `standard_process` should remain in normal operations, with margin monitoring
  rather than urgent logistics action.
- fallback categories should be shown in dashboard QA views and investigated as
  data or scoring issues.

The recommendations differentiate logistics attention, margin scrutiny, and
monitoring. They are intentionally proportional to the evidence: AO3 separates
operationally meaningful groups, but the benchmark does not prove that a
specific intervention changes realized delivery or profit.

## Dashboard Implications

The dashboard should expose the action matrix next to the AO3 segment counts and
benchmark context. Recommended first-pass visuals include:

- segment count and share by `ao3_priority_segment`;
- average predicted late-delivery risk by segment;
- average predicted profit and predicted margin by segment;
- an action-matrix table using the recommendation CSV;
- QA indicators for `requires_score_review` and `requires_margin_review`.

This lets managers connect the AO3 matrix to concrete actions while preserving
the methodology caveats needed for the final report.

## Validation

Run:

```text
tests/data_validation/validate_ao3_operational_recommendations.py
```

The validation checks full segment coverage, non-empty action fields, evidence
links, limitations, fallback treatment, and guarded recommendation language.
