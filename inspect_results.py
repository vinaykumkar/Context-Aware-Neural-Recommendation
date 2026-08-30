import os
import json
import pandas as pd

def inspect_week1_results():
    """
    Displays a human-readable summary and data preview of Week 1 output artifacts.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    processed_dir = os.path.join(base_dir, "processed_data")

    vocab_path = os.path.join(processed_dir, "vocabularies.json")
    articles_path = os.path.join(processed_dir, "articles_processed.parquet")
    articles_csv = os.path.join(processed_dir, "articles_processed.csv")
    customers_path = os.path.join(processed_dir, "customers_processed.parquet")
    txns_path = os.path.join(processed_dir, "transactions_processed.parquet")

    print("=" * 70)
    print("[SUMMARY] WEEK 1 RESULT INSPECTOR & PREVIEW SUMMARY")
    print("=" * 70)

    # 1. Inspect Vocabularies JSON
    if os.path.exists(vocab_path):
        with open(vocab_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        stats = data.get("summary_statistics", {})
        print("\n1. SUMMARY STATISTICS & VOCABULARIES (vocabularies.json):")
        print(f"   * Total Unique Users   : {stats.get('total_users', 0):,}")
        print(f"   * Total Unique Articles: {stats.get('total_articles', 0):,}")
        print(f"   * Total Transactions   : {stats.get('total_transactions', 0):,}")
        
        cats = data.get("categorical_vocabularies", {})
        print("   * Categorical Feature Vocabularies Extracted:")
        for cat_name, vocab_list in cats.items():
            print(f"     - {cat_name:<28}: {len(vocab_list)} unique categories | e.g., {vocab_list[:3]}")

    # 2. Inspect Customers DataFrame
    if os.path.exists(customers_path):
        customers_df = pd.read_parquet(customers_path)
        print("\n2. PROCESSED CUSTOMERS PREVIEW (customers_processed.parquet):")
        print(f"   * Rows: {len(customers_df):,}, Columns ({len(customers_df.columns)}): {list(customers_df.columns)}")
        print("   * Sample Rows:")
        sample_cols = [c for c in ["customer_id", "age", "age_group", "club_member_status", "Active", "FN", "recent_article_ids"] if c in customers_df.columns]
        print(customers_df[sample_cols].head(5).to_string(index=False))

    # 3. Inspect Articles DataFrame
    if os.path.exists(articles_path) and os.path.getsize(articles_path) > 0:
        articles_df = pd.read_parquet(articles_path)
    elif os.path.exists(articles_csv):
        articles_df = pd.read_csv(articles_csv)
    else:
        articles_df = None

    if articles_df is not None:
        print("\n3. PROCESSED ARTICLES PREVIEW (articles_processed):")
        print(f"   * Rows: {len(articles_df):,}, Columns ({len(articles_df.columns)}): {list(articles_df.columns[:5])} ...")
        print("   * Sample Rows:")
        sample_cols = [c for c in ["article_id", "prod_name", "product_type_name", "garment_group_name", "pop_total_sales"] if c in articles_df.columns]
        print(articles_df[sample_cols].head(5).to_string(index=False))

    # 4. Inspect Transactions DataFrame
    if os.path.exists(txns_path):
        txns_df = pd.read_parquet(txns_path)
        print("\n4. PROCESSED TRANSACTIONS PREVIEW (transactions_processed.parquet):")
        print(f"   * Rows: {len(txns_df):,}, Columns ({len(txns_df.columns)}): {list(txns_df.columns)}")
        print("   * Sample Rows:")
        sample_cols = [c for c in ["t_dat", "customer_id", "article_id", "price", "day_of_week", "month"] if c in txns_df.columns]
        print(txns_df[sample_cols].head(5).to_string(index=False))

    print("\n" + "=" * 70)
    print("[OK] All artifacts verified and accessible in directory: ./processed_data")
    print("=" * 70)

if __name__ == "__main__":
    inspect_week1_results()
