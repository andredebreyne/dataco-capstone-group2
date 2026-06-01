# Dashboard Status and Support Artifacts

This folder contains the governed Power BI dashboard project and its support
artifacts. Power BI is the selected executive-dashboard implementation path.
Dashboard pages are developed incrementally from approved Databricks Gold
outputs and governed reference artifacts.

## Files

| Path | Purpose |
| --- | --- |
| `Dashboard.pbip` | Power BI Project with semantic model and report definitions. |
| `powerbi_semantic_model.md` | Semantic-model blueprint and import instructions for the Power BI path. |
| `powerbi_measures.dax` | Draft DAX measures for AO1, AO2, and AO3 dashboard pages. |
| `exports/` | Gitignored local export folder generated from Databricks Gold outputs when the offline CSV fallback path is run. |
| `pages/q01_ao1_delivery_risk.md` | Implemented AO1 delivery-risk executive page specification for Issue `#48`. |
| `themes/dataco_executive_operations_dark.json` | Shared executive dashboard theme. |
| `wireframes/` | Versioned SVG backgrounds and layout standards. |

## Power BI Paths

The preferred Power BI path for issue #139 is direct connection from Power BI Desktop to Databricks SQL serving-layer tables. Run this Databricks registration script after AO1/AO2 scoring, AO3 segmentation, AO3 benchmark, and the supporting reference/report artifacts are available:

```text
src/dashboard/register_powerbi_databricks_tables.py
```

The script creates or replaces managed `powerbi_*` tables in the configured catalog/schema, defaulting to `workspace.default`, plus `powerbi_serving_layer_manifest` for row-count and source audit checks.

The CSV export path remains available for offline review or local fallback:

```text
src/dashboard/export_powerbi_gold_tables.py
```

The CSV script writes Power BI import files to:

```text
dashboard/exports/
```

Generated export files and `.pbix` files are intentionally ignored by Git. The `.pbix` should be submitted outside Git or rebuilt locally from `powerbi_semantic_model.md` and `powerbi_measures.dax`.

## Validate Exports

After the export runs, validate the local dashboard files:

```text
tests/data_validation/validate_powerbi_gold_exports.py
```

The validation checks required files, manifest metadata, AO3 columns, probability
ranges, and target-column exclusions. It should be run only after the export
files exist.

## Dashboard Delivery Status

- Direct Databricks SQL serving-layer connection is the preferred Power BI workflow for issue `#139`.
- The Power BI Project semantic model is connected to governed Databricks outputs.
- The AO1 delivery-risk executive page is implemented and documented (Issue `#48`).
- AO2 and AO3 executive pages remain incremental dashboard tasks.
- CSV exports remain available as offline fallback artifacts and must not be edited manually.
- No `.pbix` artifact is required or claimed in this repository.
