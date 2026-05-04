# DataCo Capstone Project Context for Codex

You are assisting with the implementation of an academic capstone project in data analytics. The project is practical and business-oriented, but it must remain academically rigorous, reproducible, and aligned with the submitted proposal.

## 1. Project Title

**Predicting Late Delivery Risk and Explaining Order Profitability in a Global E-Commerce Supply Chain**

The project uses the **DataCo Smart Supply Chain** dataset to build a pre-shipment decision-support framework for global e-commerce supply chains.

## 2. Core Research Framing

### Research Question

How can pre-shipment attributes available at order creation be used to build a practical pre-dispatch order-prioritization framework that combines late-delivery risk and expected order profitability in a global e-commerce supply chain?

### Hypotheses

**H1.** For late-delivery prediction, an XGBoost classifier will outperform logistic regression on held-out data, particularly in AUC-ROC and recall.

**H2.** For order-profitability estimation, a gradient boosting regressor will outperform linear or ridge regression on held-out data, particularly in RMSE and MAE.

**H3.** Combining predicted late-delivery risk and expected order profitability in a risk-margin framework will identify pre-dispatch priority groups that are not evident from either signal alone and therefore support differentiated operational actions.

## 3. Integrated Project Logic

This is not three separate projects.

The project is one integrated pre-shipment decision-support framework:

1. **AO1: Late-delivery risk prediction**
   - Estimate the probability that an order will be delivered late.
   - Use only information available at order creation or before dispatch.
2. **AO2: Expected profitability estimation**
   - Estimate expected order-level profitability before dispatch.
   - Avoid simply reconstructing profit from accounting formulas.
3. **AO3: Risk-margin prioritization framework**
   - Combine predicted late-delivery risk from AO1 and predicted profitability from AO2.
   - Create a practical prioritization matrix for operational decisions before dispatch.

The first two analytical outputs are inputs into the third decision-support layer.

## 4. Dataset

Primary dataset: **DataCo Smart Supply Chain for Big Data Analysis**.

Expected characteristics:

- Approximately 180,000+ transactional records.
- Around 50+ variables.
- Includes order, customer, product, shipping, logistics, and financial fields.
- Covers historical e-commerce supply chain activity from approximately 2015-2018.
- Public, anonymized, and partially synthetic.

Important: exact column names must be verified from the actual dataset and metadata file before implementation. Do not hard-code assumptions without checking the schema.

Possible relevant fields include, but are not limited to:

- `Late_delivery_risk`
- `Order Profit Per Order` or equivalent profit field
- `Benefit per order` if that is the actual available profit target
- `Order Item Profit Ratio`
- `Order Item Discount`
- `Order Item Discount Rate`
- `Sales`
- `Order Item Total`
- `Order Item Quantity`
- `Order Item Product Price`
- `Shipping Mode`
- `Days for shipment (scheduled)`
- `Days for shipping (real)`
- `Delivery Status`
- `Shipping Date`
- `Order Date`
- `Market`
- `Order Region`
- `Order Country`
- `Category Name`
- `Customer Segment`

## 5. Critical Methodological Assumptions

### 5.1 Decision-Time Integrity

The project is framed as **pre-shipment decision support**.

Therefore, models must only use information that would genuinely be available at order creation or before dispatch.

Any variable known only after shipment, during fulfillment, or after delivery must be excluded from predictors.

### 5.2 Leakage Prevention

For AO1, exclude variables such as:

- `Days for Shipping (Real)`
- `Delivery Status`
- `Shipping Date`
- any actual delivery outcome
- any field directly derived from delivery completion
- any post-shipment status field

For AO2, avoid target reconstruction. Do not include predictors that mechanically define or nearly reconstruct the profit target.

Examples of possible AO2 risks:

- using profit ratio to predict raw profit
- using fields that are mathematical components of the target without justification
- allowing duplicate financial fields that make the model a formula reconstruction instead of a useful predictive model

### 5.3 Chronological Split

Use a chronological split by order date.

Recommended approach:

- Sort records by order date.
- Use the earliest 80% as development data.
- Use the most recent 20% as final held-out test data.
- Within the development data, use validation or cross-validation for tuning.
- Do not randomly split unless explicitly justified as a secondary robustness check.

### 5.4 Preprocessing Discipline

Any preprocessing must be fit only on training data and then applied to validation/test data.

This includes:

- imputers
- encoders
- scalers
- target encoders, if used
- resampling methods
- historical aggregates
- regional/customer performance features

If SMOTE or another resampling technique is used for AO1, it must be applied only inside the training fold or training sample, never before splitting.

## 6. Target Definitions

### AO1 Target

Primary target:

