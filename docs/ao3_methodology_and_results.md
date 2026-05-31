# AO3 — Risk-Margin Segmentation: Methodology and Results

Issue: `#46`

## 1. Overview

Analytical Objective 3 (AO3) integrates the outputs of AO1 (late-delivery risk
classification) and AO2 (order profit regression) into a unified pre-dispatch
prioritization framework. The goal is to segment orders into operationally
distinct groups that a manager can act on before shipment, using predicted risk
and predicted margin as complementary signals rather than either signal alone.

AO3 does not train a new model. It defines a rule-based segmentation policy
applied to scored orders from the AO1 and AO2 pipelines. All results reported
here are derived from a held-out scored population and validated through the
project benchmark workflow (Issue `#43`).

---

## 2. Methodology

### 2.1 Input Signals

AO3 consumes two model outputs computed for each order:

| Signal | Source | Description |
| --- | --- | --- |
| `ao1_predicted_late_delivery_probability` | AO1 XGBoost classifier | Predicted probability that the order will arrive late. |
| `ao2_predicted_order_profit` | AO2 Gradient Boosting Regressor | Predicted profit per order in dollars. |

A derived margin signal is computed as:

```
ao3_predicted_margin = ao2_predicted_order_profit / ao3_order_value
```

where `ao3_order_value` is the pre-dispatch order value. This normalization
allows margin comparisons across orders of different sizes.

### 2.2 Segmentation Policy

Two approved thresholds are applied to the scored population:

| Threshold | Value | Basis |
| --- | --- | --- |
| `risk_cutoff` | 0.35 | Approved AO1 decision threshold (Issue `#67`) |
| `margin_cutoff` | 0.0 | Separates positive from negative predicted margin |

Each order is assigned to one of six segments using a priority-ordered rule:

| Priority | Condition | Segment |
| --- | --- | --- |
| 1 | `ao1_predicted_late_delivery_probability` or `ao2_predicted_order_profit` is missing | `requires_score_review` |
| 2 | `ao3_order_value` is missing, zero, or negative | `requires_margin_review` |
| 3 | High risk **and** high margin | `protect_high_value_at_risk` |
| 4 | High risk **and** low margin | `expedite_selectively` |
| 5 | Low risk **and** high margin | `preserve_service` |
| 6 | Low risk **and** low margin | `standard_process` |

Fallback categories (rows 1–2) signal data or scoring issues upstream and are
excluded from operational prioritization until the issue is resolved.

### 2.3 Design Rationale

Single-signal prioritization — ranking orders by risk alone or by margin alone
— collapses operationally distinct groups into the same action tier.
Risk-only prioritization, for example, treats a high-risk high-margin order
identically to a high-risk low-margin order, even though the appropriate
response differs materially: one warrants targeted protection of a valuable
order; the other warrants selective review before committing scarce expediting
capacity.

AO3 resolves this by constructing a two-dimensional decision layer from
approved model outputs, without introducing new model training or threshold
optimization.

### 2.4 Validation and Reproducibility

The AO3 segment policy is versioned at:

```
data/references/ao3_risk_margin_matrix_policy.csv
```

The capstone submission policy status is `approved_for_submission`.

Segmentation is executed by:

```
src/modeling/build_ao3_risk_margin_segments.py
```

Validated by:

```
tests/data_validation/validate_ao3_risk_margin_segments.py
```

The benchmark comparison (Issue `#43`) is validated by:

```
tests/data_validation/validate_ao3_risk_margin_benchmark.py
```

Operational recommendations derived from the segment definitions are versioned
at:

```
data/references/ao3_operational_recommendation_matrix.csv
```

---

## 3. Results

### 3.1 Benchmark Population

The AO3 segment table was evaluated on the held-out AO1/AO2 test score
population. All scored orders originate from the chronological test partition;
no development or inner-validation rows are included in the benchmark.

**Total held-out scored orders: 34,467**

### 3.2 Segment Distribution

