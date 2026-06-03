# Dashboard Status and Support Artifacts

This folder contains governed dashboard support artifacts for the final Power BI
dashboard deliverable.

Power BI is the selected dashboard direction. The final report package uses the
exported dashboard PDF, screenshot evidence, page inventory, semantic-model
notes, DAX measure notes, and Databricks serving-layer documentation as report
evidence. The `.pbix` source file is submitted separately through the academic
submission system and does not need to be Git-tracked.

## Files

| Path | Purpose |
| --- | --- |
| `powerbi_semantic_model.md` | Semantic-model blueprint and import instructions for the selected Power BI path. |
| `powerbi_measures.dax` | DAX measures for AO1, AO2, and AO3 Power BI dashboard pages. |
| `exports/` | Gitignored local export folder generated from Databricks Gold outputs when the offline CSV fallback path is run. |

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

Generated export files and `.pbix` files are intentionally ignored by Git. The
`.pbix` source file is submitted separately through the academic submission
system and can be rebuilt locally from `powerbi_semantic_model.md` and
`powerbi_measures.dax` if needed.

## Validate Exports

After the export runs, validate the local dashboard files:

```text
tests/data_validation/validate_powerbi_gold_exports.py
```

The validation checks required files, manifest metadata, AO3 columns, probability
ranges, and target-column exclusions. It should be run only after the export
files exist.

## Dashboard Decision Status

- Power BI is the official dashboard deliverable.
- Direct Databricks SQL serving-layer connection is the selected Power BI workflow for issue #139.
- CSV exports remain available as offline fallback artifacts.
- No Git-tracked `.pbix` artifact is required or claimed here.
- Native Databricks dashboard / Databricks AI/BI dashboard is not the planned final dashboard deliverable.
