import os
import json
import shutil
import zipfile

import pandas as pd
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = FastAPI(
    title="Context-Aware Neural Recommendation System",
    description="Week 1 Data Processing and Feature Engineering Dashboard",
    version="1.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed_data")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


# ============================================================
# DATA LOADING FUNCTIONS
# ============================================================

def read_json_file(file_path):
    """Read a JSON file if it exists."""
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print(f"[WARNING] Could not read JSON file: {error}")
        return {}


def load_vocabularies():
    """Load generated categorical vocabularies."""
    vocabulary_file = os.path.join(
        PROCESSED_DIR,
        "vocabularies.json"
    )

    return read_json_file(vocabulary_file)


def load_customers():
    """Load processed customer data."""
    file_path = os.path.join(
        PROCESSED_DIR,
        "customers_processed.parquet"
    )

    if not os.path.exists(file_path):
        return pd.DataFrame()

    try:
        return pd.read_parquet(file_path)
    except Exception as error:
        print(f"[WARNING] Could not load customers: {error}")
        return pd.DataFrame()


def load_articles():
    """Load processed article data."""
    parquet_file = os.path.join(
        PROCESSED_DIR,
        "articles_processed.parquet"
    )

    csv_file = os.path.join(
        PROCESSED_DIR,
        "articles_processed.csv"
    )

    try:
        if os.path.exists(parquet_file):
            if os.path.getsize(parquet_file) > 0:
                return pd.read_parquet(parquet_file)

        if os.path.exists(csv_file):
            return pd.read_csv(csv_file)

    except Exception as error:
        print(f"[WARNING] Could not load articles: {error}")

    return pd.DataFrame()


def load_transactions():
    """Load processed transaction data."""
    file_path = os.path.join(
        PROCESSED_DIR,
        "transactions_processed.parquet"
    )

    if not os.path.exists(file_path):
        return pd.DataFrame()

    try:
        return pd.read_parquet(file_path)
    except Exception as error:
        print(f"[WARNING] Could not load transactions: {error}")
        return pd.DataFrame()


# ============================================================
# API: DASHBOARD STATISTICS
# ============================================================

@app.get("/api/stats")
def dashboard_statistics():

    vocabulary_data = load_vocabularies()
    summary = vocabulary_data.get(
        "summary_statistics",
        {}
    )

    customers = load_customers()
    articles = load_articles()

    age_distribution = {}

    if (
        not customers.empty
        and "age_group" in customers.columns
    ):
        age_distribution = (
            customers["age_group"]
            .value_counts()
            .to_dict()
        )

    if (
        not customers.empty
        and "user_total_purchases" in customers.columns
    ):
        cold_users = int(
            (customers["user_total_purchases"] == 0).sum()
        )
    else:
        cold_users = 0

    if (
        not articles.empty
        and "pop_total_sales" in articles.columns
    ):
        cold_articles = int(
            (articles["pop_total_sales"] == 0).sum()
        )
    else:
        cold_articles = 0

    return {
        "summary": summary,
        "age_distribution": age_distribution,
        "cold_users": cold_users,
        "cold_articles": cold_articles
    }


# ============================================================
# API: VOCABULARIES
# ============================================================

@app.get("/api/vocabularies")
def get_vocabularies():

    vocabulary_data = load_vocabularies()

    return vocabulary_data.get(
        "categorical_vocabularies",
        {}
    )


# ============================================================
# API: CUSTOMERS
# ============================================================

@app.get("/api/customers")
def get_customers(limit: int = 50):

    customers = load_customers()

    if customers.empty:
        return []

    limit = max(1, min(limit, 500))

    result = customers.head(limit).copy()

    if "recent_article_ids" in result.columns:

        result["recent_article_ids"] = result[
            "recent_article_ids"
        ].apply(
            lambda value:
            list(value)
            if isinstance(value, (list, tuple, pd.Series))
            else []
        )

    return result.to_dict(orient="records")


# ============================================================
# API: ARTICLES
# ============================================================