`Late_delivery_risk`

Treat as a binary classification target.

Before modeling, validate:

- exact meaning of the label
- class distribution
- whether it aligns with delivery lateness
- whether edge cases exist
- whether it is duplicated or implied by other variables

### AO2 Target

Preferred target:

`Order Profit Per Order`

If that exact field does not exist, inspect the metadata and choose the equivalent raw order-level profit field, such as `Benefit per order`.

Do not use `Order Item Profit Ratio` as the primary target unless the team explicitly decides and documents why. It may be used descriptively or as a robustness check.

For AO3, derive expected profit margin after AO2 prediction if needed:

`predicted_profit_margin = predicted_profit / order_value`

The exact denominator must be documented and must be available at order creation.

## 7. Analytical Objectives

### AO1: Late-Delivery Risk Modeling

Goal:

- Predict whether an order is likely to be delivered late.

Baseline model:

- Logistic Regression

Primary model:

- XGBoost classifier

Evaluation metrics:

- AUC-ROC
- recall
- precision
- F1-score
- confusion matrix

Priority metric:

- AUC-ROC for overall discrimination
- recall for operational usefulness, because missing high-risk orders is costly

Important:

- Do not optimize only for accuracy.
- Accuracy may be misleading if classes are imbalanced.
- Select and document an operational threshold using validation data.

### AO2: Expected Profitability Modeling

Goal:

- Estimate order-level profitability before dispatch.

Baseline model:

- Linear Regression or Ridge Regression

Primary model:

- Gradient Boosting Regressor

Evaluation metrics:

- RMSE
- MAE
- R-squared
- residual analysis

Priority metrics:

- RMSE for penalizing larger errors
- MAE for interpretability in business terms

Important:

- Check whether the model is simply reconstructing the profit formula.
- Run an AO2 predictor audit before finalizing results.
- Document excluded financial variables and why they were excluded.

### AO3: Risk-Margin Prioritization Framework

Goal:

- Combine AO1 and AO2 predictions into a pre-dispatch prioritization framework.

Base design:

- 2x2 risk-margin matrix

Example groups:

- High delivery risk / high expected profit
- High delivery risk / low expected profit
- Low delivery risk / high expected profit
- Low delivery risk / low expected profit

The exact thresholds should be defined using validation data, percentiles, or business logic.

Do not make clustering the main AO3 method. K-means or another clustering approach may be optional only if it adds clear interpretability.

H3 must be evaluated by comparing the combined risk-margin framework against single-signal approaches:

- risk-only prioritization
- profit-only prioritization
- combined risk-margin prioritization

## 8. Expected Deliverables

The project should produce:

1. Reproducible data pipeline.
2. Data understanding and leakage audit documentation.
3. Feature availability matrix.
4. Cleaned analytical tables.
5. AO1 model outputs and evaluation.
6. AO2 model outputs and evaluation.
7. AO3 risk-margin framework.
8. Dashboard-ready outputs.
9. Executive-facing Power BI dashboard.
10. Final report figures and tables.
11. Reproducibility documentation.
12. Final presentation support.

## 9. Repository Structure

The repository already follows the agreed project structure. Codex should work within this folder structure and should not create a competing folder layout unless there is a clear reason.

