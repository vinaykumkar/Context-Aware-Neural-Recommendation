"""
Day 1-3: Train Model & Export Architecture + Item Embeddings
=============================================================
Self-generated implicit-feedback dataset simulating a recommendation
scenario (users interacting with items). A simple Matrix Factorization
(MF) model is trained with mini-batch gradient descent to learn dense
user and item embeddings, which are then exported for downstream
serving (Redis feature store + ANN retrieval).
"""

import json
import numpy as np
import pandas as pd

RANDOM_STATE = 42
rng = np.random.default_rng(RANDOM_STATE)

N_USERS = 2000
N_ITEMS = 1500
N_INTERACTIONS = 60000
TRUE_LATENT_DIM = 12      # dimensionality used to *generate* synthetic ground truth
MODEL_LATENT_DIM = 32     # embedding dimensionality the model actually learns

# -----------------------------------------------------------------------
# 1. SYNTHETIC DATA GENERATION
# -----------------------------------------------------------------------
# Ground-truth latent factors used only to *generate* plausible ratings.
# Scaled down so the combined signal stays mostly within the 1-5 rating
# range without heavy clipping, which would otherwise destroy the very
# signal the model is meant to learn.
true_user_factors = rng.normal(0, 0.4, size=(N_USERS, TRUE_LATENT_DIM))
true_item_factors = rng.normal(0, 0.4, size=(N_ITEMS, TRUE_LATENT_DIM))
user_bias_true = rng.normal(0, 0.3, size=N_USERS)
item_bias_true = rng.normal(0, 0.3, size=N_ITEMS)
global_bias_true = 3.4

user_ids = rng.integers(0, N_USERS, size=N_INTERACTIONS)
item_ids = rng.integers(0, N_ITEMS, size=N_INTERACTIONS)

scores = (
    global_bias_true
    + user_bias_true[user_ids]
    + item_bias_true[item_ids]
    + np.sum(true_user_factors[user_ids] * true_item_factors[item_ids], axis=1)
)
noise = rng.normal(0, 0.35, size=N_INTERACTIONS)
ratings = np.clip(scores + noise, 1, 5)
pct_clipped = float(np.mean((scores + noise <= 1) | (scores + noise >= 5)) * 100)
print(f"Percent of raw scores clipped at rating bounds: {pct_clipped:.2f}%")

interactions = pd.DataFrame({
    "user_id": user_ids,
    "item_id": item_ids,
    "rating": ratings.round(2),
})
interactions = interactions.drop_duplicates(subset=["user_id", "item_id"]).reset_index(drop=True)
interactions.to_csv("artifacts/interactions.csv", index=False)
print(f"Generated {len(interactions)} unique user-item interactions "
      f"({N_USERS} users, {N_ITEMS} items).")

# Train/validation split (random split of interactions)
shuffled = interactions.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)
split_idx = int(len(shuffled) * 0.9)
train_df = shuffled.iloc[:split_idx]
val_df = shuffled.iloc[split_idx:]
print(f"Train: {len(train_df)}  Val: {len(val_df)}")

