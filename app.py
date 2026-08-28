"""StyleSense AI - Streamlit demonstration app.

Presents the already-trained Two-Tower model. All recommendation logic
lives in src/recommender.py; this file only calls and displays it.

Run:  streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src import config, data_loader
from src.cache import CacheClient

st.set_page_config(page_title="StyleSense AI", page_icon=":shirt:",
                   layout="wide")

# ------------------------------------------------------------------ loading


@st.cache_resource(show_spinner="Loading trained model and FAISS index ...")
def load_engine():
    from src.recommender import RecommendationEngine

    cache = CacheClient()
    engine = RecommendationEngine(cache=cache).load()
    return engine


def load_metrics():
    if config.METRICS_PATH.exists():
        return json.loads(config.METRICS_PATH.read_text(encoding="utf-8"))
    return None


def load_summary():
    if config.DATA_SUMMARY_JSON.exists():
        return json.loads(config.DATA_SUMMARY_JSON.read_text(encoding="utf-8"))
    return {}


st.title("StyleSense AI")
st.markdown("#### Context-Aware Two-Tower Fashion Recommendation Engine")

# ------------------------------------------------------------ top status
try:
    engine = load_engine()
    model_error = None
except Exception as exc:  # artifacts missing or corrupted
    engine = None
    model_error = str(exc)

metrics = load_metrics()
summary = load_summary()

if engine is None:
    st.error("Model has not been trained yet. Run `python -m src.train` first.")
    st.caption(f"Details: {model_error}")
    st.stop()

ann_engine = "FAISS" if engine.ann.engine == "faiss" else "sklearn (fallback)"
cache_backend = engine.cache.backend
cache_status = engine.cache.status

badges = st.columns(4)
badges[0].success("Model: Loaded")
badges[1].info(f"Embedding: {engine.embedding_dim}D")
badges[2].info(f"ANN Engine: {ann_engine}")
if cache_backend == "Redis":
    badges[3].success("Cache: Redis Connected")
else:
    badges[3].warning("Cache: Memory Fallback")
st.divider()

# ------------------------------------------------------ pipeline display
left, right = st.columns(2)
with left:
    st.markdown("**Serving pipeline**")
    st.code(
        "CUSTOMER\n"
        "   |\n"
        "USER TOWER\n"
        "   |\n"
        "USER EMBEDDING (64D)\n"
        "   |\n"
        "FAISS SEARCH\n"
        "   |\n"
        "TOP-10 PRODUCTS",
        language=None,
    )
with right:
    st.markdown("**Indexing pipeline**")
    st.code(
        "PRODUCT FEATURES\n"
        "   |\n"
        "ITEM TOWER\n"
        "   |\n"
        "ITEM EMBEDDINGS (64D)\n"
        "   |\n"
        "FAISS INDEX",
        language=None,
    )

# ------------------------------------------------------ dataset overview
st.header("Project Overview")
train_rows = summary.get("train_rows", engine.model_config.get("train_rows"))
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Training Interactions", f"{train_rows:,}")
c2.metric("Validation Interactions", f"{summary.get('validation_rows', 0):,}")
c3.metric("Test Interactions", f"{summary.get('test_rows', 0):,}")
c4.metric("Customers", f"{summary.get('unique_users', 0):,}")
c5.metric("Products", f"{summary.get('unique_items', 0):,}")
c6.metric("Embedding Dimension", f"{engine.embedding_dim}D")
st.caption(
    "Dataset: H&M Personalized Fashion Recommendations (prepared subset), "
    "per-user temporal split with leakage-safe historical features. "
    f"FAISS index holds {engine.ann.size:,} item embeddings."
)

# ------------------------------------------------------ model performance
st.header("Model Performance")
st.caption("Measured on the held-out test split (each customer's last interaction).")
if metrics:
    test = metrics.get("test", metrics)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Recall@5", f"{test['recall_at_5']:.2%}")
    m2.metric("Recall@10", f"{test['recall_at_10']:.2%}")
    m3.metric("Recall@20", f"{test['recall_at_20']:.2%}")
    m4.metric("NDCG@10", f"{test['ndcg_at_10']:.2%}")
    m5.metric("NDCG@20", f"{test['ndcg_at_20']:.2%}")
else:
    st.warning("Model has not been trained yet. Run `python -m src.train`.")
st.divider()

# ------------------------------------------------------ customer selector
st.header("Customer Demo")

interaction_counts = engine.train["customer_id"].value_counts()
top_customers = interaction_counts.head(300).index.tolist()

example_path = config.DATA_DIR / "example_users.json"
default_customer = top_customers[0]
if example_path.exists():
    examples = json.loads(example_path.read_text(encoding="utf-8"))
    if examples and examples[0]["customer_id"] in top_customers:
        default_customer = examples[0]["customer_id"]

selected = st.selectbox(
    "Select Customer",
    top_customers,
    index=top_customers.index(default_customer),
    format_func=lambda cid: f"{cid}  ({interaction_counts[cid]} purchases)",
)

hist = engine._history.get(selected, pd.DataFrame())
users_row = engine.users[engine.users["customer_id"] == selected]
p1, p2, p3, p4 = st.columns(4)
p1.metric("Customer ID", selected[:12] + "...")
p2.metric("Age", int(users_row["age"].iloc[0]) if not users_row.empty else "n/a")
p3.metric("Historical Interactions", len(hist))
if not hist.empty:
    channels = hist["sales_channel_id"].mode()
    recent_date = pd.to_datetime(hist["t_dat"]).max().date()
    p4.metric("Preferred Channel / Last Purchase",
              f"Channel {int(channels.iloc[0])} / {recent_date}")
else:
    p4.metric("Preferred Channel", "n/a")

# ------------------------------------------------------ purchase history
st.subheader("Recent Purchase History")
if hist.empty:
    st.info("No purchase history available for this customer.")
else:
    recent = hist.tail(8).iloc[::-1]
    cols = st.columns(4)
    for i, (_, row) in enumerate(recent.iterrows()):
        meta = engine.items_by_id.loc[row["article_id"]]
        with cols[i % 4]:
            with st.container(border=True):
                st.markdown(f"**{meta['product_type_name']}**")
                st.caption(
                    f"{meta['product_group_name']} | {meta['colour_group_name']}\n\n"
                    f"{meta['garment_group_name']} | {meta['index_name']}")

# ------------------------------------------------------ recommendations
st.subheader("Generate Recommendations")
if st.button("Generate Recommendations", type="primary", use_container_width=True):
    with st.spinner("Running user tower + FAISS search ..."):
        st.session_state["recommendation"] = engine.recommend(selected, k=10)

rec = st.session_state.get("recommendation")
if rec and rec.get("customer_id") == selected:
    st.markdown(f"#### Top 10 Recommended Products for `{selected[:16]}...`")
    if rec.get("cache_hit"):
        st.info(f"Cache: HIT ({rec.get('cache_backend')})")
    else:
        st.success(f"Cache: MISS - freshly computed ({rec.get('cache_backend')})")

    for r in rec["results"]:
        with st.container(border=True):
            a, b, c = st.columns([1, 3, 2])
            a.markdown(f"### #{r['rank'] if 'rank' in r else rec['results'].index(r) + 1}")
            b.markdown(
                f"**{r['product_type_name']}**  ({r['article_id']})\n\n"
                f"{r['product_group_name']} | {r['colour_group_name']} | "
                f"{r['garment_group_name']}")
            c.markdown(
                f"Similarity: **{r['similarity_score']:.4f}**\n\n"
                f"Segment: {r['index_name']}")
            st.caption(f"Why: {r['why']}")

    # ------------------------------------------------ technical details
    with st.expander("Technical Details"):
        t1, t2 = st.columns(2)
        t1.markdown(
            f"**User embedding dimension:** {rec['user_embedding_dim']}\n\n"
            f"**First 8 embedding values:**\n\n"
            f"`{rec['user_embedding_preview']}`")
        t2.markdown(
            f"**ANN Engine:** {ann_engine}\n\n"
            f"**Items in FAISS index:** {engine.ann.size:,}\n\n"
            f"**FAISS candidates searched:** {rec['faiss_candidates_searched']}\n\n"
            f"**Purchased items removed:** {rec['already_purchased_removed']}\n\n"
            f"**Final Top-K:** {rec['final_top_k']}\n\n"
            f"**Cache:** {cache_status} | backend: {rec.get('cache_backend')}")
else:
    st.caption("Select a customer and click **Generate Recommendations** to run "
               "the live model + FAISS pipeline.")
st.divider()

# ------------------------------------------------------------ how it works
st.header("How It Works")
st.markdown(
    """
1. Customer and context features enter the **User Tower**.
2. The User Tower generates a **64-dimensional user embedding**.
3. Product information is converted into **item embeddings** by the Item Tower.
4. **FAISS** searches for product embeddings closest to the user embedding.
5. Products already purchased by the customer are **removed**.
6. The final **Top-10 recommendations** are displayed.
"""
)
st.caption(
    "StyleSense AI is a Two-Tower neural retrieval model. Retrieval is decided "
    "by embedding similarity; the short explanations shown on each card are "
    "generated afterwards from catalogue metadata, not by the neural network."
)
