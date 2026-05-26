# Project Workflow Orchestrator

## Purpose

`notebooks/pipeline/run_project_workflow.py` is the standard Databricks-compatible entry point for the current DataCo project workflow. It coordinates existing scripts in the approved order without copying transformation, feature engineering, leakage, EDA, or modeling logic into the orchestrator.

This orchestrator covers Bronze, Silver, feature engineering, AO1 and AO2 Gold table creation, lightweight validation, optional AO1 and AO2 chronological partition creation, optional AO1 and AO2 preprocessing, optional AO1 and AO2 validation-model training, optional AO1 and AO2 validation evaluation-pack generation, optional AO1 and AO2 SHAP explainability, optional AO2 target-reconstruction audit, optional AO2 H2 results validation, optional AO3 risk-margin matrix validation, optional AO1 decision-threshold selection, optional AO1/AO2 held-out test scoring, optional AO3 segment assignment, optional EDA artifact checks, and pre-Gold governance checks. Dashboard exports and final test-set performance evaluation are not part of this workflow.

## Executable Workflow Inventory

| Workflow step | Script or notebook path | Purpose | Input dependency | Output | Required or optional | Notes / Databricks assumptions |
| --- | --- | --- | --- | --- | --- | --- |
| Environment validation | `src/00_test_databricks_env.py` | Validate that Spark starts and a small PySpark job can run. | Databricks cluster attached to the repo. | Console smoke-test output. | Required for first setup; controlled by `RUN_ENV_CHECK`. | Uses the active Spark session or creates one. |
| Repository structure validation | `notebooks/pipeline/run_project_workflow.py` | Confirm the full repository checkout is available to Databricks before running project jobs. | Repository root resolved from Databricks Repos, current working directory, or `DATACO_REPO_ROOT`. | Clear pass/fail message listing missing paths. | Required; controlled by `RUN_REPO_STRUCTURE_CHECK`. | The orchestrator validates the project files that are already attached to the Databricks workspace. |
| Databricks Volume directory setup | `notebooks/pipeline/run_project_workflow.py` | Create and validate the standard Unity Catalog Volume folder layout. | `DATACO_VOLUME_ROOT` or default `/Volumes/workspace/default/raw_data`. | `bronze`, `silver`, `gold`, `references`, and `eda` folders under the Volume root. | Required; controlled by `RUN_VOLUME_SETUP`. | Uses Databricks `dbutils.fs.mkdirs`; disable only when folders are intentionally managed elsewhere. |
| Raw data availability check | `notebooks/pipeline/run_project_workflow.py` | Confirm the raw DataCo CSV path configured for Bronze exists. | `DATACO_RAW_INPUT_PATH` or default `/Volumes/workspace/default/raw_data/DataCoSupplyChainDataset.csv`. | Clear pass/fail message. | Required before Bronze; controlled by `RUN_RAW_DATA_CHECK`. | Uses local path checks and Databricks `dbutils.fs.ls` when available. |
| Feature availability map registration | `src/data_engineering/register_feature_availability_map.py` | Validate and register the decision-time feature availability reference. | `data/references/feature_availability_map.csv`. | Volume CSV and Delta reference table. | Required for governance runs; controlled by `RUN_REFERENCE_REGISTRATION`. | Default Volume root is `/Volumes/workspace/default/raw_data`. |
| Bronze ingestion | `src/data_engineering/ingest_bronze.py` | Ingest the raw DataCo CSV into Bronze Delta while preserving source-level data. | Raw DataCo CSV in the configured Volume path. | Bronze Delta and column mapping output. | Required; controlled by `RUN_BRONZE`. | Uses existing Bronze config and logic. |
| Silver cleaning | `src/data_engineering/clean_silver.py` | Apply deterministic Silver cleaning and type standardization. | Bronze Delta output. | Silver Delta and Silver quality report Delta. | Required; controlled by `RUN_SILVER`. | Does not perform modeling preprocessing or feature selection. |
| Silver validation / quality checks | `tests/data_validation/test_silver_quality.py` | Validate row count, required columns, key types, lineage, and quality metrics. | Silver Delta and Silver quality report Delta. | Console pass/fail result. | Required after Silver; controlled by `RUN_SILVER_VALIDATION`. | Runs in Databricks because it reads Delta paths. |
| Order-time feature engineering | `src/data_engineering/engineer_order_time_features.py` | Create order-time candidate features from Silver. | Silver Delta. | Order-time feature Delta table. | Required when feature engineering runs; controlled by `RUN_FEATURE_ENGINEERING` and `RUN_ORDER_TIME_FEATURES`. | Uses existing leakage-safe feature logic. |
| Shipping/product feature engineering | `src/data_engineering/engineer_shipping_product_features.py` | Create shipping and product candidate features from Silver. | Silver Delta. | Shipping/product feature Delta table. | Required when feature engineering runs; controlled by `RUN_FEATURE_ENGINEERING` and `RUN_SHIPPING_PRODUCT_FEATURES`. | Uses existing feature contract and output validation. |
| Customer/regional feature engineering | `src/data_engineering/engineer_customer_regional_features.py` | Create customer and regional candidate features from Silver. | Silver Delta. | Customer/regional feature Delta table. | Required when feature engineering runs; controlled by `RUN_FEATURE_ENGINEERING` and `RUN_CUSTOMER_REGIONAL_FEATURES`. | Uses existing feature contract and output validation. |
| AO1 Gold analytical table build | `src/data_engineering/build_gold_ao1_table.py` | Create the leakage-safe AO1 Gold analytical table for late-delivery modeling. | Silver Delta and the three feature-engineering Delta outputs. | AO1 Gold Delta table. | Required when Gold runs; controlled by `RUN_GOLD` and `RUN_AO1_GOLD`. | Excludes shipping-canceled, canceled, and suspected-fraud records from the primary AO1 population. |
| AO1 Gold quality validation | `tests/data_validation/test_gold_ao1_table.py` | Validate the AO1 Gold row count, target completeness, schema, keys, and leakage exclusions. | AO1 Gold Delta table. | Console pass/fail result. | Required when Gold runs; controlled by `RUN_GOLD` and `RUN_AO1_GOLD`. | Runs in Databricks because it reads Delta paths. |
| AO2 Gold analytical table build | `src/data_engineering/build_gold_ao2_table.py` | Create the leakage-safe AO2 Gold analytical table for profitability modeling. | Silver Delta and the three feature-engineering Delta outputs. | AO2 Gold Delta table. | Required when Gold runs; controlled by `RUN_GOLD` and `RUN_AO2_GOLD`. | Uses the conservative first-pass AO2 commercial predictor policy and keeps AO3 order value as a support field only. |
| AO2 Gold quality validation | `tests/data_validation/test_gold_ao2_table.py` | Validate the AO2 Gold row count, target completeness, schema, keys, AO3 support denominator, and leakage exclusions. | AO2 Gold Delta table. | Console pass/fail result. | Required when Gold runs; controlled by `RUN_GOLD` and `RUN_AO2_GOLD`. | Runs in Databricks because it reads Delta paths. |
| AO1 chronological partition creation | `src/modeling/create_ao1_chronological_partitions.py` | Materialize deterministic AO1 `development` and `test` partitions from AO1 Gold using the frozen chronological split policy. | AO1 Gold Delta table and `data/references/chronological_split_policy.csv`. | AO1 partition Delta table and `data/references/ao1_chronological_partition_summary.csv`. | Optional and disabled by default; controlled by `RUN_AO1_PARTITIONS`. | Does not train models, fit preprocessing, tune thresholds, resample, encode, scale, or create validation subpartitions. |
| AO1 chronological partition validation | `tests/data_validation/validate_ao1_chronological_partitions.py` | Validate row counts, key preservation, partition labels, row-number boundaries, chronological ordering, date ranges, and target distribution. | AO1 Gold Delta table and AO1 partition Delta table. | Console pass/fail result with target distribution summary. | Optional and disabled by default; controlled by `RUN_AO1_PARTITIONS` and `RUN_AO1_PARTITION_VALIDATION`. | Runs in Databricks because it reads Delta paths. |
| AO2 chronological partition creation | `src/modeling/create_ao2_chronological_partitions.py` | Materialize deterministic AO2 `development` and `test` partitions from AO2 Gold using the frozen chronological split policy. | AO2 Gold Delta table and `data/references/chronological_split_policy.csv`. | AO2 partition Delta table and `data/references/ao2_chronological_partition_summary.csv`. | Optional and disabled by default; controlled by `RUN_AO2_PARTITIONS`. | Does not train models, fit preprocessing, tune hyperparameters, or create validation subpartitions. |
| AO2 chronological partition validation | `tests/data_validation/validate_ao2_chronological_partitions.py` | Validate row counts, key preservation, partition labels, row-number boundaries, chronological ordering, date ranges, and AO2 target coverage. | AO2 Gold Delta table and AO2 partition Delta table. | Console pass/fail result with target coverage summary. | Optional and disabled by default; controlled by `RUN_AO2_PARTITIONS` and `RUN_AO2_PARTITION_VALIDATION`. | Runs in Databricks because it reads Delta paths. |
| AO1 preprocessing pipeline build | `src/modeling/build_ao1_preprocessing_pipeline.py` | Fit AO1 imputers, encoders, and scalers on the fitting partition only and write lightweight preprocessing metadata. | AO1 chronological partition Delta table. | `models/ao1_late_delivery/preprocessing/ao1_preprocessing_metadata.json`; optional fitted artifact in a Databricks Volume when explicitly enabled. | Optional and disabled by default; controlled by `RUN_AO1_PREPROCESSING`. | Does not train models, tune thresholds, or apply SMOTE. With current `development`/`test` partitions, fits on `development` only and transforms `test` only as a compatibility check. |
| AO1 preprocessing pipeline validation | `tests/data_validation/validate_ao1_preprocessing_pipeline.py` | Validate metadata, feature groups, excluded leakage fields, fit source, SMOTE policy, and transformed row counts when runtime shape metadata is available. | AO1 preprocessing metadata and AO1 chronological partition Delta table. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_PREPROCESSING` and `RUN_AO1_PREPROCESSING_VALIDATION`. | Runs in Databricks for Delta-dependent checks; static metadata checks can run before the Delta table is available. |
| AO2 preprocessing pipeline build | `src/modeling/build_ao2_preprocessing_pipeline.py` | Fit AO2 imputers, encoders, and scalers on the fitting partition only and write lightweight preprocessing metadata. | AO2 chronological partition Delta table. | `models/ao2_profitability/preprocessing/ao2_preprocessing_metadata.json`; optional fitted artifact in a Databricks Volume when explicitly enabled. | Optional and disabled by default; controlled by `RUN_AO2_PREPROCESSING`. | Does not train AO2 models, derive margins, or assign AO3 groups. With current `development`/`test` partitions, fits on `development` only and transforms `test` only as a compatibility check. |
| AO2 preprocessing pipeline validation | `tests/data_validation/validate_ao2_preprocessing_pipeline.py` | Validate metadata, feature groups, AO2 target/proxy exclusions, `ao3_order_value` exclusion, fit source, and transformed row counts when runtime shape metadata is available. | AO2 preprocessing metadata and AO2 chronological partition Delta table. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_PREPROCESSING` and `RUN_AO2_PREPROCESSING_VALIDATION`. | Runs in Databricks for Delta-dependent checks; static metadata checks can run before the Delta table is available. |
| AO2 Ridge baseline training | `src/modeling/train_ao2_ridge_baseline.py` | Train the AO2 Ridge Regression baseline on the approved training slice and evaluate validation only. | AO2 chronological partition Delta table and AO2 preprocessing factory. | Metrics JSON, metadata JSON, validation metrics CSV, residual diagnostics CSV, validation predictions CSV, and coefficient CSV. | Optional and disabled by default; controlled by `RUN_AO2_RIDGE_BASELINE`. | Uses an inner chronological validation split inside `development` when only `development`/`test` partitions exist. Does not use final test, train gradient boosting, derive AO3 margins, or assign AO3 segments. |
| AO2 Ridge baseline validation | `tests/data_validation/validate_ao2_ridge_baseline.py` | Validate Ridge baseline artifacts, fit boundaries, regression metrics, residual diagnostics, parameters, predictions, and coefficient output. | Completed AO2 Ridge baseline artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_RIDGE_BASELINE` and `RUN_AO2_RIDGE_BASELINE_VALIDATION`. | Runs after Ridge training. Confirms final test is marked as unused and target-reconstruction fields are not predictors. |
| AO2 Gradient Boosting regressor training | `src/modeling/train_ao2_gradient_boosting_regressor.py` | Train the AO2 primary Gradient Boosting regressor on the approved training slice, compare a small validation-only candidate set, and evaluate validation only. | AO2 chronological partition Delta table, AO2 preprocessing factory, and optional Ridge validation metrics for comparison. | Metrics JSON, metadata JSON, validation metrics CSV, residual diagnostics CSV, validation predictions CSV, model comparison CSV, and feature-importance CSV. | Optional and disabled by default; controlled by `RUN_AO2_GRADIENT_BOOSTING_REGRESSOR`. | Uses an inner chronological validation split inside `development` when only `development`/`test` partitions exist. Does not use final test, derive AO3 margins, assign AO3 segments, or run broad tuning. |
| AO2 Gradient Boosting regressor validation | `tests/data_validation/validate_ao2_gradient_boosting_regressor.py` | Validate Gradient Boosting artifacts, fit boundaries, regression metrics, selected candidate metadata, target-policy exclusions, predictions, residuals, and Ridge comparison state. | Completed AO2 Gradient Boosting artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_GRADIENT_BOOSTING_REGRESSOR` and `RUN_AO2_GRADIENT_BOOSTING_REGRESSOR_VALIDATION`. | Runs after Gradient Boosting training. Confirms final test is marked as unused and `ao3_order_value` and target-reconstruction fields are not predictors. |
| AO2 validation evaluation pack | `src/modeling/evaluate_ao2_models.py` | Compare available AO2 candidate validation predictions using RMSE, MAE, R-squared, residual diagnostics, and compact error slices. | Row-level validation prediction CSVs and model artifacts from AO2 Ridge and Gradient Boosting. | Evaluation metrics, residual diagnostics, error slices, findings note, and metadata. | Optional and disabled by default; controlled by `RUN_AO2_EVALUATION_PACK`. | Runs on validation only. Final test rows are rejected and H2 language is limited to validation-stage evidence. |
| AO2 validation evaluation pack validation | `tests/data_validation/validate_ao2_evaluation_pack.py` | Validate AO2 evaluation metadata, comparison metrics, residual diagnostics, error slices, and findings coverage. | Completed AO2 evaluation pack artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_EVALUATION_PACK` and `RUN_AO2_EVALUATION_PACK_VALIDATION`. | Runs after the AO2 evaluation pack. Confirms final test is marked as unused and target-policy caveats are documented. |
| AO2 SHAP explainability | `src/modeling/explain_ao2_gradient_boosting_shap.py` | Generate SHAP-based explanations for the selected AO2 Gradient Boosting validation model. | AO2 chronological partition Delta table, AO2 preprocessing factory, selected Gradient Boosting metadata, and AO2 evaluation metadata. | SHAP feature-importance CSV, driver summary CSV, top-feature plot, findings note, and metadata JSON. | Optional and disabled by default; controlled by `RUN_AO2_SHAP_EXPLAINABILITY`. | Uses the saved selected pipeline when available, otherwise deterministically reconstructs the selected candidate on the approved training slice. Explains validation rows only and rejects final-test use. |
| AO2 SHAP explainability validation | `tests/data_validation/validate_ao2_shap_explainability.py` | Validate AO2 SHAP metadata, artifact paths, target-policy guardrails, non-negative SHAP importances, rank validity, findings language, and final-test exclusion. | Completed AO2 SHAP explainability artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_SHAP_EXPLAINABILITY` and `RUN_AO2_SHAP_EXPLAINABILITY_VALIDATION`. | Runs after AO2 SHAP explainability. Confirms forbidden target/proxy fields and `ao3_order_value` do not appear as SHAP drivers. |
| AO2 target-reconstruction audit | `src/modeling/audit_ao2_target_reconstruction.py` | Review the selected AO2 predictor set, XGBoost feature importance, SHAP drivers, and validation evidence for target-reconstruction or proxy leakage risk. | Completed AO2 preprocessing, Gradient Boosting, evaluation, and SHAP artifacts. | Forbidden-feature check CSV, driver-review CSV, findings note, documentation note, and metadata JSON. | Optional and disabled by default; controlled by `RUN_AO2_TARGET_RECONSTRUCTION_AUDIT`. | Artifact-only audit. Does not retrain, retune, change preprocessing, use final test, change target policy, or implement AO3. |
| AO2 target-reconstruction audit validation | `tests/data_validation/validate_ao2_target_reconstruction_audit.py` | Validate audit metadata, issue id, final-test exclusion, forbidden count logic, `ao3_order_value` exclusion, output tables, and findings coverage. | Completed AO2 target-reconstruction audit artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_TARGET_RECONSTRUCTION_AUDIT` and `RUN_AO2_TARGET_RECONSTRUCTION_AUDIT_VALIDATION`. | Runs after the audit and blocks accepted decisions if any forbidden feature is detected. |
| AO2 H2 result artifact check | `notebooks/pipeline/run_project_workflow.py` | Confirm the manually generated AO2 results/H2 documentation package exists. | Completed AO2 evaluation, SHAP, and target-reconstruction audit artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_RESULTS_H2`. | Documentation/result check only. Does not train, rerun SHAP, use final test, or implement AO3. |
| AO2 H2 results validation | `tests/data_validation/validate_ao2_results_h2.py` | Validate the AO2 H2 metadata, summary CSV, findings note, documentation page, final-test exclusion, model comparison metrics, and target-reconstruction audit dependency. | Completed AO2 results/H2 documentation package and issue `#73` audit metadata. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO2_RESULTS_H2_VALIDATION`. | Confirms H2 is supported only on validation evidence and blocks supported wording if the target-reconstruction audit is missing or blocked. |
| AO3 risk-margin matrix validation | `tests/data_validation/validate_ao3_risk_margin_matrix_policy.py` | Validate the AO3 2x2 risk-margin matrix policy, AO1 threshold reuse, AO2 predicted-margin rule, quadrant labels, fallback rules, and final-test exclusion. | `docs/ao3_risk_margin_matrix.md`, `data/references/ao3_risk_margin_matrix_policy.csv`, and `data/references/ao1_decision_threshold_policy.csv`. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO3_RISK_MARGIN_MATRIX_VALIDATION`. | Design-only validation. Does not score AO3, retune thresholds, use realized outcomes, or use final test data. |
| AO1 Logistic Regression baseline training | `src/modeling/train_ao1_logistic_regression_baseline.py` | Train the AO1 Logistic Regression baseline on the approved training slice and evaluate validation only. | AO1 chronological partition Delta table and AO1 preprocessing factory. | Metrics JSON, metadata JSON, validation metrics CSV, and coefficient CSV. | Optional and disabled by default; controlled by `RUN_AO1_LOGISTIC_BASELINE`. | Uses an inner chronological validation split inside `development` when only `development`/`test` partitions exist. Does not use final test, train XGBoost, tune thresholds, or apply SMOTE. |
| AO1 Logistic Regression baseline validation | `tests/data_validation/validate_ao1_logistic_regression_baseline.py` | Validate Logistic Regression baseline artifacts, fit boundaries, metric ranges, parameters, and coefficient output. | Completed AO1 Logistic Regression baseline artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_LOGISTIC_BASELINE` and `RUN_AO1_LOGISTIC_BASELINE_VALIDATION`. | Runs after baseline training. Confirms final test is marked as unused and forbidden leakage fields are not predictors. |
| AO1 validation evaluation pack | `src/modeling/evaluate_ao1_models.py` | Compare available AO1 candidate validation predictions using ranking metrics, threshold grids, confusion matrices, operating curves, and calibration bins. | Row-level validation prediction CSVs from AO1 candidate models. | Evaluation metrics, threshold grid, curve points, calibration table, findings note, and metadata. | Optional and disabled by default; controlled by `RUN_AO1_EVALUATION_PACK`. | Runs on validation only. The final test set is not used and the final operating threshold is selected in the separate threshold-governance task. |
| AO1 validation evaluation pack validation | `tests/data_validation/validate_ao1_evaluation_pack.py` | Validate AO1 evaluation metadata, metrics, threshold, confusion-matrix, curve, calibration, and findings artifacts. | Completed AO1 evaluation pack artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_EVALUATION_PACK` and `RUN_AO1_EVALUATION_PACK_VALIDATION`. | Runs after the evaluation pack. Confirms final test is marked as unused. |
| AO1 XGBoost classifier training | `src/modeling/train_ao1_xgboost_classifier.py` | Train the AO1 primary XGBoost classifier on the approved training slice, compare a small validation-only candidate set, and evaluate validation only. | AO1 chronological partition Delta table and AO1 preprocessing factory. | Metrics JSON, metadata JSON, validation metrics CSV, candidate-comparison CSV, feature-importance CSV, and validation-prediction CSV. | Optional and disabled by default; controlled by `RUN_AO1_XGBOOST_CLASSIFIER`. | Uses an inner chronological validation split inside `development` when only `development`/`test` partitions exist. Does not use final test, tune thresholds, apply SMOTE, score AO3, or run final AO1 evaluation. |
| AO1 XGBoost classifier validation | `tests/data_validation/validate_ao1_xgboost_classifier.py` | Validate XGBoost artifacts, fit boundaries, metric ranges, selected candidate metadata, and feature-importance output. | Completed AO1 XGBoost classifier artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_XGBOOST_CLASSIFIER` and `RUN_AO1_XGBOOST_CLASSIFIER_VALIDATION`. | Runs after XGBoost training. Confirms final test is marked as unused, exactly one candidate is selected, and forbidden leakage fields are not predictors. |
| AO1 SHAP explainability | `src/modeling/explain_ao1_xgboost_shap.py` | Generate SHAP-based explanations for the selected AO1 XGBoost validation model. | AO1 chronological partition Delta table, AO1 preprocessing factory, and required selected XGBoost metadata. | SHAP feature-importance CSV, driver summary CSV, top-feature plot, findings note, and metadata JSON. | Optional and disabled by default; controlled by `RUN_AO1_SHAP_EXPLAINABILITY`. | Deterministically reconstructs the selected XGBoost candidate on the approved training slice and explains validation rows only. Does not use final test or select thresholds. |
| AO1 SHAP explainability validation | `tests/data_validation/validate_ao1_shap_explainability.py` | Validate SHAP artifacts, metadata, figure generation, leakage-token guardrails, and final-test exclusion. | Completed AO1 SHAP explainability artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_SHAP_EXPLAINABILITY` and `RUN_AO1_SHAP_EXPLAINABILITY_VALIDATION`. | Runs after SHAP explainability. |
| AO1 decision-threshold selection | `src/modeling/select_ao1_decision_threshold.py` | Select the AO1 operating threshold from validation threshold trade-offs using the documented recall-first operational rule. | AO1 evaluation metrics and threshold grid from issue `#29`. | Policy CSV, threshold metadata JSON, and recommendation note. | Optional and disabled by default; controlled by `RUN_AO1_DECISION_THRESHOLD`. | Runs on validation evidence only. Produces a provisional policy until the primary AO1 model artifact is available. |
| AO1 decision-threshold validation | `tests/data_validation/validate_ao1_decision_threshold_policy.py` | Validate the AO1 threshold policy, metadata, final-test exclusion, and AO3/dashboard reuse rule. | Completed AO1 threshold policy artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_DECISION_THRESHOLD` and `RUN_AO1_DECISION_THRESHOLD_VALIDATION`. | Runs after threshold selection. |
| AO1 post-model leakage audit validation | `tests/data_validation/validate_ao1_post_model_leakage_audit.py` | Validate the AO1 post-model leakage audit memo and checklist. | `docs/ao1_post_model_leakage_audit.md` and `data/references/ao1_post_model_leakage_audit.csv`. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_POST_MODEL_LEAKAGE_AUDIT_VALIDATION`. | Confirms final-test boundary, train-only transformation review, forbidden predictor review, reviewed SHAP caveats, and sign-off language are documented. |
| AO1 H1 results validation | `tests/data_validation/validate_ao1_results_h1.py` | Validate the AO1 results write-up, H1 conclusion, threshold reference, and final-test caveat. | AO1 evaluation pack, threshold grid, and `docs/ao1_results_h1_validation.md`. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_RESULTS_H1_VALIDATION`. | Confirms XGBoost outperforms Logistic Regression on validation ROC-AUC and recall and that the document avoids final-test claims. |
| AO1/AO2 held-out test scoring | `src/modeling/score_ao1_ao2_test_set.py` | Fit the frozen selected AO1/AO2 configurations on development partitions and generate integrated held-out test predictions for AO3. | AO1/AO2 chronological partitions, AO1/AO2 selected model metadata, and AO1 threshold policy. | Delta score table, metadata JSON, and summary CSV. | Optional and disabled by default; controlled by `RUN_AO1_AO2_TEST_SCORING`. | Uses test rows for prediction only. Does not train on test, tune thresholds, calculate final-test metrics, or assign AO3 segments. |
| AO1/AO2 held-out test score validation | `tests/data_validation/validate_ao1_ao2_test_scores.py` | Validate the integrated score table contract, test-only partitions, probability range, AO1 threshold reuse, and final-test target exclusion. | Completed AO1/AO2 held-out test score table and metadata. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_AO2_TEST_SCORING` and `RUN_AO1_AO2_TEST_SCORING_VALIDATION`. | Runs in Databricks because it reads Delta paths. Does not calculate performance metrics. |
| AO3 risk-margin segment assignment | `src/modeling/build_ao3_risk_margin_segments.py` | Apply the governed AO3 risk-margin policy to the integrated AO1/AO2 held-out test score table. | Issue `#40` AO3 policy CSV and Issue `#41` AO1/AO2 test score Delta table. | AO3 segment Delta table, metadata JSON, and summary CSV. | Optional and disabled by default; controlled by `RUN_AO3_SEGMENT_ASSIGNMENT`. | Assigns operational segments only. Does not train models, tune thresholds, use final-test targets, calculate performance metrics, or benchmark H3. |
| AO3 risk-margin segment validation | `tests/data_validation/validate_ao3_risk_margin_segments.py` | Validate the AO3 segment table contract, valid segment labels, test-only partition boundary, target exclusion, metadata, and summary row counts. | Completed AO3 segment Delta table and artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO3_SEGMENT_ASSIGNMENT` and `RUN_AO3_SEGMENT_ASSIGNMENT_VALIDATION`. | Runs in Databricks because it reads Delta paths. Benchmarking against single-signal prioritization remains Issue `#43`. |
| Silver CSV export for EDA | `notebooks/pipeline/run_project_workflow.py` | Export the Silver Delta table to a gitignored local CSV clone for EDA scripts. | Silver Delta. | `data/silver/dataco_orders_silver.csv`. | Required for local EDA; controlled by `RUN_SILVER_CSV_EXPORT`. | Intended for local EDA and review only; Delta remains the source of truth. |
| Univariate EDA | `notebooks/eda/eda_univariate_distribution_analysis.py` | Generate univariate distribution, missingness, outlier, and cardinality review outputs. | Local Silver CSV clone. | Univariate EDA summary table and figures under `report/`. | Optional; controlled by `RUN_EDA` and `EDA_ACTION`. | Disabled by default to avoid broad artifact reruns; the renamed exploratory `.ipynb` is retained as context. |
| AO1 bivariate EDA | `notebooks/eda/ao1_bivariate_late_delivery_eda.py` | Generate AO1 late-delivery bivariate EDA summaries and figures. | Local Silver CSV clone. | AO1 EDA tables and figures under `report/`. | Optional; controlled by `RUN_EDA` and `EDA_ACTION`. | Disabled by default to avoid broad artifact reruns. |
| AO2 bivariate EDA | `notebooks/eda/ao2_bivariate_profitability_eda.py` | Generate AO2 profitability bivariate EDA summaries and figures. | Local Silver CSV clone. | AO2 EDA tables and figures under `report/`. | Optional; controlled by `RUN_EDA` and `EDA_ACTION`. | Disabled by default to avoid broad artifact reruns. |
| AO1 class imbalance analysis | `notebooks/eda/ao1_class_imbalance_analysis.py` | Generate AO1 target balance and slice-level imbalance artifacts. | Local Silver CSV clone. | Class imbalance tables and figures under `report/`. | Optional; controlled by `RUN_EDA` and `EDA_ACTION`. | Disabled by default to avoid broad artifact reruns. |
| EDA summary | `docs/eda_findings_summary.md` | Synthesize implemented EDA outputs for reviewers. | Existing EDA tables, figures, and documentation. | Documentation only. | Manual documentation step. | No executable generator exists yet; document as manual unless one is added later. |
| Silver schema dictionary validation | `tests/data_validation/validate_silver_schema_dictionary.py` | Validate the Silver dictionary reference against `clean_silver.py`. | `data/references/silver_schema_data_dictionary.csv` and `src/data_engineering/clean_silver.py`. | Console pass/fail result. | Required for pre-Gold governance; controlled by `RUN_PRE_GOLD_GOVERNANCE_CHECKS`. | Does not require Spark. |
| Leakage conceptual screening validation | `tests/data_validation/validate_leakage_conceptual_screening.py` | Validate leakage screening coverage and controlled values. | Reference CSVs and implemented feature scripts. | Console pass/fail result. | Required for pre-Gold governance; controlled by `RUN_PRE_GOLD_GOVERNANCE_CHECKS`. | Does not require Spark. |
| Pre-Gold modeling decisions | `docs/pre_gold_modeling_decisions.md`, `data/references/pre_gold_modeling_decisions.csv` | Document pre-Gold modeling and leakage decisions. | Completed Silver, feature engineering, EDA, and governance review. | Documentation and reference CSV. | Manual documentation step. | No executable validator exists yet; do not invent one in this issue. |
| Pre-Gold decision log | `docs/pre_gold_decision_log.md`, `data/references/pre_gold_decision_log.csv` | Track review decisions before Gold/modeling work. | Team review. | Documentation and reference CSV. | Manual documentation step. | No executable validator exists yet; do not invent one in this issue. |

