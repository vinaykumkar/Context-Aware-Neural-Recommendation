"""
Day 7: Approximate Nearest Neighbor (ANN) Search for Candidate Retrieval
==========================================================================
Builds a FAISS ANN index over item embeddings (loaded from Redis, the
system of record at serving time) to enable fast top-K candidate
retrieval for a given user vector -- the core "retrieval" stage of a
two-stage recommender (retrieval -> ranking) architecture.

Compares:
  - Exact brute-force search (IndexFlatIP)          -- ground truth
  - Approximate search (IndexIVFFlat, inverted file) -- fast, used in prod
and reports recall@K of the approximate index against the exact one,
plus a latency benchmark for both.
"""

import json
import time
import numpy as np
import faiss
import redis

REDIS_HOST, REDIS_PORT = "localhost", 6379
K = 10                  # top-K candidates to retrieve
N_PROBE = 8              # IVF cells to search (speed/accuracy trade-off knob)
N_QUERIES = 500          # number of user queries to benchmark

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=False)

def bytes_to_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)

# -----------------------------------------------------------------------
# 1. Pull item embeddings from Redis (the feature store is the source of
#    truth at serving time -- the ANN index is rebuilt/refreshed from it)
# -----------------------------------------------------------------------
item_keys = sorted(r.keys("item:*"), key=lambda k: int(k.split(b":")[1]))
n_items = len(item_keys)
dim = None
item_vecs = []
item_biases = []
for key in item_keys:
    raw = r.hgetall(key)
    v = bytes_to_vec(raw[b"emb"])
    item_vecs.append(v)
    item_biases.append(float(raw[b"bias"]))
    if dim is None:
        dim = len(v)

item_matrix = np.vstack(item_vecs).astype(np.float32)
item_bias_arr = np.array(item_biases, dtype=np.float32)
print(f"Pulled {n_items} item vectors (dim={dim}) from Redis feature store.")

user_embeddings = np.load("artifacts/user_embeddings.npy")

# -----------------------------------------------------------------------
# 2. Build ANN index (IndexIVFFlat: inverted file index, approximate)
#    and an exact brute-force index for ground-truth comparison.
# -----------------------------------------------------------------------
n_clusters = max(8, int(np.sqrt(n_items)))  # heuristic: sqrt(N) clusters

quantizer = faiss.IndexFlatIP(dim)
ann_index = faiss.IndexIVFFlat(quantizer, dim, n_clusters, faiss.METRIC_INNER_PRODUCT)
ann_index.train(item_matrix)
ann_index.add(item_matrix)
ann_index.nprobe = N_PROBE

exact_index = faiss.IndexFlatIP(dim)
exact_index.add(item_matrix)

print(f"Built IVFFlat ANN index: {n_clusters} clusters, nprobe={N_PROBE}")
print(f"Built exact IndexFlatIP for ground-truth comparison")

# -----------------------------------------------------------------------
# 3. Candidate retrieval function (what the serving path calls per request)
# -----------------------------------------------------------------------
def retrieve_candidates(user_id: int, top_k: int = K, index=ann_index):
    """Fetch user vector from Redis, query the ANN index, return top-K item ids."""
    raw = r.hgetall(f"user:{user_id}")
    user_vec = bytes_to_vec(raw[b"emb"]).reshape(1, -1)
    scores, ids = index.search(user_vec, top_k)
    return ids[0], scores[0]

# Sanity check on one user
cand_ids, cand_scores = retrieve_candidates(user_id=42)
print(f"\nSample retrieval for user 42 -> top-{K} item ids: {cand_ids.tolist()}")

# -----------------------------------------------------------------------
# 4. Accuracy: recall@K of ANN vs. exact search
# -----------------------------------------------------------------------
rng = np.random.default_rng(0)
query_user_ids = rng.integers(0, user_embeddings.shape[0], size=N_QUERIES)
query_vecs = user_embeddings[query_user_ids].astype(np.float32)

_, ann_ids = ann_index.search(query_vecs, K)
_, exact_ids = exact_index.search(query_vecs, K)

