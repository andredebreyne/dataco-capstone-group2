# Local Silver Clones

This folder is for local copies of cleaned Silver tables used by notebooks and
review scripts. Large table exports are ignored by Git.

Expected local AO1 EDA input:

```text
data/silver/dataco_orders_silver.csv
```

Create this file by running:

```text
notebooks/pipeline/run_project_workflow.py
```

The notebook exports the Silver Delta table to this local CSV path and replaces
the file if it already exists. Do not point EDA notebooks directly at
`data/raw/`; raw-to-Silver cleaning should stay a separate, reproducible step.
