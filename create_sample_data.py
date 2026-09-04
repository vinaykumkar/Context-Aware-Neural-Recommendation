import os
import csv
import random
from datetime import datetime, timedelta

def generate_sample_dataset(data_dir=None):
    """
    Generates synthetic sample dataset matching H&M schema if real CSV files are missing.
    """
    if data_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        
    os.makedirs(data_dir, exist_ok=True)
    
    articles_path = os.path.join(data_dir, "articles.csv")
    customers_path = os.path.join(data_dir, "customers.csv")
    transactions_path = os.path.join(data_dir, "transactions_train.csv")

    if os.path.exists(articles_path) and os.path.exists(customers_path) and os.path.exists(transactions_path):
        print(f"[OK] Existing data files detected in '{data_dir}'. Skipping sample generation.")
        return data_dir

    print(f"[INFO] Generating synthetic sample H&M dataset in '{data_dir}' for pipeline verification...")

    # 1. Generate Sample Articles (100 items)
    article_ids = [108775001 + i for i in range(100)]
    product_groups = ["Garment Upper body", "Garment Lower body", "Shoes", "Accessories", "Swimwear"]
    product_types = ["T-shirt", "Trousers", "Dress", "Sneakers", "Socks", "Sweater"]
    colours = ["Black", "White", "Blue", "Red", "Green", "Grey"]

    with open(articles_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "article_id", "product_code", "prod_name", "product_type_no", "product_type_name",
            "product_group_name", "graphical_appearance_no", "graphical_appearance_name",
            "colour_group_code", "colour_group_name", "perceived_colour_value_id",
            "perceived_colour_value_name", "perceived_colour_master_id", "perceived_colour_master_name",
            "department_no", "department_name", "index_code", "index_name", "index_group_no",
            "index_group_name", "section_no", "section_name", "garment_group_no", "garment_group_name", "detail_desc"
        ])
        for aid in article_ids:
            ptype = random.choice(product_types)
            pgroup = random.choice(product_groups)
            colour = random.choice(colours)
            writer.writerow([
                aid, aid // 10, f"Sample {ptype}", 101, ptype,
                pgroup, 101001, "Solid",
                9, colour, 1, "Dark", 1, "Black",
                1001, "Tops", "A", "Ladieswear", 1, "Ladieswear",
                15, "Womens Everyday", 1002, "Jersey Basic",
                f"High quality sample {ptype} in {colour}." if random.random() > 0.1 else None
            ])

    # 2. Generate Sample Customers (50 users)
    customer_ids = [f"cust_{i:04d}_{random.randint(1000, 9999)}" for i in range(50)]
    club_statuses = ["ACTIVE", "PRE-CREATE", "LEFT CLUB", None]
    news_freqs = ["NONE", "Regularly", "Monthly", None]

    with open(customers_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "customer_id", "FN", "Active", "club_member_status",
            "fashion_news_frequency", "age", "postal_code"
        ])
        for cid in customer_ids:
            age = random.randint(18, 70) if random.random() > 0.1 else None
            status = random.choice(club_statuses)
            freq = random.choice(news_freqs)
            fn_val = 1.0 if freq in ["Regularly", "Monthly"] else None
            active_val = 1.0 if status == "ACTIVE" else None
            writer.writerow([
                cid, fn_val, active_val, status, freq, age, f"post_{random.randint(100,999)}"
            ])

    # 3. Generate Sample Transactions (250 purchase events)
    start_date = datetime(2026, 6, 1)
    with open(transactions_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["t_dat", "customer_id", "article_id", "price", "sales_channel_id"])
        # Reserve 10 customers and 15 articles to be cold-start (no transactions)
        active_cids = customer_ids[:40]
        active_aids = article_ids[:85]

        for _ in range(250):
            t_date = (start_date + timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d")
            cid = random.choice(active_cids)
            aid = random.choice(active_aids)
            price = round(random.uniform(0.01, 0.10), 4)
            channel = random.choice([1, 2])
            writer.writerow([t_date, cid, aid, price, channel])

    print(f"[OK] Generated sample dataset in '{data_dir}':")
    print(f"   - articles.csv (100 rows)")
    print(f"   - customers.csv (50 rows, including cold-start users)")
    print(f"   - transactions_train.csv (250 transactions, including cold-start items)")
    return data_dir

if __name__ == "__main__":
    generate_sample_dataset()
