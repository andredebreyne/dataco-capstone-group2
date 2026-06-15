# Final Report Draft V6 Change Log

## 1. Files Created

- `report/final_capstone_report_draft_v6.md`
- `report/final_report_draft_v6_change_log.md`

## 2. Dashboard Markers Resolved

Draft V6 resolves the two dashboard finalization markers that remained in Draft V5:

- `.pbix` submission route;
- serving-layer manifest row-count status.

Remaining dashboard finalization markers in Draft V6: 0.

## 3. `.pbix` Submission Wording Added

Draft V6 states that the Power BI `.pbix` source file is submitted separately through the academic submission system. It also states that the repository contains the dashboard export PDF, screenshot evidence, page inventory, semantic-model notes, DAX measure notes, and Databricks serving-layer documentation.

No `.pbix` file was created, claimed as Git-tracked, or required as part of the repository package.

## 4. Serving-Layer Manifest Row Counts

Verified final serving-layer manifest row counts were not found in the checked repository files inspected for this draft. The available documentation describes the Databricks serving-layer architecture and explains how to confirm row counts from `workspace.default.powerbi_serving_layer_manifest` after the registration script runs, but no final row-count manifest artifact was present.

Draft V6 therefore omits serving-layer manifest row counts and adds cautious wording rather than inventing counts.

Inspected evidence included:

- `docs/powerbi_databricks_serving_layer.md`
- `report/final_report_assets/source_manifests/`
- `dashboard/README.md`
- dashboard export and final report asset files

## 5. Remaining Dashboard Markers

Remaining dashboard finalization markers: 0.

## 6. Remaining Table/Figure Placeholders

- Remaining table placeholders: 0.
- Remaining figure placeholders: 0.

## 7. Remaining Final-Submission Blockers

- Complete final Word/PDF formatting and page-count review.
- If the instructor requests a technical audit of the live Databricks serving layer, confirm row counts directly from `workspace.default.powerbi_serving_layer_manifest` in Databricks.
- Submit the `.pbix` manually through the academic submission system.
