# DataCo Capstone Project

Decision-support analytics framework for supply chain operations using the **DataCo Smart Supply Chain** dataset.

The project combines predictive modeling and business intelligence to support pre-shipment decisions by balancing **delivery risk** and **order profitability**.

## Objectives

- **AO1:** Predict late delivery risk at order level.
- **AO2:** Estimate order-level profitability.
- **AO3:** Create a risk-margin segmentation framework for operations.
- **Executive Dashboard:** Deliver a finalized Power BI decision-support layer using governed Databricks serving tables.

## Tech Stack

- **Language:** Python (PySpark)
- **Data Platform:** Databricks
- **Processing Engine:** Apache Spark + Delta Lake
- **Dashboard/BI:** Power BI with governed Azure Databricks serving-layer tables
- **Version Control:** GitHub
- **IDE:** Cursor

## Final Navigation and Status

Use these links for final-facing review:

- Final academic report: [report/Group_2_-_Capstone_DataCo_Report_final.docx](report/Group_2_-_Capstone_DataCo_Report_final.docx). The same final DOCX is submitted through the academic submission system.
- [Final report Markdown source](report/final_capstone_report_final_markdown.md)
- [Final Artifact Index](report/final_artifact_index.md)
- [Final Validation Summary](report/final_validation_summary.md)
- [Final Submission Checklist](report/final_submission_checklist.md)
- [Report Folder Guide](report/README.md)
- [Testing Strategy](docs/TESTING.md)
- [Databricks Setup](docs/databricks_setup.md)
- [Power BI Dashboard Package](dashboard/README.md)
- [Power BI Semantic Model](dashboard/powerbi_semantic_model.md)
- [Power BI Databricks SQL Serving Layer](docs/powerbi_databricks_serving_layer.md)

Current dashboard delivery:

- Power BI is the official visualization and decision-support layer.
- The dashboard uses governed Azure Databricks serving-layer tables and checked-in Power BI Project source files.
- Executive View and Command Center use the same governed analytical outputs as AO1, AO2, and AO3 documentation.
- Power BI does not retrain models, recalculate scores, retune thresholds, or reassign AO3 segments.
- The final `.pbix` is submitted separately through the academic submission system. The repository contains the Power BI project source, documentation, page inventory, semantic-model notes, DAX notes, and supporting exports.

## Development Workflow

To ensure reproducibility, traceability, and collaboration quality, we follow these standards:

### Notebook and Module Policy

- Notebooks are used for exploration, experiments, and orchestration.
- Reusable logic should be implemented in `/src`.
- Critical cleaning, feature engineering, splitting, modeling, evaluation, and prioritization logic should not exist only inside notebooks.
- Notebooks should be runnable from top to bottom.

### 1) Branching and Merge Review

- **Protected `main`:** no direct commits.
- **Feature branches:** `feature/<issue-number>-short-name`  (example: `feature/12-databricks-setup`).
- **Merge review required:** every merge into `main` must go through review.
- **Traceability:** each review should reference its task/issue.

The detailed Git workflow, squash-and-merge rule, branch cleanup process, and cascading branch workflow are documented in `docs/git_strategy.md`.

### 2) Data Architecture (Medallion)

- **Bronze (Raw):** original data with no manual modifications.
- **Silver (Cleaned):** standardized and transformed data, fully code-driven.
- **Gold (Curated):** business-ready aggregated tables for analytics and dashboarding.
- **Reproducibility rule:** all transformations must be done via code.

