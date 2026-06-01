# Power BI Semantic Model Blueprint

This document defines the governed semantic-model layer for the DataCo
Capstone Power BI dashboard. The preferred Power BI path is direct connection
to managed Databricks SQL serving-layer tables created by
`src/dashboard/register_powerbi_databricks_tables.py`. Reproducible CSV exports
under `dashboard/exports/` remain available for offline review or fallback.

## Connection Workflows

Preferred direct Databricks path:

```text
src/dashboard/register_powerbi_databricks_tables.py
```

Or enable the optional orchestrator flag:

```text
RUN_POWERBI_DATABRICKS_SERVING_LAYER = True
```

This registers managed `powerbi_*` tables under the configured catalog/schema,
defaulting to `workspace.default`. In Power BI Desktop, use **Get data > Azure
Databricks**, enter the SQL Warehouse server hostname and HTTP path, select the
`powerbi_*` tables, and rename them to the semantic-model names below.

Offline CSV fallback:

```text
src/dashboard/export_powerbi_gold_tables.py
```

Or enable the optional CSV export flags:

```text
RUN_POWERBI_GOLD_EXPORT = True
RUN_POWERBI_GOLD_EXPORT_VALIDATION = True
```

The export job writes gitignored files under:

```text
dashboard/exports/
```

Power BI can import those fallback files with **Get data > Text/CSV** or
**Folder**. The exported files are generated artifacts and should not be edited
manually.

## Import Tables

| Power BI table | Preferred Databricks serving table | Offline CSV fallback | Dashboard purpose |
| --- | --- | --- | --- |
| `AO3_Order_Segments` | `powerbi_ao3_order_segments` | `ao3_risk_margin_segments.csv` | Primary operational fact table for AO3 segment analysis. |
| `AO1_AO2_Test_Scores` | `powerbi_ao1_ao2_test_scores` | `ao1_ao2_test_scores.csv` | Integrated held-out prediction table used upstream of AO3. |
| `AO1_Decision_Threshold_Policy` | `powerbi_ao1_decision_threshold_policy` | `ao1_decision_threshold_policy.csv` | Display the approved AO1 operating threshold reused by AO3. |
| `AO1_AO2_Test_Score_Summary` | `powerbi_ao1_ao2_test_score_summary` | `ao1_ao2_test_score_summary.csv` | Summarize the integrated AO1/AO2 held-out score population. |
| `AO3_Risk_Margin_Policy` | `powerbi_ao3_risk_margin_policy` | `ao3_risk_margin_matrix_policy.csv` | Document AO3 risk-margin policy, cutoffs, and segment definitions. |
| `AO3_Segment_Summary` | `powerbi_ao3_segment_summary` | `ao3_segment_summary.csv` | Segment counts and average score summaries. |
| `AO3_Benchmark_Segment_Summary` | `powerbi_ao3_benchmark_segment_summary` | `ao3_risk_margin_benchmark_segment_summary.csv` | Segment-level AO3 benchmark evidence. |
| `AO3_Benchmark_Insights` | `powerbi_ao3_benchmark_insights` | `ao3_risk_margin_benchmark_insights.csv` | H3 interpretation and benchmark notes. |
| `AO3_Operational_Recommendations` | `powerbi_ao3_operational_recommendations` | Not currently exported by the CSV script. | Recommended action matrix by AO3 segment. |
| `AO1_Model_Validation` | `powerbi_ao1_model_validation` | `ao1_model_validation_comparison.csv` | Compare AO1 validation models and selected metrics. |
| `AO1_Threshold_Tradeoff` | `powerbi_ao1_threshold_tradeoff` | `ao1_threshold_tradeoff_grid.csv` | Analyze precision, recall, F1, and alert-rate trade-offs. |
| `AO1_Confusion_By_Threshold` | `powerbi_ao1_confusion_by_threshold` | `ao1_confusion_matrix_by_threshold.csv` | Support confusion-matrix visuals by model and threshold. |
| `AO2_Model_Validation` | `powerbi_ao2_model_validation` | `ao2_model_validation_comparison.csv` | Compare AO2 validation models and regression metrics. |
| `AO2_Evaluation_Metrics` | `powerbi_ao2_evaluation_metrics` | `ao2_model_evaluation_metrics.csv` | Report AO2 residual and prediction diagnostics. |

## Primary Fact Grain

`AO3_Order_Segments` is the primary fact table. Its grain is one scored
order-item row from the common held-out AO1/AO2 test population.

Key dashboard columns include:

| Column | Purpose |
| --- | --- |
| `Order_Id` | Order traceability key. |
| `Order_Item_Id` | Order-item grain. |
| `order_date_DateOrders` | Date axis for trend analysis. |
| `ao1_predicted_late_delivery_probability` | Frozen AO1 late-delivery risk score. |
| `ao1_high_risk_flag` | Decision flag derived from the approved AO1 threshold. |
| `ao2_predicted_order_profit` | Frozen AO2 expected-profit prediction. |
| `ao3_order_value` | Positive order-value denominator retained for AO3 margin only. |
| `ao3_predicted_margin` | Deterministic ratio: predicted profit divided by order value. |
| `ao3_high_margin_flag` | Margin flag derived from the AO3 policy cutoff. |
| `ao3_priority_segment` | Final AO3 operational segment. |

## Relationships

The first dashboard version can keep the metric and policy tables disconnected.
`AO3_Order_Segments` should be the primary table for operational visuals.

Recommended first-pass model:

| From table | From column | To table | To column | Cardinality |
| --- | --- | --- | --- | --- |
| `AO3_Order_Segments` | `ao3_priority_segment` | `AO3_Segment_Summary` | `ao3_priority_segment` | Many-to-one, optional |

Additional dimensions should be added only after the exported AO3 fact table
includes stable customer, region, product, or shipping columns.

## Modeling Rules

- Power BI must not recreate AO1/AO2 scores, AO3 margins, thresholds, or segment
  assignments.
- The dashboard connects to Databricks serving tables or imports generated CSV
  fallback files; Databricks Delta remains the source of truth for Gold outputs.
- Target and outcome labels must not enter Power BI operational serving or
  export tables.
- Validation metric tables must remain clearly labeled as validation evidence,
  not final-test performance.
- Generated files under `dashboard/exports/` and `dashboard/*.pbix` are ignored
  by Git. CSV exports should be regenerated from the export script, and `.pbix`
  files should be submitted outside Git or rebuilt locally from these
  instructions.

## Manual Power BI Steps

1. Run `src/dashboard/register_powerbi_databricks_tables.py` in Databricks.
2. In Power BI Desktop, select **Get data > Azure Databricks**.
3. Enter the Databricks SQL Warehouse server hostname and HTTP path.
4. Select the configured catalog/schema, defaulting to `workspace > default`.
5. Import the required `powerbi_*` serving tables.
6. Rename imported tables to the semantic-model names listed in this document.
7. Add the DAX measures from `dashboard/powerbi_measures.dax`.
8. Refresh the model and confirm row counts against `powerbi_serving_layer_manifest`.

For offline fallback, run `src/dashboard/export_powerbi_gold_tables.py`, import
files from `dashboard/exports/`, and confirm row counts against
`powerbi_export_manifest.json`.
