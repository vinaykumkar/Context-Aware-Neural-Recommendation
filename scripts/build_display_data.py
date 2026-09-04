"""CLI: build the article display serving table (stage 1b).

Usage:  python scripts/build_display_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pipeline.build_display import main

if __name__ == "__main__":
    sys.exit(main())
