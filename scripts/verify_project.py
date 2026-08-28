"""End-to-end project health check (no training).

Run:  python scripts/verify_project.py

Verifies the dataset, saved model artifacts, FAISS index, the serving
pipeline and the cache, then prints a PASS/FAIL summary.
"""

import sys
from pathlib import Path

# allow running as a plain script from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from src import config, faiss_index, utils

RESULTS = []


def check(name: str, fn):
    try:
        detail = fn()
        RESULTS.append((name, True, detail or ""))
    except Exception as exc:
        RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))


# ------------------------------------------------------------------ dataset
def check_dataset():
    if not config.DATA_ZIP.exists():
        raise FileNotFoundError("model_data_ready.zip missing from project root")
    from src import data_loader

    data_loader.ensure_data_extracted()
    if not all(p.exists() for p in [config.TRAIN_CSV, config.VALIDATION_CSV,
                                    config.TEST_CSV, config.USERS_CSV,
                                    config.ITEMS_CSV]):
        raise FileNotFoundError("extracted CSVs incomplete in data/model_data/")
    return "zip + extracted CSVs available"


check("DATASET", check_dataset)


# -------------------------------------------------------------------- model
def check_model():
    import keras

    if not (config.USER_TOWER_PATH.exists() and config.ITEM_TOWER_PATH.exists()):
        raise FileNotFoundError("towers not found; run python -m src.train")
    user_tower = keras.models.load_model(config.USER_TOWER_PATH)
    if user_tower.output_shape[-1] != config.EMBEDDING_DIM:
        raise ValueError("user tower output dim mismatch")
    return f"user/item towers load, {config.EMBEDDING_DIM}D output"


check("MODEL", check_model)


# --------------------------------------------------------------- embeddings
def check_embeddings():
    emb = np.load(config.ITEM_EMBEDDINGS_PATH)
    ids = np.load(config.ITEM_IDS_PATH)
    if emb.shape[0] != len(ids):
        raise ValueError("embedding/id count mismatch")
    norms = np.linalg.norm(emb, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise ValueError("item embeddings are not L2-normalized")
    return f"{emb.shape[0]} x {emb.shape[1]}D, L2-normalized"


check("EMBEDDINGS", check_embeddings)


# -------------------------------------------------------------------- faiss
def check_faiss():
    index = faiss_index.ANNIndex.load(item_ids=np.load(config.ITEM_IDS_PATH))
    if not faiss_index.FAISS_AVAILABLE:
        raise RuntimeError("faiss-cpu not importable (sklearn fallback would be used)")
    if index.size == 0:
        raise RuntimeError("faiss.index is empty")
    return f"FAISS IndexFlatIP with {index.size:,} vectors"


check("FAISS", check_faiss)


# ------------------------------------------------------------ recommendation
def check_recommendation():
    from src.cache import CacheClient
    from src.recommender import RecommendationEngine

    engine = RecommendationEngine(cache=CacheClient()).load()
    metrics = utils.load_json(config.METRICS_PATH)
    train = engine.train

    # a customer with plenty of history, whose validation item is known
    counts = train["customer_id"].value_counts()
    customer = counts.index[0]
    rec = engine.recommend(customer, k=10, use_cache=False)

    if len(rec["results"]) != 10:
        raise ValueError(f"expected 10 results, got {len(rec['results'])}")
    catalogue = set(engine.items["article_id"])
    missing = [r["article_id"] for r in rec["results"]
               if r["article_id"] not in catalogue]
    if missing:
        raise ValueError(f"recommended unknown articles: {missing[:3]}")
    bought = set(train.loc[train["customer_id"] == customer, "article_id"])
    overlap = [r["article_id"] for r in rec["results"] if r["article_id"] in bought]
    if overlap:
        raise ValueError(f"purchased filtering failed for: {overlap[:3]}")

    hit = engine.recommend(customer, k=10)
    if not hit.get("cache_hit"):
        raise ValueError("second identical request was not served from cache")

    recall10 = metrics.get("recall_at_10")
    return (f"10/10 valid results, purchased items excluded, cache HIT ok "
            f"(test Recall@10={recall10})")


check("RECOMMENDATION", check_recommendation)


# -------------------------------------------------------------------- cache
def check_cache():
    from src.cache import CacheClient

    cache = CacheClient()
    cache.set("verify:test", {"ok": True}, ttl=60)
    if cache.get("verify:test") != {"ok": True}:
        raise RuntimeError("cache round-trip failed")
    return f"{cache.status} (backend={cache.backend})"


check("CACHE", check_cache)


# ------------------------------------------------------------------- report
print("=" * 62)
print("StyleSense AI - project verification")
print("=" * 62)
for name, ok, detail in RESULTS:
    label = "PASS" if ok else "FAIL"
    print(f"{name}: {label}" + (f" - {detail}" if detail else ""))

cache_row = next(r for r in RESULTS if r[0] == "CACHE")
print(f"CACHE: {'REDIS' if 'Connected' in cache_row[2] else 'MEMORY FALLBACK'}")

all_ok = all(ok for _, ok, _ in RESULTS)
print("PROJECT STATUS:", "READY" if all_ok else "NOT READY")
sys.exit(0 if all_ok else 1)
