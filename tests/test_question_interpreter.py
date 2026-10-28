"""Unit tests for safe question interpreter and parameter extraction."""

import pytest
from app.question_interpreter import IntentType, extract_months_from_query, interpret_question


def test_total_revenue_variations():
    """Test 11a: Tests intent matching for total revenue variations."""
    queries = [
        "What is the total revenue?",
        "What is our total revenue?",
        "How much revenue did we make?",
        "Show me overall sales",
        "Total net revenue",
        "What are our net sales?",
        "How much money was generated total?"
    ]
    for q in queries:
        res = interpret_question(q)
        assert res.intent == IntentType.TOTAL_REVENUE, f"Failed for query: {q}"
        assert res.confidence >= 0.70


def test_top_product_variations():
    """Test 11b: Tests intent matching for product performance variations."""
    queries = [
        "Which product generated the highest revenue?",
        "Which product performed best?",
        "Top product by revenue",
        "Best-selling product",
        "What is our highest-grossing product?",
        "Product revenue ranking"
    ]
    for q in queries:
        res = interpret_question(q)
        assert res.intent == IntentType.TOP_PRODUCT, f"Failed for query: {q}"


def test_monthly_trend_variations():
    """Test 11c: Tests intent matching for monthly trend variations."""
    queries = [
        "What is the monthly revenue trend?",
        "Show sales month by month",
        "Monthly revenue breakdown",
        "What is the sales trend over time?",
        "Monthly performance trend"
    ]
    for q in queries:
        res = interpret_question(q)
        assert res.intent == IntentType.MONTHLY_TREND, f"Failed for query: {q}"


def test_top_region_variations():
    """Test 11d: Tests intent matching for regional sales variations."""
    queries = [
        "Which region generated the highest sales?",
        "Which region performed best?",
        "Sales by region",
        "Regional sales breakdown",
        "Top sales region"
    ]
    for q in queries:
        res = interpret_question(q)
        assert res.intent == IntentType.TOP_REGION, f"Failed for query: {q}"


def test_month_parameter_extraction():
    """Test 11e: Tests month name and date parsing for comparison questions."""
    # Pattern with month names and year
    m1 = extract_months_from_query("Compare January and February 2026")
    assert "2026-01" in m1
    assert "2026-02" in m1

    # Pattern with ISO strings
    m2 = extract_months_from_query("Compare 2026-03 to 2026-05")
    assert "2026-03" in m2
    assert "2026-05" in m2

    # Intent mapping with parameter population
    res = interpret_question("How did revenue change between January and February 2026?")
    assert res.intent == IntentType.MONTH_COMPARISON
    assert res.parameters.get("month_a") == "2026-01"
    assert res.parameters.get("month_b") == "2026-02"


def test_empty_and_unsupported_questions():
    """Test 6: Tests empty and unsupported questions."""
    # Blank query
    r_empty = interpret_question("")
    assert r_empty.intent == IntentType.UNKNOWN
    assert "empty" in r_empty.error_message.lower()

    # Whitespace only
    r_space = interpret_question("   ")
    assert r_space.intent == IntentType.UNKNOWN

    # Irrelevant query
    r_unknown = interpret_question("Who won the soccer world cup in 1994?")
    assert r_unknown.intent == IntentType.UNKNOWN
    assert len(r_unknown.suggested_questions) > 0
