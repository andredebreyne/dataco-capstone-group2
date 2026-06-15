# Predicting Late Delivery Risk and Explaining Order Profitability in a Global E-Commerce Supply Chain

DAMO 699 Capstone Final Report Draft V1

Team: Group 2

Institution: University of Niagara Falls Canada

Instructor: Prof William Pourmajidi, PhD

Date: 02-Jun-2026

## Abstract / Executive Summary

This capstone develops a leakage-safe, pre-shipment decision-support framework for a global e-commerce supply chain using the DataCo Smart Supply Chain dataset. The business problem is that managers need to decide which orders deserve attention before dispatch, when operational action is still possible. Late-delivery risk alone does not fully answer that question because scarce intervention capacity should also consider expected order profitability. A high-risk order with strong expected margin may justify early review, while a high-risk order with weak or negative expected margin may require more selective action.

The research question is: How can pre-shipment attributes available at order creation be used to build a practical pre-dispatch order-prioritization framework that combines late-delivery risk and expected order profitability in a global e-commerce supply chain?

The project answers this question through three integrated analytical objectives. Analytical Objective 1 (AO1) predicts late-delivery risk using order-time and pre-dispatch attributes. Analytical Objective 2 (AO2) estimates expected order-level profitability before dispatch. Analytical Objective 3 (AO3) combines the AO1 and AO2 predictions into a risk-margin prioritization framework for operational triage. The dashboard layer communicates these outputs in Power BI through governed Azure Databricks serving-layer tables.

The current evidence supports the three hypotheses with important caveats. H1 is supported on chronological validation evidence: the AO1 XGBoost classifier outperformed the Logistic Regression baseline on ROC-AUC, recall, precision, F1, and log loss. H2 is supported on chronological validation evidence with modest improvement: the AO2 Gradient Boosting/XGBoost Regressor improved RMSE and MAE relative to the Ridge baseline, but explanatory power remained limited and the AO2 target-reconstruction audit accepted the model only with caution. H3 is supported by AO3 segmentation and benchmark evidence: the combined risk-margin framework separated operational groups that were not fully evident from either risk-only or margin-only prioritization.

The report does not claim causal impact, production deployment, or unsupported final-test confirmation. AO1 and AO2 results are framed as validation-stage evidence. AO3 is based on held-out scored predictions and benchmark segmentation, not realized intervention outcomes. Power BI is the official dashboard deliverable. The selected dashboard architecture is a direct Power BI connection to Azure Databricks serving-layer tables. The connection worked, and the first Power BI dashboard page was published in PR #141 according to the project status update. Final screenshots, page names, page inventory, `.pbix` submission route if required, and final serving-layer manifest details remain update points.

## Introduction and Business Problem

Late delivery is a recurring managerial problem in e-commerce supply chains because customer promises, shipping mode, geography, product mix, demand timing, and fulfillment constraints interact before the order reaches the customer. A purely retrospective dashboard can show which orders were late, but it cannot help managers decide which orders should receive attention before dispatch. The useful decision window occurs earlier, when an order has been created and planned but has not yet moved beyond the point where intervention is feasible.

This project therefore frames the DataCo problem as pre-shipment decision support rather than as after-the-fact reporting. The objective is not merely to describe historical lateness or realized profitability. The objective is to estimate early risk and expected profitability signals that can support managerial triage. That framing drives the modeling policy: features must be available at order creation or before shipment, and outcome-like or post-shipment variables must not be used as predictors.

The business problem also requires an integrated view. A risk-only ranking can identify orders that are likely to be late, but it cannot distinguish high-value at-risk orders from low-margin at-risk orders. A profit-only ranking can identify orders with stronger expected economics, but it cannot show which of those orders are most exposed to service failure. AO3 addresses that gap by combining predicted late-delivery probability from AO1 with predicted profitability and derived margin from AO2.

The intended managerial result is a practical prioritization framework. Orders with high predicted delivery risk and positive predicted margin can be placed into a protection queue. Orders with high predicted delivery risk and weak predicted margin can be reviewed selectively before expensive intervention. Lower-risk high-margin orders can receive service-preservation attention without urgent escalation, and lower-risk low-margin orders can remain under standard process with margin monitoring. These recommendations are triage guidance. They do not prove that a specific intervention will improve delivery or profit.

[INSERT TABLE: Business problem to analytical objective mapping - source: report/final_capstone_report_draft_v1.md internal synthesis from docs/proposal/proposal_summary.md and AO result docs]

## Research Question, Objectives, and Hypotheses

The capstone research question is:

> How can pre-shipment attributes available at order creation be used to build a practical pre-dispatch order-prioritization framework that combines late-delivery risk and expected order profitability in a global e-commerce supply chain?

The research question is operational and methodological. Operationally, it asks how a manager can prioritize orders before dispatch. Methodologically, it asks how to build that prioritization without using information that would not exist at the decision time.

The analytical objectives are:

1. AO1: Predict late-delivery risk using pre-shipment and order-time attributes.
2. AO2: Estimate expected order-level profitability before dispatch.
3. AO3: Combine AO1 and AO2 outputs into a risk-margin prioritization framework.
4. Dashboard layer: Communicate the analytical results through Power BI using governed Azure Databricks serving-layer tables.

The hypotheses are:

**H1.** For late-delivery prediction, an XGBoost classifier will outperform logistic regression on held-out data, particularly in AUC-ROC and recall.

**H2.** For order-profitability estimation, a gradient boosting regressor will outperform linear or ridge regression on held-out data, particularly in RMSE and MAE.

**H3.** Combining predicted late-delivery risk and expected order profitability in a risk-margin framework will identify pre-dispatch priority groups that are not evident from either signal alone and therefore support differentiated operational actions.

The three hypotheses are connected. H1 and H2 produce the risk and profitability inputs that AO3 needs. AO3 is the decision-support layer that turns model outputs into operational segments. The Power BI dashboard is the communication layer that allows a reviewer or manager to inspect those segments, metrics, and governance controls.

