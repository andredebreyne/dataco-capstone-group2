# Final Report Detailed Outline

## 1. Readiness Verdict

Current file assessed: `report/final_capstone_report.md`

| Item | Assessment |
| --- | --- |
| Readiness category | Partial draft |
| Approximate word count | 2,016 words |
| Estimated current page count | About 7-8 pages at 250-300 words per page before tables, figures, title page, references, and appendices |
| Target final report length | 25-30 APA-style pages |
| Required expansion level | Substantial expansion, approximately 3x current prose plus formatted tables, figures, references, and appendices |

The current draft is stronger than a skeleton because it already contains the research question, hypotheses, AO1/AO2/AO3 summaries, caveats, validation language, dashboard note, limitations, responsible-use language, and artifact links. It is not near-final because it is too short for the assignment, does not yet contain a literature review, does not fully describe the data engineering/cloud implementation, does not include enough method detail, does not include all required tables and figures, and uses older dashboard-status wording that no longer reflects the official Power BI decision.

Highest-priority missing sections:

1. Literature review / analytical context.
2. Data engineering and cloud implementation details, including Databricks, Delta, Medallion layers, and Power BI serving tables.
3. Statistical and diagnostic checks across EDA, AO1, AO2, AO3, and validation.
4. Full analytical methods section covering 3-5 advanced analytics methods plus supporting explainability and segmentation methods.
5. Power BI dashboard section using the official Power BI direction and direct Azure Databricks serving-layer architecture.
6. Expanded results interpretation and actionable recommendations.
7. APA references and appendices.
8. Source cleanup note: existing navigation/report-status files still mention a possible Databricks native/AI BI dashboard alternative. The final report should not present that as the planned dashboard path because Power BI is now the official direction.

## 2. Proposed APA-Style Final Report Structure

