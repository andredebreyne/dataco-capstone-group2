# Final Artifact Index

This index points graders and reviewers to the checked-in evidence for the DataCo capstone, including the finalized Power BI dashboard documentation and supporting report assets.

## Start Here

| Artifact | Purpose |
| --- | --- |
| [README.md](../README.md) | Repository overview, status, and final navigation. |
| [report/Group_2_-_Capstone_DataCo_Report_final.docx](Group_2_-_Capstone_DataCo_Report_final.docx) | Final academic report document. |
| [report/final_capstone_report_final_markdown.md](final_capstone_report_final_markdown.md) | Final report Markdown source and appendices. |
| [report/final_validation_summary.md](final_validation_summary.md) | Final-facing validation status by local, Databricks, AO1, AO2, AO3, and dashboard checks. |
| [report/final_submission_checklist.md](final_submission_checklist.md) | Final packaging and manual-submission checklist. |
| [report/README.md](README.md) | Report folder guide, final evidence map, and historical drafting location. |
| [docs/proposal/proposal_summary.md](../docs/proposal/proposal_summary.md) | Proposal-aligned research framing, hypotheses, and scope. |

## Environment and Workflow

| Artifact | Purpose |
| --- | --- |
| [docs/databricks_setup.md](../docs/databricks_setup.md) | Databricks Community Edition setup and runtime guidance. |
| [docs/medallion_structure.md](../docs/medallion_structure.md) | Bronze, Silver, Gold data architecture. |
| [docs/project_orchestrator.md](../docs/project_orchestrator.md) | Main Databricks-compatible workflow inventory and flags. |
| [notebooks/pipeline/run_project_workflow.py](../notebooks/pipeline/run_project_workflow.py) | Project orchestrator script. |
| [docs/git_strategy.md](../docs/git_strategy.md) | Branching and PR workflow. |

## Data Source and Governance

| Artifact | Purpose |
| --- | --- |
| [docs/data_source_verification.md](../docs/data_source_verification.md) | Verified DataCo source, row count, column count, and checksums. |
| [docs/silver_schema_data_dictionary.md](../docs/silver_schema_data_dictionary.md) | Silver schema and data dictionary. |
| [data/references/silver_schema_data_dictionary.csv](../data/references/silver_schema_data_dictionary.csv) | Machine-checkable Silver dictionary reference. |
| [docs/silver_cleaning_rules.md](../docs/silver_cleaning_rules.md) | Silver cleaning policy. |
| [docs/feature_availability_map.md](../docs/feature_availability_map.md) | Decision-time feature availability documentation. |
| [data/references/feature_availability_map.csv](../data/references/feature_availability_map.csv) | Feature availability reference table. |
| [docs/leakage_control_plan.md](../docs/leakage_control_plan.md) | Leakage-control policy for AO1, AO2, and AO3. |
| [docs/leakage_conceptual_screening.md](../docs/leakage_conceptual_screening.md) | Conceptual leakage screening evidence. |
| [docs/pre_gold_modeling_decisions.md](../docs/pre_gold_modeling_decisions.md) | Pre-Gold modeling inclusion/exclusion decisions. |
| [docs/chronological_split_policy.md](../docs/chronological_split_policy.md) | Master chronological split policy. |
| [data/references/chronological_split_policy.csv](../data/references/chronological_split_policy.csv) | Versioned chronological split policy. |

## Testing and Validation

| Artifact | Purpose |
| --- | --- |
| [docs/TESTING.md](../docs/TESTING.md) | Current testing strategy and command groups. |
| [tests/data_validation](../tests/data_validation) | Validation scripts for data, governance, modeling, AO3, and dashboard export artifacts. |
| [tests/data_validation/validate_silver_schema_dictionary.py](../tests/data_validation/validate_silver_schema_dictionary.py) | Local Silver dictionary validator. |
| [tests/data_validation/validate_leakage_conceptual_screening.py](../tests/data_validation/validate_leakage_conceptual_screening.py) | Local leakage screening validator. |
| [tests/data_validation/validate_chronological_split_policy.py](../tests/data_validation/validate_chronological_split_policy.py) | Local split-policy validator. |
| [tests/data_validation/test_silver_quality.py](../tests/data_validation/test_silver_quality.py) | Databricks/PySpark/Delta Silver quality validator. |
| [tests/data_validation/test_gold_ao1_table.py](../tests/data_validation/test_gold_ao1_table.py) | Databricks/PySpark/Delta AO1 Gold validator. |
| [tests/data_validation/test_gold_ao2_table.py](../tests/data_validation/test_gold_ao2_table.py) | Databricks/PySpark/Delta AO2 Gold validator. |

