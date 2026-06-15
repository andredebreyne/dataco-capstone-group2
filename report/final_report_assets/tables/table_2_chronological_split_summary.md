# Table 2. Chronological Split Summary

Source artifacts: `docs/chronological_split_policy.md`, `data/references/ao1_chronological_partition_summary.csv`, `data/references/ao2_chronological_partition_summary.csv`.

| Objective | Partition | Row count | Share | Date range | Role in modeling | Held-out usage caveat |
| --- | --- | ---: | ---: | --- | --- | --- |
| AO1 late-delivery risk | Overall | 172,765 | 1.0000 | 2015-01-01 to 2018-01-31 | Full AO1 Gold population after population policy | Overall row set only; not a model-selection slice. |
| AO1 late-delivery risk | Development | 138,212 | 0.8000 | 2015-01-01 to 2017-04-22 | Development partition; inner validation evidence is drawn from development artifacts | Final test remains untouched for AO1 model selection and H1 validation wording. |
| AO1 late-delivery risk | Test | 34,553 | 0.2000 | 2017-04-22 to 2018-01-31 | Reserved final held-out partition | Do not claim AO1 final-test confirmation unless a separate final-test artifact supports it. |
| AO2 profitability estimation | Overall | 180,519 | 1.0000 | 2015-01-01 to 2018-01-31 | Full AO2 Gold population after population policy | Overall row set only; not a model-selection slice. |
| AO2 profitability estimation | Development | 144,415 | 0.7999988921 | 2015-01-01 to 2017-04-22 | Development partition; H2 validation evidence is drawn from development artifacts | Final test remains untouched for AO2 model selection and H2 validation wording. |
| AO2 profitability estimation | Test | 36,104 | 0.2000011079 | 2017-04-22 to 2018-01-31 | Reserved final held-out partition | Do not claim AO2 final-test confirmation unless a separate final-test artifact supports it. |

Leakage-control note: rows are ordered chronologically by `order_date_DateOrders`, `Order_Id`, and `Order_Item_Id` before partitioning. The split is designed to prevent future records from informing earlier-period model selection.