| Section | Purpose | Target length | Source artifacts | Key claims to include | Tables/figures to include | Missing evidence or update notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Title Page | Provide APA-style title, course, team, institution, and date. | 1 page | Project title in `report/final_capstone_report.md`; proposal summary in `docs/proposal/proposal_summary.md` | The project predicts late-delivery risk and expected profitability for pre-shipment supply-chain decision support. | None | Add final team names, instructor, course, date. |
| 2. Abstract / Executive Summary | Summarize problem, method, results, dashboard, and recommendations. | 0.75-1 page | `report/final_capstone_report.md`; AO1/AO2/AO3 result docs | H1 and H2 supported on validation evidence; H3 supported by AO3 benchmark evidence with caveats; Power BI is official dashboard path. | Optional compact hypothesis summary table | Update dashboard sentence after final dashboard polish. |
| 3. Introduction and Business Problem | Explain operational problem and why risk and margin must be combined. | 1.5-2 pages | `docs/proposal/proposal_summary.md`; `report/final_capstone_report.md` | Late delivery risk and profitability require joint pre-dispatch prioritization. | Optional business problem flow figure | Needs a stronger academic/business motivation paragraph. |
| 4. Research Question, Objectives, and Hypotheses | State research question, AO1/AO2/AO3/dashboard objectives, and H1-H3. | 1-1.5 pages | `docs/proposal/proposal_summary.md`; `report/final_capstone_report.md` | The project is one integrated pre-shipment decision-support framework, not three unrelated models. | AO-to-hypothesis mapping table | Can be drafted now. |
| 5. Literature Review / Analytical Context | Connect project to predictive analytics, supply-chain risk, profitability, and explainable AI. | 3-4 pages | Proposal references if available; external APA sources still needed | Predictive analytics can support operational triage, but leakage-safe design and explainability are required. | Literature theme matrix if useful | [NEEDS SOURCE DETAILS] for academic references. |
| 6. Data Source and Data Governance | Document DataCo source, rows/columns, metadata, licensing, anonymization, and governance. | 1.5-2 pages | `docs/data_source_verification.md`; `data/bronze/dataco/DescriptionDataCoSupplyChain.csv`; `docs/silver_schema_data_dictionary.md` | Dataset is public, anonymized, partially synthetic, 180,519 rows and 53 columns; raw data preserved in Bronze. | Dataset summary table; data dictionary excerpt | Can be drafted now. |
| 7. Data Engineering and Cloud Implementation | Explain Databricks, Spark/Delta, Medallion architecture, orchestrator, and serving layer. | 2.5-3 pages | `docs/medallion_structure.md`; `docs/project_orchestrator.md`; `docs/databricks_setup.md`; `docs/powerbi_databricks_serving_layer.md`; `src/dashboard/register_powerbi_databricks_tables.py` | Reusable logic lives in `/src`; Databricks orchestrates Bronze/Silver/Gold/model/scoring/Power BI serving-layer jobs; serving layer publishes governed `powerbi_*` tables. | Medallion pipeline figure/table; Power BI serving table inventory | Add final statement that direct Power BI connection worked, based on team update. |
| 8. Leakage-Control and Chronological Split Methodology | Explain decision-time integrity, forbidden variables, AO2 target reconstruction risk, and time split. | 2-2.5 pages | `docs/leakage_control_plan.md`; `docs/feature_availability_map.md`; `docs/pre_gold_modeling_decisions.md`; `docs/chronological_split_policy.md`; `docs/ao2_target_reconstruction_review.md` | Predictors are pre-shipment/order-time only; final held-out test partitions use most recent 20%; AO2 accepted with caution. | Leakage-control summary table; chronological split summary table | Can be drafted now. |
| 9. Analytical Methods | Describe models and diagnostics for AO1, AO2, SHAP, AO3, and optional K-means. | 3-4 pages | AO1/AO2 method docs; `docs/ao3_risk_margin_matrix.md`; `docs/ao3_kmeans_extension.md` | Logistic/Ridge baselines support comparison; XGBoost/Gradient Boosting are primary nonlinear methods; SHAP supports explainability; AO3 is rule-based decision layer; K-means was not adopted. | Methods summary table | Can be drafted now. |
| 10. AO1 Results: Late-Delivery Risk Prediction | Present AO1 model comparison, threshold, explainability, and caveats. | 2-2.5 pages | `docs/ao1_results_h1_validation.md`; `docs/ao1_model_evaluation.md`; `docs/ao1_shap_explainability.md`; `docs/ao1_post_model_leakage_audit.md` | H1 supported on validation evidence; XGBoost improves ROC-AUC and recall; threshold 0.35 used for AO3. | AO1 model comparison table; threshold table; AO1 SHAP figure | Can be drafted now. Do not claim unsupported final-test performance. |
| 11. AO2 Results: Profitability Estimation | Present AO2 comparison, residuals, SHAP, target-reconstruction audit, and caveats. | 2-2.5 pages | `docs/ao2_results_h2.md`; `docs/ao2_model_evaluation.md`; `docs/ao2_shap_explainability.md`; `docs/ao2_target_reconstruction_review.md` | H2 supported on validation evidence with modest improvement; AO2 predictive power remains limited; accepted with caution. | AO2 model comparison table; AO2 SHAP figure; residual diagnostics table | Can be drafted now. |
| 12. AO3 Results: Risk-Margin Prioritization Framework | Present AO3 matrix, segment counts, benchmark, operational meaning, and H3 conclusion. | 2.5-3 pages | `docs/ao3_methodology_and_results.md`; `docs/ao3_risk_margin_benchmark.md`; `docs/ao3_operational_recommendations.md` | H3 supported by segmentation and benchmark evidence with caveats; AO3 adds decision-layer value beyond single-signal views. | AO3 matrix; segment summary table; benchmark/crosswalk evidence table | Can be drafted now. |
| 13. Power BI Dashboard and Visualization Layer | Explain official Power BI dashboard direction, Azure Databricks connector, serving tables, and first published page. | 2-2.5 pages | `docs/powerbi_databricks_serving_layer.md`; `dashboard/powerbi_semantic_model.md`; `dashboard/powerbi_measures.dax`; `src/dashboard/register_powerbi_databricks_tables.py`; `tests/data_validation/validate_powerbi_databricks_serving_layer.py` | Power BI is official visualization tool; direct Power BI connection to Azure Databricks serving tables is the chosen architecture; first dashboard page was published in PR #141 per team update. | Serving-layer inventory; dashboard screenshot placeholder for PR #141 page | [TO UPDATE AFTER DASHBOARD FINALIZATION] for screenshots and page details. |
| 14. Strategic and Operational Recommendations | Convert AO3 results into actionable management recommendations. | 1.5-2 pages | `docs/ao3_operational_recommendations.md`; `data/references/ao3_operational_recommendation_matrix.csv` | Recommendations are triage guidance, not causal proof. | AO3 action matrix | Can be drafted now. |
| 15. Limitations, Ethics, and Responsible Use | Document data, model, dashboard, and responsible-use caveats. | 1.5-2 pages | `report/final_capstone_report.md`; AO1/AO2/AO3 limitations docs | No causal claim, no production deployment, no live intervention test, model limitations, synthetic/anonymized data. | Optional limitations table | Can be drafted now. |
| 16. Future Research | Identify next analytical and deployment work. | 1 page | Existing limitations docs; proposal scope | Future work includes external variables, recalibration, outcome evaluation, monitoring, and dashboard iteration. | Optional future-work table | Can be drafted now. |
| 17. Conclusion | Restate integrated contribution and hypothesis outcomes. | 0.75-1 page | Final report draft; H1/H2/H3 docs | The framework provides leakage-safe pre-shipment decision support with Power BI communication layer. | None | Can be drafted after main sections. |
| 18. References | Provide APA references for dataset, methods, tools, and literature. | 2-3 pages | `docs/data_source_verification.md`; proposal references; method/tool docs | Use APA format; do not invent missing reference details. | None | [NEEDS SOURCE DETAILS]. |
| 19. Appendices | Provide supporting artifacts, code index, validations, dashboard serving docs, and AI/tooling note. | As needed outside main 25-30 page body or included after references | `report/final_artifact_index.md`; `report/final_validation_summary.md`; model metadata; validators | Appendices make the analysis reproducible and auditable. | Appendix tables | Can be drafted now with dashboard screenshot appendix later. |

