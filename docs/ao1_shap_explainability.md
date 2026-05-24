# AO1 SHAP Explainability

Issue: `#30`

## Purpose

This document defines the reproducible AO1 explainability workflow for the
selected XGBoost late-delivery model. The goal is to identify the dominant
drivers of predicted late-delivery risk and verify that they are operationally
plausible.

## Scope

The SHAP workflow explains validation-slice predictions only. It does not use
the final test partition, select the final AO1 threshold, or change the selected
model.

## Executable Script

```text
src/modeling/explain_ao1_xgboost_shap.py
```

The script retrains the selected AO1 XGBoost candidate using the approved
training slice and approved preprocessing pipeline, then computes SHAP values
for a deterministic validation sample.

## Output Artifacts

```text
report/tables/ao1_shap_feature_importance.csv
report/tables/ao1_shap_driver_summary.csv
report/tables/ao1_shap_explainability_findings.md
report/figures/ao1_shap_top_features.png
models/ao1_late_delivery/explainability/ao1_shap_explainability_metadata.json
docs/ao1_shap_explainability.md
```

## Interpretation Rules

- SHAP values explain model behavior, not causal effects.
- One-hot encoded features may split one business concept across multiple rows.
- Top features must be reviewed for business plausibility before H1 is finalized.
- Any feature that appears to represent a post-shipment outcome must be escalated
  to the AO1 leakage audit before final reporting.

## Validation

After running the explainability script, validate the artifacts:

```text
tests/data_validation/validate_ao1_shap_explainability.py
```

The validation checks required files, metadata, non-empty SHAP tables, leakage
token guardrails, figure creation, and final-test exclusion.
