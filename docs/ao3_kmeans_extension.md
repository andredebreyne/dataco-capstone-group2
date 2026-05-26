# AO3 K-means Extension

Issue: `#44`

## Purpose And Scope

This document finalizes the optional AO3 K-means clustering extension after the
Databricks run against the completed AO3 risk-margin segment table. The question
for this extension is narrow:

```text
Do unsupervised K-means clusters add interpretive value beyond the AO3 2x2
risk-margin matrix?
```

The answer from the generated artifacts is no. The final recommendation is
`do_not_adopt`.

The AO3 2x2 risk-margin matrix remains the primary decision-support framework.
The K-means extension is documented as an exploratory, non-adopted optional
analysis. It does not replace the AO3 matrix, AO3 segment assignment, the H3
benchmark, AO1 modeling, AO2 modeling, dashboard requirements, or final
reporting logic.

## Input And Evidence Slice

The extension used the finalized AO3 segment artifact from Issue `#42`:

```text
/Volumes/workspace/default/raw_data/gold/ao3_risk_margin_segments
```

Run metadata records:

| Item | Value |
| --- | --- |
| Input source | Issue `#42` AO3 risk-margin segment table |
| Evidence slice | `held_out_test_ao3_segment_table` |
| Row count | `34,467` |
| `final_test_used` | `true` |
| Final-test use scope | AO3 decision signals only; no target/outcome fields used |
| `final_test_targets_used` | `false` |

This matches the existing AO3 integration evidence slice. The extension clusters
on already generated AO3 prediction signals and does not use true
late-delivery outcomes, realized profit outcomes, delivery status fields, or
post-shipment variables.

## Feature Scope

The clustering feature set is deliberately small and tied to AO3 decision-time
signals:

- `ao1_predicted_late_delivery_probability`
- `ao3_predicted_margin`

The following fields are used only for profiling or traceability:

- `Order_Id`
- `Order_Item_Id`
- `ao2_predicted_order_profit`
- `ao3_priority_segment`

The extension does not cluster on identifiers, realized targets, target proxies,
`ao3_order_value`, post-shipment fields, or a high-dimensional one-hot feature
matrix. This keeps the analysis aligned with AO3 interpretation rather than
turning it into a separate segmentation model.

## K-means Method

The Databricks run used scikit-learn `KMeans`.

| Method item | Value |
| --- | --- |
| Preprocessing | Median imputation, standard scaling |
| Random seed | `42` |
| K candidates | `3`, `4`, `5` |
| Selected K | `3` |
| Selection rationale | Highest-silhouette candidate after applying the minimum cluster share screen where possible |

The selected model was `k = 3`. Although `k = 4` had a slightly higher
silhouette score, it produced a six-row cluster with a minimum cluster share of
`0.000174`, which is too small to be useful for operational interpretation.
`k = 5` also produced a six-row minimum cluster and had a lower silhouette score
than both `k = 3` and `k = 4`.

## Quality Metrics

| K | Inertia | Silhouette score | Cluster size distribution | Minimum cluster share | Selected |
| --- | ---: | ---: | --- | ---: | --- |
| `3` | `19,671.6795` | `0.6859` | `0: 21,080`; `1: 12,729`; `2: 658` | `0.0191` | Yes |
| `4` | `14,793.1997` | `0.6878` | `0: 21,075`; `1: 12,728`; `2: 658`; `3: 6` | `0.0002` | No |
| `5` | `12,255.5601` | `0.6309` | `0: 6,109`; `1: 21,060`; `2: 658`; `3: 6,634`; `4: 6` | `0.0002` | No |

For the selected `k = 3` solution, the smallest cluster contains `658` orders,
or `1.91%` of the scored AO3 population. The largest cluster contains `21,080`
orders, or `61.16%` of the population.

## Cluster Profiles

The cluster profile table is generated at:

```text
report/tables/ao3_kmeans_cluster_profiles.csv
```

### Cluster 0

Cluster `0` contains `21,080` orders, or `61.16%` of rows. It has low average
predicted late-delivery risk (`0.3213`), positive predicted margin (`0.1172`),
and expected profit around `21.86`. Its dominant AO3 segment is
`preserve_service`, which accounts for `95.77%` of the cluster.

Interpretation: this cluster mostly duplicates the AO3 low-risk / high-margin
`preserve_service` quadrant. It is large and easy to explain, but it does not
add a new operational group beyond the 2x2 matrix.

### Cluster 1

Cluster `1` contains `12,729` orders, or `36.93%` of rows. It has high average
predicted late-delivery risk (`0.8610`), positive predicted margin (`0.1181`),
and expected profit around `21.71`. Its dominant AO3 segment is
`protect_high_value_at_risk`, which accounts for `99.63%` of the cluster.

