import pyspark
from pyspark.sql import SparkSession, Window
import os
from pyspark.sql.functions import col, current_date, datediff, sum,when,count,min,max,avg
import sys

# 1. TELL PYSPARK EXACTLY WHERE TO FIND YOUR CLEAN JAVA 11 INSTALLATION


# Update this path to match your actual installation folder
os.environ["JAVA_HOME"] = r"C:\\java\\jdk-17"

# Add the bin folder to the system PATH environment variable
os.environ["PATH"] = os.environ["JAVA_HOME"] + r"\bin;" + os.environ["PATH"]
 # <-- Change this to match your actual install folder path

# 2. FORCE PYSPARK TO USE THE VIRTUAL ENVIRONMENT'S INTERPRETER
# This matches the 'recomm_env' execution framework you are using
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

# 3. PERMIT INTERNAL LOCALPORT SWAPPING (Bypasses minor firewall blocks)
os.environ["PYSPARK_ALLOW_INSECURE_GATEWAY"] = "1"



# 1. Define the exact path to your dataset on the D drive
DATA_DIR = r"D:\\Recommendation_system\\data"

def init_spark():
    print("🚀 Initializing PySpark Session...")
    # Configured to use all available local CPU cores and manage memory efficiently
    spark = SparkSession.builder \
        .appName("HM_Context_Aware_Recommender") \
        .config("spark.driver.memory", "8g") \
        .config("spark.sql.shuffle.partitions", "100") \
        .master("local[*]") \
        .getOrCreate()
    return spark

def load_data_with_pyspark(spark):
    print("📊 Loading CSV files via PySpark...")
    
    # 2. Read datasets with schema inference enabled
    # Header=True ensures columns are named correctly; inferSchema parses types
    articles_df = spark.read.csv("D:\\Recommendation_system\\Context-Aware-Neural-Recommendation\\data\\articles.csv", header=True, inferSchema=True)
    customers_df = spark.read.csv("D:\\Recommendation_system\\Context-Aware-Neural-Recommendation\\data\\customers.csv", header=True, inferSchema=True)
    transactions_df = spark.read.csv("D:\Recommendation_system\\Context-Aware-Neural-Recommendation\\data\\transactions_train.csv", header=True, inferSchema=True)
    transactions_df.cache()


    # 3. Print Row Counts (PySpark computes this lazily/efficiently)
    print("\n--- Spark DataFrame Statistics ---")
    print(f"Articles total rows:     {articles_df.count():,}")
    print(f"Customers total rows:    {customers_df.count():,}")
    print(f"Transactions total rows: {transactions_df.count():,}")
    
    # 4. Show Schemas to verify context data types
    # print("\n--- Transactions Data Schema ---")
    # transactions_df.printSchema()
    # articles_df.printSchema() 
    # customers_df.printSchema()
    #    # 5. Display a sample of the transactions dataframe
    # # print("\n--- Previewing first 5 rows of all csv files ---")
    # transactions_df.show(5)
    # customers_df.show(5)
    # articles_df.show(5)
    
    return articles_df, customers_df, transactions_df

if __name__ == "__main__":
    # Start the PySpark session
    spark_session = init_spark()
    
    # Execute the load function
    articles, customers, transactions = load_data_with_pyspark(spark_session)


# #Filling null values in detail description column in article dataframe with "No Description Available"
articles = articles.fillna({"detail_desc": "No Description Available"})
#Dropping duplicates in the articles dataframe
cleaned_df_articles = articles.distinct()

articles_model=cleaned_df_articles.drop('product_code','prod_name','product_type_no','graphical_appearance_no','colour_group_code','perceived_colour_value_id','perceived_colour_master_id','perceived_colour_value_name','perceived_colour_master_name','department_no','index_code','index_group_no','section_no','garment_group_no','detail_desc')
print("✅ Data Cleaning Completed for Articles DataFrame")


