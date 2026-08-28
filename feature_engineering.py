import os
import sys
import pandas as pd
import numpy as np

HAS_PYSPARK = False
try:
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import (
        col, max as spark_max, min as spark_min, count, avg,
        datediff, dayofweek, month, year, collect_list, slice as spark_slice, struct, sort_array
    )
    HAS_PYSPARK = True
except ImportError:
    HAS_PYSPARK = False

def build_temporal_features(transactions_df):
    """
    Engineers recency and calendar timestamp features.
    """
    print("[INFO] Engineering Temporal & Recency Features...")
    if not isinstance(transactions_df, pd.DataFrame):
        max_date_row = transactions_df.select(spark_max("t_dat").alias("max_dat")).collect()
        max_dat = max_date_row[0]["max_dat"]
        txns_with_time = transactions_df.withColumn(
            "day_of_week", dayofweek(col("t_dat"))
        ).withColumn(
            "month", month(col("t_dat"))
        ).withColumn(
            "year", year(col("t_dat"))
        )
        return txns_with_time, max_dat

    # Pandas
    df = transactions_df.copy()
    df["t_dat_dt"] = pd.to_datetime(df["t_dat"])
    max_dat = df["t_dat_dt"].max()
    df["days_since_max"] = (max_dat - df["t_dat_dt"]).dt.days
    df["day_of_week"] = df["t_dat_dt"].dt.dayofweek + 1
    df["month"] = df["t_dat_dt"].dt.month
    df["year"] = df["t_dat_dt"].dt.year
    df = df.drop(columns=["t_dat_dt"])
    return df, str(max_dat)

def build_article_popularity_features(transactions_df, articles_df, max_date):
    """
    Engineers 30-day and total product popularity features.
    """
    print("[INFO] Engineering Product Popularity Features...")
    if not isinstance(transactions_df, pd.DataFrame):
        overall_pop = transactions_df.groupBy("article_id").agg(
            count("customer_id").alias("pop_total_sales"),
            avg("price").alias("article_avg_price")
        )
        articles_enriched = articles_df.join(overall_pop, on="article_id", how="left").fillna({
            "pop_total_sales": 0, "article_avg_price": 0.0
        })
        print("[OK] Product Popularity Features Engineered (Spark).")
        return articles_enriched

    # Pandas
    overall_pop = transactions_df.groupby("article_id").agg(
        pop_total_sales=("customer_id", "count"),
        article_avg_price=("price", "mean")
    ).reset_index()

    pop_30d = transactions_df[transactions_df["days_since_max"] <= 30].groupby("article_id").agg(
        pop_30d_sales=("customer_id", "count")
    ).reset_index()

    articles_enriched = pd.merge(articles_df, overall_pop, on="article_id", how="left")
    articles_enriched = pd.merge(articles_enriched, pop_30d, on="article_id", how="left")

    articles_enriched["pop_total_sales"] = articles_enriched["pop_total_sales"].fillna(0).astype(int)
    articles_enriched["pop_30d_sales"] = articles_enriched["pop_30d_sales"].fillna(0).astype(int)
    articles_enriched["article_avg_price"] = articles_enriched["article_avg_price"].fillna(0.0)

    print(f"[OK] Product Popularity Features Engineered (Pandas): {len(articles_enriched.columns)} columns")
    return articles_enriched

def build_user_interaction_sequences(transactions_df, customers_df, max_sequence_length=10):
    """
    Aggregates historical interaction sequences per customer.
    """
    print("[INFO] Building Customer Interaction Sequences...")
    if not isinstance(transactions_df, pd.DataFrame):
        user_txns_ordered = transactions_df.select(
            "customer_id", "article_id", "t_dat"
        ).withColumn("txn_struct", struct("t_dat", "article_id"))

        user_sequences = user_txns_ordered.groupBy("customer_id").agg(
            sort_array(collect_list("txn_struct"), asc=False).alias("sorted_txns"),
            count("article_id").alias("user_total_purchases")
        )

        user_sequences = user_sequences.withColumn(
            "recent_article_ids",
            spark_slice(col("sorted_txns.article_id"), 1, max_sequence_length)
        ).drop("sorted_txns")

        customers_enriched = customers_df.join(user_sequences, on="customer_id", how="left").fillna({"user_total_purchases": 0})
        print("[OK] Customer Interaction Sequences Built (Spark).")
        return customers_enriched

    # Pandas
    sorted_txns = transactions_df.sort_values(by=["customer_id", "t_dat"], ascending=[True, False])
    user_sequences = sorted_txns.groupby("customer_id").agg(
        recent_article_ids=("article_id", lambda x: list(x)[:max_sequence_length]),
        user_total_purchases=("article_id", "count")
    ).reset_index()

    customers_enriched = pd.merge(customers_df, user_sequences, on="customer_id", how="left")
    customers_enriched["user_total_purchases"] = customers_enriched["user_total_purchases"].fillna(0).astype(int)
    customers_enriched["recent_article_ids"] = customers_enriched["recent_article_ids"].apply(
        lambda x: x if isinstance(x, list) else []
    )
    print("[OK] Customer Interaction Sequences Built (Pandas).")
    return customers_enriched

def assemble_contextual_interactions(transactions_df, customers_df, articles_df):
    """
    Combines transactions, user metadata, and item metadata into a context-enriched DataFrame.
    """
    print("[INFO] Assembling Context-Enriched Interactions DataFrame...")
    if not isinstance(transactions_df, pd.DataFrame):
        user_cols = ["customer_id", "age", "age_group", "club_member_status", "FN", "Active", "user_total_purchases"]
        users_subset = customers_df.select([c for c in user_cols if c in customers_df.columns])

        item_cols = [
            "article_id", "product_type_name", "product_group_name",
            "graphical_appearance_name", "colour_group_name", "department_name",
            "index_group_name", "garment_group_name", "pop_total_sales"
        ]
        items_subset = articles_df.select([c for c in item_cols if c in articles_df.columns])

        enriched = transactions_df.join(users_subset, on="customer_id", how="inner") \
                                  .join(items_subset, on="article_id", how="inner")

        print(f"[OK] Enriched Interactions assembled (Spark): {len(enriched.columns)} feature columns")
        return enriched

    # Pandas
    user_cols = [c for c in ["customer_id", "age", "age_group", "club_member_status", "FN", "Active", "user_total_purchases"] if c in customers_df.columns]
    item_cols = [c for c in ["article_id", "product_type_name", "product_group_name", "graphical_appearance_name", "colour_group_name", "department_name", "index_group_name", "garment_group_name", "pop_total_sales"] if c in articles_df.columns]

    users_subset = customers_df[user_cols]
    items_subset = articles_df[item_cols]

    enriched = pd.merge(transactions_df, users_subset, on="customer_id", how="inner")
    enriched = pd.merge(enriched, items_subset, on="article_id", how="inner")
    print(f"[OK] Enriched Interactions assembled (Pandas): {len(enriched.columns)} feature columns")
    return enriched

if __name__ == "__main__":
    from dataprep import run_data_preparation
    spark, articles_clean, customers_clean, transactions_clean, _ = run_data_preparation()
    
    txns_time, max_date = build_temporal_features(transactions_clean)
    articles_featured = build_article_popularity_features(txns_time, articles_clean, max_date)
    customers_featured = build_user_interaction_sequences(txns_time, customers_clean)
    enriched_interactions = assemble_contextual_interactions(txns_time, customers_featured, articles_featured)
