# Project Workflow Orchestrator

## Purpose

`notebooks/pipeline/run_project_workflow.py` is the standard Databricks-compatible entry point for the current DataCo project workflow. It coordinates existing scripts in the approved order without copying transformation, feature engineering, leakage, EDA, or modeling logic into the orchestrator.

This orchestrator covers Bronze, Silver, feature engineering, lightweight validation, optional EDA artifact checks, and pre-Gold governance checks. Gold tables, model training, scoring, dashboard exports, and final model evaluation are not part of this workflow.

## Executable Workflow Inventory

| Workflow step | Script or notebook path | Purpose | Input dependency | Output | Required or optional | Notes / Databricks assumptions |
| --- | --- | --- | --- | --- | --- | --- |
| Environment validation | `src/00_test_databricks_env.py` | Validate that Spark starts and a small PySpark job can run. | Databricks cluster attached to the repo. | Console smoke-test output. | Required for first setup; controlled by `RUN_ENV_CHECK`. | Uses the active Spark session or creates one. |
| Raw data availability check | `notebooks/pipeline/run_project_workflow.py` | Confirm the raw DataCo CSV path configured for Bronze exists. | `DATACO_RAW_INPUT_PATH` or default `/Volumes/workspace/default/raw_data/DataCoSupplyChainDataset.csv`. | Clear pass/fail message. | Required before Bronze; controlled by `RUN_RAW_DATA_CHECK`. | Uses local path checks and Databricks `dbutils.fs.ls` when available. |
| Feature availability map registration | `src/data_engineering/register_feature_availability_map.py` | Validate and register the decision-time feature availability reference. | `data/references/feature_availability_map.csv`. | Volume CSV and Delta reference table. | Required for governance runs; controlled by `RUN_REFERENCE_REGISTRATION`. | Default Volume root is `/Volumes/workspace/default/raw_data`. |
| Bronze ingestion | `src/data_engineering/ingest_bronze.py` | Ingest the raw DataCo CSV into Bronze Delta while preserving source-level data. | Raw DataCo CSV in the configured Volume path. | Bronze Delta and column mapping output. | Required; controlled by `RUN_BRONZE`. | Uses existing Bronze config and logic. |
| Silver cleaning | `src/data_engineering/clean_silver.py` | Apply deterministic Silver cleaning and type standardization. | Bronze Delta output. | Silver Delta and Silver quality report Delta. | Required; controlled by `RUN_SILVER`. | Does not perform modeling preprocessing or feature selection. |
| Silver validation / quality checks | `tests/data_validation/test_silver_quality.py` | Validate row count, required columns, key types, lineage, and quality metrics. | Silver Delta and Silver quality report Delta. | Console pass/fail result. | Required after Silver; controlled by `RUN_SILVER_VALIDATION`. | Runs in Databricks because it reads Delta paths. |
| Order-time feature engineering | `src/data_engineering/engineer_order_time_features.py` | Create order-time candidate features from Silver. | Silver Delta. | Order-time feature Delta table. | Required when feature engineering runs; controlled by `RUN_FEATURE_ENGINEERING` and `RUN_ORDER_TIME_FEATURES`. | Uses existing leakage-safe feature logic. |
| Shipping/product feature engineering | `src/data_engineering/engineer_shipping_product_features.py` | Create shipping and product candidate features from Silver. | Silver Delta. | Shipping/product feature Delta table. | Required when feature engineering runs; controlled by `RUN_FEATURE_ENGINEERING` and `RUN_SHIPPING_PRODUCT_FEATURES`. | Uses existing feature contract and output validation. |
| Customer/regional feature engineering | `src/data_engineering/engineer_customer_regional_features.py` | Create customer and regional candidate features from Silver. | Silver Delta. | Customer/regional feature Delta table. | Required when feature engineering runs; controlled by `RUN_FEATURE_ENGINEERING` and `RUN_CUSTOMER_REGIONAL_FEATURES`. | Uses existing feature contract and output validation. |
| Silver CSV export for EDA | `notebooks/pipeline/run_project_workflow.py` | Export the Silver Delta table to a gitignored local CSV clone for EDA scripts. | Silver Delta. | `data/silver/dataco_orders_silver.csv`. | Required for local EDA; controlled by `RUN_SILVER_CSV_EXPORT`. | Intended for local EDA and review only; Delta remains the source of truth. |
| AO1 bivariate EDA | `notebooks/eda/ao1_bivariate_late_delivery_eda.py` | Generate AO1 late-delivery bivariate EDA summaries and figures. | Local Silver CSV clone. | AO1 EDA tables and figures under `report/`. | Optional; controlled by `RUN_EDA` and `EDA_ACTION`. | Disabled by default to avoid broad artifact reruns. |
| AO2 bivariate EDA | `notebooks/eda/ao2_bivariate_profitability_eda.py` | Generate AO2 profitability bivariate EDA summaries and figures. | Local Silver CSV clone. | AO2 EDA tables and figures under `report/`. | Optional; controlled by `RUN_EDA` and `EDA_ACTION`. | Disabled by default to avoid broad artifact reruns. |
| AO1 class imbalance analysis | `notebooks/eda/ao1_class_imbalance_analysis.py` | Generate AO1 target balance and slice-level imbalance artifacts. | Local Silver CSV clone. | Class imbalance tables and figures under `report/`. | Optional; controlled by `RUN_EDA` and `EDA_ACTION`. | Disabled by default to avoid broad artifact reruns. |
| Univariate EDA | `notebooks/eda/eda_univariate_distribution_analysis.ipynb` | Generate univariate distribution review outputs. | Local project data inputs used by the notebook. | Univariate EDA tables and figures. | Optional manual step. | Not automated by the Python orchestrator because it is currently an `.ipynb` notebook. |
| EDA summary | `docs/eda_findings_summary.md` | Synthesize implemented EDA outputs for reviewers. | Existing EDA tables, figures, and documentation. | Documentation only. | Manual documentation step. | No executable generator exists yet; document as manual unless one is added later. |
| Silver schema dictionary validation | `tests/data_validation/validate_silver_schema_dictionary.py` | Validate the Silver dictionary reference against `clean_silver.py`. | `data/references/silver_schema_data_dictionary.csv` and `src/data_engineering/clean_silver.py`. | Console pass/fail result. | Required for pre-Gold governance; controlled by `RUN_PRE_GOLD_GOVERNANCE_CHECKS`. | Does not require Spark. |
| Leakage conceptual screening validation | `tests/data_validation/validate_leakage_conceptual_screening.py` | Validate leakage screening coverage and controlled values. | Reference CSVs and implemented feature scripts. | Console pass/fail result. | Required for pre-Gold governance; controlled by `RUN_PRE_GOLD_GOVERNANCE_CHECKS`. | Does not require Spark. |
| Pre-Gold modeling decisions | `docs/pre_gold_modeling_decisions.md`, `data/references/pre_gold_modeling_decisions.csv` | Document pre-Gold modeling and leakage decisions. | Completed Silver, feature engineering, EDA, and governance review. | Documentation and reference CSV. | Manual documentation step. | No executable validator exists yet; do not invent one in this issue. |
| Pre-Gold decision log | `docs/pre_gold_decision_log.md`, `data/references/pre_gold_decision_log.csv` | Track review decisions before Gold/modeling work. | Team review. | Documentation and reference CSV. | Manual documentation step. | No executable validator exists yet; do not invent one in this issue. |