categorical_cols = [
    "product_type_name",
    "product_group_name",
    "graphical_appearance_name",
    "colour_group_name",
    "department_name",
    "index_name",
    "index_group_name",
    "section_name",
    "garment_group_name"
]
from pyspark.ml.feature import StringIndexer   #Each product gets just one index

for c in categorical_cols:
    indexer = StringIndexer(
        inputCol=c,
        outputCol=c + "_index",
        handleInvalid="keep"
    )

    articles_model = indexer.fit(articles_model).transform(articles_model)  ##Learn the category-to-number mapping and then apply that mapping to the DataFrame.


articles_model = articles_model.drop(*categorical_cols)
articles_model.show(5) 

print(f"✅ Modified Articles DataFrame has {articles_model.count():,} rows and {len(articles_model.columns)} columns.")


null_counts_articles = articles_model.select(
    [
        sum(col(c).isNull().cast("int")).alias(c)
        for c in articles_model.columns
    ]
)
# null_counts_articles.show(5)


# #Dropping duplicates in the transactions dataframe
# duplicate_transactions = (
#     transactions
#     .groupBy(
#         "customer_id",
#         "article_id",
#         "t_dat"
#     )
#     .count()
#     .filter("count > 1")
# )

# duplicate_transactions.show(5)


# #processing date  column in transactions dataframe
# from pyspark.sql.functions import (
#     year, month, dayofweek
# )

# cleaned_df_transactions = (
#     transactions
#     .withColumn("year", year("t_dat"))
#     .withColumn("purchase_month", month("t_dat"))
#     .withColumn("purchase_day_of_week", dayofweek("t_dat"))
# )


# transactions_model = cleaned_df_transactions

# # # #Cleaned transactions dataframe by dropping duplicates.
# # # cleaned_df_transactions = transactions.dropDuplicates(
# # #     ["customer_id", "article_id", "t_dat"]
# # # )


# null_counts_transactions = transactions_model.select(
#     [
#         sum(col(c).isNull().cast("int")).alias(c)
#         for c in transactions_model.columns
#     ]
# )
# print(f"✅ Modified Transactions DataFrame has {transactions_model.count():,} rows and {len(transactions_model.columns)} columns.")
# null_counts_transactions.show()

# # # Filling null values in Active column and FN column based on fashion_news_frequency
# customers = customers.withColumn(
#     "Active",
#     when(
#         col("club_member_status") == "ACTIVE",
#         1.0
#     ).otherwise(0.0)
# )

# customers = customers.withColumn(
#     "FN",
#     when(
#         (col("FN").isNull()) &
#         (col("fashion_news_frequency").isin("Regularly", "Monthly")),
#         1.0
#     ).otherwise(0.0))
# # customers.show(5)

# # # #fILIING NULL,nONE VALUES IN THE fashion_news_frequency COLUMN AS "None" on the whole dataset
# customers = customers.withColumn(
#     "fashion_news_frequency",
#     when(
#         col("fashion_news_frequency").isNull() |
#         (col("fashion_news_frequency") == "NONE"),
#         "None"
#     ).otherwise(col("fashion_news_frequency")))

# # # # Filling null values in the club_member_status column as "Unknown" on the whole dataset
# customers=customers.withColumn(
#     "club_member_status",
#     when(
#         col("club_member_status").isNull(),
#         "Unknown"
#     ).otherwise(col("club_member_status")))

# median_age = customers.approxQuantile(
#     "age",
#     [0.5],
#     0.01
# )[0]

# # # # print(median_age)
# customers = customers.fillna(
#     {"age": median_age})


# # # # Dropping duplicates in the customers dataframe
# cleaned_df_customers = customers.distinct()
# customers_model = cleaned_df_customers.drop('postal_code','FN')

# # #customer behavioral features engineering
# from pyspark.sql.functions import (
#     count,
#     countDistinct,
#     avg,
#     sum,
#     min,
#     max,
#     datediff,
#     col
# )

