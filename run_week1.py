import os
import sys
import time

def execute_week1_pipeline():
    """
    Master pipeline runner for Week 1: Distributed Data Processing & Feature Engineering.
    """
    start_time = time.time()
    print("=" * 70)
    print("STARTING WEEK 1 PIPELINE: Distributed Data Processing & Feature Engineering")
    print("=" * 70)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Step 1: Check environment dependencies
    print("\n--- STEP 1: Verifying Environment & Package Installation ---")
    from install import check_and_install_requirements
    check_and_install_requirements()

    # Step 2: Dataset Verification & Extraction
    print("\n--- STEP 2: Dataset Verification & Extraction ---")
    from DataExtraction import download_dataset
    data_dir = download_dataset()

    # Step 3: PySpark Initialization & Data Cleaning (Week 1 Day 1-3)
    print("\n--- STEP 3: Data Cleaning & Cold-Start Handling (Day 1-3) ---")
    from dataprep import run_data_preparation
    spark, articles_clean, customers_clean, transactions_clean, top_popular = run_data_preparation()

    # Step 4: Feature Engineering (Week 1 Day 4-6)
    print("\n--- STEP 4: Temporal, Popularity & Sequence Feature Engineering (Day 4-6) ---")
    from feature_engineering import (
        build_temporal_features,
        build_article_popularity_features,
        build_user_interaction_sequences,
        assemble_contextual_interactions
    )
    txns_time, max_date = build_temporal_features(transactions_clean)
    articles_featured = build_article_popularity_features(txns_time, articles_clean, max_date)
    customers_featured = build_user_interaction_sequences(txns_time, customers_clean)
    enriched_interactions = assemble_contextual_interactions(txns_time, customers_featured, articles_featured)

    # Step 5: Export Vocabularies & Parquet Artifacts (Week 1 Day 7)
    print("\n--- STEP 5: Export Vocabularies & Parquet Data Artifacts (Day 7) ---")
    from export_vocabularies import generate_vocabularies_and_exports
    vocab_json_path = generate_vocabularies_and_exports(
        spark, articles_featured, customers_featured, txns_time
    )

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"[SUCCESS] WEEK 1 PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS!")
    print(f"Vocabulary Artifact: {vocab_json_path}")
    print("=" * 70)

if __name__ == "__main__":
    execute_week1_pipeline()
