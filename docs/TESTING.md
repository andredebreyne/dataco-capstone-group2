# Testing Strategy

Task: `[W2][P0][#13] Quality Framework and Git Strategy Documentation`

Issue: `#80`

## Purpose

This document defines the testing approach for the DataCo Medallion architecture. The goal is to validate data quality at each layer before downstream feature engineering, modeling, evaluation, and dashboard outputs depend on the data.

Testing is part of the project Definition of Done. A transformation is not complete until its critical assumptions are validated, documented, and reviewed.

## Medallion Testing Strategy

### Bronze

Bronze tests confirm that source registration preserves the raw dataset contract.

Expected checks:

- source row count matches the verified DataCo source
- source column count matches the verified DataCo source
- raw business fields remain strings to prevent type loss
- lineage fields are present
- technical column-name cleaning is traceable through mapping metadata

### Silver

Silver tests confirm that deterministic cleaning produced an analysis-ready table without applying model-training transformations.

Expected checks:

- row count remains stable unless a documented exclusion rule exists
- required analytical fields are present
- critical modeling fields do not contain nulls
- date fields are parsed as timestamps
- numeric fields are cast to approved analytical types
- Bronze lineage is preserved
- Silver processing metadata is appended
- Silver quality-report metrics are written for auditability

Silver must not perform fitted preprocessing such as statistical imputation, scaling, one-hot encoding, label encoding, target encoding, or resampling. Those transformations belong in model pipelines and must be fit on training data only.

The detailed Silver transformation rules are documented in `docs/silver_cleaning_rules.md`.

### Gold

Gold tests confirm that curated outputs are ready for modeling, evaluation, or dashboard consumption.

Expected checks:

- target definitions match AO1 and AO2 policies
- leakage-forbidden predictor fields are excluded from model feature matrices
- training, validation, and test splits are reproducible
- model-ready tables contain expected feature and target columns
- dashboard-ready outputs contain required business metrics and labels
- scored outputs include run metadata and enough context for auditability

## Silver Quality Validation Script

The Silver validation script is located at:

```text
tests/data_validation/test_silver_quality.py
```

The script reads the Silver Delta dataset from:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_silver
```

It reads the Silver quality-report Delta dataset from:

```text
/Volumes/workspace/default/raw_data/silver/dataco_orders_silver_quality_report
```

It validates:

- exactly `180,519` rows
- required Silver contract columns exist
- Bronze lineage columns are preserved
- `_silver_processed_timestamp` exists
- zero nulls in critical fields: `Order_Id`, `order_date_DateOrders`, `Sales`, and `Late_delivery_risk`
- key identifier, timestamp, target, financial, and lineage columns have approved Spark data types
- the Silver quality report contains required audit metrics

## Why These Checks Matter

The row-count check protects against accidental record loss between Bronze and Silver. Unexpected row loss can bias model training, reduce comparability with source verification, and make later dashboard totals inconsistent.

The required non-null checks protect core modeling and analytical fields:

- `Order_Id` is required for traceability, joins, and duplicate investigation.
- `order_date_DateOrders` is required for time-aware feature engineering and leakage-safe train/test separation.
- `Sales` is required for profitability analysis and AO2 feature/target logic.
- `Late_delivery_risk` is required for AO1 late-delivery modeling and target validation.

The timestamp check ensures order-time feature engineering can derive calendar fields, lead-time controls, and time-based splits without relying on string parsing later in the pipeline.

## Running the Silver Tests in Databricks

Run the Bronze and Silver jobs first from Databricks Repos or the Databricks workspace location where the repository scripts are available:

```text
src/data_engineering/ingest_bronze.py
src/data_engineering/clean_silver.py
```

Then run the validation script in Databricks from the repository root context:

```python
%run /path/to/tests/data_validation/test_silver_quality
```

If the repository is not mounted in Databricks Repos, copy the full script into a temporary notebook cell after running Bronze and Silver. The script should finish with:

```text
All Silver quality tests passed.
```

If a test fails, do not merge the related pull request until the root cause is understood and documented.