# customers_features = (
#     cleaned_df_transactions
#     .groupBy("customer_id")
#     .agg(
#         count("*").alias("purchase_count"),
#         countDistinct("article_id").alias("unique_articles_count"),
#         avg("price").alias("average_price"),
#         sum("price").alias("total_spent"),
#         min("t_dat").alias("first_purchase_date"),
#         max("t_dat").alias("last_purchase_date")
#     )
# )

# customers_features = (
#     customers_features
#     .withColumn(
#         "recency_days",
#         datediff(
#             col("last_purchase_date"),
#             col("first_purchase_date")
#         )
#     )
#     .withColumn(
#         "purchase_frequency",
#         col("purchase_count") /
#         (col("recency_days") + 1)
#     )
# )
# # print(f"✅ Modified Customers DataFrame has {customers_model.count():,} rows and {len(customers_model.columns)} columns.")
# customers_model=customers_model.join(
#     customers_features,
#     on="customer_id",
#     how="left"
# )
# customers_model.filter(
#     col("purchase_count").isNull()
# ).count()
# customers_model.select("customer_id").subtract(
#     customers_features.select("customer_id")
# ).count()
# from pyspark.sql.functions import coalesce, lit

# customers_model = customers_model.withColumn(
#     "purchase_count",
#     coalesce(col("purchase_count"), lit(0))
# ).withColumn(
#     "unique_articles_count",
#     coalesce(col("unique_articles_count"), lit(0))
# ).withColumn(
#     "average_price",
#     coalesce(col("average_price"), lit(0.0))
# ).withColumn(
#     "total_spent",
#     coalesce(col("total_spent"), lit(0.0))
# ).withColumn(
#     "recency_days",
#     coalesce(col("recency_days"), lit(0))
# ).withColumn(
#     "purchase_frequency",
#     coalesce(col("purchase_frequency"), lit(0.0))
# )


# customers_model = customers_model.withColumn(
#     "customer_lifetime_days",
#     when(
#         col("first_purchase_date").isNull(),
#         0
#     ).otherwise(
#         datediff(current_date(), col("first_purchase_date"))
#     )
# )

# customers_model = customers_model.withColumn(
#     "recency_days",
#     when(
#         col("last_purchase_date").isNull(),
#         -1
#     ).otherwise(
#         datediff(current_date(), col("last_purchase_date"))
#     )
# )
# # customers_features.groupBy("customer_id") \
# #     .count() \
# #     .filter(col("count") > 1) \
# #     .show()

# customers_model = customers_model.drop(
#     "first_purchase_date",
#     "last_purchase_date"
# )
# null_counts_customers = customers_model.select(
#     [
#         sum(col(c).isNull().cast("int")).alias(c)
#         for c in customers_model.columns
#     ]
# )
# print("✅ Data Cleaning Completed")
# print(f"✅ Modified Customers DataFrame has {customers_model.count():,} rows and {len(customers_model.columns)} columns.")

# null_counts_customers.show()


# # # ==============================
# # # SAVE PROCESSED DATA AS PARQUET
# # # ==============================

PARQUET_DIR = r"D:\\Recommendation_system\\Context-Aware-Neural-Recommendation\\data\\parquet"

os.makedirs(PARQUET_DIR, exist_ok=True)

print("💾 Saving DataFrames as Parquet...")

articles_model.write \
    .mode("overwrite") \
    .parquet(os.path.join(PARQUET_DIR, "articles"))

# customers_model.write \
#     .mode("overwrite") \
#     .parquet(os.path.join(PARQUET_DIR, "customers"))

# transactions_model.write \
#     .mode("overwrite") \
#     .parquet(os.path.join(PARQUET_DIR, "transactions"))

# print("✅ Articles saved")
# print("✅ Customers saved")
# print("✅ Transactions saved")


# articles_check = spark_session.read.parquet(
#     os.path.join(PARQUET_DIR, "articles")
# )

# customers_check = spark_session.read.parquet(
#     os.path.join(PARQUET_DIR, "customers")
# )

# transactions_check = spark_session.read.parquet(
#     os.path.join(PARQUET_DIR, "transactions")
# )

spark_session.stop()

print("✅ Spark Session Closed")

