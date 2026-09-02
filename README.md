# Context-Aware-Neural-Recommendation


A smart, data-driven recommendation engine that curates tailored outfit ideas, seasonal staples, and style inspiration based on individual user preferences, browsing history, and real-time trends.

Architecture
                RAW DATA
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   Customers    Articles   Transactions
       │           │           │
       └───────────┼───────────┘
                   ▼
            Data Cleaning
                   │
                   ▼
          Missing Value Handling
                   │
                   ▼
            Deduplication
                   │
                   ▼
        Temporal Feature Creation
                   │
                   ▼
       User Behavioral Features
                   │
                   ▼
        Product Popularity Features
                   │
                   ▼
       Context-Enriched Interactions
                   │
                   ▼
          Categorical Encoding
                   │
             ┌─────┴─────┐
             ▼           ▼
        User Tower    Item Tower
             │           │
             ▼           ▼
        User Vector   Item Vector
             │           │
             └─────┬─────┘
                   ▼
            Neural Training
                   │
                   ▼
          64-D Embeddings
                   │
                   ▼
             FAISS Index
                   │
                   ▼
             User Request
                   │
                   ▼
           User Embedding
                   │
                   ▼
             FAISS Search
                   │
                   ▼
             Top-K Items
                   │
                   ▼
            Recommendation

Project Structure

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

    
Installation

Windows PowerShell:

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Train Model
python -m src.train

This extracts the dataset (if needed), trains the Two-Tower model, evaluates it, and writes everything required for serving into artifacts/.

Training is NOT required every time - if artifacts/ is already present, the Streamlit app and the recommender load the saved model directly.

Run Demo
streamlit run app.py
Then open the local URL shown by Streamlit (usually http://localhost:8501).