| Objective | Primary question | Main output | Role in framework |
| --- | --- | --- | --- |
| AO1 | Which orders are likely to arrive late? | Predicted late-delivery probability and high-risk flag | Risk signal for AO3 |
| AO2 | Which orders are expected to be profitable or loss-making? | Predicted order profit and derived predicted margin | Margin signal for AO3 |
| AO3 | Which orders deserve differentiated pre-dispatch action? | Risk-margin priority segment | Decision-support layer |
| Dashboard | How can managers inspect and use the results? | Power BI report connected to Databricks serving tables | Communication and governance layer |

## Literature Review / Analytical Context

Supply-chain analytics research commonly treats prediction as useful only when the result can support an operational decision. AI and machine-learning reviews in supply-chain management describe the field as a broad decision-support domain involving forecasting, risk identification, logistics planning, and performance improvement (Toorajipour et al., 2021; Ni et al., 2020). [APA TODO: toorajipour_2021_ai_scm_review - missing full author initials, journal, volume/issue/pages, DOI or URL] [APA TODO: ni_xiao_lim_2020_ml_scm_review - missing full author initials, journal, volume/issue/pages, DOI or URL] For this project, that broad context is narrowed to a pre-dispatch order-prioritization problem.

Delivery-risk prediction is the first analytical requirement. Supply-chain risk-prediction literature supports the idea that predictive models can identify risk patterns but also highlights the trade-off between interpretability and model performance (Baryannis et al., 2019). [APA TODO: baryannis_2019_supply_chain_risk_ml - missing full author initials, venue, volume/issue/pages, DOI or URL] Applied late-delivery studies and DataCo-focused studies may provide closer comparison points if their metadata and source quality are verified (Ahmed et al., 2025; Katangoori, 2026). [APA TODO: ahmed_2025_interpretable_supply_chain_forecasting - missing full author initials, venue, volume/issue/pages, DOI or URL] [APA TODO: katangoori_2026_dataco_supply_chain_optimization - missing full publication metadata, DOI or URL, source-quality review] These sources should be used as contextual support only. The actual H1 evidence in this capstone comes from the checked-in AO1 validation artifacts.

Profitability estimation is a regression problem. General statistical learning references support the distinction between linear baselines, regularized regression, and nonlinear boosting methods (Hastie et al., 2009). [APA TODO: hastie_tibshirani_friedman_2009_esl - missing edition, publisher, and URL if online version is cited] In this project, Ridge Regression is used as a regularized baseline and Gradient Boosting/XGBoost regression is used as the primary nonlinear profitability estimator. The AO2 modeling problem requires extra caution because commercial fields can be close to accounting formulas. The final report therefore treats AO2 as expected profitability estimation, not profit reconstruction.

Leakage-safe modeling is central to the report's validity. Liu et al. (2022) support the general risk that future or test information can create leakage and falsely high evaluation results, with the limitation that the source is time-series-focused rather than supply-chain-specific. [APA TODO: liu_chen_zheng_feng_2022_leakage_suppression - missing venue or publisher, volume/issue/pages if applicable, DOI or URL] The project-specific leakage controls come from internal artifacts: `docs/leakage_control_plan.md`, `docs/feature_availability_map.md`, `docs/chronological_split_policy.md`, and the AO2 target-reconstruction audit.

Explainability is included because the capstone is intended for academic review and managerial interpretation. SHAP is used to summarize model-driver patterns for AO1 and AO2. The project interprets SHAP as model explanation, not causal inference. Lundberg and Lee (2017) are the planned method citation once full metadata is verified. [APA TODO: lundberg_lee_2017_shap - missing proceedings or venue details, DOI or URL]

AO3 uses segmentation to convert continuous prediction signals into operational groups. The project uses a governed 2x2 risk-margin policy instead of promoting unsupervised clustering as the main method. An optional K-means extension was tested but not adopted because the generated artifacts concluded that the clusters mostly duplicated the simpler risk-margin matrix. If a general segmentation source is needed, it should be verified before citation; otherwise, the final AO3 discussion should rely on project-specific artifacts.

The dashboard layer is a business-intelligence communication layer, not a modeling layer. Microsoft documentation is needed only for Power BI and Azure Databricks connection mechanics, not for analytical conclusions. The primary planned connector source is Microsoft Learn "Power BI with Azure Databricks." [APA TODO: microsoft_learn_powerbi_azure_databricks - missing Microsoft Learn page date, URL, and retrieval date if needed] The Databricks Power Platform connector blog is not used as the primary dashboard reference because it is not focused on the Power BI Desktop dashboard workflow.

## Data Source and Data Governance

The primary dataset is the DataCo Smart Supply Chain for Big Data Analysis dataset from Mendeley Data, version 5 (Constante et al., 2019). The verified source artifact is `docs/data_source_verification.md`. The dataset was published on March 12, 2019, with DOI `10.17632/8gx2fvg2k6.5`, and the checked-in source verification document records a CC BY 4.0 license.

The verified structured dataset contains 180,519 rows and 53 columns. The companion metadata file contains 52 metadata rows. The raw structured file was parsed with `latin-1` encoding and comma delimiters. The first verified columns include `Type`, `Days for shipping (real)`, `Days for shipment (scheduled)`, `Benefit per order`, `Sales per customer`, `Delivery Status`, `Late_delivery_risk`, and `Category Id`.

[INSERT TABLE: DataCo dataset summary - source: docs/data_source_verification.md]

The dataset includes order, customer, product, shipping, logistics, geography, and financial fields. Important modeling fields include `Late_delivery_risk`, `Order Profit Per Order`, shipping mode, scheduled shipping days, order dates, market, region, country, product category, discount rate, quantity, and price-related fields. Not all available fields are valid predictors. Some fields are targets, post-shipment outcomes, duplicate outcomes, target proxies, or non-operational identifiers.

Source verification also identified data-quality details that should remain visible in the final report. The metadata file has exact-name coverage for 51 of 53 dataset columns after trimming. `Order Zipcode` and `shipping date (DateOrders)` did not match the metadata exactly after trimming. Blank-value checks found 180,519 blanks in `Product Description`, 155,679 blanks in `Order Zipcode`, 8 blanks in `Customer Lname`, and 3 blanks in `Customer Zipcode`. These findings do not block ingestion, but they support the decision to document schema and cleaning rules in the Silver layer.

