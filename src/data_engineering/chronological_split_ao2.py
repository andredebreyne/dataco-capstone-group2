from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import col, row_number


def get_spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def load_ao2_gold(spark: SparkSession, path: str) -> DataFrame:
    return spark.read.format("delta").load(path)


def build_chronological_split(df: DataFrame) -> tuple[DataFrame, DataFrame]:
    """
    Creates 80/20 chronological split for AO2.
    """

    window = Window.orderBy(
        col("order_date_DateOrders").asc(),
        col("Order_Id").asc(),
        col("Order_Item_Id").asc()
    )

    df = df.withColumn("row_idx", row_number().over(window))

    total_rows = df.count()
    cutoff = int(total_rows * 0.8)

    train_df = df.filter(col("row_idx") <= cutoff)
    test_df = df.filter(col("row_idx") > cutoff)

    return train_df, test_df


def run_split(spark: SparkSession, input_path: str):
    df = load_ao2_gold(spark, input_path)

    train_df, test_df = build_chronological_split(df)

    print("Train rows:", train_df.count())
    print("Test rows:", test_df.count())

    return train_df, test_df