## 3. Section-by-Section Expansion Plan

| Section | Current content available in `final_capstone_report.md` | Additional content needed | Exact source files/artifacts to use | Recommended tables/figures | Required caveats | Estimated final length | Draft status |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| Title Page | Title only. | APA title page metadata. | `docs/proposal/proposal_summary.md` | None | None. | 1 page | Needs team details. |
| Abstract / Executive Summary | Brief executive summary exists. | Expand to APA-style abstract plus executive summary language if instructor allows both. | `report/final_capstone_report.md`; H1/H2/H3 docs | Hypothesis summary table | No production or causal claim. | 0.75-1 page | Draft now, dashboard sentence update later. |
| Introduction and Business Problem | Business problem exists in concise form. | Expand with supply-chain decision context, e-commerce service trade-offs, and managerial stakes. | `docs/proposal/proposal_summary.md` | Business decision flow | Avoid claims about actual intervention results. | 1.5-2 pages | Draft now. |
| Research Question, Objectives, Hypotheses | Present and aligned. | Add AO-to-deliverable mapping and explain integrated logic. | `docs/proposal/proposal_summary.md` | AO mapping table | Keep H wording consistent. | 1-1.5 pages | Draft now. |
| Literature Review / Analytical Context | Not present. | Add supply-chain analytics, predictive risk, profitability modeling, explainable AI, BI/dashboard literature. | Proposal references if available; external APA sources | Literature themes table | Mark source gaps until verified. | 3-4 pages | Needs source collection. |
| Data Source and Governance | Data source and pipeline overview exists. | Add data collection details, metadata, licensing, anonymization, data quality, missingness, and governance. | `docs/data_source_verification.md`; `docs/silver_schema_data_dictionary.md`; `data/references/silver_schema_data_dictionary.csv` | Dataset summary table | Dataset is public, anonymized, partially synthetic. | 1.5-2 pages | Draft now. |
| Data Engineering and Cloud Implementation | Medallion overview exists. | Add Databricks CE setup, Spark/Delta, orchestrator flags, direct Power BI serving layer, managed tables. | `docs/medallion_structure.md`; `docs/project_orchestrator.md`; `docs/databricks_setup.md`; `docs/powerbi_databricks_serving_layer.md`; `src/dashboard/register_powerbi_databricks_tables.py` | Medallion/pipeline figure; serving table inventory | Do not claim production-grade distributed deployment from CE. | 2.5-3 pages | Draft now. |
| Leakage-Control and Chronological Split | Present in concise form. | Expand forbidden fields, feature availability, train-only preprocessing, AO2 target-reconstruction policy. | `docs/leakage_control_plan.md`; `docs/feature_availability_map.md`; `docs/chronological_split_policy.md`; `docs/ao2_target_reconstruction_review.md` | Leakage matrix; split summary | AO2 accepted with caution. | 2-2.5 pages | Draft now. |
| Analytical Methods | Partially present inside AO sections. | Consolidate all methods, model roles, inputs/outputs, evaluation metrics, SHAP, AO3, K-means decision. | AO1/AO2 model docs; `docs/ao3_kmeans_extension.md` | Methods coverage table | Explain validation-stage evidence boundaries. | 3-4 pages | Draft now. |
| AO1 Results | Present. | Add confusion/threshold detail, SHAP interpretation, and leakage audit summary. | `docs/ao1_results_h1_validation.md`; `report/tables/ao1_model_validation_comparison.csv`; `report/figures/ao1_shap_top_features.png` | AO1 model comparison; AO1 SHAP | H1 validation only, not unsupported final-test confirmation. | 2-2.5 pages | Draft now. |
| AO2 Results | Present. | Add residual diagnostics and target-reconstruction discussion. | `docs/ao2_results_h2.md`; `report/tables/ao2_residual_diagnostics_by_model.csv`; `report/figures/modeling/ao2_shap_top_features.png` | AO2 comparison; residual table; SHAP | H2 modest support; low R2; accepted with caution. | 2-2.5 pages | Draft now. |
| AO3 Results | Present. | Add full matrix, segment summary, benchmark/crosswalk, and optional K-means non-adoption note. | `docs/ao3_methodology_and_results.md`; `data/references/ao3_risk_margin_benchmark_crosswalk.csv`; `docs/ao3_kmeans_extension.md` | AO3 matrix; segment summary; benchmark table | No causal or realized outcome claim. | 2.5-3 pages | Draft now. |
| Power BI Dashboard | Current draft has outdated pending/alternative status. | Replace with official Power BI direction, direct Azure Databricks connector, serving-layer tables, first published page in PR #141, and screenshot placeholders. | `docs/powerbi_databricks_serving_layer.md`; `dashboard/powerbi_semantic_model.md`; `dashboard/powerbi_measures.dax`; `tests/data_validation/validate_powerbi_databricks_serving_layer.py` | Serving table inventory; PR #141 screenshot placeholder | Do not present Databricks native dashboard as planned path. | 2-2.5 pages | Draft now; screenshot/page details later. |
| Recommendations | Present but concise. | Expand into logistics, profitability, governance, dashboard cadence, and adoption recommendations. | `docs/ao3_operational_recommendations.md`; `data/references/ao3_operational_recommendation_matrix.csv` | Recommendation matrix | Recommendations are decision-support guidance only. | 1.5-2 pages | Draft now. |
| Limitations/Ethics | Present but concise. | Expand by data, methods, AO1/AO2/AO3, dashboard, ethics, fairness, responsible use. | `report/final_capstone_report.md`; AO docs | Limitations table | No causal, no production, no intervention test. | 1.5-2 pages | Draft now. |
| Future Research | Minimal. | Add external variables, live pilot, recalibration, monitoring, dashboard expansion. | Existing limitations docs | Future research table | Do not imply completed production readiness. | 1 page | Draft now. |
| Conclusion | Not standalone enough. | Synthesize RQ answer, H outcomes, Power BI communication layer, and business value. | H1/H2/H3 docs; Power BI docs | None | Keep caveats visible. | 0.75-1 page | Draft after main sections. |
| References | Only artifact links. | Convert to APA references. | Dataset source; method/tool docs; proposal sources | None | Do not invent missing metadata. | 2-3 pages | Needs source details. |
| Appendices | Artifact links exist. | Add appendix plan and references to code, data dictionary, validators, metadata, dashboard serving docs. | `report/final_artifact_index.md`; `report/final_validation_summary.md`; model metadata | Appendix inventory | Mark generated dashboard screenshot appendix later. | As needed | Draft now with update points. |

