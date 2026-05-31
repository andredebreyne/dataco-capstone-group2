# AO1 Chronological Partitions

Issue: `#25`

## Purpose

AO1 chronological partitions provide the official development and final held-out
test windows for late-delivery risk modeling. The partitions are created after
the leakage-safe AO1 Gold analytical table is built and before any model
training, preprocessing, encoding, scaling, resampling, feature selection,
threshold tuning, or hyperparameter tuning.

The final test partition must remain untouched until final AO1 model evaluation.

## Source and Output

| Artifact | Path |
| --- | --- |
| Source AO1 Gold Delta table | `/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_analytical_table` |
| Partitioned AO1 Delta table | `/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_chronological_partitions` |
| Partition creation script | `src/modeling/create_ao1_chronological_partitions.py` |
| Partition validation script | `tests/data_validation/validate_ao1_chronological_partitions.py` |
| Generated summary CSV | `data/references/ao1_chronological_partition_summary.csv` |

The source and output Delta paths can be overridden with:

```text
DATACO_GOLD_AO1_OUTPUT_PATH
DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH
DATACO_AO1_CHRONOLOGICAL_PARTITION_SUMMARY_PATH
```

## Frozen Split Policy

The implementation follows the frozen master policy in
`docs/chronological_split_policy.md` and
`data/references/chronological_split_policy.csv`.

Exact split rule:

```text
split_anchor = order_date_DateOrders
ordering = order_date_DateOrders ASC, Order_Id ASC, Order_Item_Id ASC
development_boundary = floor(total_rows * 0.80)
development = chronological_row_number <= development_boundary
test = chronological_row_number > development_boundary
```

The script validates the frozen policy CSV before writing outputs. If the
policy is missing or contradicts these values, the job fails instead of
creating an improvised split.

## Output Columns

The partitioned Delta table preserves all AO1 Gold columns and adds only:

| Column | Meaning |
| --- | --- |
| `chronological_row_number` | Deterministic 1-based row number after frozen chronological ordering. |
| `split_partition` | Frozen partition label: `development` or `test`. |

No random split columns, target-stratification columns, model scores, fitted
preprocessing outputs, or validation subpartition labels are created in this
issue.

## Current Size Contract

The AO1 Gold table contract currently expects `172,765` rows. Under the frozen
80/20 row-number rule, the expected partition sizes are:

| Partition | Row rule | Expected rows from current AO1 Gold contract |
| --- | --- | ---: |
| `development` | `chronological_row_number <= floor(172765 * 0.80)` | `138,212` |
| `test` | `chronological_row_number > floor(172765 * 0.80)` | `34,553` |

The partition script recomputes these values from the actual AO1 Gold Delta
table at runtime and records the final counts in the generated summary CSV.

## Runtime Summary

After the partition creation script runs in Databricks, it writes
`data/references/ao1_chronological_partition_summary.csv` with:

| Field group | Included values |
| --- | --- |
| Size | row count and percentage of total by partition |
| Date range | minimum and maximum `order_date_DateOrders` by partition |
| Target distribution | late count, non-late count, late-delivery rate, and target missing count |
| Row-number range | minimum and maximum `chronological_row_number` by partition |
| Policy metadata | total AO1 rows, boundary row number, split formula, ordering columns, policy reference, and execution timestamp |

This local development environment does not contain the Databricks AO1 Gold
Delta table, so date ranges and target distributions are not hard-coded here.
They must come from the generated runtime summary to avoid fabricated results.

## Validation Checks

`tests/data_validation/validate_ao1_chronological_partitions.py` validates:

- partitioned Delta output is readable;
- required partition columns exist;
- AO1 Gold columns are preserved and only partition metadata columns are added;
- partition row count equals AO1 Gold row count;
- keys remain unique;
- no AO1 Gold keys are lost or duplicated;
- partition labels are exactly `development` and `test`;
- development rows equal `floor(total_rows * 0.80)`;
- test rows equal `total_rows - floor(total_rows * 0.80)`;
- development row numbers are at or before the boundary;
- test row numbers are after the boundary;
- row numbers are complete, unique, 1-based, and gap-free;
- chronological ordering is monotonic by row number;
- final test dates are later than or equal to the development boundary date;
- target values are complete and binary in each partition;
- target distribution is printed for validation logs;
- no random, shuffled, stratified, or target-derived split helper columns are present.

## Validation Subpartition Decision

No materialized validation subpartition is created in this issue.

The frozen master policy allows future model selection to use validation folds
or a further chronological split within the development window, but it does not
define a specific materialized validation split. Therefore, this issue saves
only `development` and `test`. Any future validation partition must be created
inside the development set only and must preserve chronological order.

## Assumptions and Limitations

- AO1 Gold has already applied the approved primary AO1 population rule.
- `Late_delivery_risk` is used only for validation and reporting, never for
  assigning partitions.
- `shipping_date_DateOrders`, `Delivery_Status`, actual shipping duration, and
  other post-shipment or outcome fields are not used for splitting.
- The split does not apply SMOTE, undersampling, oversampling, class weighting,
  imputation, scaling, encoding, threshold tuning, hyperparameter tuning, or
  feature selection.
- Any future resampling must be training-fold-only and must never be applied
  before chronological splitting.
- The final test partition is reserved for final AO1 evaluation and should not
  be used for preprocessing fit, model selection, threshold selection, or
  exploratory tuning.

## Run Order

In Databricks, run:

```text
src/modeling/create_ao1_chronological_partitions.py
tests/data_validation/validate_ao1_chronological_partitions.py
```

The project orchestrator also exposes disabled-by-default flags:

```python
RUN_AO1_PARTITIONS = False
RUN_AO1_PARTITION_VALIDATION = True
```

Set `RUN_AO1_PARTITIONS = True` only when the AO1 Gold table already exists
and reviewers are ready to materialize the official AO1 development/test
partitions. The validation switch is enabled by default, but the orchestrator
gates it behind `RUN_AO1_PARTITIONS` so validation runs only when partitioning
is run.

