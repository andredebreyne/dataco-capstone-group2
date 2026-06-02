# Final Selected APA Reference Set

## Purpose

This file reduces `report/final_apa_reference_inventory.csv` into a focused reference set for the expanded final report. It does not edit `report/final_capstone_report_expanded_draft.md`, remove citation markers, add fabricated metadata, or change analytical conclusions.

Only the DataCo dataset currently has complete APA metadata in checked-in project evidence. All other external sources below must be verified before they are inserted into the final References section.

## Selected Final External References

### Dataset

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `dataco_dataset_constante_2019` | DataCo Smart Supply Chain dataset source, version, DOI, contributors, and license | Constante, F., Silva, F., & Pereira, A. (2019). DataCo Smart Supply Chain for Big Data Analysis (Version 5) [Data set]. Mendeley Data. https://doi.org/10.17632/8gx2fvg2k6.5 | None | `docs/data_source_verification.md`; `report/final_capstone_report_expanded_draft.md` | required |

### Supply Chain Analytics / AI In Supply Chains

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `baryannis_2019_supply_chain_risk_ml` | Supply-chain risk prediction and performance-interpretability tradeoff | Baryannis et al. (2019). Predicting supply chain risks using machine learning: The trade-off between performance and interpretability. [metadata incomplete] | Full author initials, venue, volume/issue/pages, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | required |
| `toorajipour_2021_ai_scm_review` | Broad AI-in-supply-chain-management context | Toorajipour et al. (2021). Artificial intelligence in supply chain management: A systematic literature review. [metadata incomplete] | Full author initials, journal, volume/issue/pages, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | useful |
| `ni_xiao_lim_2020_ml_scm_review` | Machine-learning trends in supply-chain management | Ni, Xiao, and Lim (2020). A systematic review of the research trends of machine learning in supply chain management. [metadata incomplete] | Full author initials, journal, volume/issue/pages, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | useful |
| `gopal_2024_bda_supply_chain_performance` | Big-data analytics and supply-chain performance context | Gopal et al. (2024). Impact of big data analytics on supply chain performance. [metadata incomplete] | Full publication metadata, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | optional |

### Predictive Modeling / Machine Learning Methodology

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `hastie_tibshirani_friedman_2009_esl` | General classification, regression, and boosting methodology | Hastie, Tibshirani, and Friedman (2009). The Elements of Statistical Learning. [metadata incomplete] | Edition, publisher, URL if online version is cited | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | required |
| `xgboost_package_reference` | XGBoost implementation and primary gradient boosting model reference | Repository records `xgboost==2.0.3`; no APA-ready source metadata is checked in | Official citation or documentation metadata, author or organization, year/date, title, version if documentation, DOI or URL | `requirements.txt`; `docs/databricks_setup.md`; `report/final_apa_reference_inventory.csv` | required |
| `scikit_learn_package_reference` | Logistic Regression, Ridge Regression, model metrics, and optional K-means implementation | Repository records `scikit-learn==1.3.2`; no APA-ready source metadata is checked in | Official citation or documentation metadata, author or organization, year/date, title, version, DOI or URL | `requirements.txt`; `docs/ao3_kmeans_extension.md`; `report/final_apa_reference_inventory.csv` | useful |
| `katangoori_2026_dataco_supply_chain_optimization` | DataCo-specific comparison across risk, profit, segmentation, and leakage | Katangoori (2026). An empirical analysis of data-driven supply chain optimization in retail and logistics. [metadata incomplete] | Full publication metadata, DOI or URL, source-quality review | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | useful |

### Leakage-Safe Modeling / Validation

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `general_leakage_reference_needed` | General definition of data leakage and prediction-time feature availability | No external source metadata is checked in; the inventory only identifies the need for a general leakage source | Author(s), year, title, venue or documentation page, publisher/organization, DOI or URL | `report/final_apa_reference_inventory.csv`; `report/final_apa_reference_map.md` | required |
| `katangoori_2026_dataco_supply_chain_optimization` | DataCo-specific leakage concerns, if verified | Katangoori (2026). An empirical analysis of data-driven supply chain optimization in retail and logistics. [metadata incomplete] | Full publication metadata, DOI or URL, source-quality review | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | useful |

