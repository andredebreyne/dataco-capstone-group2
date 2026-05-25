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

The selected candidate was read from the issue `#36` metadata:

```text
models/ao2_profitability/gradient_boosting/ao2_gradient_boosting_metadata.json
```

The Databricks run confirmed:

```text
selected_model_name = ao2_gradient_boosting_regressor
selected_candidate_name = conservative_baseline
selected_model_parameters = n_estimators 200, max_depth 3, learning_rate 0.05,
  subsample 0.8, colsample_bytree 0.8, objective reg:squarederror,
  eval_metric rmse, tree_method hist, random_state 42
```

This is the selected model from the Gradient Boosting workflow. The SHAP step
does not introduce a new target, new predictors, new tuning, or new model
selection.

## Model Source

The current issue `#36` metadata records no saved fitted model artifact:

```text
model_artifact_saved = false
```

The Databricks SHAP run therefore reconstructed the selected model
deterministically from the selected candidate parameters in the metadata and
fit that specification on `development_inner_train` only. The SHAP metadata
records:

```text
model_source = deterministic_reconstruction
saved_model_available = false
deterministic_reconstruction_used = true
no_new_model_selection = true
```

If a future run records and provides a saved fitted pipeline, the same workflow
loads it and records:

```text
model_source = saved_model
```

