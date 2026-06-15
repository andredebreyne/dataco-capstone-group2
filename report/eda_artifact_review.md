# EDA Artifact Review

## Artifact Traceability Table

| artifact path | artifact type | relevant AO | supported finding | confidence level | suitable for main report | suitable for appendix | recommended use | caution or limitation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `report/final_capstone_report_final_markdown.md` | Current final report context | AO1/AO2/AO3 | Current report already covers data source, governance, leakage control, chronological split, methods, and results, so an EDA section should be short and design-focused. | High | Yes | No | Use to avoid duplication and place EDA between data engineering and leakage/split methodology. | Do not repeat results, dashboard, or full data-source description. |
| `docs/eda_findings_summary.md` | EDA synthesis document | AO1/AO2/AO3 | EDA informed feature selection, leakage review, chronological split design, metric choice, and modeling priorities; findings are descriptive, not causal. | High | Yes | Yes | Primary source for concise EDA narrative. | It is a synthesis, not a new EDA run. |
| `report/tables/ao1_class_imbalance_findings.md` | Report-facing findings table/note | AO1 | `Late_delivery_risk` has 98,977 late rows, 81,542 not-late rows, 54.83% late rate, and mild majority/minority ratio of 1.214:1. | High | Yes | Yes | Use one sentence to justify metric choices beyond accuracy. | Counts are from Silver clone EDA, not final AO1 Gold after population filtering. |
| `docs/ao1_class_imbalance_analysis.md` | Method note | AO1 | Class-imbalance EDA used the local Silver clone and did not apply resampling, train models, or set thresholds. | High | No | Yes | Use as support for claim-safety and modeling-design guardrails. | No direct result table beyond linked artifacts. |
| `report/tables/ao1_late_delivery_bivariate_findings.md` | Report-facing findings table/note | AO1 | Planned service fields showed the largest support-safe descriptive differences: First Class and one scheduled shipping day each had 95.32% late-delivery rates, while Standard Class and four scheduled days each had 38.07%. | High | Yes | Yes | Use briefly to explain why planned service fields stayed in Gold review. | Descriptive association only; not causal and not final feature selection. |
| `docs/ao1_bivariate_eda.md` | Method note | AO1 | AO1 EDA separated allowed, conditional, excluded, dashboard-only, and descriptive-only variables using leakage screening. | High | No | Yes | Use to confirm governance framing if needed. | Avoid listing all workflow mechanics in the main report. |
| `report/tables/ao2_profitability_bivariate_findings.md` | Report-facing findings table/note | AO2 | AO2 target had 180,519 valid rows, mean 21.97, median 31.52, standard deviation 104.43, minimum -4,274.98, maximum 911.80, skewness -4.742, and 18,942 IQR outliers. | High | Yes | Yes | Use to justify RMSE/MAE focus and target-reconstruction caution. | Do not imply precise item-level forecasting quality from EDA alone. |
| `docs/ao2_bivariate_eda.md` | Method note | AO2 | AO2 EDA treated financial, discount, sales, price, quantity, and order-value variables as review-sensitive because of target-reconstruction risk. | High | Yes | Yes | Use to connect EDA to AO2 feature governance. | Does not approve final predictors. |
| `report/tables/univariate_distribution_eda_findings.md` | Report-facing univariate findings | AO1/AO2/AO3 | Most reviewed variables had usable missingness, but `Order Zipcode` had 86.24% missingness; raw order timestamp, IDs, granular geography, and product name/cardinality fields required exclusion, grouping, or deferral. | High | Yes | Yes | Use briefly under data-quality findings. | Issue 18 univariate approvals are feasibility evidence only, not modeling approval. |
| `report/tables/eda_univariate_summary.csv` | Generated CSV summary | AO1/AO2/AO3 | Machine-readable source for missingness, cardinality, outlier, and review-status details. | Medium | No | Yes | Keep as appendix/reference artifact only. | Main report should use synthesized findings, not raw CSV detail. |
| `docs/pre_gold_modeling_decisions.md` | Governance decision document | AO1/AO2/AO3 | Final pre-Gold policy supersedes preliminary EDA review status where they differ, especially for commercial predictors, granular geography, and raw identifiers. | High | Yes | Yes | Use to keep EDA wording aligned with final feature policy. | Not an EDA output by itself. |
| `report/figures/eda/ao1_class_imbalance_late_rate_by_shipping_mode.svg` | EDA visualization | AO1 | Visualizes late-delivery rate variation by shipping mode. | High | Optional | Yes | Best single EDA visualization candidate if one is added, but text-only is preferred for the main report. | Duplicates a concise numeric finding already easy to state in prose. |
| `report/figures/eda/ao2_profit_distribution.svg` | EDA visualization | AO2 | Visualizes profitability distribution and supports skew/outlier discussion. | Medium | No | Yes | Appendix candidate if AO2 distribution detail is requested. | Main report already has AO2 result table and caveats; extra figure may cost too much space. |
| `report/figures/eda/ao1_class_imbalance_late_rate_by_order_month.svg` | EDA visualization | AO1 / temporal review | Visualizes late-delivery rates by order month. | Medium | No | Optional | Appendix-only if reviewers ask for temporal EDA support. | Do not claim temporal drift unless supported by additional checked analysis. |
| `report/figures/eda/*.png` univariate figures | EDA visual set | AO1/AO2/AO3 | Variable-level distributions for reviewed fields. | Medium | No | Optional | Omit from main report; keep as repository evidence. | Mostly generic and not directly tied to the research question under page constraints. |

