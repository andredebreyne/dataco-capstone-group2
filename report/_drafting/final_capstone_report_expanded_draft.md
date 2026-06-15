# Predicting Late Delivery Risk and Explaining Order Profitability in a Global E-Commerce Supply Chain

DAMO 699 Capstone Final Report Expanded Draft
Team: Group 2
Institution: [TO UPDATE]
Instructor: [TO UPDATE]
Date: [TO UPDATE]

## Abstract / Executive Summary

This project develops a leakage-safe pre-shipment decision-support framework for global e-commerce supply chain operations using the DataCo Smart Supply Chain dataset. The business problem is that supply chain managers need to prioritize orders before dispatch, when operational intervention is still possible, but late-delivery risk alone is not enough to guide action. A high-risk order with strong expected margin may justify early intervention, while a high-risk order with weak or negative expected margin may require more selective review. The project therefore combines late-delivery risk prediction, expected profitability estimation, and a risk-margin prioritization framework into one analytical workflow.

The research question is: How can pre-shipment attributes available at order creation be used to build a practical pre-dispatch order-prioritization framework that combines late-delivery risk and expected order profitability in a global e-commerce supply chain?

The project is organized around three analytical objectives. Analytical Objective 1 (AO1) predicts late-delivery risk using pre-shipment and order-time attributes. Analytical Objective 2 (AO2) estimates expected order-level profitability before dispatch. Analytical Objective 3 (AO3) combines the AO1 and AO2 outputs into a risk-margin prioritization framework. The final communication layer is a Power BI dashboard connected to governed Azure Databricks serving-layer tables.

The current evidence supports the project hypotheses with appropriate methodological caveats. H1 is supported on chronological validation evidence: the AO1 XGBoost classifier outperformed the Logistic Regression baseline on ROC-AUC, recall, and other validation metrics. H2 is supported on chronological validation evidence with modest improvement: the AO2 Gradient Boosting/XGBoost Regressor improved RMSE and MAE relative to the Ridge baseline, but explanatory power remained limited and the target-reconstruction audit accepted the model with caution. H3 is supported by AO3 segmentation and benchmark evidence: the combined risk-margin framework separated operational groups that were not fully visible from either risk-only or margin-only prioritization.

This draft does not claim causal impact, production deployment, or unsupported final-test confirmation. It distinguishes validation evidence for AO1 and AO2 from held-out scored evidence used for AO3 segmentation and benchmarking. The Power BI dashboard is the official visualization deliverable. The direct Power BI connection to Azure Databricks serving-layer tables worked, and the first dashboard page was published in PR #141 according to the team status update. Remaining dashboard screenshots and final page-level descriptions are marked as update points rather than blockers.

## Introduction and Business Problem

Late delivery is a recurring operational problem in e-commerce supply chains because customer expectations, planned shipping promises, order geography, product mix, and fulfillment constraints interact under time pressure. Managers often need to decide which orders require attention before dispatch, yet the available information is incomplete. Once an order has already shipped or a late delivery has already occurred, the decision window for preventive action is limited. A useful decision-support system should therefore operate at order creation or before shipment.

The DataCo capstone project frames this problem as a pre-shipment prioritization challenge rather than as a retrospective reporting exercise. The goal is not only to describe which orders were delivered late or which orders were profitable after the fact. The goal is to estimate signals that are available early enough to support operational action. In this setting, a late-delivery risk score can help identify orders likely to need intervention, while an expected profitability estimate can help managers determine where scarce intervention capacity is most economically justified.

The business problem also requires an integrated view. A risk-only ranking can flag orders that appear likely to arrive late, but it does not distinguish between valuable orders and orders with weak expected economics. A profit-only ranking can identify orders with stronger expected margin, but it does not show which of those orders are most at risk of service failure. AO3 addresses this limitation by combining predicted risk and predicted margin into a practical segmentation framework. This design supports differentiated actions such as protecting high-value at-risk orders, reviewing high-risk low-margin orders selectively, preserving service for lower-risk high-margin orders, and using standard processes for lower-risk low-margin orders.

The project is also shaped by academic and methodological requirements. Because the intended use case is pre-dispatch decision support, the analysis must avoid data leakage from post-shipment fields, realized delivery outcomes, target variables, and target-derived financial fields. A model that uses actual shipping duration or delivery status to predict lateness would be invalid for pre-shipment decision support. Similarly, a profitability model that reconstructs the target from direct accounting formulas would not provide defensible expected-profit estimation. The project therefore emphasizes feature availability, leakage control, chronological splitting, train-only preprocessing, validation artifacts, and transparent documentation.

The final Power BI dashboard is intended to communicate the results to managers. It connects to governed Databricks serving-layer tables rather than recreating scores, thresholds, margins, or segment assignments inside the dashboard. This design keeps the dashboard aligned with the analytical pipeline while still providing an accessible decision-support interface.

## Research Question, Objectives, and Hypotheses

The research question guiding this capstone is:

> How can pre-shipment attributes available at order creation be used to build a practical pre-dispatch order-prioritization framework that combines late-delivery risk and expected order profitability in a global e-commerce supply chain?

The project objectives are:

1. AO1: Predict late-delivery risk using pre-shipment and order-time attributes.
2. AO2: Estimate expected order profitability before dispatch.
3. AO3: Combine AO1 and AO2 predictions into a risk-margin prioritization framework.
4. Dashboard: Communicate the analytical results through Power BI using governed Databricks serving-layer tables.

