import os
import sys
import pandas as pd

HAS_PYSPARK = False
try:
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import (
        col, sum as spark_sum, when, count, min as spark_min, max as spark_max, avg, to_date, lit
    )
    HAS_PYSPARK = True
except ImportError:
    HAS_PYSPARK = False

def configure_environment():
    """
    Configures environment variables for Java and PySpark.
    """
    custom_java = r"C:\java\OpenJDK17U-jdk_x64_windows_hotspot_17.0.20_8\jdk-17.0.20+8"
    if os.path.exists(custom_java):
        os.environ["JAVA_HOME"] = custom_java
        os.environ["PATH"] = os.path.join(custom_java, "bin") + ";" + os.environ.get("PATH", "")

    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    os.environ["PYSPARK_ALLOW_INSECURE_GATEWAY"] = "1"

def init_spark():
    """
    Initializes PySpark session if winutils/Hadoop environment is present, else falls back to Pandas engine.
    """
    if not HAS_PYSPARK:
        print("[INFO] PySpark library not imported. Running Pandas DataEngine.")
        return None

    if os.name == 'nt':
        hadoop_home = os.environ.get("HADOOP_HOME")
        has_winutils = hadoop_home and os.path.exists(os.path.join(hadoop_home, "bin", "winutils.exe"))
        if not has_winutils:
            print("[INFO] Running on Windows without winutils.exe. Utilizing Pandas DataEngine for max stability.")
            return None

    try:
        print("[INFO] Initializing PySpark Session for H&M Recommender...")
        spark = SparkSession.builder \
            .appName("HM_Context_Aware_Recommender") \
            .config("spark.driver.memory", "4g") \
            .config("spark.sql.shuffle.partitions", "20") \
            .master("local[*]") \
            .getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        return spark
    except Exception as e:
        print(f"[WARN] PySpark initialization note: {e}")
        print("[INFO] Switching to Pandas DataEngine.")
        return None

def get_data_directory():
    """
    Resolves data directory path dynamically.
    """
    env_data_dir = os.environ.get("DATA_DIR")
    if env_data_dir and os.path.exists(env_data_dir):
        return env_data_dir

    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_data_dir = os.path.join(base_dir, "data")
    if os.path.exists(local_data_dir):
        return local_data_dir

    fallback_d_drive = r"D:\Recommendation_system\Context-Aware-Neural-Recommendation\data"
    if os.path.exists(fallback_d_drive):
        return fallback_d_drive

    return local_data_dir

