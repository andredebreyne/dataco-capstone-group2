# Final APA Reference Map

## Purpose

This document maps the external and internal sources needed to finish the APA references for `report/final_capstone_report_expanded_draft.md`. It is a cleanup guide only. It does not rewrite the expanded draft, remove citation placeholders, change analytical conclusions, or regenerate outputs. It records the finalized dashboard direction only for reference-cleanup and artifact-navigation purposes.

The companion inventory is `report/final_apa_reference_inventory.csv`. It provides row-level tracking for each citation placeholder, source candidate, tool reference, and internal project artifact.

## Current Reference Status

The expanded report draft currently contains 17 `[NEEDS APA SOURCE DETAILS]` markers. Each marker is represented in the CSV inventory with a `draft_marker_` or `draft_ref_` source key.

Current status from checked files and the proposal reference tracker:

| Status type | Current finding |
| --- | --- |
| Complete external APA references | The DataCo dataset citation is complete and supported by checked-in dataset verification evidence. |
| Partial literature references | The proposal tracker identifies useful sources, titles, and project relevance, but most entries still need full APA metadata before final insertion. |
| Tool and platform references | Package versions are documented for `xgboost`, `shap`, and `scikit-learn`; official APA-ready citations or documentation metadata still need verification. |
| Internal project artifacts | Key project artifacts can be linked directly in the report or appendix, but they are not substitutes for external academic references where the report makes literature claims. |
| Dashboard references | Power BI is the selected dashboard direction. The selected architecture is a direct Power BI connection to Azure Databricks serving-layer tables; PR #141 contains the first dashboard page. Final screenshots, page inventory, `.pbix` submission route if required, and serving-layer manifest details may still be added later. Databricks native dashboards / AI/BI dashboards are not the planned final dashboard deliverable. |

## References Already Available

### Complete Dataset Reference

The dataset reference is complete enough to use in the final APA reference list:

> Constante, F., Silva, F., & Pereira, A. (2019). *DataCo Smart Supply Chain for Big Data Analysis* (Version 5) [Data set]. Mendeley Data. https://doi.org/10.17632/8gx2fvg2k6.5

Supporting checked-in evidence:

- `docs/data_source_verification.md`
- `report/final_capstone_report_expanded_draft.md`

### Internal Project Artifacts

The following should be linked as internal project evidence rather than formatted as external APA literature:

| Internal artifact area | Suggested links |
| --- | --- |
| Final report and navigation | `report/final_capstone_report.md`; `report/final_artifact_index.md`; `report/final_validation_summary.md` |
| Dataset verification | `docs/data_source_verification.md` |
| Leakage and feature policy | `docs/leakage_control_plan.md`; `docs/leakage_conceptual_screening.md`; `docs/feature_availability_map.md` |
| Chronological split | `docs/chronological_split_policy.md`; `docs/ao1_chronological_partitions.md`; `docs/ao2_chronological_partitions.md` |
| AO1 evidence | `docs/ao1_results_h1_validation.md`; `report/tables/ao1_model_validation_comparison.csv`; `report/tables/ao1_shap_explainability_findings.md` |
| AO2 evidence | `docs/ao2_results_h2.md`; `docs/ao2_target_reconstruction_review.md`; `report/tables/ao2_model_validation_comparison.csv`; `report/tables/ao2_target_reconstruction_audit_findings.md` |
| AO3 evidence | `docs/ao3_methodology_and_results.md`; `docs/ao3_risk_margin_benchmark.md`; `docs/ao3_operational_recommendations.md` |
| Dashboard status | `dashboard/README.md`; `dashboard/powerbi_semantic_model.md`; `docs/powerbi_databricks_serving_layer.md` |
| Validation | `docs/TESTING.md`; `report/final_validation_summary.md` |

## References Requiring Missing Metadata

The proposal tracker at `C:/Users/bruno/OneDrive - GUSCanada/data_analytics_MSc/Capstone/DataCo/Artigos/apa_reference_usefulness_tracker.md` lists useful sources, but most entries are not yet APA-complete. The final report should only cite sources whose full details are verified.