recalls = []
for a, e in zip(ann_ids, exact_ids):
    overlap = len(set(a.tolist()) & set(e.tolist()))
    recalls.append(overlap / K)
recall_at_k = float(np.mean(recalls))
print(f"\nRecall@{K} of ANN (IVFFlat, nprobe={N_PROBE}) vs. exact search: {recall_at_k:.3f}")

# -----------------------------------------------------------------------
# 5. Latency benchmark: ANN vs. exact brute-force, end-to-end incl. Redis fetch
# -----------------------------------------------------------------------
def benchmark_retrieval(index, n=N_QUERIES):
    latencies = []
    for uid in query_user_ids[:n]:
        t0 = time.perf_counter()
        _ = retrieve_candidates(int(uid), top_k=K, index=index)
        latencies.append((time.perf_counter() - t0) * 1000)
    return np.array(latencies)

ann_latencies = benchmark_retrieval(ann_index)
exact_latencies = benchmark_retrieval(exact_index)

print(f"\nEnd-to-end retrieval latency (Redis fetch + ANN search), n={N_QUERIES}:")
print(f"  ANN   mean={ann_latencies.mean():.4f} ms  p95={np.percentile(ann_latencies,95):.4f} ms  p99={np.percentile(ann_latencies,99):.4f} ms")
print(f"  Exact mean={exact_latencies.mean():.4f} ms  p95={np.percentile(exact_latencies,95):.4f} ms  p99={np.percentile(exact_latencies,99):.4f} ms")

speedup = exact_latencies.mean() / ann_latencies.mean()
print(f"\nANN speedup over exact search: {speedup:.2f}x (at recall@{K}={recall_at_k:.3f})")

# -----------------------------------------------------------------------
# 6. nprobe sweep: accuracy/latency trade-off curve
# -----------------------------------------------------------------------
nprobe_values = [1, 2, 4, 8, 16, 32, n_clusters]
sweep_results = []
for nprobe in nprobe_values:
    ann_index.nprobe = nprobe
    _, ann_ids_sweep = ann_index.search(query_vecs, K)
    recalls_sweep = [len(set(a.tolist()) & set(e.tolist())) / K
                      for a, e in zip(ann_ids_sweep, exact_ids)]
    lat = benchmark_retrieval(ann_index, n=200)
    sweep_results.append({
        "nprobe": nprobe,
        "recall_at_k": float(np.mean(recalls_sweep)),
        "mean_latency_ms": float(lat.mean()),
    })
    print(f"nprobe={nprobe:3d}  recall@{K}={np.mean(recalls_sweep):.3f}  "
          f"mean_latency={lat.mean():.4f} ms")

ann_index.nprobe = N_PROBE  # restore default

# -----------------------------------------------------------------------
# 7. Save everything for reporting
# -----------------------------------------------------------------------
faiss.write_index(ann_index, "artifacts/ann_index.faiss")
faiss.write_index(exact_index, "artifacts/exact_index.faiss")

results = {
    "n_items_indexed": n_items,
    "embedding_dim": dim,
    "n_clusters": n_clusters,
    "nprobe_used": N_PROBE,
    "top_k": K,
    "recall_at_k": recall_at_k,
    "ann_latency_mean_ms": float(ann_latencies.mean()),
    "ann_latency_p95_ms": float(np.percentile(ann_latencies, 95)),
    "ann_latency_p99_ms": float(np.percentile(ann_latencies, 99)),
    "exact_latency_mean_ms": float(exact_latencies.mean()),
    "exact_latency_p95_ms": float(np.percentile(exact_latencies, 95)),
    "exact_latency_p99_ms": float(np.percentile(exact_latencies, 99)),
    "speedup_factor": float(speedup),
    "nprobe_sweep": sweep_results,
}
with open("artifacts/ann_benchmark.json", "w") as f:
    json.dump(results, f, indent=2)

np.save("artifacts/ann_latencies_ms.npy", ann_latencies)
np.save("artifacts/exact_latencies_ms.npy", exact_latencies)

print("\nANN index + benchmark results saved to /artifacts.")
