"""Two-Tower retrieval model built with standard TensorFlow/Keras.

USER TOWER
    customer_id embedding + small categorical embeddings + normalized
    numeric user/context features -> Dense(128, ReLU) -> Dense(64) -> L2 norm

ITEM TOWER
    article_id embedding + catalogue metadata embeddings
    -> Dense(128, ReLU) -> Dense(64) -> L2 norm

TRAINING OBJECTIVE
    In-batch softmax ("sampled softmax" with in-batch negatives): for a batch
    of (user, positive item) pairs, logits = user_emb @ item_emb.T / temperature
    and the correct class for row i is index i, i.e. every other item in the
    batch acts as an implicit negative. No huge negative datasets are created.
"""

import numpy as np
import tensorflow as tf
import keras
from keras import layers

from src import config


# ------------------------------------------------------------------ towers
def build_user_tower(vocab_sizes: dict) -> keras.Model:
    """vocab_sizes maps every USER_CATEGORICAL name to its vocab length."""
    inputs = {}
    embeds = []

    for name in config.USER_CATEGORICAL:
        inp = layers.Input(shape=(), dtype="int32", name=name)
        inputs[name] = inp
        width = config.ID_EMBEDDING_DIM if name == "customer_id" else config.CAT_EMBEDDING_DIM
        emb = layers.Embedding(vocab_sizes[name], width, name=f"{name}_emb")(inp)
        emb = layers.Dropout(config.DROPOUT, name=f"{name}_drop")(emb)
        embeds.append(emb)

    num_input = layers.Input(shape=(len(config.USER_NUMERIC),), dtype="float32", name="user_numeric")
    inputs["user_numeric"] = num_input
    embeds.append(num_input)

    x = layers.Concatenate(name="user_concat")(embeds) if len(embeds) > 1 else embeds[0]
    x = layers.Dense(config.HIDDEN_UNITS, activation="relu", name="user_dense_1")(x)
    x = layers.Dropout(config.DROPOUT, name="user_dropout")(x)
    x = layers.Dense(config.EMBEDDING_DIM, name="user_dense_2")(x)
    out = layers.UnitNormalization(name="user_embedding")(x)

    return keras.Model(inputs, out, name="user_tower")


def build_item_tower(vocab_sizes: dict) -> keras.Model:
    inputs = {}
    embeds = []

    for name in config.ITEM_CATEGORICAL:
        inp = layers.Input(shape=(), dtype="int32", name=name)
        inputs[name] = inp
        width = config.ID_EMBEDDING_DIM if name == "article_id" else config.CAT_EMBEDDING_DIM
        emb = layers.Embedding(vocab_sizes[name], width, name=f"{name}_emb")(inp)
        emb = layers.Dropout(config.DROPOUT, name=f"{name}_drop")(emb)
        embeds.append(emb)

    if config.ITEM_NUMERIC:
        num_input = layers.Input(shape=(len(config.ITEM_NUMERIC),), dtype="float32",
                                 name="item_numeric")
        inputs["item_numeric"] = num_input
        embeds.append(num_input)

    x = layers.Concatenate(name="item_concat")(embeds)
    x = layers.Dense(config.HIDDEN_UNITS, activation="relu", name="item_dense_1")(x)
    x = layers.Dropout(config.DROPOUT, name="item_dropout")(x)
    x = layers.Dense(config.EMBEDDING_DIM, name="item_dense_2")(x)
    out = layers.UnitNormalization(name="item_embedding")(x)

    return keras.Model(inputs, out, name="item_tower")


class SimilarityMatrix(layers.Layer):
    """Batch similarity matrix with logQ sampling-bias correction.

    logits[i, j] = (user_i . item_j) / temperature - log q(item_j)

    In-batch negatives are drawn from the interaction popularity
    distribution; subtracting log q corrects this bias (Yi et al. 2019,
    "Sampling-Bias-Corrected Neural Modeling for Large Corpus Item
    Recommendations") so the model can exploit item popularity, which the
    uncorrected objective cannot learn.
    """

    def __init__(self, temperature: float, **kwargs):
        super().__init__(**kwargs)
        self.temperature = temperature

    def call(self, inputs):
        user_emb, item_emb, logq = inputs
        logits = tf.matmul(user_emb, item_emb, transpose_b=True) / self.temperature
        return logits - tf.expand_dims(logq, 0)


