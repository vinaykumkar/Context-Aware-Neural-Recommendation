import matplotlib.pyplot as plt
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
           .appName("HM_EDA")
           .master("local[*]")
           .getOrCreate())
    return spark

    

def monthly_sales_analysis(spark):
    print("🔍 Starting EDA...")
    
    # Monthly sales trend analysis
    monthly_sales = (
    transactions
    .groupBy("year", "purchase_month")
    .count()    
    .orderBy("year", "purchase_month")
)

    monthly_sales.show()

    # visualize monthly sales trend
    monthly_pd = monthly_sales.toPandas()

    monthly_pd["period"] = (
    monthly_pd["year"].astype(str)
    + "-"
    + monthly_pd["purchase_month"].astype(str).str.zfill(2)
)

    plt.figure(figsize=(12, 5))
    plt.plot(monthly_pd["period"], monthly_pd["count"])
    plt.xticks(rotation=45)
    plt.xlabel("Month")
    plt.ylabel("Number of Transactions")
    plt.title("Monthly Transaction Trend")
    plt.tight_layout()
    plt.show()

    return monthly_sales
    #Top 10 most purchased articles
def top_articles_analysis(spark):
    top_articles = (
    transactions
    .groupBy("article_id")
    .count()
    .orderBy(col("count").desc())
    .limit(10)
)

    top_articles.show()

    # Visualize top 10 articles
    top_articles_pd = top_articles.toPandas()

    plt.figure(figsize=(10, 5))
    plt.bar(
    top_articles_pd["article_id"].astype(str),
    top_articles_pd["count"]
)

    plt.xlabel("Article ID")
    plt.ylabel("Purchase Count")
    plt.title("Top 10 Most Purchased Articles")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    return top_articles

    #Price distribution of articles
def price_distribution_analysis(spark):
    price_pd = (
    transactions
    .select("price")
    .dropna()
    .sample(False, 0.01, seed=42)
    .toPandas()
)
    plt.figure(figsize=(10, 5))
    plt.hist(price_pd["price"], bins=50)

    plt.xlabel("Normalized Price")
    plt.ylabel("Frequency")
    plt.title("Distribution of Normalized Product Prices")
    plt.tight_layout()
    plt.show()

    return price_pd

    #Purchases by sales channel
def sales_channel_analysis(spark):
    channel_sales = (
    transactions
    .groupBy("sales_channel_id")
    .count()
    .orderBy(col("count").desc())
)

    channel_sales.show()

    #Visualize purchases by sales channel
    channel_pd = channel_sales.toPandas()

    plt.figure(figsize=(7, 5))
    plt.bar(
        channel_pd["sales_channel_id"].astype(str),
        channel_pd["count"]
    )

    plt.xlabel("Sales Channel")
    plt.ylabel("Number of Transactions")
    plt.title("Transactions by Sales Channel")
    plt.tight_layout()
    plt.show()

    return channel_sales
    #Customer purchase frequency
def customer_purchase_frequency_analysis(spark):
    purchase_pd = (
    customers
    .select("purchase_count")
    .toPandas()
)
    plt.figure(figsize=(8, 5))
    plt.boxplot(purchase_pd["purchase_count"].dropna())

    plt.ylabel("Number of Purchases")
    plt.title("Customer Purchase Count Distribution")
    plt.tight_layout()
    plt.show()

    return purchase_pd

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

   
    # Execute the load function
    # ms_analysis=monthly_sales_analysis(spark_session)
    # top_art_anlysis = top_articles_analysis(spark_session)
    # price_dist_analysis = price_distribution_analysis(spark_session)
    # sales_chan_analysis = sales_channel_analysis(spark_session)
    # cust_freq_analysis = customer_purchase_frequency_analysis(spark_session)

    articles.show(5)

    #sample dataset from original dataframe
    # sample_df_transactions = transactions.sample(False, 0.01, seed=42)
    # sample_df_articles = articles.sample(False, 0.01, seed=42)
    # sample_df_customers = customers.sample(False, 0.01, seed=42)




    spark_session.stop()

    print("✅ Spark Session Closed")