The hypotheses are:

**H1.** For late-delivery prediction, an XGBoost classifier will outperform logistic regression on held-out data, particularly in AUC-ROC and recall.

**H2.** For order-profitability estimation, a gradient boosting regressor will outperform linear or ridge regression on held-out data, particularly in RMSE and MAE.

**H3.** Combining predicted late-delivery risk and expected order profitability in a risk-margin framework will identify pre-dispatch priority groups that are not evident from either signal alone and therefore support differentiated operational actions.

The hypotheses are intentionally connected. H1 and H2 produce the two predictive inputs required by H3. AO3 is not a separate modeling exercise that ignores AO1 and AO2. It is the decision layer that converts the upstream model outputs into a managerial prioritization framework.

| Objective | Primary question | Main output | Role in framework |
| --- | --- | --- | --- |
| AO1 | Which orders are likely to be delivered late? | Predicted late-delivery probability and high-risk flag | Risk signal for AO3 |
| AO2 | Which orders are expected to be more or less profitable? | Predicted order profit and derived predicted margin | Margin signal for AO3 |
| AO3 | Which orders should receive differentiated pre-dispatch action? | Risk-margin priority segment | Managerial decision-support layer |
| Dashboard | How can managers review and use the results? | Power BI dashboard connected to Databricks serving tables | Communication and governance layer |

## Literature Review / Analytical Context

Predictive analytics is widely used in supply chain settings to support forecasting, risk identification, and decision prioritization. In this project, the relevant literature context includes supply-chain disruption and delivery risk, machine learning classification, profitability estimation, explainable analytics, segmentation-based decision support, and business intelligence dashboards. Formal APA references still need to be verified before submission. The placeholders below should be replaced with full citations from the proposal, course materials, and method documentation.

[NEEDS APA SOURCE DETAILS: predictive analytics in supply chain management] Supply-chain analytics literature generally emphasizes that predictive models are most useful when they are linked to operational decisions. A late-delivery model that only reports historical performance is less valuable than one that helps managers identify orders at risk before shipment. The pre-shipment framing in this project follows that decision-support logic. The model inputs are restricted to information available at order creation or before dispatch, and downstream recommendations are designed around operational triage rather than retrospective explanation alone.

[NEEDS APA SOURCE DETAILS: machine learning for delivery risk and logistics prediction] Classification methods are commonly used when the outcome is categorical, such as whether an order will be late. Logistic Regression provides a transparent baseline because it is widely understood and can estimate a probability-like score under linear assumptions. Tree-based gradient boosting methods such as XGBoost can capture nonlinear relationships, interactions, and threshold effects that may exist in shipping mode, scheduled service windows, product mix, geography, and order timing. This provides the rationale for comparing Logistic Regression and XGBoost in AO1.

[NEEDS APA SOURCE DETAILS: profitability modeling and regression analytics] Profitability estimation is a regression problem because the target is a continuous order-level profit measure. Linear or Ridge Regression provides a baseline because it tests whether a simple regularized linear model can explain expected profit using approved pre-dispatch features. Gradient boosting regression is included because profitability patterns may involve nonlinear interactions among price, discount rate, quantity, product category, market, and planned shipping attributes. However, profitability modeling has a special target-reconstruction risk because many commercial variables can be close to accounting formulas. This project therefore treats AO2 results with caution and documents excluded financial fields.

[NEEDS APA SOURCE DETAILS: data leakage in predictive modeling] Leakage-safe modeling is central to the validity of this capstone. Data leakage occurs when the model uses information that would not be available at prediction time or that directly encodes the target. For AO1, examples include actual shipping duration, delivery status, shipping completion timestamps, and post-order status fields. For AO2, examples include duplicate profit fields, profit ratios, realized margin fields, and fields that mechanically reconstruct profit. The feature availability map, leakage-control plan, and target-reconstruction audit operationalize this principle.

[NEEDS APA SOURCE DETAILS: SHAP and explainable machine learning] Explainability is important because the project is not only trying to produce metrics; it is trying to support managerial interpretation and academic review. SHAP is used to summarize model driver patterns for the selected AO1 and AO2 models. The SHAP results are interpreted as model associations, not causal effects. This distinction is important because a feature can be predictive without being a controllable intervention lever.

[NEEDS APA SOURCE DETAILS: segmentation and decision-support frameworks] Segmentation supports decision-making by simplifying complex predictions into operational groups. AO3 uses predicted risk and predicted margin to create a 2x2 decision framework plus review categories. This approach keeps the final layer interpretable and action-oriented. An optional K-means extension was tested to see whether unsupervised clustering added insight, but the existing artifacts recommend not adopting it because the clusters mostly duplicate the 2x2 AO3 matrix.

[NEEDS APA SOURCE DETAILS: business intelligence dashboards and analytics communication] The Power BI dashboard is the communication layer that makes the analytical results usable for decision review. It should not recreate model logic inside the visualization tool. Instead, it should consume governed serving-layer tables from Databricks, show validated model and AO3 outputs, and preserve the distinction between validation metrics, held-out scored predictions, and operational recommendations.

## Data Source and Data Governance

The primary dataset is the DataCo Smart Supply Chain for Big Data Analysis dataset from Mendeley Data, version 5, DOI `10.17632/8gx2fvg2k6.5`. Source verification is documented in `docs/data_source_verification.md`. The verified structured dataset contains 180,519 data rows and 53 columns. The companion metadata file contains 52 metadata rows and supports variable definition review. The raw dataset was parsed using `latin-1` encoding and comma delimiters.

