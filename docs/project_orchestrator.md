# Project Workflow Orchestrator

## Purpose

`notebooks/pipeline/run_project_workflow.py` is the standard Databricks-compatible entry point for the current DataCo project workflow. It coordinates existing scripts in the approved order without copying transformation, feature engineering, leakage, EDA, or modeling logic into the orchestrator.

This orchestrator covers Bronze, Silver, feature engineering, AO1 and AO2 Gold table creation, lightweight validation, optional AO1 chronological partition creation, optional AO1 preprocessing, optional EDA artifact checks, and pre-Gold governance checks. Model training, scoring, dashboard exports, and final model evaluation are not part of this workflow.

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
| AO1 preprocessing pipeline build | `src/modeling/build_ao1_preprocessing_pipeline.py` | Fit AO1 imputers, encoders, and scalers on the fitting partition only and write lightweight preprocessing metadata. | AO1 chronological partition Delta table. | `models/ao1_late_delivery/preprocessing/ao1_preprocessing_metadata.json`; optional fitted artifact in a Databricks Volume when explicitly enabled. | Optional and disabled by default; controlled by `RUN_AO1_PREPROCESSING`. | Does not train models, tune thresholds, or apply SMOTE. With current `development`/`test` partitions, fits on `development` only and transforms `test` only as a compatibility check. |
| AO1 preprocessing pipeline validation | `tests/data_validation/validate_ao1_preprocessing_pipeline.py` | Validate metadata, feature groups, excluded leakage fields, fit source, SMOTE policy, and transformed row counts when runtime shape metadata is available. | AO1 preprocessing metadata and AO1 chronological partition Delta table. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_PREPROCESSING` and `RUN_AO1_PREPROCESSING_VALIDATION`. | Runs in Databricks for Delta-dependent checks; static metadata checks can run before the Delta table is available. |
| AO1 Logistic Regression baseline training | `src/modeling/train_ao1_logistic_regression_baseline.py` | Train the AO1 Logistic Regression baseline on the approved training slice and evaluate validation only. | AO1 chronological partition Delta table and AO1 preprocessing factory. | Metrics JSON, metadata JSON, validation metrics CSV, and coefficient CSV. | Optional and disabled by default; controlled by `RUN_AO1_LOGISTIC_BASELINE`. | Uses an inner chronological validation split inside `development` when only `development`/`test` partitions exist. Does not use final test, train XGBoost, tune thresholds, or apply SMOTE. |
| AO1 Logistic Regression baseline validation | `tests/data_validation/validate_ao1_logistic_regression_baseline.py` | Validate Logistic Regression baseline artifacts, fit boundaries, metric ranges, parameters, and coefficient output. | Completed AO1 Logistic Regression baseline artifacts. | Console pass/fail result. | Optional and disabled by default; controlled by `RUN_AO1_LOGISTIC_BASELINE` and `RUN_AO1_LOGISTIC_BASELINE_VALIDATION`. | Runs after baseline training. Confirms final test is marked as unused and forbidden leakage fields are not predictors. |
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
- `src/modeling/` contains reusable model-preparation and modeling jobs, including AO1 chronological partition creation, AO1 preprocessing metadata generation, and the AO1 Logistic Regression baseline.
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
RUN_AO1_PREPROCESSING = False
RUN_AO1_PREPROCESSING_VALIDATION = False
RUN_AO1_LOGISTIC_BASELINE = False
RUN_AO1_LOGISTIC_BASELINE_VALIDATION = False
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
- AO1 preprocessing metadata JSON.
- AO1 Logistic Regression metadata JSON.
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
