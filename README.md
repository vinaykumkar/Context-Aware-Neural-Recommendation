# AURA — H&M Personalized Fashion Recommendations

A production-style, end-to-end recommendation system built on the public
[H&M Group Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations)
dataset. Select any of **1.37M club members** and instantly see their purchase
story plus a personalized, explainable **Top-10** product selection.

All heavy computation happens **offline**; the web application answers from
compact precomputed serving artifacts — no request ever scans the ~800 MB
transaction dataset.

---

## Architecture

```
                        OFFLINE PIPELINE  (run once, ~1-2 h on 8 GB RAM)
┌────────────────────────────────────────────────────────────────────────┐
│  parquet/ (source, read-only)                                          │
│    customers · articles · transactions                                 │
│          │                                                             │
│          ▼  scripts/build_serving_data.py                              │
│  serving_data/   customer profiles · article stats · per-customer      │
│                  history buckets (hash-partitioned parquet)            │
│          │                                                             │
│          ▼  scripts/build_models.py                                    │
│  models/         item-item collaborative neighbors (recency-decayed    │
│                  co-purchase, cosine) · content neighbors (one-hot     │
│                  features) · popularity · article one-hot vectors      │
│          │                                                             │
│          ▼  scripts/build_recommendations.py                           │
│  recommendations/  top-50 candidates per customer with component       │
│                    scores + reason codes (hash-bucketed parquet)       │
└────────────────────────────────────────────────────────────────────────┘

                        ONLINE APPLICATION  (fast, O(bucket lookup))
┌────────────────────────────────────────────────────────────────────────┐
│  React + TypeScript + Vite + Tailwind + Framer Motion  (frontend/)     │
│            │  REST                                                     │
│            ▼                                                           │
│  FastAPI + DuckDB  (backend/)                                          │
│    reads one small bucket file per request                             │
│    optional runtime reranking: purchased-item filter + diversity cap   │
└────────────────────────────────────────────────────────────────────────┘
```

### Recommendation algorithm

A **hybrid, explainable ranking** blended per customer (all components
normalized 0–1):

| Component | Weight | Signal |
|---|---|---|
| Collaborative | 0.45 | top-100 cosine neighbors from recency-decayed (half-life 90 d) co-purchase matrix |
| Content similarity | 0.25 | cosine between the customer's weighted article-attribute profile and candidate attributes |
| Popularity | 0.20 | blended log-scaled total + 12-week demand |
| Repeat purchase | 0.10 | the customer's own re-buy affinity |

The dominant weighted component becomes an honest **reason code**
(`COLLABORATIVE`, `CONTENT_SIMILARITY`, `POPULARITY`, `REPEAT_PURCHASE`,
`HYBRID`). At request time the backend can exclude already-purchased items and
cap the number of recommendations per product group (diversity). Cold-start
members get a clearly labelled popularity fallback.

Why this design: it captures collaborative behavior *and* taste coherence,
survives 8 GB RAM (disk-backed DuckDB SQL with spill, sparse blockwise
computation, hash-bucketed serving, checkpoint/resume at every stage), and
every ranking can be explained to a human — ideal for an academic
demonstration.

Engineering caps (documented trade-offs for 8 GB machines): collaborative
candidates are exploded from each customer's top-8 recency-weighted articles
(top-15 neighbors each), and content scores are computed exactly for the
top-100 preliminary candidates per customer. See `docs/PIPELINE.md`.

---

## Project layout

```
├── parquet/                 # READ-ONLY source data (never committed)
├── backend/app/             # FastAPI app (routers, services, core, schemas)
├── frontend/                # React + TS + Vite + Tailwind web experience
├── scripts/                 # CLI entry points for the offline pipeline
│   └── pipeline/            #   stage implementations
├── serving_data/            # generated: profiles, article stats, history buckets
├── models/                  # generated: neighbor tables, popularity, metadata
├── recommendations/         # generated: per-customer candidate pools
├── tests/                   # pytest suite (synthetic fixture, no dataset needed)
├── docs/                    # pipeline & API documentation
├── .env.example             # all configuration options
└── requirements.txt
```

---

## Requirements

* Python **3.11+** (developed on 3.12) — see `requirements.txt`
* Node.js **20+** (frontend)
* ~8 GB RAM is enough for both the offline build and serving
* ~1 GB free disk for generated artifacts

## 1. Dataset placement

Download the H&M dataset and place the three cleaned parquet collections in:

```
parquet/
├── customers/     part-*.parquet   (customer_id, Active, club_member_status, …)
├── articles/      part-*.parquet   (article_id, *_index encoded features)
└── transactions/  part-*.parquet   (t_dat, customer_id, article_id, price, …)
```

The source data is treated as **read-only**; nothing in the pipeline writes to
it. If you place the data elsewhere, set `DATA_DIR` (see `.env.example`).

## 2. Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Offline preprocessing & recommendation generation

```bash
python scripts/inspect_data.py            # schemas + row counts (metadata only)
python scripts/build_serving_data.py      # stage 1: serving parquet (~35 min)
python scripts/build_models.py            # stage 2: similarity models (~20 min)
python scripts/build_recommendations.py   # stage 3: per-customer pools (~30 min)
# or everything at once:  python scripts/build_all.py
```

