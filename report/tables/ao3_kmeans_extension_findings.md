# AO3 K-means Extension Findings

Issue: `#44`

## Input Used

- AO3 input artifact: `/Volumes/workspace/default/raw_data/gold/ao3_risk_margin_segments`
- Evidence slice: held-out AO3 scored segment table with `split_partition = test` and `ao2_split_partition = test`
- Row count: `34467`
- Final test used: yes, for AO3 decision signals only, matching the existing AO3 segment artifact
- Final target/outcome fields used: no

## K-means Setup

- Clustering method: K-means with median imputation and standard scaling
- Random seed: `42`
- Clustering features: `ao1_predicted_late_delivery_probability, ao3_predicted_margin`
- K candidates tested: `3, 4, 5`
- Selected K for profiling: `3`
- Selected K silhouette score: `0.6859`

## Quality Metrics

| k | inertia | silhouette_score | min_cluster_size | min_cluster_share | max_cluster_share | cluster_size_summary | meets_min_share_rule | selected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 19671.6795 | 0.6859 | 658 | 0.0191 | 0.6116 | {"0": 21080, "1": 12729, "2": 658} | True | True |
| 4 | 14793.1997 | 0.6878 | 6 | 0.0002 | 0.6115 | {"0": 21075, "1": 12728, "2": 658, "3": 6} | False | False |
| 5 | 12255.5601 | 0.6309 | 6 | 0.0002 | 0.6110 | {"0": 6109, "1": 21060, "2": 658, "3": 6634, "4": 6} | False | False |

## Cluster Profile Summary

| cluster_id | row_count | row_share | mean_predicted_late_delivery_risk | median_predicted_late_delivery_risk | mean_expected_profit | median_expected_profit | mean_predicted_margin | median_predicted_margin | dominant_ao3_priority_segment | dominant_ao3_segment_share | ao3_quadrant_distribution | suggested_interpretation_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 21080 | 0.6116 | 0.3213 | 0.3319 | 21.8558 | 19.4680 | 0.1172 | 0.1186 | preserve_service | 0.9577 | {"expedite_selectively": 0.000237, "preserve_service": 0.957732, "protect_high_value_at_risk": 0.039184, "standard_process": 0.002846} | low risk / high margin |
| 1 | 12729 | 0.3693 | 0.8610 | 0.7674 | 21.7065 | 19.2266 | 0.1181 | 0.1188 | protect_high_value_at_risk | 0.9963 | {"expedite_selectively": 0.003692, "protect_high_value_at_risk": 0.996308} | high risk / high margin |
| 2 | 658 | 0.0191 | 0.5134 | 0.3343 | 5.0098 | 5.0526 | 0.4762 | 0.4885 | preserve_service | 0.6292 | {"preserve_service": 0.629179, "protect_high_value_at_risk": 0.370821} | high risk / high margin |

## Comparison Against AO3 2x2 Risk-Margin Matrix

- Weighted dominant AO3 segment share across clusters: `0.9657`
- Mostly duplicates existing AO3 2x2 matrix: `True`
- Hard to explain against AO3 matrix: `False`
- Meaningful AO3 quadrant splits: No AO3 quadrant had multiple sizeable cluster subgroups.
- Do clusters add value beyond 2x2: `False`

The AO3 2x2 risk-margin matrix remains the primary decision-support framework.
K-means is only considered as optional context if it clearly splits a major AO3
quadrant into interpretable subgroups without creating unstable or tiny groups.

## Recommendation

Recommendation: `do_not_adopt`

Reason: Selected clusters mostly duplicate existing AO3 risk-margin matrix segments (weighted dominant segment share 0.966).

## Limitations

- K-means is sensitive to scaling and assumes roughly spherical clusters.
- The extension uses only AO3 decision-time prediction signals, not realized outcomes.
- Cluster stability is not formally tested in this lightweight extension.
- Final-test target labels are not used, so this is not an outcome-performance evaluation.
- Clusters should not replace the governed AO3 risk-margin matrix or H3 benchmark.
