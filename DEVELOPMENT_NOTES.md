# Development Notes: AI Business Intelligence Assistant

This document records the engineering process, real issues encountered, debugging steps, verified test results, and future enhancement paths.

---

## 1. Engineering Process & Tooling

The application was built from scratch following an execute-first, test-driven approach:

1. **Environment Setup:**
   - Debian Linux environment with Python 3.11.2 and Node.js.
   - Installed `python3-pip` and `python3-venv` via `apt-get`.
   - Created an isolated Python virtual environment (`.venv`) and installed project dependencies:
     `fastapi`, `uvicorn`, `streamlit`, `pandas`, `pydantic`, `pytest`, `httpx`, `requests`, `plotly`.

2. **Dataset Inspection:**
   - Supplied CSV path: `data/ai_bi_assistant_sales_data - GET.csv`.
   - Dimensions verified: 51 rows, 10 columns.
   - Date format verified: `DD-MM-YYYY` (spanning January 3, 2026 to June 28, 2026).
   - Known data quality cases inspected and confirmed:
     - `TXN0033`: Status is `Returned` (Quantity = 2, Unit_price = 9500.0). Excluded from completed revenue.
     - `TXN0034`: Quantity is `0` (Unit_price = 900.0). Excluded from revenue per policy.
     - `TXN0051`: Unit_price is `NaN` / empty. Excluded per policy (never silently converted to 0).
   - Clean eligible row count verified: 48 rows.

---

## 2. Real Issues Encountered & Debugging Steps

### Issue 1: Port 8000 Address Conflict
- **Symptom:** Starting FastAPI on port 8000 resulted in `[Errno 98] error while attempting to bind on address ('0.0.0.0', 8000): address already in use`.
- **Root Cause:** In the container runtime environment, internal process `control-plane-api` is bound to port 8000.
- **Resolution:**
  - Configured FastAPI to run on port 8001 in the container environment while supporting custom ports via CLI arguments (`--backend-port`) and environment variables (`FASTAPI_URL`).
  - Added auto-discovery in `ui.py` to seamlessly detect whether port 8001 or port 8000 is active.
  - Added Vite proxy in `vite.config.ts` mapping `/api` to `http://127.0.0.1:8001`.

### Issue 2: Date Parsing in Ingestion
- **Symptom:** Raw CSV order dates are formatted as `DD-MM-YYYY` (e.g., `03-01-2026` for January 3rd, not March 1st).
- **Risk:** Standard ISO date parsers might confuse month and day for dates where day <= 12.
- **Resolution:** Explicitly specified `strptime(raw, "%d-%m-%Y")` in `app/data_loader.py` and extracted both standard ISO `YYYY-MM-DD` and `YYYY-MM` strings for clean database querying.

### Issue 3: Missing Unit Price Treatment (TXN0051)
- **Symptom:** TXN0051 had a blank string / NaN in `Unit_price`.
- **Policy Requirement:** "Never silently replace a missing unit price with zero."
- **Resolution:** The validation logic checks `pd.isna(raw_price) or str(raw_price).strip() == ""`. If detected, the row is marked `is_eligible = 0` with `exclusion_reason = "Missing Unit Price (price is null or blank; policy excludes from revenue)"` and `unit_price = NULL` in SQLite.

### Issue 4: FastAPI Lifespan Handler Deprecation
- **Symptom:** FastAPI issued deprecation warnings regarding `@app.on_event("startup")`.
- **Resolution:** Migrated to FastAPI's modern `@asynccontextmanager` `lifespan` handler, ensuring database initialization and data seeding run cleanly on startup without warnings.

---

## 3. Actual Automated Verification Results

Automated test suite execution log:
- **Test Runner:** `pytest -v`
- **Total Tests Collected:** 21
- **Passed:** 21
- **Failed:** 0
- **Duration:** 1.25 seconds

