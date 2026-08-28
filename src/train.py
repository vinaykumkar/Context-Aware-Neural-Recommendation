"""Train the Two-Tower retrieval model end-to-end.

Run:  python -m src.train

Steps:
    1. extract the dataset ZIP if needed
    2. load the prepared train/validation/test split
    3. build and save vocabularies
    4. build the user/item towers and the combined retrieval model
    5. train with in-batch softmax (in-batch negatives)
    6. print epoch/loss information
    7. evaluate validation and test with Recall@K / NDCG@K
    8. save towers, item embeddings, FAISS index, metrics and config
"""

import time

import numpy as np
import pandas as pd
import tensorflow as tf
import keras

from src import config, data_loader, evaluate, faiss_index, model, utils


def build_vocabularies(train: pd.DataFrame, items: pd.DataFrame) -> dict:
    """One vocabulary per categorical feature (index 0 = UNK)."""
    vocab = {}
    for name in config.USER_CATEGORICAL:
        if name.startswith("fav_"):
            src = name[len("fav_"):]
            vocab[name] = ["__UNK__", data_loader.NO_HISTORY_LABEL] + sorted(set(items[src]))
        else:
            vocab[name] = utils.build_vocabulary(train[name])
    for name in config.ITEM_CATEGORICAL:
        vocab[name] = utils.build_vocabulary(items[name])
    return vocab


def numeric_stats(train: pd.DataFrame) -> dict:
    num = train[config.USER_NUMERIC].to_numpy(dtype="float32")
    return {
        "mean": num.mean(axis=0).tolist(),
        "std": np.clip(num.std(axis=0), 1e-6, None).tolist(),
    }


def add_logq(df: pd.DataFrame, counts: pd.Series, n_items: int) -> pd.DataFrame:
    """Per-interaction log-popularity of the purchased item.

    q(item) = (count + 1) / (N + n_items), smoothed. Used for the logQ
    sampling-bias correction of the in-batch softmax (train time only).
    """
    df = df.copy()
    n = counts.sum()
    q = (df["article_id"].map(counts).fillna(0) + 1.0) / (n + n_items)
    df["logq"] = np.log(q.to_numpy(dtype="float32"))
    return df


def prefixed(arrays: dict, prefix: str) -> dict:
    return {f"{prefix}{k}": v for k, v in arrays.items()}


def make_dataset(user_arrays: dict, item_arrays: dict, shuffle: bool) -> tf.data.Dataset:
    x = {**prefixed(user_arrays, "user__"), **prefixed(item_arrays, "item__")}
    n = len(next(iter(x.values())))
    ds = tf.data.Dataset.from_tensor_slices((x, np.zeros((n, 1), dtype="float32")))
    if shuffle:
        ds = ds.shuffle(n, seed=config.SEED)
    return ds.batch(config.BATCH_SIZE).prefetch(tf.data.AUTOTUNE)


