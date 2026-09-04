import pandas as pd
import numpy as np

# ============================================================
# OPTIONAL PYSPARK IMPORT
# ============================================================

HAS_PYSPARK = False

try:
    from pyspark.sql import DataFrame as SparkDataFrame
    from pyspark.sql.functions import (
        col,
        max as spark_max,
        count,
        avg,
        datediff,
        dayofweek,
        month,
        year,
        collect_list,
        struct,
        sort_array,
        expr,
        lit
    )

    HAS_PYSPARK = True

except ImportError:
    HAS_PYSPARK = False


# ============================================================
# 1. TEMPORAL FEATURES
# ============================================================

def build_temporal_features(transactions_df):

    """
    Creates temporal and recency features from transactions.

    Features created:
        - days_since_max
        - day_of_week
        - month
        - year

    Returns:
        processed transactions
        maximum transaction date
    """

    print("\n[INFO] Engineering temporal features...")

    # --------------------------------------------------------
    # PYSPARK
    # --------------------------------------------------------

    if HAS_PYSPARK and isinstance(transactions_df, SparkDataFrame):

        # Make sure transaction date is DateType
        transactions_df = transactions_df.withColumn(
            "t_dat",
            col("t_dat").cast("date")
        )

        # Find latest transaction date
        max_date = transactions_df.select(
            spark_max("t_dat").alias("max_date")
        ).collect()[0]["max_date"]

        # Temporal features
        transactions_df = (
            transactions_df
            .withColumn(
                "days_since_max",
                datediff(lit(max_date), col("t_dat"))
            )
            .withColumn(
                "day_of_week",
                dayofweek(col("t_dat"))
            )
            .withColumn(
                "month",
                month(col("t_dat"))
            )
            .withColumn(
                "year",
                year(col("t_dat"))
            )
        )

        print(f"[OK] Maximum transaction date: {max_date}")
        print("[OK] Temporal features created.")

        return transactions_df, max_date

    # --------------------------------------------------------
    # PANDAS
    # --------------------------------------------------------

    df = transactions_df.copy()

    df["t_dat"] = pd.to_datetime(
        df["t_dat"],
        errors="coerce"
    )

    # Remove invalid dates
    df = df.dropna(subset=["t_dat"])

    max_date = df["t_dat"].max()

    df["days_since_max"] = (
        max_date - df["t_dat"]
    ).dt.days

    # Monday = 1, Sunday = 7
    df["day_of_week"] = (
        df["t_dat"].dt.dayofweek + 1
    )

    df["month"] = df["t_dat"].dt.month
    df["year"] = df["t_dat"].dt.year

    print(f"[OK] Maximum transaction date: {max_date}")
    print("[OK] Temporal features created.")

    return df, max_date


# ============================================================
# 2. ARTICLE POPULARITY FEATURES
# ============================================================

def build_article_popularity_features(
    transactions_df,
    articles_df,
    max_date
):

    """
    Creates product popularity features.

    Features:
        - pop_total_sales
        - pop_30d_sales
        - article_avg_price
    """

    print("\n[INFO] Engineering article popularity features...")

    # --------------------------------------------------------
    # PYSPARK
    # --------------------------------------------------------

    if HAS_PYSPARK and isinstance(transactions_df, SparkDataFrame):

        # Total sales + average price
        overall_popularity = (
            transactions_df
            .groupBy("article_id")
            .agg(
                count("*").alias("pop_total_sales"),
                avg("price").alias("article_avg_price")
            )
        )

        # Last 30 days
        recent_popularity = (
            transactions_df
            .filter(col("days_since_max") <= 30)
            .groupBy("article_id")
            .agg(
                count("*").alias("pop_30d_sales")
            )
        )

        # Join with article metadata
        articles_enriched = (
            articles_df
            .join(
                overall_popularity,
                on="article_id",
                how="left"
            )
            .join(
                recent_popularity,
                on="article_id",
                how="left"
            )
            .fillna({
                "pop_total_sales": 0,
                "pop_30d_sales": 0,
                "article_avg_price": 0.0
            })
        )

        print("[OK] Article popularity features created using Spark.")

        return articles_enriched

    # --------------------------------------------------------
    # PANDAS
    # --------------------------------------------------------

    txns = transactions_df.copy()

    # Total popularity
    overall_popularity = (
        txns
        .groupby("article_id")
        .agg(
            pop_total_sales=("customer_id", "count"),
            article_avg_price=("price", "mean")
        )
        .reset_index()
    )

    # Last 30 days popularity
    recent_transactions = txns[
        txns["days_since_max"] <= 30
    ]

    recent_popularity = (
        recent_transactions
        .groupby("article_id")
        .agg(
            pop_30d_sales=("customer_id", "count")
        )
        .reset_index()
    )

    # Merge
    articles_enriched = articles_df.merge(
        overall_popularity,
        on="article_id",
        how="left"
    )

    articles_enriched = articles_enriched.merge(
        recent_popularity,
        on="article_id",
        how="left"
    )

    # Missing popularity = zero
    articles_enriched["pop_total_sales"] = (
        articles_enriched["pop_total_sales"]
        .fillna(0)
        .astype("int64")
    )

    articles_enriched["pop_30d_sales"] = (
        articles_enriched["pop_30d_sales"]
        .fillna(0)
        .astype("int64")
    )

    articles_enriched["article_avg_price"] = (
        articles_enriched["article_avg_price"]
        .fillna(0.0)
        .astype("float32")
    )

    print(
        f"[OK] Article popularity features created. "
        f"Total columns: {len(articles_enriched.columns)}"
    )

    return articles_enriched


