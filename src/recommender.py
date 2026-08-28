"""Recommendation service: customer -> user tower -> embedding -> FAISS -> Top-K.

Loads the saved training artifacts (no retraining). The serving flow is:

    customer_id
        -> build customer/context features (users.csv + purchase history +
           current date context)
        -> user tower -> 64-dim user embedding (L2 normalized)
        -> FAISS search (over-fetch candidates)
        -> remove items the customer already purchased
        -> Top-K products -> join item metadata -> deterministic explanations
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src import config, data_loader, faiss_index, model, utils
from src.cache import CacheClient


class RecommendationEngine:
    """Loads saved artifacts once, then serves real recommendations."""

    def __init__(self, cache: CacheClient = None):
        self.cache = cache or CacheClient()
        self.loaded = False

    # ---------------------------------------------------------- loading
    def load(self) -> "RecommendationEngine":
        cfg = utils.load_json(config.MODEL_CONFIG_PATH)
        self.model_config = cfg
        self.embedding_dim = cfg["embedding_dim"]
        self.num_stats = cfg["numeric_stats"]

        self.vocab = {name: utils.load_vocabulary(name) for name in
                      cfg["user_categorical"] + cfg["item_categorical"]}

        import keras
        self.user_tower = keras.models.load_model(config.USER_TOWER_PATH)

        self.item_embeddings = np.load(config.ITEM_EMBEDDINGS_PATH)
        self.item_ids = np.load(config.ITEM_IDS_PATH).astype(str)
        self.ann = faiss_index.ANNIndex.load(item_ids=self.item_ids)

        # sklearn fallback needs rebuilding from the saved embeddings
        if not faiss_index.FAISS_AVAILABLE:
            self.ann.build(self.item_embeddings, self.item_ids)

        self.items = data_loader.load_items()
        self.users = data_loader.load_users()
        self.train = data_loader.load_train()

        self.items_by_id = self.items.set_index("article_id")
        self._history = {cid: g.sort_values("t_dat") for cid, g in
                         self.train.groupby("customer_id")}
        # "now" for inference-time historical features = end of training data
        self._history_end = pd.to_datetime(self.train["t_dat"]).max()
        self._default_channel = int(self.train["sales_channel_id"].mode().iloc[0])

        self.loaded = True
        return self

    # ------------------------------------------------- customer features
    def _customer_features(self, customer_id: str) -> pd.DataFrame:
        """One-row feature frame for the user tower (same columns as training)."""
        users_row = self.users[self.users["customer_id"] == customer_id]
        if users_row.empty:
            raise ValueError(f"Unknown customer_id: {customer_id}")

        hist = self._history.get(customer_id)
        end = self._history_end

        if hist is None or len(hist) == 0:
            num = dict.fromkeys(
                ["historical_purchase_count", "historical_unique_articles",
                 "historical_total_spend", "historical_average_price",
                 "historical_recency_days", "historical_purchase_frequency",
                 "historical_recent_purchase_count_30d", "has_history"], 0.0)
        else:
            dates = pd.to_datetime(hist["t_dat"])
            span_days = max((dates.max() - dates.min()).days, 1)
            num = {
                "historical_purchase_count": float(len(hist)),
                "historical_unique_articles": float(hist["article_id"].nunique()),
                "historical_total_spend": float(hist["price"].sum()),
                "historical_average_price": float(hist["price"].mean()),
                "historical_recency_days": float((end - dates.max()).days),
                "historical_purchase_frequency": float(len(hist) / span_days),
                "historical_recent_purchase_count_30d":
                    float((dates > end - timedelta(days=30)).sum()),
                "has_history": 1.0,
            }

        row = {
            "customer_id": customer_id,
            "age": float(users_row["age"].iloc[0]),
            "active": int(users_row["active"].iloc[0]),
            "club_member_status": str(users_row["club_member_status"].iloc[0]),
            "fashion_news_frequency": str(users_row["fashion_news_frequency"].iloc[0]),
            # context-aware part: recommendations adapt to the current date
            "sales_channel_id": self._default_channel,
            "purchase_month": end.month,  # season seen during training
            "purchase_day_of_week": datetime.now().strftime("%A"),
            **data_loader.history_favourites(hist),
            **num,
        }
        return pd.DataFrame([row])

    # ---------------------------------------------------------- recommend
    def recommend(self, customer_id: str, k: int = config.DEFAULT_K,
                  use_cache: bool = True) -> dict:
        if not self.loaded:
            self.load()

        cache_key = self.cache.recommendations_key(customer_id, k)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                cached["cache_hit"] = True
                cached["cache_backend"] = self.cache.backend
                return cached

        feats = self._customer_features(customer_id)
        arrays = model.user_feature_arrays(feats, self.vocab, self.num_stats)
        user_emb = np.asarray(self.user_tower.predict(arrays, verbose=0),
                              dtype="float32")
        user_emb /= np.clip(np.linalg.norm(user_emb, axis=1, keepdims=True),
                            1e-12, None)

        bought = set(self._history.get(customer_id, pd.DataFrame())
                     .get("article_id", pd.Series(dtype=str)).astype(str))
        fetch_k = min(k + len(bought) + config.CANDIDATE_OVERFETCH,
                      self.ann.size)
        idx, scores = self.ann.search(user_emb, fetch_k)

        results = []
        hist = self._history.get(customer_id, pd.DataFrame())
        for item_idx, score in zip(idx[0], scores[0]):
            if item_idx < 0:
                continue
            article_id = str(self.item_ids[item_idx])
            if article_id in bought:
                continue
            meta = self.items_by_id.loc[article_id]
            results.append({
                "article_id": article_id,
                "product_type_name": str(meta["product_type_name"]),
                "product_group_name": str(meta["product_group_name"]),
                "colour_group_name": str(meta["colour_group_name"]),
                "department_name": str(meta["department_name"]),
                "garment_group_name": str(meta["garment_group_name"]),
                "index_name": str(meta["index_name"]),
                "similarity_score": round(float(score), 4),
                "why": self._explain(article_id, hist),
            })
            if len(results) >= k:
                break

        payload = {
            "customer_id": customer_id,
            "results": results,
            "user_embedding_preview": [round(float(v), 4) for v in user_emb[0][:8]],
            "user_embedding_dim": int(user_emb.shape[1]),
            "faiss_candidates_searched": int(fetch_k),
            "final_top_k": len(results),
            "already_purchased_removed": len(bought),
            "cache_hit": False,
            "cache_backend": self.cache.backend,
        }

        # cache user features + recommendation payload for the demo
        self.cache.set(self.cache.user_features_key(customer_id),
                       feats.drop(columns=["purchase_day_of_week"]).iloc[0].to_dict())
        self.cache.set(cache_key, payload, ttl=config.REDIS_TTL_SECONDS)
        return payload

    # ------------------------------------------------------- explanations
    def _explain(self, article_id: str, hist: pd.DataFrame) -> str:
        """Deterministic, post-hoc metadata comparison.

        NOTE: retrieval itself is decided purely by the neural embeddings;
        this explanation is generated afterwards from catalogue metadata and
        the customer's purchase history (no LLM involved).
        """
        if hist is None or len(hist) == 0:
            return "New customer profile - retrieved by learned embedding similarity."

        meta = self.items_by_id.loc[article_id]
        top_colours = set(hist["colour_group_name"].value_counts().head(3).index)
        top_types = set(hist["product_type_name"].value_counts().head(5).index)
        top_groups = set(hist["garment_group_name"].value_counts().head(3).index)

        if meta["colour_group_name"] in top_colours:
            return (f"Matches the customer's frequently purchased "
                    f"{meta['colour_group_name']} fashion products.")
        if meta["product_type_name"] in top_types:
            return ("Similar to products previously purchased by this customer "
                    f"({meta['product_type_name']}).")
        if meta["garment_group_name"] in top_groups:
            return (f"Related to the customer's preferred garment category "
                    f"({meta['garment_group_name']}).")
        return "Close to this customer's profile in the learned embedding space."