The dataset contains order, customer, product, shipping, logistics, and financial fields. Relevant fields include `Late_delivery_risk`, `Order Profit Per Order`, `Benefit per order`, `Order Item Profit Ratio`, `Sales`, `Order Item Total`, `Order Item Discount`, `Shipping Mode`, `Days for shipment (scheduled)`, `Days for shipping (real)`, `Delivery Status`, order dates, shipping dates, market, region, country, category, and customer segment. Not all of these fields are allowed as modeling predictors. Some are targets, post-outcome variables, or target proxies.

The project preserves the raw source in Bronze and avoids manual modification of raw data. This governance choice is important because it keeps the analysis reproducible. Cleaning, type standardization, feature engineering, split creation, modeling, evaluation, AO3 segmentation, and dashboard-serving outputs are all code-driven. The project also documents missing values and metadata mismatches. For example, the raw data source verification notes blank values in `Product Description`, `Order Zipcode`, `Customer Lname`, and `Customer Zipcode`. It also notes that `Order Zipcode` and `shipping date (DateOrders)` did not match the metadata exactly after trimming. These issues do not block ingestion but should remain documented.

| Data item | Verified detail |
| --- | --- |
| Dataset | DataCo Smart Supply Chain for Big Data Analysis |
| Source | Mendeley Data, version 5 |
| DOI | `10.17632/8gx2fvg2k6.5` |
| Structured dataset rows | 180,519 |
| Structured dataset columns | 53 |
| Companion metadata rows | 52 |
| License | CC BY 4.0, based on source verification document |
| Scope note | Structured supply-chain dataset is in scope; unstructured clickstream data is out of scope unless the project scope changes |

The dataset is public, anonymized, and partially synthetic. This limits the extent to which the results can be generalized to a real operating business without additional validation. The final report should treat the project as an academic decision-support prototype rather than a production-ready deployment.

## Data Engineering and Cloud Implementation

The project follows a simplified Medallion architecture using Bronze, Silver, and Gold layers. This architecture is documented in `docs/medallion_structure.md` and implemented through reusable scripts under `/src`. The Databricks-compatible workflow entry point is `notebooks/pipeline/run_project_workflow.py`, documented in `docs/project_orchestrator.md`.

Bronze is the raw ingestion layer. It preserves original DataCo source data with no manual transformation. Silver is the cleaned and standardized analytical layer. It applies deterministic cleaning, type standardization, lineage metadata, and quality-report generation. Silver does not fit modeling preprocessors such as imputers, encoders, scalers, target encoders, or resampling methods. Those learned transformations belong in model-specific pipelines and must be fit only on training data. Gold contains curated objective-specific analytical tables for AO1 and AO2 and downstream serving outputs for scoring, AO3, and dashboard use.

Databricks Community Edition is the standard execution environment. The documented preferred runtime is Databricks Runtime 14.3 LTS with Spark 3.5.0, with 13.3 LTS as a fallback if needed. The pipeline uses Spark and Delta paths under the configured volume root, defaulting to `/Volumes/workspace/default/raw_data`. The project also uses local committed reference artifacts under `data/references/` and report artifacts under `report/tables/` and `report/figures/`.

The orchestrator coordinates the major workflow steps. It includes environment validation, repository structure validation, volume setup, raw data checks, reference registration, Bronze ingestion, Silver cleaning, feature engineering, Gold table creation, chronological partitioning, preprocessing, model training, evaluation, SHAP explainability, AO2 target-reconstruction audit, AO1 threshold selection, AO1/AO2 held-out scoring, AO3 segment assignment, AO3 benchmarking, optional AO3 K-means extension, and Power BI serving-layer registration. Many steps are disabled by default to avoid accidental reruns. This is appropriate for final packaging because model artifacts and result tables should not be regenerated unless intentionally required.

Gold analytical tables are used for modeling because they create objective-specific, leakage-safe datasets. AO1 requires a table for late-delivery modeling that excludes post-outcome fields and applies the approved AO1 population policy. AO2 requires a profitability table that excludes target-reconstruction fields and reserves `ao3_order_value` only as a support denominator for AO3. This separation prevents the dashboard or later analysis from using raw fields that would violate the decision-time framing.

The Power BI serving layer is a separate dashboard-serving layer, not a modeling layer. The script `src/dashboard/register_powerbi_databricks_tables.py` publishes governed `powerbi_*` tables in Databricks SQL, defaulting to the `workspace.default` catalog and schema. These tables are designed for direct Power BI connection through the Azure Databricks connector. The serving layer does not recreate AO1 or AO2 scores, recalculate AO3 margins, retune thresholds, union unrelated artifacts, or expose final-test target or realized-outcome columns. The direct Power BI connection to Azure Databricks serving tables has worked according to the team update, and the first dashboard page was published in PR #141. Final screenshots and page-level details still need to be inserted after dashboard finalization.

## Leakage-Control and Chronological Split Methodology

The project is governed by a pre-shipment decision-time policy. A feature may be used for modeling only if it is known at order creation or can be derived from information available before shipment. This rule is documented in `docs/leakage_control_plan.md` and supported by `docs/feature_availability_map.md`, `data/references/feature_availability_map.csv`, `docs/pre_gold_modeling_decisions.md`, and the objective-specific model documents.

