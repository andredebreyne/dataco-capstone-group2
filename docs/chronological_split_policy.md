# Master Chronological Split Policy

Issue: `#66`

## Purpose

This policy freezes the project-wide chronological split rules for AO1 and AO2
modeling. The goal is to preserve decision-time integrity, avoid future-data
leakage, and ensure that downstream model metrics reflect realistic future
performance rather than random-split optimism.

The policy must be approved before any AO1 or AO2 model partitions are created.

## Split Anchor

Use the Silver/Gold timestamp column below as the single chronological anchor:

```text
order_date_DateOrders
```

Rationale:

- The column represents order creation time.
- It is available at decision time.
- It exists in both AO1 and AO2 Gold analytical tables.
- It is already required for downstream lineage and split reproducibility.

Do not use `shipping_date_DateOrders`, actual shipping duration, delivery
status, order status, realized profit, or any post-order outcome field to define
model partitions.

## Master Split Rule

The project uses one deterministic 80/20 chronological split policy:

| Partition | Rule |
| --- | --- |
| Development set | Earliest 80% of rows after deterministic ordering. |
| Holdout test set | Most recent 20% of rows after deterministic ordering. |

The deterministic ordering must be:

```text
order_date_DateOrders ASC,
Order_Id ASC,
Order_Item_Id ASC
```

The tie-breakers are required because multiple order items can share the same
order timestamp. They make the split reproducible without randomization.

The chronological split uses deterministic 1-based row numbers after sorting by
`order_date_DateOrders`, `Order_Id`, and `Order_Item_Id`. For a table with `n`
rows, the development boundary is defined as `floor(n * 0.80)`. Rows with
`row_number <= floor(n * 0.80)` are assigned to the development partition, and
rows with `row_number > floor(n * 0.80)` are assigned to the final held-out test
partition.

This formula applies separately to each objective-specific Gold table after
that objective's population rules are applied. AO1 and AO2 may have different
row counts and therefore different boundary row numbers, but they must use the
same ordering columns, boundary formula, and partition labels. No random shuffle
is used.

## Development and Validation Strategy

The holdout test set must remain untouched until final evaluation for each AO.

Within the development set:

- model selection may use validation folds or a further chronological
  development/validation split;
- any internal validation must preserve time order;
- random shuffling is not allowed for official model selection unless the team
  documents a controlled sensitivity experiment outside the primary results.

All preprocessing and model fitting must happen inside development data only.
Any preprocessing, imputation, encoding, scaling, resampling, feature selection,
threshold tuning, or hyperparameter tuning performed during internal validation
must be fit only on the inner training portion of the development data.

Fit only on development/training data:

- imputers;
- categorical encoders;
- scalers;
- feature selectors;
- class balancing or resampling methods;
- target transformations;
- hyperparameter tuning;
- threshold selection.

Apply fitted objects to validation and test partitions without refitting.

## AO-Specific Use

### AO1

AO1 uses the leakage-safe late-delivery Gold table and the target:

```text
Late_delivery_risk
```

The AO1 primary table excludes shipping-canceled, canceled, and suspected-fraud
records according to the AO1 Gold policy. The chronological split must be
computed after the AO1 primary population rule is applied.

### AO2

AO2 uses the leakage-safe profitability Gold table and the target:

```text
Order_Profit_Per_Order
```

AO2 keeps the full Gold population unless a later approved policy documents a
specific exclusion. The chronological split must be computed on the final AO2
Gold table used for modeling.

## Shared Boundary Guidance

AO1 and AO2 should follow the same chronological policy and ordering rule. If
their row populations differ, each AO may have a different exact row-count
boundary, but the split computation must remain deterministic and documented.

If the team later decides that AO1 and AO2 must share a single calendar cutoff
date rather than separate 80/20 row-count boundaries, that change must be
recorded as an explicit policy exception before modeling results are reported.

## Repeated Entities and Temporal Patterns

Repeated customers, products, regions, and seasonal patterns are expected in
the DataCo dataset. They are not removed before splitting.

Interpretation rules:

- The split evaluates the ability to generalize from earlier orders to later
  orders.
- Repeated customers or products may appear in both development and test sets
  if they occur across time.
- This is acceptable for the primary project design because the business use
  case is future-order prediction, not cold-start entity prediction.
- Historical aggregate features must not be computed across the full dataset.
  If used later, they must be time-aware and fit only on development/training
  data.

## Reproducibility Requirements

Every partitioning script must persist or document:

- source Gold table path;
- split anchor column;
- ordering columns;
- split ratio;
- boundary row formula;
- partition labels;
- development row count;
- test row count;
- earliest and latest timestamp per partition;
- execution timestamp;
- policy reference document.

Partition labels should use:

```text
development
test
```

Do not use ambiguous names such as `train` for the full 80% development set if
additional validation splits will be created later.

## Frozen Decisions

The frozen policy values are versioned in:

```text
data/references/chronological_split_policy.csv
```

Validation script:

```text
tests/data_validation/validate_chronological_split_policy.py
```

The policy should change only if the team records and justifies the exception
before model training or final reporting.
