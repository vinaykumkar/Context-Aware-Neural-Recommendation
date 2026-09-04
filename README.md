# AURA Context-Aware-Neural-Recommendation

A smart, data-driven recommendation engine that curates tailored outfit ideas, seasonal staples, and style inspiration based on individual user preferences, browsing history, and real-time trends.

#### Data Architecture, Preprocessing and Feature Engineering

AURA follows a structured data engineering pipeline in which the raw H&M dataset is first cleaned and transformed into reusable Parquet datasets before recommendation modelling. This separation makes the pipeline more memory-efficient, reproducible and suitable for repeated model training.

The three primary datasets are:

Dataset	Key Columns	Purpose
Customers	customer_id, Active, club_member_status, fashion_news_frequency	Customer profile and behavioral features
Articles	article_id, product/category attributes	Product representation and content features
Transactions	t_dat, customer_id, article_id, price	Customer-product interaction history
4.1 Data Preprocessing Pipeline

The preprocessing stage is performed before feature engineering and model training.

Raw CSV Files → Data Validation → Cleaning → Missing-Value Handling → Duplicate Removal → Type Conversion → Feature Engineering → Parquet Storage → Model/Serving Data

The major preprocessing operations include:

Loading customers, articles and transactions.

Validating column names and data types.

Removing duplicate records.

Standardizing categorical values.

Converting transaction dates into appropriate date types.

Handling missing customer attributes.

Handling missing product attributes where required.

Validating customer_id and article_id relationships.

Checking transaction records for invalid or inconsistent values.

Preserving the original datasets separately from model-ready datasets.

Saving processed datasets in Parquet format.

Parquet was selected as the intermediate storage format because it provides columnar storage, compression and efficient selective reading compared with repeatedly processing the original CSV files.

The processed datasets are therefore reusable across EDA, feature engineering, training and serving stages without repeating the complete preprocessing operation.

#### Missing-Value Treatment

Missing values are handled according to the semantic meaning of each feature rather than using a single global imputation strategy.

Examples include:

Missing fashion_news_frequency values are assigned a meaningful "None" category where appropriate.

Binary or derived behavioral indicators are populated according to the available customer information.

Missing numerical values are handled using appropriate statistical or domain-based strategies.

Date-related features are retained as null when the underlying event does not exist rather than introducing misleading dates.

This approach prevents artificial information from being introduced into the recommendation model.

#### Duplicate and Consistency Checks

Duplicate records are identified before generating customer and article features.

The pipeline also validates the relationships:

customer_id → customer profile

article_id → article catalogue

customer_id + article_id → transaction interaction

These checks are important because the recommendation system ultimately joins information from all three datasets.

#### Feature Engineering

Feature engineering transforms the cleaned transaction, customer and article data into behavioral and contextual representations that can be consumed by the recommendation system.

Customer Behavioral Features

Transaction history is aggregated at the customer level to generate features such as:

Feature	Description
  
      purchase_count	          Total number of purchases made by a customer
      unique_articles_count	    Number of distinct articles purchased
      average_price	            Average purchase price
      total_spent	              Aggregate customer spending
      first_purchase_date	      Date of the customer's first recorded purchase
      recency	                  Date of the customer's most recent purchase
      recent_purchase_count	    Number of purchases within a recent period
      purchase_frequency	      Purchase activity relative to recency

These features provide the user tower and the hybrid recommendation layer with information about customer purchasing behavior.

Recency Features

Recency is particularly important in fashion recommendation because customer preferences can change over time.

The system therefore derives temporal features from t_dat, including:

first purchase date

latest purchase date

purchase recency

recent purchase activity

purchase frequency

temporal interaction information

The temporal split used during evaluation ensures that future interactions are not accidentally used to predict earlier interactions.

Article Features

Article metadata is transformed into model-ready categorical or numerical representations.

Relevant catalogue attributes include:

product_type_name
product_group_name
graphical_appearance_name
colour_group_name
department_name
index_name
index_group_name
section_name
garment_group_name

These attributes provide content information about each product and can be used by the item tower and hybrid content-similarity component.

#### Mapping Product Images to Articles and Transactions

A key feature of the AURA application is the ability to allow a user to identify a product visually before retrieving its recommendation information.

The H&M article catalogue contains an article_id that acts as the primary product identifier. Product images are associated with this identifier using an image-to-article mapping.

The mapping workflow is:

Product Image → Image Filename/Identifier → article_id → Article Catalogue → Transaction History → Customer Interactions → Recommendations

The image mapping is maintained separately from the transaction data so that large image collections do not need to be loaded into the recommendation model.

Image Mapping Process
The article catalogue is loaded.
The corresponding product image directory is scanned.
Image filenames are matched with their corresponding article_id.
An article-to-image lookup/index is generated.
The image path or image URL is associated with the corresponding article.
The user can view available product images in the application.
When a user selects an image, the corresponding article_id is identified.
The selected article_id is used to query the article catalogue and transaction data.
Historical purchases involving that article can then be identified.
The recommendation engine uses the selected product and customer context to generate personalized recommendations.

This creates a user-friendly bridge between the visual product catalogue and the structured recommendation data.

Product Selection Workflow

The application can therefore expose products visually rather than requiring the user to remember or manually enter an article identifier.

For example:

    Displayed Product Images
    
    ↓
    
    User selects a product
    
    ↓
    
    Retrieve mapped article_id
    
    ↓
    
    Look up article attributes
    
    ↓
    
    Check transaction/customer interactions
    
    ↓
    
    Generate personalized recommendations
    
    ↓
    
    Display recommended products with images

This approach improves the usability of the recommendation system while preserving the article_id as the common key across the data architecture.

#### Image-to-Transaction Relationship

The image itself is not directly joined to transactions.

Instead, the system uses article_id as the linking key:

Image Mapping
→ article_id

Articles
→ article_id

Transactions
→ article_id

This produces the relationship:

Image ↔ Article ↔ Transaction ↔ Customer

Consequently, when a user selects a product image, the system can determine which article was selected and retrieve the historical customer-product interactions associated with that article.

This design avoids storing image binaries inside the transaction dataset and keeps the recommendation data compact.

#### Model-Ready Parquet Datasets

After preprocessing and feature engineering, the transformed datasets are persisted as Parquet files.

A typical artifact organization is:

    data/
    ├── raw/
    │   ├── customers.csv
    │   ├── articles.csv
    │   └── transactions.csv
    │
    └── processed/
        ├── customers/
        ├── articles/
        └── transactions/

Additional engineered datasets can contain customer behavioral features and article-level features required by the recommendation model.

The Parquet layer acts as the interface between data engineering and machine learning:

Raw CSV → Preprocessing → Feature Engineering → Parquet → Training → Embeddings → FAISS → Recommendations

This also allows the model-training stage to start from already-cleaned and engineered data instead of repeatedly processing millions of transaction records.