### Explainability / SHAP

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `lundberg_lee_2017_shap` | SHAP explanation method | Lundberg and Lee (2017). A unified approach to interpreting model predictions. [metadata incomplete] | Proceedings or publication details, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | required |
| `shap_package_reference` | SHAP package implementation | Repository records `shap==0.44.1`; no APA-ready documentation metadata is checked in | Official docs or paper metadata, version, DOI or URL | `requirements.txt`; `docs/databricks_setup.md`; `report/final_apa_reference_inventory.csv` | useful |
| `ahmed_2025_interpretable_supply_chain_forecasting` | Interpretable supply-chain forecasting and SHAP in a related supply-chain context | Ahmed et al. (2025). Deep learning framework for interpretable supply chain forecasting using SOM, ANN, and SHAP. [metadata incomplete] | Full author initials, venue, volume/issue/pages, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | optional |

### Data Engineering / Spark / Delta / Databricks

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `zaharia_2016_apache_spark` | Apache Spark big-data processing engine | Zaharia et al. (2016). Apache Spark: A unified engine for big data processing. [metadata incomplete] | Full author list, venue, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | required |
| `armbrust_2020_delta_lake` | Delta Lake storage infrastructure | Armbrust et al. (2020). Delta Lake: High-performance ACID table storage over cloud object stores. [metadata incomplete] | Full author list, venue, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | required |
| `databricks_platform_reference` | Databricks Community Edition platform and serving-layer context | Internal setup guide documents runtime; no external APA documentation metadata is checked in | Official documentation page title, organization, year/date, URL, retrieval date if needed | `docs/databricks_setup.md`; `report/final_apa_reference_inventory.csv` | required |

### Power BI / Azure Databricks Connector

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `microsoft_powerbi_reference` | Selected Power BI dashboard path and dashboard tooling | Inventory records that Power BI is the selected dashboard path and the first dashboard page was published in PR #141; no Microsoft APA metadata is checked in | Official Microsoft documentation title, date, URL, retrieval date if needed | `report/final_apa_reference_inventory.csv`; `dashboard/README.md`; `dashboard/powerbi_semantic_model.md` | required |
| `azure_databricks_connector_reference` | Selected direct Power BI connection to Azure Databricks serving-layer tables | Inventory records selected architecture; no Microsoft connector APA metadata is checked in | Official Microsoft page title, date, URL, retrieval date if needed | `docs/powerbi_databricks_serving_layer.md`; `dashboard/powerbi_semantic_model.md`; `report/final_apa_reference_inventory.csv` | required |

### Responsible AI / Limitations

| Citation key | Concept supported | Current APA metadata available | Missing APA metadata | Source file found | Priority |
| --- | --- | --- | --- | --- | --- |
| `responsible_ai_governance_reference_needed` | Responsible AI, model governance, or limitations framing if the final text makes external claims | No responsible-AI or governance source metadata is checked in | Author(s), year, title, venue or documentation page, publisher/organization, DOI or URL | `report/final_apa_reference_inventory.csv`; `report/final_apa_reference_map.md` | optional |
| `lundberg_lee_2017_shap` | Explainability method that may support part of the responsible-use discussion | Lundberg and Lee (2017). A unified approach to interpreting model predictions. [metadata incomplete] | Proceedings or publication details, DOI or URL | `report/final_apa_reference_inventory.csv`; proposal reference tracker path recorded there | useful |

## Minimum Required Reference Set

The smallest credible external reference set for the final report is:

| Citation key | Why it is needed | Current status |
| --- | --- | --- |
| `dataco_dataset_constante_2019` | Dataset source and DOI | Complete |
| `baryannis_2019_supply_chain_risk_ml` | Supply-chain risk prediction and interpretability context | Partial metadata |
| `hastie_tibshirani_friedman_2009_esl` | Core modeling methodology for regression/classification/boosting | Partial metadata |
| `xgboost_package_reference` | AO1 primary model and AO2 gradient boosting implementation if XGBoost is named | Reference needed |
| `general_leakage_reference_needed` | External support for leakage-safe modeling and prediction-time feature availability | Reference needed |
| `lundberg_lee_2017_shap` | SHAP explainability | Partial metadata |
| `zaharia_2016_apache_spark` | Spark data-processing implementation | Partial metadata |
| `armbrust_2020_delta_lake` | Delta Lake storage implementation | Partial metadata |
| `databricks_platform_reference` | Databricks platform or serving-layer context if cited externally | Reference needed |
| `microsoft_powerbi_reference` | Selected Power BI dashboard tooling if cited | Reference needed |
| `azure_databricks_connector_reference` | Direct Power BI to Azure Databricks serving-layer architecture | Reference needed |

This minimum set still requires metadata collection before the final report can replace the markers. DataCo remains the only complete external APA reference in repository evidence.

## References To Exclude Or Avoid

