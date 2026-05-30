# Predicting Late Delivery Risk and Explaining Order Profitability in a Global E-Commerce Supply Chain

## Executive Summary

This capstone builds a pre-shipment decision-support framework for global e-commerce supply chain operations using the DataCo Smart Supply Chain dataset. The project combines three analytical objectives:

- AO1 predicts late-delivery risk before dispatch.
- AO2 estimates expected order-level profitability before dispatch.
- AO3 combines those two model outputs into a risk-margin prioritization framework for operational triage.

The current checked-in evidence supports the three hypotheses with important caveats. H1 is supported on chronological validation evidence: the AO1 XGBoost classifier outperforms Logistic Regression on ROC-AUC and recall. H2 is supported on chronological validation evidence, but the improvement is modest: the AO2 Gradient Boosting Regressor improves RMSE and MAE relative to Ridge, while overall explanatory power remains limited. H3 is supported by AO3 benchmark and segmentation evidence: the combined risk-margin framework separates operational groups that are not fully visible from risk-only or margin-only views.

The framework should be interpreted as decision support, not as causal proof that intervention improves delivery outcomes or profitability. The dashboard deliverable is still pending. The repository retains Power BI support artifacts as one possible dashboard path, and the team is evaluating a native Databricks AI/BI dashboard alternative. No `.pbix` artifact is claimed in this report.

## Business Problem and Decision Context

E-commerce supply chain managers need to decide which orders should receive attention before shipment. Late deliveries can harm customer experience, but expensive interventions should be targeted because not every risky order has the same expected economic value.

The project addresses this decision problem by estimating two pre-dispatch signals for each order:

- predicted probability of late delivery;
- predicted expected order profitability.

AO3 then translates those predictions into operational segments so managers can distinguish high-value orders at risk from orders that should remain in normal processing or be reviewed selectively.

## Research Question

How can pre-shipment attributes available at order creation be used to build a practical pre-dispatch order-prioritization framework that combines late-delivery risk and expected order profitability in a global e-commerce supply chain?

## Hypotheses

**H1.** For late-delivery prediction, an XGBoost classifier will outperform logistic regression on held-out data, particularly in AUC-ROC and recall.

**H2.** For order-profitability estimation, a gradient boosting regressor will outperform linear or ridge regression on held-out data, particularly in RMSE and MAE.

**H3.** Combining predicted late-delivery risk and expected order profitability in a risk-margin framework will identify pre-dispatch priority groups that are not evident from either signal alone and therefore support differentiated operational actions.

## Data Source and Pipeline Overview

The project uses the DataCo Smart Supply Chain for Big Data Analysis dataset from Mendeley Data, version 5, DOI `10.17632/8gx2fvg2k6.5`. The verified structured dataset contains 180,519 rows and 53 columns. Source verification is documented in [docs/data_source_verification.md](../docs/data_source_verification.md).

The data pipeline follows the project Medallion architecture:

- Bronze preserves the raw source data without manual modification.
- Silver applies deterministic cleaning, type standardization, and lineage fields.
- Gold creates leakage-safe analytical tables for AO1 and AO2.
- Modeling and AO3 scripts generate validation, scoring, segmentation, and benchmark artifacts.

The Databricks-compatible workflow entry point is [notebooks/pipeline/run_project_workflow.py](../notebooks/pipeline/run_project_workflow.py), documented in [docs/project_orchestrator.md](../docs/project_orchestrator.md). Environment setup is documented in [docs/databricks_setup.md](../docs/databricks_setup.md).

## Leakage-Control and Pre-Shipment Feature Policy

The project is framed as pre-shipment decision support. Predictors must be available at order creation or before dispatch. Post-shipment outcomes, realized delivery status, actual shipping duration, target fields, direct target proxies, and target-derived fields are excluded from model inputs.

Key leakage-control sources:

- [docs/leakage_control_plan.md](../docs/leakage_control_plan.md)
- [docs/leakage_conceptual_screening.md](../docs/leakage_conceptual_screening.md)
- [docs/feature_availability_map.md](../docs/feature_availability_map.md)
- [docs/pre_gold_modeling_decisions.md](../docs/pre_gold_modeling_decisions.md)
- [docs/ao1_post_model_leakage_audit.md](../docs/ao1_post_model_leakage_audit.md)
- [docs/ao2_target_reconstruction_review.md](../docs/ao2_target_reconstruction_review.md)

For AO1, forbidden predictors include `Late_delivery_risk`, `Delivery_Status`, `Days_for_shipping_real`, `shipping_date_DateOrders`, `Order_Status`, and direct post-outcome proxies. For AO2, target and near-target reconstruction fields are excluded, including duplicate profit fields, profit ratios, direct profit outcomes, sales/order-value fields that would mechanically reconstruct the target, and post-shipment fields.

The AO2 target-reconstruction audit reached an `accepted_with_caution` decision. No forbidden predictor or dominant driver was detected, but approved commercial predictors still require cautious interpretation because expected profitability remains close to accounting logic.

