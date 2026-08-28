
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import os,sys

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


def init_spark():
    print("🚀 Initializing PySpark Session...")
    # Configured to use all available local CPU cores and manage memory efficiently
    spark = (SparkSession.builder \
           .appName("HM_sample_dataset")
           .master("local[*]")
           .getOrCreate())
    return spark



if __name__ == "__main__":
    # Start the PySpark session
    spark_session = init_spark()
    
    #Load the parquet files
    PARQUET_DIR = r"D:\\Recommendation_system\\Context-Aware-Neural-Recommendation\\data\\parquet"

    articles = spark_session.read.parquet(
        PARQUET_DIR + r"\\articles"
    )

    customers = spark_session.read.parquet(
        PARQUET_DIR + r"\\customers"
    )

    transactions = spark_session.read.parquet(
        PARQUET_DIR + r"\\transactions"
    )


# -----------------------------------
# 1. Sample 5% of customers
# -----------------------------------

sample_customer_ids = (
    customers
    .select("customer_id")
    .distinct()
    .sample(False, 0.05, seed=42)
)



# -----------------------------------
# 2. Get transactions of sampled customers
# -----------------------------------

sample_transactions_model = (
    transactions
    .join(
        sample_customer_ids,
        on="customer_id",
        how="inner"
    )
)

sample_customers_model = (
    customers
    .join(
        sample_transactions_model
        .select("customer_id")
        .distinct(),
        on="customer_id",
        how="inner"
    )
)
# -----------------------------------
# 3. Get articles purchased by them
# -----------------------------------

sample_article_ids = (
    sample_transactions_model
    .select("article_id")
    .distinct()
)

sample_articles_model = (
    articles
    .join(
        sample_article_ids,
        on="article_id",
        how="inner"
    )
)

# -----------------------------------
# 4. Check the results
# -----------------------------------

print(
    "Sample customers:",
    sample_customers_model.select("customer_id").distinct().count()
)

print(
    "Sample customers in transactions:",
    sample_transactions_model.select("customer_id").distinct().count()
)

print(
    "Sample articles:",
    sample_articles_model.select("article_id").distinct().count()
)

print(
    "Sample articles in transactions:",
    sample_transactions_model.select("article_id").distinct().count()
)

print(
    "Sample transactions:",
    sample_transactions_model.count()
)