"""Real retrieval evaluation: Recall@K and NDCG@K.

Flow (identical to serving):
    user row -> user tower -> user embedding -> FAISS search
    -> remove items the user already purchased in training
    -> Top-K products -> did the held-out item appear?

Metrics are computed from the actual validation/test interactions and are
never hardcoded. With a single held-out item per user, NDCG@K equals
1 / log2(rank + 2) when the item is retrieved at 0-based rank < K, else 0.
"""

import numpy as np

from src import config, model


def compute_user_embeddings(user_tower, user_arrays: dict, batch_size: int = 512) -> np.ndarray:
    outs = []
    n = len(next(iter(user_arrays.values())))
    for start in range(0, n, batch_size):
        feed = {k: v[start:start + batch_size] for k, v in user_arrays.items()}
        outs.append(user_tower.predict(feed, verbose=0))
    emb = np.vstack(outs)
    # towers already L2-normalize; renormalize to protect against float drift
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    return emb / np.clip(norms, 1e-12, None)


def evaluate_split(user_tower, ann_index, df, vocab, num_stats,
                   purchased: dict, ks=(5, 10, 20)) -> dict:
    """Evaluate retrieval metrics for one split dataframe."""
    user_arrays = model.user_feature_arrays(df, vocab, num_stats)
    user_emb = compute_user_embeddings(user_tower, user_arrays)

    n = len(df)
    held_out = df["article_id"].to_numpy()
    customer_ids = df["customer_id"].to_numpy()

    # Overfetch so items removed by the purchased-filter still leave K results.
    max_purchases = max((len(purchased.get(c, ())) for c in customer_ids), default=0)
    fetch_k = min(max(ks) + max_purchases + config.CANDIDATE_OVERFETCH, ann_index.size)
    idx, scores = ann_index.search(user_emb, fetch_k)

    hits = {k: 0 for k in ks}
    ndcg = {k: 0.0 for k in ks}
    evaluated = 0

    for row in range(n):
        bought = purchased.get(customer_ids[row], set())
        ranked = []
        for pos, item_idx in enumerate(idx[row]):
            if item_idx < 0:
                continue
            article_id = str(ann_index.item_ids[item_idx])
            if article_id in bought:
                continue
            ranked.append((article_id, float(scores[row][pos])))
            if len(ranked) >= max(ks):
                break
        evaluated += 1
        target = str(held_out[row])
        for k in ks:
            top = ranked[:k]
            ids = [a for a, _ in top]
            if target in ids:
                hits[k] += 1
                rank0 = ids.index(target)
                ndcg[k] += 1.0 / np.log2(rank0 + 2)

    metrics = {
        f"recall_at_{k}": round(hits[k] / evaluated, 4) for k in ks
    }
    metrics.update({
        f"ndcg_at_{k}": round(float(ndcg[k]) / evaluated, 4) for k in ks
    })
    metrics["num_interactions_evaluated"] = evaluated
    return metrics