## Chronological Split Strategy

The official split policy uses `order_date_DateOrders` as the chronological anchor. Rows are sorted by:

```text
order_date_DateOrders ASC,
Order_Id ASC,
Order_Item_Id ASC
```

The earliest 80% of each objective-specific Gold population is assigned to development, and the most recent 20% is reserved as the final held-out test partition. Inside development, model selection and validation use chronological inner splits. Preprocessing is fit only on the relevant training/development slice and then applied to validation or test rows without refitting.

The split policy is documented in [docs/chronological_split_policy.md](../docs/chronological_split_policy.md) and versioned in [data/references/chronological_split_policy.csv](../data/references/chronological_split_policy.csv).

## AO1 Late-Delivery-Risk Prediction

AO1 predicts the binary target `Late_delivery_risk` using pre-dispatch features. The baseline model is Logistic Regression, and the primary model is an XGBoost classifier.

Validation comparison from [docs/ao1_results_h1_validation.md](../docs/ao1_results_h1_validation.md):

| Model | ROC-AUC | PR-AUC | Accuracy | Precision at 0.50 | Recall at 0.50 | F1 at 0.50 | Log loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| XGBoost classifier | 0.7753 | 0.8489 | 0.7212 | 0.8890 | 0.5840 | 0.7049 | 0.5133 |
| Logistic Regression baseline | 0.7426 | 0.8307 | 0.6856 | 0.8296 | 0.5645 | 0.6718 | 0.5723 |

The selected AO1 operating threshold is 0.35, based on validation trade-offs that prioritize recall while keeping alert volume manageable. AO3 reuses this threshold to define high-risk orders. Threshold selection is documented in [docs/ao1_decision_threshold.md](../docs/ao1_decision_threshold.md).

H1 is supported on validation evidence. Final test performance should not be claimed from the AO1 validation artifacts.

## AO2 Profitability Estimation

AO2 estimates expected order-level profitability before dispatch using `Order_Profit_Per_Order` as the target. The baseline model is Ridge Regression, and the primary model is a Gradient Boosting Regressor.

Validation comparison from [docs/ao2_results_h2.md](../docs/ao2_results_h2.md):

| Metric | Ridge baseline | Gradient Boosting Regressor | Improvement |
| --- | ---: | ---: | ---: |
| Validation rows | 28,883 | 28,883 | - |
| RMSE | 96.8276 | 95.6203 | 1.2073 lower |
| MAE | 54.2191 | 52.6463 | 1.5729 lower |
| R-squared | -0.0133 | 0.0118 | 0.0251 higher |
| Median absolute error | 32.5591 | 31.3954 | 1.1637 lower |
| Wrong profit-sign share | 0.2536 | 0.1974 | 0.0562 lower |

H2 is supported on validation evidence, but the effect size is modest. The Gradient Boosting model improves RMSE and MAE over Ridge, but R-squared remains low and predictions are compressed toward the mean. AO2 should therefore be used as one input to decision support rather than as a precise order-profit forecast.

## AO3 Risk-Margin Prioritization Framework

AO3 combines:

- `ao1_predicted_late_delivery_probability`;
- `ao2_predicted_order_profit`;
- `ao3_predicted_margin = ao2_predicted_order_profit / ao3_order_value`.

The approved AO3 policy uses:

| Threshold | Value | Interpretation |
| --- | ---: | --- |
| Risk cutoff | 0.35 | AO1 high-risk threshold |
| Margin cutoff | 0.0 | Positive versus negative predicted margin |

The resulting operational segments are:

- `protect_high_value_at_risk`;
- `expedite_selectively`;
- `preserve_service`;
- `standard_process`;
- `requires_score_review`;
- `requires_margin_review`.

The AO3 benchmark evaluated 34,467 held-out scored orders. The two largest groups were `protect_high_value_at_risk` with 13,752 orders and `preserve_service` with 20,603 orders. The benchmark shows that margin-only prioritization would combine these two groups despite a large delivery-risk difference, while risk-only prioritization would combine some high-risk orders with opposite margin profiles.

H3 is supported by this segmentation and benchmark evidence, with caveats. AO3 demonstrates decision-layer separation of predicted-score groups. It does not prove that acting on those groups improves realized delivery or profit outcomes.

Primary AO3 sources:

- [docs/ao3_risk_margin_matrix.md](../docs/ao3_risk_margin_matrix.md)
- [docs/ao3_segment_assignment.md](../docs/ao3_segment_assignment.md)
- [docs/ao3_risk_margin_benchmark.md](../docs/ao3_risk_margin_benchmark.md)
- [docs/ao3_operational_recommendations.md](../docs/ao3_operational_recommendations.md)
- [docs/ao3_methodology_and_results.md](../docs/ao3_methodology_and_results.md)

## Results Summary Table for H1/H2/H3

