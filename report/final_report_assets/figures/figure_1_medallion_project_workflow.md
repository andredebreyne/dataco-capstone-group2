# Figure 1. Medallion and Project Workflow Architecture

Source artifacts: `docs/medallion_structure.md`, `docs/project_orchestrator.md`, `report/final_capstone_report_final_markdown.md`.

Use this Mermaid source to render the final report architecture figure.

```mermaid
flowchart LR
    A["DataCo raw structured dataset"] --> B["Bronze layer: source preservation and registration"]
    B --> C["Silver layer: cleaning, schema standardization, feature availability, leakage controls"]
    C --> D1["Gold AO1 table: late-delivery risk modeling"]
    C --> D2["Gold AO2 table: profitability modeling"]
    D1 --> E1["AO1 XGBoost classifier and Logistic Regression baseline"]
    D2 --> E2["AO2 Gradient Boosting/XGBoost regressor and Ridge baseline"]
    E1 --> F["Held-out AO1/AO2 scored outputs"]
    E2 --> F
    F --> G["AO3 risk-margin framework"]
    G --> H["Power BI serving layer tables"]
    H --> I["Power BI dashboard"]
```

Final report caption suggestion:

Figure 1. Medallion and project workflow architecture from DataCo source data through Bronze, Silver, Gold, AO1/AO2 modeling, AO3 risk-margin prioritization, and the Power BI serving layer.

PNG status: not generated in this task. The Mermaid source can be rendered later in Markdown, Mermaid CLI, VS Code, or another approved report-production tool. No model, Databricks, or dashboard artifact was regenerated.
