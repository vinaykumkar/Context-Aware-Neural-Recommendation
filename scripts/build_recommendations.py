"""CLI: generate per-customer candidate recommendations (stage 3).

DuckDB-backed, disk-spilling, per-bucket resumable implementation.

Usage:
  python scripts/build_recommendations.py            # all buckets (resumable)
  python scripts/build_recommendations.py 0,1,2      # specific buckets only
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pipeline.build_recs_duckdb import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
