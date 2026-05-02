"""Smoke test for validating the team Databricks PySpark environment."""

from pyspark.sql import SparkSession


def main() -> None:
    """Create a small DataFrame and display it to confirm Spark execution."""
    spark = SparkSession.builder.getOrCreate()

    # This dummy dataset is used only to validate that the configured
    # Databricks runtime can initialize Spark and execute a basic DataFrame job.
    validation_rows = [
        (1, "ready"),
        (2, "running"),
        (3, "complete"),
    ]

    validation_df = spark.createDataFrame(validation_rows, ["id", "status"])

    validation_df.printSchema()
    validation_df.show()


if __name__ == "__main__":
    main()
