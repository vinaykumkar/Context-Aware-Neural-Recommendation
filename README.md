# StyleSense AI
## Context-Aware Two-Tower Fashion Recommendation Engine

StyleSense AI is a neural recommendation engine for fashion products. It learns
customer and product embeddings with a **Two-Tower retrieval model**, serves
**Top-K recommendations** through a **FAISS** nearest-neighbour index, and
demonstrates the full pipeline in an interactive **Streamlit** app with an
optional **Redis** cache.

---

## Project Overview

- Real Two-Tower neural retrieval model (TensorFlow/Keras), trained with
  in-batch negatives using a softmax cross-entropy objective.
- 64-dimensional L2-normalized embeddings for customers and products.
- FAISS ANN index over item embeddings for fast retrieval.
- Serving flow: customer → user tower → 64D user embedding → FAISS →
  purchased-item filtering → Top-10 products.
- Redis caching of user features and recommendation results, with an
  automatic in-memory fallback when Redis is not running.

## Current Implementation

### Week 2 Completed
- Two-Tower model (user tower + item tower)
- 64D embeddings
- Model training with in-batch negatives (in-batch softmax retrieval objective)
- Evaluation: Recall@K and NDCG@K on held-out validation/test interactions

### Week 3 Completed
- Item embedding export
- FAISS ANN index and Top-K recommendation serving
- Purchased-item filtering during retrieval
- Redis cache with in-memory fallback
- Streamlit interactive demonstration

## Architecture

```
Customer
   ↓
User Tower  (customer ID + user/context features)
   ↓
User Embedding (64D, L2-normalized)
   ↓
FAISS Search
   ↓
Top-K Recommendations
```

```
Product Metadata
   ↓
Item Tower  (article ID + catalogue features)
   ↓
Item Embedding (64D, L2-normalized)
   ↓
FAISS Index
```

## Dataset

Prepared subset based on the [H&M Personalized Fashion Recommendations]
(https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations)
dataset, with a per-user temporal split and leakage-safe historical features:

| Split | Interactions |
|---|---|
| Train | 44,718 |
| Validation | 5,000 |
| Test | 5,000 |
| Customers | 5,000 |
| Products | 4,668 |

The dataset ships as `model_data_ready.zip` in the repository root and is
extracted automatically to `data/model_data/` on first run.

## Tech Stack

- Python
- TensorFlow / Keras
- FAISS (faiss-cpu)
- Redis (optional, in-memory fallback built in)
- Pandas / NumPy
- Streamlit

## Project Structure

```
├── app.py                    # Streamlit demo
├── requirements.txt
├── model_data_ready.zip      # prepared dataset (auto-extracted)
├── src/
│   ├── config.py             # paths and hyperparameters
│   ├── data_loader.py        # zip extraction + split loading + affinity features
│   ├── model.py              # two-tower model, in-batch softmax loss
│   ├── train.py              # end-to-end training + artifact export
│   ├── evaluate.py           # Recall@K / NDCG@K with FAISS retrieval
│   ├── faiss_index.py        # FAISS index wrapper (sklearn fallback)
│   ├── recommender.py        # RecommendationEngine serving flow
│   ├── cache.py              # Redis cache / in-memory fallback
│   └── utils.py              # seeds, vocabularies, JSON helpers
├── artifacts/                # trained model, embeddings, FAISS index, metrics
└── scripts/
    └── verify_project.py     # end-to-end health check
```

## Installation

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Train Model

```
python -m src.train
```

This extracts the dataset (if needed), trains the Two-Tower model, evaluates
it, and writes everything required for serving into `artifacts/`.

**Training is NOT required every time** - if `artifacts/` is already present,
the Streamlit app and the recommender load the saved model directly.

## Run Demo

```
streamlit run app.py
```

Then open the local URL shown by Streamlit (usually http://localhost:8501).

## Model Metrics

Actual metrics measured on the held-out test split (each customer's last
interaction, previously purchased items excluded from candidates):

| Metric | Value |
|---|---|
| Recall@5 | 7.38% |
| Recall@10 | 14.00% |
| Recall@20 | 20.84% |
| NDCG@10 | 6.59% |
| NDCG@20 | 8.31% |

The values above were produced by the current trained artifacts; re-running
`python -m src.train` regenerates them into `artifacts/metrics.json`.

## Current Limitation

The current model is trained on a representative subset for architecture
validation. Recommendation quality can be improved further with larger-scale
training, additional interaction history and hyperparameter tuning.

## Future Work

- Training on the full H&M dataset
- PySpark data pipelines
- Larger-scale Two-Tower training
- FastAPI serving service
- Airflow scheduling
- Production Redis feature store
- Cloud deployment