## Current Executable Structure

- `notebooks/pipeline/` contains the single project workflow entry point: `run_project_workflow.py`.
- `src/data_engineering/` contains reusable Bronze, Silver, reference registration, feature engineering, and Gold table jobs.
- `src/modeling/` contains reusable model-preparation and modeling jobs, including AO1/AO2 chronological partition creation, AO1/AO2 preprocessing metadata generation, the AO1 Logistic Regression baseline, the AO2 Ridge baseline, the AO2 Gradient Boosting regressor, the AO1 XGBoost classifier, AO1 and AO2 validation evaluation packaging, AO1 and AO2 SHAP explainability, the AO2 target-reconstruction audit, AO1 decision-threshold selection, AO1/AO2 held-out test scoring, and AO3 segment assignment for integration.
- `tests/data_validation/` contains lightweight validation scripts for data quality and governance artifacts.
- `notebooks/eda/` contains EDA scripts and notebooks. Python EDA scripts are the orchestrator-supported executable format; `.ipynb` files are retained only as exploratory or historical context.
- `report/tables/` and `report/figures/` contain generated report-facing artifacts.
- `data/references/` contains small committed reference and governance CSVs.

The earlier medallion-only runner was removed after the project-level orchestrator replaced it. Existing references were updated to point to `notebooks/pipeline/run_project_workflow.py`.

