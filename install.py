```python
import os
import sys
import importlib
import subprocess


# ============================================================
# CONFIGURATION
# ============================================================

REQUIRED_PACKAGES = {
    "tensorflow": "tensorflow",
    "pandas": "pandas",
    "numpy": "numpy",
    "pyarrow": "pyarrow",
    "kagglehub": "kagglehub",
    "redis": "redis",
    "fastapi": "fastapi",
    "pyspark": "pyspark"
}


# ============================================================
# DISPLAY HELPERS
# ============================================================

def print_header(title):
    """Display a formatted section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# PYTHON VERSION CHECK
# ============================================================

def check_python_version():
    """Check whether the installed Python version is supported."""

    print_header("PYTHON VERSION CHECK")

    major = sys.version_info.major
    minor = sys.version_info.minor
    micro = sys.version_info.micro

    print(f"[INFO] Python version: {major}.{minor}.{micro}")

    if (major, minor) >= (3, 9):
        print("[OK] Python version is supported.")
        return True

    print("[WARN] Python 3.9 or newer is recommended.")
    return False


# ============================================================
# JAVA CHECK
# ============================================================

def check_java():
    """
    Check JAVA_HOME and Java installation.
    Java is required for Apache Spark.
    """

    print_header("JAVA / SPARK ENVIRONMENT CHECK")

    java_home = os.environ.get("JAVA_HOME")

    if java_home:
        print(f"[INFO] JAVA_HOME: {java_home}")

        if os.path.exists(java_home):
            print("[OK] JAVA_HOME path exists.")
        else:
            print("[WARN] JAVA_HOME is set, but the path does not exist.")
    else:
        print("[WARN] JAVA_HOME is not set.")

    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            version_output = (
                result.stderr.strip()
                if result.stderr
                else result.stdout.strip()
            )

            first_line = version_output.splitlines()[0]

            print(f"[OK] Java is available: {first_line}")
            return True

        print("[WARN] Java command was found but could not be executed.")
        return False

    except FileNotFoundError:
        print("[WARN] Java is not installed or is not available in PATH.")
        return False

    except Exception as error:
        print(f"[WARN] Could not verify Java: {error}")
        return False


# ============================================================
# PACKAGE VERSION
# ============================================================

def get_package_version(module_name):
    """
    Get the installed version of a Python package.
    """

    try:
        module = importlib.import_module(module_name)

        version = getattr(module, "__version__", None)

        if version:
            return version

        try:
            from importlib.metadata import version as get_version

            return get_version(module_name)

        except Exception:
            return "version unavailable"

    except Exception:
        return None


# ============================================================
# PACKAGE CHECK
# ============================================================

def check_package(package_name, module_name):
    """
    Check whether a Python package can be imported.
    """

    try:
        importlib.import_module(module_name)

        version = get_package_version(module_name)

        if version:
            print(
                f"  [OK] {package_name:<12} "
                f"installed (version: {version})"
            )
        else:
            print(
                f"  [OK] {package_name:<12} "
                f"installed"
            )

        return True

    except ImportError:
        print(
            f"  [MISSING] {package_name:<12} "
            f"not installed"
        )

        return False

    except Exception as error:
        print(
            f"  [ERROR] {package_name:<12} "
            f"could not be imported"
        )

        print(f"          Reason: {error}")

        return False


# ============================================================
# PYTHON DEPENDENCY CHECK
# ============================================================

def check_python_dependencies():
    """
    Check all required Python packages.
    """

    print_header("PYTHON DEPENDENCY CHECK")

    installed_packages = []
    missing_packages = []
    failed_packages = []

    for package_name, module_name in REQUIRED_PACKAGES.items():

        try:
            importlib.import_module(module_name)

            version = get_package_version(module_name)

            if version:
                print(
                    f"  [OK] {package_name:<12} "
                    f"installed (version: {version})"
                )
            else:
                print(
                    f"  [OK] {package_name:<12} "
                    f"installed"
                )

            installed_packages.append(package_name)

        except ImportError:
            print(
                f"  [MISSING] {package_name:<12} "
                f"not installed"
            )

            missing_packages.append(package_name)

        except Exception as error:
            print(
                f"  [ERROR] {package_name:<12} "
                f"import failed"
            )

            print(f"           Reason: {error}")

            failed_packages.append(package_name)

    return (
        installed_packages,
        missing_packages,
        failed_packages
    )


# ============================================================
# INSTALL MISSING PACKAGES
# ============================================================

def show_install_command(missing_packages):
    """
    Display the pip command required to install missing packages.
    """

    if not missing_packages:
        return

    print_header("MISSING DEPENDENCIES")

    print("[INFO] The following packages are missing:")

    for package in missing_packages:
        print(f"  - {package}")

    print("\n[INFO] Install them using:")

    print(
        "\npip install "
        + " ".join(missing_packages)
    )


# ============================================================
# SPARK-SPECIFIC CHECK
# ============================================================

def check_pyspark_environment():
    """
    Perform additional checks for PySpark.
    """

    print_header("PYSPARK CHECK")

    try:
        import pyspark

        spark_version = getattr(
            pyspark,
            "__version__",
            "unknown"
        )

        print(
            f"[OK] PySpark is installed "
            f"(version: {spark_version})."
        )

        java_home = os.environ.get("JAVA_HOME")

        if java_home and os.path.exists(java_home):
            print("[OK] JAVA_HOME is available for Spark.")
        else:
            print(
                "[WARN] JAVA_HOME is not properly configured. "
                "Spark may fail to start."
            )

        return True

    except ImportError:
        print("[MISSING] PySpark is not installed.")

        print("\n[INFO] Install PySpark using:")

        print("\npip install pyspark")

        return False

    except Exception as error:
        print(
            f"[ERROR] PySpark check failed: {error}"
        )

        return False


# ============================================================
# SYSTEM REQUIREMENT CHECK
# ============================================================

def check_and_install_requirements():
    """
    Verify system and Python dependencies for the
    Context-Aware Neural Recommendation System.
    """

    print("\n" + "=" * 70)
    print("   CONTEXT-AWARE NEURAL RECOMMENDATION SYSTEM")
    print("   SYSTEM REQUIREMENT & DEPENDENCY CHECKER")
    print("=" * 70)

    print("\n[INFO] Starting environment verification...")

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    python_ok = check_python_version()

    # --------------------------------------------------------
    # Java
    # --------------------------------------------------------

    java_ok = check_java()

    # --------------------------------------------------------
    # Python packages
    # --------------------------------------------------------

    (
        installed_packages,
        missing_packages,
        failed_packages
    ) = check_python_dependencies()

    # --------------------------------------------------------
    # PySpark
    # --------------------------------------------------------

    pyspark_ok = check_pyspark_environment()

    # --------------------------------------------------------
    # Missing package instructions
    # --------------------------------------------------------

    show_install_command(missing_packages)

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print_header("ENVIRONMENT CHECK SUMMARY")

    print(
        f"[INFO] Python environment : "
        f"{'READY' if python_ok else 'CHECK REQUIRED'}"
    )

    print(
        f"[INFO] Java environment   : "
        f"{'READY' if java_ok else 'CHECK REQUIRED'}"
    )

    print(
        f"[INFO] Packages installed  : "
        f"{len(installed_packages)}/{len(REQUIRED_PACKAGES)}"
    )

    print(
        f"[INFO] Packages missing    : "
        f"{len(missing_packages)}"
    )

    print(
        f"[INFO] Import failures     : "
        f"{len(failed_packages)}"
    )

    print(
        f"[INFO] PySpark environment : "
        f"{'READY' if pyspark_ok else 'CHECK REQUIRED'}"
    )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    if (
        python_ok
        and java_ok
        and not missing_packages
        and not failed_packages
        and pyspark_ok
    ):
        print(
            "[SUCCESS] All required dependencies "
            "are available."
        )

        print(
            "[READY] The development environment "
            "is ready for the project."
        )

    else:
        print(
            "[WARNING] Environment setup is incomplete."
        )

        print(
            "[ACTION] Review the warnings above "
            "and install/configure the missing dependencies."
        )

    print("=" * 70)

    return (
        python_ok
        and java_ok
        and not missing_packages
        and not failed_packages
        and pyspark_ok
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    check_and_install_requirements()
```
