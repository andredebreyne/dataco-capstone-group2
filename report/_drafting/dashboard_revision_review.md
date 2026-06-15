# Revised Dashboard Folder Review

## Decision

needs targeted dashboard fixes

The revised dashboard folder contains a substantial Power BI Project source, semantic model, DAX support, page documentation, and theme assets. It is strong enough to draft the final-report dashboard section, but it is not fully ready for a final evidence package because `dashboard/` does not contain a dashboard PDF export, exported page images, or an updated dashboard page inventory, and one semantic-model table still points to a local CSV path rather than the documented Databricks serving-layer source.

## Files Reviewed

Dashboard-folder evidence reviewed:

- `dashboard/README.md`
- `dashboard/Dashboard.pbip`
- `dashboard/Dashboard.Report/definition/report.json`
- `dashboard/Dashboard.Report/definition/pages/pages.json`
- `dashboard/Dashboard.Report/definition/pages/*/page.json`
- `dashboard/Dashboard.Report/definition/pages/*/visuals/*/visual.json` at page-title, visual-type, and native-query-reference level
- `dashboard/Dashboard.SemanticModel/definition/model.tmdl`
- `dashboard/Dashboard.SemanticModel/definition/relationships.tmdl`
- `dashboard/Dashboard.SemanticModel/definition/tables/*.tmdl`
- `dashboard/Dashboard.SemanticModel/TMDLScripts/*.tmdl`
- `dashboard/powerbi_semantic_model.md`
- `dashboard/powerbi_measures.dax`
- `dashboard/pages/*.md`
- `dashboard/themes/*`
- `dashboard/wireframes/*`
- `dashboard/exports/.gitkeep`

Context-only report evidence reviewed:

- Pasted current report text from `C:\Users\bruno\.codex\attachments\07b4b8f8-3b12-454e-8027-1238ca8aad26\pasted-text.txt`
- Current report dashboard section lines 255-266
- Current report Appendix G dashboard artifact notes lines 338-345

The original `.docx` file could not be read directly because it was locked by another process. The pasted text was used instead.

## Dashboard Artifact Inventory

| Artifact | Purpose | Current status | Final-facing use | Report placement |
| --- | --- | --- | --- | --- |
| `dashboard/Dashboard.pbip` | Power BI Project entry file | Present, about 288 bytes | Final source artifact, but not a screenshot/export | Submission package/source reference |
| `dashboard/Dashboard.Report/` | Versioned Power BI report definition | Present with 11 report pages | Final source artifact | Not main report; cite as repository artifact |
| `dashboard/Dashboard.SemanticModel/` | Versioned semantic model and table definitions | Present | Final source artifact; needs one data-source fix | Appendix or technical artifact |
| `dashboard/README.md` | Dashboard status and support-artifact overview | Present and mostly current | Useful for reproducibility | Appendix/supporting documentation |
| `dashboard/powerbi_semantic_model.md` | Semantic-model blueprint and import instructions | Present | Final-facing documentation | Appendix/supporting documentation |
| `dashboard/powerbi_measures.dax` | DAX measure notes | Present | Supporting technical artifact | Appendix only |
| `dashboard/pages/*.md` | Page-level documentation for AO1/AO2/AO3/geographic/executive views | Present | Useful page evidence, but some issue-closing wording is stale for final report | Appendix/supporting documentation |
| `dashboard/themes/*` | Shared visual theme and background assets | Present | Power BI support asset | Submission package only |
| `dashboard/wireframes/*` | Layout and readability standards | Present | Design support evidence | Appendix only |
| `dashboard/exports/` | Intended offline CSV export location | Contains only `.gitkeep`; no PDF, image, CSV, or manifest exports | Not final evidence in current state | Do not cite as completed export evidence |
| `dashboard/*.pbix` | Power BI Desktop binary source | Not present | README says no `.pbix` artifact is required or claimed in repo | Submit separately if required |
| Dashboard PDF export | Final report visual evidence | Not present in `dashboard/` | Needs separate export or human confirmation | Main report/appendix only after export |
| Exported page images/screenshots | Final report visual evidence | Not present in `dashboard/` | Needs separate export or human confirmation | Main report/appendix only after export |

## Revised Page Inventory Summary

Actual PBIP page order from `dashboard/Dashboard.Report/definition/pages/pages.json`:

| Page | Title | Recommended use | Status |
| ---: | --- | --- | --- |
| 1 | `Cover` | Opening page only | appendix_only |
| 2 | `Executive Overview` | Best main-report dashboard figure | final_needs_formatting |
| 3 | `AO1 | Policy Evidence` | AO1 threshold and validation appendix | final |
| 4 | `AO1.1 | Operational Action` | AO1 operational drill-down appendix | final |
| 5 | `AO2 | Profitability` | AO2 profitability appendix | final |
| 6 | `AO2.1 | Margin Protection` | AO2 margin-protection appendix | final |
| 7 | `AO3 Prioritization` | AO3 matrix and governance appendix | final |
| 8 | `AO3.1 | Operational Allocation` | AO3 operational allocation appendix | final |
| 9 | `AO3.2 | Operational Decision Timeline` | AO3 recent operating pressure appendix | final |
| 10 | `P04 | Geographic & Commercial Hotspots` | Geographic hotspot appendix | final |
| 11 | `P04 Geographic Risk-Margin Exposure` | Map/scatter appendix only after confirmation | needs_human_confirmation |

The complete updated inventory was created at `report/dashboard_page_inventory_updated.csv`.

## Main Report Figure Recommendation

Recommended main report figure page:

- `Executive Overview` from PBIP page 2, not PBIP page 1.

Proposed figure title:

- `Power BI Executive Overview for DataCo Risk-Margin Prioritization`

Proposed caption:

- `The Power BI Executive Overview summarizes the governed scored order population, AO1 delivery-risk exposure, AO2 expected profitability, and AO3 operational priority groups in a single decision-support view. The page shows the active review queue, protected value at risk, expected profit, expected margin, and management action agenda using frozen upstream model outputs.`

Proposed source note:

- `Source: Power BI dashboard project in dashboard/Dashboard.pbip, page "Executive Overview". Use the current exported PDF or PNG from the final submission package as the visual source after export. Power BI consumes governed upstream outputs and does not retrain AO1/AO2 models or redefine AO3 thresholds.`

Rationale:

- `Executive Overview` is the only page that clearly integrates AO1, AO2, and AO3 for executive readers.
- PBIP page 1 is `Cover`, so the current report wording that treats Page 1 as the executive screenshot is stale under the revised dashboard project.
- The page supports the final report narrative without overloading the reader with AO1/AO2/AO3 implementation detail.

## Appendix Page Recommendations

Recommended appendix pages:

- `AO1 | Policy Evidence` for AO1 threshold, validation recall/precision, alert-rate, and confusion-matrix context.
- `AO1.1 | Operational Action` for the preventive attention queue.
- `AO2 | Profitability` for expected profit, expected margin, profit-band distribution, and AO2 validation limitations.
- `AO2.1 | Margin Protection` for negative-profit exposure and loss-concentration review.
- `AO3 Prioritization` for the risk-margin matrix and governed cutoffs.
- `AO3.1 | Operational Allocation` for protect/selectively-expedite/preserve-service operating treatments.
- `AO3.2 | Operational Decision Timeline` for four-week operating pressure and action matrix.
- `P04 | Geographic & Commercial Hotspots` for geographic workload versus severity.
- `P04 Geographic Risk-Margin Exposure` only after human confirmation that map rendering is clean and no visible map warning appears.

Do not use `Cover` as an analytical report figure.

## Current Report Section Gaps

Still correct:

- Power BI is correctly described as the official dashboard deliverable.
- The dashboard is correctly described as a communication layer, not a modeling layer.
- The report correctly states that Power BI should not recreate AO1/AO2 scores, recalculate AO3 margins, retune thresholds, or reassign segments.
- Separate `.pbix` submission is consistent with `dashboard/README.md`, which says generated `.pbix` files are ignored by Git and should be submitted outside Git or rebuilt locally.
- The governance distinction between validation evidence and operational scored outputs remains correct.

Outdated or incomplete:

- The report says the exported dashboard PDF, Page 1 executive screenshot, and page inventory are included as final report evidence. Those artifacts are not present in `dashboard/`; `dashboard/exports/` contains only `.gitkeep`.
- The report uses Page 1 as the main executive screenshot source. In the revised PBIP page order, Page 1 is `Cover` and Page 2 is `Executive Overview`.
- The report section labels the figure as Figure 5, while Appendix G refers to Figure 2. This is an internal report numbering inconsistency.
- The report references `report/final_report_assets/figures/DataCo_Dashboard.pdf`, `figure_2_powerbi_executive_command_center.png`, and old page-inventory files. Those are outside the requested dashboard-folder source of truth and were not validated as current.
- The report says the serving-layer manifest supports quality review. The current PBIP semantic model does not show a manifest table imported into the dashboard model.
- The report's direct Databricks serving-layer wording is mostly supported, but `dashboard/Dashboard.SemanticModel/definition/tables/powerbi_geographic_summary.tmdl` currently imports from `C:\Users\jorha\Downloads\powerbi_geographic_summary.csv`, which conflicts with the documented Databricks serving-layer architecture.
- The current report does not summarize the actual revised PBIP page titles and grouping.
- The current report does not mention the revised distinction between executive overview, AO1 policy/action, AO2 profitability/margin protection, AO3 prioritization/allocation/timeline, and geographic pages.

