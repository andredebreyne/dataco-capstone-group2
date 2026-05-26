# AO3 Risk-Margin Benchmark

Issue: `#43`

## Purpose

This document defines the AO3 benchmark that compares the combined risk-margin
framework against single-signal prioritization. The benchmark supports the H3
review by showing what AO3 reveals beyond risk-only or margin-only views.

The benchmark is a decision-layer comparison. It does not train models, change
thresholds, use realized delivery or profit outcomes, calculate final-test
performance metrics, or claim causal business impact.

## Input

The benchmark reads the AO3 segment table from Issue `#42`:

```text
/Volumes/workspace/default/raw_data/gold/ao3_risk_margin_segments
```

The source table must use the same held-out scored AO1/AO2 population created
for AO3. Required fields include:

| Column | Purpose |
| --- | --- |
| `ao1_predicted_late_delivery_probability` | AO1 risk signal. |
| `ao2_predicted_order_profit` | AO2 expected profit signal. |
| `ao3_predicted_margin` | AO2 predicted profit divided by AO3 order value. |
| `ao3_high_risk_flag` | Approved AO1 threshold applied to AO3. |
| `ao3_high_margin_flag` | Approved AO3 margin cutoff applied to AO3. |
| `ao3_priority_segment` | Combined AO3 operational segment. |

Actual target or outcome columns such as `Late_delivery_risk` and
`Order_Profit_Per_Order` must not be present in the benchmark source table.

## Comparison Design

The benchmark compares three decision views:

| View | Rule |
| --- | --- |
| AO3 combined | Use `ao3_priority_segment`. |
| Risk-only | Group orders by `ao3_high_risk_flag`. |
| Margin-only | Group orders by `ao3_high_margin_flag`. |

This design keeps the comparison simple and reproducible. It reuses the approved
AO3 cutoffs rather than introducing new ranking thresholds.

## Outputs

The workflow writes:

```text
data/references/ao3_risk_margin_benchmark_segment_summary.csv
data/references/ao3_risk_margin_benchmark_crosswalk.csv
data/references/ao3_risk_margin_benchmark_insights.csv
models/ao3_integration/risk_margin_benchmark/ao3_risk_margin_benchmark_metadata.json
```

The crosswalk shows how risk-only and margin-only groups split across AO3
segments. The insight CSV contains compact decision metrics, including the share
of high-risk orders that AO3 separates into high-margin and low-margin actions,
and the share of high-margin orders that AO3 separates into high-risk and
low-risk actions.

## H3 Interpretation

The benchmark supports H3 if the combined AO3 view separates single-signal groups
into operationally different actions. The conclusion should be based on the
observed held-out benchmark, not assumed to be equally strong for both
single-signal views. For example:

- risk-only prioritization groups `protect_high_value_at_risk` and
  `expedite_selectively` together, even though their margin implications differ;
- margin-only prioritization groups `protect_high_value_at_risk` and
  `preserve_service` together, even though their delivery-risk implications
  differ.

The conclusion should be stated in practical terms: AO3 helps managers separate
urgent high-value protection, selective expediting, service preservation, and
standard processing. It should not be stated as proof that AO3 improves realized
profit or delivery outcomes without a later outcome-based evaluation.

If the benchmark shows stronger separation for margin-only prioritization than
for risk-only prioritization, the H3 statement should emphasize that nuance. In
that case, AO3 still adds decision-layer value by separating high-margin orders
that need risk protection from high-margin orders that can remain in
preserve-service handling, while risk-only differentiation should be described
according to the observed split.

## Validation

Run the benchmark in Databricks after the Issue `#42` segment table exists:

```text
src/modeling/benchmark_ao3_risk_margin_framework.py
```

Then run:

```text
tests/data_validation/validate_ao3_risk_margin_benchmark.py
```

The validation checks that the benchmark uses the AO3 held-out segment table,
excludes target/outcome columns, preserves the test-only boundary, writes all
expected artifacts, compares AO3 against both single-signal views, and declares
that no final-test performance metrics were calculated.
