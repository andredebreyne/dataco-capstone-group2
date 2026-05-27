# Power BI Dashboard

This folder contains the Power BI dashboard workspace and governed dashboard
support artifacts.

## Files

| Path | Purpose |
| --- | --- |
| `Dashboard.pbix` | Local Power BI Desktop dashboard file. |
| `powerbi_semantic_model.md` | Semantic-model blueprint and import instructions. |
| `powerbi_measures.dax` | Initial DAX measures for AO1, AO2, and AO3 dashboard pages. |
| `exports/` | Gitignored local export folder generated from Databricks Gold outputs. |

## Export Data for Power BI

Run the Databricks export script after AO1/AO2 scoring and AO3 segmentation are
available:

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
ranges, and target-column exclusions.

## Power BI Setup

1. Open `Dashboard.pbix`.
2. Import the CSV files from `dashboard/exports/`.
3. Rename tables according to `powerbi_semantic_model.md`.
4. Add the measures from `powerbi_measures.dax`.
5. Refresh the model and compare row counts with `powerbi_export_manifest.json`.