| Candidate source | Current use in report | Metadata still needed |
| --- | --- | --- |
| Ahmed et al. (2025), deep learning/interpretable supply-chain forecasting | AO1 late-delivery context; SHAP in supply-chain forecasting | Full author initials, venue, DOI/URL |
| Armbrust et al. (2020), Delta Lake | Delta Lake platform support | Full author list, venue, DOI/URL |
| Ashraf et al. (2025), customer segmentation | AO3 segmentation context if relevant | Full publication metadata and relevance check |
| Baryannis et al. (2019), supply-chain risk prediction and interpretability | AO1 risk prediction and interpretability framing | Full author initials, venue, pages, DOI/URL |
| Chatrath (2026), AI in supply chain and logistics | Broad background if retained | Full publication metadata and source-quality review |
| Chawla et al. (2002), SMOTE | Not currently needed because AO1 documentation says SMOTE is not used | Only verify if final text discusses SMOTE as an alternative |
| Douaioui et al. (2024), late-delivery risk prediction | AO1 logistics-risk background | Full publication metadata and method-fit review |
| Gopal et al. (2024), big-data analytics and supply-chain performance | Business context | Full publication metadata |
| Hastie et al. (2009), statistical learning | General model-methodology support | Edition, publisher, URL if online |
| Ivanov et al. (2019/2021), digital supply-chain twins | Supply-chain visibility/resilience context | Correct year, full title, venue, DOI/URL |
| Katangoori (2026), DataCo optimization | DataCo comparison across risk, profit, segmentation, leakage | Full publication metadata and source-quality review |
| Liang (2025), decision trees for fraud and late delivery | AO1 late-delivery prediction background | Full publication metadata |
| Lundberg and Lee (2017), SHAP | Explainability method | Proceedings or publication details, DOI/URL |
| Ni et al. (2020), ML in supply-chain management review | Broad ML-in-SCM framing | Full journal details, pages, DOI/URL |
| Toorajipour et al. (2021), AI in SCM review | Broad AI-in-SCM framing | Full journal details, pages, DOI/URL |
| Zaharia et al. (2016), Apache Spark | Spark platform support | Full author list, venue, DOI/URL |

## Tool / Platform / Package References

These references should be included only when the final text directly cites the tool, platform, or package. Package versions found in the repo do not by themselves provide APA metadata.

| Tool or platform | Repo evidence | Citation status |
| --- | --- | --- |
| XGBoost | `requirements.txt` records `xgboost==2.0.3`; `docs/databricks_setup.md` records Databricks-stable use | Reference needed: verified paper or official documentation |
| SHAP | `requirements.txt` records `shap==0.44.1`; proposal tracker lists Lundberg and Lee (2017) | Partial: full SHAP paper metadata and/or official docs needed |
| scikit-learn | `requirements.txt` records `scikit-learn==1.3.2` | Reference needed: official docs or accepted citation |
| Apache Spark | `docs/databricks_setup.md` records Spark 3.5.0 preferred and Spark 3.4.1 fallback | Partial: Zaharia et al. (2016) metadata or official docs needed |
| Delta Lake | Pipeline docs use Delta terminology | Partial: Armbrust et al. (2020) metadata or official docs needed |
| Databricks | `docs/databricks_setup.md` documents Community Edition setup | Reference needed if platform behavior is externally cited |
| Microsoft Power BI | `dashboard/README.md` and `dashboard/powerbi_semantic_model.md` document the selected Power BI dashboard path | Reference needed only if final report cites Power BI mechanics |
| Azure Databricks Power BI connector | `docs/powerbi_databricks_serving_layer.md` documents the selected direct Power BI connection to Azure Databricks serving-layer tables | Reference needed if connector instructions remain in final report |
| Python, pandas, NumPy, Matplotlib | `requirements.txt` includes Python package versions for NumPy and pandas, but no current expanded-draft marker requires these citations | Do not add unless final text makes package-specific claims |

## Dataset Reference

Use the complete DataCo citation above in the final reference list. The in-text citation can be `Constante et al. (2019)` when discussing the dataset source, dataset scale, public Mendeley Data source, version, DOI, and licensing evidence.

Recommended supporting internal artifact link: `docs/data_source_verification.md`.

## Literature / Academic Context References

Use a small, verified set of literature sources instead of listing every source from the proposal tracker. Suggested mapping:

| Report concept | Candidate citations to verify |
| --- | --- |
| Predictive analytics in supply-chain management | Toorajipour et al. (2021); Ni et al. (2020); Gopal et al. (2024); Baryannis et al. (2019) |
| Machine learning for delivery risk and logistics prediction | Baryannis et al. (2019); Ahmed et al. (2025); Douaioui et al. (2024); Liang (2025); Katangoori (2026) |
| Profitability modeling and regression analytics | Hastie et al. (2009); Katangoori (2026), if verified as supporting DataCo profit modeling |
| Data leakage in predictive modeling | Add a verified general leakage reference; Katangoori (2026) may support project-specific DataCo leakage concerns if verified |
| SHAP and explainable machine learning | Lundberg and Lee (2017); Ahmed et al. (2025), if verified |
| Segmentation and decision support | Ashraf et al. (2025); Katangoori (2026); add a stronger decision-support source if the final text keeps broad decision-support claims |
| Business intelligence dashboards and analytics communication | Add a verified BI or analytics-communication source; Microsoft docs only support tool mechanics |
| Responsible AI and model governance | Add a verified governance or responsible-AI source if the final ethical/responsible-use section makes external claims |

