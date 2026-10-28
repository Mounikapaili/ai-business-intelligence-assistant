# Architecture Document: AI Business Intelligence Assistant

This document outlines the architectural blueprint, design principles, data pipeline, and security model of the **AI Business Intelligence Assistant**.

---

## 1. System Architecture Flow

The application implements a decoupled, multi-tier pipeline designed for zero-hallucination, secure business analytics:

```text
┌──────────────┐
│  1. User     │   Enters natural language question (e.g. "What is our total revenue?")
└───────┬──────┘
        │
        ▼
┌──────────────┐
│  2. UI Layer │   Streamlit Interface (`ui.py`) or Web Frontend (`src/App.tsx`)
└───────┬──────┘
        │  HTTP POST /ask { "question": "..." }
        ▼
┌──────────────┐
│  3. FastAPI  │   REST API Gateway (`app/main.py`) validates payload & request
└───────┬──────┘
        │
        ▼
┌───────────────────────────┐
│  4. Question Interpreter  │   `app/question_interpreter.py`
│                           │   Deterministic Intent Classification & Parameter Extraction
└───────────┬───────────────┘   (e.g., Intent: `total_revenue`, Params: {})
            │
            ▼
┌───────────────────────────┐
│  5. Analytics Functions   │   `app/analytics.py`
│                           │   Selects approved analytics routine & builds parameterized SQL
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  6. SQLite Database       │   `sales_bi.db` with indexed `sales_transactions`
│                           │   Executes parameterized SQL aggregation
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  7. Structured Response   │   JSON payload with human narrative, supporting numbers,
│                           │   breakdowns, currency symbol, and data governance caveats
└───────────┬───────────────┘
            │
            ▼
┌──────────────┐
│  8. UI View  │   Renders executive metric cards, narrative banner, & Plotly charts
└──────────────┘
```

---

## 2. Component Responsibilities

### 2.1 UI Layer (`ui.py`)
- **Technology:** Streamlit & Plotly.
- **Responsibilities:**
  - Provides natural language text input with quick-select example buttons.
  - Communicates exclusively with the FastAPI REST API over HTTP.
  - Formats numbers, highlights peak metrics, and renders interactive data tables.
  - Visualizes trends using Plotly charts (bar, line, donut, comparison).
  - Displays transparent data governance audit badges for excluded records.

### 2.2 FastAPI Backend (`app/main.py`)
- **Technology:** FastAPI, Uvicorn, Pydantic.
- **Responsibilities:**
  - Exposes RESTful endpoints: `/ask`, `/health`, `/examples`, `/summary`, `/transactions`, `/ingest`.
  - Enforces schema validation using Pydantic models.
  - Measures request latency and formats response envelopes.
  - Catches global exceptions and formats error responses without exposing raw stack traces.

### 2.3 Question Interpreter (`app/question_interpreter.py`)
- **Technology:** Python regex, tokenization, keyword taxonomy.
- **Responsibilities:**
  - Classifies user questions into one of 5 supported business intents:
    1. `TOTAL_REVENUE`
    2. `TOP_PRODUCT`
    3. `MONTHLY_TREND`
    4. `TOP_REGION`
    5. `MONTH_COMPARISON`
  - Extracts parameters (e.g. `month_a: '2026-01'`, `month_b: '2026-02'`).
  - Rejects ambiguous or out-of-domain queries gracefully with helpful suggested questions.
  - **Security Barrier:** Never allows arbitrary user text to reach the SQL execution engine.

### 2.4 SQL Analytics Engine (`app/analytics.py`)
- **Technology:** Parameterized SQLite SQL.
- **Responsibilities:**
  - Implements dedicated analytical query functions:
    - `get_total_revenue()`
    - `get_product_revenue_ranking()`
    - `get_monthly_revenue_trend()`
    - `get_regional_revenue_ranking()`
    - `compare_monthly_revenue(month_a, month_b)`
    - `get_data_quality_report()`
  - Enforces the uniform revenue policy: `WHERE is_eligible = 1`.
  - Calculates percentages, ranks items, checks for ties, and handles edge cases (zero division, missing months, single-month datasets).

### 2.5 Data Ingestion & Governance (`app/data_loader.py` & `app/database.py`)
- **Technology:** Pandas, SQLite.
- **Responsibilities:**
  - Parses dates strictly in `DD-MM-YYYY` format into ISO `YYYY-MM-DD` and `YYYY-MM`.
  - Normalizes raw CSV headers to standard snake_case.
  - Validates business criteria:
    - Excludes returns (`Status == 'Returned'`).
    - Excludes non-positive quantities (`Quantity <= 0`).
    - Excludes records missing unit prices (never assumes zero).
  - Calculates net revenue: `(Quantity × Unit Price) − Discount Amount`.
  - Preserves the original CSV unmodified.
  - Provides idempotent ingestion using SQLite `ON CONFLICT DO UPDATE`.

---

## 3. Database Schema

The SQLite schema consists of two tables:

### Table 1: `sales_transactions`
Stores cleaned and normalized sales records:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Auto-incrementing identifier |
| `transaction_id` | TEXT UNIQUE | Original transaction code (e.g., `TXN0001`) |
| `order_date` | TEXT | Parsed ISO date (`YYYY-MM-DD`) for indexed chronological queries |
| `raw_order_date` | TEXT | Original date string from CSV (`DD-MM-YYYY`) |
| `order_month` | TEXT | Year-Month (`YYYY-MM`) for trend aggregations |
| `order_year` | INTEGER | Year integer (e.g., `2026`) |
| `product` | TEXT | Product name (e.g., `Monitor`, `Office Chair`) |
| `category` | TEXT | Product category (e.g., `Electronics`, `Accessories`) |
| `region` | TEXT | Sales territory (`North`, `South`, `East`, `West`) |
| `sales_channel` | TEXT | Channel (`Online`, `Retail`) |
| `quantity` | INTEGER | Item quantity ordered |
| `unit_price` | REAL | Unit selling price (NULL if missing) |
| `discount_amount` | REAL | Transaction-level discount deducted once |
| `net_revenue` | REAL | `(quantity * unit_price) - discount_amount` |
| `status` | TEXT | Transaction state (`Completed`, `Returned`) |
| `is_eligible` | INTEGER | `1` if completed sales sale; `0` if excluded |
| `exclusion_reason` | TEXT | Audit log explaining exclusion reason |

### Table 2: `data_quality_summary`
Tracks data ingestion runs and audits:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Ingestion batch ID |
| `import_timestamp` | TIMESTAMP | Execution timestamp |
| `source_file` | TEXT | Source CSV filename |
| `total_records` | INTEGER | Total rows in file (51) |
| `eligible_records` | INTEGER | Eligible rows imported (48) |
| `excluded_records` | INTEGER | Excluded rows flagged (3) |
| `details_json` | TEXT | JSON audit array containing each flagged row & reason |

---

## 4. Security & Governance Principles

1. **Parameterization:** All database operations utilize SQLite parameterized queries (`?` placeholders). No user-supplied text is ever concatenated into SQL strings.
2. **Deterministic Routing:** Questions are resolved using deterministic pattern matching. No external untrusted LLM generates database statements.
3. **Data Immutability:** Raw CSV files are never rewritten or mutated. Ingestion creates a cleaned operational database layer while preserving source truth.
4. **Error Masking:** Client-facing responses never contain raw Python tracebacks or database errors; errors are wrapped in clean JSON envelopes with appropriate HTTP status codes.