The DataCo dataset is public, anonymized, and partially synthetic. That status supports ethical academic use but limits generalization to a live operating business. The final report should not imply that the results have been validated against a production enterprise environment with carrier contracts, fulfillment capacity constraints, real-time disruptions, customer lifetime value, or intervention-cost data.

Data governance is implemented through the repository's Medallion structure. Bronze preserves raw source data and source metadata. Silver applies cleaning, type standardization, lineage fields, and feature-availability documentation. Gold contains objective-specific analytical tables, model outputs, AO3 segment outputs, and dashboard-serving outputs. This design keeps raw source data unchanged while making downstream analysis reproducible.

## Data Engineering and Cloud Implementation

The project uses a simplified Bronze-Silver-Gold Medallion architecture documented in `docs/medallion_structure.md`. Bronze stores raw or lightly registered DataCo source data. Silver stores cleaned and standardized analytical tables. Gold stores curated model-ready, evaluation, score, AO3, and dashboard-ready outputs. Small reference files are maintained under `data/references/` when they are safe to commit.

[INSERT FIGURE: Medallion and project workflow architecture - source: docs/medallion_structure.md and docs/project_orchestrator.md]

The intended cloud execution environment is Databricks Community Edition. The documented preferred runtime is Databricks Runtime 14.3 LTS with Spark 3.5.0, with 13.3 LTS as a fallback. Spark and Delta support the scalable data-processing and table-management pattern for the academic workflow. Spark and Delta external citations should be completed only after metadata verification. [APA TODO: zaharia_2016_apache_spark - missing full author list, venue, DOI or URL] [APA TODO: armbrust_2020_delta_lake - missing full author list, venue, DOI or URL] [APA TODO: databricks_official_reference - missing documentation page title, organization, date or year, URL, retrieval date if needed]

The repository keeps reusable logic in `/src` and uses notebooks or workflow scripts as orchestration layers. The main Databricks-compatible entry point is `notebooks/pipeline/run_project_workflow.py`, documented in `docs/project_orchestrator.md`. The orchestrator coordinates setup validation, structure checks, raw data validation, reference registration, Bronze ingestion, Silver cleaning, feature engineering, Gold analytical tables, chronological partitions, model training, evaluation, explainability, AO2 target-reconstruction audit, AO1 threshold selection, AO1/AO2 held-out scoring, AO3 segmentation, AO3 benchmarking, optional K-means extension, and Power BI serving-layer registration.

Many orchestrator steps are disabled by default. This is intentional for final packaging because model and dashboard artifacts should not be regenerated accidentally. The report uses checked-in artifacts as evidence and does not rerun data engineering, model training, evaluation, export generation, or dashboard creation.

Gold analytical tables are objective-specific. AO1 uses a late-delivery analytical table that applies the approved population policy and excludes post-outcome fields. AO2 uses a profitability analytical table that excludes target-reconstruction fields and reserves `ao3_order_value` only for later AO3 margin construction. AO3 consumes model scores and applies a rule-based segment policy. The dashboard consumes governed serving-layer tables and does not recreate model scores or thresholds.

The Power BI serving layer is documented in `docs/powerbi_databricks_serving_layer.md`. The entry point is `src/dashboard/register_powerbi_databricks_tables.py`. It publishes one managed Databricks SQL table per governed dashboard artifact under the configured catalog and schema, defaulting to `workspace.default`. The serving tables are prefixed with `powerbi_` and are designed for Power BI Desktop connection through Azure Databricks.

[INSERT TABLE: Power BI serving-layer table inventory - source: docs/powerbi_databricks_serving_layer.md and dashboard/powerbi_semantic_model.md]

## Leakage-Control and Chronological Split Methodology

The project is governed by a decision-time integrity rule: a feature may be used for modeling only if it is known at order creation or can be derived from information available before shipment. This rule is documented in `docs/leakage_control_plan.md` and operationalized through the feature availability map, pre-Gold modeling decisions, chronological split policy, objective-specific preprocessing metadata, and post-model audits.

AO1 forbidden predictors include the target `Late_delivery_risk`, `Delivery Status`, `Days for shipping (real)`, `shipping date (DateOrders)`, `Order Status`, and other direct post-outcome or target-proxy fields. AO2 forbidden predictors include `Order Profit Per Order`, `Benefit per order`, `Order Item Profit Ratio`, direct transformations of profit, duplicate profit outcomes, and realized margin-like fields. Non-operational identifiers such as customer names, masked passwords, street address detail, image links, and empty descriptions are also excluded from modeling predictors unless a documented descriptive exception exists.

[INSERT TABLE: Leakage-control and feature availability summary - source: docs/leakage_control_plan.md, docs/feature_availability_map.md, data/references/feature_availability_map.csv]

The split strategy is chronological rather than random. The master split anchor is `order_date_DateOrders`, representing order creation time. Rows are sorted by `order_date_DateOrders`, `Order_Id`, and `Order_Item_Id`. The earliest 80% become the development set, and the most recent 20% become the final held-out test set. This rule is applied separately to each objective-specific Gold table after that table's population policy is applied.

AO1 has 172,765 Gold rows after its population policy. The development partition contains 138,212 rows and the test partition contains 34,553 rows. AO2 has 180,519 Gold rows. Its development partition contains 144,415 rows and its test partition contains 36,104 rows. The final test partitions remain untouched for AO1 and AO2 validation claims in the checked-in result documents.

[INSERT TABLE: Chronological split summary - source: docs/chronological_split_policy.md, data/references/ao1_chronological_partition_summary.csv, data/references/ao2_chronological_partition_summary.csv]

Within the development partition, model training and validation use additional chronological development/validation splits. Preprocessing is fit only on the inner training slice and applied unchanged to validation or test slices. This applies to imputers, encoders, scalers, feature selectors, resampling, threshold selection, and hyperparameter tuning. The current AO1 workflow does not use SMOTE. A SMOTE citation should therefore not appear unless the final text explicitly discusses SMOTE as an unused or rejected method.