# -----------------------------------------------------------------------
# 2. MODEL ARCHITECTURE: Matrix Factorization w/ biases (Funk-SVD style)
#    Trained via mini-batch SGD with L2 regularization.
# -----------------------------------------------------------------------
class MatrixFactorizationModel:
    """
    Predicted rating: r_hat(u,i) = mu + b_u + b_i + p_u . q_i

    mu   : global bias (scalar)
    b_u  : per-user bias vector
    b_i  : per-item bias vector
    p_u  : user embedding matrix (N_USERS x K)
    q_i  : item embedding matrix (N_ITEMS x K)
    """

    def __init__(self, n_users, n_items, n_factors=32, reg=0.02, lr=0.01, seed=42):
        self.n_users = n_users
        self.n_items = n_items
        self.n_factors = n_factors
        self.reg = reg
        self.lr = lr
        r = np.random.default_rng(seed)
        self.mu = 0.0
        self.b_u = np.zeros(n_users)
        self.b_i = np.zeros(n_items)
        self.P = r.normal(0, 0.05, size=(n_users, n_factors))
        self.Q = r.normal(0, 0.05, size=(n_items, n_factors))

    def predict(self, u, i):
        return self.mu + self.b_u[u] + self.b_i[i] + np.sum(self.P[u] * self.Q[i], axis=-1)

    def fit(self, train_df, val_df, n_epochs=25, batch_size=2048, verbose=True,
            early_stopping_patience=4):
        self.mu = train_df["rating"].mean()
        history = []
        u_arr = train_df["user_id"].to_numpy()
        i_arr = train_df["item_id"].to_numpy()
        r_arr = train_df["rating"].to_numpy()
        n = len(train_df)

        best_val_rmse = np.inf
        best_state = None
        epochs_without_improvement = 0

        for epoch in range(1, n_epochs + 1):
            perm = np.random.permutation(n)
            for start in range(0, n, batch_size):
                idx = perm[start:start + batch_size]
                u, i, r = u_arr[idx], i_arr[idx], r_arr[idx]
                pred = self.predict(u, i)
                err = r - pred

                # Gradient updates (vectorized SGD step per batch)
                self.b_u[u] += self.lr * (err - self.reg * self.b_u[u])
                self.b_i[i] += self.lr * (err - self.reg * self.b_i[i])
                grad_P = err[:, None] * self.Q[i] - self.reg * self.P[u]
                grad_Q = err[:, None] * self.P[u] - self.reg * self.Q[i]
                np.add.at(self.P, u, self.lr * grad_P)
                np.add.at(self.Q, i, self.lr * grad_Q)

            train_rmse = self._rmse(train_df)
            val_rmse = self._rmse(val_df)
            history.append({"epoch": epoch, "train_rmse": train_rmse, "val_rmse": val_rmse})
            if verbose and (epoch % 2 == 0 or epoch == 1):
                print(f"Epoch {epoch:2d}  train_rmse={train_rmse:.4f}  val_rmse={val_rmse:.4f}")

            # Early stopping: checkpoint best-on-validation weights
            if val_rmse < best_val_rmse - 1e-4:
                best_val_rmse = val_rmse
                best_state = (self.mu, self.b_u.copy(), self.b_i.copy(),
                              self.P.copy(), self.Q.copy())
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= early_stopping_patience:
                    print(f"Early stopping at epoch {epoch} "
                          f"(no val improvement for {early_stopping_patience} epochs). "
                          f"Restoring best checkpoint (val_rmse={best_val_rmse:.4f}).")
                    break

        # Restore best-on-validation weights before returning
        if best_state is not None:
            self.mu, self.b_u, self.b_i, self.P, self.Q = best_state
        return pd.DataFrame(history)

    def _rmse(self, df):
        pred = self.predict(df["user_id"].to_numpy(), df["item_id"].to_numpy())
        return float(np.sqrt(np.mean((df["rating"].to_numpy() - pred) ** 2)))


model = MatrixFactorizationModel(N_USERS, N_ITEMS, n_factors=MODEL_LATENT_DIM,
                                  reg=0.045, lr=0.02, seed=RANDOM_STATE)
history_df = model.fit(train_df, val_df, n_epochs=40, batch_size=2048,
                        early_stopping_patience=6)
history_df.to_csv("artifacts/training_history.csv", index=False)

# -----------------------------------------------------------------------
# 3. EXPORT: model architecture (JSON card) + embeddings (npy)
# -----------------------------------------------------------------------
model_card = {
    "model_name": "mf_recommender_v1",
    "architecture": "Matrix Factorization with user/item bias terms (Funk-SVD style)",
    "n_users": N_USERS,
    "n_items": N_ITEMS,
    "embedding_dim": MODEL_LATENT_DIM,
    "regularization_l2": model.reg,
    "learning_rate": model.lr,
    "training_epochs": 25,
    "final_train_rmse": float(history_df.iloc[-1]["train_rmse"]),
    "final_val_rmse": float(history_df.iloc[-1]["val_rmse"]),
    "global_bias": float(model.mu),
    "prediction_formula": "r_hat(u,i) = mu + b_u[u] + b_i[i] + dot(P[u], Q[i])",
    "export_files": {
        "user_embeddings": "user_embeddings.npy",
        "item_embeddings": "item_embeddings.npy",
        "user_bias": "user_bias.npy",
        "item_bias": "item_bias.npy",
    },
}
with open("artifacts/model_card.json", "w") as f:
    json.dump(model_card, f, indent=2)

np.save("artifacts/user_embeddings.npy", model.P.astype(np.float32))
np.save("artifacts/item_embeddings.npy", model.Q.astype(np.float32))
np.save("artifacts/user_bias.npy", model.b_u.astype(np.float32))
np.save("artifacts/item_bias.npy", model.b_i.astype(np.float32))

print("\nModel architecture and embeddings exported to /artifacts:")
print(" - model_card.json (architecture + hyperparameters)")
print(" - user_embeddings.npy", model.P.shape)
print(" - item_embeddings.npy", model.Q.shape)
print(" - user_bias.npy / item_bias.npy")
print(f"\nFinal validation RMSE: {history_df.iloc[-1]['val_rmse']:.4f} "
      f"(baseline global-mean-only RMSE for reference below)")

baseline_rmse = float(np.sqrt(np.mean((val_df["rating"] - train_df["rating"].mean()) ** 2)))
print(f"Baseline (global mean) val RMSE: {baseline_rmse:.4f}")
with open("artifacts/baseline_rmse.txt", "w") as f:
    f.write(str(baseline_rmse))
