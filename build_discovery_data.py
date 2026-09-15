"""CLI: build customer discovery serving table (stage 5).

Usage:  python scripts/build_discovery_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pipeline.build_discovery import main

if __name__ == "__main__":
    sys.exit(main())