## AO1 Target, Pipeline, and Results

| Artifact | Purpose |
| --- | --- |
| [docs/ao1_target_definition.md](../docs/ao1_target_definition.md) | AO1 target definition and target policy. |
| [docs/ao1_chronological_partitions.md](../docs/ao1_chronological_partitions.md) | AO1 partitioning. |
| [docs/ao1_preprocessing_pipeline.md](../docs/ao1_preprocessing_pipeline.md) | AO1 preprocessing contract. |
| [docs/ao1_logistic_regression_baseline.md](../docs/ao1_logistic_regression_baseline.md) | AO1 baseline model. |
| [docs/ao1_xgboost_classifier.md](../docs/ao1_xgboost_classifier.md) | AO1 primary model. |
| [docs/ao1_model_evaluation.md](../docs/ao1_model_evaluation.md) | AO1 validation evaluation pack. |
| [docs/ao1_decision_threshold.md](../docs/ao1_decision_threshold.md) | AO1 threshold policy. |
| [docs/ao1_shap_explainability.md](../docs/ao1_shap_explainability.md) | AO1 explainability. |
| [docs/ao1_post_model_leakage_audit.md](../docs/ao1_post_model_leakage_audit.md) | AO1 post-model leakage audit. |
| [docs/ao1_results_h1_validation.md](../docs/ao1_results_h1_validation.md) | Report-ready AO1 H1 result summary. |

## AO1 Key Tables and Figures

| Artifact | Purpose |
| --- | --- |
| [report/tables/ao1_model_validation_comparison.csv](tables/ao1_model_validation_comparison.csv) | Logistic Regression versus XGBoost validation metrics. |
| [report/tables/ao1_threshold_tradeoff_grid.csv](tables/ao1_threshold_tradeoff_grid.csv) | AO1 threshold trade-off grid. |
| [report/tables/ao1_confusion_matrix_by_threshold.csv](tables/ao1_confusion_matrix_by_threshold.csv) | Confusion matrix by threshold. |
| [report/tables/ao1_shap_driver_summary.csv](tables/ao1_shap_driver_summary.csv) | AO1 SHAP driver summary. |
| [report/figures/ao1_shap_top_features.png](figures/ao1_shap_top_features.png) | AO1 SHAP top-features figure. |
| [report/figures/eda/ao1_class_imbalance_overall.svg](figures/eda/ao1_class_imbalance_overall.svg) | AO1 class imbalance figure. |

## AO1 Validators

| Artifact | Purpose |
| --- | --- |
| [tests/data_validation/validate_ao1_chronological_partitions.py](../tests/data_validation/validate_ao1_chronological_partitions.py) | Databricks AO1 partition validator. |
| [tests/data_validation/validate_ao1_preprocessing_pipeline.py](../tests/data_validation/validate_ao1_preprocessing_pipeline.py) | Hybrid AO1 preprocessing validator. |
| [tests/data_validation/validate_ao1_logistic_regression_baseline.py](../tests/data_validation/validate_ao1_logistic_regression_baseline.py) | Local AO1 baseline artifact validator. |
| [tests/data_validation/validate_ao1_xgboost_classifier.py](../tests/data_validation/validate_ao1_xgboost_classifier.py) | Local AO1 XGBoost artifact validator. |
| [tests/data_validation/validate_ao1_evaluation_pack.py](../tests/data_validation/validate_ao1_evaluation_pack.py) | Local AO1 evaluation-pack validator. |
| [tests/data_validation/validate_ao1_decision_threshold_policy.py](../tests/data_validation/validate_ao1_decision_threshold_policy.py) | Local AO1 threshold validator. |
| [tests/data_validation/validate_ao1_post_model_leakage_audit.py](../tests/data_validation/validate_ao1_post_model_leakage_audit.py) | Local AO1 leakage-audit validator. |
| [tests/data_validation/validate_ao1_results_h1.py](../tests/data_validation/validate_ao1_results_h1.py) | Local AO1 H1 result validator. |

## AO2 Target, Pipeline, and Results