AO2 receives special target-reconstruction controls. The target-reconstruction audit reviewed the finalized AO2 Gradient Boosting predictor and driver evidence. It found zero forbidden features and 1,308 caution features, confirmed that `ao3_order_value` was not detected as an AO2 predictor or dominant driver, and issued the final decision `accepted_with_caution`. This supports reporting AO2 as defensible for expected profitability estimation while keeping the target-reconstruction caveat visible.

[INSERT TABLE: AO2 target-reconstruction audit summary - source: report/tables/ao2_target_reconstruction_audit_findings.md]

## Analytical Methods

The project uses several complementary analytical methods rather than a single standalone model. Logistic Regression provides an interpretable AO1 classification baseline. XGBoost classification provides the primary nonlinear AO1 model. Ridge Regression provides an AO2 regularized linear baseline. Gradient Boosting/XGBoost regression provides the primary nonlinear AO2 profitability model. SHAP supports model-driver explanation for AO1 and AO2. AO3 uses a rule-based risk-margin segmentation framework. An optional K-means extension was evaluated but not adopted.

[INSERT TABLE: Analytical methods coverage matrix - source: report/final_report_detailed_outline.md, docs/ao1_results_h1_validation.md, docs/ao2_results_h2.md, docs/ao3_methodology_and_results.md]

For AO1, the target is `Late_delivery_risk`, with `1` representing a historical late-delivery event and `0` representing a non-late event under the approved target policy. The baseline model is Logistic Regression, and the primary model is XGBoost classification. The selected XGBoost candidate is `deeper_conservative`, chosen from a validation-only candidate set using ROC-AUC as the primary selection metric and recall as the secondary metric. XGBoost implementation support should cite official XGBoost documentation after metadata verification. [APA TODO: xgboost_documentation_3_2_0 - missing documentation page title, organization, release/version, URL, retrieval date if needed] If the final report keeps broad XGBoost methodology discussion, the canonical Chen and Guestrin source should be verified before use. [APA TODO: chen_guestrin_2016_xgboost_method - missing full paper title, venue, publisher/proceedings, DOI or URL]

For AO2, the target is `Order_Profit_Per_Order`. Ridge Regression provides a baseline with regularization, and Gradient Boosting/XGBoost regression provides the primary nonlinear model. The selected Gradient Boosting candidate is `conservative_baseline`. scikit-learn Ridge documentation should be cited only if the report discusses the Ridge implementation mechanics. [APA TODO: scikit_learn_ridge_documentation - missing Ridge documentation page title, URL, retrieval date if needed] A broad scikit-learn citation should be added only if the final text cites scikit-learn as a general implementation library. [APA TODO: scikit_learn_broad_citation_needed - missing canonical paper or documentation metadata]

For explainability, SHAP summaries are used to interpret model driver patterns. The project uses SHAP results as validation-model explanations and leakage-audit support, not as causal evidence. AO1 SHAP highlights the dominance of First Class shipping-mode effects, scheduled service windows, order timing, and geography. AO2 SHAP highlights commercial, geography, product, discount, and quantity signals with target-policy caution.

For AO3, no additional model is trained. The method applies a risk cutoff of 0.35 and a margin cutoff of 0.0 to held-out AO1/AO2 scores. The resulting segments are `protect_high_value_at_risk`, `expedite_selectively`, `preserve_service`, `standard_process`, `requires_score_review`, and `requires_margin_review`. The optional K-means extension produced a selected `k = 3` solution but was not adopted because it mostly duplicated the governed 2x2 risk-margin policy and would make the decision story less clear.

## AO1 Results: Late-Delivery Risk Prediction

AO1 asks whether order-level late-delivery risk can be predicted before dispatch using decision-time information from the DataCo supply chain dataset. The AO1 target is `Late_delivery_risk`. The validation evidence uses the shared chronological validation slice inside the development partition. The final test partition is reserved and is not used for AO1 model selection, threshold selection, SHAP explainability, or H1 validation in the current result documentation.

The AO1 partition structure used in the result document is:

| Slice | Rows | Use |
| --- | ---: | --- |
| Development inner training | 110,569 | Preprocessing fit and model training |
| Development inner validation | 27,643 | Model comparison, threshold review, and validation metrics |
| Final test | 34,553 | Reserved for final AO1 evaluation |

[INSERT TABLE: AO1 model comparison - source: report/tables/ao1_model_validation_comparison.csv]

The XGBoost classifier outperformed the Logistic Regression baseline on the shared validation slice. XGBoost achieved ROC-AUC 0.7753, PR-AUC 0.8489, accuracy 0.7212, precision 0.8890, recall 0.5840, F1 0.7049, and log loss 0.5133 at the 0.50 threshold. Logistic Regression achieved ROC-AUC 0.7426, PR-AUC 0.8307, accuracy 0.6856, precision 0.8296, recall 0.5645, F1 0.6718, and log loss 0.5723. XGBoost improved ROC-AUC by 0.0327 and recall by 0.0195 at the default threshold.

The operating threshold for AO3 is not the default 0.50 threshold. The threshold policy prioritizes recall while keeping the predicted positive rate operationally manageable. No evaluated threshold satisfied both recall of at least 0.70 and predicted positive rate of no more than 0.65. The policy therefore selected the highest-recall threshold under the alert-rate cap. The chosen AO1 high-risk rule is:

```text
ao1_predicted_late_delivery_probability >= 0.35
```

At threshold 0.35, the validation precision is 0.8469, recall is 0.6171, predicted positive rate is 0.4154, false negatives are 6,035, and false positives are 1,758.

[INSERT TABLE: AO1 threshold recommendation - source: report/tables/ao1_decision_threshold_recommendation.md and data/references/ao1_decision_threshold_policy.csv]

AO1 SHAP results support model interpretation and leakage review. The strongest driver is `categorical__shipping_mode_normalized_first_class`, with mean absolute SHAP 5.780122 and importance share 0.3810. Scheduled service window features such as `numeric_continuous__scheduled_shipping_days` and `categorical__shipping_speed_tier_standard` are also important. Geography one-hot features appear among the top drivers and should be interpreted cautiously because sparse location indicators may be unstable.