# ============================================================
# 3. CUSTOMER INTERACTION SEQUENCES
# ============================================================

def build_user_interaction_sequences(
    transactions_df,
    customers_df,
    max_sequence_length=10
):

    """
    Creates customer purchase history.

    Features:
        - user_total_purchases
        - recent_article_ids

    recent_article_ids contains the latest N purchased articles.
    """

    print("\n[INFO] Building customer interaction sequences...")

    # --------------------------------------------------------
    # PYSPARK
    # --------------------------------------------------------

    if HAS_PYSPARK and isinstance(transactions_df, SparkDataFrame):

        # Create struct so date and article remain together
        ordered_transactions = (
            transactions_df
            .select(
                "customer_id",
                "article_id",
                "t_dat"
            )
            .withColumn(
                "transaction_struct",
                struct(
                    col("t_dat"),
                    col("article_id")
                )
            )
        )

        user_sequences = (
            ordered_transactions
            .groupBy("customer_id")
            .agg(
                sort_array(
                    collect_list("transaction_struct"),
                    asc=False
                ).alias("sorted_transactions"),

                count("article_id").alias(
                    "user_total_purchases"
                )
            )
        )

        # Extract article IDs from sorted structures
        user_sequences = user_sequences.withColumn(
            "recent_article_ids",
            expr(
                f"transform("
                f"slice(sorted_transactions, 1, {max_sequence_length}), "
                f"x -> x.article_id)"
            )
        )

        user_sequences = user_sequences.drop(
            "sorted_transactions"
        )

        # Join with customer metadata
        customers_enriched = (
            customers_df
            .join(
                user_sequences,
                on="customer_id",
                how="left"
            )
            .fillna({
                "user_total_purchases": 0
            })
        )

        print(
            "[OK] Customer interaction sequences "
            "created using Spark."
        )

        return customers_enriched

    # --------------------------------------------------------
    # PANDAS
    # --------------------------------------------------------

    txns = transactions_df.copy()

    txns["t_dat"] = pd.to_datetime(
        txns["t_dat"],
        errors="coerce"
    )

    # Sort latest purchase first
    txns = txns.sort_values(
        by=["customer_id", "t_dat"],
        ascending=[True, False]
    )

    # Aggregate customer history
    user_sequences = (
        txns
        .groupby("customer_id")
        .agg(
            recent_article_ids=(
                "article_id",
                lambda x: list(x.head(max_sequence_length))
            ),

            user_total_purchases=(
                "article_id",
                "count"
            )
        )
        .reset_index()
    )

    # Merge with customers
    customers_enriched = customers_df.merge(
        user_sequences,
        on="customer_id",
        how="left"
    )

    # Cold-start users
    customers_enriched["user_total_purchases"] = (
        customers_enriched["user_total_purchases"]
        .fillna(0)
        .astype("int64")
    )

    customers_enriched["recent_article_ids"] = (
        customers_enriched["recent_article_ids"]
        .apply(
            lambda x:
            x if isinstance(x, list)
            else []
        )
    )

    print(
        f"[OK] Customer interaction sequences created."
    )

    return customers_enriched


# ============================================================
# 4. CONTEXT-ENRICHED INTERACTIONS
# ============================================================