The detailed folder, Databricks destination, and rerun conventions are documented in `docs/medallion_structure.md`.
The decision-time feature availability map is documented in `docs/feature_availability_map.md`.
- [Project Orchestrator](docs/project_orchestrator.md)
- [Databricks Setup](docs/databricks_setup.md)
- [Power BI Databricks SQL Serving Layer](docs/powerbi_databricks_serving_layer.md)
- [Power BI Geographic Global Map Data](dashboard/pages/q05_geographic_global_map.md)
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
- [AO3 Operational Recommendations](docs/ao3_operational_recommendations.md)
- [AO3 Methodology and Results](docs/ao3_methodology_and_results.md)
- [AO3 K-means Extension](docs/ao3_kmeans_extension.md)
- [AO1 Logistic Regression Baseline](docs/ao1_logistic_regression_baseline.md)
- [AO1 Model Evaluation Pack](docs/ao1_model_evaluation.md)
- [AO1 XGBoost Classifier](docs/ao1_xgboost_classifier.md)
- [AO1 SHAP Explainability](docs/ao1_shap_explainability.md)
- [AO1 Decision Threshold Policy](docs/ao1_decision_threshold.md)
- [AO1 Post-Model Leakage Audit](docs/ao1_post_model_leakage_audit.md)
- [AO1 Results and H1 Validation](docs/ao1_results_h1_validation.md)
- [EDA Findings Summary](docs/eda_findings_summary.md)

### 3) Power BI serving layer

Power BI is the finalized dashboard path. The selected workflow connects Power BI Desktop directly to governed Azure Databricks SQL serving-layer tables.

Supported Power BI consumption paths:

- Preferred: direct Databricks SQL serving layer from `src/dashboard/register_powerbi_databricks_tables.py`.
- Offline fallback: CSV export workflow from `src/dashboard/export_powerbi_gold_tables.py`.
- Geographic global-map support: `src/dashboard/build_powerbi_geographic_summary.py`.

The Databricks serving layer publishes one managed `powerbi_*` table per governed dashboard artifact under the configured catalog/schema, defaulting to `workspace.default`. It preserves the same logical architecture as the CSV export workflow and does not recreate AO1/AO2 scores, AO3 margins, thresholds, segments, or final-test outcome fields.

To refresh the Databricks SQL serving layer from a Databricks notebook:

```python
import os
import runpy
from pathlib import Path

repo_root = Path("/Workspace/Repos/<workspace-user>/dataco-capstone-group2")
os.environ["DATACO_REPO_ROOT"] = str(repo_root)
os.environ["DATACO_POWERBI_SERVING_CATALOG"] = "workspace"
os.environ["DATACO_POWERBI_SERVING_SCHEMA"] = "default"

runpy.run_path(
    str(repo_root / "src/dashboard/register_powerbi_databricks_tables.py"),
    run_name="__main__",
)
```

Override `DATACO_AO1_AO2_TEST_SCORE_OUTPUT_PATH`, `DATACO_AO3_RISK_MARGIN_SEGMENT_OUTPUT_PATH`, or `DATACO_VOLUME_ROOT` only when the upstream Databricks Delta artifacts live outside the documented defaults.

See `docs/powerbi_databricks_serving_layer.md` for table mappings and Power BI connection steps.

## Data Quality

Data quality and methodology are validated across the Medallion architecture, model artifacts, AO3 decision layer, and dashboard/export support files. Silver-layer validation checks row count, required columns, critical non-null fields, key data types, lineage metadata, and quality-report metrics for the cleaned DataCo orders table. Additional validators cover leakage screening, chronological split policy, AO1, AO2, AO3, and dashboard exports when generated.

To run the Silver quality validation in Databricks, execute the Bronze and Silver jobs first, then run:

```text
tests/data_validation/test_silver_quality.py
```

See [docs/TESTING.md](docs/TESTING.md) and [report/final_validation_summary.md](report/final_validation_summary.md) for the current testing strategy and validation details.

## Repository Structure

- `/data` - medallion data folders and references
- `/notebooks` - EDA, experiments, and execution notebooks
- `/src` - reusable modules for cleaning, feature engineering, and modeling
- `/models` - trained model artifacts and outputs
- `/docs` - governance and project documentation
- `/dashboard` - finalized Power BI project source, documentation, page specs, exports, and dashboard support assets
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
- Merge review is complete and the working branch is deleted.

## Final Review Checklist

- Use the final academic report, final artifact index, and report README for grader navigation.
- Treat H1 and H2 as validation-evidence conclusions unless a cited artifact explicitly states otherwise.
- Treat H3 as AO3 segmentation and benchmark evidence, not realized intervention outcome evidence.
- Re-run local or Databricks validators only in the appropriate environment described in `docs/TESTING.md`.
- Treat Power BI as the finalized dashboard deliverable; submit the `.pbix` separately through the academic submission system.