For AO1, forbidden predictors include `Late_delivery_risk`, `Delivery Status`, `Days for shipping (real)`, `shipping date (DateOrders)`, `Order Status`, and direct post-delivery outcome proxies. These fields are forbidden because they are either the target, known only after shipping or delivery, or likely to encode the target. AO1 uses `Late_delivery_risk` only as the classification target.

For AO2, the target is `Order_Profit_Per_Order`. Forbidden or suspicious predictors include duplicate profit fields, `Benefit_per_order`, `Order_Item_Profit_Ratio`, direct transformations of profit, realized margin fields, and commercial fields that mechanically reconstruct the target. The AO2 target-reconstruction audit also confirms that `ao3_order_value` is excluded from AO2 predictors and reserved only for AO3 margin construction. The final audit decision was `accepted_with_caution`, not unconditional acceptance.

The chronological split policy is documented in `docs/chronological_split_policy.md` and versioned in `data/references/chronological_split_policy.csv`. The split anchor is `order_date_DateOrders`, which represents order creation time and is available at decision time. Rows are sorted by:

```text
order_date_DateOrders ASC,
Order_Id ASC,
Order_Item_Id ASC
```

The earliest 80% of rows after deterministic sorting are assigned to development, and the most recent 20% are reserved as final held-out test rows. The split is computed separately for each objective-specific Gold table after objective-specific population rules are applied. Within the development partition, the project uses inner chronological validation slices for model comparison and threshold review. All preprocessing, encoding, scaling, imputation, candidate selection, resampling if used, threshold selection, and SHAP explainability must remain inside the training or validation boundary and must not use the final test partition for model selection.

This distinction matters throughout the final report. AO1 and AO2 hypothesis evidence is validation-stage evidence. AO3 uses a held-out scored population created by applying frozen AO1 and AO2 decisions to common test rows, but it does not use final-test target labels to calculate performance metrics. The AO3 benchmark is therefore a decision-layer comparison of predicted signals and segments, not a realized outcome evaluation.

## Analytical Methods

The project uses several analytics methods to satisfy the assignment requirement for advanced analytics while preserving the integrated decision-support design.

**Logistic Regression baseline for AO1.** Logistic Regression is the baseline binary classifier for late-delivery risk. It uses the AO1 Gold analytical table, approved chronological partitions, and preprocessing fit only on the training slice. Its role is to provide an interpretable linear benchmark against which the XGBoost classifier can be compared. The output is a predicted late-delivery probability and predicted label on the validation slice. Validation evidence includes ROC-AUC, PR-AUC, accuracy, precision, recall, F1, log loss, and confusion matrix values.

**XGBoost classifier for AO1.** The XGBoost classifier is the primary AO1 model. It is used because late-delivery risk may depend on nonlinear interactions among planned shipping information, service windows, order geography, product mix, and time features. The selected candidate is `deeper_conservative`. It outputs predicted late-delivery probabilities and supports the AO1 high-risk flag used by AO3. Model comparison and threshold selection are based on validation evidence only.

**Ridge Regression baseline for AO2.** Ridge Regression is the baseline regression model for expected profitability estimation. It provides a regularized linear comparison model and helps determine whether a nonlinear model adds value beyond a simpler baseline. The output is predicted `Order_Profit_Per_Order` on the validation slice.

**Gradient Boosting / XGBoost regression for AO2.** The AO2 primary model is an XGBoost Gradient Boosting Regressor with selected candidate `conservative_baseline`. It is used because profitability may depend on nonlinear relationships among approved commercial features, product mix, geography, order timing, quantity, discount rate, and planned shipping fields. Its output is predicted order profit, which AO3 later converts into predicted margin using the approved order-value denominator. The AO2 evaluation uses RMSE, MAE, R-squared, median absolute error, residual diagnostics, and wrong profit-sign share.

**SHAP explainability.** SHAP explainability is used for both AO1 and AO2. It supports model interpretation and post-model leakage review. SHAP values identify which transformed features most strongly influence model predictions on validation rows. The results are interpreted as model behavior, not as causal effects. A feature can be associated with higher predicted risk or profit without proving that changing the feature would change delivery or profit outcomes.

**AO3 risk-margin segmentation.** AO3 is a deterministic decision layer, not a new predictive model. It consumes AO1 predicted late-delivery probability, AO2 predicted order profit, and derived predicted margin. It applies the approved risk cutoff of 0.35 and margin cutoff of 0.0 to assign orders into operational segments. The framework compares combined risk-margin prioritization against risk-only and margin-only views.

**Optional K-means extension.** The optional K-means extension tested whether unsupervised clustering on AO3 decision signals added interpretive value beyond the 2x2 matrix. The final recommendation from `docs/ao3_kmeans_extension.md` is `do_not_adopt`. The selected `k = 3` solution had a silhouette score of 0.6859 and a smallest cluster share of 1.91%, but the clusters mostly duplicated the governed AO3 matrix. The extension is therefore documented as exploratory and non-adopted.

## AO1 Results: Late-Delivery Risk Prediction

AO1 predicts the binary target `Late_delivery_risk`, where `1` represents a historical late-delivery event and `0` represents a non-late delivery outcome under the approved AO1 target policy. The AO1 workflow uses the leakage-safe AO1 Gold analytical table, chronological partitions, approved preprocessing, Logistic Regression baseline, XGBoost primary model, evaluation pack, decision-threshold policy, SHAP explainability, and post-model leakage audit.

