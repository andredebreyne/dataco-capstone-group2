# Bronze-Silver-Gold Structure

Issue: `#6`
Milestone: `W1-Initiation`
Workstream: `Setup`
Priority: `Medium`


## Purpose

This document defines the repository and Databricks conventions for the DataCo Capstone medallion structure. The goal is to support reproducible reruns from raw source files to dashboard-ready outputs while keeping large local data files out of Git.

## Layer Definitions

| Layer | Purpose | Mutation rule | Primary consumers |
| --- | --- | --- | --- |
| Bronze | Raw or lightly registered source data from DataCo. | Preserve source files and source-level schema. No manual edits. | Schema inspection, data validation, Silver transforms. |
| Silver | Cleaned, standardized analytical tables. | Code-driven transformations only. Apply documented exclusions and leakage controls. | EDA, feature engineering, modeling notebooks. |
| Gold | Curated model and dashboard-ready outputs. | Code-driven outputs from approved Silver inputs and model predictions. | AO1/AO2 evaluation, AO3 prioritization, Power BI dashboard. |
| References | Small lookup files, metadata, and manually maintained reference tables. | Version if small and non-sensitive. Document source and owner. | Feature definitions, mappings, dashboard labels. |

## Repository Folder Convention

The repository uses these local folders:

```text
data/
|-- raw/
|-- bronze/
|-- silver/
|-- gold/
`-- references/
```

### `data/raw/`

Local-only landing area for manually downloaded source files. This folder may exist on team members' machines but should not contain committed large CSV files.

Expected local files:

```text
data/raw/DataCoSupplyChainDataset.csv
data/raw/DescriptionDataCoSupplyChain.csv
data/raw/tokenized_access_logs.csv
```

`DataCoSupplyChainDataset.csv` and `tokenized_access_logs.csv` are ignored by Git because they are large source files. The official source and checksum rules are documented in `docs/data_source_verification.md`.

### `data/bronze/`

Versioned Bronze references and small source-support files. Large Bronze source CSVs should remain ignored unless the team explicitly changes the repository policy.

Current structured DataCo convention:

```text
data/bronze/dataco/
|-- README.md
`-- DescriptionDataCoSupplyChain.csv
```

Bronze data should preserve source column names and source-level meaning. Cleaning, renaming, exclusions, and modeling decisions belong in Silver or later layers.

### `data/silver/`

Destination for cleaned analytical tables used by notebooks and reusable code. Silver outputs must be reproducible from Bronze/raw inputs.

Recommended local file convention:

```text
data/silver/dataco_orders_silver.parquet
data/silver/feature_availability_matrix.csv
data/silver/leakage_audit_results.csv
```

Silver responsibilities:

- parse and standardize dates
- standardize column names if the team approves a naming convention
- apply agreed row-level exclusions
- enforce target and leakage policies
- create reusable analytical tables for AO1, AO2, and AO3

### `data/gold/`

Destination for curated model-ready, evaluation, and dashboard-ready outputs.

Recommended local file convention:

```text
data/gold/ao1_late_delivery_scored.parquet
data/gold/ao2_profitability_scored.parquet
data/gold/ao3_risk_margin_priority.parquet
data/gold/dashboard_orders_export.csv
```

Gold responsibilities:

- contain finalized feature sets or scored outputs
- include AO1 predicted late-delivery risk
- include AO2 predicted order profit
- include AO3 predicted profit margin and priority group
- support Power BI exports and final report tables

### `data/references/`

Destination for small lookup tables, manually curated mappings, and source metadata that are safe to commit.

Examples:

```text
data/references/region_mapping.csv
data/references/priority_group_actions.csv
data/references/feature_availability_categories.csv
```

Reference files must include enough documentation to explain their source, owner, and maintenance rule.

## Databricks Destination Convention

Databricks Community Edition is the shared validation environment. Because Community Edition has limited storage and collaboration features, the repository remains the source of truth for code and documentation.

Recommended DBFS folder convention:

```text
/FileStore/tables/dataco/bronze/
/FileStore/tables/dataco/silver/
/FileStore/tables/dataco/gold/
/FileStore/tables/dataco/references/
```

Recommended Spark table naming convention, if tables are created in a Databricks workspace:

```text
dataco_bronze_<table_name>
dataco_silver_<table_name>
dataco_gold_<table_name>
```

Example table names:

```text
dataco_bronze_orders_raw
dataco_silver_orders_clean
dataco_gold_ao1_late_delivery_scored
dataco_gold_ao2_profitability_scored
dataco_gold_ao3_risk_margin_priority
```

If a team member cannot create managed tables in Community Edition, file-based DBFS paths are acceptable. The notebook or script must document the actual path used.

## Reproducible Rerun Rule

The intended rerun path is:

```text
raw source files
-> Bronze registration / source validation
-> Silver cleaning and methodological controls
-> Gold model-ready and dashboard-ready outputs
-> Power BI dashboard exports
```

Rules:

- Do not manually edit Bronze, Silver, or Gold outputs.
- All Silver and Gold outputs must be created by versioned code or notebooks.
- Preprocessing must be fit on training data only for modeling tasks.
- AO1 and AO2 target policies must be applied before Gold modeling tables are frozen.
- Gold outputs must include enough metadata or documentation to identify input source, run date, and assumptions.

## Dependencies

Standard environment:

- Databricks Community Edition
- Databricks Runtime `14.3 LTS (Scala 2.12, Spark 3.5.0)`
- Fallback runtime `13.3 LTS (Scala 2.12, Spark 3.4.1)`
- Python / PySpark notebooks
- GitHub repository as source of truth
- Power BI for dashboard consumption

See `docs/databricks_setup.md` for environment setup and smoke-test instructions.

## Group Access Checklist

Each group member should confirm:

- GitHub repository access is available.
- The repository can be cloned or opened through Databricks Repos.
- Databricks Community Edition workspace access is available.
- The standard cluster runtime can be selected, or fallback runtime use is documented.
- The DataCo source files can be placed locally or uploaded to DBFS.
- The Bronze, Silver, Gold, and References DBFS folders or equivalent paths can be created.
- The smoke test in `src/00_test_databricks_env.py` runs successfully.

## Assumptions and Limitations

- Community Edition is the official validation environment for this project unless the team changes the standard.
- Large raw data files are local or DBFS artifacts, not Git artifacts.
- Local folder placeholders exist so code can reference the intended medallion structure.
- Databricks paths may differ by team member; deviations must be documented in the related pull request or notebook.
- Issue `#63` and issue `#64` define target-specific methodological rules that should be applied before AO1 and AO2 Gold modeling tables are finalized.

