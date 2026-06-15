# Final Report Tables and Figures Manifest

This manifest documents the final report table and figure assets created under `report/final_report_assets/`.

| Asset ID | Type | Report slot | Output path | Source status | Generated status | Ready for main report | Appendix candidate | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `table_1_dataco_dataset_summary` | Table | Table 1. DataCo dataset summary | `tables/table_1_dataco_dataset_summary.md`; `tables/table_1_dataco_dataset_summary.csv` | `ready` | `ready` | Yes | Yes | Dataset source, row count, column count, checksum, governance, and limitation summary. |
| `figure_1_medallion_project_workflow` | Figure | Figure 1. Medallion and project workflow architecture | `figures/figure_1_medallion_project_workflow.md` | `ready` | `ready_needs_formatting` | Yes | Yes | Mermaid source is ready; render to PNG later if needed. |
| `table_2_chronological_split_summary` | Table | Table 2. Chronological split summary | `tables/table_2_chronological_split_summary.md`; `tables/table_2_chronological_split_summary.csv` | `ready` | `ready` | Yes | Yes | AO1/AO2 chronological split summary with final-test caveats. |
| `table_3_ao1_model_validation_comparison` | Table | Table 3. AO1 model validation comparison | `tables/table_3_ao1_model_validation_comparison.md`; `tables/table_3_ao1_model_validation_comparison.csv` | `ready` | `ready` | Yes | No | AO1 validation metrics copied from committed artifact; no metric changes. |
| `table_4_ao2_model_validation_comparison` | Table | Table 4. AO2 model validation comparison | `tables/table_4_ao2_model_validation_comparison.md`; `tables/table_4_ao2_model_validation_comparison.csv` | `ready` | `ready` | Yes | No | AO2 validation metrics copied from committed artifact; includes modest-improvement caveat. |
| `table_5_ao3_risk_margin_matrix_policy` | Table | Table 5. AO3 risk-margin matrix policy | `tables/table_5_ao3_risk_margin_matrix_policy.md`; `tables/table_5_ao3_risk_margin_matrix_policy.csv` | `ready` | `ready` | Yes | No | AO3 deterministic policy and fallback segment rows. |
| `table_6_ao3_held_out_segment_summary` | Table | Table 6. AO3 held-out scored segment summary | `tables/table_6_ao3_held_out_segment_summary.md`; `tables/table_6_ao3_held_out_segment_summary.csv` | `ready` | `ready` | Yes | No | Held-out scored segment summary with H3 evidence note. |
| `figure_2_powerbi_dashboard_screenshot` | Figure | Figure 2. Power BI Executive Command Center for DataCo Risk-Margin Prioritization | `figures/figure_2_powerbi_executive_command_center.png`; `figures/DataCo_Dashboard.pdf`; `figures/Dashboard - Executive view.pdf`; `figures/Dashboard - Command center.pdf` | `ready` | `ready` | Yes | No | Figure 2 PNG was created from the supplied Page 1 dashboard image export. The PDFs remain dashboard evidence sources. No `.pbix` or fake dashboard artifact was created. |
| `powerbi_dashboard_page_inventory` | Dashboard evidence | Power BI dashboard page inventory | `figures/powerbi_dashboard_page_inventory.md`; `figures/powerbi_dashboard_page_inventory.csv` | `ready` | `ready` | Yes | Yes | Page inventory lists 11 exported dashboard pages, main-report use, appendix use, key focus, and Page 11 map/visual warning caveat. |
| `table_7_ao3_operational_recommendation_matrix` | Table | Table 7. AO3 operational recommendation matrix | `tables/table_7_ao3_operational_recommendation_matrix.md`; `tables/table_7_ao3_operational_recommendation_matrix.csv` | `ready` | `ready` | Yes | No | Full source-faithful AO3 managerial action matrix. Source columns are mapped directly and recommendation fields are preserved. |
| `table_7_ao3_operational_recommendation_matrix_concise` | Table | Table 7. AO3 operational recommendation matrix - concise view | `tables/table_7_ao3_operational_recommendation_matrix_concise.md`; `tables/table_7_ao3_operational_recommendation_matrix_concise.csv` | `ready` | `ready` | Yes | No | Optional main-report concise view using only source wording from `segment_interpretation`, `recommended_action`, and `limitations`. |

## Dashboard Evidence

Figure 2 is ready for the main report. The dashboard evidence source is `figures/DataCo_Dashboard.pdf`, and the main report screenshot is `figures/figure_2_powerbi_executive_command_center.png`, created from Page 1 of the supplied dashboard page image export.

The `.pbix` source file is not required as a Git-tracked report artifact. If required by the course, submit or maintain it separately as the Power BI source file.

## Appendix Candidates

If the final Word/PDF report becomes too long, Table 1, Figure 1, Table 2, and the dashboard page inventory can move to appendices while Tables 3 through 7 and Figure 2 remain in the main body. For Table 7, use the full source-faithful table when space allows, or use the concise view in the main report and place the full source-faithful table in an appendix.
