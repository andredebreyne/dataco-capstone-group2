# Local Silver Clones

This folder is for local copies of cleaned Silver tables used by notebooks and
review scripts. Large table exports are ignored by Git.

Expected local AO1 EDA input:

```text
data/silver/dataco_orders_silver.csv
```

Create this file by exporting the Databricks Silver table or by regenerating the
Silver output from the documented pipeline. Do not point EDA notebooks directly
at `data/raw/`; raw-to-Silver cleaning should stay a separate, reproducible step.