| Hypothesis | Current evidence | Status | Caveat |
| --- | --- | --- | --- |
| H1 | XGBoost outperforms Logistic Regression on chronological validation ROC-AUC and recall. | Supported on validation evidence. | Final test performance is not claimed from validation artifacts. |
| H2 | Gradient Boosting improves validation RMSE and MAE over Ridge. | Supported on validation evidence, modest improvement. | AO2 has low R-squared, compressed predictions, and target-reconstruction caution. |
| H3 | AO3 benchmark separates operational groups that risk-only or margin-only views do not fully distinguish. | Supported by AO3 segmentation and benchmark evidence with caveats. | No causal claim and no realized intervention outcome evaluation. |

## Operational Interpretation

The AO3 framework supports differentiated pre-dispatch action:

| AO3 segment | Interpretation | Operational use |
| --- | --- | --- |
| `protect_high_value_at_risk` | High predicted late-delivery risk and high predicted margin. | Prioritize monitoring, exception handling, and targeted service protection. |
| `expedite_selectively` | High predicted risk and low predicted margin. | Review case by case before using scarce or costly expedited capacity. |
| `preserve_service` | Low predicted risk and high predicted margin. | Maintain service quality and monitor for risk drift. |
| `standard_process` | Low predicted risk and low predicted margin. | Use normal operating procedures and monitor pricing or cost drivers. |
| `requires_score_review` | Missing AO1 or AO2 score. | Treat as a scoring completeness issue before prioritization. |
| `requires_margin_review` | Missing or invalid margin denominator. | Treat as a data-quality issue before margin-based action. |

These recommendations should be used as a triage layer. They do not establish that an intervention will reduce lateness or increase profit.

## Dashboard Status Note

The dashboard deliverable is still pending. The repository contains Power BI semantic-model, DAX, and export-validation support artifacts as one possible implementation path, but the team is also evaluating a native Databricks AI/BI dashboard. This report does not document a final dashboard technology choice, does not claim generated Power BI exports are currently present, and does not claim a `.pbix` file exists.

Dashboard documentation:

- [dashboard/README.md](../dashboard/README.md)
- [dashboard/powerbi_semantic_model.md](../dashboard/powerbi_semantic_model.md)
- [dashboard/powerbi_measures.dax](../dashboard/powerbi_measures.dax)

## Limitations

- The project is a decision-support prototype, not a production deployment.
- AO1 and AO2 model conclusions are based on validation evidence unless a cited artifact explicitly states otherwise.
- AO3 uses held-out scored predictions for segmentation and benchmarking, but it does not evaluate realized outcomes or intervention effects.
- SHAP and feature-importance patterns are model associations, not causal explanations.
- AO2 profitability prediction remains methodologically sensitive because commercial predictors can sit close to accounting formulas.
- The dataset is public, anonymized, and partially synthetic, so operational findings should be validated before real-world deployment.
- The dashboard layer is not complete in the checked-in repository.

## Reproducibility and Validation

The project uses small committed reference artifacts, model metadata, report tables, and validation scripts to keep the work reviewable. Databricks/PySpark/Delta validators are required for jobs that read Delta tables under the project Volume. Local Python validators cover artifact contracts, documentation checks, model metadata, validation metric tables, AO2 target-reconstruction audit outputs, AO3 policy files, and dashboard export files when generated.

The final validation map is summarized in [report/final_validation_summary.md](final_validation_summary.md). The full testing strategy is documented in [docs/TESTING.md](../docs/TESTING.md).

## Ethical and Responsible-Use Considerations

The framework should be used to support human operational review, not to automatically deny service, penalize customers, or make unsupported claims about regions, products, or customer groups. Geography and customer-segment features may reflect historical operational patterns and should be monitored for unfair or unstable impacts. Any production use would require additional governance, monitoring, model drift checks, intervention outcome tracking, and human override processes.

## AI/Tooling Usage Note

AI coding assistance was used to help navigate the repository and draft final-facing documentation from checked-in artifacts. The AI assistant did not generate new model metrics, retrain models, build dashboard files, or create a `.pbix`. All conclusions in this draft should be reviewed by the project team against the cited artifacts before submission.

## References / Artifact Links

| Category | Link |
| --- | --- |
| Proposal summary | [docs/proposal/proposal_summary.md](../docs/proposal/proposal_summary.md) |
| Data source verification | [docs/data_source_verification.md](../docs/data_source_verification.md) |
| Databricks setup | [docs/databricks_setup.md](../docs/databricks_setup.md) |
| Project orchestrator | [docs/project_orchestrator.md](../docs/project_orchestrator.md) |
| Testing strategy | [docs/TESTING.md](../docs/TESTING.md) |
| AO1 results and H1 | [docs/ao1_results_h1_validation.md](../docs/ao1_results_h1_validation.md) |
| AO2 results and H2 | [docs/ao2_results_h2.md](../docs/ao2_results_h2.md) |
| AO3 methodology and results | [docs/ao3_methodology_and_results.md](../docs/ao3_methodology_and_results.md) |
| Final artifact index | [report/final_artifact_index.md](final_artifact_index.md) |
| Final validation summary | [report/final_validation_summary.md](final_validation_summary.md) |
