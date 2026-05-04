# Databricks Community Edition Setup Guide

## Purpose

This guide defines the standard Databricks Community Edition environment for the DataCo Capstone project. All team members should use the same compute configuration when validating PySpark transformations, data engineering logic, and modeling preparation steps.

The goal is to reduce runtime inconsistencies across team members and ensure that project outputs can be reproduced in a common Spark environment.

## Platform Requirement

Use Databricks Community Edition:

<https://community.cloud.databricks.com/>

Each team member should create or access an individual Community Edition workspace and configure a cluster using the specifications below.

## Standard Cluster Configuration

| Setting | Required value |
| --- | --- |
| Platform | Databricks Community Edition |
| Compute type | Single Node |
| Databricks Runtime | `14.3 LTS (Scala 2.12, Spark 3.5.0)` |
| Fallback Runtime | `13.3 LTS (Scala 2.12, Spark 3.4.1)` if 14.3 LTS is unavailable |
| Worker nodes | None |
| Primary use | PySpark notebooks and environment validation |

Community Edition runs on a limited single-node environment. Results and performance in Community Edition may not reflect behavior on a real distributed Spark cluster. This is expected for the project and should be treated as the official development runtime unless the team formally changes the environment standard.

## Runtime Selection Rule

Use `14.3 LTS (Scala 2.12, Spark 3.5.0)` as the preferred runtime.

If Community Edition does not show 14.3 LTS in the runtime dropdown, select `13.3 LTS (Scala 2.12, Spark 3.4.1)` and document the fallback in the related task or pull request.

When using the fallback runtime, include this exact note in the related pull request:

`Runtime: 13.3 LTS (fallback)`

Do not use non-LTS runtimes for official project validation unless the team agrees to update this guide.

## Auto-Termination Notice

Databricks Community Edition clusters automatically stop after a period of inactivity. If a notebook fails because the cluster is detached or unavailable, restart the cluster and reattach the notebook before rerunning the workflow.

Team members should avoid treating stopped clusters as errors in the project code. Cluster shutdown is an expected behavior of the free Community Edition environment.

## Manual CSV Upload to DBFS

Community Edition does not provide the same production-grade storage integrations as paid Databricks workspaces. For this project, local CSV files can be uploaded manually to DBFS for development and validation.

Recommended upload process:

1. Open the Databricks Community Edition workspace.
2. Go to the workspace home page or data upload area.
3. Select the option to upload data.
4. Choose the local CSV file from the project Bronze folder.
5. Upload the file to DBFS.
6. Record the DBFS path shown by Databricks.
7. Use that path in notebooks or PySpark scripts when reading the file.

For consistency, team members should use the following project path when possible:

`/FileStore/tables/dataco/bronze/DataCoSupplyChainDataset.csv`

Example read pattern:

```python
df = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv("/FileStore/tables/dataco/bronze/DataCoSupplyChainDataset.csv")
)
```

If Databricks creates a different path during upload, update the notebook or script to use the actual path shown in the Databricks UI and document the difference in the related task or pull request.

## Team Usage Rules

- Write and version final project code in the GitHub repository.
- Validate PySpark data engineering logic in Databricks using the standard runtime.
- Keep raw Bronze files unchanged.
- Document any runtime fallback or environment exception in the related task or pull request.
- Do not commit local Databricks exports, temporary files, or large uploaded datasets unless they are explicitly approved for version control.

## Smoke Test

Use `src/00_test_databricks_env.py` to confirm that Spark starts correctly and can create a basic DataFrame.

The smoke test does not validate project data or business logic. It only confirms that the Databricks environment can execute a minimal PySpark workload.
