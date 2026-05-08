# DataCo Capstone Project

Decision-support analytics framework for supply chain operations using the **DataCo Smart Supply Chain** dataset.

The project combines predictive modeling and business intelligence to support pre-shipment decisions by balancing **delivery risk** and **order profitability**.

## Objectives

- **AO1:** Predict late delivery risk at order level.
- **AO2:** Estimate order-level profitability.
- **AO3:** Create a risk-margin segmentation framework for operations.
- **Executive Dashboard:** Deliver insights for tactical and strategic decisions.

## Tech Stack

- **Language:** Python (PySpark)
- **Data Platform:** Databricks
- **Processing Engine:** Apache Spark + Delta Lake
- **Visualization:** Power BI
- **Version Control:** GitHub
- **IDE:** Cursor

## Development Workflow

To ensure reproducibility, traceability, and collaboration quality, we follow these standards:

### Notebook and Module Policy

- Notebooks are used for exploration, experiments, and orchestration.
- Reusable logic should be implemented in `/src`.
- Critical cleaning, feature engineering, splitting, modeling, evaluation, and prioritization logic should not exist only inside notebooks.
- Notebooks should be runnable from top to bottom.

### 1) Branching and Pull Requests

- **Protected `main`:** no direct commits.
- **Feature branches:** `feature/<issue-number>-short-name`  (example: `feature/12-databricks-setup`).
- **Pull Requests required:** every merge into `main` must go through PR review.
- **Traceability:** each PR should reference its task/issue.

The detailed Git workflow, squash-and-merge rule, branch cleanup process, and cascading branch workflow are documented in `docs/git_strategy.md`.

### 2) Data Architecture (Medallion)

- **Bronze (Raw):** original data with no manual modifications.
- **Silver (Cleaned):** standardized and transformed data, fully code-driven.
- **Gold (Curated):** business-ready aggregated tables for analytics and dashboarding.
- **Reproducibility rule:** all transformations must be done via code.

The detailed folder, Databricks destination, and rerun conventions are documented in `docs/medallion_structure.md`.
The decision-time feature availability map is documented in `docs/feature_availability_map.md`.

## Data Quality

Data quality is validated across the Medallion architecture before downstream feature engineering, modeling, or dashboard outputs depend on the data. Silver-layer validation currently checks row count, required columns, critical non-null fields, key data types, lineage metadata, and quality-report metrics for the cleaned DataCo orders table.

To run the Silver quality validation in Databricks, execute the Bronze and Silver jobs first, then run:

```text
tests/data_validation/test_silver_quality.py
```

See `docs/TESTING.md` for the complete testing strategy and validation details.

## Repository Structure

- `/data` - medallion data folders and references
- `/notebooks` - EDA, experiments, and execution notebooks
- `/src` - reusable modules for cleaning, feature engineering, and modeling
- `/models` - trained model artifacts and outputs
- `/docs` - governance and project documentation
- `/dashboard` - Power BI files (`.pbix`)
- `/report` - final academic report and presentation materials

## Project Management (Agile/Kanban)

### Status Flow

`Backlog` -> `Ready` -> `In Progress` -> `In Review` -> `Done`

### WIP and Prioritization

- **WIP limit:** max 2 tasks per person in `In Progress`.
- **Priority levels:** `P0 (Critical)`, `P1 (High)`, `P2 (Medium)`, `P3 (Low)`.

### Definition of Done (DoD)

A task is considered **Done** only when:

- Deliverable is completed and reviewed.
- Outputs are validated against project objectives.
- README/Wiki documentation is updated.
- PR is merged and working branch is deleted.

## Next Steps

- Finalize feature engineering for late-delivery modeling.
- Benchmark baseline and advanced models for AO1 and AO2.
- Connect curated Gold tables to the executive Power BI dashboard.