# ------------------------------------------------------- combined training
class InBatchSoftmaxLoss(keras.losses.Loss):
    """Softmax cross-entropy over the in-batch similarity matrix.

    y_true is ignored; the diagonal (row i -> column i) is always the label,
    so every other item in the batch is an implicit negative.
    """

    def call(self, y_true, y_pred):
        batch = tf.shape(y_pred)[0]
        labels = tf.range(batch)
        return tf.nn.sparse_softmax_cross_entropy_with_logits(
            labels=labels, logits=y_pred
        )


def inbatch_accuracy(y_true, y_pred):
    """Share of rows where the user's own positive item is the batch argmax."""
    labels = tf.range(tf.shape(y_pred)[0])
    preds = tf.cast(tf.argmax(y_pred, axis=1), tf.int32)
    return tf.reduce_mean(tf.cast(tf.equal(preds, labels), tf.float32))


def build_two_tower_model(user_tower: keras.Model, item_tower: keras.Model,
                          temperature: float = config.TEMPERATURE) -> keras.Model:
    """Combine both towers into one trainable model that outputs a
    (batch x batch) similarity matrix of user vs. in-batch items."""

    # Prefixed combined inputs so the two towers never share input names.
    user_inputs = {}
    item_inputs = {}

    for name in config.USER_CATEGORICAL:
        user_inputs[name] = layers.Input(shape=(), dtype="int32", name=f"user__{name}")
    user_inputs["user_numeric"] = layers.Input(
        shape=(len(config.USER_NUMERIC),), dtype="float32", name="user__user_numeric"
    )

    for name in config.ITEM_CATEGORICAL:
        item_inputs[name] = layers.Input(shape=(), dtype="int32", name=f"item__{name}")
    if config.ITEM_NUMERIC:
        item_inputs["item_numeric"] = layers.Input(
            shape=(len(config.ITEM_NUMERIC),), dtype="float32", name="item__item_numeric"
        )

    # logq: per-item log popularity, used only for training-time correction
    logq_input = layers.Input(shape=(), dtype="float32", name="item__logq")

    all_inputs = list(user_inputs.values()) + list(item_inputs.values()) + [logq_input]

    user_emb = user_tower(user_inputs)
    item_emb = item_tower(item_inputs)

    logits = SimilarityMatrix(temperature, name="similarity_logits")(
        [user_emb, item_emb, logq_input]
    )

    return keras.Model(all_inputs, logits, name="two_tower_retrieval")


# ------------------------------------------------------- feature encoding
def user_feature_arrays(df, vocab: dict, num_stats: dict) -> dict:
    """Encode a dataframe (train/validation/test or a single user row) into
    the integer/float arrays the user tower expects."""
    arrays = {}
    for name in config.USER_CATEGORICAL:
        lookup = {v: i for i, v in enumerate(vocab[name])}
        arrays[name] = np.array(
            [lookup.get(str(v), 0) for v in df[name]], dtype="int32"
        )
    num = df[config.USER_NUMERIC].to_numpy(dtype="float32")
    mean = np.array(num_stats["mean"], dtype="float32")
    std = np.array(num_stats["std"], dtype="float32")
    arrays["user_numeric"] = (num - mean) / std
    return arrays


def item_feature_arrays(df, vocab: dict, item_num_stats: dict = None) -> dict:
    arrays = {}
    for name in config.ITEM_CATEGORICAL:
        lookup = {v: i for i, v in enumerate(vocab[name])}
        arrays[name] = np.array(
            [lookup.get(str(v), 0) for v in df[name]], dtype="int32"
        )
    if config.ITEM_NUMERIC:
        num = df[config.ITEM_NUMERIC].to_numpy(dtype="float32")
        if item_num_stats is not None:
            mean = np.array(item_num_stats["mean"], dtype="float32")
            std = np.array(item_num_stats["std"], dtype="float32")
            num = (num - mean) / std
        arrays["item_numeric"] = num
    return arrays