## 4. Required Tables and Figures

| Table/Figure number | Proposed title | Source artifact path | Report section | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Table 1 | DataCo Dataset Summary | `docs/data_source_verification.md` | Data Source and Governance | Available | Include rows, columns, source, DOI, metadata file, license. |
| Figure 1 | Medallion and Project Workflow Architecture | `docs/medallion_structure.md`; `docs/project_orchestrator.md` | Data Engineering and Cloud Implementation | Needs formatting | Can be a report-created diagram/table based on existing docs. |
| Table 2 | Feature Availability and Leakage-Control Summary | `docs/feature_availability_map.md`; `data/references/feature_availability_map.csv`; `docs/leakage_control_plan.md` | Leakage-Control Methodology | Available, needs formatting | Summarize allowed, forbidden, review categories. |
| Table 3 | Chronological Split Policy Summary | `docs/chronological_split_policy.md`; `data/references/chronological_split_policy.csv`; `data/references/ao1_chronological_partition_summary.csv`; `data/references/ao2_chronological_partition_summary.csv` | Leakage-Control Methodology | Available | Include 80/20 policy and objective-specific row counts. |
| Table 4 | AO1 Model Validation Comparison | `report/tables/ao1_model_validation_comparison.csv` | AO1 Results | Available | Use XGBoost vs Logistic metrics. |
| Table 5 | AO1 Operating Threshold Recommendation | `report/tables/ao1_decision_threshold_recommendation.md`; `data/references/ao1_decision_threshold_policy.csv` | AO1 Results | Available | Include threshold 0.35 and validation trade-off. |
| Figure 2 | AO1 SHAP Top Features | `report/figures/ao1_shap_top_features.png` | AO1 Results | Available | Include caveat about associations, not causality. |
| Table 6 | AO2 Model Validation Comparison | `report/tables/ao2_model_validation_comparison.csv`; `report/tables/ao2_results_h2_summary.csv` | AO2 Results | Available | Use RMSE, MAE, R2, residual metrics. |
| Table 7 | AO2 Residual Diagnostics | `report/tables/ao2_residual_diagnostics_by_model.csv` | AO2 Results | Available | Include compression and residual caveats. |
| Figure 3 | AO2 SHAP Top Features | `report/figures/modeling/ao2_shap_top_features.png` | AO2 Results | Available | Tie to accepted-with-caution target audit. |
| Table 8 | AO2 Target-Reconstruction Audit Summary | `report/tables/ao2_target_reconstruction_audit_findings.md`; `models/ao2_profitability/target_reconstruction_audit/ao2_target_reconstruction_audit_metadata.json` | AO2 Results / Methodology | Available | Summarize `accepted_with_caution`. |
| Table 9 | AO3 Risk-Margin Matrix | `docs/ao3_risk_margin_matrix.md`; `data/references/ao3_risk_margin_matrix_policy.csv` | AO3 Results | Available | Present risk cutoff 0.35 and margin cutoff 0.0. |
| Table 10 | AO3 Segment Summary | `data/references/ao3_segment_summary.csv`; `data/references/ao3_risk_margin_benchmark_segment_summary.csv` | AO3 Results | Available | Use held-out scored population count of 34,467 where supported. |
| Table 11 | AO3 Benchmark / Crosswalk Evidence | `data/references/ao3_risk_margin_benchmark_crosswalk.csv`; `data/references/ao3_risk_margin_benchmark_insights.csv` | AO3 Results | Available | Supports H3 against risk-only and margin-only views. |
| Table 12 | Power BI Serving-Layer Table Inventory | `docs/powerbi_databricks_serving_layer.md`; `dashboard/powerbi_semantic_model.md`; `src/dashboard/register_powerbi_databricks_tables.py` | Power BI Dashboard | Available | Include `powerbi_*` tables and semantic names. |
| Figure 4 | Power BI First Dashboard Page Screenshot | [TO UPDATE AFTER DASHBOARD FINALIZATION] | Power BI Dashboard | Needs dashboard update | First page reportedly published in PR #141; no repo screenshot found during this review. |
| Table 13 | Operational Recommendation Matrix | `data/references/ao3_operational_recommendation_matrix.csv`; `docs/ao3_operational_recommendations.md` | Recommendations | Available | Tie recommendations directly to AO3 segments. |
| Table 14 | Validation Summary by Environment | `report/final_validation_summary.md`; `docs/TESTING.md` | Reproducibility / Appendix | Available | Separate local and Databricks validators. |

