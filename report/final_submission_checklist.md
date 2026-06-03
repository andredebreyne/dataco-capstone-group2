# Final Submission Checklist

Status key: `complete`, `manual upload required`, `optional`, `not applicable`.

## 1. Final Report Files

| Item | Status | Evidence / note |
| --- | --- | --- |
| Final Markdown report | `complete` | `report/final_capstone_report_final_markdown.md` |
| Final submission Markdown draft | `complete` | `report/final_capstone_report_submission_draft.md` |
| Final report source draft history | `complete` | `report/final_capstone_report_draft_v6.md` and prior drafts remain available for traceability. |
| Draft V6 change log | `complete` | `report/final_report_draft_v6_change_log.md` |
| Final artifact index | `complete` | `report/final_artifact_index.md` |
| Final validation summary | `complete` | `report/final_validation_summary.md` |
| Final report PDF/Word | `manual upload required` | Convert the final Markdown report to the course-required Word/PDF format before upload. |

## 2. Dataset / Code / Repository Deliverables

| Item | Status | Evidence / note |
| --- | --- | --- |
| Repository package | `complete` | Source code, notebooks, validators, docs, report assets, and dashboard support files are in the repository. |
| Project repository URL | `manual upload required` | Replace `[INSERT FINAL REPOSITORY URL]` in the final Markdown after the final repository URL is confirmed. |
| Final submission branch | `complete` | `report/final-capstone-report` |
| Final branch/tag/commit hash | `manual upload required` | Replace `[INSERT FINAL COMMIT HASH AFTER FINAL COMMIT]` after the final commit or tag is created. |
| Repository availability note | `complete` | Added to Appendix D in `report/final_capstone_report_final_markdown.md`. |
| Dataset source documentation | `complete` | DataCo source and checksums are documented in `docs/data_source_verification.md`; dataset/data dictionary artifacts are referenced in the report appendices. |
| Data dictionary / schema documentation | `complete` | `docs/data_dictionary.md`, `docs/silver_schema_data_dictionary.md`, and related reference artifacts. |
| Databricks setup documentation | `complete` | `docs/databricks_setup.md` and `docs/powerbi_databricks_serving_layer.md`. |
| Project orchestrator documentation | `complete` | `docs/project_orchestrator.md`. |
| Final report assets included | `complete` | Tables, figures, dashboard export, screenshot, and source manifests are under `report/final_report_assets/`. |
| Large local data files | `not applicable` | Large raw/local files are not required as Git-tracked final report artifacts. |

## 3. Power BI Dashboard Deliverables

| Item | Status | Evidence / note |
| --- | --- | --- |
| Power BI dashboard direction | `complete` | Power BI is the official dashboard deliverable. |
| Dashboard PDF export | `complete` | `report/final_report_assets/figures/DataCo_Dashboard.pdf` |
| Main dashboard screenshot | `complete` | `report/final_report_assets/figures/figure_2_powerbi_executive_command_center.png` |
| Dashboard page inventory | `complete` | `report/final_report_assets/figures/powerbi_dashboard_page_inventory.md` and `.csv`. |
| Semantic model notes | `complete` | `dashboard/powerbi_semantic_model.md` |
| DAX measure notes | `complete` | `dashboard/powerbi_measures.dax` |
| Azure Databricks serving-layer documentation | `complete` | `docs/powerbi_databricks_serving_layer.md` |
| Live serving-layer row-count manifest | `optional` | Not included in the report package. Confirm from `workspace.default.powerbi_serving_layer_manifest` only if requested during technical review. |

## 4. `.pbix` Manual Submission Note

| Item | Status | Evidence / note |
| --- | --- | --- |
| `.pbix` Git tracking | `not applicable` | The `.pbix` does not need to be Git-tracked. |
| `.pbix` course submission | `manual upload required` | Submit the Power BI `.pbix` source file separately through the academic submission system. |
| Fake `.pbix` artifact | `not applicable` | No fake `.pbix` should be created or committed. |