Stage progress prints to the console; stage timings are stored in
`serving_data/meta.json` and `models/*_meta.json`.

## 4. Start the backend

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# interactive API docs: http://127.0.0.1:8000/docs
```

Startup loads no large data; DuckDB opens serving files lazily.

## 5. Start the frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 (proxies /api → :8000)
```

Production build: `npm run build` → static files in `frontend/dist/`.

### One-command local hosting (Windows)

`start_local.bat` (project root) restarts both servers bound to all
interfaces — this PC on `http://localhost:5173` and other devices on the same
Wi-Fi via `http://<your-LAN-IP>:5173` — then opens the browser. Logs go to
`logs/`. (Windows may ask to allow Python/Node through the firewall once for
LAN access.)

## 6. Image configuration

Real product images are supported. Point `IMAGE_DIR` at the H&M images folder
(read-only, never copied into the project) and build the lightweight index once:

```bash
# .env
IMAGE_DIR=D:/Dataset/h-and-m-personalized-fashion-recommendations/images
python scripts/build_image_index.py
```

* The index (`serving_data/image_index.parquet`, ~0.6 MB) maps the canonical
  10-digit article id to its image path; the 28 GB folder is scanned once,
  filenames only.
* Images are served to the browser through `GET /api/images/{article_id}`
  (validated, index-backed — raw filesystem paths are never exposed).
* Articles without an image (442 in the current data, 99.6% coverage) fall
  back to the deterministic editorial placeholder.
* Cloud/CDN alternative: set `IMAGE_URL_TEMPLATE` with `{article_id}`
  (10-digit) / `{article_id_raw}` (numeric) — no code changes needed.
* With neither configured the app runs fully on placeholders.

## 7. GitHub / deployment notes

* `parquet/`, `serving_data/`, `recommendations/`, models and node_modules are
  git-ignored — the repository stays small and the 800 MB dataset is never
  committed.
* Backend deploy: any FastAPI container/server; serving artifacts must sit on
  the server disk (or object storage with the same layout).
* Frontend deploy: static hosting; set the API base URL via the Vite proxy
  config or a reverse proxy.
* All configuration flows through environment variables (`.env.example`).

## API overview

| Endpoint | Description |
|---|---|
| `GET /health` | serving-artifact status |
| `GET /api/config` | image mode + serving options |
| `GET /api/customers?q=&page=&page_size=&sort=&has_purchases=` | paginated member discovery |
| `GET /api/customers/{id}` | profile + category affinities |
| `GET /api/customers/{id}/history?limit=` | recent purchases (article display joined) |
| `GET /api/customers/{id}/recommendations?count=&exclude_purchased=&diversify=` | personal Top-N with reasons + signal scores |
| `GET /api/articles/{id}` | article stats + similar articles |
| `GET /api/articles/popular?limit=` | global popular rail |
| `GET /api/stats` | dataset + model metadata |

## Tests

```bash
python -m pytest tests/ -q
```

34 tests cover dataset discovery helpers, bucketing stability, customer
lookup, history ordering, recommendation count/dedup/ranking/reason codes,
purchased-item exclusion, popularity fallback, image providers, and API
validation/error handling — all against a synthetic fixture, no dataset
required.

To verify that every ID and row in the generated artifacts exists verbatim
in the source dataset (referential integrity), run:

```bash
python scripts/validate_outputs.py   # 8 checks, needs the built artifacts
```

## Performance

Measured on the development machine (12-core, **8 GB RAM**, NVMe) — note that
the 8 GB constraint dominated the pipeline design:

| Metric | Value |
|---|---|
| Backend startup | < 2 s (no data loaded) |
| `/health` first request | ~30 ms |
| Customer discovery (page of 24) | ~0.35–0.8 s |
| Customer profile | ~0.13 s |
| Purchase history (60 items, joined) | ~0.18 s |
| Recommendations (Top-10, reranked) | ~0.19 s |
| Offline stage 1 (serving data) | ~33 min |
| Offline stage 2 (similarity models) | ~1–2 h |
| Offline stage 3 (recommendation pools) | ~72 min (32 buckets × ~110 s) |
| Generated artifacts on disk | ~1.4 GB total |

Every online request reads at most a handful of small parquet bucket files —
the ~800 MB source dataset is never opened at request time.

---

## Honest limitations

* The cleaned source data ships article attributes as label-encoded indices
  **without the decoding map** and without product names — the UI therefore
  shows codes (`Type ·33`) alongside real demand statistics rather than
  fabricated names.
* No product images exist in the dataset and no public image CDN could be
  verified; the placeholder/provider design keeps the app ready for a real
  image source (see section 6).
* Prices are normalized source units (0–0.59); no absolute currency can be
  recovered, so the UI labels them as normalized price.
* Offline evaluation (recall@k / MAP) was not computed against a hold-out
  split; the hybrid weights are heuristic, documented and tunable via env.