[INSERT FIGURE: AO1 SHAP top features - source: report/figures/ao1_shap_top_features.png]

The AO1 post-model leakage audit reviewed SHAP and feature-importance outputs and found no driver resembling the target, actual shipping duration, delivery status, shipping completion status, realized profit, final-test labels, or another direct post-outcome proxy. The audit does not prove leakage is impossible, but it supports the conclusion that AO1 is reportable with caveats.

H1 is supported on validation evidence. The final wording should remain careful: validation evidence supports H1 because XGBoost achieved stronger held-out validation performance than Logistic Regression for AO1 late-delivery prediction, particularly in ROC-AUC and recall. Final-test confirmation should not be claimed unless a separate final-test artifact supports it.

## AO2 Results: Profitability Estimation

AO2 estimates expected order-level profitability before dispatch. The target is `Order_Profit_Per_Order`. The output should be interpreted as expected profitability, not as known profit at dispatch time and not as a direct accounting formula. AO2 is an input to AO3 and should not be used alone as an automated action rule.

The AO2 validation result uses the chronological validation slice inside the development partition. The final test partition is reserved and was not used for training, preprocessing fit, model selection, validation metrics, residual diagnostics, SHAP explainability, target-reconstruction audit, or H2 conclusion. The generated metadata records `final_test_used = false`.

The AO2 partition structure used in the result document is:

| Slice | Rows | Use |
| --- | ---: | --- |
| Development inner training | 115,532 | Preprocessing fit and model training |
| Development inner validation | 28,883 | Model comparison, residual review, SHAP explanation, and H2 validation evidence |
| Final test | 36,104 | Reserved for future final AO2 evaluation |

[INSERT TABLE: AO2 model comparison - source: report/tables/ao2_model_validation_comparison.csv and report/tables/ao2_results_h2_summary.csv]

The Gradient Boosting/XGBoost Regressor improved the primary AO2 metrics relative to Ridge. The Gradient Boosting model achieved RMSE 95.6203, MAE 52.6463, R2 0.0118, median absolute error 31.3954, and mean error 0.9627. Ridge achieved RMSE 96.8276, MAE 54.2191, R2 -0.0133, median absolute error 32.5591, and mean error 0.6453. The improvement is 1.2073 lower RMSE, 1.5729 lower MAE, and 0.0251 higher R2.

The support for H2 is modest. R2 remains low, and both models compress predictions toward the mean. The validation target standard deviation is 96.1905, while the prediction standard deviation is 19.5479 for Ridge and 11.9159 for Gradient Boosting. Both models miss some extreme-profit and severe-loss cases. The wrong profit-sign share improved from 0.2536 for Ridge to 0.1974 for Gradient Boosting, which is useful for AO3 because profit-sign errors can affect the high-margin or low-margin classification.

[INSERT TABLE: AO2 residual diagnostics - source: report/tables/ao2_residual_diagnostics_by_model.csv]

AO2 SHAP explainability is based on a 5,000-row sample from `development_inner_validation`. The top driver families include commercial price, geography, product mix, discount rate, and quantity. These are plausible predictive signals, but they must be interpreted cautiously because approved commercial predictors can still be close to profitability calculation context.

[INSERT FIGURE: AO2 SHAP top features - source: report/figures/modeling/ao2_shap_top_features.png]

The target-reconstruction audit is central to AO2 credibility. It found zero forbidden features and no evidence that `ao3_order_value` entered the AO2 predictors or dominant drivers. The final audit decision was `accepted_with_caution`. This means AO2 is defensible for pre-dispatch expected-profitability estimation, but the report should not overstate it as precise profit prediction.

H2 is supported on validation evidence with modest improvement. The Gradient Boosting model improves RMSE and MAE over Ridge on the shared chronological validation slice, but the model remains limited by low explanatory power, compressed predictions, and target-policy caveats.

## AO3 Results: Risk-Margin Prioritization Framework

AO3 integrates AO1 and AO2 into a unified prioritization framework. It does not train a new model. It consumes `ao1_predicted_late_delivery_probability` from the selected AO1 XGBoost classifier and `ao2_predicted_order_profit` from the selected AO2 Gradient Boosting Regressor. It derives predicted margin as:

```text
ao3_predicted_margin = ao2_predicted_order_profit / ao3_order_value
```

The denominator `ao3_order_value` is reserved for AO3 support and is not used as an AO2 predictor. This preserves the distinction between expected-profit estimation and downstream margin construction.

The approved AO3 thresholds are:

| Threshold | Value | Basis |
| --- | ---: | --- |
| `risk_cutoff` | 0.35 | Approved AO1 decision threshold |
| `margin_cutoff` | 0.0 | Separates positive from negative predicted margin |

[INSERT TABLE: AO3 risk-margin matrix - source: docs/ao3_risk_margin_matrix.md and data/references/ao3_risk_margin_matrix_policy.csv]

The AO3 segment table was evaluated on 34,467 held-out scored orders from the common AO1/AO2 test score population. These rows come from the chronological test partition scoring workflow, but AO3 segmentation uses prediction signals rather than realized target values. The scored output excludes actual target columns from the operational dashboard-serving layer.

[INSERT TABLE: AO3 segment summary - source: data/references/ao3_risk_margin_benchmark_segment_summary.csv]

The observed held-out AO3 segment distribution is:

| AO3 segment | Count | Share | Avg predicted risk | Avg predicted profit | Avg predicted margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| `protect_high_value_at_risk` | 13,752 | 39.9% | 0.832 | 21.61 | 0.126 |
| `preserve_service` | 20,603 | 59.8% | 0.319 | 21.60 | 0.126 |
| `expedite_selectively` | 52 | 0.15% | 0.811 | -14.64 | -0.127 |
| `standard_process` | 60 | 0.17% | 0.298 | -20.61 | -0.293 |
| `requires_score_review` | 0 | 0.0% | n/a | n/a | n/a |
| `requires_margin_review` | 0 | 0.0% | n/a | n/a | n/a |

