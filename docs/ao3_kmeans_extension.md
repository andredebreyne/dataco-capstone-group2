# AO3 K-means Extension

Issue: `#44`

## Purpose And Scope

This page documents the optional AO3 K-means clustering extension. The extension
asks whether unsupervised clusters add interpretive value beyond the approved AO3
2x2 risk-margin matrix. It is not part of the core AO3 decision framework and it
must not replace the H3 benchmark against risk-only and margin-only views.

## Optional Status

The primary AO3 tool remains the governed 2x2 risk-margin matrix:

- high risk / high margin
- high risk / low margin
- low risk / high margin
- low risk / low margin

K-means is retained only as optional context if the generated findings show a
clear interpretive benefit. The current generated recommendation is
`do_not_adopt`.

## Input AO3 Artifact

- Input artifact: `/Volumes/workspace/default/raw_data/gold/ao3_risk_margin_segments`
- Evidence slice: held-out AO3 scored segment table
- Row count used by the latest run: `34467`
- Final-test scope: AO3 decision signals only; target/outcome fields are not used

## Clustering Features

The extension clusters only on the small AO3 decision-signal feature set:

- `ao1_predicted_late_delivery_probability`
- `ao3_predicted_margin`

`ao2_predicted_order_profit` is used for cluster profiling only. Identifiers,
true late-delivery labels, realized profit fields, post-shipment fields, and
AO2 target-reconstruction risk fields are excluded from clustering.

## Method

- Algorithm: scikit-learn `KMeans`
- Preprocessing: median imputation and standard scaling
- Random seed: `42`
- K candidates: `3, 4, 5`
- Selected K for profiling: `3`

## Outputs

- Quality metrics: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao3_kmeans_quality_metrics.csv`
- Cluster profiles: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao3_kmeans_cluster_profiles.csv`
- Assignment sample: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao3_kmeans_cluster_assignments_sample.csv`
- Findings note: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/report/tables/ao3_kmeans_extension_findings.md`
- Metadata: `/Workspace/Users/bruno.de8627@myunfc.ca/dataco-capstone-group2/models/ao3_integration/kmeans_extension/ao3_kmeans_extension_metadata.json`

## Business Interpretation

The extension compares each cluster against the existing AO3 risk-margin
segments. It checks whether clusters mostly duplicate the 2x2 matrix, split an
important quadrant into useful subgroups, or create mixed groups that would
confuse dashboard interpretation.

## Final Recommendation

Recommendation: `do_not_adopt`

Reason: Selected clusters mostly duplicate existing AO3 risk-margin matrix segments (weighted dominant segment share 0.966).

The AO3 2x2 risk-margin matrix remains the decision tool for the dashboard and
report unless a reviewed future issue explicitly adopts the clustering view.

## Limitations

- K-means can be sensitive to scaling and outliers.
- Cluster stability is not formally tested.
- The extension does not use realized late-delivery or profit outcomes.
- The extension does not estimate operational impact.
- The findings should be treated as optional interpretation, not policy.
