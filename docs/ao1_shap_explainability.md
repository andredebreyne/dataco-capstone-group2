# AO1 SHAP Explainability

Issue: `#30`

## Purpose

This document defines the reproducible AO1 explainability workflow for the
selected XGBoost late-delivery model. The goal is to identify the dominant
drivers of predicted late-delivery risk and verify that they are operationally
plausible.

## Scope

The SHAP workflow explains validation-slice predictions only for the selected
AO1 XGBoost model specification. It does not use the final test partition,
select the final AO1 threshold, or change the selected model.

## Executable Script

```text
src/modeling/explain_ao1_xgboost_shap.py
```

The script requires the AO1 XGBoost selected-model metadata at:

```text
models/ao1_late_delivery/xgboost_classifier/ao1_xgboost_classifier_metadata.json
```

The workflow uses deterministic reconstruction for explainability: it reads the
selected candidate from the XGBoost metadata, rebuilds the same candidate
specification from the approved XGBoost candidate grid, fits that specification
on the approved training slice, and computes SHAP values for a deterministic
validation sample. It does not select a new model. This is used because the
current XGBoost workflow stores selected-model metadata and only optionally
stores a fitted model artifact.

Project dependencies for this workflow are pinned to `xgboost==2.0.3` and
`shap==0.44.1` for Databricks reproducibility.

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
- SHAP values explain the positive late-delivery class: `Late_delivery_risk = 1`.
- `TreeExplainer` is used in the default raw model-output space, so values are
  interpreted as directional contributions in raw margin / log-odds space rather
  than direct probability-point changes.
- One-hot encoded features may split one business concept across multiple rows.
- Top features must be reviewed for business plausibility before H1 is finalized.
- Any feature that appears to represent a post-shipment outcome must be escalated
  to the AO1 leakage audit before final reporting.

## Business Plausibility Summary

The current top drivers are plausible pre-dispatch signals because they emphasize
shipping mode, planned shipping days, shipping-speed tier, and geography. These
features are available before dispatch and align with the operational story that
service promise and route context affect late-delivery risk prioritization. The
large `shipping_mode_normalized_first_class` effect should be flagged for review
rather than treated as causal proof; it may reflect service-level, route, or data
composition patterns that need business interpretation.

## Validation

After running the explainability script, validate the artifacts:

```text
tests/data_validation/validate_ao1_shap_explainability.py
```

The validation checks required files, metadata, non-empty SHAP tables, leakage
token guardrails, figure creation, and final-test exclusion.
