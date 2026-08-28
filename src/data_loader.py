"""Dataset loading.

Extracts model_data_ready.zip into data/model_data/ automatically when the
CSV files are missing, then loads the prepared train/validation/test split.
No re-splitting, no re-preprocessing: the data is used exactly as prepared.
"""

import zipfile

import pandas as pd

from src import config


def ensure_data_extracted() -> None:
    """Extract the dataset ZIP if the expected CSVs are not on disk yet."""
    needed = [config.TRAIN_CSV, config.VALIDATION_CSV, config.TEST_CSV,
              config.USERS_CSV, config.ITEMS_CSV]
    if all(p.exists() for p in needed):
        return
    if not config.DATA_ZIP.exists():
        raise FileNotFoundError(
            f"Dataset ZIP not found at {config.DATA_ZIP}. "
            "Put model_data_ready.zip in the project root."
        )
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(config.DATA_ZIP) as zf:
        zf.extractall(config.DATA_DIR)


def load_train() -> pd.DataFrame:
    ensure_data_extracted()
    df = pd.read_csv(config.TRAIN_CSV, dtype={"customer_id": str, "article_id": str})
    return df


def load_validation() -> pd.DataFrame:
    ensure_data_extracted()
    return pd.read_csv(config.VALIDATION_CSV, dtype={"customer_id": str, "article_id": str})


def load_test() -> pd.DataFrame:
    ensure_data_extracted()
    return pd.read_csv(config.TEST_CSV, dtype={"customer_id": str, "article_id": str})


def load_users() -> pd.DataFrame:
    ensure_data_extracted()
    return pd.read_csv(config.USERS_CSV, dtype={"customer_id": str})


def load_items() -> pd.DataFrame:
    ensure_data_extracted()
    return pd.read_csv(config.ITEMS_CSV, dtype={"article_id": str})


def load_all() -> dict:
    """Load every split + static tables in one call."""
    return {
        "train": load_train(),
        "validation": load_validation(),
        "test": load_test(),
        "users": load_users(),
        "items": load_items(),
    }


def purchased_map(train: pd.DataFrame) -> dict:
    """customer_id -> set of article_ids already purchased (train history)."""
    return train.groupby("customer_id")["article_id"].agg(set).to_dict()


# ---------------------------------------------------------- affinity features
AFFINITY_SOURCE_COLS = ["colour_group_name", "garment_group_name", "product_group_name"]
NO_HISTORY_LABEL = "__NONE__"


def add_affinity_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add fav_<col> columns: the user's favourite value of each metadata
    column among STRICTLY PRIOR interactions (leakage-safe, matching the
    historical_* features already prepared in the dataset).

    Rows are processed per customer in chronological order; the current row
    is excluded from its own favourite computation.
    """
    d = df.reset_index(drop=True)
    d["_orig"] = d.index
    d = d.sort_values(["customer_id", "t_dat"], kind="mergesort").reset_index(drop=True)

    for col in AFFINITY_SOURCE_COLS:
        dummies = pd.get_dummies(d[col]).astype("int32")
        prior = dummies.groupby(d["customer_id"], sort=False).cumsum() - dummies
        best = prior.to_numpy().argmax(axis=1)
        has_any = prior.to_numpy().max(axis=1) > 0
        d[f"fav_{col}"] = [
            str(prior.columns[b]) if h else NO_HISTORY_LABEL
            for b, h in zip(best, has_any)
        ]

    return d.sort_values("_orig", kind="mergesort").set_index("_orig")


def history_favourites(hist: pd.DataFrame) -> dict:
    """Favourite metadata values over a customer's full known history.

    Used at serving time for the user tower's affinity features.
    """
    out = {}
    for col in AFFINITY_SOURCE_COLS:
        if hist is None or len(hist) == 0:
            out[f"fav_{col}"] = NO_HISTORY_LABEL
        else:
            counts = hist[col].value_counts()
            out[f"fav_{col}"] = str(counts.index[0]) if len(counts) else NO_HISTORY_LABEL
    return out
