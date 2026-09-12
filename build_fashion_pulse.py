"""CLI: build AURA Fashion Pulse signals (stage 7).

Usage:  python scripts/build_fashion_pulse.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pipeline.build_fashion_pulse import main

if __name__ == "__main__":
    sys.exit(main())
