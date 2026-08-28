# PROJECT REVIEW NOTES (StyleSense AI)

These notes are written in very simple English so you can quickly study and
explain the project during review or viva.

---

## WHAT IS THE PROJECT?

StyleSense AI is a fashion product recommendation engine. You select a
customer, and the system shows 10 products that the customer has never bought
but is likely to enjoy, based on their purchase history and profile.

## WHAT PROBLEM DOES IT SOLVE?

Online fashion shops have thousands of products. A customer cannot see
everything. The system must pick a small set of products to show each
customer. This project shows one standard way to do that: learn a "taste
vector" (embedding) for every customer and every product, then find the
products whose taste vectors are closest to the customer's.

## WHAT DATASET DO WE USE?

A prepared subset of the H&M Personalized Fashion Recommendations dataset
(from Kaggle). It contains:

- 44,718 training interactions (customer bought product)
- 5,000 validation interactions
- 5,000 test interactions
- 5,000 customers
- 4,668 products

The data was split by TIME for each customer: earlier purchases go to
training, the second-last purchase goes to validation, the last purchase goes
to test. This is called a temporal split. It stops the model from "cheating"
by seeing the future.

## WHAT HAVE WE COMPLETED?

- Week 1: Data cleaning, preprocessing, and leakage-safe temporal
  train/validation/test preparation.
- Week 2: Two-Tower neural network, model training, and evaluation with
  Recall@K and NDCG@K.
- Week 3: Item embedding export, FAISS retrieval, Redis caching, and the
  interactive Streamlit demo.

---

## SIMPLE EXPLANATIONS OF THE CONCEPTS

### WHAT IS USER TOWER?

The User Tower is a small neural network. It takes customer information
(customer ID, age, purchase history numbers, favourite colours, day of week,
etc.) and converts it into one vector of 64 numbers, called the user
embedding. Think of it as a "taste profile" of the customer.

### WHAT IS ITEM TOWER?

The Item Tower is a similar small neural network for products. It takes
product information (product type, colour, garment group, segment, product
ID) and converts it into a 64-number vector, the item embedding. This is a
"profile" of the product.

### WHAT IS AN EMBEDDING?

An embedding is a list of numbers (a vector) that represents something
complex, like a customer or a product, in a way a computer can compare
easily. Similar things end up close together in this number space. If a
customer often buys black dresses, their embedding will be close to the
embeddings of black dresses.

### WHY 64 DIMENSIONS?

The vector has 64 numbers. This is a common small size: big enough to capture
customer taste and product properties, small enough to train quickly on a
normal laptop CPU and to search fast. Both towers MUST produce the same size
(64) because we compare them with each other.

### HOW TRAINING WORKS?

For every training row we know a customer and a product they actually bought
(a "positive" pair). The model computes both embeddings and makes the customer
vector closer to the bought product's vector. At the same time it pushes the
customer vector away from other products in the same batch. We repeat this
over the whole training set for several epochs until the embeddings are
useful.

### WHAT ARE IN-BATCH NEGATIVES?

Instead of building a huge list of "products the customer did NOT buy" (which
would be millions of rows), we use the other products inside the same
training batch as negative examples. For example, in a batch of 256
(customer, product) pairs, the 255 other products of a row act as its
negatives. This is memory-friendly and works well. We also subtract the log
of each item's popularity (logQ correction) so that popular products do not
unfairly dominate the training.

### WHAT IS FAISS?

FAISS (Facebook AI Similarity Search) is a library for very fast
nearest-neighbour search over vectors. We store all 4,668 product embeddings
in a FAISS index. When a customer's 64D embedding arrives, FAISS instantly
returns the product embeddings closest to it.

### WHAT IS COSINE SIMILARITY?

Cosine similarity measures the angle between two vectors. 1 means "same
direction" (very similar), 0 means "no relation". Because our embeddings are
L2-normalized (length exactly 1), comparing them with inner product is the
same as cosine similarity - that is why the FAISS index uses inner product
search.

### WHAT IS TOP-K?

Top-K means "the K best items". Our demo uses K = 10, so we show the 10
products with the highest similarity to the customer's embedding.

### WHAT IS RECALL@K?

Recall@K answers: "If the customer's next real purchase is somewhere in our
top-K list, how often do we catch it?" For example, Recall@10 = 14% means:
for 14% of the test customers, the product they actually bought next appears
inside our top-10 list. Our current test values: Recall@5 = 7.38%,
Recall@10 = 14.00%, Recall@20 = 20.84%.

### WHAT IS NDCG?

NDCG (Normalized Discounted Cumulative Gain) is like Recall but it also cares
about the POSITION. Finding the right product at position 1 scores much
higher than finding it at position 10. Our current test values: NDCG@10 =
6.59%, NDCG@20 = 8.31%.

### WHAT IS REDIS?

Redis is a fast in-memory data store often used as a cache. In a real
recommendation system it stores user features and recent recommendation
results so the system does not recompute everything for every click.

### WHY IS REDIS OPTIONAL LOCALLY?

Not every machine has a Redis server installed. Our code tries to connect to
localhost:6379. If Redis is available it uses it; if not, it automatically
falls back to a small in-memory Python cache with the same behaviour (TTL of
3600 seconds). The app never crashes, and it honestly shows which cache
backend is active.

### HOW DOES ONE RECOMMENDATION REQUEST WORK?

```
Customer selected
   ↓
User features (profile + history + current date context)
   ↓
User Tower
   ↓
64D embedding
   ↓
FAISS
   ↓
nearest product embeddings
   ↓
remove purchased products
   ↓
Top 10
```

Step by step:

