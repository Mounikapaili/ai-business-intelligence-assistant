# AI Business Intelligence Assistant

A complete, production-grade business sales analytics application that enables non-technical and executive stakeholders to ask natural-language questions about sales transactions and receive verified, deterministic answers backed by real SQL database queries.

Built entirely without external paid LLM dependencies, API keys, or cloud lock-in.

---

## Table of Contents

1. [Project Overview & Key Features](#project-overview--key-features)
2. [Technologies Used](#technologies-used)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Windows Installation Guide (Beginner-Friendly)](#windows-installation-guide-beginner-friendly)
6. [macOS / Linux Installation Guide](#macos--linux-installation-guide)
7. [Running the Application](#running-the-application)
8. [Automated Testing](#automated-testing)
9. [Supported Business Questions & Variations](#supported-business-questions--variations)
10. [Data Ingestion & Revenue Governance Policy](#data-ingestion--revenue-governance-policy)
11. [Troubleshooting & Known Limitations](#troubleshooting--known-limitations)
12. [Uploading to GitHub](#uploading-to-github)

---

## Project Overview & Key Features

- **Natural Language Question Answering:** Ask natural business questions in plain English and receive human-readable explanations accompanied by verified numerical figures.
- **Deterministic & Safe Execution:** Maps user questions to safe, pre-compiled parameterized SQL queries. Guarantees zero SQL injection vulnerabilities and zero LLM hallucinations.
- **Strict Revenue Governance Policy:** Automatically flags and excludes returned goods, zero/negative quantities, and records with missing unit prices without altering the raw CSV.
- **Interactive Visualizations:** High-fidelity charts for monthly trends, product performance rankings, regional market shares, and month-over-month comparisons.
- **Dual Interface:** Streamlit desktop/web interface (`ui.py`) and an optional React web dashboard, both powered by a unified FastAPI REST backend (`app/main.py`).
- **Comprehensive Automated Test Suite:** 21 automated tests covering calculations, known dataset edge cases, idempotency, API routes, and injection protection.

---

## Technologies Used

- **Language:** Python 3.10+
- **Backend API:** FastAPI & Uvicorn
- **Database:** SQLite (embedded, persistent, ACID-compliant)
- **User Interface:** Streamlit & Plotly (interactive charts)
- **Data Ingestion & Cleaning:** Pandas & Standard Library
- **Analytics Engine:** Parameterized SQL queries
- **Testing:** Pytest & FastAPI TestClient

---

## Project Structure

```text
ai-business-intelligence-assistant/
├── app/
│   ├── __init__.py               # Application package definition
│   ├── database.py               # SQLite schema creation and connection manager
│   ├── data_loader.py            # CSV ingestion, data normalization & policy validation
│   ├── analytics.py              # Parameterized SQL calculations for all 5 business questions
│   ├── question_interpreter.py   # Deterministic intent matching & parameter parsing
│   └── main.py                   # FastAPI application with REST endpoints
├── data/
│   └── ai_bi_assistant_sales_data - GET.csv  # Raw supplied sales dataset (51 rows)
├── tests/
│   ├── __init__.py               # Test package definition
│   ├── test_analytics.py         # Unit tests for revenue calculations & rankings
│   ├── test_data_loader.py       # Tests for exclusions (TXN0033, TXN0034, TXN0051) & idempotency
│   ├── test_question_interpreter.py # Tests for natural language matching & month parsing
│   └── test_api.py               # Integration tests for FastAPI endpoints & SQL safety
├── ui.py                         # Streamlit interactive user interface
├── run_app.py                    # Unified runner script (backend + frontend)
├── run_backend.bat               # 1-click Windows runner for FastAPI
├── run_ui.bat                    # 1-click Windows runner for Streamlit
├── run_tests.bat                 # 1-click Windows runner for test suite
├── requirements.txt              # Pinned Python package dependencies
├── README.md                     # Comprehensive documentation
├── ARCHITECTURE.md               # End-to-end architecture explanation
├── DEVELOPMENT_NOTES.md          # Real development logs, debugging & verification
└── .gitignore                    # Git exclusion rules
```

---

## Prerequisites

- **Python:** Version 3.10, 3.11, or 3.12 installed on your machine.
- **Git:** Installed on your computer (for version control and GitHub upload).
- Optional: Modern web browser (Chrome, Edge, Firefox, Safari).

---

## Windows Installation Guide (Beginner-Friendly)

Follow these exact steps in **PowerShell** or **Command Prompt**:

### Step 1: Open Terminal in the Project Folder
Open PowerShell and navigate to the project directory:
```powershell
cd path\to\ai-business-intelligence-assistant
```

### Step 2: Create a Virtual Environment
```powershell
python -m venv .venv
```

### Step 3: Activate the Virtual Environment
- In PowerShell:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *(If PowerShell displays an Execution Policy error, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*
- Or in standard Command Prompt (`cmd.exe`):
  ```cmd
  .venv\Scripts\activate.bat
  ```

### Step 4: Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## macOS / Linux Installation Guide

Open your Terminal and run:

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Running the Application

### Option A: Unified 1-Command Runner (Recommended)

Run both the FastAPI backend and Streamlit UI together:
```bash
# Windows
python run_app.py

# macOS / Linux
python3 run_app.py
```
This automatically starts:
- **FastAPI Backend:** `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`)
- **Streamlit UI:** `http://127.0.0.1:8501`

---

### Option B: Running in Two Separate Terminals

#### Terminal 1 — Start the Backend:
```bash
# Activate virtual environment first
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
You can verify the backend is running by opening: `http://127.0.0.1:8000/health`.

#### Terminal 2 — Start the Streamlit User Interface:
```bash
# Activate virtual environment first
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

streamlit run ui.py
```
The browser will automatically open `http://localhost:8501`.

---

## Automated Testing

The project includes an automated test suite with **21 tests** covering all five analytics questions, edge cases, data policy exclusions, and API endpoints.

Run the test suite with:
```bash
pytest -v
```

Expected output:
```text
tests/test_analytics.py::test_total_revenue_calculation PASSED
tests/test_analytics.py::test_highest_revenue_product PASSED
tests/test_analytics.py::test_monthly_revenue_aggregation PASSED
tests/test_analytics.py::test_highest_revenue_region PASSED
tests/test_analytics.py::test_month_to_month_comparison PASSED
tests/test_api.py::test_health_endpoint PASSED
tests/test_api.py::test_examples_endpoint PASSED
tests/test_api.py::test_summary_endpoint PASSED
tests/test_api.py::test_ask_all_five_required_questions PASSED
tests/test_api.py::test_ask_unsupported_and_empty_payloads PASSED
tests/test_api.py::test_sql_injection_safety PASSED
tests/test_api.py::test_transactions_endpoint PASSED
tests/test_data_loader.py::test_data_ingestion_and_policy_exclusions PASSED
tests/test_data_loader.py::test_repeated_csv_ingestion_idempotency PASSED
tests/test_data_loader.py::test_real_dataset_known_cases PASSED
tests/test_question_interpreter.py::test_total_revenue_variations PASSED
tests/test_question_interpreter.py::test_top_product_variations PASSED
tests/test_question_interpreter.py::test_monthly_trend_variations PASSED
tests/test_question_interpreter.py::test_top_region_variations PASSED
tests/test_question_interpreter.py::test_month_parameter_extraction PASSED
tests/test_question_interpreter.py::test_empty_and_unsupported_questions PASSED

======================== 21 passed in 1.25s ========================
```

---

## Supported Business Questions & Variations

The assistant natively recognizes and answers the 5 core business questions and their phrasing variations:

### 1. Total Net Revenue
- *"What is the total revenue?"*
- *"What is our total revenue?"*
- *"How much revenue did we make?"*
- *"Total net sales"*
- **Result:** **₹1,439,200.00** across 48 eligible completed orders (633 units sold, ₹4,500 in discounts).

### 2. Highest-Revenue Product
- *"Which product generated the highest revenue?"*
- *"Which product performed best?"*
- *"Top product by sales"*
- **Result:** **Monitor** (Electronics) at **₹473,000.00** across 9 orders (32.87% revenue share).

### 3. Monthly Revenue Trend
- *"What is the monthly revenue trend?"*
- *"Show sales month by month"*
- *"Revenue trend over time"*
- **Result:** Spans 6 months (January to June 2026). Peak revenue occurred in **May 2026** at **₹318,500.00**.

### 4. Highest-Revenue Region
- *"Which region generated the highest sales?"*
- *"Which region performed best?"*
- *"Sales by region"*
- **Result:** **South** at **₹411,200.00** across 13 transactions (28.57% revenue share).

### 5. Month-over-Month Comparison
- *"How did revenue change between two months?"*
- *"Compare January and February 2026"*
- *"Compare 2026-04 to 2026-05"*
- **Result:** Revenue increased by **+₹24,350.00 (+11.58%)** from January 2026 (₹210,250.00) to February 2026 (₹234,600.00).

---

## Data Ingestion & Revenue Governance Policy

The data ingestion module (`app/data_loader.py`) enforces strict validation rules to guarantee data integrity:

1. **Net Revenue Formula:**
   $$\text{Net Revenue} = (\text{Quantity} \times \text{Unit Price}) - \text{Discount Amount}$$
   Discount amount is treated as a transaction-level deduction.

2. **Exclusion Rules:**
   - **Returned Transactions:** Excluded from completed sales.
     - *Verified Case:* `TXN0033` (Status: `Returned`) is flagged and omitted from revenue.
   - **Zero or Negative Quantity:** Excluded from completed sales.
     - *Verified Case:* `TXN0034` (Quantity: `0`) is flagged and omitted from revenue.
   - **Missing Unit Price:** Excluded.
     - *Verified Case:* `TXN0051` (Unit price is empty) is excluded. The system **never** silently replaces missing prices with zero.

3. **Source CSV Preservation:** The original `data/ai_bi_assistant_sales_data - GET.csv` is read in read-only mode and preserved completely intact.

4. **Idempotency:** Re-running the ingestion pipeline (`ingest_sales_csv()`) uses SQLite `ON CONFLICT(transaction_id) DO UPDATE` so repeated imports never create duplicate records.

---

## Troubleshooting & Known Limitations

### Common Issues & Fixes:
1. **Port Already in Use:**
   If port 8000 or 8501 is occupied by another application, specify custom ports:
   ```bash
   python run_app.py --backend-port 8001 --ui-port 8502
   ```
2. **Missing Dependencies:**
   Ensure your virtual environment is activated before running scripts. The prompt should show `(.venv)`.
3. **Streamlit Connection Warning:**
   If Streamlit indicates "Backend Disconnected", make sure the FastAPI server is running in a terminal.

### Known Limitations:
- The initial question interpreter uses deterministic regex and keyword pattern matching for maximum reliability and offline execution. Queries far outside sales analytics (e.g., weather or general trivia) are classified as unsupported with clear guidance.
- An optional LLM provider can be integrated via the modular `SafeQuestionInterpreter` class interface if complex conversational dialog is required in the future.

---

## Uploading to GitHub

To push this project to your GitHub account:

```bash
# 1. Initialize Git repository
git init

# 2. Stage all project files (.gitignore ensures venv and databases are excluded)
git add .

# 3. Create initial commit
git commit -m "feat: complete AI Business Intelligence Assistant application"

# 4. Create a repository on github.com, then link it:
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/ai-business-intelligence-assistant.git

# 5. Push to main branch
git branch -M main
git push -u origin main
```
