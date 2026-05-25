# AO2 SHAP Explainability

Issue: `#38`

## Purpose and Scope

This workflow explains the selected AO2 Gradient Boosting profitability model
with SHAP values. It is an explainability layer only: it does not change AO2
Gold, preprocessing, target policy, model selection, Ridge logic, Gradient
Boosting training logic, AO3 margin scoring, or H2 final-test conclusions.

The selected AO2 model is:

```text
ao2_gradient_boosting_regressor
selected candidate = conservative_baseline
target = Order_Profit_Per_Order
```

The selected candidate is read from:

```text
models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metadata.json
```

If that metadata is missing or does not identify a selected candidate, the
SHAP job fails clearly rather than guessing a model configuration.

## Model Source

The current issue `#36` metadata records no saved fitted model artifact:

```text
model_artifact_saved = false
```

Therefore the SHAP workflow reconstructs the selected model deterministically
from the selected candidate parameters in the metadata and fits that
specification on the approved AO2 training slice only. The metadata written by
the SHAP job records:

```text
model_source = deterministic_reconstruction
```

If a future run records and provides a saved fitted pipeline, the same workflow
loads it and records:

```text
model_source = saved_model
```

In either case, SHAP explains the selected model specification. It does not
perform new tuning or candidate selection.

## Input Data Slice

Input partition:

```text
/Volumes/workspace/default/raw_data/gold/ao2_profitability_chronological_partitions
```

The current AO2 partition artifact has `development` and `test` labels. The
workflow follows the same inner chronological split used by the selected
Gradient Boosting model:

```text
development_inner_train = first 80% of development rows
development_inner_validation = final 20% of development rows
```

SHAP is computed on `development_inner_validation`, capped by a fixed sample
size for Databricks Community Edition friendliness:

```text
DATACO_AO2_SHAP_MAX_ROWS = 5000
DATACO_AO2_SHAP_RANDOM_STATE = 42
```

If the validation slice is smaller than the cap, the full validation slice is
used. The final `test` partition is not used for fitting, SHAP calculation,
plots, findings, validation, or documentation.

## SHAP Method

The workflow uses:

```text
shap.TreeExplainer
xgboost.XGBRegressor
xgboost==2.0.3
shap==0.44.1
```

SHAP values are computed after the approved AO2 sklearn preprocessing pipeline
has transformed the validation rows into the same feature representation used
by the selected Gradient Boosting model.

Model output space:

```text
raw model output in predicted profit units
```

## Target-Policy Review

AO2 is vulnerable to target reconstruction, so the SHAP workflow checks both
the approved raw feature list and transformed SHAP feature names. The following
must not appear as AO2 predictors or SHAP drivers:

- `Order_Profit_Per_Order`
- `Benefit_per_order`
- `Order_Item_Profit_Ratio`
- `Order_Item_Total`
- `ao3_order_value`
- `Sales`
- `Sales_per_customer`
- `Order_Item_Discount`
- `Product_Price`
- realized margin or profit outcome fields
- delivery outcome and post-shipment fields
- final-test, holdout, partition, identifier, date-anchor, or lineage fields

`ao3_order_value` remains reserved for future AO3 predicted-margin construction
and is not an AO2 predictor or SHAP driver.

Approved commercial predictors such as `item_unit_price`,
`item_discount_rate`, and `order_item_quantity` may appear as SHAP drivers.
They are commercially plausible but should still be interpreted cautiously
because AO2 target reconstruction is a known methodological risk.

## Business Plausibility

The generated driver summary classifies top SHAP features into practical
driver families where possible:

- shipping service
- geography
- product mix
- customer context
- discount policy
- order quantity
- commercial price
- order timing
- order flags

These are useful for AO2 and later AO3 interpretation because they describe
which pre-shipment signals the selected profitability model relies on. They do
not become AO3 segmentation logic, and they should not be interpreted as proof
that changing one feature will causally change profit.

Granular one-hot features, especially geography or product-category levels,
should be reviewed for support and stability before making broad business
claims.

## Artifacts

The Databricks SHAP run writes:

| Artifact | Path |
| --- | --- |
| SHAP script | `src/modeling/explain_ao2_gradient_boosting_shap.py` |
| Validation script | `tests/data_validation/validate_ao2_shap_explainability.py` |
| Metadata | `models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json` |
| SHAP feature importance | `report/tables/ao2_shap_feature_importance.csv` |
| SHAP driver summary | `report/tables/ao2_shap_driver_summary.csv` |
| Findings note | `report/tables/ao2_shap_explainability_findings.md` |
| Top-feature figure | `report/figures/modeling/ao2_shap_top_features.png` |

The generated findings note contains the current top drivers, commercial
plausibility review, target-policy review, and caveats. The static project
documentation intentionally avoids hard-coding a top-driver list before the
Databricks SHAP job has generated those artifacts.

## Run Order

In Databricks, after issue `#36` and issue `#37` artifacts are present, run:

```text
src/modeling/explain_ao2_gradient_boosting_shap.py
tests/data_validation/validate_ao2_shap_explainability.py
```

The project orchestrator exposes disabled-by-default flags:

```python
RUN_AO2_SHAP_EXPLAINABILITY = False
RUN_AO2_SHAP_EXPLAINABILITY_VALIDATION = False
```

## Assumptions and Limitations

- SHAP explanations use validation rows only.
- Final test rows are not used.
- SHAP values are model explanations and associations, not causal effects.
- One-hot encoded features can be granular and unstable.
- The selected model is reconstructed only when no saved fitted model is
  available.
- This workflow depends on completed AO2 Gradient Boosting metadata and the
  issue `#37` AO2 evaluation metadata.
- H2 final confirmation remains deferred to later final-test evaluation.
