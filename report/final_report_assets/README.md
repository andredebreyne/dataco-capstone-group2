# Final Report Assets

This folder contains final report-ready table, figure, dashboard, and inventory assets for the final DataCo capstone report package.

The assets were built from checked-in project artifacts and supplied Power BI export evidence only. This package does not regenerate models, rerun Databricks, create a `.pbix`, or change analytical conclusions.

## Folder Structure

| Folder | Purpose |
| --- | --- |
| `tables/` | Main report table assets in Markdown and CSV format. |
| `figures/` | Figure source files, Power BI dashboard evidence, screenshot, and page inventory. |
| `appendix_tables/` | Reserved for tables moved out of the main report during final formatting. |
| `source_manifests/` | Traceability files documenting source artifacts, readiness status, and cleanup decisions. |

## Main Report Assets

| Report slot | Asset files | Status |
| --- | --- | --- |
| Table 1. DataCo dataset summary | `tables/table_1_dataco_dataset_summary.md`; `tables/table_1_dataco_dataset_summary.csv` | Ready. |
| Table 2. Chronological split summary | `tables/table_2_chronological_split_summary.md`; `tables/table_2_chronological_split_summary.csv` | Ready. |
| Table 3. AO1 model validation comparison | `tables/table_3_ao1_model_validation_comparison.md`; `tables/table_3_ao1_model_validation_comparison.csv` | Ready. |
| Table 4. AO2 model validation comparison | `tables/table_4_ao2_model_validation_comparison.md`; `tables/table_4_ao2_model_validation_comparison.csv` | Ready. |
| Table 5. AO3 risk-margin matrix policy | `tables/table_5_ao3_risk_margin_matrix_policy.md`; `tables/table_5_ao3_risk_margin_matrix_policy.csv` | Ready. |
| Table 6. AO3 held-out scored segment summary | `tables/table_6_ao3_held_out_segment_summary.md`; `tables/table_6_ao3_held_out_segment_summary.csv` | Ready. |
| Table 7. AO3 operational recommendation matrix | `tables/table_7_ao3_operational_recommendation_matrix.md`; `tables/table_7_ao3_operational_recommendation_matrix.csv` | Ready as full source-faithful version. |
| Table 7. AO3 operational recommendation matrix - concise view | `tables/table_7_ao3_operational_recommendation_matrix_concise.md`; `tables/table_7_ao3_operational_recommendation_matrix_concise.csv` | Optional concise main-report view using source wording only. |
| Figure 1. Medallion and project workflow architecture | `figures/figure_1_medallion_project_workflow.md` | Ready as Mermaid source; render to PNG later if needed. |
| Figure 2. Power BI Executive Command Center screenshot | `figures/figure_2_powerbi_executive_command_center.png` | Ready. |
| Power BI dashboard PDF evidence | `figures/DataCo_Dashboard.pdf`; `figures/Dashboard - Executive view.pdf`; `figures/Dashboard - Command center.pdf` | Ready. |
| Power BI dashboard page inventory | `figures/powerbi_dashboard_page_inventory.md`; `figures/powerbi_dashboard_page_inventory.csv` | Ready. |

## Use Notes

- Keep Tables 3, 4, 5, 6, 7, and Figure 2 in the main report if space allows.
- Tables 1 and 2 and Figure 1 can move to appendices if final Word/PDF page count is too long.
- Figure 2 uses the real Power BI Executive Command Center screenshot supplied for final packaging.
- Do not treat files in `source_manifests/` as report tables.
