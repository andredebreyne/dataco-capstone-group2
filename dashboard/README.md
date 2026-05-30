# Dashboard Status and Support Artifacts

This folder contains governed dashboard support artifacts. The final dashboard
deliverable is still pending, and the team is evaluating a native Databricks
AI/BI dashboard as an alternative to Power BI.

Power BI artifacts in this folder remain one possible implementation path. This
folder does not currently claim a completed dashboard file.

## Files

| Path | Purpose |
| --- | --- |
| `powerbi_semantic_model.md` | Semantic-model blueprint and import instructions for the Power BI path. |
| `powerbi_measures.dax` | Draft DAX measures for AO1, AO2, and AO3 dashboard pages if Power BI is selected. |
| `exports/` | Gitignored local export folder generated from Databricks Gold outputs when the Power BI export path is run. |

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

## Dashboard Decision Status

- Dashboard deliverable is still pending.
- Native Databricks AI/BI dashboard is being evaluated as an alternative to Power BI.
- Power BI remains documented as one possible path.
- No `.pbix` artifact is required or claimed here.
