# AO1 Class Imbalance Analysis

Issue: `[W3][P1][#4] Class imbalance analysis for AO1 #21`

## Purpose

This docs entry points to the reproducible AO1 class imbalance EDA artifacts.
The report-facing findings note is kept beside the generated tables so EDA
outputs stay together during review and report drafting.

## Reproducible Script

```text
notebooks/eda/ao1_class_imbalance_analysis.py
```

The script uses only the local Silver clone:

```text
data/silver/dataco_orders_silver.csv
```

If the Silver clone is missing, generate it by running:

```text
notebooks/pipeline/run_medallion_pipeline.py
```

The script intentionally does not fall back to raw data and does not duplicate
Silver cleaning logic. Set `DATACO_AO1_IMBALANCE_INPUT_PATH` only when using
another local Silver CSV clone.

## EDA Artifacts

The co-located EDA outputs are:

```text
report/tables/ao1_class_imbalance_findings.md
report/tables/ao1_class_imbalance_overall.csv
report/tables/ao1_class_imbalance_by_slice.csv
report/tables/ao1_class_imbalance_group_review_list.csv
```

Focused figures are saved under:

```text
report/figures/eda/
```

## Scope Guardrails

This issue measures overall and leakage-safe slice-level class proportions for
`Late_delivery_risk`. It does not train AO1 models, finalize Gold tables, apply
resampling, or set operating thresholds.

No resampling is applied during EDA. If resampling such as SMOTE,
undersampling, or class weighting is considered later, it must be applied only
inside the training fold or training data after the chronological split, never
before splitting and never on the full dataset.
