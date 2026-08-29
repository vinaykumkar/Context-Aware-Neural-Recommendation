"""
Day 4-6: Redis Feature Store Setup
====================================
Loads the trained model's user/item embeddings and biases (exported in
Day 1-3) into Redis, structured for low-latency lookups at inference
time. Uses Redis hashes for compact storage and binary-packed float32
vectors to minimize serialization overhead.
"""

import json
import time
import numpy as np
import redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=False)

# -----------------------------------------------------------------------
# 1. Load exported artifacts from Day 1-3
# -----------------------------------------------------------------------
with open("artifacts/model_card.json") as f:
    model_card = json.load(f)

user_embeddings = np.load("artifacts/user_embeddings.npy")
item_embeddings = np.load("artifacts/item_embeddings.npy")
user_bias = np.load("artifacts/user_bias.npy")
item_bias = np.load("artifacts/item_bias.npy")

print(f"Loaded embeddings: users={user_embeddings.shape}, items={item_embeddings.shape}")

# -----------------------------------------------------------------------
# 2. Key design
# -----------------------------------------------------------------------
# user:{id}       -> HASH { emb: <float32 bytes>, bias: <float>, updated_at: <ts> }
# item:{id}       -> HASH { emb: <float32 bytes>, bias: <float> }
# meta:model      -> HASH { model card fields, for serving-side sanity checks }
#
# Vectors are stored as raw float32 bytes (via .tobytes()) rather than
# JSON/text, which keeps payload size minimal and avoids per-request
# parsing overhead -- important for a low-latency serving path.

def vec_to_bytes(v: np.ndarray) -> bytes:
    return v.astype(np.float32).tobytes()

def bytes_to_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)

# -----------------------------------------------------------------------
# 3. Flush and bulk-load via pipeline (batched writes for throughput)
# -----------------------------------------------------------------------
r.flushdb()
start = time.time()

pipe = r.pipeline(transaction=False)
BATCH = 500

for uid in range(user_embeddings.shape[0]):
    pipe.hset(f"user:{uid}", mapping={
        "emb": vec_to_bytes(user_embeddings[uid]),
        "bias": float(user_bias[uid]),
        "updated_at": int(time.time()),
    })
    if uid % BATCH == 0:
        pipe.execute()
        pipe = r.pipeline(transaction=False)
pipe.execute()

pipe = r.pipeline(transaction=False)
for iid in range(item_embeddings.shape[0]):
    pipe.hset(f"item:{iid}", mapping={
        "emb": vec_to_bytes(item_embeddings[iid]),
        "bias": float(item_bias[iid]),
    })
    if iid % BATCH == 0:
        pipe.execute()
        pipe = r.pipeline(transaction=False)
pipe.execute()

r.hset("meta:model", mapping={k: str(v) for k, v in model_card.items()
                               if not isinstance(v, dict)})

load_time = time.time() - start
n_keys = r.dbsize()
print(f"Loaded {n_keys} keys into Redis in {load_time:.3f}s "
      f"({n_keys / load_time:.0f} writes/sec)")

# -----------------------------------------------------------------------
# 4. Verify: read back a sample user/item and measure lookup latency
# -----------------------------------------------------------------------
sample_uid, sample_iid = 42, 100

t0 = time.perf_counter()
raw = r.hgetall(f"user:{sample_uid}")
t1 = time.perf_counter()
fetched_vec = bytes_to_vec(raw[b"emb"])
original_vec = user_embeddings[sample_uid]

assert np.allclose(fetched_vec, original_vec, atol=1e-6), "Roundtrip mismatch!"
print(f"\nVerified roundtrip for user:{sample_uid} — vectors match exactly.")
print(f"Single HGETALL latency: {(t1 - t0) * 1000:.3f} ms")

# Benchmark: 1000 random single-key lookups (simulating per-request feature fetch)
rng = np.random.default_rng(0)
sample_uids = rng.integers(0, user_embeddings.shape[0], size=1000)
latencies = []
for uid in sample_uids:
    t0 = time.perf_counter()
    _ = r.hgetall(f"user:{int(uid)}")
    latencies.append((time.perf_counter() - t0) * 1000)

latencies = np.array(latencies)
print(f"\n1000-lookup benchmark (single-key HGETALL, user profile fetch):")
print(f"  mean   = {latencies.mean():.3f} ms")
print(f"  p50    = {np.percentile(latencies, 50):.3f} ms")
print(f"  p95    = {np.percentile(latencies, 95):.3f} ms")
print(f"  p99    = {np.percentile(latencies, 99):.3f} ms")

with open("artifacts/redis_benchmark.json", "w") as f:
    json.dump({
        "n_keys_loaded": n_keys,
        "bulk_load_time_sec": load_time,
        "bulk_load_writes_per_sec": n_keys / load_time,
        "lookup_mean_ms": float(latencies.mean()),
        "lookup_p50_ms": float(np.percentile(latencies, 50)),
        "lookup_p95_ms": float(np.percentile(latencies, 95)),
        "lookup_p99_ms": float(np.percentile(latencies, 99)),
        "n_lookups_benchmarked": len(latencies),
    }, f, indent=2)

# Save raw latencies for visualization later
np.save("artifacts/redis_lookup_latencies_ms.npy", latencies)
print("\nBenchmark results saved to artifacts/redis_benchmark.json")
