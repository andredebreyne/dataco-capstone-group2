# Final Selected APA Reference Set

## Purpose

This file refines the final APA reference pool for `report/final_capstone_report_expanded_draft.md`. It uses the checked-in APA planning files and the provided `apa_reference_usefulness_tracker.md` source pool. It does not edit the expanded draft, remove citation markers, add fabricated metadata, or change analytical conclusions.

Only the DataCo dataset currently has complete APA metadata in repository evidence. All other academic, tool, and documentation references remain incomplete or missing until their source metadata is manually verified.

## Source Pool Inspected

- `report/final_capstone_report_expanded_draft.md`
- `report/final_apa_reference_map.md`
- `report/final_apa_reference_inventory.csv`
- `docs/proposal/proposal_summary.md`
- `C:/Users/bruno/OneDrive - GUSCanada/data_analytics_MSc/Capstone/DataCo/Artigos/apa_reference_usefulness_tracker.md`
- External `Artigos` folder reference files. No reference PDFs were found inside this repository. The external folder contains additional files, including a bibliography document and a data-leakage/time-series PDF, but those files do not provide complete APA metadata for the selected report references.

## Classification Rules

| Slot type | Meaning |
| --- | --- |
| `fixed_source` | A known source from the already-used source pool. It can be cited only after complete APA metadata is verified, except DataCo, which is already complete. |
| `replaceable_topic_slot` | A needed topic citation where the current pool does not provide a fully verified source. The final text can either add a verified source or be rewritten to avoid the unsupported claim. |
| `official_documentation_slot` | A needed software, platform, or connector citation that must come from official documentation or a canonical source. |
| `optional_remove_if_not_used` | A source that should not appear in the final References section unless the final report directly discusses that concept. |

## Core Academic / Literature Sources

These are the main academic sources to use if complete metadata is collected.