## In-Text Citation Plan

The expanded draft markers should be handled as follows:

| Draft marker | Proposed citation plan |
| --- | --- |
| Predictive analytics in supply chain management | Replace with a concise citation set from verified SCM analytics review/background sources. |
| Machine learning for delivery risk and logistics prediction | Cite verified supply-chain risk and delivery-risk sources; keep AO1 model claims tied to internal validation artifacts. |
| Profitability modeling and regression analytics | Cite methodology literature for regression/boosting and use internal AO2 target-policy artifacts for project-specific target-reconstruction controls. |
| Data leakage in predictive modeling | Add a verified external leakage source for the definition; cite internal leakage artifacts for project-specific implementation controls. |
| SHAP and explainable machine learning | Cite verified SHAP source; cite internal SHAP artifacts for project results. |
| Segmentation and decision-support frameworks | Cite verified segmentation/decision-support sources; cite AO3 artifacts for the actual 2x2 framework and K-means caveat. |
| Business intelligence dashboards and analytics communication | Add verified BI communication literature or narrow the text to project dashboard requirements and internal status docs. |
| XGBoost original paper or official documentation | Add verified XGBoost source if XGBoost implementation is cited. |
| SHAP original paper or official documentation | Add verified SHAP paper/docs. |
| scikit-learn documentation | Add verified scikit-learn docs if package-specific implementation is cited. |
| Apache Spark documentation | Use verified Spark source only if cited beyond internal setup evidence. |
| Delta Lake documentation | Use verified Delta Lake source only if cited beyond internal pipeline evidence. |
| Databricks documentation | Use official Databricks docs only if external platform behavior is cited. |
| Microsoft Power BI Azure Databricks connector documentation | Use official Microsoft docs only if connector mechanics remain in final text. |
| Supply-chain analytics literature | Select and verify the final literature set from the proposal tracker. |
| Predictive analytics and decision-support literature | Verify a source that directly supports decision-support claims. |
| Responsible AI, model governance, or explainability literature | Add a governance/responsible-AI source or narrow the section to internal governance controls plus SHAP. |

## Internal Project Artifact Citation Plan

For final report evidence, use internal links to point graders to the checked-in artifacts:

- Use `docs/ao1_results_h1_validation.md` and `report/tables/ao1_model_validation_comparison.csv` for H1 validation evidence.
- Use `docs/ao2_results_h2.md`, `docs/ao2_target_reconstruction_review.md`, and `report/tables/ao2_model_validation_comparison.csv` for H2 validation evidence and AO2 caution.
- Use `docs/ao3_methodology_and_results.md`, `docs/ao3_risk_margin_benchmark.md`, and `docs/ao3_operational_recommendations.md` for H3 evidence and caveats.
- Use `docs/leakage_control_plan.md`, `docs/leakage_conceptual_screening.md`, and `docs/feature_availability_map.md` for project-specific leakage controls.
- Use `dashboard/README.md`, `dashboard/powerbi_semantic_model.md`, and `docs/powerbi_databricks_serving_layer.md` to document the selected Power BI dashboard path, the selected Azure Databricks serving-layer connection, and remaining final screenshot, page-inventory, `.pbix` submission-route, or serving-layer manifest update points.

Internal project artifacts should appear in report artifact links or appendix-style navigation. They should not be formatted as peer-reviewed external references.

## Final Reference Cleanup Checklist

- Confirm the full APA metadata for every external source selected from the proposal tracker.
- Replace each `[NEEDS APA SOURCE DETAILS]` marker in `report/final_capstone_report_expanded_draft.md` with verified in-text citations or remove the marker if no citation is needed.
- Keep the DataCo dataset reference exactly aligned with `docs/data_source_verification.md`.
- Add XGBoost, SHAP, scikit-learn, Spark, Delta Lake, Databricks, and Microsoft documentation references only when the final text explicitly cites those tools or platforms.
- Do not add SMOTE to the final references unless the final report discusses it as an alternative or rejected method; AO1 documentation says SMOTE is not used.
- Keep dashboard wording honest: Power BI is the selected dashboard direction, the direct Azure Databricks serving-layer connection worked, PR #141 contains the first dashboard page, final screenshots/page inventory and `.pbix` submission details may still be added later, and Databricks native dashboards / AI/BI dashboards are not the planned final dashboard deliverable.
- Preserve analytical caveats: no causal claims, no realized intervention outcome, validation evidence only where applicable, and AO2 target-reconstruction accepted with caution.
- Run a final marker grep after updating the expanded draft in a later task.