## 5. Advanced Analytics Methods Coverage

| Method name | Project objective | Why it was used | Input data | Output | Validation/diagnostic evidence | Report section |
| --- | --- | --- | --- | --- | --- | --- |
| Logistic Regression baseline | AO1 | Interpretable classification baseline for late-delivery prediction. | AO1 Gold chronological training/validation data. | Validation predictions and baseline metrics. | `docs/ao1_logistic_regression_baseline.md`; `report/tables/ao1_logistic_regression_validation_metrics.csv` | Analytical Methods; AO1 Results |
| XGBoost classification | AO1 | Primary nonlinear classifier expected to improve discrimination and recall. | AO1 leakage-safe pre-shipment features. | Late-delivery probability and high-risk flag. | `docs/ao1_xgboost_classifier.md`; `report/tables/ao1_xgboost_classifier_validation_metrics.csv`; `docs/ao1_results_h1_validation.md` | Analytical Methods; AO1 Results |
| Ridge Regression baseline | AO2 | Regularized linear baseline for profitability estimation. | AO2 Gold chronological training/validation data. | Predicted order profit baseline. | `docs/ao2_ridge_baseline.md`; `report/tables/ao2_ridge_validation_metrics.csv` | Analytical Methods; AO2 Results |
| Gradient Boosting / XGBoost regression | AO2 | Primary nonlinear profitability model expected to reduce RMSE and MAE. | AO2 pre-dispatch profitability features. | Predicted order profit. | `docs/ao2_gradient_boosting_regressor.md`; `report/tables/ao2_gradient_boosting_validation_metrics.csv`; `docs/ao2_results_h2.md` | Analytical Methods; AO2 Results |
| SHAP explainability | AO1 and AO2 | Explains model driver patterns and supports leakage review. | Validation model outputs and transformed features. | SHAP feature importance and driver summaries. | `docs/ao1_shap_explainability.md`; `docs/ao2_shap_explainability.md`; SHAP figures | Analytical Methods; AO1/AO2 Results |
| Risk-margin segmentation framework | AO3 | Combines predicted risk and predicted profit/margin into operational action groups. | AO1/AO2 held-out score table. | AO3 priority segment. | `docs/ao3_methodology_and_results.md`; `data/references/ao3_risk_margin_benchmark_*` | Analytical Methods; AO3 Results; Recommendations |
| Optional K-means extension | AO3 exploratory extension | Tested whether unsupervised clusters add value beyond the 2x2 matrix. | AO3 prediction signals only. | Cluster profiles and quality metrics. | `docs/ao3_kmeans_extension.md`; `report/tables/ao3_kmeans_quality_metrics.csv` | Analytical Methods; AO3 Results appendix |

