# AO2 Preprocessing Pipeline

Issue: `#34`

## Purpose and Scope

The AO2 preprocessing pipeline converts the already leakage-safe AO2
chronological Gold partitions into algorithm-ready feature matrices for future
profitability regression models.

This issue does not rebuild Silver, rerun feature engineering, change AO2 Gold
selection, change the chronological split, train AO2 models, create AO2 model
metrics, derive predicted margins, or assign AO3 risk-margin groups.

## Source Artifact

| Artifact | Path |
| --- | --- |
| Source AO2 partition Delta table | `/Volumes/workspace/default/raw_data/gold/ao2_profitability_chronological_partitions` |
| Preprocessing script | `src/modeling/build_ao2_preprocessing_pipeline.py` |
| Validation script | `tests/data_validation/validate_ao2_preprocessing_pipeline.py` |
| Metadata artifact | `models/ao2_profitability/preprocessing/ao2_preprocessing_metadata.json` |

The source path can be overridden with:

```text
DATACO_AO2_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH
```

## Partition Usage

The current AO2 partition artifact from issue `#33` contains:

- `development`
- `test`

Because no materialized validation partition exists, the standalone
preprocessing artifact fits only on `development`. The `test` partition may be
transformed only as a compatibility check using objects fit on `development`.
It must not be used for fitting, model selection, residual review, tuning, or
final model choice.

Future AO2 model selection must create time-preserving validation folds or a
further chronological validation split inside `development`. In that setting,
preprocessing must be refit inside each inner training fold.

If a future artifact contains explicit `train`, `validation`, and `test`
labels, preprocessing must fit only on `train` and transform validation/test
without refitting.

## Target

The AO2 target is:

```text
Order_Profit_Per_Order
```

It is used only as the regression target and must never appear in the feature
matrix.

## Approved Predictor Policy

AO2 Gold is the leakage-safe analytical modeling table. The preprocessing
pipeline uses the approved first-pass AO2 predictor columns from
`src/data_engineering/build_gold_ao2_table.py`.

### Numeric Continuous Predictors

- `order_year`
- `order_quarter`
- `order_month`
- `order_week_of_year`
- `order_day_of_month`
- `order_day_of_week`
- `order_hour`
- `scheduled_shipping_days`
- `item_unit_price`
- `item_discount_rate`
- `order_item_quantity`

### Binary Flag Predictors

- `order_is_weekend`
- `is_same_day_or_next_day_shipping`
- `is_standard_shipping`
- `customer_zipcode_available`
- `order_zipcode_available`
- `customer_order_country_match`
- `customer_order_state_match`
- `geo_coordinates_available`

### Categorical Predictors

- `Type`
- `order_season`
- `shipping_speed_tier`
- `shipping_mode_normalized`
- `product_category_key`
- `product_department_key`
- `customer_segment_normalized`
- `customer_country_normalized`
- `customer_state_normalized`
- `market_normalized`
- `order_country_normalized`
- `order_region_normalized`
- `order_state_normalized`

## Excluded Columns

Identifier, lineage, date, and partition columns are not predictors:

- `Order_Id`
- `Order_Item_Id`
- `order_date_DateOrders`
- `chronological_row_number`
- `split_partition`
- `_gold_ao2_processed_timestamp`

Forbidden target-reconstruction, near-formula, and proxy fields are excluded
from the main AO2 predictor path if present:

- `Order_Profit_Per_Order`
- `Benefit_per_order`
- `Order_Item_Profit_Ratio`
- `Order_Item_Total`
- `ao3_order_value`
- `Sales`
- `Sales_per_customer`
- `Order_Item_Discount`
- `Product_Price`
- realized margin, profit-ratio, and direct profit outcome fields
- delivery outcome and post-shipment fields

`ao3_order_value` is retained only as an AO3 support denominator. It is not an
AO2 predictor.

## Preprocessing Rules

| Group | Missing-value handling | Scaling or encoding |
| --- | --- | --- |
| Numeric continuous | `SimpleImputer(strategy="median")` fit on fitting partition only | `StandardScaler()` fit on fitting partition only |
| Binary flags | `SimpleImputer(strategy="most_frequent")` fit on fitting partition only | passthrough after imputation |
| Categorical | `SimpleImputer(strategy="constant", fill_value="unknown")` fit on fitting partition only | `OneHotEncoder(handle_unknown="ignore")` fit on fitting partition only |

The pipeline does not use target encoding, frequency encoding, target-based
feature selection, or any transformation fit on final test rows.

## Validation Checks

`tests/data_validation/validate_ao2_preprocessing_pipeline.py` validates:

- metadata file presence and required keys;
- target exclusion from feature columns;
- identifier, partition, date, and lineage exclusion;
- forbidden AO2 target-reconstruction exclusions;
- `ao3_order_value` exclusion as an AO2 predictor;
- non-overlapping and complete column groups;
- allowed fit source of `development` or `train` only;
- no validation or test rows used for fitting;
- declared feature columns, target numeric type, unique keys, and transformed
  row counts when the AO2 partition Delta table is available.

Static metadata checks can run locally. Delta-dependent checks require
Databricks.

## Interpretation Implications

- One-hot encoding changes coefficient interpretation for future linear and
  ridge regression baselines.
- Standard scaling changes raw coefficient magnitude for numeric predictors.
- Imputation can affect marginal interpretation if missingness is informative.
- Excluding `ao3_order_value` preserves the AO2 target-policy boundary.
- `ao3_order_value` may be used later to construct predicted AO3 margin from
  AO2 predictions, not as an AO2 model input.

## Assumptions and Limitations

- AO2 Gold is already the leakage-safe analytical table.
- The current AO2 partition labels are `development` and `test`.
- No random validation split is created in this issue.
- No large fitted binary object is committed. A fitted preprocessor can be
  saved to a Databricks Volume only when `DATACO_AO2_SAVE_FITTED_PREPROCESSOR`
  is explicitly set to `true`.
- The committed metadata is lightweight specification metadata. Running the
  build script in Databricks overwrites it with runtime fit status and
  transformed shape metadata.

## Run Order

In Databricks, run:

```text
src/modeling/build_ao2_preprocessing_pipeline.py
tests/data_validation/validate_ao2_preprocessing_pipeline.py
```

The project orchestrator exposes disabled-by-default flags:

```python
RUN_AO2_PREPROCESSING = False
RUN_AO2_PREPROCESSING_VALIDATION = False
```