The AO1 validation partition contains 27,643 rows. The final test partition contains 34,553 rows but remains reserved for final evaluation and is not used in the H1 validation document. The shared validation comparison shows that XGBoost outperforms Logistic Regression across the reported metrics.

| Model | ROC-AUC | PR-AUC | Accuracy | Precision at 0.50 | Recall at 0.50 | F1 at 0.50 | Log loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| XGBoost classifier | 0.7753 | 0.8489 | 0.7212 | 0.8890 | 0.5840 | 0.7049 | 0.5133 |
| Logistic Regression baseline | 0.7426 | 0.8307 | 0.6856 | 0.8296 | 0.5645 | 0.6718 | 0.5723 |

The XGBoost classifier improves ROC-AUC by 0.0327 and recall by 0.0195 at the default 0.50 threshold. This supports H1 at the validation stage. The model also improves PR-AUC, accuracy, precision, F1, and log loss. The improvement is meaningful for the project because recall is operationally important: missing a late-risk order can prevent timely intervention. However, recall remains moderate, so AO1 should be positioned as a prioritization aid rather than a complete late-delivery detection solution.

The threshold-selection workflow does not use the default 0.50 threshold as the final operating threshold. The selected threshold is 0.35, based on validation trade-offs that prioritize recall while keeping the alert volume operationally manageable. At threshold 0.35, the XGBoost classifier has precision 0.8469, recall 0.6171, predicted positive rate 0.4154, 6,035 false negatives, and 1,758 false positives. This threshold becomes the AO3 high-risk cutoff.

AO1 explainability artifacts identify planned shipping and service-promise variables as important driver families. The dominant SHAP feature is `categorical__shipping_mode_normalized_first_class`, with mean absolute SHAP value 5.780122 and importance share 0.3810. Scheduled shipping days and shipping speed tier also appear as important features. Geography one-hot features are present among top drivers. These patterns are operationally plausible because planned service, scheduled duration, and geography are available before dispatch, but they require careful interpretation. The report should not claim that First Class shipping causes lateness; it should describe the result as a model association that should be monitored.

The AO1 post-model leakage audit found no reviewed SHAP driver resembling the AO1 target, actual shipping duration, delivery status, shipping completion status, final-test labels, realized profit, or another direct post-outcome proxy. The audit concluded that AO1 is acceptable to continue toward reporting and AO3 integration under a leakage-safe-with-caveats status.

The H1 conclusion for the final report should be: validation evidence supports H1 because XGBoost outperformed Logistic Regression for late-delivery prediction, particularly in ROC-AUC and recall, while preserving the leakage-control and validation boundaries. This conclusion should remain explicitly tied to validation evidence unless a separately verified final-test evaluation artifact is added.

## AO2 Results: Profitability Estimation

AO2 estimates expected order-level profitability before dispatch. The target is `Order_Profit_Per_Order`. The selected target is an economic outcome and must not be treated as known at dispatch time. The model output is an expected profitability estimate that supports prioritization, not a guaranteed accounting result.

The AO2 predictor policy excludes target, proxy, duplicate, post-shipment, and near-formula commercial fields. Excluded fields include `Benefit_per_order`, `Order_Item_Profit_Ratio`, `Order_Item_Total`, `ao3_order_value`, `Sales`, `Sales_per_customer`, `Product_Price`, `Order_Item_Discount`, realized margin fields, profit-ratio fields, direct profit outcome fields, and delivery outcome fields. Approved commercial predictors such as `item_unit_price`, `item_discount_rate`, and `order_item_quantity` are allowed but require caution because they remain close to the commercial calculation context.

The AO2 validation comparison uses 28,883 validation rows. The final test partition contains 36,104 rows and remains reserved for future final evaluation. The models compared are Ridge Regression with candidate `fixed_alpha_1_0` and XGBoost Gradient Boosting Regressor with candidate `conservative_baseline`.

| Metric | Ridge baseline | Gradient Boosting Regressor | Improvement |
| --- | ---: | ---: | ---: |
| Validation rows | 28,883 | 28,883 | - |
| RMSE | 96.8276 | 95.6203 | 1.2073 lower |
| MAE | 54.2191 | 52.6463 | 1.5729 lower |
| R-squared | -0.0133 | 0.0118 | 0.0251 higher |
| Median absolute error | 32.5591 | 31.3954 | 1.1637 lower |
| Mean error / bias | 0.6453 | 0.9627 | Slightly more underprediction |
| Wrong profit-sign share | 0.2536 | 0.1974 | 0.0562 lower |

The Gradient Boosting Regressor improves RMSE and MAE relative to Ridge, which supports H2 on validation evidence. It also improves R-squared from slightly negative to slightly positive and reduces wrong profit-sign share from 0.2536 to 0.1974. However, the improvement is modest. The selected model's R-squared is only 0.0118, indicating limited explanatory power for individual profit values.

Residual diagnostics reinforce this caution. The Gradient Boosting model has residual mean 0.9627, residual standard deviation 95.6171, residual median 15.3847, and absolute-error p90 110.3725. Ridge has residual mean 0.6453, residual standard deviation 96.8271, residual median 15.6653, and absolute-error p90 112.9203. Both models compress predictions toward the mean and miss some extreme-profit or severe-loss cases. This means AO2 can help rank and approximate expected profitability, but it should not be used as a precise standalone profit forecast.

AO2 SHAP explainability identifies commercial price, geography, product mix, discount rate, and quantity as important driver families. `numeric_continuous__item_unit_price` ranks first among SHAP drivers. Product and geography one-hot features also appear among top drivers. These patterns are plausible for profitability but require caution. SHAP results are associations, not causal effects, and approved commercial predictors remain near the target formula context.