| Citation key | Source category | Slot type | Concept supported | Final report section | Metadata status | Missing fields | Should appear in final References? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dataco_dataset_constante_2019` | Dataset | `fixed_source` | DataCo Smart Supply Chain dataset source | Data source and pipeline overview | `complete` | None | Yes | Use the checked APA entry from `docs/data_source_verification.md`. |
| `baryannis_2019_supply_chain_risk_ml` | Core literature | `fixed_source` | Supply-chain risk prediction and interpretability trade-offs | Business problem; AO1; explainability | `partial_needs_metadata` | Author initials, venue, volume/issue/pages, DOI or URL | Yes, after metadata verification | Strong core source for risk prediction and interpretability. |
| `toorajipour_2021_ai_scm_review` | Core literature | `fixed_source` | AI in supply-chain management review context | Business problem and literature context | `partial_needs_metadata` | Author initials, journal, volume/issue/pages, DOI or URL | Yes, after metadata verification | Use as broad AI-in-SCM background. |
| `ni_xiao_lim_2020_ml_scm_review` | Core literature | `fixed_source` | ML research trends in supply-chain management | Literature context | `partial_needs_metadata` | Author initials, journal, volume/issue/pages, DOI or URL | Yes, after metadata verification if used with or instead of Toorajipour | Tracker notes the PDF is image-based; verify detailed claims directly. |
| `katangoori_2026_dataco_supply_chain_optimization` | Core literature | `fixed_source` | DataCo risk, profit, segmentation, and leakage-aware comparison | AO1/AO2/AO3 literature context | `partial_needs_metadata` | Full publication metadata, DOI or URL, source-quality review | Yes, after metadata verification | Closest applied DataCo comparison if metadata/source quality are confirmed. |
| `ahmed_2025_interpretable_supply_chain_forecasting` | Core literature | `fixed_source` | DataCo late delivery, shipping-time forecasting, and SHAP | AO1 and explainability context | `partial_needs_metadata` | Author initials, venue, volume/issue/pages, DOI or URL | Yes, after metadata verification if DataCo late-delivery precedent is discussed | Useful applied DataCo/SHAP source. |
| `hastie_tibshirani_friedman_2009_esl` | Methodology literature | `fixed_source` | Statistical learning, regression/classification, boosting, validation | AO1/AO2 methods | `partial_needs_metadata` | Author initials, edition, publisher, URL if online version is cited | Yes, after metadata verification | Core methods reference, not supply-chain-specific. |
| `lundberg_lee_2017_shap` | Explainability literature | `fixed_source` | SHAP method and model interpretation | SHAP/explainability; responsible-use caveats | `partial_needs_metadata` | Author initials, proceedings or venue, DOI or URL | Yes, after metadata verification | Foundational SHAP source. |
| `zaharia_2016_apache_spark` | Infrastructure literature | `fixed_source` | Apache Spark big-data processing | Data engineering and reproducibility | `partial_needs_metadata` | Full author list, venue, DOI or URL | Yes, after metadata verification if Spark is cited externally | Supports infrastructure only, not model validity. |
| `armbrust_2020_delta_lake` | Infrastructure literature | `fixed_source` | Delta Lake storage and reliable lakehouse tables | Data engineering and reproducibility | `partial_needs_metadata` | Full author list, venue, DOI or URL | Yes, after metadata verification if Delta Lake is cited externally | Supports storage/reproducibility only. |

## Useful But Optional Sources

These can be used if the final report keeps the relevant claims and metadata is verified.

| Citation key | Source category | Slot type | Concept supported | Final report section | Metadata status | Missing fields | Should appear in final References? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `gopal_2024_bda_supply_chain_performance` | Optional literature | `fixed_source` | Big-data analytics and supply-chain performance | Business value and operational interpretation | `partial_needs_metadata` | Full publication metadata, DOI or URL | Conditional | Useful for business-performance framing, not model choice. |
| `douaioui_2024_late_delivery_resilience` | Optional literature | `fixed_source` | Late-delivery prediction and resilience | AO1 literature context | `partial_needs_metadata` | Full publication metadata, DOI or URL | Conditional | Use if final report needs an additional advanced late-delivery study. |
| `liang_2025_supply_chain_risk_decision_trees` | Optional literature | `fixed_source` | DataCo decision-tree risk prediction and interpretability | AO1 literature context | `partial_needs_metadata` | Full publication metadata, DOI or URL | Conditional | Use if final report discusses interpretable decision-tree DataCo precedent. |
| `ashraf_2025_customer_segmentation` | Optional literature | `optional_remove_if_not_used` | Segmentation/clustering context | AO3 segmentation caveat or K-means extension | `partial_needs_metadata` | Full publication metadata, DOI or URL | No, unless segmentation literature is directly needed | Marketing-oriented; not central to risk-margin framework. |
| `ivanov_2021_digital_supply_chain_twins` | Optional literature | `optional_remove_if_not_used` | Digital twins, disruption visibility, resilience | Limitations or decision-support context | `partial_needs_metadata` | Correct year, full title, venue, DOI or URL | No, unless digital twins/resilience framing remains | Resolve 2019/2021 year ambiguity before use. |
| `chatrath_2026_ai_supply_chain_logistics` | Optional literature | `optional_remove_if_not_used` | Broad AI in supply chain and logistics | Background only | `partial_needs_metadata` | Full publication metadata, DOI or URL | No, unless broad background needs one more source | Use carefully; tracker marks it as broad background. |

## Sources To Avoid Unless The Final Text Changes

| Citation key | Source category | Slot type | Concept supported | Final report section | Metadata status | Missing fields | Should appear in final References? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `chawla_2002_smote` | Methodology literature | `optional_remove_if_not_used` | SMOTE and class imbalance | AO1 class imbalance only if discussed | `not_needed_remove_marker` | Full metadata only needed if SMOTE is discussed | No | Current AO1 documentation says SMOTE is not used. Do not include unless class imbalance handling or SMOTE is explicitly discussed. |
| `python_pandas_numpy_matplotlib_reference` | Tool/package slot | `optional_remove_if_not_used` | Python and common data-analysis packages | AI/tooling note only if substantively discussed | `not_needed_remove_marker` | Official docs or package citations only if final text requires them | No | Do not cite routine package use unless final report makes package-specific claims. |

## Still Missing Official / Tool References

These should remain as documentation slots until official or canonical metadata is collected.

| Citation key | Source category | Slot type | Concept supported | Final report section | Metadata status | Missing fields | Should appear in final References? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `xgboost_documentation_3_2_0` | Tool documentation | `official_documentation_slot` | XGBoost documentation release 3.2.0 / current docs page for implementation/package support | AO1/AO2 modeling methods | `reference_needed` | Documentation page title, organization, URL, retrieval date if needed | Yes, if XGBoost implementation is named | Current repo runtime records `xgboost==2.0.3`; the selected citation source is XGBoost documentation release 3.2.0 / current docs page. |
| `chen_guestrin_2016_xgboost_method` | Academic method slot | `replaceable_topic_slot` | Canonical XGBoost academic method reference if broad methodology is discussed | AO1/AO2 modeling methods | `reference_needed` | Full paper title, venue, publisher/proceedings, DOI or URL | Conditional | Use only if the final report discusses XGBoost methodology beyond package implementation. Do not invent metadata. |
| `scikit_learn_ridge_documentation` | Tool documentation | `official_documentation_slot` | scikit-learn Ridge documentation for Ridge baseline implementation | AO2 baseline implementation | `reference_needed` | Ridge documentation page title, URL, retrieval date if needed | Conditional | Use only if the final report discusses the Ridge baseline implementation. |
| `scikit_learn_broad_citation_needed` | Academic/tool slot | `replaceable_topic_slot` | scikit-learn broad implementation library citation | AO1/AO2/AO3 methods | `reference_needed` | scikit-learn paper or canonical citation metadata, DOI or URL | Conditional | Use only if final text cites scikit-learn broadly as the implementation library. |
| `databricks_official_reference` | Platform documentation | `official_documentation_slot` | Databricks platform and serving-layer context | Reproducibility and dashboard architecture | `reference_needed` | Organization, page title, year/date, URL, retrieval date if needed | Yes, if Databricks platform behavior is cited | Databricks native dashboards / AI/BI dashboards are not the planned final dashboard deliverable. |
| `microsoft_powerbi_official_reference` | Tool documentation | `official_documentation_slot` | Selected Power BI dashboard direction and Power BI tooling | Dashboard status and tooling | `reference_needed` | Microsoft page title, date, URL, retrieval date if needed | Yes, if Power BI mechanics are cited | Power BI is the official/selected dashboard direction; PR #141 contains the first dashboard page. |
| `microsoft_learn_powerbi_azure_databricks` | Connector documentation | `official_documentation_slot` | Microsoft Learn "Power BI with Azure Databricks" for Power BI Desktop connecting to Azure Databricks clusters and SQL warehouses | Dashboard architecture | `reference_needed` | Microsoft Learn page date, URL, retrieval date if needed | Yes, if connector architecture is cited | Primary official source for the selected direct Power BI connection to Azure Databricks serving-layer tables. |
| `databricks_power_platform_blog_optional` | Optional tool source | `optional_remove_if_not_used` | Databricks Power Platform connector blog | Dashboard or Power Platform context only if discussed | `not_needed_remove_marker` | Blog title, date, URL only if used | No, unless broader Power Platform integration is discussed | Do not use as the primary Power BI dashboard source; it concerns Power Apps, Power Automate, and Copilot Studio. |
| `liu_chen_zheng_feng_2022_leakage_suppression` | Methodology literature | `fixed_source` | Leakage suppression and falsely high evaluation risk from future/test information | Leakage-control and chronological split policy | `partial_needs_metadata` | Venue or publisher, volume/issue/pages if applicable, DOI or URL | Yes, after metadata verification | Replacement for generic leakage slot. Limitation: time-series leakage source, not supply-chain-specific. |
| `responsible_ai_governance_reference_needed` | Governance topic slot | `replaceable_topic_slot` | Responsible AI, model governance, limitations, or explainability governance | Ethical/responsible-use considerations | `reference_needed` | Author(s), year, title, venue/page, DOI or URL | Conditional | Use only if final text keeps broad responsible-AI/governance claims. Lundberg and Lee can support SHAP only, not broad governance. |

## Practical Core Set For Final Report

Use this core set if metadata is collected:

1. `dataco_dataset_constante_2019`
2. `baryannis_2019_supply_chain_risk_ml`
3. `toorajipour_2021_ai_scm_review` and/or `ni_xiao_lim_2020_ml_scm_review`
4. `katangoori_2026_dataco_supply_chain_optimization` and/or `ahmed_2025_interpretable_supply_chain_forecasting`
5. `hastie_tibshirani_friedman_2009_esl`
6. `lundberg_lee_2017_shap`
7. `zaharia_2016_apache_spark`
8. `armbrust_2020_delta_lake`
9. `xgboost_documentation_3_2_0`
10. `databricks_official_reference`
11. `microsoft_powerbi_official_reference`
12. `microsoft_learn_powerbi_azure_databricks`
13. `liu_chen_zheng_feng_2022_leakage_suppression`, unless the leakage definition is rewritten to cite only internal project controls.

## Marker Replacement Plan

| Expanded-draft marker | Replacement key(s) | Action |
| --- | --- | --- |
| `[NEEDS APA SOURCE DETAILS: predictive analytics in supply chain management]` | `toorajipour_2021_ai_scm_review`; `ni_xiao_lim_2020_ml_scm_review`; optionally `gopal_2024_bda_supply_chain_performance` | Replace after metadata verification. |
| `[NEEDS APA SOURCE DETAILS: machine learning for delivery risk and logistics prediction]` | `baryannis_2019_supply_chain_risk_ml`; `katangoori_2026_dataco_supply_chain_optimization`; optionally `ahmed_2025_interpretable_supply_chain_forecasting`, `douaioui_2024_late_delivery_resilience`, or `liang_2025_supply_chain_risk_decision_trees` | Replace after metadata verification; use optional studies only if final text discusses DataCo/late-delivery precedent. |
| `[NEEDS APA SOURCE DETAILS: profitability modeling and regression analytics]` | `hastie_tibshirani_friedman_2009_esl`; optionally `katangoori_2026_dataco_supply_chain_optimization` | Replace after metadata verification; rewrite any broad profitability-literature claim if no specific source is verified. |
| `[NEEDS APA SOURCE DETAILS: data leakage in predictive modeling]` | `liu_chen_zheng_feng_2022_leakage_suppression`; optionally `katangoori_2026_dataco_supply_chain_optimization` for DataCo-specific leakage | Replace after Liu et al. (2022) metadata is verified, or rewrite sentence to rely on internal leakage-control artifacts only. Note limitation: time-series leakage source, not supply-chain-specific. |
| `[NEEDS APA SOURCE DETAILS: SHAP and explainable machine learning]` | `lundberg_lee_2017_shap`; optionally `ahmed_2025_interpretable_supply_chain_forecasting` | Replace after metadata verification. |
| `[NEEDS APA SOURCE DETAILS: segmentation and decision-support frameworks]` | `katangoori_2026_dataco_supply_chain_optimization`; optionally `ashraf_2025_customer_segmentation`; internal AO3 artifacts | Rewrite unsupported broad decision-support claims unless a direct source is verified. |
| `[NEEDS APA SOURCE DETAILS: business intelligence dashboards and analytics communication]` | `microsoft_powerbi_official_reference`; `microsoft_learn_powerbi_azure_databricks`; possible new BI communication source | Use Microsoft docs only for tooling/connector mechanics; rewrite broad analytics-communication claim unless a BI literature source is verified. |
| `[NEEDS APA SOURCE DETAILS: XGBoost original paper or official documentation]` | `xgboost_documentation_3_2_0`; optionally `chen_guestrin_2016_xgboost_method` for broader methodology | Use XGBoost documentation release 3.2.0 / current docs page after metadata is verified; add Chen and Guestrin (2016) only if full metadata is collected and broad XGBoost methodology is discussed. |
| `[NEEDS APA SOURCE DETAILS: SHAP original paper or official documentation]` | `lundberg_lee_2017_shap`; optionally `shap_package_reference` if package docs are cited | Replace after metadata verification. |
| `[NEEDS APA SOURCE DETAILS: scikit-learn documentation for Logistic Regression, Ridge Regression, metrics, and K-means]` | `scikit_learn_ridge_documentation`; optionally `scikit_learn_broad_citation_needed` | Use Ridge documentation only if Ridge baseline implementation is discussed; use broad scikit-learn citation only if the library is cited broadly; otherwise remove or narrow marker. |
| `[NEEDS APA SOURCE DETAILS: Apache Spark documentation if cited]` | `zaharia_2016_apache_spark`; optionally official Spark docs | Replace after metadata verification if Spark is cited externally. |
| `[NEEDS APA SOURCE DETAILS: Delta Lake documentation if cited]` | `armbrust_2020_delta_lake`; optionally official Delta Lake docs | Replace after metadata verification if Delta Lake is cited externally. |
| `[NEEDS APA SOURCE DETAILS: Databricks documentation if cited]` | `databricks_official_reference` | Keep pending until official Databricks metadata is verified; cite platform/serving-layer context only. |
| `[NEEDS APA SOURCE DETAILS: Microsoft Power BI Azure Databricks connector documentation if cited]` | `microsoft_learn_powerbi_azure_databricks`; `microsoft_powerbi_official_reference` | Use Microsoft Learn "Power BI with Azure Databricks" as the primary connector source after metadata is verified. Do not use the Databricks Power Platform connector blog unless broader Power Platform integration is discussed. |
| `[NEEDS APA SOURCE DETAILS: supply chain analytics literature used in the proposal or course materials]` | `toorajipour_2021_ai_scm_review`; `ni_xiao_lim_2020_ml_scm_review`; `baryannis_2019_supply_chain_risk_ml`; optionally `gopal_2024_bda_supply_chain_performance` | Replace with concise verified citation set. |
| `[NEEDS APA SOURCE DETAILS: predictive analytics and decision-support literature]` | `baryannis_2019_supply_chain_risk_ml`; `hastie_tibshirani_friedman_2009_esl`; optionally `ivanov_2021_digital_supply_chain_twins` only if resilience/visibility framing remains | Rewrite unsupported decision-support claim or keep pending until a direct source is verified. |
| `[NEEDS APA SOURCE DETAILS: responsible AI, model governance, or explainability literature]` | `responsible_ai_governance_reference_needed`; `lundberg_lee_2017_shap` for explainability only | Keep pending until governance source is verified, or rewrite around internal controls and SHAP caveats. |