## 5. Tables and Figures

| Item | Status | Evidence / note |
| --- | --- | --- |
| Tables 1-7 present in report | `complete` | Present in `report/final_capstone_report_final_markdown.md`. |
| Figure 1 workflow diagram present | `complete` | Mermaid workflow figure is included in the final Markdown report. |
| Figure 2 Power BI screenshot present | `complete` | Figure 2 points to the real Page 1 Power BI screenshot asset. |
| Table/figure placeholder language removed | `complete` | No table or figure placeholder markers remain in the submission draft. |
| Full source-faithful Table 7 available | `complete` | `report/final_report_assets/tables/table_7_ao3_operational_recommendation_matrix.md` and `.csv`. |

## 6. References and APA Formatting

| Item | Status | Evidence / note |
| --- | --- | --- |
| APA citation placeholders removed | `complete` | No unresolved APA citation markers remain in the final Markdown report. |
| Generic source-detail placeholders removed | `complete` | No unresolved source-detail markers remain in the final Markdown report. |
| `## References` section present | `complete` | References section is present in the final Markdown report. |
| Draft-only reference heading removed | `complete` | No draft-only reference heading remains. |
| In-text citation coverage | `complete` | Checked citation surnames against the References section; no missing reference entries were identified. |
| Final APA visual formatting | `manual upload required` | Confirm hanging indents, italics, spacing, and line breaks in the final Word/PDF conversion. |

## 7. Validation Evidence

| Item | Status | Evidence / note |
| --- | --- | --- |
| Local validation summary | `complete` | `report/final_validation_summary.md` |
| Testing documentation | `complete` | `docs/TESTING.md` |
| AO1 validation evidence | `complete` | AO1 validation and comparison artifacts are linked in the report and artifact index. |
| AO2 validation evidence | `complete` | AO2 validation, modest-improvement caveat, and target-reconstruction caution are linked in the report and artifact index. |
| AO3 benchmark evidence | `complete` | AO3 held-out scored segment summary and benchmark documentation are linked in the report and artifact index. |
| Dashboard validation evidence | `complete` | Dashboard export, page inventory, serving-layer docs, semantic model notes, and DAX notes are included. |

## 8. Remaining Manual Checks Before Upload

| Item | Status | Evidence / note |
| --- | --- | --- |
| Convert Markdown to Word/PDF | `manual upload required` | Confirm page layout, heading hierarchy, table wrapping, figure scaling, and appendix placement. |
| Review Figure 2 rendering | `manual upload required` | Confirm the PNG renders clearly in the final Word/PDF file. |
| Confirm final page count | `manual upload required` | Check final formatted length after tables, figures, references, and appendices. |
| Submit `.pbix` separately | `manual upload required` | Required only through the academic submission system, not Git. |
| Final human read-through | `manual upload required` | Confirm no accidental formatting loss during conversion. |

## 9. Items Intentionally Not Git-Tracked

| Item | Status | Evidence / note |
| --- | --- | --- |
| Power BI `.pbix` source file | `not applicable` | Submitted separately through the academic submission system. |
| Large raw/local data files | `not applicable` | Source and setup documentation are provided instead. |
| Local Databricks runtime state | `not applicable` | Reproducibility is documented through setup, orchestrator, and validation docs. |
| Generated local dashboard exports outside final assets | `optional` | CSV/export fallback artifacts are not required unless regenerated for local review. |

## 10. Final Risks, If Any

| Risk | Status | Evidence / note |
| --- | --- | --- |
| Serving-layer row counts not included in report package | `optional` | The report uses dashboard evidence and serving-layer documentation. Live row counts can be confirmed in Databricks if requested. |
| Word/PDF formatting may affect wide tables | `manual upload required` | Use appendix placement or landscape layout if needed. |
| `.pbix` handled outside Git | `manual upload required` | Make sure the manual submission step is completed with the report package. |
