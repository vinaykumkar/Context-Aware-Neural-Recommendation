```python
import os
import shutil
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

REQUIRED_FILES = [
    "articles.csv",
    "customers.csv",
    "transactions_train.csv"
]

DATASET_NAME = "h-and-m-personalized-fashion-recommendations"


# ============================================================
# DIRECTORY HELPERS
# ============================================================

def get_project_directory():
    """
    Returns the project directory where this script is located.
    Falls back to the current working directory if __file__
    is unavailable.
    """
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def get_data_directory(target_dir=None):
    """
    Returns the target data directory.
    """

    if target_dir is not None:
        return Path(target_dir).resolve()

    return get_project_directory() / "data"


# ============================================================
# DATASET VALIDATION
# ============================================================

def get_missing_files(data_dir):
    """
    Returns a list of required dataset files that are missing.
    """

    return [
        filename
        for filename in REQUIRED_FILES
        if not (data_dir / filename).is_file()
    ]


def verify_dataset(data_dir):
    """
    Checks whether all required H&M dataset files are available.
    """

    missing_files = get_missing_files(data_dir)

    if not missing_files:
        print("[OK] All required H&M dataset files are available.")

        for filename in REQUIRED_FILES:
            file_path = data_dir / filename
            size_mb = file_path.stat().st_size / (1024 * 1024)

            print(
                f"   - {filename:<25} "
                f"{size_mb:.2f} MB"
            )

        return True

    print("[WARN] Required dataset files are missing:")

    for filename in missing_files:
        print(f"   - {filename}")

    return False


# ============================================================
# KAGGLE DOWNLOAD
# ============================================================

def download_from_kaggle(data_dir):
    """
    Downloads the H&M Personalized Fashion Recommendations
    dataset using KaggleHub.

    Returns:
        True  -> dataset downloaded successfully
        False -> download failed
    """

    print("\n[INFO] Attempting Kaggle dataset download...")
    print(f"[INFO] Dataset: {DATASET_NAME}")

    try:
        import kagglehub

    except ImportError:
        print("[WARN] kagglehub is not installed.")

        print(
            "[INFO] Install it using:"
        )

        print(
            "       pip install kagglehub"
        )

        return False

    try:
        download_path = kagglehub.competition_download(
            DATASET_NAME
        )

        download_path = Path(download_path)

        print(
            f"[OK] Kaggle dataset downloaded to:\n"
            f"     {download_path}"
        )

    except Exception as error:

        print(
            "[WARN] Kaggle dataset download failed."
        )

        print(
            f"[WARN] Reason: {error}"
        )

        return False

    # --------------------------------------------------------
    # Check whether KaggleHub downloaded files directly
    # --------------------------------------------------------

    if verify_dataset(data_dir):
        return True

    # --------------------------------------------------------
    # Search downloaded directory for required files
    # --------------------------------------------------------

    print(
        "\n[INFO] Searching downloaded dataset "
        "for required CSV files..."
    )

    if not download_path.exists():
        print(
            "[WARN] Kaggle download path does not exist."
        )
        return False

    found_files = {}

    for filename in REQUIRED_FILES:

        matches = list(
            download_path.rglob(filename)
        )

        if matches:
            found_files[filename] = matches[0]

    # --------------------------------------------------------
    # Copy discovered files to project data directory
    # --------------------------------------------------------

    if len(found_files) == len(REQUIRED_FILES):

        print(
            "[OK] All required CSV files were located."
        )

        for filename, source_path in found_files.items():

            destination_path = data_dir / filename

            try:
                shutil.copy2(
                    source_path,
                    destination_path
                )

                print(
                    f"   [COPIED] {filename}"
                )

            except Exception as error:

                print(
                    f"   [ERROR] Could not copy "
                    f"{filename}: {error}"
                )

                return False

        return verify_dataset(data_dir)

    # --------------------------------------------------------
    # Some files are still missing
    # --------------------------------------------------------

    print(
        "[WARN] Not all required dataset files "
        "were found after download."
    )

    for filename in REQUIRED_FILES:

        if filename not in found_files:
            print(
                f"   [MISSING] {filename}"
            )

    return False


# ============================================================
# SYNTHETIC DATA FALLBACK
# ============================================================

def generate_synthetic_dataset(data_dir):
    """
    Generates a synthetic dataset when the real Kaggle dataset
    cannot be downloaded.

    Requires create_sample_data.py in the project directory.
    """

    print(
        "\n[INFO] Initializing synthetic H&M dataset "
        "generator..."
    )

    try:
        from create_sample_data import generate_sample_dataset

    except ImportError:

        print(
            "[ERROR] create_sample_data.py could not be imported."
        )

        print(
            "[ERROR] Make sure create_sample_data.py exists "
            "in the project directory."
        )

        return False

    try:

        generated_path = generate_sample_dataset(
            str(data_dir)
        )

        print(
            f"[OK] Synthetic dataset generation completed."
        )

        if generated_path:
            print(
                f"[INFO] Generated data location: "
                f"{generated_path}"
            )

        # Verify the generated files
        if verify_dataset(data_dir):
            return True

        print(
            "[WARN] Synthetic dataset generator completed, "
            "but required files could not be verified."
        )

        return False

    except Exception as error:

        print(
            "[ERROR] Synthetic dataset generation failed."
        )

        print(
            f"[ERROR] Reason: {error}"
        )

        return False


# ============================================================
# MAIN DATASET FUNCTION
# ============================================================

def download_dataset(target_dir=None):
    """
    Prepare the H&M Personalized Fashion Recommendations dataset.

    Process:
        1. Create the data directory.
        2. Check whether the dataset already exists.
        3. Attempt to download the dataset from Kaggle.
        4. Validate downloaded files.
        5. Fall back to synthetic data if necessary.

    Returns:
        str or None:
            Path to the data directory on success,
            otherwise None.
    """

    print("\n" + "=" * 70)
    print("       H&M DATASET PREPARATION")
    print("       Context-Aware Neural Recommendation System")
    print("=" * 70)

    # --------------------------------------------------------
    # Determine data directory
    # --------------------------------------------------------

    data_dir = get_data_directory(target_dir)

    try:
        data_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    except Exception as error:

        print(
            f"[ERROR] Could not create data directory: {error}"
        )

        return None

    print(
        f"\n[INFO] Target data directory:\n"
        f"       {data_dir}"
    )

    # --------------------------------------------------------
    # Check existing dataset
    # --------------------------------------------------------

    print(
        "\n[INFO] Checking for existing dataset..."
    )

    if verify_dataset(data_dir):

        print(
            "\n[OK] Existing H&M dataset is ready."
        )

        print("=" * 70)

        return str(data_dir)

    # --------------------------------------------------------
    # Attempt Kaggle download
    # --------------------------------------------------------

    kaggle_success = download_from_kaggle(
        data_dir
    )

    if kaggle_success:

        print(
            "\n[SUCCESS] H&M dataset successfully prepared "
            "from Kaggle."
        )

        print("=" * 70)

        return str(data_dir)

    # --------------------------------------------------------
    # Synthetic dataset fallback
    # --------------------------------------------------------

    print(
        "\n[INFO] Kaggle dataset is unavailable."
    )

    print(
        "[INFO] Falling back to synthetic dataset generation."
    )

    synthetic_success = generate_synthetic_dataset(
        data_dir
    )

    if synthetic_success:

        print(
            "\n[SUCCESS] Synthetic H&M dataset is ready."
        )

        print("=" * 70)

        return str(data_dir)

    # --------------------------------------------------------
    # Complete failure
    # --------------------------------------------------------

    print(
        "\n[ERROR] Dataset preparation failed."
    )

    print(
        "[ACTION] Please check Kaggle access, "
        "kagglehub installation, and create_sample_data.py."
    )

    print("=" * 70)

    return None


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    result = download_dataset()

    if result is None:
        raise SystemExit(1)

    print(
        f"\n[READY] Dataset directory: {result}"
    )
```