Breakdown of tests executed:
1. `tests/test_analytics.py::test_total_revenue_calculation` — Verified net revenue equals ₹4,850.00 on controlled fixtures with returns and zero-quantity items excluded.
2. `tests/test_analytics.py::test_highest_revenue_product` — Verified top product identification and descending ranking order.
3. `tests/test_analytics.py::test_monthly_revenue_aggregation` — Verified monthly groupings, growth amounts, and peak month detection.
4. `tests/test_analytics.py::test_highest_revenue_region` — Verified regional breakdown and market share calculations.
5. `tests/test_analytics.py::test_month_to_month_comparison` — Verified absolute and percentage change, direction, and zero-base handling.
6. `tests/test_api.py::test_health_endpoint` — Verified HTTP 200 and healthy status response.
7. `tests/test_api.py::test_examples_endpoint` — Verified all 5 business intents are returned.
8. `tests/test_api.py::test_summary_endpoint` — Verified 51 total rows, 48 eligible rows, 3 excluded rows.
9. `tests/test_api.py::test_ask_all_five_required_questions` — Verified HTTP 200 and correct intent matching for all 5 business questions.
10. `tests/test_api.py::test_ask_unsupported_and_empty_payloads` — Verified HTTP 400 for empty questions and graceful `unsupported` status for irrelevant questions.
11. `tests/test_api.py::test_sql_injection_safety` — Verified that injection strings (`'; DROP TABLE...`, `1=1 OR ''=''`) cannot alter tables or execute malicious commands.
12. `tests/test_api.py::test_transactions_endpoint` — Verified paginated transaction fetching and eligibility filters.
13. `tests/test_data_loader.py::test_data_ingestion_and_policy_exclusions` — Verified policy exclusion of returns, zero quantities, and missing prices.
14. `tests/test_data_loader.py::test_repeated_csv_ingestion_idempotency` — Verified re-running ingestion does not create duplicate database rows.
15. `tests/test_data_loader.py::test_real_dataset_known_cases` — Verified TXN0033, TXN0034, and TXN0051 on the actual supplied dataset.
16. `tests/test_question_interpreter.py::test_total_revenue_variations` — Verified 7 natural language phrasing variations for total revenue.
17. `tests/test_question_interpreter.py::test_top_product_variations` — Verified 6 variations for top product.
18. `tests/test_question_interpreter.py::test_monthly_trend_variations` — Verified 5 variations for monthly trend.
19. `tests/test_question_interpreter.py::test_top_region_variations` — Verified 5 variations for top region.
20. `tests/test_question_interpreter.py::test_month_parameter_extraction` — Verified month extraction for comparisons (e.g., January and February 2026, 2026-03 vs 2026-05).
21. `tests/test_question_interpreter.py::test_empty_and_unsupported_questions` — Verified empty string and non-domain question handling.

---

## 4. Key Calculation Benchmarks on Real Dataset

Based on the 48 eligible completed transactions:
- **Total Net Revenue:** ₹1,439,200.00
- **Total Units Sold:** 633
- **Total Discounts Applied:** ₹4,500.00
- **Average Order Value:** ₹29,983.33
- **Highest-Revenue Product:** Monitor (₹473,000.00; 9 orders, 50 units sold; 32.87% revenue share)
- **Second Product:** Desk (₹222,500.00; 6 orders, 18 units sold)
- **Highest-Revenue Region:** South (₹411,200.00; 13 orders, 182 units sold; 28.57% revenue share)
- **Peak Month:** 2026-05 (May 2026) with ₹318,500.00 across 8 orders
- **Lowest Month:** 2026-01 (January 2026) with ₹210,250.00 across 8 orders
- **Excluded Records:**
  1. `TXN0033`: Returned item
  2. `TXN0034`: Quantity = 0
  3. `TXN0051`: Missing Unit Price

---

## 5. Future Enhancements

1. **Pluggable LLM Interpreter:** Add optional integration with an external LLM (e.g. Gemini) via an environment variable (`ENABLE_LLM_INTERPRETER=true`), allowing semantic fallback for queries that don't match deterministic patterns while retaining parameterized SQL query execution.
2. **Dynamic CSV Upload:** Support uploading new CSV files through the Streamlit interface with automated schema validation.
3. **Automated Scheduled Ingestion:** Implement cron-based directory monitoring for automated daily sales batch imports.