Final recommendation for K-means: do not adopt as the main AO3 method. Existing artifacts state that K-means mostly duplicates the governed AO3 2x2 risk-margin matrix and may confuse the H3 story if promoted to the main dashboard or recommendation layer.

## 6. Hypothesis Evidence Map

| Hypothesis | Exact conclusion for final report | Primary metric evidence | Source artifact path | Caveats | Final report section |
| --- | --- | --- | --- | --- | --- |
| H1 | H1 is supported on validation evidence: XGBoost outperformed Logistic Regression for AO1 late-delivery prediction, including ROC-AUC and recall. | XGBoost ROC-AUC 0.7753 vs Logistic Regression 0.7426; XGBoost recall at 0.50 0.5840 vs Logistic Regression 0.5645. | `docs/ao1_results_h1_validation.md`; `report/tables/ao1_model_validation_comparison.csv` | Validation-stage evidence; final-test performance not claimed; SHAP associations are not causal; threshold recall remains moderate. | AO1 Results |
| H2 | H2 is supported on validation evidence, with modest improvement: Gradient Boosting improved RMSE and MAE over Ridge. | Gradient Boosting RMSE 95.6203 vs Ridge 96.8276; MAE 52.6463 vs 54.2191; R2 0.0118 vs -0.0133. | `docs/ao2_results_h2.md`; `report/tables/ao2_results_h2_summary.csv`; `report/tables/ao2_model_validation_comparison.csv` | Validation-stage evidence; modest improvement; low R2; compressed predictions; AO2 target reconstruction accepted with caution. | AO2 Results |
| H3 | H3 is supported by AO3 segmentation and benchmark evidence with caveats: the combined risk-margin framework identifies operational groups not fully evident from risk-only or margin-only views. | AO3 benchmark population 34,467 held-out scored orders; margin-only would mix `protect_high_value_at_risk` and `preserve_service`; risk-only would mix high-risk segments with different margin profiles. | `docs/ao3_methodology_and_results.md`; `data/references/ao3_risk_margin_benchmark_segment_summary.csv`; `data/references/ao3_risk_margin_benchmark_crosswalk.csv` | No causal claim; no realized intervention outcome; segment proportions depend on one scored population and selected thresholds. | AO3 Results; Recommendations |

## 7. Dashboard Section Plan

Power BI is the official visualization tool for the final report. The dashboard section should not present Databricks native dashboards, Databricks AI/BI, or a Databricks dashboard alternative as the planned deliverable.

Recommended dashboard section subsections:

1. **Dashboard purpose.** Explain that Power BI communicates AO1 risk, AO2 profitability, and AO3 prioritization to managers.
2. **Chosen architecture.** State that the direct Power BI connection to Azure Databricks serving-layer tables is the chosen architecture.
3. **Serving-layer implementation.** Summarize `src/dashboard/register_powerbi_databricks_tables.py`, which publishes governed `powerbi_*` tables and `powerbi_serving_layer_manifest`.
4. **Connection status.** State that the direct Power BI connection to Azure Databricks serving-layer tables worked, based on the team update.
5. **Dashboard progress.** State that the first Power BI dashboard page has been published in PR #141, based on the team update. Repository artifact for PR #141 was not found during this review, so screenshots/details should be added later.
6. **`.pbix` policy.** Use documented policy: `.pbix` files are ignored by Git and should be submitted outside Git or rebuilt locally from `dashboard/powerbi_semantic_model.md` and `dashboard/powerbi_measures.dax`.
7. **Serving tables.** Include the table inventory from `docs/powerbi_databricks_serving_layer.md`, especially:
   - `powerbi_ao3_order_segments`
   - `powerbi_ao1_ao2_test_scores`
   - `powerbi_ao1_decision_threshold_policy`
   - `powerbi_ao1_ao2_test_score_summary`
   - `powerbi_ao3_risk_margin_policy`
   - `powerbi_ao3_segment_summary`
   - `powerbi_ao3_benchmark_segment_summary`
   - `powerbi_ao3_benchmark_insights`
   - `powerbi_ao3_operational_recommendations`
   - `powerbi_ao1_model_validation`
   - `powerbi_ao1_threshold_tradeoff`
   - `powerbi_ao1_confusion_by_threshold`
   - `powerbi_ao2_model_validation`
   - `powerbi_ao2_evaluation_metrics`
   - `powerbi_serving_layer_manifest`
8. **Dashboard interpretation.** Explain how dashboard pages support:
   - AO1 late-delivery risk interpretation;
   - AO2 profitability interpretation;
   - AO3 risk-margin prioritization and operational action;
   - governance through validation metrics and manifest/serving-layer checks.

Required update markers:

- `[TO UPDATE AFTER DASHBOARD FINALIZATION] Add screenshot and title of first Power BI page from PR #141.`
- `[TO UPDATE AFTER DASHBOARD FINALIZATION] Add final page inventory and any remaining dashboard polish notes.`
- `[TO UPDATE AFTER DASHBOARD FINALIZATION] Confirm whether `.pbix` is submitted outside Git, rebuilt from instructions, or attached through course submission tooling.`

## 8. Recommendations Section Plan

Structure the recommendations around AO3 because AO3 is the integrated decision-support layer.

| Recommendation category | Recommendation | Evidence link | Guardrail |
| --- | --- | --- | --- |
| Logistics prioritization | Use AO3 priority groups as the pre-dispatch triage view rather than risk-only or margin-only ranking. | `docs/ao3_methodology_and_results.md`; AO3 benchmark crosswalk | Decision support only; no causal intervention claim. |
| High-risk/high-margin order protection | Prioritize `protect_high_value_at_risk` for monitoring, exception handling, and targeted service protection. | `data/references/ao3_operational_recommendation_matrix.csv` | Avoid blanket costly expediting without business review. |
| High-risk/low-margin selective review | Use `expedite_selectively` as a controlled review queue before committing scarce expedited capacity. | AO3 segment summary and recommendation matrix | Segment is small in the benchmark; do not overgeneralize. |
| Pricing and profitability oversight | Monitor low-margin groups and AO2 residual limitations when interpreting profitability. | `docs/ao2_results_h2.md`; `docs/ao3_operational_recommendations.md` | AO2 predictive power is limited; avoid treating predictions as accounting truth. |
| Monitoring and governance | Recalibrate thresholds and review leakage/feature drift before future use. | `docs/leakage_control_plan.md`; `docs/chronological_split_policy.md`; `docs/TESTING.md` | Academic prototype, not production monitoring system. |
| Dashboard adoption and cadence | Use Power BI dashboard refreshes from Databricks serving tables for recurring managerial review. | `docs/powerbi_databricks_serving_layer.md`; `dashboard/powerbi_semantic_model.md` | Dashboard screenshots/details to update after finalization. |

## 9. Limitations and Future Research Plan

Include these limitations:

- DataCo is a secondary, public, anonymized, and partially synthetic dataset.
- The project does not establish causality.
- The project does not claim production deployment.
- No live operational intervention or A/B test was conducted.
- AO1 recall remains moderate at operationally manageable thresholds.
- AO1 SHAP patterns, especially shipping-mode and granular geography drivers, are associations and require cautious interpretation.
- AO2 has modest improvement, low R2, compressed predictions, residual limitations, and target-reconstruction caution.
- AO3 benchmark evidence is decision-layer evidence, not realized delivery or profit outcome evidence.
- AO3 thresholds may require recalibration for future periods or different business contexts.
- Power BI dashboard details may still need final screenshot/page updates.

Future research:

- Add external operational variables such as weather, carrier performance, holidays, disruption indicators, fulfillment-center capacity, and route constraints.
- Evaluate realized intervention outcomes through a controlled pilot or quasi-experimental study.
- Recalibrate AO1 threshold and AO3 cutoffs over time.
- Test model stability across future time windows.
- Add production monitoring for drift, fairness, segment stability, and dashboard data freshness.
- Expand Power BI dashboard pages after managerial feedback.

## 10. References and APA Gaps

Needed APA references:

| Reference area | Known source or artifact | APA gap |
| --- | --- | --- |
| DataCo dataset | Mendeley Data DOI `10.17632/8gx2fvg2k6.5`; `docs/data_source_verification.md` | Need final APA dataset citation formatting. |
| XGBoost | XGBoost library/model documentation or original paper | [NEEDS SOURCE DETAILS] |
| SHAP | SHAP method documentation or Lundberg and Lee paper | [NEEDS SOURCE DETAILS] |
| scikit-learn | scikit-learn documentation for Logistic Regression, Ridge, metrics, K-means if cited | [NEEDS SOURCE DETAILS] |
| Databricks / Spark / Delta | Databricks, Apache Spark, Delta Lake documentation if cited as platform | [NEEDS SOURCE DETAILS] |
| Power BI / Azure Databricks connector | Microsoft Power BI and Azure Databricks connector documentation | [NEEDS SOURCE DETAILS] |
| Supply chain analytics literature | Proposal or course literature if already used | [NEEDS SOURCE DETAILS] |
| Predictive analytics / decision support | Academic sources for predictive decision-support framing | [NEEDS SOURCE DETAILS] |
| Responsible AI / explainability | SHAP and model-governance sources if used in ethics section | [NEEDS SOURCE DETAILS] |

Do not invent author names, titles, years, journal details, or URLs. Add only verified citations during final drafting.

## 11. Appendices Plan

Recommended appendices:

