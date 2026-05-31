# Power BI Databricks SQL Serving Layer

## Purpose

The Power BI Databricks SQL serving layer publishes governed dashboard artifacts as managed Databricks tables under `workspace.default`. This allows Power BI Desktop to connect directly through the Azure Databricks connector instead of relying only on local CSV imports.

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

Example:

```python
import os
import runpy
from pathlib import Path

repo_root = Path("/Workspace/Users/andredebreyne@gmail.com/dataco-capstone-group2")
os.environ["DATACO_REPO_ROOT"] = str(repo_root)

runpy.run_path(
    str(repo_root / "src/dashboard/register_powerbi_databricks_tables.py"),
    run_name="__main__",
)
```

## Published tables

The script publishes one managed Databricks SQL table per governed dashboard artifact:

| Databricks table | Power BI semantic-model table |
| --- | --- |
| `workspace.default.powerbi_ao3_order_segments` | `AO3_Order_Segments` |
| `workspace.default.powerbi_ao1_ao2_test_scores` | `AO1_AO2_Test_Scores` |
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
| `workspace.default.powerbi_serving_layer_manifest` | Optional QA manifest |

## Power BI connection steps

1. Run the registration script in Databricks.
2. Open Power BI Desktop.
3. Select **Get data > Azure Databricks**.
4. Use the Databricks SQL Warehouse `Server hostname` and `HTTP Path`.
5. Authenticate with the permitted workspace method, such as a Personal Access Token or organizational account.
6. In the Navigator, open `workspace > default`.
7. Select the required `powerbi_*` tables.
8. Rename imported tables to the semantic-model names listed above.
9. Add DAX measures from `dashboard/powerbi_measures.dax`.
10. Build pages #48, #49, and #50 from the curated serving tables.

## Validation expectations

After running the script, confirm:

```sql
SHOW TABLES IN workspace.default LIKE 'powerbi_*';
```

Then confirm the row counts in:

```sql
SELECT *
FROM workspace.default.powerbi_serving_layer_manifest;
```

The manifest should list every published table and its row count.

## Relationship to CSV export

The CSV export workflow from issue #47 remains valid for reproducibility and offline review. The Databricks SQL serving layer provides a direct Power BI connection option using the same logical table structure.

Recommended use:

- CSV export: backup, reproducibility, review, and local fallback
- Databricks serving layer: Power BI Desktop connection and dashboard refresh workflow
