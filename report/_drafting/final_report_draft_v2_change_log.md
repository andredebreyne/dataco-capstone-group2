# Final Report Draft V2 Change Log

This change log summarizes revisions from `report/final_capstone_report_draft_v1.md` to `report/final_capstone_report_draft_v2.md`. V1 was not overwritten.

## 1. Major Edits Made

- Created a cleaner review-ready V2 draft with a less repository-checklist tone.
- Preserved the same analytical conclusions, metrics, caveats, and dashboard direction from V1.
- Reduced main-body artifact path density and moved reproducibility references toward table placeholders, source notes, and appendices.
- Standardized evidence wording across AO1, AO2, and AO3.
- Kept Power BI as the official dashboard deliverable and retained the direct Azure Databricks serving-layer architecture.

## 2. Abstract Cleanup

- Removed internal GitHub status wording from the abstract.
- Removed dashboard finalization/update-point language from the abstract.
- Focused the abstract on the problem, research question, AO1/AO2/AO3 methods, key evidence, Power BI direction, and required caveats.
- Kept the abstract explicit that there is no causal intervention claim, no production deployment claim, and no unsupported final-test confirmation.

## 3. Dashboard Wording Cleanup

- Replaced internal development-status phrasing with final-report wording.
- Stated that the first Power BI dashboard page has been implemented and connected to the Databricks serving layer.
- Kept final screenshot, page title, page inventory, `.pbix` route, and serving-layer manifest details as dashboard finalization markers.
- Preserved the negative statement that Databricks native dashboards and Databricks AI/BI dashboards are not the final planned dashboard deliverable.

## 4. Table/Figure Placeholder Cleanup

V2 reduces and prioritizes placeholders around the essential final report visuals:

| Placeholder | Purpose |
| --- | --- |
| Table 1. DataCo dataset summary | Dataset source, rows, columns, DOI, and governance summary. |
| Figure 1. Medallion and project workflow architecture | Data pipeline and workflow overview. |
| Table 2. Chronological split summary | AO1/AO2 development and test partition evidence. |
| Table 3. AO1 model validation comparison | H1 validation evidence. |
| Table 4. AO2 model validation comparison | H2 validation evidence. |
| Table 5. AO3 risk-margin matrix policy | AO3 segmentation rules. |
| Table 6. AO3 held-out scored segment summary | H3 benchmark segmentation evidence. |
| Figure 2. Final Power BI dashboard page screenshot | Final dashboard visual evidence to add later. |
| Table 7. AO3 operational recommendation matrix | Managerial action summary by segment. |

## 5. Remaining APA TODO Count

V2 keeps keyed APA TODO placeholders and does not add fake metadata.

Current APA TODO count in V2: 31.

Generic source-detail markers should be absent.

## 6. Remaining Dashboard Update Markers

Current dashboard finalization markers in V2: 5.

They cover:

- final dashboard screenshot and page title;
- final Power BI page inventory;
- `.pbix` submission route if required;
- final serving-layer manifest row counts if available and verified;
- final dashboard screenshots/page names appendix.

## 7. Remaining Blockers Before Final Submission

| Blocker or risk | Severity | Next action |
| --- | --- | --- |
| Missing APA metadata | Major | Verify source metadata and replace keyed APA TODOs with final APA references. |
| Missing final dashboard screenshots/page names | Major | Add final Power BI screenshot, page title, and page inventory. |
| `.pbix` submission route not confirmed | Major | Confirm whether course submission requires a separate `.pbix`, rebuilt dashboard, or screenshot evidence. |
| Final Word/PDF formatting not complete | Major | Convert after APA and dashboard updates, then check page count and layout. |
| Remaining older dashboard-status wording in other final-facing docs | Major | Reconcile if those docs remain part of final packaging. |
| Responsible-AI/governance source not verified | Minor to major, depending on final wording | Add a verified source or keep ethics discussion grounded in project controls. |
| Final serving-layer manifest row counts not inserted | Minor | Add only if a verified final serving-layer run is available. |
