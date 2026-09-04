import os
import json
import sys
import pandas as pd
import numpy as np

HAS_PYSPARK = False
try:
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col
    HAS_PYSPARK = True
except ImportError:
    HAS_PYSPARK = False

def safe_save_parquet(df, target_path):
    """
    Safely writes a Pandas DataFrame to Parquet format handling Windows file locks.
    """
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
        except Exception:
            pass
    try:
        df.to_parquet(target_path, index=False, engine="pyarrow")
        print(f"[OK] Saved {target_path} ({len(df)} rows, {len(df.columns)} cols)")
    except Exception as e:
        print(f"[WARN] Could not write parquet file {target_path}: {e}")
        fallback_csv = target_path.replace(".parquet", ".csv")
        df.to_csv(fallback_csv, index=False)
        print(f"[OK] Saved CSV fallback {fallback_csv} ({len(df)} rows, {len(df.columns)} cols)")

def extract_column_vocabulary(df, col_name, limit=None):
    """
    Extracts distinct values of a given column as a plain Python list of strings.
    """
    if not isinstance(df, pd.DataFrame):
        distinct_rows = df.select(col_name).filter(col(col_name).isNotNull()).distinct()
        if limit:
            distinct_rows = distinct_rows.limit(limit)
        rows = distinct_rows.collect()
        return [str(r[col_name]) for r in rows]

    # Pandas
    vals = df[col_name].dropna().unique().tolist()
    if limit:
        vals = vals[:limit]
    return [str(v) for v in vals]

def generate_vocabularies_and_exports(spark, articles_df, customers_df, transactions_df, output_dir=None):
    """
    Extracts feature vocabularies and writes Parquet + JSON metadata artifacts.
    """
    if output_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "processed_data")

    os.makedirs(output_dir, exist_ok=True)
    print(f"[INFO] Target export directory: {output_dir}")

    print("[INFO] Extracting User and Article vocabularies...")
    user_vocab = extract_column_vocabulary(customers_df, "customer_id")
    article_vocab = extract_column_vocabulary(articles_df, "article_id")

    print("[INFO] Extracting Categorical metadata vocabularies...")
    categorical_cols = [
        "product_type_name", "product_group_name", "graphical_appearance_name",
        "colour_group_name", "department_name", "index_group_name", "garment_group_name"
    ]
    
    cat_vocabularies = {}
    articles_cols = articles_df.columns if hasattr(articles_df, "columns") else []
    for c in categorical_cols:
        if c in articles_cols:
            cat_vocabularies[c] = extract_column_vocabulary(articles_df, c)

    customer_cat_cols = ["age_group", "club_member_status", "fashion_news_frequency"]
    customers_cols = customers_df.columns if hasattr(customers_df, "columns") else []
    for c in customer_cat_cols:
        if c in customers_cols:
            cat_vocabularies[c] = extract_column_vocabulary(customers_df, c)

    txn_count = len(transactions_df) if isinstance(transactions_df, pd.DataFrame) else (transactions_df.count() if transactions_df else 0)
    vocab_data = {
        "summary_statistics": {
            "total_users": int(len(user_vocab)),
            "total_articles": int(len(article_vocab)),
            "total_transactions": int(txn_count)
        },
        "user_id_vocabulary": user_vocab,
        "article_id_vocabulary": article_vocab,
        "categorical_vocabularies": cat_vocabularies
    }

    json_path = os.path.join(output_dir, "vocabularies.json")
    print(f"[INFO] Saving vocabulary JSON artifact to: {json_path}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(vocab_data, f, indent=2)

    print("[INFO] Exporting processed DataFrames to Parquet format...")
    if not isinstance(articles_df, pd.DataFrame):
        articles_df.write.mode("overwrite").parquet(os.path.join(output_dir, "articles_processed.parquet"))
        customers_df.write.mode("overwrite").parquet(os.path.join(output_dir, "customers_processed.parquet"))
        if transactions_df:
            transactions_df.write.mode("overwrite").parquet(os.path.join(output_dir, "transactions_processed.parquet"))
    else:
        safe_save_parquet(articles_df, os.path.join(output_dir, "articles_processed.parquet"))
        safe_save_parquet(customers_df, os.path.join(output_dir, "customers_processed.parquet"))
        if transactions_df is not None:
            safe_save_parquet(transactions_df, os.path.join(output_dir, "transactions_processed.parquet"))

    print("[OK] Week 1 Vocabularies and Parquet Exports Completed Successfully!")
    return json_path

if __name__ == "__main__":
    from dataprep import run_data_preparation
    from feature_engineering import (
        build_temporal_features,
        build_article_popularity_features,
        build_user_interaction_sequences
    )
    
    spark, articles_clean, customers_clean, transactions_clean, _ = run_data_preparation()
    txns_time, max_date = build_temporal_features(transactions_clean)
    articles_featured = build_article_popularity_features(txns_time, articles_clean, max_date)
    customers_featured = build_user_interaction_sequences(txns_time, customers_clean)

    generate_vocabularies_and_exports(spark, articles_featured, customers_featured, txns_time)
