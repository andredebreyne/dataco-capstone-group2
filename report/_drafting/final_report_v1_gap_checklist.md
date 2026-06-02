# Final Report Draft V1 Gap Checklist

This checklist reviews `report/final_capstone_report_draft_v1.md` against the current course-facing report needs. It does not edit the expanded final report, model artifacts, dashboard artifacts, or APA inventory.

## 1. Requirement Coverage

| Requirement | Status | Draft V1 coverage | Remaining work |
| --- | --- | --- | --- |
| Research problem/objective | covered | Introduction frames the business problem as pre-dispatch order prioritization combining late-delivery risk and expected profitability. | Add final course, team, and instructor metadata on title page. |
| Research question/hypotheses | covered | Research question, AO1/AO2/AO3 objectives, and H1/H2/H3 wording are included and kept consistent with current project docs. | Confirm instructor-preferred wording before final submission. |
| Data description/preprocessing | covered | Data Source and Data Governance section includes dataset DOI, row/column counts, metadata coverage, missing values, Bronze/Silver/Gold governance, and leakage-related preprocessing rules. | Add final formatted data summary table and possibly a data dictionary excerpt. |
| Statistical/diagnostic checks | partially covered | AO1 metrics, AO1 threshold evidence, AO2 validation metrics, AO2 residual limitations, AO2 target-reconstruction audit, AO3 benchmark evidence, and validation boundaries are summarized. | Insert final tables and figure captions; verify any additional diagnostic requirements from the course rubric. |
| 3-5 advanced analytics methods | covered | Logistic Regression, XGBoost classification, Ridge Regression, Gradient Boosting/XGBoost regression, SHAP explainability, AO3 risk-margin segmentation, and optional K-means review are described. | Tighten wording if page count requires a shorter methods section. |
| Visualizations/dashboard | partially covered | Power BI is documented as the official dashboard deliverable, with the direct Azure Databricks serving-layer architecture and PR #141 first-page status. | Add final screenshots, page titles, final page inventory, and manifest details if available. |
| Strategic implications | covered | Strategic and Operational Recommendations section maps AO3 segments to managerial actions. | Add final recommendation matrix table and any instructor-required executive implication summary. |
| Limitations/future research | covered | Limitations, ethics, responsible use, and future research sections cover non-causality, no production deployment, AO1/AO2/AO3 limits, and future intervention evaluation. | Add verified responsible-AI or governance citation if broad governance claims remain. |
| Appendices/code/dataset | partially covered | Appendices identify artifact index, validation summary, data dictionary, code index, model metadata, Power BI serving docs, dashboard artifacts, and AI/tooling note. | Add final appendix numbering and any required code/dataset submission links. |
| APA references | partially covered | Working References includes the complete DataCo citation and APA TODO entries keyed to the selected reference plan. | Collect missing metadata and convert TODO entries into final APA references. |

## 2. Remaining APA Work

No generic source-detail markers remain in the V1 draft. The draft uses normal author-year placeholders where author/year evidence exists and uses keyed APA TODO placeholders where metadata remains incomplete.

Incomplete or pending citation keys in the draft:

