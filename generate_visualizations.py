"""
Visualization generation for Week 3: Model Serving & Feature Store Setup
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns
from sklearn.decomposition import PCA

sns.set_theme(style="whitegrid")

# -----------------------------------------------------------------------
# Load artifacts
# -----------------------------------------------------------------------
history_df = pd.read_csv("artifacts/training_history.csv")
with open("artifacts/redis_benchmark.json") as f:
    redis_bench = json.load(f)
with open("artifacts/ann_benchmark.json") as f:
    ann_bench = json.load(f)
with open("artifacts/model_card.json") as f:
    model_card = json.load(f)

redis_latencies = np.load("artifacts/redis_lookup_latencies_ms.npy")
ann_latencies = np.load("artifacts/ann_latencies_ms.npy")
exact_latencies = np.load("artifacts/exact_latencies_ms.npy")
item_embeddings = np.load("artifacts/item_embeddings.npy")
item_bias = np.load("artifacts/item_bias.npy")

with open("artifacts/baseline_rmse.txt") as f:
    baseline_rmse = float(f.read())

# =========================================================================
# VIZ 1 — Training curve: train vs val RMSE, with early-stopping point marked
# =========================================================================
plt.figure(figsize=(8, 5.5))
plt.plot(history_df["epoch"], history_df["train_rmse"], marker="o", label="Train RMSE", color="#4C72B0")
plt.plot(history_df["epoch"], history_df["val_rmse"], marker="o", label="Validation RMSE", color="#DD8452")
best_epoch = history_df.loc[history_df["val_rmse"].idxmin(), "epoch"]
best_val = history_df["val_rmse"].min()
plt.axvline(best_epoch, color="grey", linestyle="--", alpha=0.7)
plt.scatter([best_epoch], [best_val], color="green", s=120, zorder=5, label=f"Best checkpoint (epoch {int(best_epoch)})")
plt.axhline(baseline_rmse, color="red", linestyle=":", alpha=0.7, label=f"Global-mean baseline ({baseline_rmse:.3f})")
plt.xlabel("Epoch")
plt.ylabel("RMSE")
plt.title("Matrix Factorization Training Curve\n(Early Stopping on Validation RMSE)", fontsize=13, weight="bold")
plt.legend()
plt.tight_layout()
plt.savefig("artifacts/viz1_training_curve.png", dpi=150)
plt.close()

# =========================================================================
# VIZ 2 — Redis feature-store lookup latency distribution
# =========================================================================
plt.figure(figsize=(8, 5.5))
plt.hist(redis_latencies, bins=40, color="#4E9F50", alpha=0.8, edgecolor="white")
plt.axvline(redis_bench["lookup_p50_ms"], color="black", linestyle="--", label=f"p50 = {redis_bench['lookup_p50_ms']:.3f} ms")
plt.axvline(redis_bench["lookup_p95_ms"], color="orange", linestyle="--", label=f"p95 = {redis_bench['lookup_p95_ms']:.3f} ms")
plt.axvline(redis_bench["lookup_p99_ms"], color="red", linestyle="--", label=f"p99 = {redis_bench['lookup_p99_ms']:.3f} ms")
plt.xlabel("Lookup Latency (ms)")
plt.ylabel("Frequency")
plt.title(f"Redis Feature Store: User Profile Lookup Latency\n(n={redis_bench['n_lookups_benchmarked']} single-key HGETALL calls)",
          fontsize=13, weight="bold")
plt.legend()
plt.tight_layout()
plt.savefig("artifacts/viz2_redis_latency_distribution.png", dpi=150)
plt.close()

# =========================================================================
# VIZ 3 — ANN recall vs. nprobe, and latency vs. nprobe (dual-axis trade-off)
# =========================================================================
sweep = pd.DataFrame(ann_bench["nprobe_sweep"])
fig, ax1 = plt.subplots(figsize=(8.5, 5.5))
color1 = "#4C72B0"
ax1.plot(sweep["nprobe"], sweep["recall_at_k"], marker="o", color=color1, label="Recall@K")
ax1.set_xlabel("nprobe (IVF cells searched)")
ax1.set_ylabel("Recall@K (vs. exact search)", color=color1)
ax1.tick_params(axis="y", labelcolor=color1)
ax1.set_ylim(0, 1.05)

ax2 = ax1.twinx()
color2 = "#DD8452"
ax2.plot(sweep["nprobe"], sweep["mean_latency_ms"], marker="s", color=color2, label="Mean Latency (ms)")
ax2.set_ylabel("Mean Retrieval Latency (ms)", color=color2)
ax2.tick_params(axis="y", labelcolor=color2)

plt.title("ANN Accuracy/Latency Trade-off\n(IVFFlat index, varying nprobe)", fontsize=13, weight="bold")
fig.tight_layout()
plt.savefig("artifacts/viz3_ann_tradeoff.png", dpi=150)
plt.close()

# =========================================================================
# VIZ 4 — ANN vs Exact search latency comparison (box/violin)
# =========================================================================
plt.figure(figsize=(7.5, 5.5))
plot_data = pd.DataFrame({
    "Latency (ms)": np.concatenate([ann_latencies, exact_latencies]),
    "Method": ["ANN (IVFFlat)"] * len(ann_latencies) + ["Exact (Brute-force)"] * len(exact_latencies)
})
sns.boxplot(data=plot_data, x="Method", y="Latency (ms)", palette=["#4C72B0", "#DD8452"])
plt.title(f"End-to-End Retrieval Latency: ANN vs. Exact Search\n"
          f"(Recall@{ann_bench['top_k']}={ann_bench['recall_at_k']:.3f} at nprobe={ann_bench['nprobe_used']})",
          fontsize=13, weight="bold")
plt.tight_layout()
plt.savefig("artifacts/viz4_ann_vs_exact_latency.png", dpi=150)
plt.close()

# =========================================================================
# VIZ 5 — Item embedding space (PCA projection to 2D), colored by item bias
# =========================================================================
pca = PCA(n_components=2, random_state=42)
item_2d = pca.fit_transform(item_embeddings)
plt.figure(figsize=(8, 6.5))
sc = plt.scatter(item_2d[:, 0], item_2d[:, 1], c=item_bias, cmap="coolwarm", s=18, alpha=0.75)
plt.colorbar(sc, label="Item bias (learned popularity offset)")
var_explained = pca.explained_variance_ratio_.sum() * 100
plt.title(f"Item Embedding Space (PCA projection, {var_explained:.1f}% variance explained)\n"
          f"Colored by learned item bias", fontsize=13, weight="bold")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.tight_layout()
plt.savefig("artifacts/viz5_embedding_space_pca.png", dpi=150)
plt.close()

# =========================================================================
# VIZ 6 — System architecture diagram
# =========================================================================
fig, ax = plt.subplots(figsize=(11, 6.5))
ax.set_xlim(0, 11)
ax.set_ylim(0, 7)
ax.axis("off")

def box(x, y, w, h, text, color="#4C72B0", textcolor="white", fontsize=10):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.1",
                            facecolor=color, edgecolor="black", linewidth=1.2)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            color=textcolor, fontsize=fontsize, weight="bold", wrap=True)

def arrow(x1, y1, x2, y2, text=""):
    arr = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18,
                           color="#333333", linewidth=1.5)
    ax.add_patch(arr)
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, text, ha="center", fontsize=8.5, style="italic")

# Stage boxes
box(0.3, 5.3, 2.4, 1.1, "Training Pipeline\n(Matrix Factorization)", color="#55A868")
box(0.3, 3.4, 2.4, 1.1, "Model Artifacts\nEmbeddings + Bias (.npy)\nModel Card (.json)", color="#4C72B0")
box(3.6, 3.4, 2.4, 1.1, "Redis Feature Store\nuser:{id}, item:{id}\nHash + float32 bytes", color="#C44E52")
box(6.9, 3.4, 2.2, 1.1, "FAISS ANN Index\nIVFFlat (item vectors)", color="#8172B2")
box(9.3, 3.4, 1.4, 1.1, "Top-K\nCandidates", color="#937860")
box(3.6, 1.2, 2.4, 1.1, "Inference Request\n(user_id)", color="#DA8BC3")
box(6.9, 1.2, 2.2, 1.1, "Ranking Stage\n(downstream, out of scope)", color="#8C8C8C")

arrow(1.5, 5.3, 1.5, 4.5, "export")
arrow(2.7, 3.95, 3.6, 3.95, "bulk load")
arrow(6.0, 3.95, 6.9, 3.95, "vectors")
arrow(9.1, 3.95, 9.3, 3.95, "search")
arrow(4.8, 2.3, 4.8, 3.4, "fetch user vec")
arrow(5.8, 1.75, 6.9, 1.75, "candidates")
arrow(4.8, 1.2, 4.8, 0.5)
ax.text(4.8, 0.3, "Client / App", ha="center", fontsize=9, style="italic")

plt.title("Model Serving & Feature Store Architecture", fontsize=14, weight="bold", pad=15)
plt.tight_layout()
plt.savefig("artifacts/viz6_architecture_diagram.png", dpi=150)
plt.close()

print("All visualizations generated.")
print(f"Best epoch: {int(best_epoch)}, best val RMSE: {best_val:.4f}")
