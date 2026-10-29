# 📊 AI Business Intelligence Assistant

A local-first sales analytics dashboard that lets users ask supported business questions in plain English and see answers backed by validated SQL queries. The project uses Python, FastAPI, SQLite, Pandas, and Streamlit. **It does not require an OpenAI API key or a paid AI service**: question interpretation is rule-based and runs locally.
<img width="1366" height="768" alt="Screenshot (121)" src="https://github.com/user-attachments/assets/8d668bfa-0ff0-474f-ad28-97002c595948" />
<img width="1366" height="768" alt="Screenshot (127) - Copy" src="https://github.com/user-attachments/assets/1da62846-50af-489e-bcd5-72804dde80e2" />

<img width="1366" height="768" alt="Screenshot (125)" src="https://github.com/user-attachments/assets/8a8c9d6f-2d8e-43a0-a709-8c7c563af0e6" />



## Features

- Ask sales questions in plain English using a fixed set of supported analysis types.
- View net revenue, eligible transaction count, number of products, and excluded source rows.
- Explore monthly revenue, product performance, and regional performance with charts and tables.
- Compare two months and see absolute and percentage change.
- Validate CSV records before importing them into SQLite.
- Review data-quality exclusions and the revenue policy.
- Use a FastAPI backend with `/ask`, `/health`, `/examples`, and `/summary` endpoints.
- Run automated tests with Pytest.
- No generated SQL is executed from user input; SQL statements are predefined and month values are parameterized.

## Technology stack

- Python 3.10+
- FastAPI and Uvicorn — REST API
- Streamlit — dashboard interface
- SQLite — local database
- Pandas — CSV validation and data preparation
- Requests — dashboard-to-API communication
- Pytest and HTTPX — tests

## Project structure

```text
ai-business-intelligence-assistant/
├── app/
│   ├── __init__.py
│   ├── analytics.py          # SQL-backed analytics functions
│   ├── database.py           # SQLite schema and connections
│   ├── data_loader.py        # CSV validation and import
│   ├── import_data.py        # Manual CSV import command
│   ├── main.py               # FastAPI endpoints
│   └── question_interpreter.py # Supported question patterns
├── data/
│   └── ai_bi_assistant_sales_data - GET.csv
├── screenshots/
│   └── output_screen.png     # Dashboard preview
├── tests/
│   ├── conftest.py
│   ├── test_analytics.py
│   ├── test_api.py
│   └── test_question_interpreter.py
├── ui.py
├── requirements.txt
├── README.md
├── ARCHITECTURE.md
├── DEVELOPMENT_NOTES.md
└── .gitignore
```

## Run locally on Windows (VS Code)

### 1. Open the project folder

Extract the ZIP, then open the `ai-business-intelligence-assistant` folder in VS Code. Open **Terminal → New Terminal** and confirm the terminal is in the project root (the folder containing `ui.py` and `requirements.txt`).

### 2. Create and activate a virtual environment

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current terminal session, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install packages

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Import the sales CSV (optional)

The API imports the bundled CSV when it starts. You can also import it manually:

```powershell
python -m app.import_data
```

The command prints a report showing how many source rows were read, imported, or excluded.

### 5. Start the backend API

In **Terminal 1**, run:

```powershell
uvicorn app.main:app --reload
```

Keep this terminal open. Useful backend URLs:

- API health: `http://127.0.0.1:8000/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Dataset summary: `http://127.0.0.1:8000/summary`

### 6. Start the dashboard

Open **Terminal 2** in the same project folder and activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run ui.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`. Both the API and dashboard terminals must remain running.

### 7. Run tests

From the project root, with the virtual environment active:

```powershell
python -m pytest -v
```

The included test suite was verified in the build environment: **17 tests passed**.

## Example questions

Try these in the dashboard:

- `What is the total revenue?`
- `Which product generated the highest revenue?`
- `What is the monthly revenue trend?`
- `Which region generated the highest sales?`
- `Compare January and February 2026.`

Question interpretation is intentionally limited to approved analytics patterns. Questions asking for unsupported analyses will receive a helpful message rather than a guessed answer. This is not currently a general-purpose LLM chatbot.

## Dataset and example results

The bundled CSV contains **51 source rows** covering January–June 2026. On import, the validation policy accepted **48 eligible completed transactions** and excluded **3 source rows**:

- `TXN0033` — returned transaction.
- `TXN0034` — quantity is zero.
- `TXN0051` — unit price is missing.

Observed aggregate results from the supplied dataset:

| Metric | Result |
|---|---:|
| Net revenue | 1,439,200.00 |
| Eligible transactions | 48 |
| Units sold | 633 |
| Highest-revenue product | Monitor — 473,000.00 |
| Highest-revenue region | South — 411,200.00 |
| Highest month | May 2026 — 318,500.00 |
| Lowest month | January 2026 — 210,250.00 |

**Currency note:** The CSV does not specify a currency, so the application reports values in unspecified dataset currency units rather than assuming INR, USD, or another currency.

## Data validation and revenue calculation

- Date strings are parsed strictly as `DD-MM-YYYY` and stored in ISO format.
- Required fields and numeric values are validated before a row can enter the analytics database.
- Returned transactions, invalid dates/statuses, duplicate IDs, missing prices, and zero/negative or invalid quantities are excluded and reported.
- Net revenue is calculated as `quantity × unit price − transaction-level discount`.
- Missing unit prices are not replaced with zero.
- Re-importing a CSV is idempotent by transaction ID; it does not multiply duplicate records.
- Analytics operate only on accepted transactions. The original CSV is not modified.

## API quick test (PowerShell)

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Ask a question:

```powershell
$body = @{ question = 'Which region generated the highest sales?' } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/ask `
  -ContentType 'application/json' `
  -Body $body
```

## Troubleshooting

- **Dashboard says it cannot reach the API:** Start `uvicorn app.main:app --reload` in Terminal 1 and refresh the dashboard.
- **CSV file not found:** Check that the CSV is inside the project's `data` folder and the filename matches.
- **PowerShell blocks environment activation:** Use the process-scoped execution policy command above or activate from Command Prompt with `.venv\Scripts\activate.bat`.
- **Port 8000 is already in use:** Start the API on another port, for example `uvicorn app.main:app --reload --port 8001`, then set `$env:BI_API_URL = 'http://127.0.0.1:8001'` before running Streamlit.
- **A question is unsupported:** Rephrase it using one of the example question patterns. Add new intent handling and tests before expanding the supported question set.

## Limitations

- The interpreter supports a finite set of analytics question types; it does not infer every possible business question.
- The dataset currency is not identified.
- The dashboard is intended for local development and is not hardened for multi-user production deployment.
- A live Streamlit screenshot should be captured after starting the app on your own machine; the included PNG is a preview based on real data values.
