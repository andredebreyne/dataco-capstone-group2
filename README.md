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
- [Project Orchestrator](docs/project_orchestrator.md)
- [Conceptual Leakage Screening](docs/leakage_conceptual_screening.md)
- [Silver Schema Data Dictionary](docs/silver_schema_data_dictionary.md)
- [Pre-Gold Modeling Decisions](docs/pre_gold_modeling_decisions.md)
- [Master Chronological Split Policy](docs/chronological_split_policy.md)
- [AO1 Chronological Partitions](docs/ao1_chronological_partitions.md)
- [AO2 Chronological Partitions](docs/ao2_chronological_partitions.md)
- [AO1 Preprocessing Pipeline](docs/ao1_preprocessing_pipeline.md)
- [AO2 Preprocessing Pipeline](docs/ao2_preprocessing_pipeline.md)
- [AO2 Ridge Baseline](docs/ao2_ridge_baseline.md)
- [AO2 Gradient Boosting Regressor](docs/ao2_gradient_boosting_regressor.md)
- [AO2 Model Evaluation](docs/ao2_model_evaluation.md)
- [AO2 SHAP Explainability](docs/ao2_shap_explainability.md)
- [AO2 Target-Reconstruction Review](docs/ao2_target_reconstruction_review.md)
- [AO2 Results and H2](docs/ao2_results_h2.md)
- [AO1/AO2 Held-Out Test Scoring](docs/ao1_ao2_test_scoring.md)
- [AO3 Risk-Margin Matrix](docs/ao3_risk_margin_matrix.md)
- [AO3 Segment Assignment](docs/ao3_segment_assignment.md)
- [AO3 Risk-Margin Benchmark](docs/ao3_risk_margin_benchmark.md)
- [AO3 K-means Extension](docs/ao3_kmeans_extension.md)
- [AO1 Logistic Regression Baseline](docs/ao1_logistic_regression_baseline.md)
- [AO1 Model Evaluation Pack](docs/ao1_model_evaluation.md)
- [AO1 XGBoost Classifier](docs/ao1_xgboost_classifier.md)
- [AO1 SHAP Explainability](docs/ao1_shap_explainability.md)
- [AO1 Decision Threshold Policy](docs/ao1_decision_threshold.md)
- [AO1 Post-Model Leakage Audit](docs/ao1_post_model_leakage_audit.md)
- [AO1 Results and H1 Validation](docs/ao1_results_h1_validation.md)
- [EDA Findings Summary](docs/eda_findings_summary.md)

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
