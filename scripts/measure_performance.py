"""Measure serving-side performance (backend must be running on :8000).

Usage:  python scripts/measure_performance.py
"""
import sys
import time
import statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from backend.app.core.config import get_settings

BASE = "http://127.0.0.1:8000"


def timed(client: httpx.Client, path: str, n: int = 5) -> dict:
    times = []
    for _ in range(n):
        t = time.perf_counter()
        r = client.get(path)
        times.append((time.perf_counter() - t) * 1000)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
    return {"path": path, "min_ms": round(min(times), 1), "median_ms": round(statistics.median(times), 1), "max_ms": round(max(times), 1)}


def main() -> int:
    settings = get_settings()
    s = settings.serving_data_dir / "meta.json"
    dataset = __import__("json").loads(s.read_text())["dataset"] if s.exists() else {}

    with httpx.Client(base_url=BASE, timeout=30) as c:
        print("=== performance ===")
        t0 = time.perf_counter()
        r = c.get("/health")
        print(f"health: {r.status_code} (first request {(time.perf_counter() - t0) * 1000:.0f} ms)")

        for path in [
            "/api/customers?page=1&page_size=24",
            "/api/customers?page=2&page_size=24&q=be19",
            "/api/articles/popular?limit=12",
            "/api/stats",
        ]:
            print(timed(c, path, n=3))

        # pick three real customers: top purchaser + two from page 1
        ids = [i["customer_id"] for i in c.get("/api/customers?page_size=3&sort=purchase_count").json()["items"]]
        for cid in ids:
            print(timed(c, f"/api/customers/{cid}", n=5))
            print(timed(c, f"/api/customers/{cid}/history?limit=60", n=5))
            print(timed(c, f"/api/customers/{cid}/recommendations?count=10", n=5))

    def dir_mb(p: Path) -> float:
        return round(sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6, 1) if p.exists() else 0.0

    print("\n=== artifact sizes ===")
    print(f"serving_data:  {dir_mb(settings.serving_data_dir)} MB")
    print(f"recommendations: {dir_mb(settings.recommendations_dir)} MB")
    print(f"models:        {dir_mb(settings.models_dir)} MB")
    print(f"\ndataset build timing: {dataset.get('total_seconds', '?')} s (stage 1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
