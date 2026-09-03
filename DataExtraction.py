import os
import sys

def download_dataset(target_dir=None):
    """
    Downloads and extracts the H&M Personalized Fashion Recommendations dataset from Kaggle.
    If Kaggle API credentials are not set, generates a synthetic dataset matching the schema.
    """
    if target_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(base_dir, "data")
        
    os.makedirs(target_dir, exist_ok=True)
    print(f"[INFO] Target data directory set to: {target_dir}")
    
    # Verify if CSV files already exist
    required_files = ["articles.csv", "customers.csv", "transactions_train.csv"]
    existing_files = [f for f in required_files if os.path.exists(os.path.join(target_dir, f))]
    
    if len(existing_files) == len(required_files):
        print("[OK] All required dataset files are present:")
        for f in required_files:
            print(f"   - {os.path.join(target_dir, f)}")
        return target_dir

    print("[INFO] Attempting Kaggle dataset download (h-and-m-personalized-fashion-recommendations)...")
    try:
        import kagglehub
        download_path = kagglehub.competition_download(
            'h-and-m-personalized-fashion-recommendations',
            output_dir=target_dir
        )
        print("\n[OK] Competition dataset extracted to:", download_path)
        return download_path
    except Exception as e:
        print(f"\n[WARN] Kaggle download unavailable ({e}).")
        print("[INFO] Initializing synthetic H&M dataset generator for pipeline execution...")
        from create_sample_data import generate_sample_dataset
        return generate_sample_dataset(target_dir)

if __name__ == "__main__":
    download_dataset()
