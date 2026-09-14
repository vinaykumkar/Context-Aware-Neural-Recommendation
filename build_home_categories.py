"""CLI: build home category cards (stage 6).

Usage:  python scripts/build_home_categories.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pipeline.build_home_categories import main

if __name__ == "__main__":
    sys.exit(main())
