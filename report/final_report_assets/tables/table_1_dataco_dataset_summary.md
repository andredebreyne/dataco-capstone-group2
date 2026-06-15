# Table 1. DataCo Dataset Summary

Source artifacts: `docs/data_source_verification.md`, `docs/medallion_structure.md`, `report/final_capstone_report_final_markdown.md`.

| Field | Value | Final report note |
| --- | --- | --- |
| Dataset name | DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS | Primary structured dataset for the capstone. |
| Source | Mendeley Data, Version 5 | Official URL recorded as `https://data.mendeley.com/datasets/8gx2fvg2k6/5`. |
| DOI | `10.17632/8gx2fvg2k6.5` | Use the DOI in final References. |
| Published date | 2019-03-12 | Dataset source date. |
| Contributors | Fabian Constante; Fernando Silva; Antonio Pereira | Dataset contributor names from source verification. |
| License | CC BY 4.0 | Public academic use with attribution. |
| Main structured file | `DataCoSupplyChainDataset.csv` | Structured transactional supply-chain dataset. |
| Companion metadata file | `DescriptionDataCoSupplyChain.csv` | Used for source metadata and data dictionary review. |
| Data rows | 180,519 | Verified parsed row count. |
| Dataset columns | 53 | Verified parsed column count. |
| Companion metadata rows | 52 | Metadata row count from companion file. |
| Data domain | Order, customer, product, shipping, logistics, geography, and financial fields | Supports AO1, AO2, and AO3. |
| Project use | Pre-shipment late-delivery risk prediction, profitability estimation, and AO3 risk-margin prioritization | Structured clickstream file is out of scope unless project scope changes. |
| Governance notes | Raw source files are preserved without manual changes; cleaning and modeling controls are handled through Silver, Gold, and documented policies | Supports reproducible Bronze-Silver-Gold workflow. |
| Main dataset SHA-256 verification | Passed; official checksum `fa6d022ed437155e1a2f0378710602848703c8a7f203f7ff5d77805bf8480aa6` | Checksum/source verification evidence. |
| Metadata file SHA-256 verification | Passed; official checksum `9828e34669bd6d77e3b4463364cc44a5d52446b5e246fc258758cfe592566c4b` | Checksum/source verification evidence. |
| Known limitations | Public academic dataset; final report treats the project as an academic decision-support prototype, not a validated production operating system | Limits generalization to live enterprise operations. |