Unsupported by dashboard-folder evidence:

- A current dashboard PDF export.
- Current dashboard screenshots/images.
- A current dashboard-folder page inventory.
- A Git-tracked `.pbix` file.
- Final serving-layer manifest row counts.

## Metrics and Content Consistency

Internally consistent within dashboard page documentation:

- AO1 page documentation reports 34,467 scored order items, 13,804 high-risk order items, a 40.0% high-risk rate, and a 35.0% approved AO1 threshold.
- AO2 page documentation reports 34,467 scored order items, $740,319 aggregate expected profit, $21.48 average expected profit, 10.4% expected margin, and 112 negative expected-profit items.
- AO3 page documentation reports 34,467 scored order items, 13,804 active review items, 13,752 protect-high-value-at-risk items, 52 expedite-selectively items, 20,603 preserve-service items, and 60 standard-process items.
- The AO3 segment counts sum to the documented scored population: 13,752 + 52 + 20,603 + 60 = 34,467.

Needs `needs_project_artifact_cross-check`:

- Any numeric metric that must be recalculated from refreshed Databricks serving tables or CSV exports, because no data export files are present in `dashboard/exports/`.
- Dashboard PDF/page-image agreement, because no dashboard-folder PDF or page images are present.
- Page 11 map warning status, because the PBIP contains a `filledMap` visual but the dashboard folder does not contain a rendered screenshot/PDF for visual inspection.

Consistency issues:

- The README and semantic-model documentation describe Databricks serving-layer tables as the preferred path, but `powerbi_geographic_summary.tmdl` still uses a local CSV file path.
- Dashboard page documentation under `dashboard/pages/` covers business-question specifications, but it does not provide a complete 11-page PBIP inventory using the actual revised page titles.
- Some page documentation still contains issue-closing instructions such as "attach a final screenshot to the pull request"; this is useful development history but stale for final-report prose.

## Dashboard Architecture and Governance

Supported by dashboard-folder evidence:

- Power BI is the selected dashboard platform.
- The dashboard consumes governed upstream AO1, AO2, and AO3 outputs.
- Power BI must not retrain models, reconstruct targets, recreate thresholds, or redefine AO3 segment assignments.
- The semantic model includes core AO1, AO2, AO3, recommendation, policy, validation, geography, visualization, and date tables.
- Most `powerbi_*` semantic tables connect through `DatabricksMultiCloud.Catalogs(...)` to the documented Databricks SQL warehouse path.
- DAX measures support KPI aggregation, QA checks, threshold display, AO1/AO2 validation display, AO3 segmentation, and executive time-window summaries.

Architecture issue:

- `powerbi_geographic_summary.tmdl` uses `Csv.Document(File.Contents("C:\Users\jorha\Downloads\powerbi_geographic_summary.csv"))`. This should be replaced with the governed Databricks serving-layer table or documented explicitly as an offline fallback before final submission.

Governance language to preserve in the final report:

- Validation evidence is not realized intervention evidence.
- Expected profitability is modeled expected profit, not realized accounting profit.
- Protected value is exposure, not realized savings.
- Four-week operating comparisons are not statistical forecasts.
- The dashboard is an academic decision-support prototype, not a production deployment claim.

## PBIX and Submission Route

PBIX status:

- No `.pbix` file exists inside `dashboard/`.
- `dashboard/Dashboard.pbip` exists and is approximately 288 bytes.
- The full Power BI Project source is represented by `Dashboard.pbip`, `Dashboard.Report/`, and `Dashboard.SemanticModel/`.
- `dashboard/README.md` states that generated `.pbix` files are intentionally ignored by Git and that the `.pbix` should be submitted outside Git or rebuilt locally.

Recommendation:

- Do not Git-track `.pbix` unless the course explicitly requires repository submission of the binary file.
- Keep the PBIP project tracked as the repository source artifact.
- Submit a `.pbix` separately through the academic submission system if required.
- Human confirmation is needed only for the final academic submission route: whether the instructor expects `.pbix`, PBIP, PDF export, or all of them.

