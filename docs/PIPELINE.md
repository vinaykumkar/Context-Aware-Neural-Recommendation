# Pipeline documentation

## Data contracts

### Source (read-only)

| Collection | Key columns | Notes |
|---|---|---|
| `customers` | `customer_id` (64-hex), `purchase_count`, `unique_articles_count`, `average_price`, `total_spent`, `recency_days`, `purchase_frequency`, `customer_lifetime_days`, `age`, `club_member_status`, `fashion_news_frequency`, `Active` | 1,371,980 rows |
| `articles` | `article_id` + 9 `*_index` encoded categorical features | 105,542 rows; no names/images in source |
| `transactions` | `t_dat`, `customer_id`, `article_id`, `price`, `sales_channel_id` (+year/month/dow) | 31,788,324 rows, 2018-09-20 → 2020-09-22 |

### Generated serving artifacts

| File | Contents |
|---|---|
| `serving_data/customers_serving.parquet` | profile + per-customer top feature codes (`top_product_group`, …), first/last purchase, `has_purchases` |
| `serving_data/articles_serving.parquet` | features + demand stats (`purchase_count`, `unique_customers`, `avg_price`, `sales_last_28d/84d`, …) |
| `serving_data/history/bucket_XX.parquet` | last 60 purchases per customer, sorted `customer_id, t_dat DESC` |
| `models/article_popularity.parquet` | blended popularity score + global rank |
| `models/item_neighbors_collab.parquet` | top-150 item-item neighbors, cosine over decayed co-purchases |
| `models/item_neighbors_content.parquet` | top-150 neighbors from one-hot feature cosine |
| `models/article_onehot.npz` | 105K × ~572 one-hot feature matrix |
| `recommendations/buckets/bucket_XX.parquet` | top-50 candidates per customer: `rank, score, comp_collaborative, comp_content, comp_popularity, comp_repurchase, reason` |

## Bucketing

`bucket = crc32(customer_id_bytes) % NUM_BUCKETS` (default 32) — implemented
once in `backend/app/core/serving.py` and shared by pipeline and backend.
A single customer's history and recommendations live in exactly one small
file; requests open that file directly.

## Scoring math

* Transaction decay: `w(t) = 0.5^(Δdays / 90)` (relative to the dataset end date)
* Co-purchase weight: `w_ij = Σ_u w_u(i) · w_u(j)` via sparse `AᵀA` (A holds `√w`)
* Collaborative similarity: `s_ij = w_ij / sqrt(d_i d_j)` (cosine); top-40 kept per item
* Hybrid: `0.45·collab + 0.25·content + 0.20·popularity + 0.10·repeat`
* Reason = dominant weighted component; near-ties (top < 1.25 × runner-up) → `HYBRID`

Content score — exact cosine between the customer's weighted attribute-profile
direction `p = Σ w_i·x_i / W` and each candidate's unit-norm one-hot vector:

    content(c) = ( Σ_{l ∈ x_c} S_l ) / ( 3 · sqrt( Σ_l S_l² ) ),   S_l = Σ w_i·[x_i has l]

Collaborative candidate generation is capped for 8 GB machines: only the
customer's **top-8 weighted (recency-decayed) articles** seed the neighbor
explosion (top-15 neighbors each). Content scores are computed **exactly** for
each customer's **top-100 preliminary candidates** (ranked by
collaborative + popularity + repeat) — a documented approximation that keeps
the SQL joins within the 2 GB DuckDB memory budget (everything spills to
`models/tmp_duckdb` beyond that).

## Memory safety (8 GB target)

* Stage 3 is fully **disk-backed DuckDB SQL**: `memory_limit=2000MB`,
  `temp_directory=models/tmp_duckdb`, 4 threads — hash joins/aggregations
  spill to disk instead of growing RAM
* Buckets are independent processes with **checkpoint/resume**: finished
  buckets are skipped on rerun, so an interrupted build only redoes the
  current bucket
* Transactions are scanned once per bucket through DuckDB's streaming
  operators (no pandas, no full-dataset frames)
* Stages 1–2 use polars bucketed scans and blockwise sparse scipy — the
  105K × 105K similarity matrix is never materialized; per-block part files
  make both phases resumable