@app.get("/api/articles")
def get_articles(limit: int = 50):

    articles = load_articles()

    if articles.empty:
        return []

    limit = max(1, min(limit, 500))

    if "pop_total_sales" in articles.columns:

        result = (
            articles
            .sort_values(
                by="pop_total_sales",
                ascending=False
            )
            .head(limit)
        )

    else:
        result = articles.head(limit)

    return result.to_dict(orient="records")


# ============================================================
# API: TRANSACTIONS
# ============================================================

@app.get("/api/transactions")
def get_transactions(limit: int = 50):

    transactions = load_transactions()

    if transactions.empty:
        return []

    limit = max(1, min(limit, 500))

    return transactions.head(limit).to_dict(
        orient="records"
    )


# ============================================================
# API: FILE UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_resource(
    file: UploadFile = File(...)
):

    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "No file was selected."
            }
        )

    original_name = file.filename
    filename = original_name.lower()

    save_path = os.path.join(
        DATA_DIR,
        original_name
    )

    try:

        # ----------------------------------------------------
        # Save uploaded file
        # ----------------------------------------------------

        with open(save_path, "wb") as output_file:
            shutil.copyfileobj(
                file.file,
                output_file
            )

        print(
            f"[INFO] Uploaded: {original_name}"
        )

        # ----------------------------------------------------
        # Process ZIP archive
        # ----------------------------------------------------

        if filename.endswith(".zip"):

            print("[INFO] Extracting ZIP archive...")

            with zipfile.ZipFile(
                save_path,
                "r"
            ) as archive:

                archive.extractall(DATA_DIR)

            os.remove(save_path)

        # ----------------------------------------------------
        # Process CSV / Parquet
        # ----------------------------------------------------

        elif (
            filename.endswith(".csv")
            or filename.endswith(".parquet")
        ):

            if filename.endswith(".parquet"):
                dataframe = pd.read_parquet(
                    save_path
                )
            else:
                dataframe = pd.read_csv(
                    save_path
                )

            # Articles dataset
            if (
                "article_id" in dataframe.columns
                and "product_code" in dataframe.columns
            ):

                output_file = os.path.join(
                    DATA_DIR,
                    "articles.csv"
                )

                dataframe.to_csv(
                    output_file,
                    index=False
                )

                print(
                    "[INFO] Identified articles dataset."
                )

            # Customers dataset
            elif (
                "customer_id" in dataframe.columns
                and "club_member_status" in dataframe.columns
            ):

                output_file = os.path.join(
                    DATA_DIR,
                    "customers.csv"
                )

                dataframe.to_csv(
                    output_file,
                    index=False
                )

                print(
                    "[INFO] Identified customers dataset."
                )

            # Transactions dataset
            elif (
                "t_dat" in dataframe.columns
                and "price" in dataframe.columns
            ):

                output_file = os.path.join(
                    DATA_DIR,
                    "transactions_train.csv"
                )

                dataframe.to_csv(
                    output_file,
                    index=False
                )

                print(
                    "[INFO] Identified transactions dataset."
                )

        # ----------------------------------------------------
        # Run Week 1 pipeline
        # ----------------------------------------------------

        try:

            from run_week1 import (
                execute_week1_pipeline
            )

            execute_week1_pipeline()

            return JSONResponse(
                content={
                    "status": "success",
                    "message": (
                        f"'{original_name}' uploaded successfully "
                        "and the Week 1 pipeline was executed."
                    )
                }
            )

        except Exception as pipeline_error:

            print(
                f"[WARNING] Pipeline error: "
                f"{pipeline_error}"
            )

            return JSONResponse(
                content={
                    "status": "warning",
                    "message": (
                        f"'{original_name}' was uploaded, "
                        "but the pipeline could not be completed: "
                        f"{pipeline_error}"
                    )
                }
            )

    except Exception as error:

        print(
            f"[ERROR] Upload failed: {error}"
        )

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": (
                    f"Unable to process '{original_name}': "
                    f"{error}"
                )
            }
        )


# ============================================================
# HTML DASHBOARD
# ============================================================

