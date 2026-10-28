"""FastAPI Application for AI Business Intelligence Assistant.

Provides REST endpoints for question answering, data summary, health checks,
and dataset exploration backed by SQLite and safe deterministic interpretation.
"""

import os
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.analytics import (
    compare_monthly_revenue,
    get_data_quality_report,
    get_monthly_revenue_trend,
    get_product_revenue_ranking,
    get_regional_revenue_ranking,
    get_total_revenue,
)
from app.data_loader import DEFAULT_CSV_PATH, ingest_sales_csv
from app.database import DEFAULT_DB_PATH, get_db_connection, init_db
from app.question_interpreter import (
    EXAMPLE_QUESTIONS,
    IntentType,
    interpret_question,
)

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensures database is initialized and seed CSV is ingested on startup."""
    init_db()
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM sales_transactions;").fetchone()[0]
    conn.close()
    if count == 0 and os.path.exists(DEFAULT_CSV_PATH):
        ingest_sales_csv(DEFAULT_CSV_PATH)
    yield


app = FastAPI(
    title="AI Business Intelligence Assistant API",
    description="Deterministic natural-language analytics engine for sales transactions.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local Streamlit, frontend UI, and cross-origin tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language business question")


class AskResponse(BaseModel):
    status: str
    original_question: str
    intent: str
    intent_description: str
    answer: str
    supporting_figures: Dict[str, Any]
    currency: str = "INR"
    currency_symbol: str = "₹"
    caveats: List[str] = []
    execution_time_ms: float
    suggested_questions: Optional[List[str]] = None



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Prevents raw stack traces from leaking to clients while logging error."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal error occurred while processing your request.",
            "detail": str(exc)
        }
    )


@app.get("/health", summary="Health Check")
def health_check() -> Dict[str, Any]:
    """Returns application health, database status, and record counts."""
    try:
        conn = get_db_connection()
        total_records = conn.execute("SELECT COUNT(*) FROM sales_transactions;").fetchone()[0]
        eligible_records = conn.execute("SELECT COUNT(*) FROM sales_transactions WHERE is_eligible = 1;").fetchone()[0]
        conn.close()
        db_connected = True
    except Exception as e:
        total_records = 0
        eligible_records = 0
        db_connected = False

    return {
        "status": "healthy" if db_connected else "degraded",
        "service": "AI Business Intelligence Assistant",
        "database": {
            "type": "SQLite",
            "connected": db_connected,
            "total_records": total_records,
            "eligible_records": eligible_records,
            "excluded_records": total_records - eligible_records
        },
        "engine": "Deterministic AI Assistant with Parameterized SQL"
    }


@app.get("/examples", summary="List Example Questions")
def get_example_questions() -> Dict[str, Any]:
    """Returns curated example questions organized by business intent."""
    return {
        "status": "success",
        "supported_intents": [
            {
                "id": "total_revenue",
                "name": "Total Revenue",
                "sample_question": "What is the total revenue?",
                "variations": [
                    "What is our total revenue?",
                    "How much revenue did we make?",
                    "Total net sales"
                ]
            },
            {
                "id": "top_product",
                "name": "Top Product Ranking",
                "sample_question": "Which product generated the highest revenue?",
                "variations": [
                    "Which product performed best?",
                    "Best selling product by revenue",
                    "Product sales ranking"
                ]
            },
            {
                "id": "monthly_trend",
                "name": "Monthly Revenue Trend",
                "sample_question": "What is the monthly revenue trend?",
                "variations": [
                    "Show sales month by month",
                    "Monthly sales breakdown",
                    "Revenue trend over time"
                ]
            },
            {
                "id": "top_region",
                "name": "Regional Sales Ranking",
                "sample_question": "Which region generated the highest sales?",
                "variations": [
                    "Which region performed best?",
                    "Regional sales breakdown",
                    "Sales by territory"
                ]
            },
            {
                "id": "month_comparison",
                "name": "Month-to-Month Comparison",
                "sample_question": "How did revenue change between two months?",
                "variations": [
                    "Compare January and February 2026",
                    "Compare 2026-04 to 2026-05",
                    "Revenue change from Jan to Mar 2026"
                ]
            }
        ],
        "all_examples": EXAMPLE_QUESTIONS
    }


@app.get("/summary", summary="Dataset and Data Quality Summary")
def get_dataset_summary() -> Dict[str, Any]:
    """Returns dataset overview, data quality audit, and exclusions."""
    dq = get_data_quality_report()
    conn = get_db_connection()
    date_info = conn.execute("""
        SELECT
            MIN(order_date) AS min_date,
            MAX(order_date) AS max_date,
            COUNT(DISTINCT product) AS unique_products,
            COUNT(DISTINCT region) AS unique_regions
        FROM sales_transactions
        WHERE is_eligible = 1;
    """).fetchone()
    conn.close()

    return {
        "status": "success",
        "dataset_name": "ai_bi_assistant_sales_data",
        "date_range": {
            "earliest_order": date_info["min_date"] if date_info else None,
            "latest_order": date_info["max_date"] if date_info else None
        },
        "metrics": {
            "total_transactions": dq["total_records"],
            "eligible_transactions": dq["eligible_records"],
            "excluded_transactions": dq["excluded_records"],
            "unique_products": date_info["unique_products"] if date_info else 0,
            "unique_regions": date_info["unique_regions"] if date_info else 0
        },
        "revenue_policy": {
            "net_revenue_formula": "(Quantity × Unit_price) − Discount_amount",
            "discount_handling": "Transaction-level discount deducted directly",
            "exclusions_applied": [
                "Returned transactions excluded from completed sales revenue (TXN0033)",
                "Zero or negative quantity transactions excluded (TXN0034)",
                "Transactions with missing unit price excluded; never silently converted to zero (TXN0051)"
            ]
        },
        "data_quality_audit": dq
    }


@app.post("/ask", summary="Ask Natural Language Question", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    """Interprets a natural-language business question and returns answers backed by SQL."""
    start_time = time.perf_counter()
    question = payload.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be blank.")

    interpretation = interpret_question(question)
    dq = get_data_quality_report()

    # If unrecognized or unsupported intent
    if interpretation.intent == IntentType.UNKNOWN:
        elapsed = round((time.perf_counter() - start_time) * 1000, 2)
        return AskResponse(
            status="unsupported",
            original_question=question,
            intent="unknown",
            intent_description="Unsupported or Ambiguous Query",
            answer=(
                "I could not understand that question. I can answer questions about: "
                "total revenue, highest-revenue product, monthly revenue trends, "
                "top sales regions, and month-to-month revenue comparisons. "
                "Please choose from the example questions below."
            ),
            supporting_figures={},
            currency="INR",
            currency_symbol="₹",
            caveats=dq["caveats"],
            execution_time_ms=elapsed,
            suggested_questions=interpretation.suggested_questions
        )

    # Route to safe SQL analytics function
    if interpretation.intent == IntentType.TOTAL_REVENUE:
        res = get_total_revenue()
    elif interpretation.intent == IntentType.TOP_PRODUCT:
        res = get_product_revenue_ranking()
    elif interpretation.intent == IntentType.MONTHLY_TREND:
        res = get_monthly_revenue_trend()
    elif interpretation.intent == IntentType.TOP_REGION:
        res = get_regional_revenue_ranking()
    elif interpretation.intent == IntentType.MONTH_COMPARISON:
        month_a = interpretation.parameters.get("month_a", "2026-01")
        month_b = interpretation.parameters.get("month_b", "2026-02")
        res = compare_monthly_revenue(month_a, month_b)
    else:
        raise HTTPException(status_code=400, detail="Unknown intent encountered.")

    elapsed = round((time.perf_counter() - start_time) * 1000, 2)

    return AskResponse(
        status="success",
        original_question=question,
        intent=interpretation.intent.value,
        intent_description=interpretation.description,
        answer=res["narrative"],
        supporting_figures=res["figures"],
        currency="INR",
        currency_symbol="₹",
        caveats=dq["caveats"],
        execution_time_ms=elapsed,
        suggested_questions=interpretation.suggested_questions or EXAMPLE_QUESTIONS[:4]
    )


@app.get("/transactions", summary="List Transactions")
def get_transactions(
    eligible_only: bool = Query(False, description="Filter only eligible transactions"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Retrieves paginated transactions for inspection."""
    conn = get_db_connection()
    cursor = conn.cursor()

    where_clause = "WHERE is_eligible = 1" if eligible_only else ""
    cursor.execute(f"SELECT COUNT(*) FROM sales_transactions {where_clause};")
    total = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT
            transaction_id,
            raw_order_date,
            order_date,
            order_month,
            product,
            category,
            region,
            sales_channel,
            quantity,
            unit_price,
            discount_amount,
            net_revenue,
            status,
            is_eligible,
            exclusion_reason
        FROM sales_transactions
        {where_clause}
        ORDER BY order_date ASC, transaction_id ASC
        LIMIT ? OFFSET ?;
    """, (limit, offset))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "status": "success",
        "total": total,
        "limit": limit,
        "offset": offset,
        "transactions": rows
    }


@app.post("/ingest", summary="Trigger CSV Ingestion")
def trigger_ingest(clean_existing: bool = True) -> Dict[str, Any]:
    """Re-ingests the sales CSV idempotently into SQLite."""
    try:
        report = ingest_sales_csv(clean_existing=clean_existing)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