## Dashboard Folder Cleanup Recommendations

| Path or pattern | Recommendation | Reason |
| --- | --- | --- |
| `dashboard/Dashboard.pbip` | keep_final | Power BI Project entry file. |
| `dashboard/Dashboard.Report/` | keep_final | Current report source with 11 PBIP pages. |
| `dashboard/Dashboard.SemanticModel/` | keep_final | Current semantic model source; fix geographic local CSV source before final refresh. |
| `dashboard/README.md` | keep_final | Good dashboard overview; should be updated only if final export package paths are added. |
| `dashboard/powerbi_semantic_model.md` | keep_final | Core semantic-model documentation. |
| `dashboard/powerbi_measures.dax` | keep_appendix | Useful DAX notes; PBIP TMDL is the stronger source of current implemented measures. |
| `dashboard/pages/q01_ao1_delivery_risk.md` | keep_appendix | AO1 documentation and metric support. |
| `dashboard/pages/q02_ao2_profitability.md` | keep_appendix | AO2 documentation and metric support. |
| `dashboard/pages/q03_ao3_prioritization.md` | keep_appendix | AO3 documentation and metric support. |
| `dashboard/pages/q04_geographic_commercial_hotspots.md` | keep_appendix | Geographic deployment documentation. |
| `dashboard/pages/q05_executive_command_center.md` | keep_appendix | Executive overview documentation. |
| `dashboard/pages/q05_geographic_global_map.md` | needs_human_review | Naming overlaps with Q05 executive page while the PBIP page is P04 geographic exposure. |
| `dashboard/themes/*` | keep_final | Referenced visual/theme assets. |
| `dashboard/wireframes/*` | keep_appendix | Design standards and layout support. |
| `dashboard/exports/.gitkeep` | keep_final | Placeholder only; not final evidence. |
| `dashboard/.gitkeep` | delete_after_confirmation | Root dashboard folder is no longer empty. |
| `dashboard/Dashboard.Report/StaticResources/RegisteredResources/Background*.png` | needs_human_review | Many background assets are registered in the PBIP report; do not delete without Power BI dependency verification. |
| Dashboard PDF exports | needs_human_review | None found under `dashboard/`; export current dashboard before citing. |
| Dashboard screenshots/page images | needs_human_review | None found under `dashboard/`; export current pages before citing. |
| Dashboard page inventory files in `dashboard/` | needs_human_review | None found; this task created the updated inventory under `report/`. |
| `.pbix` files | needs_human_review | None found; submit separately if required by the academic system. |

No stale PDFs, duplicate PDFs, old screenshots, exported CSV files, or temporary files were found inside `dashboard/exports/`.

## Blockers

- The supplied `.docx` report could not be read directly because it was locked by another process; the pasted report text was used instead.
- No dashboard-folder PDF export or page-image export exists, so visual export agreement could not be verified.
- No dashboard-folder CSV exports or manifest exist, so dashboard metrics could not be recalculated from exported data within the requested scope.
- Page 11 visual warning status cannot be confirmed without a current rendered export.

## Major Issues

1. `powerbi_geographic_summary.tmdl` points to a local CSV file in another user's Downloads folder, which conflicts with the documented governed Databricks serving-layer architecture.
2. The current report says Page 1 is the executive screenshot, but the revised PBIP page 1 is `Cover`; the main report should use `Executive Overview`, which is PBIP page 2.
3. The current report and appendix cite PDF, PNG, and inventory assets that are not present in `dashboard/` and therefore were not confirmed from the revised dashboard-folder source of truth.
4. The current report has figure-number inconsistency: Figure 5 in the dashboard section versus Figure 2 in Appendix G.

## Minor Issues

- `dashboard/pages/` documentation uses Q01-Q05 business-question files, while the PBIP contains 11 report pages. The docs are useful but not a complete current page inventory.
- Some page docs still use development-review wording such as PR screenshot attachment instructions.
- `powerbi_measures.dax` appears to be supporting DAX notes, while the implemented PBIP measures live in TMDL. Treat the TMDL semantic model as the stronger current implementation source.
- Page 11 uses a `filledMap` visual and should not be used in the main report without a clean rendered export.

## Recommended Next Step

Export the current revised Power BI dashboard to PDF and current page PNGs, confirm that `Executive Overview` is the main figure, fix the geographic semantic-model source so it uses the governed Databricks serving table or a documented fallback, and then replace the existing report dashboard section with `report/final_report_dashboard_section_draft.md`.
