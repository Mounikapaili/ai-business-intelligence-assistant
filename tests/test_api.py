"""API endpoint integration tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check returns healthy status and database metrics."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert data["database"]["connected"] is True
    assert data["database"]["total_records"] >= 51


def test_examples_endpoint():
    """Test example questions endpoint."""
    response = client.get("/examples")
    assert response.status_code == 200
    data = response.json()
    assert len(data["supported_intents"]) == 5
    assert len(data["all_examples"]) >= 5


def test_summary_endpoint():
    """Test summary endpoint returns metrics and policy exclusions."""
    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert data["metrics"]["total_transactions"] == 51
    assert data["metrics"]["eligible_transactions"] == 48
    assert data["metrics"]["excluded_transactions"] == 3
    assert len(data["data_quality_audit"]["excluded_details"]) == 3


def test_ask_all_five_required_questions():
    """Test 12: Verifies /ask endpoint answers all 5 required business questions accurately."""
    questions = [
        ("What is the total revenue?", "total_revenue"),
        ("Which product generated the highest revenue?", "top_product"),
        ("What is the monthly revenue trend?", "monthly_trend"),
        ("Which region generated the highest sales?", "top_region"),
        ("How did revenue change between two months?", "month_comparison"),
    ]

    for q, expected_intent in questions:
        res = client.post("/ask", json={"question": q})
        assert res.status_code == 200, f"Failed for question: {q}"
        data = res.json()
        assert data["status"] == "success"
        assert data["intent"] == expected_intent
        assert len(data["answer"]) > 0
        assert isinstance(data["supporting_figures"], dict)
        assert data["currency"] == "INR"
        assert len(data["caveats"]) >= 3


def test_ask_unsupported_and_empty_payloads():
    """Test validation and error handling for bad requests."""
    # Blank string inside payload -> 400 Bad Request
    res_blank = client.post("/ask", json={"question": "   "})
    assert res_blank.status_code == 400

    # Irrelevant query -> status: unsupported
    res_unsupported = client.post("/ask", json={"question": "Tell me a joke about airplanes"})
    assert res_unsupported.status_code == 200
    data = res_unsupported.json()
    assert data["status"] == "unsupported"
    assert data["intent"] == "unknown"
    assert len(data["suggested_questions"]) > 0


def test_sql_injection_safety():
    """Test that malicious SQL injection inputs are safely handled without code execution."""
    malicious_inputs = [
        "'; DROP TABLE sales_transactions; --",
        "What is total revenue WHERE 1=1 OR ''='",
        "UNION SELECT * FROM sales_transactions --",
        "'; DELETE FROM sales_transactions WHERE 'a'='a"
    ]

    for attack in malicious_inputs:
        res = client.post("/ask", json={"question": attack})
        assert res.status_code in [200, 400]
        # Verify table still exists and data is intact
        health = client.get("/health").json()
        assert health["database"]["total_records"] == 51


def test_transactions_endpoint():
    """Test transactions endpoint returns records and supports filtering."""
    res_all = client.get("/transactions?limit=10")
    assert res_all.status_code == 200
    data = res_all.json()
    assert len(data["transactions"]) == 10

    res_eligible = client.get("/transactions?eligible_only=true")
    assert res_eligible.status_code == 200
    data_el = res_eligible.json()
    assert data_el["total"] == 48
    assert all(tx["is_eligible"] == 1 for tx in data_el["transactions"])