def assemble_contextual_interactions(
    transactions_df,
    customers_df,
    articles_df
):

    """
    Combines transaction + customer + article information.

    This DataFrame becomes the main training dataset
    for the Two-Tower recommendation model.
    """

    print(
        "\n[INFO] Creating context-enriched interactions..."
    )

    # --------------------------------------------------------
    # REQUIRED CUSTOMER FEATURES
    # --------------------------------------------------------

    user_cols = [
        "customer_id",
        "age",
        "age_group",
        "club_member_status",
        "FN",
        "Active",
        "user_total_purchases"
    ]

    # Keep only columns that actually exist
    user_cols = [
        c for c in user_cols
        if c in customers_df.columns
    ]

    # --------------------------------------------------------
    # REQUIRED ARTICLE FEATURES
    # --------------------------------------------------------

    item_cols = [
        "article_id",
        "product_type_name",
        "product_group_name",
        "graphical_appearance_name",
        "colour_group_name",
        "department_name",
        "index_group_name",
        "garment_group_name",
        "pop_total_sales",
        "pop_30d_sales",
        "article_avg_price"
    ]

    item_cols = [
        c for c in item_cols
        if c in articles_df.columns
    ]

    # --------------------------------------------------------
    # PYSPARK
    # --------------------------------------------------------

    if HAS_PYSPARK and isinstance(
        transactions_df,
        SparkDataFrame
    ):

        users_subset = customers_df.select(user_cols)

        items_subset = articles_df.select(item_cols)

        enriched = (
            transactions_df
            .join(
                users_subset,
                on="customer_id",
                how="inner"
            )
            .join(
                items_subset,
                on="article_id",
                how="inner"
            )
        )

        print(
            f"[OK] Context-enriched interactions created "
            f"using Spark."
        )

        print(
            f"[INFO] Total feature columns: "
            f"{len(enriched.columns)}"
        )

        return enriched

    # --------------------------------------------------------
    # PANDAS
    # --------------------------------------------------------

    users_subset = customers_df[user_cols].copy()
    items_subset = articles_df[item_cols].copy()

    enriched = transactions_df.merge(
        users_subset,
        on="customer_id",
        how="inner"
    )

    enriched = enriched.merge(
        items_subset,
        on="article_id",
        how="inner"
    )

    print(
        f"[OK] Context-enriched interactions created "
        f"using Pandas."
    )

    print(
        f"[INFO] Total feature columns: "
        f"{len(enriched.columns)}"
    )

    return enriched


# ============================================================
# 5. COMPLETE FEATURE ENGINEERING PIPELINE
# ============================================================

def build_all_features(
    transactions_df,
    customers_df,
    articles_df,
    max_sequence_length=10
):

    """
    Runs the complete feature engineering pipeline.

    Returns:
        transactions_featured
        customers_featured
        articles_featured
        enriched_interactions
        max_date
    """

    print("\n" + "=" * 70)
    print("STARTING FEATURE ENGINEERING PIPELINE")
    print("=" * 70)

    # 1. Temporal features
    transactions_featured, max_date = (
        build_temporal_features(
            transactions_df
        )
    )

    # 2. Article popularity
    articles_featured = (
        build_article_popularity_features(
            transactions_featured,
            articles_df,
            max_date
        )
    )

    # 3. Customer sequences
    customers_featured = (
        build_user_interaction_sequences(
            transactions_featured,
            customers_df,
            max_sequence_length
        )
    )

    # 4. Contextual interactions
    enriched_interactions = (
        assemble_contextual_interactions(
            transactions_featured,
            customers_featured,
            articles_featured
        )
    )

    print("\n" + "=" * 70)
    print("FEATURE ENGINEERING COMPLETED")
    print("=" * 70)

    return (
        transactions_featured,
        customers_featured,
        articles_featured,
        enriched_interactions,
        max_date
    )


# ============================================================
# 6. TEST / EXECUTION
# ============================================================

if __name__ == "__main__":

    print("[INFO] Loading prepared datasets...")

    from dataprep import run_data_preparation

    (
        spark,
        articles_clean,
        customers_clean,
        transactions_clean,
        _
    ) = run_data_preparation()

    # Run complete feature engineering
    (
        transactions_featured,
        customers_featured,
        articles_featured,
        enriched_interactions,
        max_date
    ) = build_all_features(
        transactions_clean,
        customers_clean,
        articles_clean,
        max_sequence_length=10
    )

    print("\n[INFO] FEATURE ENGINEERING OUTPUT")
    print("-" * 70)

    # --------------------------------------------------------
    # SPARK OUTPUT
    # --------------------------------------------------------

    if HAS_PYSPARK and isinstance(
        transactions_featured,
        SparkDataFrame
    ):

        print(
            f"Transactions columns: "
            f"{len(transactions_featured.columns)}"
        )

        print(
            f"Customer columns: "
            f"{len(customers_featured.columns)}"
        )

        print(
            f"Article columns: "
            f"{len(articles_featured.columns)}"
        )

        print(
            f"Interaction columns: "
            f"{len(enriched_interactions.columns)}"
        )

        print("\nSample enriched interactions:")
        enriched_interactions.show(5, truncate=False)

    # --------------------------------------------------------
    # PANDAS OUTPUT
    # --------------------------------------------------------

    else:

        print(
            f"Transactions shape: "
            f"{transactions_featured.shape}"
        )

        print(
            f"Customers shape: "
            f"{customers_featured.shape}"
        )

        print(
            f"Articles shape: "
            f"{articles_featured.shape}"
        )

        print(
            f"Interactions shape: "
            f"{enriched_interactions.shape}"
        )

        print("\nSample enriched interactions:")
        print(
            enriched_interactions.head()
        )

    print("\n[OK] Feature engineering pipeline finished successfully.")