## Visualization Review

| source artifact | finding communicated | value to the report | duplicates existing table or figure | recommendation | estimated space cost |
| --- | --- | --- | --- | --- | --- |
| `report/figures/eda/ao1_class_imbalance_late_rate_by_shipping_mode.svg` | Late-delivery rates vary descriptively by planned shipping mode. | Supports AO1 feature-design discussion. | Partly duplicates the proposed EDA prose and later AO1 interpretation. | Appendix if needed; omit from main report unless one EDA visual is required. | About one-third to one-half page. |
| `report/figures/eda/ao1_class_imbalance_overall.svg` | AO1 target class balance. | Low; the class balance can be stated in one sentence. | Duplicates numeric class-balance prose. | Omit. | About one-quarter page. |
| `report/figures/eda/ao2_profit_distribution.svg` | Profit target skew and outlier sensitivity. | Moderate; supports AO2 target difficulty. | Partly duplicates AO2 EDA statistics and AO2 results caveats. | Appendix if page budget allows. | About one-third page. |
| `report/figures/eda/ao1_class_imbalance_late_rate_by_order_month.svg` | Month-level late-delivery rate variation. | Limited unless the report needs a temporal EDA visual. | Could duplicate chronological split discussion without proving drift. | Appendix only; avoid main report. | About one-third page. |
| `report/figures/eda/ao2_profit_by_category_name.svg` | Profitability varies descriptively by product category. | Moderate but not essential. | Duplicates product-mix prose. | Appendix only. | About one-third to one-half page. |
| `report/figures/eda/*.png` univariate figures | Missingness/cardinality/distribution detail for individual fields. | Low for final report narrative. | Duplicates artifact-level evidence rather than methodological decision. | Omit from main report. | Variable; likely too costly. |

Recommendation: use a text-only EDA subsection in the main report. No existing EDA visualization is strong enough to justify main-report space unless the instructor explicitly expects an EDA chart. If one visual must be added, use `report/figures/eda/ao1_class_imbalance_late_rate_by_shipping_mode.svg` as the most directly connected to AO1 feature design; otherwise keep EDA visuals in the appendix or repository evidence only.

## Integration Recommendation

- Placement: insert the EDA subsection after `## Data Engineering and Cloud Implementation` and before `## Leakage-Control and Chronological Split Methodology`.
- Rationale: this location lets EDA bridge data processing and the modeling controls without interrupting AO1/AO2/AO3 results.
- Duplication control: keep the section short; do not repeat Table 1, Table 2, the leakage-control policy, or AO1/AO2/AO3 result metrics.
- Current report paragraphs to shorten if needed: if page count becomes tight, shorten the Data Source paragraph that lists broad dataset domains or move extra EDA statistics to an appendix.
- Main-report figure recommendation: no EDA figure in the main report; use text-only unless a reviewer specifically requests an EDA visualization.

## Claim-Safety Notes

- No statistical significance, causality, or final feature-importance claims should be made from EDA.
- EDA findings should be described as descriptive variation, target review, data-quality review, or feature-governance support.
- Numerical findings in the draft trace to `docs/eda_findings_summary.md`, `report/tables/ao1_class_imbalance_findings.md`, `report/tables/ao1_late_delivery_bivariate_findings.md`, `report/tables/ao2_profitability_bivariate_findings.md`, and `report/tables/univariate_distribution_eda_findings.md`.
- No new external citations or references are needed for this EDA subsection.