| Artifact | Purpose |
| --- | --- |
| [docs/ao2_target_policy.md](../docs/ao2_target_policy.md) | AO2 target policy. |
| [docs/ao2_chronological_partitions.md](../docs/ao2_chronological_partitions.md) | AO2 partitioning. |
| [docs/ao2_preprocessing_pipeline.md](../docs/ao2_preprocessing_pipeline.md) | AO2 preprocessing contract. |
| [docs/ao2_ridge_baseline.md](../docs/ao2_ridge_baseline.md) | AO2 Ridge baseline. |
| [docs/ao2_gradient_boosting_regressor.md](../docs/ao2_gradient_boosting_regressor.md) | AO2 Gradient Boosting model. |
| [docs/ao2_model_evaluation.md](../docs/ao2_model_evaluation.md) | AO2 validation evaluation pack. |
| [docs/ao2_shap_explainability.md](../docs/ao2_shap_explainability.md) | AO2 explainability. |
| [docs/ao2_target_reconstruction_review.md](../docs/ao2_target_reconstruction_review.md) | AO2 target-reconstruction audit. |
| [docs/ao2_results_h2.md](../docs/ao2_results_h2.md) | Report-ready AO2 H2 result summary. |

## AO2 Key Tables and Figures

| Artifact | Purpose |
| --- | --- |
| [report/tables/ao2_model_validation_comparison.csv](tables/ao2_model_validation_comparison.csv) | Ridge versus Gradient Boosting validation comparison. |
| [report/tables/ao2_model_evaluation_metrics.csv](tables/ao2_model_evaluation_metrics.csv) | AO2 validation metrics. |
| [report/tables/ao2_residual_diagnostics_by_model.csv](tables/ao2_residual_diagnostics_by_model.csv) | AO2 residual diagnostics. |
| [report/tables/ao2_results_h2_summary.csv](tables/ao2_results_h2_summary.csv) | H2 summary table. |
| [report/tables/ao2_target_reconstruction_audit_findings.md](tables/ao2_target_reconstruction_audit_findings.md) | AO2 target-reconstruction findings. |
| [report/figures/modeling/ao2_shap_top_features.png](figures/modeling/ao2_shap_top_features.png) | AO2 SHAP top-features figure. |
| [report/figures/eda/ao2_profit_distribution.svg](figures/eda/ao2_profit_distribution.svg) | AO2 profit distribution figure. |

## AO2 Validators

| Artifact | Purpose |
| --- | --- |
| [tests/data_validation/validate_ao2_chronological_partitions.py](../tests/data_validation/validate_ao2_chronological_partitions.py) | Databricks AO2 partition validator. |
| [tests/data_validation/validate_ao2_preprocessing_pipeline.py](../tests/data_validation/validate_ao2_preprocessing_pipeline.py) | Hybrid AO2 preprocessing validator. |
| [tests/data_validation/validate_ao2_ridge_baseline.py](../tests/data_validation/validate_ao2_ridge_baseline.py) | Local AO2 Ridge artifact validator. |
| [tests/data_validation/validate_ao2_gradient_boosting_regressor.py](../tests/data_validation/validate_ao2_gradient_boosting_regressor.py) | Local AO2 Gradient Boosting artifact validator. |
| [tests/data_validation/validate_ao2_evaluation_pack.py](../tests/data_validation/validate_ao2_evaluation_pack.py) | Local AO2 evaluation-pack validator. |
| [tests/data_validation/validate_ao2_shap_explainability.py](../tests/data_validation/validate_ao2_shap_explainability.py) | Local AO2 SHAP validator. |
| [tests/data_validation/validate_ao2_target_reconstruction_audit.py](../tests/data_validation/validate_ao2_target_reconstruction_audit.py) | Local AO2 target-reconstruction audit validator. |
| [tests/data_validation/validate_ao2_results_h2.py](../tests/data_validation/validate_ao2_results_h2.py) | Local AO2 H2 result validator. |

## AO3 Methodology, Results, and Dashboard Inputs

| Artifact | Purpose |
| --- | --- |
| [docs/ao1_ao2_test_scoring.md](../docs/ao1_ao2_test_scoring.md) | Integrated AO1/AO2 held-out score generation for AO3. |
| [docs/ao3_risk_margin_matrix.md](../docs/ao3_risk_margin_matrix.md) | AO3 risk-margin matrix policy. |
| [docs/ao3_segment_assignment.md](../docs/ao3_segment_assignment.md) | AO3 segment assignment logic. |
| [docs/ao3_risk_margin_benchmark.md](../docs/ao3_risk_margin_benchmark.md) | AO3 benchmark against risk-only and margin-only views. |
| [docs/ao3_operational_recommendations.md](../docs/ao3_operational_recommendations.md) | AO3 action matrix. |
| [docs/ao3_methodology_and_results.md](../docs/ao3_methodology_and_results.md) | Report-ready AO3 methodology and H3 result summary. |
| [docs/ao3_kmeans_extension.md](../docs/ao3_kmeans_extension.md) | Optional clustering extension, not the primary AO3 method. |

