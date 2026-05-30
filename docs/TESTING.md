# Testing Strategy

## Purpose

This document summarizes the current validation strategy for the DataCo capstone. The test suite protects project validity rather than full model performance. It focuses on data contracts, leakage controls, chronological split integrity, AO1/AO2 model artifact boundaries, AO2 target-reconstruction risk, AO3 segmentation policy, and dashboard/export artifact checks.

The project uses both local Python validators and Databricks/PySpark/Delta-dependent validators. Do not overstate local pass status for validators that require Databricks Delta tables.

## Validation Scope

The validation suite covers:

- Silver and Gold data quality contracts;
- feature availability and leakage screening;
- chronological split policy and partition outputs;
- AO1 target, preprocessing, model, evaluation, threshold, SHAP, leakage, and H1 artifacts;
- AO2 target policy, preprocessing, model, evaluation, SHAP, target-reconstruction audit, and H2 artifacts;
- AO3 risk-margin policy, held-out score contract, segment assignment, benchmark, recommendations, and optional K-means extension;
- dashboard/export support files when generated.

The suite does not validate final dashboard design quality, Power BI visual formatting, `.pbix` files, or exact future model performance values.

## Local Python Validators

These validators run against checked-in CSV, JSON, Markdown, and report artifacts. They do not require Spark or Delta tables.

### Governance and Reference Checks

```text
python tests/data_validation/validate_silver_schema_dictionary.py
python tests/data_validation/validate_leakage_conceptual_screening.py
python tests/data_validation/validate_chronological_split_policy.py
```

### AO1 Checks

```text
python tests/data_validation/validate_ao1_logistic_regression_baseline.py
python tests/data_validation/validate_ao1_xgboost_classifier.py
python tests/data_validation/validate_ao1_evaluation_pack.py
python tests/data_validation/validate_ao1_decision_threshold_policy.py
python tests/data_validation/validate_ao1_post_model_leakage_audit.py
python tests/data_validation/validate_ao1_shap_explainability.py
python tests/data_validation/validate_ao1_results_h1.py
```

### AO2 Checks

```text
python tests/data_validation/validate_ao2_ridge_baseline.py
python tests/data_validation/validate_ao2_gradient_boosting_regressor.py
python tests/data_validation/validate_ao2_evaluation_pack.py
python tests/data_validation/validate_ao2_shap_explainability.py
python tests/data_validation/validate_ao2_target_reconstruction_audit.py
python tests/data_validation/validate_ao2_results_h2.py
```

### AO3 Checks

```text
python tests/data_validation/validate_ao3_risk_margin_matrix_policy.py
python tests/data_validation/validate_ao3_operational_recommendations.py
python tests/data_validation/validate_ao3_kmeans_extension.py
```

### Dashboard Export Check

```text
python tests/data_validation/validate_powerbi_gold_exports.py
```

This validator is local, but it requires generated export files under `dashboard/exports/`. Those files are gitignored and are absent unless the Power BI export script has been run intentionally from Databricks.

## Databricks / PySpark / Delta Validators

These validators require Databricks Community Edition or an equivalent PySpark/Delta environment with the project Volume outputs available.

```text
python tests/data_validation/test_silver_quality.py
python tests/data_validation/test_gold_ao1_table.py
python tests/data_validation/test_gold_ao2_table.py
python tests/data_validation/validate_ao1_chronological_partitions.py
python tests/data_validation/validate_ao2_chronological_partitions.py
python tests/data_validation/validate_ao1_ao2_test_scores.py
python tests/data_validation/validate_ao3_risk_margin_segments.py
python tests/data_validation/validate_ao3_risk_margin_benchmark.py
```

These scripts read Delta tables from the configured project Volume. They should be run after the corresponding Databricks pipeline outputs exist. Environment setup is documented in [databricks_setup.md](databricks_setup.md), and the workflow inventory is documented in [project_orchestrator.md](project_orchestrator.md).

## Hybrid Validators

The preprocessing validators include static metadata checks and optional data-dependent checks. The static portions can run locally after artifacts are present, but full validation requires Delta partition tables.

```text
python tests/data_validation/validate_ao1_preprocessing_pipeline.py
python tests/data_validation/validate_ao2_preprocessing_pipeline.py
```

## AO1 Validation Status

AO1 has checked-in validators for:

- chronological partition integrity;
- preprocessing fit boundaries and leakage exclusions;
- Logistic Regression baseline artifacts;
- XGBoost classifier artifacts;
- validation evaluation pack;
- operating threshold policy;
- SHAP explainability;
- post-model leakage audit;
- H1 validation summary.

