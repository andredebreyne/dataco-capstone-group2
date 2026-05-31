# DataCo Bronze Files

This folder contains the tracked Bronze metadata file and is the canonical
local staging area for the uncommitted DataCo Smart Supply Chain CSV before it
is uploaded to Databricks.

The main raw dataset is intentionally not committed because it is a large
source file. Download it from the official Mendeley Data record and verify it
against the checksum below.

## Official Source

- Dataset: DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS
- DOI: `10.17632/8gx2fvg2k6.5`
- Version: 5
- Publisher: Mendeley Data
- Licence: CC BY 4.0

## Files Used

| File | Tracked in Git | Size | SHA-256 |
| --- | --- | ---: | --- |
| `DataCoSupplyChainDataset.csv` | No | 95,910,149 bytes | `fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6` |
| `DescriptionDataCoSupplyChain.csv` | Yes | 3,444 bytes | `9828e34669bd6d77e3b4463364cc44a5d52446b5e246fc258758cfe592566c4b` | *
*This file is the official variable-description file from the source dataset and is committed because it is small and required for schema interpretation.

The `tokenized_access_logs.csv` clickstream file is not part of the current predictive modeling scope and is not downloaded for the core Bronze verification task.

## File Placement

Use one local staging path for the uncommitted raw dataset:

`data/bronze/dataco/DataCoSupplyChainDataset.csv`

Then upload that file to the standard Databricks Volume path used by the
pipeline:

`/Volumes/workspace/default/raw_data/DataCoSupplyChainDataset.csv`

The pipeline reads from the Databricks Volume path by default through
`DATACO_RAW_INPUT_PATH`. Do not point `DATACO_RAW_INPUT_PATH` at a local
repository path; the ingestion job expects a `/Volumes/...` path. Large raw CSV
files remain ignored by Git.