## Current Executable Structure

- `notebooks/pipeline/` contains the single project workflow entry point: `run_project_workflow.py`.
- `src/data_engineering/` contains reusable Bronze, Silver, reference registration, and feature engineering jobs.
- `tests/data_validation/` contains lightweight validation scripts for data quality and governance artifacts.
- `notebooks/eda/` contains EDA scripts and notebooks.
- `report/tables/` and `report/figures/` contain generated report-facing artifacts.
- `data/references/` contains small committed reference and governance CSVs.

The earlier medallion-only runner was removed after the project-level orchestrator replaced it. Existing references were updated to point to `notebooks/pipeline/run_project_workflow.py`.

## Databricks Assumptions

- Use Databricks Community Edition with runtime `14.3 LTS` where available, or `13.3 LTS` as the documented fallback.
- Run the orchestrator from Databricks Repos or set `DATACO_REPO_ROOT` to the repository checkout path.
- The default Volume root is `DATACO_VOLUME_ROOT=/Volumes/workspace/default/raw_data`.
- The default raw DataCo CSV path is `/Volumes/workspace/default/raw_data/DataCoSupplyChainDataset.csv`; override with `DATACO_RAW_INPUT_PATH` only when needed.
- Bronze, Silver, feature, and reference output paths use Unity Catalog Volume paths by default.
- The local Silver CSV clone expected by EDA scripts is `data/silver/dataco_orders_silver.csv`.
- EDA scripts must use the Silver CSV clone or an explicitly configured Silver clone path, not raw data.

## Running The Orchestrator

Open `notebooks/pipeline/run_project_workflow.py` in Databricks and run it top to bottom. Adjust only the flags at the top of the file for partial reruns.

Common flag usage:

```python
RUN_ENV_CHECK = True
RUN_RAW_DATA_CHECK = True
RUN_BRONZE = True
RUN_SILVER = True
RUN_SILVER_VALIDATION = True
RUN_FEATURE_ENGINEERING = True
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

The univariate EDA `.ipynb` remains a manual notebook step unless it is converted to an executable Python workflow later.

## Failure Handling

Each orchestrator step prints:

- `[START] <step name>`
- `[DONE] <step name>` when successful
- `[FAIL] <step name>: <error>` when failed
- `[SKIP] <step name>` when disabled by flags

Required steps raise a clear `RuntimeError` that names the failed step. Optional EDA checks are reported but do not block the required Bronze/Silver/feature workflow.

## Future Contribution Rule

Any task that adds, renames, removes, or changes an executable pipeline step, validation script, feature engineering job, EDA artifact generator, model training step, scoring step, or dashboard export must update `notebooks/pipeline/run_project_workflow.py` and this document before the PR is considered complete.

