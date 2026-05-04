# Data Source Verification

Task: `[W1][P0][#4] Download and verify the DataCo dataset`

## Source

- Dataset: DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS
- DOI: `10.17632/8gx2fvg2k6.5`
- Official URL: <https://data.mendeley.com/datasets/8gx2fvg2k6/5>
- Version: 5
- Published: 2019-03-12
- Contributors: Fabian Constante, Fernando Silva, Antonio Pereira
- Licence: CC BY 4.0

## Downloaded Files

The following files were downloaded from the official Mendeley Data public API and stored locally under `data/bronze/dataco/`.

| File | Purpose | Size | SHA-256 verification |
| --- | --- | ---: | --- |
| `DataCoSupplyChainDataset.csv` | Main structured supply-chain dataset | 95,910,149 bytes | Passed |
| `DescriptionDataCoSupplyChain.csv` | Companion metadata / data dictionary | 3,444 bytes | Passed |

The official Mendeley checksums are:

```text
DataCoSupplyChainDataset.csv
fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6

DescriptionDataCoSupplyChain.csv
9828e34669bd6d77e3b4463364cc44a5d52446b5e246fc258758cfe592566c4b
```

## Verification Results

The main structured dataset was successfully parsed with:

- Encoding: `latin-1`
- Delimiter: comma
- Data rows: 180,519
- Columns: 53

The first columns are:

```text
Type
Days for shipping (real)
Days for shipment (scheduled)
Benefit per order
Sales per customer
Delivery Status
Late_delivery_risk
Category Id
```

## Metadata Check

The companion metadata file contains 52 metadata rows.

Exact-name coverage against the 53 dataset columns:

- 51 columns matched exactly after trimming whitespace
- 2 dataset columns were not matched exactly in the metadata file:
  - `Order Zipcode`
  - `shipping date (DateOrders)`

This does not block ingestion, but it should be noted during Silver-layer schema documentation.

## Missing Value Snapshot

Columns with blank values in the raw dataset:

| Column | Blank rows |
| --- | ---: |
| `Product Description` | 180,519 |
| `Order Zipcode` | 155,679 |
| `Customer Lname` | 8 |
| `Customer Zipcode` | 3 |

No manual changes were made to the raw CSV files. Cleaning and transformations must be handled later through code in the Silver layer.

## Scope Note

The Mendeley dataset also includes `tokenized_access_logs.csv`, an unstructured clickstream file. The approved project proposal defines the structured `DataCoSupplyChainDataset.csv` as the primary dataset and uses the companion metadata file for variable definitions. The clickstream file is therefore out of scope for this task unless the project scope changes.