The AO2 target-reconstruction audit reviewed the selected predictor set, feature importance, SHAP drivers, and validation evidence. The final decision was `accepted_with_caution`. The audit found zero forbidden feature rows, 1,308 caution-status reviewed features, passed predictor audit status, passed SHAP driver audit status, passed feature-importance audit status, and no detection of `ao3_order_value` as an AO2 predictor or driver. The audit did not perform a formal ablation rerun because the issue guardrails prohibited retraining. The conclusion is that AO2 is defensible for pre-dispatch expected-profitability estimation, but it should not be presented as a formula-like profit calculation.

The H2 conclusion for the final report should be: validation evidence supports H2 because the Gradient Boosting Regressor improved RMSE and MAE relative to Ridge. The support is modest, and the model remains limited by low explanatory power, residual error, compressed predictions, and target-reconstruction caution.

## AO3 Results: Risk-Margin Prioritization Framework

AO3 integrates AO1 and AO2 into the final decision-support layer. It consumes two model outputs for each scored order: `ao1_predicted_late_delivery_probability` from the AO1 XGBoost classifier and `ao2_predicted_order_profit` from the AO2 Gradient Boosting Regressor. It also derives predicted margin:

```text
ao3_predicted_margin = ao2_predicted_order_profit / ao3_order_value
```

The denominator `ao3_order_value` is reserved as an AO3 support field and is excluded from AO2 predictors. This preserves the distinction between predicted profit estimation and downstream margin construction.

The approved AO3 policy applies a risk cutoff of 0.35 and a margin cutoff of 0.0. Orders with predicted late-delivery probability greater than or equal to 0.35 are considered high risk. Orders with predicted margin greater than or equal to 0.0 are considered high margin. The segment rules create four operational segments and two review categories:

| Segment | Definition | Operational interpretation |
| --- | --- | --- |
| `protect_high_value_at_risk` | High risk and high margin | Prioritize protection and exception handling |
| `expedite_selectively` | High risk and low margin | Review before costly intervention |
| `preserve_service` | Low risk and high margin | Maintain service quality without escalation |
| `standard_process` | Low risk and low margin | Use normal process and monitor margin |
| `requires_score_review` | Missing AO1 or AO2 score | Hold prioritization until scores are reviewed |
| `requires_margin_review` | Missing or invalid margin denominator | Hold margin-based action until denominator is reviewed |

The AO3 benchmark evaluated 34,467 held-out scored orders. These rows come from the common AO1/AO2 test scoring population, but actual target columns are excluded from the scored output. AO3 therefore uses held-out prediction signals for segmentation, not realized delivery or profit outcomes.

| AO3 segment | Count | Share | Avg predicted risk | Avg predicted profit | Avg predicted margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| `protect_high_value_at_risk` | 13,752 | 39.9% | 0.832 | 21.61 | 0.126 |
| `preserve_service` | 20,603 | 59.8% | 0.319 | 21.60 | 0.126 |
| `expedite_selectively` | 52 | 0.15% | 0.811 | -14.64 | -0.127 |
| `standard_process` | 60 | 0.17% | 0.298 | -20.61 | -0.293 |
| `requires_score_review` | 0 | 0.0% | n/a | n/a | n/a |
| `requires_margin_review` | 0 | 0.0% | n/a | n/a | n/a |

The benchmark supports H3 because the combined risk-margin view reveals decision groups that single-signal views do not fully distinguish. Margin-only prioritization would group `protect_high_value_at_risk` and `preserve_service` together because both have positive predicted margins and nearly identical average predicted profit. However, their average predicted late-delivery risk differs substantially: 0.832 versus 0.319. AO3 separates them into urgent high-value protection and preserve-service handling.

Risk-only prioritization would group `protect_high_value_at_risk` and `expedite_selectively` together because both are high risk. However, their predicted economics differ sharply: average predicted profit is 21.61 for `protect_high_value_at_risk` and -14.64 for `expedite_selectively`. AO3 separates these into different action queues. The risk-only differentiation is weaker in this held-out sample because 99.6% of high-risk orders are also high margin, but the difference still illustrates why combining risk and margin is more informative than either signal alone.

The AO3 benchmark insights show 34,467 total scored orders, 13,804 high-risk orders, and 34,355 high-margin orders. Among high-margin orders, 40.0% are high-risk protection priorities and 60.0% are lower-risk preserve-service orders. This is the primary dimension on which AO3 adds decision-layer value in the benchmark population.

The optional K-means extension was not adopted. The selected `k = 3` solution had inertia 19,671.6795, silhouette score 0.6859, and a minimum cluster share of 1.91%. The generated artifacts concluded that the clusters mostly duplicated the AO3 matrix. The final recommendation was `do_not_adopt`, which supports keeping the AO3 framework simple, explainable, and manager-readable.

The H3 conclusion for the final report should be: AO3 is supported by segmentation and benchmark evidence with caveats. It adds decision-layer value relative to risk-only and margin-only views, but it does not prove that intervention improves realized delivery or profit outcomes.

## Power BI Dashboard and Visualization Layer

Power BI is the official dashboard deliverable for this project. The dashboard is designed to communicate AO1, AO2, and AO3 results to managers through governed tables rather than through manually recreated logic. The selected architecture is a direct Power BI connection to Azure Databricks serving-layer tables. According to the team status update, this connection worked, and the first Power BI dashboard page was published in PR #141.

