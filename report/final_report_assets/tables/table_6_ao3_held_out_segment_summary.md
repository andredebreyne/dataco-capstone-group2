# Table 6. AO3 Held-Out Scored Segment Summary

Source artifacts: `data/references/ao3_risk_margin_benchmark_segment_summary.csv`, `docs/ao3_segment_assignment.md`, `docs/ao3_risk_margin_benchmark.md`, `docs/ao3_methodology_and_results.md`.

Population: 34,467 held-out scored AO1/AO2 prediction outputs used for AO3 segmentation and benchmark comparison.

| Segment label | Human-readable label | Row count | Share | Avg predicted risk | Avg predicted profit | Avg predicted margin | Key operational interpretation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `protect_high_value_at_risk` | Protect high-value at-risk orders | 13,752 | 0.3989903385847332 | 0.8324602947089823 | 21.61366738959954 | 0.12554767718238763 | Primary protection queue for differentiated pre-dispatch review. |
| `preserve_service` | Preserve service for high-margin lower-risk orders | 20,603 | 0.5977601764006151 | 0.31855199708932536 | 21.602960398379558 | 0.12551371875167308 | Maintain service quality without urgent escalation by default. |
| `expedite_selectively` | Selectively review high-risk weak-margin orders | 52 | 0.0015086894710882874 | 0.8112713201687887 | -14.641808715577309 | -0.12700143337418418 | Small exception queue for selective review before expensive intervention. |
| `standard_process` | Standard process and margin monitoring | 60 | 0.0017407955435634085 | 0.2981830401346087 | -20.6062355131687 | -0.2930214698307763 | Routine handling with margin monitoring. |
| `requires_score_review` | Score review required | 0 | 0.0 | n/a | n/a | n/a | Data-quality exception category. |
| `requires_margin_review` | Margin review required | 0 | 0.0 | n/a | n/a | n/a | Data-quality exception category. |

H3 evidence note: the combined AO3 framework separates groups that risk-only or margin-only views would not fully distinguish. The strongest example is the separation between high-margin high-risk orders and high-margin lower-risk orders.