In this run, SHAP explains the reconstructed selected-model specification. It
does not explain a separately saved fitted object, and it does not represent a
newly selected or newly tuned model.

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
validation_rows_available = 28883
sample_size = 5000
random_state = 42
input_slice = development_inner_validation
training_slice = development_inner_train
final_test_used = false
```

The final `test` partition is not used for fitting, preprocessing fit, SHAP
calculation, plots, findings, validation, or documentation.

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

The approved preprocessing pipeline transformed 32 raw AO2 feature columns
into 1,306 model features. SHAP values are reported in that transformed
feature space, so many categorical effects appear as individual one-hot
levels.

## Databricks SHAP Results

The SHAP run completed at `2026-05-25T21:46:14.041268+00:00` and produced 20
top-driver rows. The table below lists the top 15 features by mean absolute
SHAP value.

| Rank | Feature | Mean Abs SHAP | Importance Share | Driver Family | Target-Policy Status |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `numeric_continuous__item_unit_price` | 106.2163 | 0.0684 | commercial price | caution |
| 2 | `categorical__order_state_normalized_kandahar` | 84.0925 | 0.0542 | geography | caution |
| 3 | `categorical__order_state_normalized_tadlaazilal` | 82.8676 | 0.0534 | geography | caution |
| 4 | `categorical__product_category_key_9_cardio_equipment` | 75.7850 | 0.0488 | product mix | caution |
| 5 | `categorical__order_state_normalized_jeju` | 75.6462 | 0.0487 | geography | caution |
| 6 | `categorical__order_state_normalized_diana` | 52.9509 | 0.0341 | geography | caution |
| 7 | `categorical__order_state_normalized_nyanza` | 48.8613 | 0.0315 | geography | caution |
| 8 | `categorical__order_state_normalized_surjandarn` | 43.7942 | 0.0282 | geography | caution |
| 9 | `categorical__order_country_normalized_taiwn` | 40.5223 | 0.0261 | geography | caution |
| 10 | `categorical__order_state_normalized_yaroslavl` | 38.6225 | 0.0249 | geography | caution |
| 11 | `categorical__order_state_normalized_drenthe` | 37.9398 | 0.0244 | geography | caution |
| 12 | `categorical__order_state_normalized_stvropol` | 36.4076 | 0.0234 | geography | caution |
| 13 | `categorical__order_state_normalized_mequineztafilalet` | 31.9214 | 0.0206 | geography | caution |
| 14 | `categorical__order_state_normalized_zhytmyr` | 30.8582 | 0.0199 | geography | caution |
| 15 | `numeric_continuous__item_discount_rate` | 29.9250 | 0.0193 | discount policy | caution |

The remaining top-20 drivers include `product_category_key_45_fishing`,
`customer_state_normalized_in`, additional order-state one-hot levels, and
`numeric_continuous__order_item_quantity` at rank 20. No shipping-speed feature
appears in the top 20 SHAP drivers for this run, even though shipping features
remain part of the approved AO2 feature set.

The dominant pattern is a mix of commercial predictors and granular one-hot
features:

- `item_unit_price` is the strongest SHAP driver.
- Most top drivers are geography one-hot levels, especially `order_state`,
  `order_country`, and `customer_state` encoded values.
- Product mix appears through `product_category_key_9_cardio_equipment` and
  `product_category_key_45_fishing`.
- Discount rate appears at rank 15.
- Quantity appears in the top 20 but not the top 15.

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

The Databricks metadata records:

```text
target_policy_check_status = passed
forbidden_feature_check_status = passed
raw_feature_check_status = passed
forbidden_feature_tokens_found = []
```

The actual SHAP outputs do not include `Order_Profit_Per_Order`,
`Benefit_per_order`, `Order_Item_Profit_Ratio`, `Order_Item_Total`,
`ao3_order_value`, `Sales`, `Sales_per_customer`, `Order_Item_Discount`,
`Product_Price`, delivery outcome fields, post-shipment fields, final-test
labels, identifiers, partition labels, or lineage columns as SHAP drivers.

`Order_Profit_Per_Order` remains the target only. `ao3_order_value` remains
excluded from AO2 predictors and does not appear as a SHAP driver.

Every top-20 driver has `target_policy_status = caution`, not `forbidden`.
This is expected because the top drivers are either approved commercial
predictors that need careful interpretation (`item_unit_price`,
`item_discount_rate`, `order_item_quantity`) or granular one-hot category
levels that may be sparse or unstable. These caution labels do not indicate a
target-policy failure.

## Business Plausibility

The main SHAP drivers are commercially plausible for profitability prediction,
but they should be interpreted as model behavior on the validation sample, not
as causal effects.

`item_unit_price` is commercially meaningful because unit price can reflect
assortment mix, premium versus low-price items, and expected gross profit
opportunity. It is an approved AO2 predictor, but it is also close to the
commercial calculation context, so the finding should be described cautiously
and reviewed alongside the AO2 target-policy controls.

`item_discount_rate` and `order_item_quantity` are also approved commercial
predictors. They can affect expected profitability through discounting and
order composition, but they require the same caution because AO2 profitability
is vulnerable to target reconstruction if near-formula financial fields are
allowed without controls.

The many geography one-hot drivers are plausible because region, country,
state, or customer-location patterns may reflect market mix, fulfillment cost,
product availability, demand composition, or localized discounting. However,
the specific one-hot levels are granular. Without support-count review, they
should be treated as model-specific associations rather than broad regional
conclusions.

Product category drivers are also plausible because product mix often carries
different margin structures. In this run, cardio equipment and fishing appear
among the top product-related drivers. These are useful interpretive clues for
AO2, but they do not create AO3 segmentation rules by themselves.

## Artifacts

The Databricks SHAP run wrote:

| Artifact | Path |
| --- | --- |
| SHAP script | `src/modeling/explain_ao2_gradient_boosting_shap.py` |
| Validation script | `tests/data_validation/validate_ao2_shap_explainability.py` |
| Metadata | `models/ao2_profitability/explainability/ao2_shap_explainability_metadata.json` |
| SHAP feature importance | `report/tables/ao2_shap_feature_importance.csv` |
| SHAP driver summary | `report/tables/ao2_shap_driver_summary.csv` |
| Findings note | `report/tables/ao2_shap_explainability_findings.md` |
| Top-feature figure | `report/figures/modeling/ao2_shap_top_features.png` |

The top-feature plot is stored at:

```text
report/figures/modeling/ao2_shap_top_features.png
```

The generated findings note contains the full top-20 table, commercial
plausibility review, target-policy review, and caveats.

## Relationship to H2

SHAP supports interpretation of the selected AO2 Gradient Boosting model, but
it does not itself prove H2. H2 evidence remains based on the validation metric
comparison in the AO2 evaluation pack, where the Gradient Boosting Regressor
improved over the Ridge baseline on validation RMSE and MAE. Final H2
confirmation still requires the later held-out final-test evaluation.

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
- The selected model was deterministically reconstructed because no saved
  fitted model artifact was available; SHAP therefore explains the selected
  model specification, not a saved fitted object.
- The 5,000-row SHAP sample may not capture every rare category pattern from
  the full validation slice.
- This workflow depends on completed AO2 Gradient Boosting metadata and the
  issue `#37` AO2 evaluation metadata.
- H2 final confirmation remains deferred to later final-test evaluation.