| Citation key | Missing metadata or decision |
| --- | --- |
| `toorajipour_2021_ai_scm_review` | Full author initials, journal, volume/issue/pages, DOI or URL. |
| `ni_xiao_lim_2020_ml_scm_review` | Full author initials, journal, volume/issue/pages, DOI or URL. |
| `baryannis_2019_supply_chain_risk_ml` | Full author initials, venue, volume/issue/pages, DOI or URL. |
| `ahmed_2025_interpretable_supply_chain_forecasting` | Full author initials, venue, volume/issue/pages, DOI or URL. |
| `katangoori_2026_dataco_supply_chain_optimization` | Full publication metadata, DOI or URL, source-quality review. |
| `hastie_tibshirani_friedman_2009_esl` | Edition, publisher, URL if online version is cited. |
| `liu_chen_zheng_feng_2022_leakage_suppression` | Venue or publisher, volume/issue/pages if applicable, DOI or URL. |
| `lundberg_lee_2017_shap` | Proceedings or venue details, DOI or URL. |
| `microsoft_learn_powerbi_azure_databricks` | Microsoft Learn page date, URL, retrieval date if needed. |
| `zaharia_2016_apache_spark` | Full author list, venue, DOI or URL. |
| `armbrust_2020_delta_lake` | Full author list, venue, DOI or URL. |
| `databricks_official_reference` | Official page title, organization, date/year, URL, retrieval date if needed. |
| `xgboost_documentation_3_2_0` | Documentation page title, organization, release/version, URL, retrieval date if needed. |
| `chen_guestrin_2016_xgboost_method` | Full paper title, venue, publisher/proceedings, DOI or URL; use only if broad method discussion remains. |
| `scikit_learn_ridge_documentation` | Ridge documentation page title, URL, retrieval date if used. |
| `scikit_learn_broad_citation_needed` | Canonical paper or documentation metadata; use only if scikit-learn is cited broadly. |
| `responsible_ai_governance_reference_needed` | Verified responsible-AI, model governance, or limitations source if broad governance claims remain. |
| `microsoft_powerbi_official_reference` | Needed only if Power BI tooling mechanics are discussed beyond the Azure Databricks connector source. |

References to verify manually:

- Confirm whether the final literature review needs all selected supply-chain sources or a smaller set.
- Confirm whether Chen and Guestrin (2016) remains necessary after method wording is finalized.
- Confirm whether scikit-learn should be cited broadly or only through the Ridge documentation slot.
- Confirm whether a responsible-AI/governance source is required by the final limitations section.
- Confirm Microsoft Learn metadata for "Power BI with Azure Databricks."

## 3. Dashboard Updates Still Needed

| Update item | Status | Notes |
| --- | --- | --- |
| PR #141 screenshot/page title | update later | Draft contains a finalization marker for the first Power BI dashboard page screenshot and title. |
| Final Power BI page inventory | update later | Draft requests final executive, AO1, AO2, AO3, and governance page inventory if present. |
| `.pbix` submission route if required | update later | Draft says no `.pbix` is claimed as present in Git and asks for final course submission route. |
| Final serving-layer manifest details | update later | Draft asks for final row counts if available and verified. |
| Final dashboard captions | update later | Add figure captions once screenshots are available. |

Dashboard status wording used in the draft:

- Power BI is the official dashboard deliverable.
- Direct Power BI connection to Azure Databricks serving-layer tables is the selected architecture.
- The connection worked.
- The first dashboard page was published in PR #141.
- Final screenshots, page names, page inventory, `.pbix` route, and manifest details remain update points.

## 4. Tables and Figures Still Needed

Every table or figure callout currently in the draft:

| Callout | Source/status |
| --- | --- |
| Business problem to analytical objective mapping | Internal synthesis from proposal and AO result docs; can remain as a report-created table. |
| DataCo dataset summary | Source available: `docs/data_source_verification.md`. |
| Medallion and project workflow architecture | Needs formatted figure from `docs/medallion_structure.md` and `docs/project_orchestrator.md`. |
| Power BI serving-layer table inventory | Source available: `docs/powerbi_databricks_serving_layer.md` and `dashboard/powerbi_semantic_model.md`. |
| Leakage-control and feature availability summary | Source available: `docs/leakage_control_plan.md`, `docs/feature_availability_map.md`, `data/references/feature_availability_map.csv`. |
| Chronological split summary | Source available: `docs/chronological_split_policy.md`, `data/references/ao1_chronological_partition_summary.csv`, `data/references/ao2_chronological_partition_summary.csv`. |
| AO2 target-reconstruction audit summary | Source available: `report/tables/ao2_target_reconstruction_audit_findings.md`. |
| Analytical methods coverage matrix | Source available: detailed outline and AO result docs. |
| AO1 model comparison | Source available: `report/tables/ao1_model_validation_comparison.csv`. |
| AO1 threshold recommendation | Source available: `report/tables/ao1_decision_threshold_recommendation.md` and `data/references/ao1_decision_threshold_policy.csv`. |
| AO1 SHAP top features | Source available: `report/figures/ao1_shap_top_features.png`. |
| AO2 model comparison | Source available: `report/tables/ao2_model_validation_comparison.csv` and `report/tables/ao2_results_h2_summary.csv`. |
| AO2 residual diagnostics | Source available: `report/tables/ao2_residual_diagnostics_by_model.csv`. |
| AO2 SHAP top features | Source available: `report/figures/modeling/ao2_shap_top_features.png`. |
| AO3 risk-margin matrix | Source available: `docs/ao3_risk_margin_matrix.md` and `data/references/ao3_risk_margin_matrix_policy.csv`. |
| AO3 segment summary | Source available: `data/references/ao3_risk_margin_benchmark_segment_summary.csv`. |
| AO3 benchmark and crosswalk evidence | Source available: `data/references/ao3_risk_margin_benchmark_crosswalk.csv` and `data/references/ao3_risk_margin_benchmark_insights.csv`. |
| Final Power BI serving-layer inventory with manifest status | Inventory source available; final manifest row counts still need verified final run details. |
| Power BI dashboard screenshot/page title | Needs final screenshot/page title from PR #141 or final dashboard PR. |
| AO3 operational recommendation matrix | Source available: `data/references/ao3_operational_recommendation_matrix.csv` and `docs/ao3_operational_recommendations.md`. |
| Final Power BI dashboard screenshots/page names appendix | Needs final dashboard artifacts. |

