"""Central configuration for StyleSense AI.

All paths are relative to the project root so the project works after a
plain `git clone` on any machine. No absolute paths anywhere.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- paths
DATA_ZIP = PROJECT_ROOT / "model_data_ready.zip"
DATA_DIR = PROJECT_ROOT / "data" / "model_data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
VOCAB_DIR = ARTIFACTS_DIR / "vocabularies"

TRAIN_CSV = DATA_DIR / "train.csv"
VALIDATION_CSV = DATA_DIR / "validation.csv"
TEST_CSV = DATA_DIR / "test.csv"
USERS_CSV = DATA_DIR / "users.csv"
ITEMS_CSV = DATA_DIR / "items.csv"
DATA_SUMMARY_JSON = DATA_DIR / "data_summary.json"

USER_TOWER_PATH = ARTIFACTS_DIR / "user_tower.keras"
ITEM_TOWER_PATH = ARTIFACTS_DIR / "item_tower.keras"
ITEM_EMBEDDINGS_PATH = ARTIFACTS_DIR / "item_embeddings.npy"
ITEM_IDS_PATH = ARTIFACTS_DIR / "item_ids.npy"
FAISS_INDEX_PATH = ARTIFACTS_DIR / "faiss.index"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
MODEL_CONFIG_PATH = ARTIFACTS_DIR / "model_config.json"

# ---------------------------------------------------------------- model
SEED = 42
EMBEDDING_DIM = 64          # final output dim of BOTH towers (must match)
ID_EMBEDDING_DIM = 8        # small on purpose: prevents pure ID memorization
CAT_EMBEDDING_DIM = 8       # embedding width for small categorical features
HIDDEN_UNITS = 128          # first dense layer of each tower
TEMPERATURE = 0.15           # softmax temperature for in-batch contrastive loss
BATCH_SIZE = 256
EPOCHS = 40
LEARNING_RATE = 3e-3
EARLY_STOP_PATIENCE = 8
DROPOUT = 0.2

# User tower features.
# Identity: customer_id. Numeric: normalized user/context numbers.
# Categorical: club/status + context (channel, month, day-of-week)
# + content-affinity favourites computed from prior purchases.
USER_CATEGORICAL = [
    "customer_id",
    "club_member_status",
    "fashion_news_frequency",
    "sales_channel_id",
    "purchase_month",
    "purchase_day_of_week",
    "fav_colour_group_name",
    "fav_garment_group_name",
    "fav_product_group_name",
]
USER_NUMERIC = [
    "age",
    "active",
    "historical_purchase_count",
    "historical_unique_articles",
    "historical_total_spend",
    "historical_average_price",
    "historical_recency_days",
    "historical_purchase_frequency",
    "historical_recent_purchase_count_30d",
    "has_history",
]

# Item tower features. Identity: article_id + core catalogue metadata.
ITEM_CATEGORICAL = [
    "article_id",
    "product_type_name",
    "product_group_name",
    "colour_group_name",
    "garment_group_name",
    "index_name",
]
ITEM_NUMERIC = []  # kept empty: popularity enters via logQ correction instead

# ---------------------------------------------------------------- serving
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_TTL_SECONDS = 3600    # recommendation cache TTL
DEFAULT_K = 10              # Top-K recommendations
CANDIDATE_OVERFETCH = 50    # fetch extra FAISS candidates before filtering