Current report status: H1 is supported on chronological validation evidence. XGBoost outperforms Logistic Regression on ROC-AUC and recall in the validation artifacts. Final test performance is not claimed from AO1 validation documents.

## AO2 Validation Status

AO2 has checked-in validators for:

- chronological partition integrity;
- preprocessing fit boundaries and target/proxy exclusions;
- Ridge baseline artifacts;
- Gradient Boosting Regressor artifacts;
- validation evaluation pack;
- SHAP explainability;
- target-reconstruction audit;
- H2 validation summary.

Current report status: H2 is supported on chronological validation evidence, with modest improvement. Gradient Boosting improves RMSE and MAE relative to Ridge, but explanatory power remains limited. The AO2 target-reconstruction audit is accepted with caution.

## AO3 Validation Status

AO3 has checked-in validators for:

- AO1/AO2 held-out score contract;
- risk-margin matrix policy;
- segment assignment;
- benchmark against risk-only and margin-only views;
- operational recommendation matrix;
- optional K-means extension.

Current report status: H3 is supported by AO3 segmentation and benchmark evidence with caveats. AO3 shows decision-layer separation of predicted-score groups, but it does not prove realized delivery or profit improvement from intervention.

## Dashboard / Export Validation Status

Dashboard status:

- Dashboard deliverable is still pending.
- Native Databricks AI/BI dashboard is being evaluated as an alternative to Power BI.
- Power BI semantic-model, DAX, and export-validation artifacts remain as one possible dashboard path.
- Generated Power BI exports are absent unless regenerated from Databricks.
- No `.pbix` file is claimed as present.

Dashboard/export validation:

- `src/dashboard/export_powerbi_gold_tables.py` is the optional Databricks export script for the Power BI path.
- `tests/data_validation/validate_powerbi_gold_exports.py` validates generated exports after they exist.
- Do not run export validation as evidence of dashboard readiness unless export files have been regenerated and are available locally.

## Final Validation Command Groups

Use these groups for final review.

### Local Governance

```text
python tests/data_validation/validate_silver_schema_dictionary.py
python tests/data_validation/validate_leakage_conceptual_screening.py
python tests/data_validation/validate_chronological_split_policy.py
```

### Local AO1

```text
python tests/data_validation/validate_ao1_logistic_regression_baseline.py
python tests/data_validation/validate_ao1_xgboost_classifier.py
python tests/data_validation/validate_ao1_evaluation_pack.py
python tests/data_validation/validate_ao1_decision_threshold_policy.py
python tests/data_validation/validate_ao1_post_model_leakage_audit.py
python tests/data_validation/validate_ao1_shap_explainability.py
python tests/data_validation/validate_ao1_results_h1.py
```

### Local AO2

```text
python tests/data_validation/validate_ao2_ridge_baseline.py
python tests/data_validation/validate_ao2_gradient_boosting_regressor.py
python tests/data_validation/validate_ao2_evaluation_pack.py
python tests/data_validation/validate_ao2_shap_explainability.py
python tests/data_validation/validate_ao2_target_reconstruction_audit.py
python tests/data_validation/validate_ao2_results_h2.py
```

### Local AO3

```text
python tests/data_validation/validate_ao3_risk_margin_matrix_policy.py
python tests/data_validation/validate_ao3_operational_recommendations.py
python tests/data_validation/validate_ao3_kmeans_extension.py
```

### Databricks / Delta

```text
python tests/data_validation/test_silver_quality.py
python tests/data_validation/test_gold_ao1_table.py
python tests/data_validation/test_gold_ao2_table.py
python tests/data_validation/validate_ao1_chronological_partitions.py
python tests/data_validation/validate_ao2_chronological_partitions.py
python tests/data_validation/validate_ao1_ao2_test_scores.py
python tests/data_validation/validate_ao3_risk_margin_segments.py
python tests/data_validation/validate_ao3_risk_margin_benchmark.py
```

### Dashboard Export, Only After Export Generation

```text
python tests/data_validation/validate_powerbi_gold_exports.py
```

## Known Deferred Items

- Final dashboard implementation.
- Final dashboard technology decision between native Databricks AI/BI and Power BI.
- Regenerated dashboard export files, if the Power BI path is chosen.
- `.pbix` creation, if the team later chooses Power BI.
- Realized intervention outcome evaluation for AO3.
- Production model monitoring, drift review, and fairness review beyond the academic prototype.
