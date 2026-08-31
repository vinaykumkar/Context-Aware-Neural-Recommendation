# Context-Aware-Neural-Recommendation


A smart, data-driven recommendation engine that curates tailored outfit ideas, seasonal staples, and style inspiration based on individual user preferences, browsing history, and real-time trends.

Architecture
Customer
   ↓
User Tower  (customer ID + user/context features)
   ↓
User Embedding (64D, L2-normalized)
   ↓
FAISS Search
   ↓
Top-K Recommendations
Product Metadata
   ↓
Item Tower  (article ID + catalogue features)
   ↓
Item Embedding (64D, L2-normalized)
   ↓
FAISS Index
