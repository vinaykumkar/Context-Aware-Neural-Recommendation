"""Small shared helpers: seeding and vocabulary handling."""

import json
import os
import random

from src import config


def set_seeds(seed: int = config.SEED) -> None:
    """Seed python, numpy and tensorflow for reproducible training."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    os.environ["TF_DETERMINISTIC_OPS"] = "1"
    try:
        import numpy as np
        import tensorflow as tf

        np.random.seed(seed)
        tf.random.set_seed(seed)
    except ImportError:  # pragma: no cover - numpy/tf always present in practice
        pass


def save_json(path, payload) -> None:
    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_json(path):
    with open(str(path), "r", encoding="utf-8") as f:
        return json.load(f)


def save_vocabulary(name: str, values: list) -> None:
    """Persist one vocabulary (list of known values, index 0 reserved for UNK)."""
    save_json(config.VOCAB_DIR / f"{name}.json", values)


def load_vocabulary(name: str) -> list:
    return load_json(config.VOCAB_DIR / f"{name}.json")


def encode_with_vocab(values, vocab: list):
    """Map raw values to integer indices; unknown values map to 0 (UNK)."""
    lookup = {v: i for i, v in enumerate(vocab)}
    return [lookup.get(v, 0) for v in values]


def build_vocabulary(values) -> list:
    """Build [UNK, sorted unique values...] from training data."""
    return ["__UNK__"] + sorted({str(v) for v in values})
