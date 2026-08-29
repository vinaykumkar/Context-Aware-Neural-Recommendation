import os
import json
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

def get_project_directory():
    """
    Returns the directory where this Python script is located.
    If __file__ is unavailable, uses the current working directory.
    """
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def get_processed_directory():
    """
    Returns the processed_data directory.
    """
    project_dir = get_project_directory()
    processed_dir = os.path.join(project_dir, "processed_data")

    return processed_dir


# ============================================================
# FILE CHECKING
# ============================================================

def check_file(file_path):
    """
    Checks whether a file exists and is not empty.
    """
    if not os.path.exists(file_path):
        return False

    if os.path.getsize(file_path) == 0:
        return False

    return True


# ============================================================
# JSON INSPECTION
# ============================================================

def inspect_vocabularies(vocab_path):
    """
    Reads and displays information from vocabularies.json.
    """

    print("\n" + "=" * 70)
    print("1. VOCABULARIES / SUMMARY STATISTICS")
    print("=" * 70)

    if not check_file(vocab_path):
        print("[WARNING] vocabularies.json was not found or is empty.")
        print(f"Expected location: {vocab_path}")
        return

    try:
        with open(vocab_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            print("[ERROR] vocabularies.json does not contain a valid JSON object.")
            return

        summary = data.get("summary_statistics", {})

        print("\nSummary Statistics:")
        print(
            f"   Total Unique Users    : "
            f"{summary.get('total_users', 0):,}"
        )

        print(
            f"   Total Unique Articles : "
            f"{summary.get('total_articles', 0):,}"
        )

        print(
            f"   Total Transactions    : "
            f"{summary.get('total_transactions', 0):,}"
        )

        categorical_vocabularies = data.get(
            "categorical_vocabularies",
            {}
        )

        print("\nCategorical Feature Vocabularies:")

        if not categorical_vocabularies:
            print("   No categorical vocabularies found.")
            return

        for category_name, values in categorical_vocabularies.items():

            if isinstance(values, list):
                number_of_values = len(values)
                examples = values[:3]
            else:
                number_of_values = 0
                examples = []

            print(
                f"   - {category_name:<30}: "
                f"{number_of_values:,} unique values | "
                f"Examples: {examples}"
            )

    except json.JSONDecodeError as error:
        print("[ERROR] Invalid JSON file.")
        print(f"Details: {error}")

    except Exception as error:
        print("[ERROR] Could not read vocabularies.json.")
        print(f"Details: {error}")


# ============================================================
# DATAFRAME LOADING
# ============================================================

def load_dataframe(file_path):
    """
    Safely loads a Parquet or CSV file.

    Returns:
        pandas.DataFrame or None
    """

    if not check_file(file_path):
        return None

    extension = os.path.splitext(file_path)[1].lower()

    try:

        if extension == ".parquet":
            try:
                return pd.read_parquet(file_path)

            except ImportError:
                print(
                    "[ERROR] Parquet support is not installed."
                )
                print(
                    "Install it using:"
                )
                print(
                    "pip install pyarrow"
                )
                return None

        elif extension == ".csv":
            return pd.read_csv(file_path)

        else:
            print(f"[ERROR] Unsupported file format: {extension}")
            return None

    except Exception as error:
        print(f"[ERROR] Could not load file:")
        print(f"       {file_path}")
        print(f"       Details: {error}")
        return None


# ============================================================
# COLUMN SELECTION
# ============================================================

def get_available_columns(dataframe, requested_columns):
    """
    Returns only columns that actually exist in the DataFrame.
    """

    return [
        column
        for column in requested_columns
        if column in dataframe.columns
    ]


# ============================================================
# CUSTOMER INSPECTION
# ============================================================

def inspect_customers(customers_path):
    """
    Displays customer DataFrame information.
    """

    print("\n" + "=" * 70)
    print("2. PROCESSED CUSTOMERS")
    print("=" * 70)

    if not check_file(customers_path):
        print("[WARNING] Customer Parquet file was not found.")
        print(f"Expected location: {customers_path}")
        return

    customers_df = load_dataframe(customers_path)

    if customers_df is None:
        return

    print("\nCustomer Dataset Information:")

    print(f"   Rows    : {len(customers_df):,}")
    print(f"   Columns : {len(customers_df.columns):,}")

    print("\nColumn Names:")
    print("   ", list(customers_df.columns))

    requested_columns = [
        "customer_id",
        "age",
        "age_group",
        "club_member_status",
        "Active",
        "FN",
        "recent_article_ids"
    ]

    sample_columns = get_available_columns(
        customers_df,
        requested_columns
    )

    print("\nSample Data:")

    if not sample_columns:
        print("   No requested preview columns were found.")
    else:
        print(
            customers_df[
                sample_columns
            ].head(5).to_string(index=False)
        )


# ============================================================
# ARTICLE INSPECTION
# ============================================================

def inspect_articles(articles_path, articles_csv_path):
    """
    Displays article DataFrame information.

    Uses Parquet first.
    If Parquet is unavailable, tries CSV.
    """

    print("\n" + "=" * 70)
    print("3. PROCESSED ARTICLES")
    print("=" * 70)

    articles_df = None
    source_file = None

    # Try Parquet first
    if check_file(articles_path):

        articles_df = load_dataframe(articles_path)

        if articles_df is not None:
            source_file = articles_path

    # If Parquet failed, try CSV
    if articles_df is None and check_file(articles_csv_path):

        print("[INFO] Trying CSV version of articles data...")

        articles_df = load_dataframe(articles_csv_path)

        if articles_df is not None:
            source_file = articles_csv_path

    if articles_df is None:

        print("[WARNING] No valid articles file was found.")

        print(
            f"Parquet expected at:\n"
            f"{articles_path}"
        )

        print(
            f"CSV expected at:\n"
            f"{articles_csv_path}"
        )

        return

    print(f"\nLoaded from: {source_file}")

    print("\nArticle Dataset Information:")

    print(f"   Rows    : {len(articles_df):,}")
    print(f"   Columns : {len(articles_df.columns):,}")

    print("\nColumn Names:")

    print(
        "   ",
        list(articles_df.columns)
    )

    requested_columns = [
        "article_id",
        "prod_name",
        "product_type_name",
        "garment_group_name",
        "pop_total_sales"
    ]

    sample_columns = get_available_columns(
        articles_df,
        requested_columns
    )

    print("\nSample Data:")

    if not sample_columns:
        print("   No requested preview columns were found.")
    else:
        print(
            articles_df[
                sample_columns
            ].head(5).to_string(index=False)
        )


# ============================================================
# TRANSACTION INSPECTION
# ============================================================

def inspect_transactions(txns_path):
    """
    Displays transaction DataFrame information.
    """

    print("\n" + "=" * 70)
    print("4. PROCESSED TRANSACTIONS")
    print("=" * 70)

    if not check_file(txns_path):
        print("[WARNING] Transaction Parquet file was not found.")
        print(f"Expected location: {txns_path}")
        return

    transactions_df = load_dataframe(txns_path)

    if transactions_df is None:
        return

    print("\nTransaction Dataset Information:")

    print(f"   Rows    : {len(transactions_df):,}")
    print(f"   Columns : {len(transactions_df.columns):,}")

    print("\nColumn Names:")

    print(
        "   ",
        list(transactions_df.columns)
    )

    requested_columns = [
        "t_dat",
        "customer_id",
        "article_id",
        "price",
        "day_of_week",
        "month"
    ]

    sample_columns = get_available_columns(
        transactions_df,
        requested_columns
    )

    print("\nSample Data:")

    if not sample_columns:
        print("   No requested preview columns were found.")
    else:
        print(
            transactions_df[
                sample_columns
            ].head(5).to_string(index=False)
        )


# ============================================================
# DIRECTORY INSPECTION
# ============================================================

def display_processed_files(processed_dir):
    """
    Displays all files available inside processed_data.
    """

    print("\n" + "=" * 70)
    print("AVAILABLE PROCESSED DATA FILES")
    print("=" * 70)

    if not os.path.exists(processed_dir):

        print("[ERROR] processed_data directory does not exist.")

        print(
            f"\nExpected directory:\n"
            f"{processed_dir}"
        )

        return False

    files = os.listdir(processed_dir)

    if not files:

        print("[WARNING] processed_data directory is empty.")
        return False

    print(f"\nDirectory: {processed_dir}")

    for filename in sorted(files):

        full_path = os.path.join(
            processed_dir,
            filename
        )

        if os.path.isfile(full_path):

            size = os.path.getsize(full_path)

            print(
                f"   - {filename:<40} "
                f"{size / (1024 * 1024):.2f} MB"
            )

    return True


# ============================================================
# MAIN INSPECTION FUNCTION
# ============================================================

def inspect_week1_results():

    print("\n" + "=" * 70)
    print("       WEEK 1 RESULT INSPECTOR")
    print("=" * 70)

    # Get directories
    project_dir = get_project_directory()
    processed_dir = get_processed_directory()

    print("\nProject Directory:")
    print(f"   {project_dir}")

    print("\nProcessed Data Directory:")
    print(f"   {processed_dir}")

    # Display available files
    directory_exists = display_processed_files(
        processed_dir
    )

    if not directory_exists:
        print("\n[STOP] No processed data directory available.")
        return

    # File paths
    vocab_path = os.path.join(
        processed_dir,
        "vocabularies.json"
    )

    customers_path = os.path.join(
        processed_dir,
        "customers_processed.parquet"
    )

    articles_path = os.path.join(
        processed_dir,
        "articles_processed.parquet"
    )

    articles_csv_path = os.path.join(
        processed_dir,
        "articles_processed.csv"
    )

    transactions_path = os.path.join(
        processed_dir,
        "transactions_processed.parquet"
    )

    # --------------------------------------------------------
    # Inspect each artifact
    # --------------------------------------------------------

    inspect_vocabularies(
        vocab_path
    )

    inspect_customers(
        customers_path
    )

    inspect_articles(
        articles_path,
        articles_csv_path
    )

    inspect_transactions(
        transactions_path
    )

    # --------------------------------------------------------
    # Final message
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("[OK] WEEK 1 INSPECTION COMPLETED")
    print("=" * 70)

    print(
        "\nProcessed data directory:"
    )

    print(
        f"   {processed_dir}"
    )

    print(
        "\nThe inspector completed without stopping because of "
        "a missing individual file."
    )

    print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    inspect_week1_results()