## 5. Claims to Review Carefully

| Claim | Risk | Review guidance |
| --- | --- | --- |
| H1 is supported | Could be overstated if described as final-test evidence. | Keep as validation evidence unless final-test artifact exists. |
| H2 is supported | Improvement is modest and R2 is low. | Preserve "supported with modest improvement" and target-reconstruction caution. |
| AO2 predicts profitability | Could sound like exact accounting reconstruction. | Use "expected profitability estimation" and cite `accepted_with_caution`. |
| AO3 supports differentiated actions | Could imply causal intervention impact. | State as decision-layer evidence, not realized outcome evidence. |
| Power BI page was published in PR #141 | Team status says this occurred, but final screenshot/page details are not yet inserted. | Add screenshot and page title before final submission. |
| Direct Power BI connection worked | Team status says this occurred. | Add final connection/manifest details if available. |
| Responsible use/fairness language | External governance citation is not verified. | Keep grounded in internal controls or add verified source. |
| Spark/Delta/Databricks platform discussion | External APA metadata is incomplete. | Verify source metadata or keep as internal implementation documentation. |

## 6. Final Formatting Tasks

- Convert Markdown headings into APA-style heading levels during Word/PDF conversion.
- Add final title-page metadata.
- Insert final table numbers, titles, notes, and source captions.
- Insert final figure numbers, titles, notes, and source captions.
- Replace APA TODO placeholders with verified citations and full references.
- Remove optional working references not cited in final text.
- Add final appendices and appendix labels.
- Add final dashboard screenshot/page title from PR #141 or final dashboard PR.
- Confirm `.pbix` submission route if required by the course.
- Run page-count check after Word/PDF conversion.
- Check all artifact links and table/figure paths after final formatting.

## 7. Risks Before Final Submission

| Risk | Classification | Mitigation |
| --- | --- | --- |
| Incomplete APA metadata | major | Collect missing fields and replace APA TODO placeholders before final submission. |
| Dashboard screenshot/page inventory missing | major | Insert PR #141 screenshot/page title and final page inventory. |
| `.pbix` route unclear if required | major | Confirm whether course submission expects external `.pbix`, rebuilt dashboard, or screenshot evidence. |
| H1/H2 wording overstates final-test evidence | blocker if introduced | Keep validation-only wording unless a verified final-test artifact supports stronger wording. |
| AO3 wording implies realized intervention outcome | blocker if introduced | Preserve decision-support and no-causal-claim caveats. |
| AO2 target-reconstruction caution omitted | blocker if introduced | Keep `accepted_with_caution` and low-R2 caveats. |
| Old dashboard-status wording in other final-facing docs | major | Reconcile remaining final-facing navigation docs before submission if they are still used. |
| Missing final serving-layer manifest details | minor | Add only if a verified final Databricks run provides row counts. |
| Page count not checked after conversion | minor | Convert to Word/PDF and inspect final length. |
| Optional references included without use | minor | Remove unused optional sources from the final References section. |