The benchmark supports H3 because single-signal views would hide important distinctions. Margin-only prioritization would group `protect_high_value_at_risk` and `preserve_service` together because both have positive predicted margins and nearly identical average predicted profit. AO3 separates them because their average predicted late-delivery risk differs materially: 0.832 versus 0.319. This is the main decision-layer value observed in the benchmark population.

Risk-only prioritization would group `protect_high_value_at_risk` and `expedite_selectively` together because both are high risk. AO3 separates them because their predicted economics differ sharply: average predicted profit is 21.61 for `protect_high_value_at_risk` and -14.64 for `expedite_selectively`, and the predicted margin signs differ. Risk-only differentiation is weaker in this held-out sample because 99.6% of high-risk orders are also high margin, but the split still shows why risk alone is not sufficient.

[INSERT TABLE: AO3 benchmark and crosswalk evidence - source: data/references/ao3_risk_margin_benchmark_crosswalk.csv and data/references/ao3_risk_margin_benchmark_insights.csv]

The optional K-means extension was evaluated but not adopted. The selected `k = 3` solution had inertia 19,671.6795, silhouette score 0.6859, and a minimum cluster share of 1.91%. Existing artifacts concluded that K-means mostly duplicated the governed AO3 risk-margin matrix. The final recommendation was `do_not_adopt`.

H3 is supported by AO3 segmentation and benchmark evidence with caveats. AO3 identifies operational groups not fully evident from risk-only or margin-only views, but it does not prove that interventions improve realized delivery or profit outcomes.

## Power BI Dashboard and Visualization Layer

Power BI is the official dashboard deliverable for this capstone. The selected dashboard architecture is a direct Power BI connection to Azure Databricks serving-layer tables. The direct connection worked, and the first Power BI dashboard page was published in PR #141 according to the project status update. Databricks native dashboards or AI/BI dashboards are not the planned final dashboard direction.

The Power BI dashboard is a communication layer, not a modeling layer. It should consume governed serving tables created by `src/dashboard/register_powerbi_databricks_tables.py`. It must not recreate AO1 or AO2 scores, recalculate AO3 margins, retune thresholds, reassign segments, or introduce actual target/outcome columns into operational dashboard tables.

The serving-layer documentation identifies these tables as core dashboard inputs:

| Databricks serving table | Power BI semantic-model table |
| --- | --- |
| `powerbi_ao3_order_segments` | `AO3_Order_Segments` |
| `powerbi_ao1_ao2_test_scores` | `AO1_AO2_Test_Scores` |
| `powerbi_ao1_decision_threshold_policy` | `AO1_Decision_Threshold_Policy` |
| `powerbi_ao1_ao2_test_score_summary` | `AO1_AO2_Test_Score_Summary` |
| `powerbi_ao3_risk_margin_policy` | `AO3_Risk_Margin_Policy` |
| `powerbi_ao3_segment_summary` | `AO3_Segment_Summary` |
| `powerbi_ao3_benchmark_segment_summary` | `AO3_Benchmark_Segment_Summary` |
| `powerbi_ao3_benchmark_insights` | `AO3_Benchmark_Insights` |
| `powerbi_ao3_operational_recommendations` | `AO3_Operational_Recommendations` |
| `powerbi_ao1_model_validation` | `AO1_Model_Validation` |
| `powerbi_ao1_threshold_tradeoff` | `AO1_Threshold_Tradeoff` |
| `powerbi_ao1_confusion_by_threshold` | `AO1_Confusion_By_Threshold` |
| `powerbi_ao2_model_validation` | `AO2_Model_Validation` |
| `powerbi_ao2_evaluation_metrics` | `AO2_Evaluation_Metrics` |
| `powerbi_serving_layer_manifest` | QA manifest |

[INSERT TABLE: Final Power BI serving-layer inventory with manifest status - source: docs/powerbi_databricks_serving_layer.md and final Databricks serving-layer manifest]

The dashboard should support review of AO1 risk patterns and threshold implications, AO2 expected profitability and residual context, AO3 segment counts and operational actions, and governance information such as validation metrics and serving-layer table freshness. The main fact table is `AO3_Order_Segments`, with one scored order-item row from the common held-out AO1/AO2 test population.

Validation tables in the dashboard should remain clearly labeled as validation evidence. Held-out AO3 scored rows should be labeled as scored prediction outputs, not as realized intervention outcomes. This distinction is important because the dashboard helps managers inspect priorities but does not prove that the recommended actions have changed outcomes.