- Appendix A: Data dictionary and cleaned dataset schema.
  - Sources: `docs/silver_schema_data_dictionary.md`, `data/references/silver_schema_data_dictionary.csv`.
- Appendix B: Code repository and script index.
  - Sources: `report/final_artifact_index.md`, `docs/project_orchestrator.md`.
- Appendix C: Validation summary.
  - Sources: `report/final_validation_summary.md`, `docs/TESTING.md`.
- Appendix D: Leakage-control and feature availability references.
  - Sources: `docs/leakage_control_plan.md`, `docs/feature_availability_map.md`.
- Appendix E: Model metadata and metrics.
  - Sources: `models/ao1_late_delivery/`, `models/ao2_profitability/`, `models/ao3_integration/`, `report/tables/`.
- Appendix F: Power BI serving-layer documentation.
  - Sources: `docs/powerbi_databricks_serving_layer.md`, `dashboard/powerbi_semantic_model.md`, `dashboard/powerbi_measures.dax`.
- Appendix G: Additional figures and tables.
  - Sources: `report/figures/`, `report/tables/`.
- Appendix H: AI/tooling usage note, if required by course policy.
  - Source: `report/final_capstone_report.md` AI/tooling note, expanded as needed.

## 12. Final Drafting Plan

Sections that can be drafted immediately:

1. Title Page.
2. Abstract / Executive Summary, with dashboard sentence adjusted to official Power BI direction.
3. Introduction and Business Problem.
4. Research Question, Objectives, and Hypotheses.
5. Data Source and Data Governance.
6. Data Engineering and Cloud Implementation.
7. Leakage-Control and Chronological Split Methodology.
8. Analytical Methods.
9. AO1 Results.
10. AO2 Results.
11. AO3 Results.
12. Recommendations.
13. Limitations, Ethics, Responsible Use.
14. Future Research.
15. Conclusion.
16. Appendices based on existing artifacts.

Sections needing later dashboard updates:

- Power BI Dashboard and Visualization Layer: draft now, then insert PR #141 screenshot/page details after dashboard finalization.
- References: add verified APA metadata before submission.

Metrics to recheck before final submission:

- AO1 model comparison metrics and threshold table.
- AO2 model comparison metrics and residual diagnostics.
- AO2 target-reconstruction audit status.
- AO3 segment counts, benchmark crosswalk, and operational recommendation matrix.
- Power BI serving-layer table inventory and manifest row counts if included in the final report.
- Final dashboard screenshot/page title from PR #141 or final dashboard PR.

Recommended writing order:

1. Methods and data sections first because they define validity boundaries.
2. AO1, AO2, and AO3 results next, using existing report-ready docs.
3. Dashboard section after methods/results so the visuals are clearly downstream of governed artifacts.
4. Recommendations, limitations, future research, and conclusion.
5. Abstract/executive summary last.
6. References and appendices last after citation details are verified.

## 13. Risks Before Final Submission

| Risk | Classification | Why it matters | Mitigation |
| --- | --- | --- | --- |
| APA references are incomplete or unverified. | Major | The assignment expects APA-style reporting and sources. | Collect verified method, tool, dataset, and supply-chain literature citations. |
| Existing navigation docs still mention a Databricks dashboard alternative. | Major | This conflicts with the official Power BI direction. | Update final-facing docs before submission or ensure the final report overrides them clearly. |
| Dashboard screenshots/page details from PR #141 are not in the repo. | Minor | The report can proceed, but final dashboard section needs visual evidence. | Add `[TO UPDATE AFTER DASHBOARD FINALIZATION]` placeholders now, then insert final screenshot/details. |
| Power BI serving-layer manifest row counts are not cited from a final run. | Minor | Useful for dashboard validation but not core analytical evidence. | Add manifest details only if available and verified. |
| AO1/AO2 final-test wording is overstated. | Major | Would weaken methodological rigor. | Keep H1/H2 as validation evidence unless a final-test artifact explicitly supports stronger wording. |
| AO2 profitability claims are too strong. | Major | AO2 has modest improvement and target-reconstruction caution. | Preserve low R2, compressed prediction, and accepted-with-caution caveats. |
| AO3 recommendations imply causal impact. | Major | AO3 is a decision-layer benchmark, not an intervention study. | State recommendations as triage guidance, not proven outcome improvement. |
| Minor dashboard polish remains. | Minor | The pasted instructions state this is not a blocker for drafting. | Draft dashboard section now and update details later. |
| Production deployment is implied. | Major | Project is an academic prototype. | Use prototype and decision-support language throughout. |
| Future external data is discussed as if already used. | Minor | Could confuse scope. | Keep weather/carrier/disruption variables in future research only. |

Dashboard interpretation for final drafting: Power BI is the official dashboard direction, the direct Power BI connection to Azure Databricks serving-layer tables is the chosen architecture, and remaining dashboard details are update points rather than blockers.
