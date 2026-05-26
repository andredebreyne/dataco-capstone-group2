# AO3 K-means Extension

Issue: `#44`

## Purpose And Scope

This document defines the optional AO3 K-means clustering extension. The
extension asks whether unsupervised clusters add interpretive value beyond the
approved AO3 2x2 risk-margin matrix.

The AO3 2x2 matrix remains the primary decision-support tool. K-means is not a
replacement for the risk-margin matrix, the H3 benchmark, AO1 late-delivery
modeling, or AO2 profitability modeling.

## Why This Is Optional

AO3 already has a governed, manager-readable 2x2 framework:

- high risk / high margin
- high risk / low margin
- low risk / high margin
- low risk / low margin

K-means is optional because it can add complexity without improving decision
clarity. The extension should be adopted only if generated clusters split an
important AO3 quadrant into useful, stable, and explainable subgroups. If the
clusters mostly duplicate the 2x2 matrix or create mixed groups, the correct
recommendation is `do_not_adopt` or `document_but_do_not_use`.

## Input AO3 Artifact

The extension uses the finalized AO3 risk-margin segment artifact from Issue
`#42`:

```text
/Volumes/workspace/default/raw_data/gold/ao3_risk_margin_segments
```

This is the same held-out AO3 scored segment table used by the AO3 benchmark.
It contains test-slice prediction signals and AO3 segment assignments, but the
extension must not use true late-delivery labels, realized profit targets, or
other target/outcome fields.

## Clustering Features

The default K-means feature set is deliberately small:

- `ao1_predicted_late_delivery_probability`
- `ao3_predicted_margin`

The script profiles clusters with `ao2_predicted_order_profit` and
`ao3_priority_segment`, but those fields are not used as clustering features.
Identifiers, post-shipment fields, realized targets, profit-ratio fields, and
`ao3_order_value` are excluded from clustering.

## Method

The extension is implemented in:

```text
src/modeling/run_ao3_kmeans_extension.py
```

Method choices:

- Algorithm: scikit-learn `KMeans`
- Preprocessing: median imputation and standard scaling
- Random seed: `42`
- K candidates: `3`, `4`, and `5`
- Selection screen: silhouette score, minimum cluster share, and interpretability
  against AO3 quadrants

The script writes the run-specific quality metrics, profiles, recommendation,
and metadata only after it can read the AO3 segment table.

## Output Artifacts

Expected generated artifacts:

```text
models/ao3_integration/kmeans_extension/ao3_kmeans_extension_metadata.json
report/tables/ao3_kmeans_cluster_assignments_sample.csv
report/tables/ao3_kmeans_cluster_profiles.csv
report/tables/ao3_kmeans_quality_metrics.csv
report/tables/ao3_kmeans_extension_findings.md
```

The findings markdown is the authoritative run-specific summary. It includes
the input used, K candidates tested, selected K, quality metrics, cluster
profiles, comparison against the AO3 risk-margin matrix, recommendation, and
limitations.

## Comparison To AO3 2x2

The extension explicitly checks whether clusters:

- mostly duplicate existing AO3 quadrants;
- split an important quadrant into useful subgroups;
- reveal a meaningful ambiguous or middle group;
- create tiny or unstable groups;
- would confuse the main dashboard interpretation.

The main question is:

```text
Do K-means clusters add insight beyond the AO3 2x2 risk-margin matrix?
```

The allowed recommendations are:

- `adopt_as_optional_context`
- `document_but_do_not_use`
- `do_not_adopt`

## Business Interpretation

Cluster labels are descriptive only. They should not be treated as operational
policy unless a later reviewed issue adopts them. The AO3 business actions still
come from the governed risk-margin framework.

## Limitations

- K-means is sensitive to scaling and outliers.
- K-means assumes compact numeric clusters and may not match business groupings.
- Cluster stability is not formally tested in this lightweight extension.
- The extension does not use realized late-delivery or realized profit outcomes.
- The extension does not estimate causal or operational impact.
- The extension remains disabled by default in the orchestrator.
