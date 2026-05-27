# Power BI Semantic Model Blueprint

This document defines the governed semantic-model layer for the DataCo
Capstone Power BI dashboard. The dashboard should import reproducible CSV
exports generated from approved Databricks Gold Delta outputs and committed
reference/report artifacts.

## Export Workflow

Run the export job in Databricks after AO1/AO2 scoring and AO3 segmentation
have completed:

```text
src/dashboard/export_powerbi_gold_tables.py
```

Or enable the optional orchestrator flags:

```text
RUN_POWERBI_GOLD_EXPORT = True
RUN_POWERBI_GOLD_EXPORT_VALIDATION = True
```

The export job writes gitignored files under:

```text
dashboard/exports/
```

Power BI should import from that folder. The exported files are generated
artifacts and should not be edited manually.

## Import Tables

| Power BI table | Export file | Source system | Dashboard purpose |
| --- | --- | --- | --- |
| `AO3_Order_Segments` | `ao3_risk_margin_segments.csv` | Databricks Gold Delta | Primary operational fact table for AO3 segment analysis. |
| `AO1_AO2_Test_Scores` | `ao1_ao2_test_scores.csv` | Databricks Gold Delta | Integrated held-out prediction table used upstream of AO3. |
| `AO1_Decision_Threshold_Policy` | `ao1_decision_threshold_policy.csv` | Governed reference CSV | Display the approved AO1 operating threshold reused by AO3. |
| `AO3_Risk_Margin_Policy` | `ao3_risk_margin_matrix_policy.csv` | Governed reference CSV | Document AO3 risk-margin policy, cutoffs, and segment definitions. |
| `AO3_Segment_Summary` | `ao3_segment_summary.csv` | Governed reference CSV | Segment counts and average score summaries. |
| `AO3_Benchmark_Segment_Summary` | `ao3_risk_margin_benchmark_segment_summary.csv` | Governed reference CSV | Segment-level AO3 benchmark evidence. |
| `AO3_Benchmark_Insights` | `ao3_risk_margin_benchmark_insights.csv` | Governed reference CSV | H3 interpretation and benchmark notes. |
| `AO1_Model_Validation` | `ao1_model_validation_comparison.csv` | Report artifact | Compare AO1 validation models and selected metrics. |
| `AO1_Threshold_Tradeoff` | `ao1_threshold_tradeoff_grid.csv` | Report artifact | Analyze precision, recall, F1, and alert-rate trade-offs. |
| `AO1_Confusion_By_Threshold` | `ao1_confusion_matrix_by_threshold.csv` | Report artifact | Support confusion-matrix visuals by model and threshold. |
| `AO2_Model_Validation` | `ao2_model_validation_comparison.csv` | Report artifact | Compare AO2 validation models and regression metrics. |
| `AO2_Evaluation_Metrics` | `ao2_model_evaluation_metrics.csv` | Report artifact | Report AO2 residual and prediction diagnostics. |

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
- The dashboard imports exported artifacts; Databricks Delta remains the source
  of truth for Gold outputs.
- Target and outcome labels must not enter Power BI operational exports.
- Validation metric tables must remain clearly labeled as validation evidence,
  not final-test performance.
- Generated files under `dashboard/exports/` are ignored by Git and should be
  regenerated from the export script.

## Manual Power BI Steps

1. Run the Power BI export job in Databricks.
2. In Power BI Desktop, select **Get data > Text/CSV** or **Folder**.
3. Import files from `dashboard/exports/`.
4. Rename imported tables to the names listed in this document.
5. Add the DAX measures from `dashboard/powerbi_measures.dax`.
6. Refresh the model and confirm row counts against `powerbi_export_manifest.json`.
