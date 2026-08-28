import os
import json
import shutil
import zipfile
import pandas as pd
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="Context-Aware Neural Recommendation System - Week 1 Dashboard")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed_data")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def load_vocabularies():
    vocab_path = os.path.join(PROCESSED_DIR, "vocabularies.json")
    if os.path.exists(vocab_path):
        with open(vocab_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_customers():
    path = os.path.join(PROCESSED_DIR, "customers_processed.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame()

def load_articles():
    parquet_path = os.path.join(PROCESSED_DIR, "articles_processed.parquet")
    csv_path = os.path.join(PROCESSED_DIR, "articles_processed.csv")
    if os.path.exists(parquet_path) and os.path.getsize(parquet_path) > 0:
        return pd.read_parquet(parquet_path)
    elif os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

def load_transactions():
    path = os.path.join(PROCESSED_DIR, "transactions_processed.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame()

@app.get("/api/stats")
def get_stats():
    vocab = load_vocabularies()
    stats = vocab.get("summary_statistics", {})
    customers = load_customers()
    articles = load_articles()
    
    age_dist = {}
    if not customers.empty and "age_group" in customers.columns:
        age_dist = customers["age_group"].value_counts().to_dict()

    return {
        "summary": stats,
        "age_distribution": age_dist,
        "cold_users": int((customers["user_total_purchases"] == 0).sum()) if "user_total_purchases" in customers.columns else 0,
        "cold_articles": int((articles["pop_total_sales"] == 0).sum()) if "pop_total_sales" in articles.columns else 0
    }

@app.get("/api/vocabularies")
def get_vocabularies():
    vocab = load_vocabularies()
    return vocab.get("categorical_vocabularies", {})

@app.get("/api/customers")
def get_customers(limit: int = 50):
    customers = load_customers()
    if customers.empty:
        return []
    sample = customers.head(limit).copy()
    if "recent_article_ids" in sample.columns:
        sample["recent_article_ids"] = sample["recent_article_ids"].apply(
            lambda x: list(x) if isinstance(x, (list, pd.Series)) else []
        )
    return sample.to_dict(orient="records")

@app.get("/api/articles")
def get_articles(limit: int = 50):
    articles = load_articles()
    if articles.empty:
        return []
    sample = articles.sort_values(by="pop_total_sales", ascending=False).head(limit)
    return sample.to_dict(orient="records")

@app.get("/api/transactions")
def get_transactions(limit: int = 50):
    txns = load_transactions()
    if txns.empty:
        return []
    return txns.head(limit).to_dict(orient="records")

@app.post("/api/upload")
async def upload_resource(file: UploadFile = File(...)):
    """
    Accepts resource uploads in CSV, Parquet, JSON, or ZIP format and updates the recommendation pipeline.
    """
    filename = file.filename.lower()
    save_path = os.path.join(DATA_DIR, file.filename)
    
    # Save uploaded file
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    print(f"[INFO] Received upload: {file.filename} ({save_path})")

    # Handle ZIP Archives
    if filename.endswith(".zip"):
        print("[INFO] Unzipping dataset archive...")
        with zipfile.ZipFile(save_path, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)
        os.remove(save_path)

    # Standardize Dataset Naming for CSV/Parquet
    elif filename.endswith(".csv") or filename.endswith(".parquet"):
        df = pd.read_parquet(save_path) if filename.endswith(".parquet") else pd.read_csv(save_path)
        
        if "article_id" in df.columns and "product_code" in df.columns:
            target_file = os.path.join(DATA_DIR, "articles.csv")
            df.to_csv(target_file, index=False)
        elif "customer_id" in df.columns and "club_member_status" in df.columns:
            target_file = os.path.join(DATA_DIR, "customers.csv")
            df.to_csv(target_file, index=False)
        elif "t_dat" in df.columns and "price" in df.columns:
            target_file = os.path.join(DATA_DIR, "transactions_train.csv")
            df.to_csv(target_file, index=False)

    # Trigger Pipeline Re-execution
    try:
        from run_week1 import execute_week1_pipeline
        execute_week1_pipeline()
        return JSONResponse({
            "status": "success",
            "message": f"Successfully uploaded '{file.filename}' and re-processed Week 1 pipeline!"
        })
    except Exception as e:
        return JSONResponse({
            "status": "warning",
            "message": f"File '{file.filename}' uploaded to './data/', but pipeline rerun logged: {e}"
        })

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Context-Aware Recommender - Week 1 Results</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); }
        .tab-active { border-bottom: 3px solid #3b82f6; color: #3b82f6; font-weight: 600; }
        .drag-zone { border: 2px dashed #3b82f6; background-color: rgba(59, 130, 246, 0.05); }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen">
    <!-- Top Header Navigation -->
    <header class="gradient-header border-b border-slate-800 p-6 shadow-lg">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <span class="bg-blue-600 text-white p-2 rounded-lg text-xl"><i class="fa-solid fa-brain"></i></span>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Context-Aware Neural Recommendation Engine</h1>
                </div>
                <p class="text-sm text-slate-400 mt-1">Week 1 Results: Distributed Data Processing & Feature Engineering Dashboard</p>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="switchTab('upload')" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg text-sm transition-all flex items-center gap-2 shadow-md">
                    <i class="fa-solid fa-cloud-arrow-up"></i> Upload Resources
                </button>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto p-6 space-y-6">

        <!-- Stat Metric Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-slate-800/80 border border-slate-700/60 rounded-xl p-5 shadow-sm">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs uppercase tracking-wider font-semibold text-slate-400">Total Users</p>
                        <h3 class="text-3xl font-extrabold mt-1 text-white" id="stat-users">--</h3>
                    </div>
                    <span class="p-3 bg-blue-500/10 text-blue-400 rounded-lg text-lg"><i class="fa-solid fa-users"></i></span>
                </div>
                <p class="text-xs text-slate-400 mt-3 flex items-center gap-1">
                    <i class="fa-solid fa-user-snowflake text-cyan-400"></i> <span id="stat-cold-users">--</span> Cold-Start Users Handled
                </p>
            </div>

            <div class="bg-slate-800/80 border border-slate-700/60 rounded-xl p-5 shadow-sm">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs uppercase tracking-wider font-semibold text-slate-400">Total Articles</p>
                        <h3 class="text-3xl font-extrabold mt-1 text-white" id="stat-articles">--</h3>
                    </div>
                    <span class="p-3 bg-indigo-500/10 text-indigo-400 rounded-lg text-lg"><i class="fa-solid fa-shirt"></i></span>
                </div>
                <p class="text-xs text-slate-400 mt-3 flex items-center gap-1">
                    <i class="fa-solid fa-box text-amber-400"></i> <span id="stat-cold-articles">--</span> Unseen Cold Items Mapped
                </p>
            </div>

            <div class="bg-slate-800/80 border border-slate-700/60 rounded-xl p-5 shadow-sm">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs uppercase tracking-wider font-semibold text-slate-400">Transactions Processed</p>
                        <h3 class="text-3xl font-extrabold mt-1 text-white" id="stat-txns">--</h3>
                    </div>
                    <span class="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg text-lg"><i class="fa-solid fa-receipt"></i></span>
                </div>
                <p class="text-xs text-slate-400 mt-3">With Temporal Recency Features</p>
            </div>

            <div class="bg-slate-800/80 border border-slate-700/60 rounded-xl p-5 shadow-sm">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs uppercase tracking-wider font-semibold text-slate-400">Output Artifacts</p>
                        <h3 class="text-3xl font-extrabold mt-1 text-emerald-400">4 / 4</h3>
                    </div>
                    <span class="p-3 bg-purple-500/10 text-purple-400 rounded-lg text-lg"><i class="fa-solid fa-database"></i></span>
                </div>
                <p class="text-xs text-slate-400 mt-3">JSON Vocabs & Parquet Datasets</p>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="border-b border-slate-800 flex gap-6 text-sm font-medium">
            <button onclick="switchTab('overview')" id="tab-overview" class="py-3 px-2 tab-active transition-all"><i class="fa-solid fa-chart-pie mr-2"></i> Overview</button>
            <button onclick="switchTab('upload')" id="tab-upload" class="py-3 px-2 text-slate-400 hover:text-slate-200 transition-all"><i class="fa-solid fa-cloud-arrow-up mr-2"></i> Upload Resources</button>
            <button onclick="switchTab('vocabularies')" id="tab-vocabularies" class="py-3 px-2 text-slate-400 hover:text-slate-200 transition-all"><i class="fa-solid fa-tags mr-2"></i> Vocabularies</button>
            <button onclick="switchTab('customers')" id="tab-customers" class="py-3 px-2 text-slate-400 hover:text-slate-200 transition-all"><i class="fa-solid fa-user-group mr-2"></i> User Sequences</button>
            <button onclick="switchTab('articles')" id="tab-articles" class="py-3 px-2 text-slate-400 hover:text-slate-200 transition-all"><i class="fa-solid fa-fire mr-2"></i> Popularity Ranks</button>
        </div>

        <!-- TAB 1: OVERVIEW -->
        <div id="content-overview" class="space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Age Group Distribution Chart -->
                <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6 shadow-sm">
                    <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2"><i class="fa-solid fa-chart-bar text-blue-400"></i> Customer Age Group Distribution</h3>
                    <div class="h-64 flex justify-center">
                        <canvas id="ageGroupChart"></canvas>
                    </div>
                </div>

                <!-- Deliverable Verification Checklist -->
                <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6 shadow-sm flex flex-col justify-between">
                    <div>
                        <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2"><i class="fa-solid fa-list-check text-emerald-400"></i> Week 1 Requirements Verification</h3>
                        <div class="space-y-3 text-sm">
                            <div class="flex items-center justify-between p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
                                <span class="flex items-center gap-2"><i class="fa-solid fa-circle-check text-emerald-400"></i> PySpark Data Processing & Missing Value Imputation</span>
                                <span class="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">Completed</span>
                            </div>
                            <div class="flex items-center justify-between p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
                                <span class="flex items-center gap-2"><i class="fa-solid fa-circle-check text-emerald-400"></i> User & Item Cold-Start Strategy</span>
                                <span class="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">Completed</span>
                            </div>
                            <div class="flex items-center justify-between p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
                                <span class="flex items-center gap-2"><i class="fa-solid fa-circle-check text-emerald-400"></i> Recency & Temporal Calendar Features</span>
                                <span class="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">Completed</span>
                            </div>
                            <div class="flex items-center justify-between p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
                                <span class="flex items-center gap-2"><i class="fa-solid fa-circle-check text-emerald-400"></i> Customer Interaction History Sequence Aggregation</span>
                                <span class="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">Completed</span>
                            </div>
                            <div class="flex items-center justify-between p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
                                <span class="flex items-center gap-2"><i class="fa-solid fa-circle-check text-emerald-400"></i> Feature Embedding Vocabularies & Parquet Exports</span>
                                <span class="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">Completed</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB: UPLOAD RESOURCES -->
        <div id="content-upload" class="hidden space-y-6">
            <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-8 max-w-3xl mx-auto shadow-lg">
                <div class="text-center mb-6">
                    <span class="p-4 bg-blue-500/10 text-blue-400 rounded-full text-3xl inline-block mb-3"><i class="fa-solid fa-file-arrow-up"></i></span>
                    <h3 class="text-xl font-bold text-white">Upload Dataset & Recommendation Resources</h3>
                    <p class="text-sm text-slate-400 mt-1">Upload files in <strong>CSV, Parquet, JSON, or ZIP</strong> format to re-run the Context-Aware pipeline automatically.</p>
                </div>

                <!-- File Drop Zone -->
                <div class="drag-zone rounded-xl p-8 text-center cursor-pointer hover:bg-blue-500/10 transition-all" onclick="document.getElementById('file-input').click()">
                    <i class="fa-solid fa-cloud-arrow-up text-4xl text-blue-400 mb-3"></i>
                    <p class="text-base font-semibold text-slate-200">Click to browse or drag and drop files here</p>
                    <p class="text-xs text-slate-400 mt-1">Supports: <code>.csv</code>, <code>.parquet</code>, <code>.json</code>, <code>.zip</code> (Kaggle Dataset Archives)</p>
                    <input type="file" id="file-input" class="hidden" onchange="handleFileUpload(event)">
                </div>

                <!-- Status Banner -->
                <div id="upload-status" class="hidden mt-6 p-4 rounded-lg text-sm"></div>
            </div>
        </div>

        <!-- TAB 2: VOCABULARIES -->
        <div id="content-vocabularies" class="hidden space-y-6">
            <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6">
                <h3 class="text-lg font-bold text-white mb-2"><i class="fa-solid fa-tags text-indigo-400 mr-2"></i> Extracted Categorical Feature Vocabularies</h3>
                <p class="text-sm text-slate-400 mb-6">Vocabularies used by TensorFlow Recommenders StringLookup and IntegerLookup embedding layers in Week 2.</p>
                <div id="vocab-cards-container" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <!-- Populated dynamically via JS -->
                </div>
            </div>
        </div>

        <!-- TAB 3: CUSTOMERS -->
        <div id="content-customers" class="hidden space-y-6">
            <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6 overflow-x-auto">
                <h3 class="text-lg font-bold text-white mb-4"><i class="fa-solid fa-user-group text-blue-400 mr-2"></i> Processed Customer Profiles & Interaction Sequences</h3>
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="bg-slate-900/80 text-xs uppercase text-slate-400 border-b border-slate-700">
                        <tr>
                            <th class="p-3">Customer ID</th>
                            <th class="p-3">Age</th>
                            <th class="p-3">Age Group</th>
                            <th class="p-3">Club Status</th>
                            <th class="p-3">Active</th>
                            <th class="p-3">Recent Purchased Article IDs</th>
                        </tr>
                    </thead>
                    <tbody id="customers-table-body" class="divide-y divide-slate-800">
                        <!-- Populated via JS -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 4: ARTICLES -->
        <div id="content-articles" class="hidden space-y-6">
            <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6 overflow-x-auto">
                <h3 class="text-lg font-bold text-white mb-4"><i class="fa-solid fa-fire text-amber-400 mr-2"></i> Processed Articles & Product Popularity Ranks</h3>
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="bg-slate-900/80 text-xs uppercase text-slate-400 border-b border-slate-700">
                        <tr>
                            <th class="p-3">Article ID</th>
                            <th class="p-3">Product Name</th>
                            <th class="p-3">Type</th>
                            <th class="p-3">Garment Group</th>
                            <th class="p-3">Total Sales</th>
                            <th class="p-3">Avg Price</th>
                        </tr>
                    </thead>
                    <tbody id="articles-table-body" class="divide-y divide-slate-800">
                        <!-- Populated via JS -->
                    </tbody>
                </table>
            </div>
        </div>

    </main>

    <script>
        let ageChart = null;

        async function fetchDashboardData() {
            // 1. Fetch Stats
            const resStats = await fetch('/api/stats');
            const dataStats = await resStats.json();
            
            document.getElementById('stat-users').innerText = dataStats.summary.total_users || 0;
            document.getElementById('stat-articles').innerText = dataStats.summary.total_articles || 0;
            document.getElementById('stat-txns').innerText = dataStats.summary.total_transactions || 0;
            document.getElementById('stat-cold-users').innerText = dataStats.cold_users || 0;
            document.getElementById('stat-cold-articles').innerText = dataStats.cold_articles || 0;

            // Render Age Group Chart
            const ageData = dataStats.age_distribution || {};
            const ctx = document.getElementById('ageGroupChart').getContext('2d');
            if (ageChart) { ageChart.destroy(); }
            ageChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(ageData),
                    datasets: [{
                        data: Object.values(ageData),
                        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } }
                }
            });

            // 2. Fetch Vocabularies
            const resVocab = await fetch('/api/vocabularies');
            const dataVocab = await resVocab.json();
            const vocabContainer = document.getElementById('vocab-cards-container');
            vocabContainer.innerHTML = '';
            for (const [key, list] of Object.entries(dataVocab)) {
                const card = document.createElement('div');
                card.className = 'p-4 bg-slate-900/80 border border-slate-700/60 rounded-lg';
                card.innerHTML = `
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold text-slate-200">${key}</span>
                        <span class="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded font-mono">${list.length} categories</span>
                    </div>
                    <div class="flex flex-wrap gap-1.5 mt-2">
                        ${list.slice(0, 8).map(v => `<span class="bg-slate-800 text-slate-300 text-xs px-2 py-1 rounded border border-slate-700">${v}</span>`).join('')}
                        ${list.length > 8 ? `<span class="text-xs text-slate-500 font-mono py-1">+${list.length - 8} more</span>` : ''}
                    </div>
                `;
                vocabContainer.appendChild(card);
            }

            // 3. Fetch Customers
            const resCustomers = await fetch('/api/customers?limit=15');
            const dataCustomers = await resCustomers.json();
            const custBody = document.getElementById('customers-table-body');
            custBody.innerHTML = '';
            dataCustomers.forEach(c => {
                const tr = document.createElement('tr');
                const seq = (c.recent_article_ids || []).slice(0, 4).join(', ');
                tr.innerHTML = `
                    <td class="p-3 font-mono text-xs text-blue-400">${c.customer_id}</td>
                    <td class="p-3">${c.age}</td>
                    <td class="p-3"><span class="px-2 py-0.5 text-xs bg-slate-800 rounded border border-slate-700">${c.age_group}</span></td>
                    <td class="p-3 text-slate-400">${c.club_member_status}</td>
                    <td class="p-3">${c.Active === 1.0 ? '<span class="text-emerald-400"><i class="fa-solid fa-check"></i> Active</span>' : '<span class="text-slate-500">Inactive</span>'}</td>
                    <td class="p-3 font-mono text-xs text-slate-400">${seq || '<span class="text-slate-600">No purchase history (Cold User)</span>'}</td>
                `;
                custBody.appendChild(tr);
            });

            // 4. Fetch Articles
            const resArticles = await fetch('/api/articles?limit=15');
            const dataArticles = await resArticles.json();
            const artBody = document.getElementById('articles-table-body');
            artBody.innerHTML = '';
            dataArticles.forEach(a => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="p-3 font-mono text-xs text-indigo-400">${a.article_id}</td>
                    <td class="p-3 font-semibold text-slate-200">${a.prod_name || 'N/A'}</td>
                    <td class="p-3 text-slate-400">${a.product_type_name || 'N/A'}</td>
                    <td class="p-3 text-slate-400">${a.garment_group_name || 'N/A'}</td>
                    <td class="p-3 font-bold text-amber-400">${a.pop_total_sales || 0}</td>
                    <td class="p-3 font-mono">${a.article_avg_price ? '$' + a.article_avg_price.toFixed(4) : '$0.0000'}</td>
                `;
                artBody.appendChild(tr);
            });
        }

        async function handleFileUpload(event) {
            const files = event.target.files;
            if (!files.length) return;

            const file = files[0];
            const formData = new FormData();
            formData.append("file", file);

            const statusDiv = document.getElementById('upload-status');
            statusDiv.classList.remove('hidden', 'bg-emerald-500/20', 'text-emerald-300', 'bg-rose-500/20', 'text-rose-300');
            statusDiv.className = 'mt-6 p-4 rounded-lg text-sm bg-blue-500/20 text-blue-300 border border-blue-500/30 flex items-center gap-2';
            statusDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading resource file and executing feature engineering pipeline...';

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();

                if (result.status === 'success') {
                    statusDiv.className = 'mt-6 p-4 rounded-lg text-sm bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-2';
                    statusDiv.innerHTML = '<i class="fa-solid fa-circle-check"></i> ' + result.message;
                    await fetchDashboardData();
                } else {
                    statusDiv.className = 'mt-6 p-4 rounded-lg text-sm bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-2';
                    statusDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> ' + result.message;
                    await fetchDashboardData();
                }
            } catch (err) {
                statusDiv.className = 'mt-6 p-4 rounded-lg text-sm bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-2';
                statusDiv.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Failed to upload file: ' + err.message;
            }
        }

        function switchTab(tabName) {
            ['overview', 'upload', 'vocabularies', 'customers', 'articles'].forEach(t => {
                document.getElementById('content-' + t).classList.add('hidden');
                document.getElementById('tab-' + t).className = 'py-3 px-2 text-slate-400 hover:text-slate-200 transition-all';
            });
            document.getElementById('content-' + tabName).classList.remove('hidden');
            document.getElementById('tab-' + tabName).className = 'py-3 px-2 tab-active transition-all';
        }

        window.onload = fetchDashboardData;
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    print("[INFO] Launching Week 1 FastAPI Web Dashboard on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
