"""CLI: run the complete offline pipeline (stages 1-3).

Usage:  python scripts/build_all.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pipeline.build_neighbors import main as neighbors_main
from scripts.pipeline.build_recs_duckdb import main as recs_main
from scripts.pipeline.build_serving import main as serving_main


def main() -> int:
    t0 = time.time()
    for name, fn in (("stage 1 - serving data", serving_main),
                     ("stage 2 - neighbor models", neighbors_main),
                     ("stage 3 - recommendations", recs_main)):
        print(f"\n########## {name} ##########", flush=True)
        rc = fn()
        if rc != 0:
            return rc
    print(f"\nAll stages complete in {time.time() - t0:,.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
