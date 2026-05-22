# AO1 Preprocessing Pipeline

Issue: `#26`

## Purpose and Scope

The AO1 preprocessing pipeline converts the already leakage-safe AO1
chronological Gold partitions into algorithm-ready matrices for later
late-delivery risk modeling.

This issue does not rebuild Silver, engineer features, change AO1 Gold feature
selection, change chronological split logic, train Logistic Regression, train
XGBoost, tune thresholds, or report model metrics.

## Source Table

The preprocessing job consumes the AO1 chronological partition table created in
issue `#25`:

```text
/Volumes/workspace/default/raw_data/gold/ao1_late_delivery_chronological_partitions
```

Override path:

```text
DATACO_AO1_CHRONOLOGICAL_PARTITIONS_OUTPUT_PATH
```

The source table must already contain:

- `Order_Id`
- `Order_Item_Id`
- `order_date_DateOrders`
- `Late_delivery_risk`
- `chronological_row_number`
- `split_partition`

The partition artifact currently uses only:

- `development`
- `test`

No materialized validation partition exists yet.

## Target and Partition Use

Target column:

```text
Late_delivery_risk
```

Because only `development` and `test` labels exist, the standalone
preprocessing artifact fits learned objects on `development` only. The final
`test` partition may be transformed only as a compatibility check using objects
already fit on `development`.

Future AO1 model selection must create validation folds or a further
chronological validation split inside the development window. In that workflow,
imputers, encoders, scalers, SMOTE, feature selection, model fitting, and
threshold tuning must be fit only inside each inner training fold.

## Excluded Columns

These columns are excluded from predictors:

- `Order_Id`
- `Order_Item_Id`
- `order_date_DateOrders`
- `chronological_row_number`
- `split_partition`
- `_gold_ao1_processed_timestamp`
- `Late_delivery_risk`

Forbidden leakage and outcome fields from the AO1 Gold contract remain excluded,
including actual shipping duration, delivery status, shipping date, order
status, profit, sales, realized margin, granular identifiers, and personal
fields.

## Predictor Columns

The preprocessing feature list is taken from the AO1 Gold table contract in
`src/data_engineering/build_gold_ao1_table.py`.

### Numeric Continuous

- `order_year`
- `order_quarter`
- `order_month`
- `order_week_of_year`
- `order_day_of_month`
- `order_day_of_week`
- `order_hour`
- `scheduled_shipping_days`

Rule:

- impute missing values with the training-only median;
- scale with `StandardScaler` fit on the fitting partition only.

### Binary Flags

- `order_is_weekend`
- `is_same_day_or_next_day_shipping`
- `is_standard_shipping`
- `customer_zipcode_available`
- `order_zipcode_available`
- `customer_order_country_match`
- `customer_order_state_match`
- `geo_coordinates_available`

Rule:

- impute missing values with the training-only most frequent value;
- keep as numeric flags after imputation;
- do not scale in the first-pass baseline preprocessing.

### Categorical

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

Rule:

- impute missing values with constant `unknown`;
- encode with `OneHotEncoder(handle_unknown="ignore")`;
- fit categories on the fitting partition only.

Target encoding is not used.

## SMOTE and Resampling

The AO1 class imbalance analysis reports mild imbalance with a majority to
minority ratio of about `1.214:1`. SMOTE is therefore configured for future
training experiments but deferred in this preprocessing issue.

SMOTE rules:

- never apply SMOTE before chronological splitting;
- never apply SMOTE to validation or test data;
- never apply SMOTE to the full dataset;
- apply SMOTE only to training data or inside future training folds;
- do not save a full resampled dataset as a source of truth.

Default configuration if enabled later:

- `sampling_strategy="auto"`
- `random_state=620`
- `k_neighbors=5`

## Artifacts

Implementation script:

```text
src/modeling/build_ao1_preprocessing_pipeline.py
```

Validation script:

```text
tests/data_validation/validate_ao1_preprocessing_pipeline.py
```

Lightweight metadata:

```text
models/ao1_late_delivery/preprocessing/ao1_preprocessing_metadata.json
```

Optional fitted sklearn artifact:

```text
/Volumes/workspace/default/raw_data/models/ao1_late_delivery/preprocessing/ao1_preprocessor.joblib
```

The fitted binary artifact is not saved by default. To save it in Databricks,
set:

```text
DATACO_AO1_SAVE_FITTED_PREPROCESSOR=true
DATACO_AO1_PREPROCESSOR_ARTIFACT_PATH=/Volumes/workspace/default/raw_data/models/ao1_late_delivery/preprocessing/ao1_preprocessor.joblib
```

## Validation

The validation script checks:

- metadata exists and includes required keys;
- the target is not in the feature list;
- identifiers, partition columns, and metadata columns are not predictors;
- forbidden leakage fields are not predictors;
- numeric, binary, and categorical groups do not overlap;
- declared feature columns exist in the AO1 partition table when Delta is
  available;
- preprocessing fit source is `development` or `train`, never `test`;
- transformed row counts match partition row counts before any SMOTE step when
  runtime shape metadata is available;
- SMOTE is marked training-only and is not applied to validation or test;
- no resampled validation or test artifacts are created.

## Assumptions and Limitations

- AO1 Gold is already the leakage-safe model-ready analytical table.
- The AO1 partition artifact currently has `development` and `test` labels only.
- The final test partition remains untouched for final AO1 evaluation.
- Test transformation in this issue is only a compatibility check, not model
  selection or evaluation.
- Future AO1 training must fit preprocessing inside each training fold.
- This issue does not produce model results, predictions, thresholds, feature
  importance, SHAP values, or dashboard outputs.