The dashboard-serving layer is documented in `docs/powerbi_databricks_serving_layer.md`. The entry point is:

```text
src/dashboard/register_powerbi_databricks_tables.py
```

This script publishes one managed Databricks SQL table per governed dashboard artifact under the configured catalog and schema, defaulting to `workspace.default`. The tables are prefixed with `powerbi_` and are designed to be discovered by Power BI Desktop through the Azure Databricks connector. The serving layer also publishes a `powerbi_serving_layer_manifest` table for row-count and source-audit checks.

| Databricks serving table | Power BI semantic model table |
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

The dashboard should support several review tasks. It should show AO1 risk patterns and threshold implications, AO2 expected profitability and residual context, AO3 segment counts and action categories, and governance information such as model-validation tables and serving-layer manifest checks. The main fact table is `AO3_Order_Segments`, which has one scored order-item row from the common held-out AO1/AO2 test population. Important fields include `Order_Id`, `Order_Item_Id`, `order_date_DateOrders`, `ao1_predicted_late_delivery_probability`, `ao1_high_risk_flag`, `ao2_predicted_order_profit`, `ao3_order_value`, `ao3_predicted_margin`, `ao3_high_margin_flag`, and `ao3_priority_segment`.

Power BI must not recreate AO1 or AO2 scores, AO3 margins, thresholds, or segment assignments. It should consume the governed serving tables. Target and realized outcome columns must not be introduced into operational dashboard tables. Validation metrics should remain labeled as validation evidence, not final-test performance.

`.pbix` files are not tracked in Git because project documentation and `.gitignore` exclude dashboard `.pbix` artifacts. If a `.pbix` is required for final submission, it should be submitted outside Git or rebuilt locally from `dashboard/powerbi_semantic_model.md`, `dashboard/powerbi_measures.dax`, and the Azure Databricks connector instructions.

[TO UPDATE AFTER DASHBOARD FINALIZATION] Add screenshot and title of the first Power BI dashboard page published in PR #141.

[TO UPDATE AFTER DASHBOARD FINALIZATION] Add final page inventory, including AO1, AO2, AO3, executive summary, and governance views if present.

[TO UPDATE AFTER DASHBOARD FINALIZATION] Confirm final `.pbix` submission route if required by the course.

## Strategic and Operational Recommendations

The recommendations follow directly from AO3 because AO3 is the integrated decision-support layer.

First, managers should use the AO3 priority segment rather than relying only on risk-only or margin-only ranking. The benchmark shows that margin-only prioritization would combine high-margin orders with very different risk levels, while risk-only prioritization would combine high-risk orders with different margin profiles. The combined view is more aligned with operational action.

Second, `protect_high_value_at_risk` should be treated as the primary protection queue. These orders have high predicted late-delivery risk and high predicted margin. Appropriate actions may include closer monitoring, proactive exception review, careful fulfillment tracking, and targeted service protection. The recommendation does not imply that every order in this segment should receive expensive expedited shipping. Intervention costs still need managerial judgment.

Third, `expedite_selectively` should be handled through controlled review. These orders have high predicted risk but low or negative predicted margin. They may still matter for customer experience, contractual obligations, or strategic accounts, but the predicted economics do not automatically support costly intervention. This group is small in the benchmark population, so future scoring runs should monitor whether its size changes.

Fourth, `preserve_service` should be used to maintain service quality for orders with high predicted margin but lower predicted delivery risk. These orders do not require the same urgent intervention as high-risk high-margin orders, but they remain important because they represent valuable expected economics. The operational focus should be reliability, monitoring, and avoiding unnecessary escalation.

Fifth, `standard_process` should remain under normal fulfillment operations, with attention to pricing and cost drivers because the group has low predicted margin. This does not mean these orders are unimportant; it means the model evidence does not justify urgent logistics intervention based on the current risk-margin framework.

Sixth, the Power BI dashboard should become part of a recurring review cadence. Managers can review segment counts, risk distributions, expected profit patterns, threshold implications, and recommendation categories. The dashboard should also support governance by showing the scoring period, model-validation context, and serving-layer table freshness.

Finally, the team should monitor model performance and recalibrate thresholds over time. The AO1 risk cutoff of 0.35 and AO3 margin cutoff of 0.0 are defensible for this project, but future data may shift. Any future operational deployment should include drift monitoring, threshold review, and outcome tracking.

## Limitations, Ethics, and Responsible Use

The project has several limitations. The DataCo dataset is a public, anonymized, and partially synthetic secondary dataset. It is valuable for academic analysis, but it does not fully represent a live enterprise environment with carrier contracts, fulfillment-center capacity, weather disruptions, geopolitical events, customer lifetime value, or real-time operational constraints.

The project does not establish causality. AO1 predicts late-delivery risk, AO2 estimates expected profitability, and AO3 creates decision segments, but none of these analyses proves that a specific intervention will reduce late deliveries or increase profit. A live intervention test or controlled pilot would be required for causal evaluation.

The project does not claim production deployment. Databricks, Spark, Delta, and Power BI are used to build a reproducible academic workflow and dashboard-serving layer, but production deployment would require additional monitoring, security, access control, data-refresh governance, and operational integration.

AO1 has moderate recall at operational thresholds. It is useful as a prioritization aid but should not be treated as a perfect late-delivery detector. AO1 SHAP patterns, especially the dominant First Class shipping-mode effect and granular geography indicators, require careful monitoring and should not be interpreted causally.