1. The app takes the selected customer ID.
2. The engine builds the customer's feature row (profile, historical counts,
   favourite colour/garment/group, current month/weekday).
3. The User Tower turns this into a 64-number embedding.
4. FAISS searches the item index and returns more candidates than needed.
5. Products the customer already bought are removed.
6. The top 10 remaining products are joined with product metadata and shown,
   each with a similarity score and a short reason.

The "reason" text is generated AFTER retrieval by comparing product metadata
with the customer's history. It is NOT produced by the neural network itself.

---

## IMPORTANT VIVA QUESTIONS (Q&A)

**1. What backend/model technology are you using?**
Python with TensorFlow/Keras for the Two-Tower model, FAISS for retrieval,
Redis for caching, and Streamlit for the demo.

**2. What is TensorFlow?**
An open-source machine learning library by Google. We use it to build and
train the neural network towers.

**3. What is a Two-Tower model?**
A retrieval model with two separate neural networks: one for users (user
tower) and one for items (item tower). Each produces an embedding, and
recommendations are found by comparing the embeddings.

**4. Why two towers?**
Because the item embeddings of the full product catalogue can be precomputed
once and indexed in FAISS. At serving time we only need one cheap pass of the
user tower and one fast ANN search - no expensive scoring of every product.

**5. What is a user embedding?**
A 64-number vector that represents a customer's taste, produced by the user
tower from their profile and history features.

**6. What is an item embedding?**
A 64-number vector that represents a product, produced by the item tower
from its catalogue metadata.

**7. What features enter the User Tower?**
Customer ID, age, activity flag, historical purchase counts, total spend,
average price, recency, purchase frequency, recent 30-day count, club member
status, fashion news frequency, sales channel, purchase month, weekday, and
favourite colour/garment group/product group from prior purchases.

**8. What features enter the Item Tower?**
Article ID, product type, product group, colour group, garment group, and
index (segment).

**9. What does 64D mean?**
Each customer and product is represented by a vector of 64 numbers.

**10. How does the model learn?**
By gradient descent on a softmax cross-entropy loss: the bought product must
score highest against all in-batch negatives. Embeddings are adjusted a
little every step (Adam optimizer, learning rate 3e-3).

**11. What are positive interactions?**
Real purchases from the training data - pairs of (customer, product) that
actually happened.

**12. What are in-batch negatives?**
The other products in the same training batch act as negative examples, so we
do not need to generate a huge separate negative dataset.

**13. What is FAISS?**
A library for fast nearest-neighbour search over many vectors.

**14. Why FAISS?**
Because searching 4,668 (or millions of) item embeddings one by one is slow;
FAISS does it in milliseconds and scales to very large catalogues.

**15. What is cosine similarity?**
A similarity measure based on the angle between two vectors: 1 = same
direction, 0 = unrelated. Our vectors are length-normalized, so inner product
equals cosine similarity.

**16. How do you evaluate recommendations?**
We hide each test customer's last purchase, ask the model for top-K
recommendations, and check whether the real purchase appears - reporting
Recall@K and NDCG@K. Previously purchased items are excluded from candidates.

**17. What is Recall@10?**
The share of test customers whose actual next purchase appears in our top-10
list.

**18. Current Recall@10?**
Approximately 14% on the current test split (Recall@5 = 7.38%,
Recall@20 = 20.84%).

**19. What is NDCG?**
A ranking metric like Recall@K but position-aware: a hit at rank 1 scores
higher than a hit at rank 10.

**20. Why exclude previously purchased items?**
Customers rarely buy exactly the same article again, and recommending
already-owned items is useless. It also makes evaluation honest: the model
must find NEW products the customer will like.

**21. What is Redis?**
A fast in-memory key-value store, commonly used as a cache.

**22. Why Redis?**
To cache user features and recommendation results, so repeated requests are
served instantly without recomputing embeddings and FAISS searches.

**23. What happens if Redis isn't running?**
The implementation automatically uses an in-memory fallback cache. The app
keeps working and clearly shows "Memory Fallback" in the UI.

**24. Why use Streamlit?**
It allows rapid interactive demonstration of the machine-learning pipeline. A
production system could later expose the model through FastAPI and a separate
frontend.

**25. Why not the full 35GB dataset now?**
We first validate the complete architecture on a representative model-ready
dataset. The full dataset requires distributed processing and longer training.

**26. What have you completed till now?**
Week 1: data cleaning, preprocessing, leakage-safe temporal split
preparation. Week 2: Two-Tower neural network, training, Recall@K / NDCG@K
evaluation. Week 3: embedding export, FAISS retrieval, Redis caching, and the
interactive Streamlit demo.

**27. What remains?**
Production scaling, Airflow scheduling, FastAPI service, full dataset
training and deployment.

**28. Are the metrics in the demo real?**
Yes. They are computed from the actual validation/test interactions during
training and stored in `artifacts/metrics.json`. Nothing is hardcoded.

---

## QUICK DEMO SCRIPT (for review)

1. Run `streamlit run app.py`.
2. Point at the status badges: Model Loaded, 64D embeddings, FAISS engine,
   cache backend (Redis or Memory Fallback).
3. Show the pipeline diagram and the real dataset numbers.
4. Show the model performance cards (real Recall@K / NDCG@K values).
5. Pick a customer with many purchases, show their recent purchase history.
6. Click "Generate Recommendations" and walk through the top-10 cards,
   similarity scores, and the "why" explanations.
7. Open "Technical Details" and show the real user embedding values, the
   number of FAISS candidates searched, and how many purchased items were
   removed.
8. Generate the same customer twice to demonstrate the cache HIT.
