## Power BI Dashboard and Visualization Layer

### 1. Dashboard Purpose

Power BI is the final visualization and decision-support layer for the capstone. Its role is to translate governed AO1, AO2, and AO3 outputs into an interface that can be interpreted by executive, operations, and finance stakeholders. The dashboard supports delivery-risk monitoring, expected profitability review, risk-margin prioritization, operational allocation, and executive interpretation.

The dashboard is not a model-training layer. AO1 late-delivery probabilities, AO2 expected-profit estimates, and AO3 segment assignments are produced upstream and consumed as frozen analytical outputs. Power BI presents these outputs through governed KPIs, segmentation views, validation evidence, and operational queues so that managers can review where attention should be allocated before dispatch.

### 2. Dashboard Architecture

The dashboard is maintained as a Power BI Project in `dashboard/Dashboard.pbip`, with report definitions under `dashboard/Dashboard.Report` and semantic-model definitions under `dashboard/Dashboard.SemanticModel`. The documented preferred workflow connects Power BI Desktop to Azure Databricks SQL serving-layer tables that expose governed `powerbi_*` outputs. The dashboard folder also documents an offline CSV fallback path for review or local import, but the analytical source of truth remains the governed upstream outputs.

The semantic model organizes the dashboard around scored order-item outputs, AO1 threshold-policy evidence, AO2 validation and profitability evidence, AO3 segment and policy tables, operational recommendations, and geographic summaries. DAX measures support presentation, interaction, aggregation, QA indicators, and executive time-window comparisons. They do not retrain AO1 or AO2, recalculate model scores, retune thresholds, or redefine AO3 segments.

This architecture preserves the boundary between analytics and reporting. Validation tables are presented as validation evidence, while AO3 scored rows are presented as prediction outputs and segment assignments. Expected profitability should therefore be read as modeled expected profit, not realized accounting profit, and protected value should be read as governed order-value exposure, not realized savings.

### 3. Dashboard Page Structure

The revised Power BI project contains 11 report pages:

1. `Cover`
2. `Executive Overview`
3. `AO1 | Policy Evidence`
4. `AO1.1 | Operational Action`
5. `AO2 | Profitability`
6. `AO2.1 | Margin Protection`
7. `AO3 Prioritization`
8. `AO3.1 | Operational Allocation`
9. `AO3.2 | Operational Decision Timeline`
10. `P04 | Geographic & Commercial Hotspots`
11. `P04 Geographic Risk-Margin Exposure`

The `Executive Overview` page is the strongest main-report figure because it summarizes the full decision-support narrative in one view. It combines the scored order population, high delivery-risk exposure, expected profitability, active review queue, protected value at risk, AO3 portfolio mix, and executive action agenda.

The AO1 pages provide the delivery-risk lens. `AO1 | Policy Evidence` presents the approved threshold and validation evidence, while `AO1.1 | Operational Action` turns high-risk exposure into an immediate preventive review queue. The AO2 pages provide the profitability lens. `AO2 | Profitability` summarizes expected-profit exposure and model limitations, while `AO2.1 | Margin Protection` focuses on negative-profit and loss-exposure review. The AO3 pages provide the integrated prioritization layer through the risk-margin matrix, operational allocation view, and recent decision timeline. The geographic pages support regional deployment by separating high-volume workload hotspots from disproportionate severity hotspots.

### 4. Main Dashboard Findings

The revised dashboard communicates a governed scored population of 34,467 order items. Within that population, 13,804 order items are classified as high delivery risk, representing 40.0% of scored items under the approved AO1 threshold of 35.0%. This high-risk group defines the preventive attention queue used by the dashboard.

AO2 profitability evidence shows an aggregate expected profit of $740,319 and an expected margin of 10.4% for the scored population. The dashboard also identifies 112 negative expected-profit items, which are treated as a margin-protection review queue rather than as realized losses.

AO3 combines the delivery-risk and profitability signals into differentiated operating treatments. The documented AO3 portfolio includes 13,752 `protect_high_value_at_risk` items, 52 `expedite_selectively` items, 20,603 `preserve_service` items, and 60 `standard_process` items. The dashboard highlights $2,816,571 in protected order value at risk, supporting a management focus on broad preventive protection while keeping premium-cost expedite decisions selective.

### 5. Decision-Support Interpretation

The dashboard supports management by separating workload scale from severity and by linking each analytical signal to a practical decision. A risk-only view identifies late-delivery exposure, but it does not show whether intervention is economically justified. A profitability-only view identifies margin exposure, but it does not show whether the order is operationally at risk. The AO3 dashboard layer combines both signals and therefore helps managers focus attention on orders where service risk and expected value interact.

The `protect_high_value_at_risk` segment should be treated as the primary preventive protection queue. These items justify monitoring, dispatch-readiness checks, and exception management before lower-priority work. The `expedite_selectively` segment should receive individual review before premium-cost intervention because the items are high risk but financially weaker. The `preserve_service` segment supports normal service quality without unnecessary escalation, while the `standard_process` segment supports routine handling unless new operational information emerges.

The geographic pages add a deployment lens. They help distinguish countries or regions with large high-risk workload from locations with disproportionate high-risk rates. This supports capacity planning and investigation, but it does not redefine AO1 thresholds, AO2 profitability estimates, or AO3 segment assignments.

### 6. Governance and Limitations

Dashboard values depend on frozen upstream outputs. Power BI should not be interpreted as recalculating AO1 scores, AO2 expected profits, AO3 thresholds, or AO3 segment assignments. Validation metrics and operational scored outputs also refer to different analytical contexts and should not be combined as though they were the same population.

Displayed expected profitability is modeled expected profit rather than realized accounting profit. Protected value is exposure requiring managerial attention, not evidence of savings. The dashboard does not prove that any intervention caused improved delivery performance or profitability. It also does not represent a production deployment claim. Production use would require refresh governance, access controls, monitoring, drift review, intervention-cost logic, and periodic threshold reassessment.

The dashboard should therefore be used as a governed academic decision-support prototype. It supports prioritization, review, and communication, while preserving the need for human oversight and periodic review of model outputs, thresholds, and operational policies.

### 7. Dashboard Evidence and Submission Package

The dashboard repository folder contains the Power BI Project source, report definitions, semantic-model definitions, DAX measure notes, page documentation, theme assets, and wireframe standards. The updated page inventory is maintained separately as `report/dashboard_page_inventory_updated.csv`.

The `.pbix` file is not required as a Git-tracked repository artifact according to the dashboard documentation. If the academic submission system requires a `.pbix`, it should be submitted separately from Git. Dashboard screenshots or PDF exports used in the final report should be generated from the current revised Power BI file and treated as presentation evidence rather than as the analytical source of truth.