AO2 has modest explanatory power. Although Gradient Boosting improves RMSE and MAE over Ridge, R-squared remains low and predictions are compressed toward the mean. The target-reconstruction audit accepted the model with caution. This means AO2 should support prioritization but should not be treated as precise accounting.

AO3 depends on AO1 and AO2. If upstream predictions are unstable or applied to a population unlike the training data, AO3 segments may become unreliable. The risk cutoff and margin cutoff may need recalibration for future periods. AO3 recommendations are triage guidance, not automated decisions.

Responsible use requires human oversight. The model should not be used to penalize customers, regions, or products based solely on predicted risk or margin. Geography and customer-segment features may reflect historical operations and could reproduce past service patterns. A future production version should include fairness review, stakeholder review, and monitoring for unintended impacts.

## Future Research

Future research should add external variables that are not available in the current dataset, such as weather, carrier capacity, fulfillment-center workload, holiday peaks, traffic or route constraints, disruption indicators, and geopolitical or customs-related factors. These variables could improve the realism of late-delivery prediction if they are available before shipment.

Future work should also evaluate the effect of interventions. AO3 identifies orders that may deserve different actions, but it does not measure whether those actions work. A controlled pilot, A/B test, or quasi-experimental design could compare intervention outcomes for protected high-value at-risk orders against similar untreated orders.

The AO1 threshold and AO3 cutoffs should be recalibrated over time. The current risk threshold of 0.35 is based on validation trade-offs, and the margin cutoff of 0.0 separates positive from negative predicted margin. Future operational use may require alternative thresholds based on capacity, service-level agreements, margin targets, or customer value.

AO2 profitability modeling could be extended with stronger business context if available. Future data might include cost-to-serve, carrier cost, return behavior, customer lifetime value, inventory availability, and promotion strategy. These additions could help separate true profit drivers from near-formula commercial predictors.

Power BI dashboard work should continue after final page finalization. Future dashboard improvements could include role-specific views for operations, finance, and leadership; refresh monitoring; drill-through views; and outcome tracking once realized intervention data exists.

## Conclusion

This capstone develops a reproducible pre-shipment decision-support framework that combines late-delivery risk prediction, expected profitability estimation, and risk-margin prioritization. The project answers the research question by showing how order-time and pre-dispatch attributes can support a practical prioritization framework when handled with leakage-control discipline and chronological validation.

H1 is supported on validation evidence because XGBoost outperformed Logistic Regression for AO1 late-delivery prediction, including ROC-AUC and recall. H2 is supported on validation evidence with modest improvement because Gradient Boosting improved RMSE and MAE over Ridge for AO2 profitability estimation. H3 is supported by AO3 segmentation and benchmark evidence because the combined risk-margin framework identifies operational groups not fully evident from risk-only or margin-only views.

The project's value is not that it produces perfect predictions. Its value is that it integrates predictive modeling, profitability estimation, leakage control, chronological validation, explainability, segmentation, and Power BI communication into one defensible academic workflow. The final framework supports managerial triage while preserving caveats about validation evidence, target reconstruction, non-causality, and the need for future outcome evaluation.

## References

Constante, F., Silva, F., & Pereira, A. (2019). *DataCo Smart Supply Chain for Big Data Analysis* (Version 5) [Data set]. Mendeley Data. https://doi.org/10.17632/8gx2fvg2k6.5

[NEEDS APA SOURCE DETAILS: XGBoost original paper or official documentation]

[NEEDS APA SOURCE DETAILS: SHAP original paper or official documentation]

[NEEDS APA SOURCE DETAILS: scikit-learn documentation for Logistic Regression, Ridge Regression, metrics, and K-means]

[NEEDS APA SOURCE DETAILS: Apache Spark documentation if cited]

[NEEDS APA SOURCE DETAILS: Delta Lake documentation if cited]

[NEEDS APA SOURCE DETAILS: Databricks documentation if cited]

[NEEDS APA SOURCE DETAILS: Microsoft Power BI Azure Databricks connector documentation if cited]

[NEEDS APA SOURCE DETAILS: supply chain analytics literature used in the proposal or course materials]

[NEEDS APA SOURCE DETAILS: predictive analytics and decision-support literature]

[NEEDS APA SOURCE DETAILS: responsible AI, model governance, or explainability literature]

## Appendices

### Appendix A. Artifact Index

Use `report/final_artifact_index.md` as the master artifact navigation file. It links to README, Databricks setup, project orchestrator, testing strategy, AO1/AO2/AO3 docs, key report tables, key figures, validators, dashboard docs, and final report artifacts.

### Appendix B. Validation Summary

Use `report/final_validation_summary.md` and `docs/TESTING.md` to document local validators, Databricks/PySpark/Delta validators, AO1 validation status, AO2 validation status, AO3 validation status, and dashboard/export validation status.

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

[TO UPDATE AFTER DASHBOARD FINALIZATION] Add final Power BI dashboard screenshots, page names, and any course-required `.pbix` submission note. Do not commit generated `.pbix` files unless repository policy changes.

### Appendix H. AI / Tooling Usage Note

AI coding assistance was used to help navigate repository artifacts and draft report documentation from checked-in sources. The assistant did not regenerate models, change metrics, create dashboard screenshots, create `.pbix` files, or fabricate evidence. All claims should be reviewed by the project team against the cited artifacts before final submission.
