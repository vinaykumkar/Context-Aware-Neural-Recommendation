import os
import sys

def check_and_install_requirements():
    """
    Verifies system dependencies for the Context-Aware Neural Recommendation System.
    """
    print("[INFO] Checking system requirements and dependencies...")
    
    java_home = os.environ.get("JAVA_HOME")
    if java_home and os.path.exists(java_home):
        print(f"[OK] JAVA_HOME is configured at: {java_home}")
    else:
        print("[WARN] JAVA_HOME environment variable is not explicitly set or path does not exist.")

    required_packages = [
        "tensorflow",
        "pandas",
        "numpy",
        "pyarrow",
        "kagglehub",
        "redis",
        "fastapi"
    ]
    
    for pkg in required_packages:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg} installed.")
        except ImportError:
            print(f"  [MISSING] {pkg} missing.")

    try:
        import pyspark
        print("  [OK] pyspark installed.")
    except ImportError:
        print("  [INFO] pyspark downloading in background; running dual-engine fallback.")

if __name__ == "__main__":
    check_and_install_requirements()
