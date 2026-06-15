# Power BI Databricks SQL Serving Layer

## Purpose

The Power BI Databricks SQL serving layer publishes governed dashboard artifacts as managed Databricks tables under the configured catalog/schema, defaulting to `workspace.default`. This is the finalized Power BI connection path because Power BI Desktop can refresh directly through the Azure Databricks connector instead of relying on local CSV imports.

This layer is a dashboard-serving layer, not a modeling layer.

It does not:

- recreate AO1 or AO2 scores
- recalculate AO3 margins or segments
- retune thresholds
- union unrelated artifacts
- expose final-test target or realized-outcome columns

## Entry point

```text
src/dashboard/register_powerbi_databricks_tables.py
```

Run from Databricks after AO1/AO2 scoring, AO3 segmentation, AO3 benchmark, and the reference/report artifacts exist.
The project orchestrator can also run this step when `RUN_POWERBI_DATABRICKS_SERVING_LAYER = True`; it is disabled by default.

Example. Replace `<workspace-user>` with the Databricks workspace folder for the repository checkout:

```python
import os
import runpy
from pathlib import Path

repo_root = Path("/Workspace/Repos/<workspace-user>/dataco-capstone-group2")
os.environ["DATACO_REPO_ROOT"] = str(repo_root)
os.environ["DATACO_POWERBI_SERVING_CATALOG"] = "workspace"
os.environ["DATACO_POWERBI_SERVING_SCHEMA"] = "default"

runpy.run_path(
    str(repo_root / "src/dashboard/register_powerbi_databricks_tables.py"),
    run_name="__main__",
)
```

## Configuration

Supported environment overrides:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATACO_REPO_ROOT` | Repository checkout path in Databricks Repos. | Current repo discovery. |
| `DATACO_POWERBI_SERVING_CATALOG` | Unity Catalog catalog for managed serving tables. | `workspace` |
| `DATACO_POWERBI_SERVING_SCHEMA` | Unity Catalog schema for managed serving tables. | `default` |
| `DATACO_VOLUME_ROOT` | Base Volume root used to resolve default Delta source paths. | `/Volumes/workspace/default/raw_data` |
| `DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH` | Source Delta path for integrated AO1/AO2 held-out scores. | `${DATACO_VOLUME_ROOT}/gold/ao1_ao2_test_scores` |
| `DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH` | Source Delta path for AO3 risk-margin segment assignments. | `${DATACO_VOLUME_ROOT}/gold/ao3_risk_margin_segments` |
| `DATACO_POWERBI_GEOGRAPHIC_SUMMARY_OUTPUT_PATH` | Source Delta path for the Power BI geographic global-map summary. | `${DATACO_VOLUME_ROOT}/gold/powerbi_geographic_summary` |
| `DATACO_POWERBI_LOGISTICS_KPI_SUMMARY_OUTPUT_PATH` | Source Delta path for the Power BI logistics KPI risk exposure summary. | `${DATACO_VOLUME_ROOT}/gold/powerbi_logistics_kpi_summary` |

## Published tables

The script publishes one managed Databricks SQL table per governed dashboard artifact. Delta-sourced fact tables are projected to dashboard-safe allowlisted schemas that match the CSV export contract, so target/outcome columns and unnecessary upstream fields are not published.

| Databricks table | Power BI semantic-model table |
| --- | --- |
| `workspace.default.powerbi_ao3_order_segments` | `AO3_Order_Segments` |
| `workspace.default.powerbi_ao1_ao2_test_scores` | `AO1_AO2_Test_Scores` |
| `workspace.default.powerbi_geographic_summary` | `Geographic_Summary` |
| `workspace.default.powerbi_logistics_kpi_summary` | `Logistics_KPI_Summary` |
| `workspace.default.powerbi_ao1_decision_threshold_policy` | `AO1_Decision_Threshold_Policy` |
| `workspace.default.powerbi_ao1_ao2_test_score_summary` | `AO1_AO2_Test_Score_Summary` |
| `workspace.default.powerbi_ao3_risk_margin_policy` | `AO3_Risk_Margin_Policy` |
| `workspace.default.powerbi_ao3_segment_summary` | `AO3_Segment_Summary` |
| `workspace.default.powerbi_ao3_benchmark_segment_summary` | `AO3_Benchmark_Segment_Summary` |
| `workspace.default.powerbi_ao3_benchmark_insights` | `AO3_Benchmark_Insights` |
| `workspace.default.powerbi_ao3_operational_recommendations` | `AO3_Operational_Recommendations` |
| `workspace.default.powerbi_ao1_model_validation` | `AO1_Model_Validation` |
| `workspace.default.powerbi_ao1_threshold_tradeoff` | `AO1_Threshold_Tradeoff` |
| `workspace.default.powerbi_ao1_confusion_by_threshold` | `AO1_Confusion_By_Threshold` |
| `workspace.default.powerbi_ao2_model_validation` | `AO2_Model_Validation` |
| `workspace.default.powerbi_ao2_evaluation_metrics` | `AO2_Evaluation_Metrics` |
| `workspace.default.powerbi_serving_layer_manifest` | QA manifest |

## Power BI connection steps

1. Run the registration script in Databricks.
2. Open Power BI Desktop.
3. Select **Get data > Azure Databricks**.
4. Use the Databricks SQL Warehouse `Server hostname` and `HTTP Path`.
5. Authenticate with the permitted workspace method, such as a Personal Access Token or organizational account.
6. In the Navigator, open the configured catalog/schema, defaulting to `workspace > default`.
7. Select the required `powerbi_*` tables.
8. Rename imported tables to the semantic-model names listed above.
9. Add DAX measures from `dashboard/powerbi_measures.dax`.
10. Build the executive, AO1, AO2, AO3, geographic, and command-center pages from the curated serving tables.

For the geographic global map page, run
`src/dashboard/build_powerbi_geographic_summary.py` before this registration
script so `powerbi_geographic_summary` is available.

For the logistics KPI risk exposure page, run
`src/dashboard/build_powerbi_logistics_kpi_summary.py` before this registration
script so `powerbi_logistics_kpi_summary` is available.

`.pbix` files are not tracked in Git because `.gitignore` excludes `dashboard/*.pbix`. Submit the `.pbix` outside Git or rebuild it locally from these connection and semantic-model instructions.

## Validation expectations

Before live Databricks execution, run the static contract validator from the repository root:

```text
python tests/data_validation/validate_powerbi_databricks_serving_layer.py
```

After running the script, confirm:

```sql
SHOW TABLES IN workspace.default LIKE 'powerbi_*';
```

Then confirm the row counts in:

```sql
SELECT *
FROM workspace.default.powerbi_serving_layer_manifest;
```

The manifest should list every published table with generated timestamp, workflow name, serving catalog/schema, fully qualified target table, source type, source path, artifact category, row count, column count, run status, and description. The script also logs row counts while publishing, and Power BI Navigator should discover the selected `powerbi_*` tables under the configured catalog/schema.

## Relationship to CSV export

The CSV export workflow remains valid for reproducibility and offline review. The Databricks SQL serving layer is the preferred Power BI Desktop connection and refresh workflow, using the same core logical table structure without requiring local CSV imports.

The logistics KPI summary is also available in the CSV fallback export as:

```text
dashboard/exports/powerbi_logistics_kpi_summary.csv
```

Recommended use:

- CSV export: backup, reproducibility, review, and local fallback
- Databricks serving layer: Power BI Desktop connection and dashboard refresh workflow