| AO3 Segment | Count | Share | Avg Predicted Risk | Avg Predicted Profit (USD) | Avg Predicted Margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| `protect_high_value_at_risk` | 13,752 | 39.9% | 0.832 | 21.61 | 0.126 |
| `preserve_service` | 20,603 | 59.8% | 0.319 | 21.60 | 0.126 |
| `expedite_selectively` | 52 | 0.15% | 0.811 | -14.64 | -0.127 |
| `standard_process` | 60 | 0.17% | 0.298 | -20.61 | -0.293 |
| `requires_score_review` | 0 | 0.0% | — | — | — |
| `requires_margin_review` | 0 | 0.0% | — | — | — |
| **Total** | **34,467** | **100%** | | | |

*Percentages are rounded independently; counts sum exactly to 34,467.*

Complete segment summary with full statistics:
`data/references/ao3_risk_margin_benchmark_segment_summary.csv`

### 3.3 Key Observations

**Protect vs preserve split.** The two largest segments — `protect_high_value_at_risk`
(39.9%) and `preserve_service` (59.8%) — have nearly identical average predicted
profit (~USD 21.60) and predicted margin (~0.126). They are distinguished
entirely by delivery risk: 0.832 versus 0.319. Without AO3, margin-only
prioritization would group both into the same high-margin tier and assign the
same handling priority, obscuring the risk differential.

**Expedite_selectively is a small, economically weak group.** The 52 orders
(0.15%) with high predicted risk and negative predicted margin represent a
genuinely different situation from `protect_high_value_at_risk`. Their average
predicted profit is −USD 14.64. Risk-only prioritization would group them with
the 13,752 protect orders. AO3 separates them as a distinct review queue where
committing premium expediting cost is not automatically supported by the
predicted economics.

**Standard_process is small and margin-negative.** The 60 orders (0.17%) with
low risk and negative margin warrant normal operations and margin monitoring
rather than urgent logistics attention.

**No fallback cases observed.** Zero orders in `requires_score_review` or
`requires_margin_review` in this benchmark run, indicating complete score and
margin coverage for the reviewed population.

---

## 4. Value of Combined Prioritization vs Single-Signal Views

The AO3 benchmark (Issue `#43`) compared the combined view against risk-only
and margin-only prioritization using the same held-out population.

### 4.1 What Risk-Only Prioritization Cannot Distinguish

Risk-only prioritization groups orders by `ao3_high_risk_flag` alone. In this
benchmark population, the high-risk group contains:

- `protect_high_value_at_risk`: 13,752 orders with positive predicted margin (0.126)
- `expedite_selectively`: 52 orders with negative predicted margin (−0.127)

These two groups have nearly identical average predicted risk (0.832 vs 0.811)
but opposing margin profiles. Risk-only prioritization offers no basis for
differentiating them. AO3 separates them into distinct action queues.

Note: risk-only differentiation is relatively weak in this held-out sample
because 99.6% of high-risk orders (13,752 of 13,804) are also high-margin.
This reflects a structural property of the data for this test period and should
not be assumed to generalise to all future scoring runs.

### 4.2 What Margin-Only Prioritization Cannot Distinguish

Margin-only prioritization groups orders by `ao3_high_margin_flag` alone. In
this benchmark population, the high-margin group contains:

- `protect_high_value_at_risk`: 13,752 orders with high predicted risk (0.832)
- `preserve_service`: 20,603 orders with low predicted risk (0.319)

Both groups have the same average predicted profit and margin. Margin-only
prioritization would assign both the same urgency tier. AO3 separates them:
`protect_high_value_at_risk` warrants early logistics intervention; `preserve_service`
warrants quality maintenance without escalation. This is the primary dimension
on which AO3 adds decision-layer value in this benchmark.

---

## 5. H3 Conclusion

**H3 statement:** A combined AO3 risk-margin view separates held-out scored
orders into operationally distinct action tiers that neither risk-only nor
margin-only prioritization can fully distinguish.

**Benchmark evidence:**

- Margin-only prioritization would group `protect_high_value_at_risk` and
  `preserve_service` together, even though they differ in predicted delivery
  risk by 0.51 probability units (0.832 vs 0.319). AO3 separates them.
- Risk-only prioritization would group `protect_high_value_at_risk` and
  `expedite_selectively` together, even though their predicted economics differ
  by approximately USD 36 per order (21.61 vs −14.64) and their average margins
  differ in sign. AO3 separates them.