## Databricks Assumptions

- Use Databricks Community Edition with runtime `14.3 LTS` where available, or `13.3 LTS` as the documented fallback.
- Run the orchestrator from the full repository checkout in Databricks or set `DATACO_REPO_ROOT` to the repository checkout path.
- The orchestrator assumes the project files are already available in Databricks. It does not manage external workspace setup or version-control operations.
- The default Volume root is `DATACO_VOLUME_ROOT=/Volumes/workspace/default/raw_data`.
- The default raw DataCo CSV path is `/Volumes/workspace/default/raw_data/DataCoSupplyChainDataset.csv`; override with `DATACO_RAW_INPUT_PATH` only when needed.
- Bronze, Silver, feature, and reference output paths use Unity Catalog Volume paths by default.
- The standard Volume setup creates or validates `bronze`, `silver`, `gold`, `references`, and `eda` folders under the configured Volume root.
- The local Silver CSV clone expected by EDA scripts is `data/silver/dataco_orders_silver.csv`.
- EDA scripts must use the Silver CSV clone or an explicitly configured Silver clone path, not raw data.

## Running The Orchestrator

Open `notebooks/pipeline/run_project_workflow.py` in Databricks and run it top to bottom. Adjust only the flags at the top of the file for partial reruns.

Common flag usage:

```python
RUN_ENV_CHECK = True
RUN_REPO_STRUCTURE_CHECK = True
RUN_VOLUME_SETUP = True
RUN_RAW_DATA_CHECK = True
RUN_BRONZE = True
RUN_SILVER = True
RUN_SILVER_VALIDATION = True
RUN_FEATURE_ENGINEERING = True
RUN_GOLD = True
RUN_AO1_PARTITIONS = False
RUN_AO1_PARTITION_VALIDATION = False
RUN_AO2_PARTITIONS = False
RUN_AO2_PARTITION_VALIDATION = False
RUN_AO1_PREPROCESSING = False
RUN_AO1_PREPROCESSING_VALIDATION = False
RUN_AO2_PREPROCESSING = False
RUN_AO2_PREPROCESSING_VALIDATION = False
RUN_AO2_RIDGE_BASELINE = False
RUN_AO2_RIDGE_BASELINE_VALIDATION = False
RUN_AO2_GRADIENT_BOOSTING_REGRESSOR = False
RUN_AO2_GRADIENT_BOOSTING_REGRESSOR_VALIDATION = False
RUN_AO2_EVALUATION_PACK = False
RUN_AO2_EVALUATION_PACK_VALIDATION = False
RUN_AO2_SHAP_EXPLAINABILITY = False
RUN_AO2_SHAP_EXPLAINABILITY_VALIDATION = False
RUN_AO2_TARGET_RECONSTRUCTION_AUDIT = False
RUN_AO2_TARGET_RECONSTRUCTION_AUDIT_VALIDATION = False
RUN_AO2_RESULTS_H2 = False
RUN_AO2_RESULTS_H2_VALIDATION = False
RUN_AO3_RISK_MARGIN_MATRIX_VALIDATION = False
RUN_AO1_LOGISTIC_BASELINE = False
RUN_AO1_LOGISTIC_BASELINE_VALIDATION = False
RUN_AO1_EVALUATION_PACK = False
RUN_AO1_EVALUATION_PACK_VALIDATION = False
RUN_AO1_XGBOOST_CLASSIFIER = False
RUN_AO1_XGBOOST_CLASSIFIER_VALIDATION = False
RUN_AO1_SHAP_EXPLAINABILITY = False
RUN_AO1_SHAP_EXPLAINABILITY_VALIDATION = False
RUN_AO1_DECISION_THRESHOLD = False
RUN_AO1_DECISION_THRESHOLD_VALIDATION = False
RUN_AO1_POST_MODEL_LEAKAGE_AUDIT_VALIDATION = False
RUN_AO1_RESULTS_H1_VALIDATION = False
RUN_AO1_AO2_TEST_SCORING = False
RUN_AO1_AO2_TEST_SCORING_VALIDATION = False
RUN_AO3_SEGMENT_ASSIGNMENT = False
RUN_AO3_SEGMENT_ASSIGNMENT_VALIDATION = False
RUN_SILVER_CSV_EXPORT = True
RUN_PRE_GOLD_GOVERNANCE_CHECKS = True
RUN_EDA = False
```