[TO UPDATE AFTER DASHBOARD FINALIZATION: insert screenshot and title of the first Power BI dashboard page published in PR #141]

[TO UPDATE AFTER DASHBOARD FINALIZATION: add final Power BI page inventory, including executive, AO1, AO2, AO3, and governance views if present]

[TO UPDATE AFTER DASHBOARD FINALIZATION: confirm final `.pbix` submission route if required by the course; no `.pbix` is claimed as present in Git]

[TO UPDATE AFTER DASHBOARD FINALIZATION: add final serving-layer manifest row counts if available and verified]

## Strategic and Operational Recommendations

The strategic recommendation is to use AO3 priority segments as the primary pre-dispatch decision view. AO3 is more useful than a risk-only or margin-only ranking because it combines service risk and expected economics into action-oriented groups.

`protect_high_value_at_risk` should be treated as the primary protection queue. These orders have high predicted late-delivery risk and positive predicted margin. Appropriate actions may include closer monitoring, proactive exception review, careful fulfillment tracking, and targeted service protection. The recommendation does not imply that every order in this segment should receive costly expedited shipping.

`expedite_selectively` should be handled through controlled review. These orders are high risk but have low or negative predicted margin. They may still matter for customer experience, contractual obligation, or strategic account reasons, but the predicted economics do not automatically support expensive intervention. This segment is small in the benchmark population, so future scoring runs should monitor whether its size changes.

`preserve_service` should be used to maintain service quality for high-margin orders with lower predicted delivery risk. These orders remain economically important, but the model evidence does not place them in the urgent high-risk queue. The appropriate focus is service reliability, monitoring, and avoiding unnecessary escalation.

`standard_process` should remain under normal fulfillment processes, with attention to margin drivers. These orders have lower predicted risk and low or negative predicted margin. They are not unimportant, but the current risk-margin framework does not justify urgent logistics intervention for them.

[INSERT TABLE: AO3 operational recommendation matrix - source: data/references/ao3_operational_recommendation_matrix.csv and docs/ao3_operational_recommendations.md]

Managers should also use the Power BI dashboard for governance review. The dashboard can support recurring review of segment counts, risk distributions, expected profit patterns, threshold implications, and serving-layer freshness. Thresholds should be recalibrated before future operational use if order patterns, service policies, margin structure, or intervention capacity change.

## Limitations, Ethics, and Responsible Use

The DataCo dataset is a public, anonymized, and partially synthetic secondary dataset. It supports academic analysis but does not fully represent a live enterprise supply chain with carrier contracts, fulfillment-center workloads, weather disruptions, holidays, customs delays, labor constraints, customer lifetime value, or real intervention costs.

The project does not establish causality. AO1 predicts late-delivery risk, AO2 estimates expected profitability, and AO3 creates decision segments, but none of these analyses proves that a specific intervention will reduce late delivery or improve profit. A controlled pilot, A/B test, or quasi-experimental evaluation would be required to evaluate realized intervention outcomes.

The project does not claim production deployment. Databricks, Spark, Delta, and Power BI are used to build a reproducible academic workflow and dashboard-serving layer. Production use would require additional access controls, refresh governance, monitoring, security review, drift detection, fairness review, incident handling, and operational integration.

AO1 has moderate recall at operationally manageable thresholds. It is useful for prioritization, but it is not a complete late-delivery detector. AO1 SHAP patterns, especially the dominant First Class shipping-mode effect and granular geography indicators, should be monitored and interpreted as model associations rather than causal relationships.

AO2 has limited explanatory power. Although Gradient Boosting improves RMSE and MAE over Ridge, R2 remains low and predictions are compressed toward the mean. The target-reconstruction audit accepted AO2 with caution. AO2 should support prioritization, not replace financial review.

AO3 depends on AO1 and AO2. Errors or instability in either upstream model can propagate into the risk-margin segments. The thresholds also depend on current validation policy and business assumptions. A future operational version should monitor segment stability and recalibrate thresholds as conditions change.

Responsible use requires human oversight. The model should not be used to penalize customers, geographies, products, or teams based solely on predicted risk or margin. Geography and customer-segment signals may reflect historical service patterns and could reproduce past inequities. Because a broader responsible-AI governance source has not yet been verified, the final report should keep ethics claims grounded in internal controls, transparent caveats, human review, and SHAP explanation limits. [APA TODO: responsible_ai_governance_reference_needed - missing verified responsible AI, model governance, or limitations source if broad governance claims remain]

## Future Research

Future research should add pre-shipment external variables that are not available in the current dataset. Candidate variables include weather, carrier capacity, route constraints, holiday peaks, fulfillment-center workload, customs or disruption indicators, and regional service constraints. These variables should be added only if they are available before shipment and can be incorporated without leakage.

Future work should evaluate the effect of interventions. AO3 identifies which orders may deserve differentiated action, but it does not measure whether those actions work. A controlled pilot or quasi-experimental design could compare protected high-value at-risk orders with similar unprotected orders.

The AO1 threshold and AO3 cutoffs should be recalibrated over time. The current risk cutoff of 0.35 and margin cutoff of 0.0 are defensible for this project, but future operations may need capacity-based, service-level, customer-value, or cost-sensitive thresholds.

AO2 profitability modeling could be improved with richer business context. Future data could include cost-to-serve, carrier cost, inventory status, returns, customer lifetime value, promotion strategy, and fulfillment-center assignment. These additions could improve the distinction between expected profit and near-formula commercial predictors if handled with target-policy discipline.

Power BI dashboard work should continue after final page finalization. Future dashboard improvements could include role-specific pages for operations, finance, and leadership; drill-through views; refresh monitoring; outcome tracking; and segment stability monitoring.

## Conclusion

This capstone develops a reproducible pre-shipment decision-support framework that combines late-delivery risk prediction, expected profitability estimation, risk-margin prioritization, and Power BI communication. The project answers the research question by showing how order-time and pre-dispatch attributes can support practical order prioritization when handled with leakage-control discipline and chronological validation.

H1 is supported on validation evidence because XGBoost outperformed Logistic Regression for AO1 late-delivery prediction, including ROC-AUC and recall. H2 is supported on validation evidence with modest improvement because Gradient Boosting improved RMSE and MAE over Ridge for AO2 profitability estimation. H3 is supported by AO3 segmentation and benchmark evidence because the combined risk-margin framework identifies operational groups not fully evident from risk-only or margin-only views.

The framework's value is not perfect prediction. Its value is the integration of a governed data pipeline, leakage-safe modeling, target-reconstruction caution, explainability, segment-based decision support, and a Power BI dashboard path that consumes governed Databricks serving tables. The final report should preserve the caveats that make the work defensible: no causal claim, no production-deployment claim, no unsupported final-test confirmation, and no fabricated dashboard or reference evidence.

## Working References

Only the DataCo dataset reference is complete based on checked-in repository evidence. All other entries below require manual APA verification before final submission.

Constante, F., Silva, F., & Pereira, A. (2019). *DataCo Smart Supply Chain for Big Data Analysis* (Version 5) [Data set]. Mendeley Data. https://doi.org/10.17632/8gx2fvg2k6.5

Ahmed et al. (2025). Deep learning framework for interpretable supply chain forecasting using SOM, ANN, and SHAP. [APA TODO: ahmed_2025_interpretable_supply_chain_forecasting - missing full author initials, venue, volume/issue/pages, DOI or URL]

Armbrust et al. (2020). Delta Lake: High-performance ACID table storage over cloud object stores. [APA TODO: armbrust_2020_delta_lake - missing full author list, venue, DOI or URL]

Baryannis et al. (2019). Predicting supply chain risks using machine learning: The trade-off between performance and interpretability. [APA TODO: baryannis_2019_supply_chain_risk_ml - missing full author initials, venue, volume/issue/pages, DOI or URL]

Chen and Guestrin (2016). [APA TODO: chen_guestrin_2016_xgboost_method - missing full paper title, venue, publisher/proceedings, DOI or URL; use only if broad XGBoost methodology discussion remains]

Hastie, Tibshirani, and Friedman (2009). The Elements of Statistical Learning. [APA TODO: hastie_tibshirani_friedman_2009_esl - missing edition, publisher, URL if online version is cited]

Katangoori (2026). An empirical analysis of data-driven supply chain optimization in retail and logistics. [APA TODO: katangoori_2026_dataco_supply_chain_optimization - missing full publication metadata, DOI or URL, source-quality review]

Liu, Chen, Zheng, and Feng (2022). A Prediction Method with Data Leakage Suppression for Time Series. [APA TODO: liu_chen_zheng_feng_2022_leakage_suppression - missing venue or publisher, volume/issue/pages if applicable, DOI or URL; limitation: time-series leakage source, not supply-chain-specific]

Lundberg and Lee (2017). A unified approach to interpreting model predictions. [APA TODO: lundberg_lee_2017_shap - missing proceedings or venue details, DOI or URL]

Microsoft Learn. Power BI with Azure Databricks. [APA TODO: microsoft_learn_powerbi_azure_databricks - missing Microsoft Learn page date, URL, retrieval date if needed]

Ni, Xiao, and Lim (2020). A systematic review of the research trends of machine learning in supply chain management. [APA TODO: ni_xiao_lim_2020_ml_scm_review - missing full author initials, journal, volume/issue/pages, DOI or URL]

scikit-learn Ridge documentation. [APA TODO: scikit_learn_ridge_documentation - missing documentation page title, URL, retrieval date if used]

Toorajipour et al. (2021). Artificial intelligence in supply chain management: A systematic literature review. [APA TODO: toorajipour_2021_ai_scm_review - missing full author initials, journal, volume/issue/pages, DOI or URL]

XGBoost documentation, release 3.2.0 / current docs page. [APA TODO: xgboost_documentation_3_2_0 - missing documentation page title, organization, URL, retrieval date if needed]

Zaharia et al. (2016). Apache Spark: A unified engine for big data processing. [APA TODO: zaharia_2016_apache_spark - missing full author list, venue, DOI or URL]

Additional references to verify only if the final text keeps the relevant claims:

- `databricks_official_reference` for Databricks platform behavior and serving-layer context.
- `microsoft_powerbi_official_reference` for Power BI tooling mechanics beyond the Azure Databricks connector.
- `responsible_ai_governance_reference_needed` for broad responsible-AI or model-governance claims.
- `gopal_2024_bda_supply_chain_performance`, `douaioui_2024_late_delivery_resilience`, and `liang_2025_supply_chain_risk_decision_trees` if the literature review needs additional verified supply-chain analytics sources.

Sources intentionally excluded unless the final text changes:

- `chawla_2002_smote`, because the current AO1 workflow does not use SMOTE.
- `python_pandas_numpy_matplotlib_reference`, because routine package use is not discussed substantively.
- `databricks_power_platform_blog_optional`, because the report does not discuss Power Apps, Power Automate, or Copilot Studio integration.

## Appendices

### Appendix A. Artifact Index

Use `report/final_artifact_index.md` as the master navigation file for graders and reviewers. It links to README, Databricks setup, project orchestrator, testing strategy, AO1/AO2/AO3 docs, key tables, key figures, validators, dashboard docs, and final report artifacts. Some older dashboard-status language in existing navigation files should be reconciled before final submission if those files remain final-facing.

### Appendix B. Validation Summary

Use `report/final_validation_summary.md` and `docs/TESTING.md` to document local validators, Databricks/PySpark/Delta validators, AO1 validation status, AO2 validation status, AO3 validation status, dashboard serving-layer validation status, and known deferred items. The final validation appendix should distinguish local checks from checks requiring Databricks, PySpark, and Delta outputs.

### Appendix C. Data Dictionary and Schema

Include `docs/silver_schema_data_dictionary.md` and `data/references/silver_schema_data_dictionary.csv`. These files document cleaned Silver columns, data types, policy notes, lineage fields, and references to source metadata.

### Appendix D. Code Repository and Script Index

Use `docs/project_orchestrator.md` to summarize the executable workflow and major scripts. Key script families include `/src/data_engineering`, `/src/modeling`, `/src/dashboard`, `/notebooks/pipeline`, and `/tests/data_validation`.

### Appendix E. Model Metadata

Reference model metadata under:

- `models/ao1_late_delivery/`
- `models/ao2_profitability/`
- `models/ao3_integration/`

These metadata files document selected candidates, validation boundaries, threshold decisions, SHAP workflows, target-reconstruction audit status, AO3 scoring, segment assignment, and benchmark outputs.

### Appendix F. Power BI Serving-Layer Documentation

Include `docs/powerbi_databricks_serving_layer.md`, `dashboard/powerbi_semantic_model.md`, `dashboard/powerbi_measures.dax`, `src/dashboard/register_powerbi_databricks_tables.py`, and `tests/data_validation/validate_powerbi_databricks_serving_layer.py`. These artifacts document the direct Azure Databricks serving-table architecture for Power BI.

### Appendix G. Dashboard Artifacts

[TO UPDATE AFTER DASHBOARD FINALIZATION: add final Power BI dashboard screenshots, page names, and any course-required `.pbix` submission note; do not commit generated `.pbix` files unless repository policy changes]

### Appendix H. AI / Tooling Usage Note

AI coding assistance was used to help navigate repository artifacts and draft report documentation from checked-in sources. The assistant did not regenerate models, change metrics, create dashboard screenshots, create `.pbix` files, or fabricate evidence. All claims should be reviewed by the project team against the cited artifacts before final submission.