```text
repo/
|-- data/
|   |-- raw/
|   |-- bronze/
|   |-- silver/
|   |-- gold/
|   `-- references/
|-- notebooks/
|   |-- 00_setup_check.py
|   |-- 01_data_understanding.py
|   |-- 02_leakage_audit.py
|   |-- 03_eda.py
|   |-- 04_ao1_late_delivery_model.py
|   |-- 05_ao2_profitability_model.py
|   |-- 06_ao3_risk_margin_framework.py
|   `-- 07_dashboard_outputs.py
|-- src/
|   |-- __init__.py
|   |-- config.py
|   |-- data_io.py
|   |-- schema.py
|   |-- leakage.py
|   |-- features.py
|   |-- split.py
|   |-- preprocessing.py
|   |-- modeling_ao1.py
|   |-- modeling_ao2.py
|   |-- evaluation.py
|   |-- prioritization.py
|   `-- utils.py
|-- tests/
|   |-- test_leakage.py
|   |-- test_split.py
|   |-- test_feature_availability.py
|   |-- test_ao2_target_policy.py
|   |-- test_preprocessing.py
|   `-- test_prioritization.py
|-- models/
|   |-- ao1_late_delivery/
|   |-- ao2_profitability/
|   `-- metadata/
|-- docs/
|   |-- CODEX_PROJECT_CONTEXT.md
|   |-- data_dictionary.md
|   |-- leakage_audit.md
|   |-- feature_availability_matrix.md
|   |-- modeling_protocol.md
|   |-- ao2_target_policy.md
|   |-- dashboard_storyboard.md
|   `-- assumptions_and_limitations.md
|-- dashboard/
|   |-- pbix/
|   |-- exports/
|   `-- screenshots/
|-- report/
|   |-- figures/
|   |-- tables/
|   |-- slides/
|   `-- final_report/
|-- README.md
|-- requirements.txt
`-- .gitignore
```

The `/data` folder may contain local dataset files and references for the team, but large raw data files should not be committed unless the repository policy explicitly allows it. At minimum, the repository must document where the data comes from, how to place it locally, and how to regenerate Silver, Gold, model, dashboard, and report outputs.

## 10. Minimum Tests

Use `/tests` for lightweight validation of reusable logic in `/src`. The test suite should focus on preventing methodological errors, especially data leakage, invalid split logic, AO2 target reconstruction, and incorrect AO3 risk-margin assignment. Tests are not expected to validate full model performance, but they should protect the assumptions that support the research design.

### 10.1 `test_leakage.py`

Checks that forbidden post-shipment variables are not included in AO1 predictors.

Must catch fields like:

- `Days for Shipping (Real)`
- `Delivery Status`
- `Shipping Date`
- actual delivery outcome fields

This is probably the most important test.

### 10.2 `test_split.py`

Checks that the chronological split is valid.

Acceptance logic:

- all training dates are earlier than or equal to validation/test dates
- no future data leaks into training
- split proportions are approximately correct
- order date is parsed correctly

### 10.3 `test_feature_availability.py`

Checks that every modeling feature is classified as one of:

- available at order creation
- available before dispatch
- post-shipment
- unknown / needs review

The model should fail or warn if any post-shipment or unknown feature is used without approval.

### 10.4 `test_ao2_target_policy.py`

Checks that AO2 predictors do not mechanically reconstruct the profit target.

This should validate that forbidden or suspicious fields are excluded from AO2 predictors, especially:

- profit ratio fields
- duplicate profit fields
- fields directly derived from the target
- post-order adjustment fields, if present

This is critical because AO2 is the most vulnerable methodological area.

### 10.5 `test_prioritization.py`

Checks the AO3 risk-margin matrix.

It should validate:

- high risk / high margin classification
- high risk / low margin classification
- low risk / high margin classification
- low risk / low margin classification
- threshold behavior at boundaries
- no missing group assignment

### 10.6 What Not to Test Heavily

Do not spend too much time testing:

- full model training
- exact metric values
- Power BI files
- notebook outputs
- visual formatting

Those are better handled through review checkpoints and documentation.

Best practical rule: use tests for project validity, not for everything.

For this project, the test priority should be:

1. leakage rules
2. chronological split
3. feature availability
4. AO2 target-policy logic
5. AO3 segmentation logic

## 11. Databricks and GitHub Workflow

The team is using Databricks Community Edition.

Important collaboration model:

- Each team member has an individual Databricks Community account.
- GitHub is the central source of truth.
- Databricks Repos should be linked to the GitHub repository.
- Notebooks are used as execution/orchestration layers.
- Reusable logic should live in Python modules under `/src`.

Do not put all logic inside notebooks.

Preferred pattern:

- Notebooks call functions from `/src`.
- `/src` contains reusable transformations, modeling logic, and evaluation utilities.
- Notebooks should be runnable top-to-bottom.

## 12. Branching and Review Policy

Never commit directly to `main`.

Use one branch per issue:

```text
feature/<issue-number>-short-name
```

Example:

```text
feature/12-databricks-setup
```

Every merge into `main` should happen through a pull request.

PR requirements:

- Link to the GitHub issue.
- Summarize what was done.
- List files changed.
- Confirm acceptance criteria.
- Mention assumptions or limitations.
- Require at least one reviewer.
- No self-merge for high-priority or leakage-sensitive tasks.

## 13. Coding Standards

Write clear, simple, reproducible code.

Use:

- Python functions with docstrings.
- Type hints where helpful.
- Config variables instead of hard-coded paths.
- Consistent naming.
- Small, focused modules.
- Explicit random seeds.
- Clear comments for non-obvious decisions.

Avoid:

- hidden manual steps
- hard-coded local paths
- duplicate transformation logic
- fitting preprocessors on full data
- output-heavy notebooks
- fake metrics or placeholder conclusions presented as real results

## 14. Documentation Requirements

Every major phase should update documentation.

Minimum documentation artifacts:

- `README.md`
- `docs/data_dictionary.md`
- `docs/leakage_audit.md`
- `docs/feature_availability_matrix.md`
- `docs/modeling_protocol.md`
- `docs/dashboard_storyboard.md`
- final metrics tables under `outputs/metrics/`

All assumptions must be documented.

Critical assumptions:

- what is considered available at order creation
- what is considered post-shipment
- AO1 target semantics
- AO2 target and excluded predictor policy
- chronological split rule
- threshold selection logic
- AO3 risk-margin cutoff logic

## 15. Dashboard Logic

The dashboard is not just for model performance. It should support managerial decisions.

Recommended dashboard pages:

1. Executive summary
   - total orders
   - late-delivery risk distribution
   - expected profitability distribution
   - priority group counts
2. Delivery risk view
   - risk by region/market
   - risk by shipping mode
   - risk by product category
   - threshold-based high-risk orders
3. Profitability view
   - expected profit by category
   - expected margin by discount band
   - weak-margin segments
4. Risk-margin prioritization view
   - 2x2 matrix
   - recommended actions by group
   - comparison against risk-only and profit-only prioritization
5. Model governance / limitations
   - metrics
   - holdout period
   - leakage controls
   - known limitations

## 16. Suggested Managerial Actions by AO3 Segment

### High Risk / High Profit

Priority intervention:

- monitor closely
- consider faster shipping
- proactive exception management

### High Risk / Low Profit

Controlled intervention:

- avoid expensive recovery unless strategically necessary
- review discount/shipping policy
- monitor for systemic causes

### Low Risk / High Profit

Protect and scale:

- preserve service quality
- identify profitable patterns
- maintain standard fulfillment

### Low Risk / Low Profit

Efficiency focus:

- automate or deprioritize
- review pricing or discount strategy
- avoid unnecessary intervention cost

These actions are examples. Final actions must be supported by the analysis.

## 17. Definition of Done for Issues

An issue is done only when:

- Code or documentation is committed.
- The output is reproducible.
- The output is reviewed by another team member.
- Relevant assumptions are documented.
- No unresolved blockers remain.
- Acceptance criteria are satisfied.
- For modeling tasks, metrics are saved.
- For data tasks, leakage risks are checked.
- For dashboard tasks, the business question is clear.

## 18. How Codex Should Work on This Repo

When asked to work on an issue:

1. Inspect the current repository structure first.
2. Read relevant existing files before creating new ones.
3. Restate the task objective briefly.
4. Identify impacted files.
5. Check for leakage or reproducibility risks.
6. Propose the implementation plan.
7. Make the smallest useful code changes.
8. Update documentation where needed.
9. Add or update tests where practical.
10. Summarize what changed and what still needs review.

Do not invent results.
Do not fabricate metrics.
Do not silently change the project scope.
Do not use post-shipment variables as predictors.
Do not treat placeholder smoke-test outputs as final analysis.

## 19. First Implementation Priorities

Start with these before modeling:

1. Repository structure.
2. Databricks setup notes.
3. Data ingestion.
4. Schema inspection.
5. Data dictionary.
6. AO1 target validation.
7. AO2 target validation.
8. Feature availability matrix.
9. Leakage audit.
10. Master chronological split policy.

Do not start final AO1 or AO2 modeling before target definitions, leakage rules, and split logic are frozen.

## 20. Key Risks to Guard Against

### Risk 1: Data Leakage

Post-shipment variables may accidentally enter the model.

Control:

- use a feature availability matrix
- implement automated leakage checks
- review feature importance for suspicious variables

### Risk 2: AO2 Target Reconstruction

Profit may be mechanically reconstructed from included financial fields.

Control:

- define allowed and forbidden predictors
- run AO2 predictor audit
- document excluded fields

### Risk 3: Inflated Performance from Random Split

Random split may make results unrealistic.

Control:

- use chronological split
- reserve final holdout set
- tune only on development data

### Risk 4: Notebook-Only Logic

Important logic trapped inside notebooks reduces reproducibility.

Control:

- move reusable logic to `/src`
- notebooks orchestrate only

### Risk 5: Dashboard Becomes Too Technical

Dashboard may show model metrics but not support decisions.

Control:

- define dashboard decision questions first
- design around AO3 priority groups
- include recommended operational actions

## 21. Final Project Success Criteria

The project is successful if it can show:

1. A leakage-safe pipeline from raw DataCo data to analytical tables.
2. A defensible AO1 model comparison.
3. A defensible AO2 model comparison.
4. A practical AO3 risk-margin prioritization framework.
5. Evidence that combined prioritization adds value beyond risk-only or profit-only views.
6. A dashboard that supports managerial interpretation.
7. Clear documentation of assumptions, limitations, and reproducibility steps.