Interpretation: this cluster mostly duplicates the AO3 high-risk / high-margin
`protect_high_value_at_risk` quadrant. It is large and clear, but it reinforces
the existing AO3 segment rather than adding a distinct subgroup.

### Cluster 2

Cluster `2` contains `658` orders, or `1.91%` of rows. It has a higher mean
predicted risk (`0.5134`) but a median predicted risk just below the AO3 risk
cutoff (`0.3343`). It has lower expected profit (`5.01`) and high predicted
margin (`0.4762`). Its dominant AO3 segment is `preserve_service`, but only
`62.92%` of the cluster is in that segment; `37.08%` is
`protect_high_value_at_risk`.

Interpretation: this is a small mixed high-margin boundary group. It may reflect
orders near the AO3 risk cutoff or orders with unusually high predicted margins,
but the split between `preserve_service` and `protect_high_value_at_risk` makes
it less clean than the 2x2 matrix. It is not large or clear enough to justify a
new operational category.

## Comparison Against AO3 2x2 Risk-Margin Matrix

The generated findings directly answer the main extension question:

```text
Do K-means clusters add insight beyond the AO3 2x2 risk-margin matrix?
```

No. The selected K-means clusters mostly duplicate the existing AO3 2x2
risk-margin matrix.

Evidence:

- Weighted dominant AO3 segment share across clusters is `0.9657`.
- The metadata marks `mostly_duplicates_ao3_2x2` as `true`.
- The metadata marks `clusters_add_value_beyond_2x2` as `false`.
- No AO3 quadrant was split into multiple sizeable, useful K-means subgroups.
- The two large clusters align closely with `preserve_service` and
  `protect_high_value_at_risk`.
- The small third cluster is mixed and does not provide a stable dashboard-ready
  operational action.

The K-means result does not reveal a useful low-margin subgroup. That is
consistent with the AO3 segment summary, where low-margin segments are very
small in the held-out AO3 population: `expedite_selectively` has `52` rows and
`standard_process` has `60` rows. K-means does not improve the business story
for those small groups.

Using K-means clusters in the dashboard would likely confuse the H3 story
because the clusters would sit beside, but mostly repeat, the governed AO3
quadrants. The AO3 benchmark already provides the cleaner comparison against
risk-only and margin-only prioritization.

## Final Recommendation

Recommendation: `do_not_adopt`

Reason: selected clusters mostly duplicate existing AO3 risk-margin matrix
segments. The weighted dominant AO3 segment share is `0.966`, and the run did
not identify a meaningful subgroup beyond the core 2x2 framework.

This recommendation does not weaken AO3. It supports keeping the main AO3
framework simple, explainable, and manager-readable.

## Business Interpretation

The K-means extension confirms that the two main concentrations in the held-out
AO3 population already correspond to the 2x2 risk-margin framework:

- lower-risk, high-margin orders mostly map to `preserve_service`;
- high-risk, high-margin orders mostly map to `protect_high_value_at_risk`.

The small mixed cluster is not strong enough to create a new action rule. It may
be useful as an exploratory note for future sensitivity analysis, but it should
not be used to prioritize orders, redesign the dashboard, or modify H3
reporting.

The practical conclusion is that clustering adds little operational nuance
beyond the AO3 quadrants. The 2x2 matrix remains the clearer decision layer.

## Limitations

- This is an optional extension and is not part of the required AO3 core
  pipeline.
- K-means is sensitive to scaling, outliers, and the selected feature set.
- The feature set is intentionally limited to two AO3 decision signals.
- The extension does not use high-dimensional one-hot inputs.
- Clusters are descriptive, not causal.
- Cluster stability was not formally tested.
- Future scoring distributions could shift cluster boundaries or cluster sizes.
- The extension does not use realized late-delivery or realized profit outcomes.
- Clusters should not replace AO3 quadrants, AO3 managerial actions, or the H3
  benchmark.

## Artifact References

- `models/ao3_integration/kmeans_extension/ao3_kmeans_extension_metadata.json`
- `report/tables/ao3_kmeans_cluster_assignments_sample.csv`
- `report/tables/ao3_kmeans_cluster_profiles.csv`
- `report/tables/ao3_kmeans_quality_metrics.csv`
- `report/tables/ao3_kmeans_extension_findings.md`

## Orchestrator Status

The project orchestrator documents the K-means extension as optional. The flags
remain disabled by default:

```python
RUN_AO3_KMEANS_EXTENSION = False
RUN_AO3_KMEANS_EXTENSION_VALIDATION = False
```

The extension is not required for AO3 segment assignment, AO3 benchmarking, H3
reporting, or dashboard delivery.
