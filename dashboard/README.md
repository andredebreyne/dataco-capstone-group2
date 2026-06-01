# Dashboard Status and Support Artifacts

This folder contains the governed Power BI dashboard project and its support
artifacts. Power BI is the selected executive-dashboard implementation path.
Dashboard pages are developed incrementally from approved Databricks Gold
outputs and governed reference artifacts.

## Files

| Path | Purpose |
| --- | --- |
| `powerbi_semantic_model.md` | Semantic-model blueprint and import instructions for the Power BI path. |
| `powerbi_measures.dax` | Draft DAX measures for AO1, AO2, and AO3 dashboard pages if Power BI is selected. |
| `exports/` | Gitignored local export folder generated from Databricks Gold outputs when the Power BI export path is run. |
| `pages/q01_ao1_delivery_risk.md` | Implemented AO1 delivery-risk executive page specification for Issue `#48`. |
| `themes/dataco_executive_operations_dark.json` | Shared executive dashboard theme. |
| `wireframes/` | Versioned SVG backgrounds and layout standards. |

## Optional Power BI Export Path

If the team chooses or tests the Power BI path, run the Databricks export script
after AO1/AO2 scoring and AO3 segmentation are available:

```text
src/dashboard/export_powerbi_gold_tables.py
```

The script writes Power BI import files to:

```text
dashboard/exports/
```

Generated export files are intentionally ignored by Git. They should be
regenerated from Databricks rather than edited manually.

## Validate Exports

After the export runs, validate the local dashboard files:

```text
tests/data_validation/validate_powerbi_gold_exports.py
```

The validation checks required files, manifest metadata, AO3 columns, probability
ranges, and target-column exclusions. It should be run only after the export
files exist.

## Dashboard Delivery Status

- The Power BI semantic model is connected to governed Databricks outputs.
- The AO1 delivery-risk executive page is implemented and documented.
- AO2 and AO3 executive pages remain incremental dashboard tasks.
- Generated data exports remain reproducible and must not be edited manually.
