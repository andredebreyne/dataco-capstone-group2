# AO1 Class Imbalance Analysis Findings

Issue: `[W3][P1][#4] Class imbalance analysis for AO1 #21`

## Purpose

This report note summarizes the focused AO1 class imbalance analysis for
`Late_delivery_risk`. It is intended for review and later report/modeling
design. It does not train AO1 models, finalize Gold tables, apply resampling,
or set operating thresholds.

Related artifacts:

- `notebooks/eda/ao1_class_imbalance_analysis.py`
- `docs/ao1_class_imbalance_analysis.md`
- `report/tables/ao1_class_imbalance_overall.csv`
- `report/tables/ao1_class_imbalance_by_slice.csv`
- `report/tables/ao1_class_imbalance_group_review_list.csv`

## Dataset And Target Audit

The EDA used:

```text
data/silver/dataco_orders_silver.csv
```

The loaded Silver clone contains 180,519 rows and 53
columns. The target is `Late_delivery_risk` and is binary in the current Silver clone.

| Class | Count | Rate |
| --- | ---: | ---: |
| Late = 1 | 98,977 | 54.83% |
| Not late = 0 | 81,542 | 45.17% |

Missing target rows: 0. Invalid non-binary target rows:
0. The majority-to-minority ratio is
1.214:1, so the overall imbalance is
**mild** and the positive late-delivery class is the
majority class.

## Leakage-Safe Grouping Review

Grouping fields were approved only when
`data/references/leakage_conceptual_screening.csv` marked them as AO1 `allowed`,
`candidate_feature`, not `needs_group_review`, and not `conditional_review`.

Approved grouping fields:

| Grouping field | Analysis column |
| --- | --- |
| `Shipping Mode` | `Shipping_Mode` |
| `shipping_speed_tier` | `shipping_speed_tier` |
| `Market` | `Market` |
| `Order Region` | `Order_Region` |
| `Order Country` | `Order_Country` |
| `Customer Segment` | `Customer_Segment` |
| `Category Name` | `Category_Name` |
| `Department Name` | `Department_Name` |
| `order_month` | `order_month` |
| `order_day_of_week` | `order_day_of_week` |
| `order_is_weekend` | `order_is_weekend` |

Forbidden, dashboard-only, target, post-shipment, post-delivery, actual-duration,
shipping-date, profit-outcome, profit-proxy, conditional, and `needs_group_review`
fields were not used as approved grouping slices.

## Main Descriptive Findings

Overall class imbalance is mild. Accuracy alone should still not be the main
AO1 metric because missing high-risk orders has operational cost, but the full
Silver clone does not show an extreme rare-event target.

The largest supported slice differences are:

| Slice | Late-delivery rate | Difference from overall | Rows |
| --- | --- | --- | --- |
| `Shipping Mode = First Class` | 95.32% | +40.49 pp | 27,814 |
| `shipping_speed_tier = expedited` | 82.47% | +27.64 pp | 37,551 |
| `shipping_speed_tier = standard` | 76.63% | +21.80 pp | 35,216 |
| `Shipping Mode = Second Class` | 76.63% | +21.80 pp | 35,216 |
| `shipping_speed_tier = economy` | 38.07% | -16.76 pp | 107,752 |
| `Shipping Mode = Standard Class` | 38.07% | -16.76 pp | 107,752 |
| `Shipping Mode = Same Day` | 45.74% | -9.09 pp | 9,737 |
| `Order Region = Canada` | 48.80% | -6.03 pp | 959 |

Planned service fields show the strongest descriptive differences. Market-level
late-delivery rates are close to the overall rate in this Silver clone. These
patterns are descriptive and should not be interpreted causally.

## Modeling Implications

AO1 should report recall, precision, F1, confusion matrix, AUC-ROC, and PR-AUC
if imbalance remains meaningful after chronological splitting. Threshold choice
should be evaluated later using validation data, not the final test set.

No resampling is applied during EDA. If resampling such as SMOTE, undersampling, or class weighting is considered later, it must be applied only inside the training fold or training data after the chronological split, never before splitting and never on the full dataset.

## Group Validation Needed

The group review list contains 41 conditional or
`needs_group_review` variables. The team should decide whether each can be used
for AO1 modeling design, descriptive EDA only, or should remain excluded before
AO1 preprocessing is locked.