**Assessment:** The benchmark is consistent with H3. AO3 adds measurable
decision-layer value relative to both single-signal baselines for this
held-out population.

The H3 conclusion is appropriately qualified: it applies to the held-out scored
population evaluated in the benchmark run. It does not assert that AO3
intervention improves realised delivery performance or profit outcomes, and it
does not extrapolate to all future scoring periods. Evaluation against actual
delivery and profit outcomes would require a separate outcome-based study.

---

## 6. Limitations

**6.1 Non-causal framework.** AO3 segments and recommendations are based on
predicted risk and predicted profit, not realised outcomes. Assigning an order
to `protect_high_value_at_risk` does not by itself reduce delivery risk or
increase profit. The framework identifies which orders are predicted to need
attention, not which interventions will be effective.

**6.2 Rule-based segmentation.** The segment boundaries are defined by fixed
threshold values (`risk_cutoff = 0.35`, `margin_cutoff = 0.0`). Orders near
either boundary may be segmented differently under small changes to model
outputs or data. The segment counts are sensitive to these thresholds and should
not be interpreted as precise population measurements.

**6.3 Data and scoring dependence.** AO3 results depend entirely on the quality
of AO1 and AO2 predictions. If the models are applied to orders whose
characteristics differ substantially from the training population, segment
assignments may be unreliable. The held-out benchmark covers one chronological
test period; results for other periods or contexts may differ.

**6.4 Benchmark population reflects one run.** The segment distribution
(39.9% protect, 59.8% preserve, 0.15% expedite, 0.17% standard) was observed
in a single benchmark run on the test partition. In particular, the near-zero
size of `expedite_selectively` and `standard_process` reflects the specific
risk and margin profile of this test population. These proportions should not
be assumed to hold for future scored populations without re-evaluation.

**6.5 Margin construction.** The predicted margin signal (`ao2_predicted_order_profit
/ ao3_order_value`) depends on the AO2 regression model and on the accuracy of
the order value denominator. Model errors in AO2 — noting that the selected AO2 Gradient Boosting model
achieved R² = 0.012 on the inner validation set, indicating limited predictive
accuracy for individual profit values — propagate directly into margin estimates
and segment assignments. AO2 predictions should be interpreted as approximations
of expected profit, not precise forecasts.

**6.6 No outcome evaluation.** AO3 has not been evaluated against final realised
delivery or profit outcomes. The benchmark comparison is limited to a structural
analysis of predicted-score distributions within the held-out population. A
complete evaluation would require tracking whether orders in
`protect_high_value_at_risk` experienced worse realised outcomes than those in
`preserve_service`, controlling for intervention.

---

## 7. Artifacts and Reproducibility

| Artifact | Path |
| --- | --- |
| Segment policy | `data/references/ao3_risk_margin_matrix_policy.csv` |
| Segment builder script | `src/modeling/build_ao3_risk_margin_segments.py` |
| Segment validator | `tests/data_validation/validate_ao3_risk_margin_segments.py` |
| Benchmark script | `src/modeling/benchmark_ao3_risk_margin_framework.py` |
| Benchmark validator | `tests/data_validation/validate_ao3_risk_margin_benchmark.py` |
| Benchmark segment summary | `data/references/ao3_risk_margin_benchmark_segment_summary.csv` |
| Benchmark crosswalk | `data/references/ao3_risk_margin_benchmark_crosswalk.csv` |
| Benchmark insights | `data/references/ao3_risk_margin_benchmark_insights.csv` |
| Benchmark metadata | `models/ao3_integration/risk_margin_benchmark/ao3_risk_margin_benchmark_metadata.json` |
| Operational recommendation matrix | `data/references/ao3_operational_recommendation_matrix.csv` |
| Segment assignment metadata | `models/ao3_integration/risk_margin_segments/ao3_segment_assignment_metadata.json` |

All outputs are deterministic given the same AO1/AO2 test score table and
policy file. Reproducibility requires the held-out AO1/AO2 Delta table and
the approved policy CSV; no model retraining is needed.
