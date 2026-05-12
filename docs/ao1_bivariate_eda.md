# AO1 Bivariate Late-Delivery EDA

Issue: `[W3][P1][#2] Bivariate EDA: correlates of late delivery #19`

## Purpose

This note documents the focused AO1 bivariate EDA workflow implemented in:

```text
notebooks/eda/ao1_bivariate_late_delivery_eda.py
```

The notebook identifies descriptive associations with `Late_delivery_risk` for
candidate order-time and pre-dispatch variables. It does not train models,
finalize Gold tables, perform target-based feature selection, or approve
conditional variables for modeling.

## Input Contract

The notebook expects one local Silver CSV clone:

```text
data/silver/dataco_orders_silver.csv
```

Set `DATACO_AO1_EDA_INPUT_PATH` only when using another local Silver CSV clone.
The notebook intentionally does not fall back to `data/raw/`. If the Silver CSV
is missing, run `notebooks/pipeline/run_medallion_pipeline.py` first.

The notebook may derive deterministic review features already documented in the
W2 feature-engineering notes, such as order calendar fields, planned shipping
speed tiers, normalized shipping mode, customer/regional tokens, and
product/category review fields. These derivations use order-time or pre-dispatch
inputs only and do not replace the Silver cleaning step.

## Leakage Review Rule

The notebook starts from:

```text
data/references/leakage_conceptual_screening.csv
```

It separates variables into:

- `candidate_for_gold_review`: AO1 `allowed`, not `needs_group_review`, and
  listed as candidate features by the screening artifact.
- `conditional_requires_group_review`: AO1 `conditional` or any variable with
  `needs_group_review` or `conditional_review` policy.
- `exclude_from_ao1_modeling`: target, post-shipment, post-delivery,
  sensitive identifier, profit outcome/proxy, or forbidden predictor fields.
- `dashboard_only`: outcome or audit fields that may support descriptive views
  but must not be AO1 predictors.
- `descriptive_context_only`: metadata or non-candidate fields.

Conditional and `needs_group_review` variables may be summarized descriptively,
but they are not added to the recommended AO1 feature list. All such variables
are written to the group-validation list for team review before modeling. The
list includes a `validation_priority` field so stronger support-safe EDA patterns
can be reviewed first.

## Bivariate EDA Scope

For categorical variables, the notebook reports:

- category counts
- late-delivery rate by category
- difference from the overall late-delivery rate
- a minimum support threshold to avoid overinterpreting small groups

For numeric variables, the notebook reports:

- missing rate
- median comparison by target class
- quantile/bin late-delivery rates when useful

For date/time variables, the notebook uses order-time derived features such as
month, weekday, hour, quarter, weekend flag, and season. The raw order timestamp
is not recommended as a direct model input without explicit group review.

## Outputs

The notebook writes:

```text
report/tables/ao1_late_delivery_bivariate_summary.csv
report/tables/ao1_late_delivery_bivariate_detail_by_group.csv
report/tables/ao1_late_delivery_group_validation_list.csv
```

It also writes a small set of SVG figures under:

```text
report/figures/eda/
```

The summary table includes the leakage policy, decision-time review result,
EDA summary, notable pattern, sample-size caveat, modeling recommendation, and
whether group validation is required.

## Caveats

- Bivariate EDA identifies associations, not causal effects.
- Small groups below the support threshold are not used for signal ranking.
- Dashboard-only, target, post-shipment, post-delivery, actual duration,
  shipping-date, and profit-outcome fields are not candidate AO1 predictors.
- Raw identifiers and postal codes are not ranked as direct numeric signals;
  they require approved grouping or time-aware aggregate design before modeling.
- Conditional or `needs_group_review` variables require project owner or team
  validation before AO1 modeling.
- Final modeling features must still be selected during Gold/modeling work using
  leakage-control rules, chronological split rules, and train-only preprocessing.
