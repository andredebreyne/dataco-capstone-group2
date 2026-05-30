# Final Validation Summary

This summary records the current validation posture for the DataCo capstone without rerunning data generation, model training, dashboard export, or dashboard build steps.

## Validator Categories

The project has two main validator categories:

- Local Python validators: run against committed CSV, JSON, Markdown, and report artifacts. These do not require Spark or Delta tables.
- Databricks/PySpark/Delta validators: require Databricks or an equivalent PySpark/Delta runtime because they read Delta tables under the project Volume.

Some preprocessing validators are hybrid. They can perform static metadata checks locally, but full data-dependent checks require the relevant Delta partitions.

## Local Validators

These validators can run locally from the repository root after Python dependencies are installed:

```text
python tests/data_validation/validate_silver_schema_dictionary.py
python tests/data_validation/validate_leakage_conceptual_screening.py
python tests/data_validation/validate_chronological_split_policy.py
python tests/data_validation/validate_ao1_logistic_regression_baseline.py
python tests/data_validation/validate_ao1_xgboost_classifier.py
python tests/data_validation/validate_ao1_evaluation_pack.py
python tests/data_validation/validate_ao1_decision_threshold_policy.py
python tests/data_validation/validate_ao1_post_model_leakage_audit.py
python tests/data_validation/validate_ao1_shap_explainability.py
python tests/data_validation/validate_ao1_results_h1.py
python tests/data_validation/validate_ao2_ridge_baseline.py
python tests/data_validation/validate_ao2_gradient_boosting_regressor.py
python tests/data_validation/validate_ao2_evaluation_pack.py
python tests/data_validation/validate_ao2_shap_explainability.py
python tests/data_validation/validate_ao2_target_reconstruction_audit.py
python tests/data_validation/validate_ao2_results_h2.py
python tests/data_validation/validate_ao3_risk_margin_matrix_policy.py
python tests/data_validation/validate_ao3_operational_recommendations.py
python tests/data_validation/validate_ao3_kmeans_extension.py
python tests/data_validation/validate_powerbi_gold_exports.py
```

Important dashboard/export caveat: `validate_powerbi_gold_exports.py` is a local validator, but it requires generated export files under `dashboard/exports/`. Those files are gitignored and are currently absent unless regenerated from Databricks.

## Databricks / PySpark / Delta Validators

These validators require Databricks Community Edition or another Spark/Delta environment with the project Volume outputs available:

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

Hybrid validators:

```text
python tests/data_validation/validate_ao1_preprocessing_pipeline.py
python tests/data_validation/validate_ao2_preprocessing_pipeline.py
```

The hybrid validators include static metadata checks, but full partition-shape and data checks require the Delta partition tables.

## AO1 Validation Status

AO1 has checked-in validation evidence for:

- target definition;
- chronological partitions;
- preprocessing metadata;
- Logistic Regression baseline;
- XGBoost classifier;
- validation evaluation pack;
- operating threshold policy;
- SHAP explainability;
- post-model leakage audit;
- H1 validation summary.

Status: H1 is supported on validation evidence. XGBoost outperforms Logistic Regression on the shared chronological validation slice, including ROC-AUC and recall. Final test performance is not claimed from the AO1 validation artifacts.

Key source: [docs/ao1_results_h1_validation.md](../docs/ao1_results_h1_validation.md).

## AO2 Validation Status

AO2 has checked-in validation evidence for:

- target policy;
- chronological partitions;
- preprocessing metadata;
- Ridge baseline;
- Gradient Boosting Regressor;
- validation evaluation pack;
- SHAP explainability;
- target-reconstruction audit;
- H2 validation summary.

Status: H2 is supported on validation evidence, with modest improvement. Gradient Boosting improves validation RMSE and MAE relative to Ridge, but R-squared remains low and predictions are compressed toward the mean. The AO2 target-reconstruction audit decision is `accepted_with_caution`.

Key source: [docs/ao2_results_h2.md](../docs/ao2_results_h2.md).

## AO3 Validation Status

AO3 has checked-in evidence for:

- AO1/AO2 held-out score contract;
- risk-margin matrix policy;
- segment assignment documentation and metadata;
- benchmark against risk-only and margin-only views;
- operational recommendation matrix;
- optional K-means extension.

Status: H3 is supported by AO3 segmentation and benchmark evidence with caveats. The benchmark shows that the combined risk-margin framework separates operational groups that are not fully evident from either risk-only or margin-only prioritization. This is decision-layer evidence, not a realized intervention outcome evaluation.

Key source: [docs/ao3_methodology_and_results.md](../docs/ao3_methodology_and_results.md).

## Dashboard / Export Validation Status

Dashboard status:

- Dashboard deliverable is still pending.
- A native Databricks AI/BI dashboard is being evaluated as an alternative to Power BI.
- Power BI semantic-model and DAX support artifacts remain checked in as one possible dashboard path.
- Generated Power BI export files are absent unless intentionally regenerated from Databricks.
- No `.pbix` file is claimed as present.

Export validation:

- `tests/data_validation/validate_powerbi_gold_exports.py` can validate generated Power BI exports after `src/dashboard/export_powerbi_gold_tables.py` is run.
- This task did not run the export script.
- This task did not create or require a `.pbix`.

## Final Validation Command Groups

Run local governance checks:

```text
python tests/data_validation/validate_silver_schema_dictionary.py
python tests/data_validation/validate_leakage_conceptual_screening.py
python tests/data_validation/validate_chronological_split_policy.py
```

Run local AO1 artifact checks:

```text
python tests/data_validation/validate_ao1_logistic_regression_baseline.py
python tests/data_validation/validate_ao1_xgboost_classifier.py
python tests/data_validation/validate_ao1_evaluation_pack.py
python tests/data_validation/validate_ao1_decision_threshold_policy.py
python tests/data_validation/validate_ao1_post_model_leakage_audit.py
python tests/data_validation/validate_ao1_shap_explainability.py
python tests/data_validation/validate_ao1_results_h1.py
```

Run local AO2 artifact checks:

```text
python tests/data_validation/validate_ao2_ridge_baseline.py
python tests/data_validation/validate_ao2_gradient_boosting_regressor.py
python tests/data_validation/validate_ao2_evaluation_pack.py
python tests/data_validation/validate_ao2_shap_explainability.py
python tests/data_validation/validate_ao2_target_reconstruction_audit.py
python tests/data_validation/validate_ao2_results_h2.py
```

Run local AO3 policy/recommendation checks:

```text
python tests/data_validation/validate_ao3_risk_margin_matrix_policy.py
python tests/data_validation/validate_ao3_operational_recommendations.py
python tests/data_validation/validate_ao3_kmeans_extension.py
```

Run Databricks/Delta checks after the relevant pipeline outputs exist:

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

Run dashboard export validation only after exports are regenerated:

```text
python tests/data_validation/validate_powerbi_gold_exports.py
```

## Known Deferred Items

- Final dashboard implementation.
- Final dashboard tool decision between native Databricks AI/BI and Power BI.
- Generated dashboard export files, unless regenerated from Databricks.
- `.pbix` creation, if the team later chooses the Power BI path.
- Realized intervention outcome evaluation for AO3.
- Any production monitoring, drift detection, or fairness audit beyond the academic prototype scope.
