# Final Report Conversion Check

## 1. Files Created

- `report/final_capstone_report.docx`
- `report/final_report_conversion_check.md`

## 2. Conversion Tool Used

The DOCX was generated from `report/final_capstone_report_final_markdown.md` using the bundled Python runtime and `python-docx`.

Pandoc was not available on PATH. LibreOffice / `soffice` was also not available, so automated rendered-page PNG/PDF visual QA could not be completed in this environment.

## 3. DOCX Status

Status: created and structurally opened successfully.

Structural check results:

- DOCX size: approximately 1.77 MB.
- Paragraph count: 214.
- Word table count: 9.
- Embedded image count: 1.
- References section present.
- Appendices through Appendix H present.

## 4. Source Markdown Marker Status

The source Markdown check found no unresolved APA citation markers, generic source-detail markers, table/figure placeholder markers, or dashboard-finalization markers.

No `.pbix` file was created.

## 5. Figure 1 Rendering Status

Figure 1 is represented in the DOCX as Mermaid source text with a note that it should be manually rendered if a graphical workflow image is required in the final Word/PDF submission.

Mermaid did not render automatically because no Mermaid/Pandoc rendering pipeline was available in this environment.

## 6. Figure 2 Rendering Status

Figure 2 points to the real Power BI screenshot:

`report/final_report_assets/figures/figure_2_powerbi_executive_command_center.png`

The image path resolves successfully and the image was embedded in the DOCX.

## 7. Tables Status

Markdown tables were converted into Word tables. The DOCX structural check found 9 Word tables, covering the report's comparison, summary, result, and recommendation tables plus smaller report/navigation tables.

Manual review is still required for wide-table wrapping, row breaks, and table readability in the final Word/PDF layout.

## 8. References / Appendices Status

The References heading and reference entries are present in the DOCX.

Appendices A through H are present, including artifact navigation, validation summary, data dictionary/schema, repository availability, model metadata, Power BI serving-layer documentation, dashboard artifacts, and AI/tooling usage note.

## 9. Page Count Estimate

Precise page count was not available because rendered-page DOCX/PDF QA could not run without LibreOffice.

Estimated formatted length: approximately 25-32 pages after Word layout, depending on table wrapping, Figure 2 scaling, reference spacing, and appendix placement.

## 10. Manual Formatting Fixes Still Needed

- Render or replace Figure 1 with a graphical Mermaid workflow image if the final Word/PDF should not show Mermaid source text.
- Open the DOCX in Word and confirm Figure 2 is clear, scaled appropriately, and paired with its caption.
- Review wide tables for wrapping, readability, and page breaks.
- Confirm APA reference formatting, especially hanging indents and italic styling after Word conversion.
- Replace repository placeholders before final submission:
  - `[INSERT FINAL REPOSITORY URL]`
  - `[INSERT FINAL COMMIT HASH AFTER FINAL COMMIT]`
- Export the final reviewed DOCX to PDF in Word.

## 11. Recommended Final Manual Review Steps

1. Open `report/final_capstone_report.docx` in Word.
2. Replace the repository URL and final commit-hash placeholders if the final values are available.
3. Render Figure 1 manually as an image or confirm that the Mermaid source representation is acceptable.
4. Check every table for readable column widths and page breaks.
5. Check Figure 2 image clarity and caption placement.
6. Confirm References and Appendices formatting.
7. Save the final Word file and export to PDF.
8. Submit the Power BI `.pbix` separately through the academic submission system.