| Citation key | Recommendation | Reason |
| --- | --- | --- |
| `chawla_2002_smote` | remove | AO1 documentation states SMOTE is not used. Include only if the final report discusses SMOTE as a rejected alternative. |
| `python_pandas_numpy_matplotlib_reference` | remove | No expanded-draft marker currently requires these package citations. Add only if the final report makes substantive package-specific claims. |
| `chatrath_2026_ai_supply_chain_logistics` | optional or avoid | Broad background source with incomplete metadata; prioritize stronger peer-reviewed SCM analytics sources. |
| `ivanov_2021_digital_supply_chain_twins` | optional or avoid | Useful only if the final report discusses digital twins, visibility, or resilience; year ambiguity must be resolved first. |
| `ashraf_2025_customer_segmentation` | optional | Use only if the final AO3 text needs external segmentation literature beyond internal AO3 artifacts. |
| `douaioui_2024_late_delivery_resilience` | optional | Use only if full metadata is verified and the final report needs additional late-delivery literature. |
| `liang_2025_supply_chain_risk_decision_trees` | optional | Use only if full metadata is verified and decision-tree late-delivery context is directly discussed. |
| `gopal_2024_bda_supply_chain_performance` | optional | Background only unless final business-context claims need it. |
| `ahmed_2025_interpretable_supply_chain_forecasting` | optional | Useful for related SHAP/supply-chain context, but not necessary if Lundberg and Lee plus AO1/AO2 internal SHAP artifacts are sufficient. |

## Missing Metadata Collection Checklist

Collect the following before updating the expanded draft:

| Citation key | Author(s) | Year | Title | Venue/page | Publisher/org | Volume/issue/pages | DOI/URL | Retrieval date | Version |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dataco_dataset_constante_2019` | complete | complete | complete | complete | complete | not applicable | complete | not needed unless style requires | complete |
| `baryannis_2019_supply_chain_risk_ml` | missing initials | present | present | missing | missing | missing | missing | likely not needed if article DOI exists | not applicable |
| `toorajipour_2021_ai_scm_review` | missing initials | present | present | missing | missing | missing | missing | likely not needed if article DOI exists | not applicable |
| `ni_xiao_lim_2020_ml_scm_review` | missing initials | present | present | missing | missing | missing | missing | likely not needed if article DOI exists | not applicable |
| `hastie_tibshirani_friedman_2009_esl` | names present, initials needed | present | present | book details missing | missing | not applicable | URL optional if online version used | not needed unless online text cited | edition needed |
| `xgboost_package_reference` | missing | missing | missing | missing | missing | not applicable | missing | needed if documentation page is used | version available from repo |
| `scikit_learn_package_reference` | missing | missing | missing | missing | missing | not applicable | missing | needed if documentation page is used | version available from repo |
| `general_leakage_reference_needed` | missing | missing | missing | missing | missing | missing if article | missing | depends on source type | not applicable |
| `lundberg_lee_2017_shap` | names present, initials needed | present | present | missing | missing | missing if applicable | missing | likely not needed if article/proceedings URL exists | not applicable |
| `shap_package_reference` | missing | missing | missing | missing | missing | not applicable | missing | needed if documentation page is used | version available from repo |
| `zaharia_2016_apache_spark` | missing full author list | present | present | missing | missing | missing | missing | likely not needed if paper DOI/URL exists | not applicable |
| `armbrust_2020_delta_lake` | missing full author list | present | present | missing | missing | missing | missing | likely not needed if paper DOI/URL exists | not applicable |
| `databricks_platform_reference` | organization likely needed | missing | missing | missing | missing | not applicable | missing | needed if documentation page is used | runtime version documented internally |
| `microsoft_powerbi_reference` | organization likely needed | missing | missing | missing | missing | not applicable | missing | needed if documentation page is used | not applicable unless docs versioned |
| `azure_databricks_connector_reference` | organization likely needed | missing | missing | missing | missing | not applicable | missing | needed if documentation page is used | not applicable unless docs versioned |
| `responsible_ai_governance_reference_needed` | missing | missing | missing | missing | missing | missing if article | missing | depends on source type | not applicable |

## Citation Replacement Plan

| Marker from expanded draft | Selected citation key(s) | Action |
| --- | --- | --- |
| `[NEEDS APA SOURCE DETAILS: predictive analytics in supply chain management]` | `baryannis_2019_supply_chain_risk_ml`; `toorajipour_2021_ai_scm_review`; optionally `ni_xiao_lim_2020_ml_scm_review` | keep pending until source metadata is verified, then replace with citation |
| `[NEEDS APA SOURCE DETAILS: machine learning for delivery risk and logistics prediction]` | `baryannis_2019_supply_chain_risk_ml`; optionally `katangoori_2026_dataco_supply_chain_optimization`, `douaioui_2024_late_delivery_resilience`, or `ahmed_2025_interpretable_supply_chain_forecasting` | keep pending until source metadata is verified, then replace with citation |
| `[NEEDS APA SOURCE DETAILS: profitability modeling and regression analytics]` | `hastie_tibshirani_friedman_2009_esl`; optionally `katangoori_2026_dataco_supply_chain_optimization` | replace with citation after metadata verification; rewrite any unsupported profitability-literature claim if no specific source is verified |
| `[NEEDS APA SOURCE DETAILS: data leakage in predictive modeling]` | `general_leakage_reference_needed`; optionally `katangoori_2026_dataco_supply_chain_optimization` for DataCo-specific leakage | keep pending until source is verified or rewrite sentence to cite internal leakage artifacts only |
| `[NEEDS APA SOURCE DETAILS: SHAP and explainable machine learning]` | `lundberg_lee_2017_shap`; optionally `ahmed_2025_interpretable_supply_chain_forecasting` | keep pending until source metadata is verified, then replace with citation |
| `[NEEDS APA SOURCE DETAILS: segmentation and decision-support frameworks]` | optionally `ashraf_2025_customer_segmentation`; optionally `katangoori_2026_dataco_supply_chain_optimization`; otherwise internal AO3 artifacts | rewrite sentence to avoid unsupported external claim or keep pending until a decision-support source is verified |
| `[NEEDS APA SOURCE DETAILS: business intelligence dashboards and analytics communication]` | `microsoft_powerbi_reference`; `azure_databricks_connector_reference`; possible new BI communication source | rewrite broad analytics-communication claim unless a BI literature source is verified; cite Microsoft docs only for tooling mechanics |
| `[NEEDS APA SOURCE DETAILS: XGBoost original paper or official documentation]` | `xgboost_package_reference` | keep pending until official source metadata is verified |
| `[NEEDS APA SOURCE DETAILS: SHAP original paper or official documentation]` | `lundberg_lee_2017_shap`; optionally `shap_package_reference` | keep pending until source metadata is verified |
| `[NEEDS APA SOURCE DETAILS: scikit-learn documentation for Logistic Regression, Ridge Regression, metrics, and K-means]` | `scikit_learn_package_reference` | replace with citation after metadata verification if package implementation remains named; otherwise remove marker |
| `[NEEDS APA SOURCE DETAILS: Apache Spark documentation if cited]` | `zaharia_2016_apache_spark`; optionally `apache_spark_docs_reference` from inventory | replace with verified Spark paper/docs citation if Spark is cited externally |
| `[NEEDS APA SOURCE DETAILS: Delta Lake documentation if cited]` | `armbrust_2020_delta_lake`; optionally `delta_lake_docs_reference` from inventory | replace with verified Delta Lake paper/docs citation if Delta Lake is cited externally |
| `[NEEDS APA SOURCE DETAILS: Databricks documentation if cited]` | `databricks_platform_reference` | keep pending until official Databricks docs metadata is verified; cite only platform/serving-layer context |
| `[NEEDS APA SOURCE DETAILS: Microsoft Power BI Azure Databricks connector documentation if cited]` | `azure_databricks_connector_reference`; `microsoft_powerbi_reference` | keep pending until official Microsoft docs metadata is verified |
| `[NEEDS APA SOURCE DETAILS: supply chain analytics literature used in the proposal or course materials]` | `baryannis_2019_supply_chain_risk_ml`; `toorajipour_2021_ai_scm_review`; optionally `ni_xiao_lim_2020_ml_scm_review` or `gopal_2024_bda_supply_chain_performance` | keep pending until selected sources are verified, then replace with concise citation set |
| `[NEEDS APA SOURCE DETAILS: predictive analytics and decision-support literature]` | `baryannis_2019_supply_chain_risk_ml`; `hastie_tibshirani_friedman_2009_esl`; possible new decision-support source | rewrite unsupported decision-support claim or keep pending until a direct decision-support source is verified |
| `[NEEDS APA SOURCE DETAILS: responsible AI, model governance, or explainability literature]` | `responsible_ai_governance_reference_needed`; `lundberg_lee_2017_shap` for explainability only | keep pending until governance source is verified, or rewrite section around internal controls and SHAP caveats |
