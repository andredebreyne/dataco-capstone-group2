# AO2 Bivariate Profitability EDA

Issue: `[W3][P1][#3] Bivariate EDA: profitability drivers #20`

## Purpose

This note documents the focused AO2 bivariate EDA workflow implemented in:

```text
notebooks/eda/ao2_bivariate_profitability_eda.py
```

The notebook identifies descriptive associations with `Order_Profit_Per_Order`
for candidate order-time and pre-dispatch variables. It does not train AO2
models, finalize Gold tables, perform target-based feature selection, or approve
conditional commercial variables for modeling.

## Input Contract

The notebook expects one local Silver CSV clone:

```text
data/silver/dataco_orders_silver.csv
```

Set `DATACO_AO2_EDA_INPUT_PATH` only when using another local Silver CSV clone.
The notebook intentionally rejects raw inputs and does not fall back to
`data/raw/`. If the Silver CSV is missing, run:

```text
notebooks/pipeline/run_project_workflow.py
```

The notebook may derive deterministic review features already documented in the
W2 feature notes, such as order calendar fields, planned shipping speed tiers,
normalized shipping mode, product/category descriptors, customer/regional
tokens, and commercial review fields. These derivations are for EDA review only
and do not replace Silver cleaning or Gold feature construction.

## AO2 Target Rule

The primary target is:

```text
Order_Profit_Per_Order
```

If that column is absent, the notebook checks for `Benefit_per_order` only as an
explicit fallback and flags that condition for group review. In the current
Silver clone, `Order_Profit_Per_Order` is expected to be present and
`Benefit_per_order` remains an excluded duplicate/proxy profit outcome.

The target audit summarizes count, missingness after target filtering, mean,
median, standard deviation, min, max, selected percentiles, skewness, IQR
outliers, `Benefit_per_order` equivalence, and confirms
`Order_Item_Profit_Ratio` is excluded from predictors.

## Leakage And AO2 Policy Rule

The notebook starts from:

```text
data/references/leakage_conceptual_screening.csv
```

It separates variables into these actions:

- `candidate_for_gold_review`: AO2 `allowed`, not `needs_group_review`, and
  listed as candidate features by the screening artifact.
- `conditional_requires_group_review`: AO2 `conditional` or any variable with
  `needs_group_review` or `conditional_review` policy.
- `exclude_from_ao2_modeling`: forbidden predictor fields.
- `dashboard_only`: outcome or audit fields that may support descriptive views
  but must not be AO2 predictors.
- `target_or_proxy_excluded`: AO2 target, duplicate profit outcome, realized
  profit ratio, direct profit proxy, or direct profit transformation.
- `descriptive_context_only`: metadata or non-candidate fields.

Financial, discount, sales, price, quantity, and order-value variables are not
silently approved as predictors. Even when they show a descriptive association
with profit, they remain conditional until the project owner or team validates
their order-time semantics, duplicate-field handling, and target-reconstruction
risk.

## Bivariate EDA Scope

For categorical variables, the notebook reports:

- category counts
- mean profit
- median profit
- difference from the overall mean and median profit
- minimum support threshold to avoid overinterpreting small groups

For numeric variables, the notebook reports:

- missing rate
- quantile-based bins where useful
- mean and median profit by bin
- possible monotonic or nonlinear bin patterns
- outlier and target-reconstruction caveats

The EDA focuses on AO2-relevant topics such as profitability by shipping mode,
planned shipping speed, market, region, customer segment, product category,
department, discount bands, price bands, quantity bands, and order-value bands.
Commercial/order-value fields are analyzed descriptively only and are written to
the group-validation list when conditional or reconstruction-sensitive.

## Outputs

The notebook writes:

```text
report/tables/ao2_profitability_bivariate_summary.csv
report/tables/ao2_profitability_bivariate_detail_by_group.csv
report/tables/ao2_profitability_group_validation_list.csv
```

It also writes a small set of SVG figures under:

```text
report/figures/eda/
```

The summary table includes screening policy, decision-time review result,
target-reconstruction risk, EDA summary, notable pattern, sample-size caveat,
modeling recommendation, group-validation flag, and recommended action.

The group-validation list includes conditional or `needs_group_review` fields
and relevant financial/commercial/profit-proxy fields. For each such variable it
documents the observed pattern, why it may be useful, why it may be risky,
target-reconstruction concern, proposed decision, and the exact group validation
question.

## Caveats

- Bivariate EDA identifies associations, not causal effects.
- Profit is skewed and outlier-sensitive, so mean and median should both be
  reviewed.
- Financial and order-value fields may be useful descriptively but can create
  target-reconstruction risk.
- Conditional or `needs_group_review` variables require team validation before
  AO2 modeling.
- Dashboard-only, post-shipment, post-delivery, actual duration, shipping-date,
  delivery-status, target, and profit-proxy fields must not be AO2 predictors.
- Final AO2 modeling features must still be selected later using leakage
  controls, AO2 target policy, chronological split rules, and train-only
  preprocessing.