def main() -> None:
    t0 = time.time()
    utils.set_seeds(config.SEED)

    print("=" * 60)
    print("StyleSense AI - Two-Tower training")
    print("=" * 60)

    # 1-2. data
    data = data_loader.load_all()
    train, val, test = data["train"], data["validation"], data["test"]
    users, items = data["users"], data["items"]
    print(f"train={len(train)}  validation={len(val)}  test={len(test)}  "
          f"users={len(users)}  items={len(items)}")

    # 3. vocabularies + numeric normalization stats
    vocab = build_vocabularies(train, items)
    for name, values in vocab.items():
        utils.save_vocabulary(name, values)
    num_stats = numeric_stats(train)

    pop_counts = train["article_id"].value_counts()
    train = add_logq(train, pop_counts, len(items))
    val = add_logq(val, pop_counts, len(items))

    # leakage-safe content-affinity favourites from strictly prior purchases
    train["_split"], val["_split"], test["_split"] = "train", "val", "test"
    union = pd.concat([train, val, test], ignore_index=True)
    union = data_loader.add_affinity_columns(union)
    train = union[union["_split"] == "train"].drop(columns=["_split"]).reset_index(drop=True)
    val = union[union["_split"] == "val"].drop(columns=["_split"]).reset_index(drop=True)
    test = union[union["_split"] == "test"].drop(columns=["_split"]).reset_index(drop=True)

    # 4. model
    vocab_sizes = {name: len(v) for name, v in vocab.items()}
    user_tower = model.build_user_tower(vocab_sizes)
    item_tower = model.build_item_tower(vocab_sizes)
    two_tower = model.build_two_tower_model(user_tower, item_tower, config.TEMPERATURE)
    two_tower.compile(
        optimizer=keras.optimizers.Adam(config.LEARNING_RATE),
        loss=model.InBatchSoftmaxLoss(),
        metrics=[model.inbatch_accuracy],
    )
    user_tower.summary(print_fn=print)
    item_tower.summary(print_fn=print)

    # 5-6. training
    train_user = model.user_feature_arrays(train, vocab, num_stats)
    train_item = model.item_feature_arrays(train, vocab)
    train_item["logq"] = train["logq"].to_numpy(dtype="float32")
    val_user = model.user_feature_arrays(val, vocab, num_stats)
    val_item = model.item_feature_arrays(val, vocab)
    val_item["logq"] = val["logq"].to_numpy(dtype="float32")

    history = two_tower.fit(
        make_dataset(train_user, train_item, shuffle=True),
        validation_data=make_dataset(val_user, val_item, shuffle=False),
        epochs=config.EPOCHS,
        callbacks=[keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=config.EARLY_STOP_PATIENCE,
            restore_best_weights=True,
        )],
        verbose=2,
    )
    for epoch, (loss, vloss) in enumerate(zip(history.history["loss"],
                                              history.history["val_loss"]), 1):
        acc = history.history["inbatch_accuracy"][epoch - 1]
        vacc = history.history["val_inbatch_accuracy"][epoch - 1]
        print(f"epoch {epoch}: loss={loss:.4f} acc={acc:.4f} "
              f"val_loss={vloss:.4f} val_acc={vacc:.4f}")

    # 7. retrieval evaluation on real validation/test interactions
    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    item_arrays = model.item_feature_arrays(items, vocab)
    item_embeddings = np.asarray(item_tower.predict(item_arrays, batch_size=512,
                                                    verbose=0), dtype="float32")
    item_embeddings /= np.clip(np.linalg.norm(item_embeddings, axis=1,
                                              keepdims=True), 1e-12, None)
    item_ids = items["article_id"].to_numpy().astype(str)

    index = faiss_index.ANNIndex(item_embeddings, item_ids)
    purchased = data_loader.purchased_map(train)

    print("evaluating validation split ...")
    val_metrics = evaluate.evaluate_split(user_tower, index, val, vocab,
                                          num_stats, purchased)
    print("validation:", val_metrics)
    print("evaluating test split ...")
    test_metrics = evaluate.evaluate_split(user_tower, index, test, vocab,
                                           num_stats, purchased)
    print("test:", test_metrics)

    # 8. save artifacts
    user_tower.save(config.USER_TOWER_PATH)
    item_tower.save(config.ITEM_TOWER_PATH)
    np.save(config.ITEM_EMBEDDINGS_PATH, item_embeddings)
    np.save(config.ITEM_IDS_PATH, item_ids)
    index.save()

    metrics_out = {
        **{k: v for k, v in test_metrics.items() if k != "num_interactions_evaluated"},
        "validation": val_metrics,
        "test": test_metrics,
        "evaluated_on": "test split (per-user temporal, last interaction)",
    }
    utils.save_json(config.METRICS_PATH, metrics_out)

    utils.save_json(config.MODEL_CONFIG_PATH, {
        "embedding_dim": config.EMBEDDING_DIM,
        "id_embedding_dim": config.ID_EMBEDDING_DIM,
        "cat_embedding_dim": config.CAT_EMBEDDING_DIM,
        "hidden_units": config.HIDDEN_UNITS,
        "temperature": config.TEMPERATURE,
        "batch_size": config.BATCH_SIZE,
        "epochs_run": len(history.history["loss"]),
        "seed": config.SEED,
        "user_categorical": config.USER_CATEGORICAL,
        "user_numeric": config.USER_NUMERIC,
        "item_categorical": config.ITEM_CATEGORICAL,
        "item_numeric": config.ITEM_NUMERIC,
        "logq_correction": True,
        "vocab_sizes": {k: len(v) for k, v in vocab.items()},
        "numeric_stats": num_stats,
        "ann_engine": "faiss" if faiss_index.FAISS_AVAILABLE else "sklearn_fallback",
        "train_rows": len(train),
        "num_users": len(users),
        "num_items": len(items),
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "training_seconds": round(time.time() - t0, 1),
    })

    print("-" * 60)
    print(f"done in {time.time() - t0:.1f}s - artifacts saved to {config.ARTIFACTS_DIR}")
    print(f"ANN engine: {'FAISS' if faiss_index.FAISS_AVAILABLE else 'sklearn fallback'}")


if __name__ == "__main__":
    main()