@app.get("/", response_class=HTMLResponse)
def dashboard():

    html = """
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        Context-Aware Recommendation Engine
    </title>

    <script src="https://cdn.tailwindcss.com"></script>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <link
        rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    >

    <style>

        body {
            background:
                radial-gradient(
                    circle at top right,
                    #172554 0%,
                    #020617 45%
                );
        }

        .header-gradient {
            background:
                linear-gradient(
                    135deg,
                    #111827,
                    #020617
                );
        }

        .active-tab {
            color: #60a5fa;
            border-bottom: 3px solid #3b82f6;
            font-weight: 600;
        }

        .upload-zone {
            border: 2px dashed #3b82f6;
            background: rgba(59, 130, 246, 0.05);
        }

        .upload-zone:hover {
            background: rgba(59, 130, 246, 0.10);
        }

        .metric-card {
            transition: transform 0.2s ease;
        }

        .metric-card:hover {
            transform: translateY(-3px);
        }

    </style>

</head>


<body class="text-slate-100 min-h-screen font-sans">


<!-- ======================================================
     HEADER
======================================================= -->

<header
    class="header-gradient border-b border-slate-800 shadow-xl"
>

    <div
        class="max-w-7xl mx-auto px-6 py-6
               flex flex-col md:flex-row
               justify-between items-center gap-5"
    >

        <div>

            <div class="flex items-center gap-3">

                <div
                    class="bg-blue-600
                           rounded-xl
                           p-3
                           shadow-lg"
                >

                    <i
                        class="fa-solid fa-brain text-xl"
                    ></i>

                </div>

                <h1
                    class="text-2xl font-bold"
                >
                    Context-Aware Neural
                    Recommendation Engine
                </h1>

            </div>

            <p
                class="text-sm text-slate-400 mt-2"
            >
                Week 1 — Distributed Data Processing
                & Feature Engineering
            </p>

        </div>


        <button
            onclick="changeTab('upload')"
            class="bg-blue-600
                   hover:bg-blue-500
                   px-5 py-2.5
                   rounded-lg
                   font-semibold
                   text-sm
                   transition"
        >

            <i
                class="fa-solid fa-cloud-arrow-up mr-2"
            ></i>

            Upload Resources

        </button>

    </div>

</header>


<!-- ======================================================
     MAIN CONTENT
======================================================= -->

<main
    class="max-w-7xl mx-auto px-6 py-6 space-y-6"
>


<!-- ======================================================
     STATISTICS
======================================================= -->

<section
    class="grid
           grid-cols-1
           sm:grid-cols-2
           lg:grid-cols-4
           gap-4"
>


    <!-- Users -->

    <div
        class="metric-card
               bg-slate-800/80
               border border-slate-700
               rounded-xl
               p-5"
    >

        <div
            class="flex justify-between"
        >

            <div>

                <p
                    class="text-xs
                           uppercase
                           text-slate-400
                           font-semibold"
                >
                    Total Users
                </p>

                <h2
                    id="total-users"
                    class="text-3xl
                           font-extrabold
                           mt-2"
                >
                    0
                </h2>

            </div>

            <span
                class="bg-blue-500/10
                       text-blue-400
                       rounded-lg
                       p-3"
            >

                <i class="fa-solid fa-users"></i>

            </span>

        </div>

        <p
            class="text-xs text-slate-400 mt-3"
        >

            <span
                id="cold-users"
                class="text-cyan-400 font-semibold"
            >
                0
            </span>

            cold-start users

        </p>

    </div>


    <!-- Articles -->

    <div
        class="metric-card
               bg-slate-800/80
               border border-slate-700
               rounded-xl
               p-5"
    >

        <div
            class="flex justify-between"
        >

            <div>

                <p
                    class="text-xs
                           uppercase
                           text-slate-400
                           font-semibold"
                >
                    Total Articles
                </p>

                <h2
                    id="total-articles"
                    class="text-3xl
                           font-extrabold
                           mt-2"
                >
                    0
                </h2>

            </div>

            <span
                class="bg-indigo-500/10
                       text-indigo-400
                       rounded-lg
                       p-3"
            >

                <i class="fa-solid fa-shirt"></i>

            </span>

        </div>

        <p
            class="text-xs text-slate-400 mt-3"
        >

            <span
                id="cold-articles"
                class="text-amber-400 font-semibold"
            >
                0
            </span>

            cold items

        </p>

    </div>


    <!-- Transactions -->

    <div
        class="metric-card
               bg-slate-800/80
               border border-slate-700
               rounded-xl
               p-5"
    >

        <div
            class="flex justify-between"
        >

            <div>

                <p
                    class="text-xs
                           uppercase
                           text-slate-400
                           font-semibold"
                >
                    Transactions
                </p>

                <h2
                    id="total-transactions"
                    class="text-3xl
                           font-extrabold
                           mt-2"
                >
                    0
                </h2>

            </div>

            <span
                class="bg-emerald-500/10
                       text-emerald-400
                       rounded-lg
                       p-3"
            >

                <i class="fa-solid fa-receipt"></i>

            </span>

        </div>

        <p
            class="text-xs
                   text-slate-400
                   mt-3"
        >
            Temporal features included
        </p>

    </div>


    <!-- Artifacts -->

    <div
        class="metric-card
               bg-slate-800/80
               border border-slate-700
               rounded-xl
               p-5"
    >

        <div
            class="flex justify-between"
        >

            <div>

                <p
                    class="text-xs
                           uppercase
                           text-slate-400
                           font-semibold"
                >
                    Output Artifacts
                </p>

                <h2
                    class="text-3xl
                           font-extrabold
                           mt-2
                           text-emerald-400"
                >
                    4 / 4
                </h2>

            </div>

            <span
                class="bg-purple-500/10
                       text-purple-400
                       rounded-lg
                       p-3"
            >

                <i class="fa-solid fa-database"></i>

            </span>

        </div>

        <p
            class="text-xs
                   text-slate-400
                   mt-3"
        >
            Processed datasets & vocabularies
        </p>

    </div>

</section>


<!-- ======================================================
     NAVIGATION
======================================================= -->

<nav
    class="border-b border-slate-800
           flex gap-6
           overflow-x-auto"
>

    <button
        id="tab-overview"
        onclick="changeTab('overview')"
        class="active-tab py-3 px-2 whitespace-nowrap"
    >

        <i class="fa-solid fa-chart-pie mr-2"></i>
        Overview

    </button>


    <button
        id="tab-upload"
        onclick="changeTab('upload')"
        class="text-slate-400
               py-3 px-2
               whitespace-nowrap"
    >

        <i class="fa-solid fa-cloud-arrow-up mr-2"></i>
        Upload

    </button>


    <button
        id="tab-vocabularies"
        onclick="changeTab('vocabularies')"
        class="text-slate-400
               py-3 px-2
               whitespace-nowrap"
    >

        <i class="fa-solid fa-tags mr-2"></i>
        Vocabularies

    </button>


    <button
        id="tab-customers"
        onclick="changeTab('customers')"
        class="text-slate-400
               py-3 px-2
               whitespace-nowrap"
    >

        <i class="fa-solid fa-users mr-2"></i>
        User Sequences

    </button>


    <button
        id="tab-articles"
        onclick="changeTab('articles')"
        class="text-slate-400
               py-3 px-2
               whitespace-nowrap"
    >

        <i class="fa-solid fa-fire mr-2"></i>
        Popularity

    </button>

</nav>


<!-- ======================================================
     OVERVIEW
======================================================= -->

<section
    id="content-overview"
    class="space-y-6"
>

    <div
        class="grid
               grid-cols-1
               lg:grid-cols-2
               gap-6"
    >


        <!-- Age chart -->

        <div
            class="bg-slate-800/70
                   border border-slate-700
                   rounded-xl
                   p-6"
        >

            <h3
                class="text-lg font-bold mb-5"
            >

                <i
                    class="fa-solid
                           fa-chart-doughnut
                           text-blue-400 mr-2"
                ></i>

                Customer Age Distribution

            </h3>

            <div class="h-72">

                <canvas
                    id="ageChart"
                ></canvas>

            </div>

        </div>


        <!-- Week 1 checklist -->

        <div
            class="bg-slate-800/70
                   border border-slate-700
                   rounded-xl
                   p-6"
        >

            <h3
                class="text-lg
                       font-bold
                       mb-5"
            >

                <i
                    class="fa-solid
                           fa-list-check
                           text-emerald-400 mr-2"
                ></i>

                Week 1 Requirements

            </h3>


            <div class="space-y-3">

                <div class="check-item">
                    <i
                        class="fa-solid
                               fa-circle-check
                               text-emerald-400 mr-2"
                    ></i>

                    PySpark data processing
                </div>


                <div class="check-item">
                    <i
                        class="fa-solid
                               fa-circle-check
                               text-emerald-400 mr-2"
                    ></i>

                    Missing value imputation
                </div>


                <div class="check-item">
                    <i
                        class="fa-solid
                               fa-circle-check
                               text-emerald-400 mr-2"
                    ></i>

                    User & item cold-start strategy
                </div>


                <div class="check-item">
                    <i
                        class="fa-solid
                               fa-circle-check
                               text-emerald-400 mr-2"
                    ></i>

                    Recency & temporal features
                </div>


                <div class="check-item">
                    <i
                        class="fa-solid
                               fa-circle-check
                               text-emerald-400 mr-2"
                    ></i>

                    Customer interaction sequences
                </div>


                <div class="check-item">
                    <i
                        class="fa-solid
                               fa-circle-check
                               text-emerald-400 mr-2"
                    ></i>

                    Feature vocabularies & Parquet exports
                </div>

            </div>

        </div>

    </div>

</section>


<!-- ======================================================
     UPLOAD TAB
======================================================= -->

<section
    id="content-upload"
    class="hidden"
>

    <div
        class="max-w-3xl
               mx-auto
               bg-slate-800/70
               border border-slate-700
               rounded-xl
               p-8"
    >

        <div class="text-center">

            <div
                class="inline-block
                       bg-blue-500/10
                       text-blue-400
                       p-4
                       rounded-full
                       text-3xl"
            >

                <i
                    class="fa-solid fa-file-arrow-up"
                ></i>

            </div>

            <h2
                class="text-xl
                       font-bold
                       mt-4"
            >
                Upload Dataset Resources
            </h2>

            <p
                class="text-sm
                       text-slate-400
                       mt-2"
            >
                Upload CSV, Parquet or ZIP
                datasets and execute the
                Week 1 pipeline.
            </p>

        </div>


        <div
            class="upload-zone
                   rounded-xl
                   p-10
                   mt-6
                   text-center
                   cursor-pointer"
            onclick="
                document
                .getElementById('file-input')
                .click()
            "
        >

            <i
                class="fa-solid
                       fa-cloud-arrow-up
                       text-4xl
                       text-blue-400"
            ></i>

            <p
                class="font-semibold
                       mt-3"
            >
                Click to select a file
            </p>

            <p
                class="text-xs
                       text-slate-400
                       mt-2"
            >
                Supported:
                CSV, Parquet, JSON, ZIP
            </p>

            <input
                id="file-input"
                type="file"
                class="hidden"
                accept=".csv,.parquet,.json,.zip"
                onchange="uploadFile(event)"
            >

        </div>


        <div
            id="upload-status"
            class="hidden
                   mt-5
                   p-4
                   rounded-lg
                   text-sm"
        ></div>

    </div>

</section>


<!-- ======================================================
     VOCABULARIES
======================================================= -->

<section
    id="content-vocabularies"
    class="hidden"
>

    <div
        class="bg-slate-800/70
               border border-slate-700
               rounded-xl
               p-6"
    >

        <h2
            class="text-lg
                   font-bold"
        >

            <i
                class="fa-solid
                       fa-tags
                       text-indigo-400 mr-2"
            ></i>

            Categorical Vocabularies

        </h2>

        <p
            class="text-sm
                   text-slate-400
                   mt-2 mb-6"
        >
            These vocabularies can later be used
            by TensorFlow Recommenders lookup
            and embedding layers.
        </p>

        <div
            id="vocabulary-container"
            class="grid
                   grid-cols-1
                   md:grid-cols-2
                   gap-4"
        ></div>

    </div>

</section>


<!-- ======================================================
     CUSTOMERS
======================================================= -->

<section
    id="content-customers"
    class="hidden"
>

    <div
        class="bg-slate-800/70
               border border-slate-700
               rounded-xl
               p-6
               overflow-x-auto"
    >

        <h2
            class="text-lg
                   font-bold mb-5"
        >

            <i
                class="fa-solid
                       fa-user-group
                       text-blue-400 mr-2"
            ></i>

            Customer Interaction Sequences

        </h2>

        <table
            class="w-full text-sm"
        >

            <thead
                class="text-xs
                       uppercase
                       text-slate-400
                       bg-slate-900"
            >

                <tr>

                    <th class="p-3 text-left">
                        Customer ID
                    </th>

                    <th class="p-3 text-left">
                        Age
                    </th>

                    <th class="p-3 text-left">
                        Age Group
                    </th>

                    <th class="p-3 text-left">
                        Club Status
                    </th>

                    <th class="p-3 text-left">
                        Active
                    </th>

                    <th class="p-3 text-left">
                        Recent Articles
                    </th>

                </tr>

            </thead>

            <tbody
                id="customers-body"
                class="divide-y divide-slate-800"
            ></tbody>

        </table>

    </div>

</section>


<!-- ======================================================
     ARTICLES
======================================================= -->

<section
    id="content-articles"
    class="hidden"
>

    <div
        class="bg-slate-800/70
               border border-slate-700
               rounded-xl
               p-6
               overflow-x-auto"
    >

        <h2
            class="text-lg
                   font-bold mb-5"
        >

            <i
                class="fa-solid
                       fa-fire
                       text-amber-400 mr-2"
            ></i>

            Article Popularity Ranking

        </h2>

        <table
            class="w-full text-sm"
        >

            <thead
                class="text-xs
                       uppercase
                       text-slate-400
                       bg-slate-900"
            >

                <tr>

                    <th class="p-3 text-left">
                        Article ID
                    </th>

                    <th class="p-3 text-left">
                        Product
                    </th>

                    <th class="p-3 text-left">
                        Product Type
                    </th>

                    <th class="p-3 text-left">
                        Garment Group
                    </th>

                    <th class="p-3 text-left">
                        Sales
                    </th>

                    <th class="p-3 text-left">
                        Avg Price
                    </th>

                </tr>

            </thead>

            <tbody
                id="articles-body"
                class="divide-y divide-slate-800"
            ></tbody>

        </table>

    </div>

</section>


</main>


<!-- ======================================================
     JAVASCRIPT
======================================================= -->

<script>

let ageChart = null;


/* --------------------------------------------------------
   TAB MANAGEMENT
--------------------------------------------------------- */

function changeTab(tabName) {

    const tabs = [
        "overview",
        "upload",
        "vocabularies",
        "customers",
        "articles"
    ];

    tabs.forEach(function(tab) {

        document
            .getElementById("content-" + tab)
            .classList
            .add("hidden");

        document
            .getElementById("tab-" + tab)
            .className =
                "text-slate-400 py-3 px-2 whitespace-nowrap";

    });


    document
        .getElementById("content-" + tabName)
        .classList
        .remove("hidden");


    document
        .getElementById("tab-" + tabName)
        .className =
            "active-tab py-3 px-2 whitespace-nowrap";
}


/* --------------------------------------------------------
   LOAD DASHBOARD DATA
--------------------------------------------------------- */

async function loadDashboard() {

    try {

        /* Stats */

        const statsResponse =
            await fetch("/api/stats");

        const stats =
            await statsResponse.json();

        const summary =
            stats.summary || {};


        document.getElementById(
            "total-users"
        ).innerText =
            summary.total_users || 0;


        document.getElementById(
            "total-articles"
        ).innerText =
            summary.total_articles || 0;


        document.getElementById(
            "total-transactions"
        ).innerText =
            summary.total_transactions || 0;


        document.getElementById(
            "cold-users"
        ).innerText =
            stats.cold_users || 0;


        document.getElementById(
            "cold-articles"
        ).innerText =
            stats.cold_articles || 0;


        /* Age chart */

        renderAgeChart(
            stats.age_distribution || {}
        );


        /* Other dashboard sections */

        await loadVocabularies();
        await loadCustomers();
        await loadArticles();

    }

    catch (error) {

        console.error(
            "Dashboard loading error:",
            error
        );

    }

}


/* --------------------------------------------------------
   AGE CHART
--------------------------------------------------------- */

function renderAgeChart(ageData) {

    const canvas =
        document.getElementById(
            "ageChart"
        );

    if (ageChart) {
        ageChart.destroy();
    }


    ageChart = new Chart(
        canvas,
        {
            type: "doughnut",

            data: {

                labels:
                    Object.keys(ageData),

                datasets: [

                    {
                        data:
                            Object.values(ageData),

                        backgroundColor: [
                            "#3b82f6",
                            "#10b981",
                            "#f59e0b",
                            "#8b5cf6"
                        ]
                    }

                ]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                plugins: {

                    legend: {

                        position: "bottom",

                        labels: {
                            color: "#94a3b8"
                        }

                    }

                }

            }

        }
    );

}


/* --------------------------------------------------------
   VOCABULARIES
--------------------------------------------------------- */

async function loadVocabularies() {

    const response =
        await fetch("/api/vocabularies");

    const vocabularies =
        await response.json();

    const container =
        document.getElementById(
            "vocabulary-container"
        );

    container.innerHTML = "";


    Object.entries(vocabularies)
        .forEach(function([name, values]) {

            const card =
                document.createElement("div");

            card.className =
                "bg-slate-900 border " +
                "border-slate-700 rounded-lg p-4";


            const visibleValues =
                values.slice(0, 8);


            let tags = "";

            visibleValues.forEach(
                function(value) {

                    tags += `
                        <span
                            class="
                                bg-slate-800
                                border
                                border-slate-700
                                rounded
                                px-2
                                py-1
                                text-xs
                                text-slate-300
                            "
                        >
                            ${value}
                        </span>
                    `;

                }
            );


            if (values.length > 8) {

                tags += `
                    <span
                        class="
                            text-xs
                            text-slate-500
                            px-2
                            py-1
                        "
                    >
                        +${values.length - 8} more
                    </span>
                `;

            }


            card.innerHTML = `

                <div
                    class="
                        flex
                        justify-between
                        items-center
                        mb-3
                    "
                >

                    <span
                        class="
                            font-bold
                            text-slate-200
                        "
                    >
                        ${name}
                    </span>

                    <span
                        class="
                            text-xs
                            bg-blue-500/20
                            text-blue-300
                            px-2
                            py-1
                            rounded
                        "
                    >
                        ${values.length} categories
                    </span>

                </div>

                <div
                    class="
                        flex
                        flex-wrap
                        gap-2
                    "
                >
                    ${tags}
                </div>

            `;


            container.appendChild(card);

        });

}


/* --------------------------------------------------------
   CUSTOMERS
--------------------------------------------------------- */

async function loadCustomers() {

    const response =
        await fetch(
            "/api/customers?limit=15"
        );

    const customers =
        await response.json();

    const table =
        document.getElementById(
            "customers-body"
        );

    table.innerHTML = "";


    customers.forEach(function(customer) {

        const row =
            document.createElement("tr");


        const recent =
            (
                customer.recent_article_ids
                || []
            )
            .slice(0, 4)
            .join(", ");


        const active =
            customer.Active === 1
            || customer.Active === 1.0;


        row.innerHTML = `

            <td
                class="
                    p-3
                    font-mono
                    text-xs
                    text-blue-400
                "
            >
                ${customer.customer_id || "N/A"}
            </td>

            <td class="p-3">
                ${customer.age || "N/A"}
            </td>

            <td class="p-3">
                ${customer.age_group || "N/A"}
            </td>

            <td
                class="
                    p-3
                    text-slate-400
                "
            >
                ${customer.club_member_status || "N/A"}
            </td>

            <td class="p-3">

                ${
                    active
                    ? `
                        <span
                            class="text-emerald-400"
                        >
                            <i
                                class="
                                    fa-solid
                                    fa-check
                                "
                            ></i>
                            Active
                        </span>
                    `
                    : `
                        <span
                            class="text-slate-500"
                        >
                            Inactive
                        </span>
                    `
                }

            </td>

            <td
                class="
                    p-3
                    font-mono
                    text-xs
                    text-slate-400
                "
            >
                ${
                    recent
                    || "No purchase history"
                }
            </td>

        `;


        table.appendChild(row);

    });

}


/* --------------------------------------------------------
   ARTICLES
--------------------------------------------------------- */

async function loadArticles() {

    const response =
        await fetch(
            "/api/articles?limit=15"
        );

    const articles =
        await response.json();

    const table =
        document.getElementById(
            "articles-body"
        );

    table.innerHTML = "";


    articles.forEach(function(article) {

        const row =
            document.createElement("tr");


        const sales =
            article.pop_total_sales || 0;


        const price =
            article.article_avg_price
            ? "$" +
              Number(
                  article.article_avg_price
              ).toFixed(4)
            : "$0.0000";


        row.innerHTML = `

            <td
                class="
                    p-3
                    font-mono
                    text-xs
                    text-indigo-400
                "
            >
                ${article.article_id || "N/A"}
            </td>

            <td
                class="
                    p-3
                    font-semibold
                "
            >
                ${article.prod_name || "N/A"}
            </td>

            <td
                class="
                    p-3
                    text-slate-400
                "
            >
                ${article.product_type_name || "N/A"}
            </td>

            <td
                class="
                    p-3
                    text-slate-400
                "
            >
                ${article.garment_group_name || "N/A"}
            </td>

            <td
                class="
                    p-3
                    font-bold
                    text-amber-400
                "
            >
                ${sales}
            </td>

            <td
                class="
                    p-3
                    font-mono
                "
            >
                ${price}
            </td>

        `;


        table.appendChild(row);

    });

}


/* --------------------------------------------------------
   FILE UPLOAD
--------------------------------------------------------- */

async function uploadFile(event) {

    const selectedFile =
        event.target.files[0];


    if (!selectedFile) {
        return;
    }


    const status =
        document.getElementById(
            "upload-status"
        );


    status.className =
        "mt-5 p-4 rounded-lg text-sm " +
        "bg-blue-500/20 text-blue-300 " +
        "border border-blue-500/30";


    status.innerHTML = `
        <i
            class="
                fa-solid
                fa-spinner
                fa-spin
                mr-2
            "
        ></i>

        Uploading
        <strong>
            ${selectedFile.name}
        </strong>
        and processing the dataset...
    `;


    const formData =
        new FormData();


    formData.append(
        "file",
        selectedFile
    );


    try {

        const response =
            await fetch(
                "/api/upload",
                {
                    method: "POST",
                    body: formData
                }
            );


        const result =
            await response.json();


        if (result.status === "success") {

            status.className =
                "mt-5 p-4 rounded-lg text-sm " +
                "bg-emerald-500/20 " +
                "text-emerald-300 " +
                "border border-emerald-500/30";


            status.innerHTML = `
                <i
                    class="
                        fa-solid
                        fa-circle-check
                        mr-2
                    "
                ></i>

                ${result.message}
            `;

        }

        else {

            status.className =
                "mt-5 p-4 rounded-lg text-sm " +
                "bg-amber-500/20 " +
                "text-amber-300 " +
                "border border-amber-500/30";


            status.innerHTML = `
                <i
                    class="
                        fa-solid
                        fa-triangle-exclamation
                        mr-2
                    "
                ></i>

                ${result.message}
            `;

        }


        await loadDashboard();

    }

    catch (error) {

        status.className =
            "mt-5 p-4 rounded-lg text-sm " +
            "bg-red-500/20 text-red-300 " +
            "border border-red-500/30";


        status.innerHTML = `
            <i
                class="
                    fa-solid
                    fa-circle-xmark
                    mr-2
                "
            ></i>

            Upload failed:
            ${error.message}
        `;

    }

}


/* --------------------------------------------------------
   INITIALIZE DASHBOARD
--------------------------------------------------------- */

window.addEventListener(
    "load",
    loadDashboard
);

</script>


</body>

</html>
"""

    return HTMLResponse(content=html)


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    print(
        "[INFO] Starting Context-Aware "
        "Recommendation Dashboard..."
    )

    print(
        "[INFO] Open: http://localhost:8000"
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