For EDA, leave `RUN_EDA = False` during normal pipeline runs. To validate that expected EDA artifacts exist without rerunning EDA, set:

```python
RUN_EDA = True
EDA_ACTION = "check"
```

To rerun the implemented Python EDA scripts intentionally, set:

```python
RUN_EDA = True
EDA_ACTION = "run_python_scripts"
```

The univariate EDA now has an orchestrator-supported Python script. The exploratory notebook is retained as `notebooks/eda/eda_univariate_distribution_analysis_exploratory.ipynb` and is not called by the orchestrator.

## Primary Output Paths

At the end of each run, the orchestrator prints the primary paths that reviewers should verify:

- Volume root.
- Raw DataCo CSV.
- Bronze Delta table.
- Bronze column mapping Delta table.
- Feature availability map Delta table.
- Silver Delta table.
- Silver quality report Delta table.
- Order-time feature Delta table.
- Shipping/product feature Delta table.
- Customer/regional feature Delta table.
- AO1 Gold analytical table Delta table.
- AO2 Gold analytical table Delta table.
- AO1 chronological partitions Delta table.
- AO2 chronological partitions Delta table.
- AO1 preprocessing metadata JSON.
- AO2 preprocessing metadata JSON.
- AO2 Ridge baseline metadata JSON.
- AO2 Ridge validation predictions CSV.
- AO2 Gradient Boosting metadata JSON.
- AO2 Gradient Boosting validation predictions CSV.
- AO2 evaluation metadata JSON.
- AO2 SHAP driver summary CSV.
- AO2 target-reconstruction audit metadata JSON.
- AO2 H2 results metadata JSON.
- AO2 H2 results summary CSV.
- AO3 risk-margin matrix policy CSV.
- AO1 Logistic Regression metadata JSON.
- AO1 evaluation metadata JSON.
- AO1 XGBoost metadata JSON.
- AO1 XGBoost validation predictions CSV.
- AO1 SHAP driver summary CSV.
- AO1 decision threshold policy CSV.
- AO1 post-model leakage audit reference CSV.
- AO1 H1 results summary CSV.
- AO1/AO2 held-out test score Delta table.
- AO1/AO2 held-out test score metadata JSON.
- AO3 risk-margin segment Delta table.
- AO3 segment assignment metadata JSON.
- Local Silver CSV clone for EDA.

## Failure Handling

Each orchestrator step prints:

- `[START] <step name>`
- `[DONE] <step name>` when successful
- `[FAIL] <step name>: <error>` when failed
- `[SKIP] <step name>` when disabled by flags

Required steps raise a clear `RuntimeError` that names the failed step. Optional EDA checks are reported but do not block the required Bronze/Silver/feature workflow.

## Future Contribution Rule

Any task that adds, renames, removes, or changes an executable pipeline step, validation script, feature engineering job, EDA artifact generator, model training step, scoring step, or dashboard export must update `notebooks/pipeline/run_project_workflow.py` and this document before the PR is considered complete.