## AO3 Key Tables

| Artifact | Purpose |
| --- | --- |
| [data/references/ao3_risk_margin_matrix_policy.csv](../data/references/ao3_risk_margin_matrix_policy.csv) | Governed AO3 threshold and segment policy. |
| [data/references/ao3_segment_summary.csv](../data/references/ao3_segment_summary.csv) | AO3 segment summary. |
| [data/references/ao3_risk_margin_benchmark_segment_summary.csv](../data/references/ao3_risk_margin_benchmark_segment_summary.csv) | AO3 benchmark segment summary. |
| [data/references/ao3_risk_margin_benchmark_crosswalk.csv](../data/references/ao3_risk_margin_benchmark_crosswalk.csv) | AO3 versus single-signal crosswalk. |
| [data/references/ao3_risk_margin_benchmark_insights.csv](../data/references/ao3_risk_margin_benchmark_insights.csv) | H3 benchmark insight table. |
| [data/references/ao3_operational_recommendation_matrix.csv](../data/references/ao3_operational_recommendation_matrix.csv) | AO3 managerial action matrix. |

## AO3 Validators

| Artifact | Purpose |
| --- | --- |
| [tests/data_validation/validate_ao1_ao2_test_scores.py](../tests/data_validation/validate_ao1_ao2_test_scores.py) | Databricks integrated score validator. |
| [tests/data_validation/validate_ao3_risk_margin_matrix_policy.py](../tests/data_validation/validate_ao3_risk_margin_matrix_policy.py) | Local AO3 matrix-policy validator. |
| [tests/data_validation/validate_ao3_risk_margin_segments.py](../tests/data_validation/validate_ao3_risk_margin_segments.py) | Databricks AO3 segment-table validator. |
| [tests/data_validation/validate_ao3_risk_margin_benchmark.py](../tests/data_validation/validate_ao3_risk_margin_benchmark.py) | Databricks AO3 benchmark validator. |
| [tests/data_validation/validate_ao3_operational_recommendations.py](../tests/data_validation/validate_ao3_operational_recommendations.py) | Local AO3 recommendation validator. |
| [tests/data_validation/validate_ao3_kmeans_extension.py](../tests/data_validation/validate_ao3_kmeans_extension.py) | Local optional K-means extension validator. |

## Dashboard Docs and Evidence

| Artifact | Purpose |
| --- | --- |
| [dashboard/README.md](../dashboard/README.md) | Final Power BI dashboard package overview and delivery notes. |
| [dashboard/Dashboard.pbip](../dashboard/Dashboard.pbip) | Power BI Project entry file for the checked-in dashboard source package. |
| [dashboard/powerbi_semantic_model.md](../dashboard/powerbi_semantic_model.md) | Governed Power BI semantic-model documentation. |
| [dashboard/powerbi_measures.dax](../dashboard/powerbi_measures.dax) | Power BI DAX measures used by the dashboard pages. |
| [docs/powerbi_databricks_serving_layer.md](../docs/powerbi_databricks_serving_layer.md) | Azure Databricks SQL serving-layer documentation. |
| [report/final_report_assets/figures/DataCo_Dashboard.pdf](final_report_assets/figures/DataCo_Dashboard.pdf) | Final dashboard PDF evidence used by the report package. |
| [report/final_report_assets/figures/figure_2_powerbi_executive_command_center.png](final_report_assets/figures/figure_2_powerbi_executive_command_center.png) | Main report Power BI screenshot evidence. |
| [report/final_report_assets/figures/powerbi_dashboard_page_inventory.md](final_report_assets/figures/powerbi_dashboard_page_inventory.md) | Final dashboard page inventory and report-use guidance. |
| [src/dashboard/register_powerbi_databricks_tables.py](../src/dashboard/register_powerbi_databricks_tables.py) | Databricks serving-layer registration script. |
| [src/dashboard/export_powerbi_gold_tables.py](../src/dashboard/export_powerbi_gold_tables.py) | Offline CSV fallback export script. |
| [tests/data_validation/validate_powerbi_gold_exports.py](../tests/data_validation/validate_powerbi_gold_exports.py) | Validator for generated Power BI exports when they exist. |

Dashboard status: Power BI is the official visualization and decision-support layer. The dashboard uses governed Azure Databricks serving-layer tables and checked-in Power BI Project source files. The `.pbix` file is submitted separately through the academic submission system and is not Git-tracked.
