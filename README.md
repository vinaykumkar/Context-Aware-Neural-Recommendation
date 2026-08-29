# Model Serving & Feature Store Setup — Week 3

## Overview
An end-to-end model-serving pipeline for a recommender system: train a Matrix Factorization model, export its architecture and embeddings, load them into Redis as a low-latency feature store, and implement FAISS-based Approximate Nearest Neighbor (ANN) search for candidate retrieval.

**Dataset:** self-generated implicit-feedback data (2,000 users, 1,500 items, ~59,400 interactions) since no pre-existing trained model was available — built to exercise the full serving pipeline end-to-end.

## Contents
- `Week3_Model_Serving_Feature_Store_Report.docx` — full report: architecture, methodology, benchmarks, visualizations, and critical discussion.
- `day1_3_train_export.py` — data generation, Matrix Factorization training (with early stopping), and artifact export.
- `day4_6_redis_feature_store.py` — bulk-loads embeddings into Redis and benchmarks lookup latency.
- `day7_ann_search.py` — builds a FAISS IVFFlat ANN index, benchmarks recall@K and latency vs. exact search.
- `generate_visualizations.py` — generates all 6 report figures.
- `artifacts/` — exported model card, embeddings, benchmark JSON results, and figures.

## How to reproduce
```bash
pip install pandas numpy matplotlib seaborn scikit-learn redis faiss-cpu

# Start Redis (or point REDIS_HOST/PORT at an existing instance)
redis-server --daemonize yes --port 6379

python day1_3_train_export.py
python day4_6_redis_feature_store.py
python day7_ann_search.py
python generate_visualizations.py
```

## Key results
- Matrix Factorization model (32-dim embeddings) beat a global-mean baseline by ~13.6% (val RMSE 0.660 vs. 0.764), using early stopping to avoid overfitting.
- Redis feature store: ~83,900 writes/sec bulk load; p99 single-key lookup latency of 0.107 ms.
- FAISS IVFFlat ANN index: Recall@10 of 0.663 at nprobe=8, rising to 0.995 at nprobe=32 — a clear accuracy/latency trade-off curve.
- At this catalog size (1,500 items), ANN showed only a modest ~1.09x speedup over exact search — both are sub-millisecond, and ANN's real advantage emerges at much larger catalog scales (100K+ items), a key documented finding.

## Tools
Python · pandas · NumPy · scikit-learn · Redis (redis-py) · FAISS · matplotlib · seaborn