def load_raw_data(spark, data_dir):
    """
    Loads raw CSV files into PySpark DataFrames (or Pandas DataFrames as fallback).
    """
    print(f"[INFO] Reading CSV files from: {data_dir}")
    articles_path = os.path.join(data_dir, "articles.csv")
    customers_path = os.path.join(data_dir, "customers.csv")
    transactions_path = os.path.join(data_dir, "transactions_train.csv")

    for path in [articles_path, customers_path, transactions_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing dataset file at '{path}'.")

    if spark is not None:
        try:
            articles_df = spark.read.csv(articles_path, header=True, inferSchema=True)
            customers_df = spark.read.csv(customers_path, header=True, inferSchema=True)
            transactions_df = spark.read.csv(transactions_path, header=True, inferSchema=True)
            return articles_df, customers_df, transactions_df
        except Exception as e:
            print(f"[WARN] Spark CSV read failed ({e}). Falling back to Pandas.")

    # Pandas Fallback
    articles_df = pd.read_csv(articles_path)
    customers_df = pd.read_csv(customers_path)
    transactions_df = pd.read_csv(transactions_path)
    return articles_df, customers_df, transactions_df

def clean_articles(articles_df):
    """
    Cleans articles dataframe: missing values & deduplication.
    """
    print("[INFO] Cleaning Articles DataFrame...")
    if not isinstance(articles_df, pd.DataFrame):
        articles_cleaned = articles_df.fillna({"detail_desc": "No Description Available"})
        articles_cleaned = articles_cleaned.fillna("Unknown")
        articles_cleaned = articles_cleaned.distinct()
        print(f"[OK] Cleaned Articles (Spark): {articles_cleaned.count():,} rows")
        return articles_cleaned

    # Pandas
    articles_df["detail_desc"] = articles_df["detail_desc"].fillna("No Description Available")
    articles_df = articles_df.fillna("Unknown").drop_duplicates()
    print(f"[OK] Cleaned Articles (Pandas): {len(articles_df):,} rows")
    return articles_df

def clean_customers(customers_df):
    """
    Cleans customers dataframe: imputes median age, club status, age_group, FN, Active.
    """
    print("[INFO] Cleaning Customers DataFrame...")
    if not isinstance(customers_df, pd.DataFrame):
        customers = customers_df.withColumn(
            "club_member_status",
            when(col("club_member_status").isNull(), "Unknown").otherwise(col("club_member_status"))
        ).withColumn(
            "fashion_news_frequency",
            when(col("fashion_news_frequency").isNull() | (col("fashion_news_frequency") == "NONE"), "None")
            .otherwise(col("fashion_news_frequency"))
        ).withColumn(
            "Active", when(col("club_member_status") == "ACTIVE", 1.0).otherwise(0.0)
        ).withColumn(
            "FN", when((col("FN").isNull()) & (col("fashion_news_frequency").isin("Regularly", "Monthly")), 1.0)
            .otherwise(when(col("FN").isNull(), 0.0).otherwise(col("FN").cast("double")))
        )

        quantiles = customers.approxQuantile("age", [0.5], 0.01)
        median_age = quantiles[0] if quantiles and quantiles[0] is not None else 30.0
        customers = customers.fillna({"age": median_age})

        customers = customers.withColumn(
            "age_group",
            when(col("age") < 25, "Young")
            .when(col("age") < 40, "Adult")
            .when(col("age") < 60, "Middle_Aged")
            .otherwise("Senior")
        ).distinct()
        print(f"[OK] Cleaned Customers (Spark): {customers.count():,} rows")
        return customers

    # Pandas
    df = customers_df.copy()
    df["club_member_status"] = df["club_member_status"].fillna("Unknown")
    df["fashion_news_frequency"] = df["fashion_news_frequency"].replace({"NONE": "None"}).fillna("None")
    df["Active"] = (df["club_member_status"] == "ACTIVE").astype(float)
    df["FN"] = df["fashion_news_frequency"].isin(["Regularly", "Monthly"]).astype(float)
    
    median_age = df["age"].median()
    if pd.isna(median_age):
        median_age = 30.0
    df["age"] = df["age"].fillna(median_age)

    def get_age_group(age):
        if age < 25: return "Young"
        elif age < 40: return "Adult"
        elif age < 60: return "Middle_Aged"
        else: return "Senior"

    df["age_group"] = df["age"].apply(get_age_group)
    df = df.drop_duplicates()
    print(f"[OK] Cleaned Customers (Pandas): {len(df):,} rows")
    return df

def clean_transactions(transactions_df):
    """
    Cleans transactions dataframe: formats dates, price casting, deduplication.
    """
    print("[INFO] Cleaning Transactions DataFrame...")
    if not isinstance(transactions_df, pd.DataFrame):
        txns = transactions_df.withColumn("t_dat", to_date(col("t_dat"), "yyyy-MM-dd"))
        txns = txns.withColumn("price", col("price").cast("double"))
        txns_cleaned = txns.dropDuplicates(["customer_id", "article_id", "t_dat"])
        print(f"[OK] Cleaned Transactions (Spark): {txns_cleaned.count():,} rows")
        return txns_cleaned

    # Pandas
    df = transactions_df.copy()
    df["t_dat"] = pd.to_datetime(df["t_dat"]).dt.strftime("%Y-%m-%d")
    df["price"] = df["price"].astype(float)
    df = df.drop_duplicates(subset=["customer_id", "article_id", "t_dat"])
    print(f"[OK] Cleaned Transactions (Pandas): {len(df):,} rows")
    return df

def apply_cold_start_strategy(spark, articles_df, customers_df, transactions_df):
    """
    Cold-start strategies for unobserved users and articles.
    """
    print("[INFO] Applying Cold-Start Strategies...")
    if not isinstance(transactions_df, pd.DataFrame):
        active_articles = transactions_df.select("article_id").distinct()
        cold_articles = articles_df.join(active_articles, on="article_id", how="left_anti")

        active_customers = transactions_df.select("customer_id").distinct()
        cold_customers = customers_df.join(active_customers, on="customer_id", how="left_anti")

        top_popular_articles = (
            transactions_df.groupBy("article_id")
            .agg(count("customer_id").alias("purchase_count"))
            .sort(col("purchase_count").desc())
            .limit(100)
        )
        print(f"[INFO] Cold-Start (Spark): {cold_articles.count():,} cold items, {cold_customers.count():,} cold users")
        return cold_articles, cold_customers, top_popular_articles

    # Pandas
    active_aids = set(transactions_df["article_id"].unique())
    cold_articles = articles_df[~articles_df["article_id"].isin(active_aids)]

    active_cids = set(transactions_df["customer_id"].unique())
    cold_customers = customers_df[~customers_df["customer_id"].isin(active_cids)]

    top_popular_articles = (
        transactions_df.groupby("article_id")["customer_id"]
        .count().reset_index()
        .rename(columns={"customer_id": "purchase_count"})
        .sort_values(by="purchase_count", ascending=False)
        .head(100)
    )
    print(f"[INFO] Cold-Start (Pandas): {len(cold_articles):,} cold items, {len(cold_customers):,} cold users")
    return cold_articles, cold_customers, top_popular_articles

def run_data_preparation():
    """
    Main pipeline function for Data Processing & Cold Start Handling.
    """
    configure_environment()
    spark = init_spark()
    data_dir = get_data_directory()

    articles_raw, customers_raw, transactions_raw = load_raw_data(spark, data_dir)

    articles_clean = clean_articles(articles_raw)
    customers_clean = clean_customers(customers_raw)
    transactions_clean = clean_transactions(transactions_raw)

    cold_articles, cold_customers, top_popular = apply_cold_start_strategy(
        spark, articles_clean, customers_clean, transactions_clean
    )

    print("[OK] Week 1 Data Cleaning & Cold-Start Strategy successfully configured.")
    return spark, articles_clean, customers_clean, transactions_clean, top_popular

if __name__ == "__main__":
    run_data_preparation()
