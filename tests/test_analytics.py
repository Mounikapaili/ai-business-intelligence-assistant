"""Unit tests for analytics calculations using isolated temporary databases."""

import os
import sqlite3
import tempfile
import pytest

from app.analytics import (
    compare_monthly_revenue,
    get_monthly_revenue_trend,
    get_product_revenue_ranking,
    get_regional_revenue_ranking,
    get_total_revenue,
)
from app.database import init_db


@pytest.fixture
def test_db():
    """Creates a temporary test database with controlled fixtures."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Controlled test data:
    # 4 eligible records, 1 excluded return, 1 excluded zero quantity
    # Row 1: Widget A, 2026-01, 10 units @ 100, 50 discount -> net = 950
    # Row 2: Widget B, 2026-01, 5 units @ 200, 0 discount -> net = 1000
    # Row 3: Widget A, 2026-02, 20 units @ 100, 0 discount -> net = 2000
    # Row 4: Widget C, 2026-02, 2 units @ 500, 100 discount -> net = 900
    # Row 5 (Returned): Widget A, 2026-02, 5 units @ 100 -> net = 500, eligible = 0
    # Row 6 (Zero Qty): Widget B, 2026-01, 0 units @ 200 -> net = 0, eligible = 0
    test_rows = [
        ("T1", "2026-01-05", "05-01-2026", "2026-01", 2026, "Widget A", "Hardware", "North", "Online", 10, 100.0, 50.0, 950.0, "Completed", 1, None),
        ("T2", "2026-01-15", "15-01-2026", "2026-01", 2026, "Widget B", "Hardware", "South", "Retail", 5, 200.0, 0.0, 1000.0, "Completed", 1, None),
        ("T3", "2026-02-10", "10-02-2026", "2026-02", 2026, "Widget A", "Hardware", "North", "Online", 20, 100.0, 0.0, 2000.0, "Completed", 1, None),
        ("T4", "2026-02-20", "20-02-2026", "2026-02", 2026, "Widget C", "Office", "West", "Retail", 2, 500.0, 100.0, 900.0, "Completed", 1, None),
        ("T5", "2026-02-25", "25-02-2026", "2026-02", 2026, "Widget A", "Hardware", "North", "Online", 5, 100.0, 0.0, 500.0, "Returned", 0, "Returned"),
        ("T6", "2026-01-25", "25-01-2026", "2026-01", 2026, "Widget B", "Hardware", "South", "Retail", 0, 200.0, 0.0, 0.0, "Completed", 0, "Zero quantity")
    ]

    cursor.executemany("""
    INSERT INTO sales_transactions (
        transaction_id, order_date, raw_order_date, order_month, order_year,
        product, category, region, sales_channel, quantity, unit_price,
        discount_amount, net_revenue, status, is_eligible, exclusion_reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, test_rows)
    conn.commit()
    conn.close()

    yield path

    if os.path.exists(path):
        os.remove(path)


def test_total_revenue_calculation(test_db):
    """Test 1: Verifies total net revenue excludes invalid records and computes sums accurately."""
    result = get_total_revenue(test_db)
    figs = result["figures"]

    # Expected: 950 + 1000 + 2000 + 900 = 4850.0
    assert figs["total_net_revenue"] == 4850.0
    assert figs["transaction_count"] == 4
    # Expected units: 10 + 5 + 20 + 2 = 37
    assert figs["total_units_sold"] == 37
    # Expected discounts: 50 + 0 + 0 + 100 = 150.0
    assert figs["total_discounts_applied"] == 150.0
    assert figs["average_order_value"] == round(4850.0 / 4, 2)


def test_highest_revenue_product(test_db):
    """Test 2: Verifies highest revenue product identification and correct ranking order."""
    result = get_product_revenue_ranking(test_db)
    figs = result["figures"]

    top = figs["top_product"]
    # Widget A has 950 + 2000 = 2950.0
    # Widget B has 1000.0
    # Widget C has 900.0
    assert top["product"] == "Widget A"
    assert top["net_revenue"] == 2950.0
    assert top["units_sold"] == 30
    assert top["transaction_count"] == 2

    # Check ranking order
    ranking = figs["ranking"]
    assert len(ranking) == 3
    assert ranking[0]["product"] == "Widget A"
    assert ranking[1]["product"] == "Widget B"
    assert ranking[2]["product"] == "Widget C"


def test_monthly_revenue_aggregation(test_db):
    """Test 3: Verifies monthly revenue aggregation and trend detection."""
    result = get_monthly_revenue_trend(test_db)
    figs = result["figures"]
    trend = figs["trend"]

    # 2026-01: 950 + 1000 = 1950.0
    # 2026-02: 2000 + 900 = 2900.0
    assert len(trend) == 2
    assert trend[0]["order_month"] == "2026-01"
    assert trend[0]["net_revenue"] == 1950.0
    assert trend[1]["order_month"] == "2026-02"
    assert trend[1]["net_revenue"] == 2900.0

    # Growth: 2900 - 1950 = +950.0
    assert trend[1]["growth_amount"] == 950.0
    assert trend[1]["is_increase"] is True
    assert figs["best_month"]["order_month"] == "2026-02"


def test_highest_revenue_region(test_db):
    """Test 4: Verifies regional revenue ranking and market share calculation."""
    result = get_regional_revenue_ranking(test_db)
    figs = result["figures"]

    # North: 950 + 2000 = 2950.0
    # South: 1000.0
    # West: 900.0
    assert figs["top_region"]["region"] == "North"
    assert figs["top_region"]["net_revenue"] == 2950.0
    assert len(figs["ranking"]) == 3


def test_month_to_month_comparison(test_db):
    """Test 5: Verifies month-over-month comparison, percentage changes, and edge cases."""
    res = compare_monthly_revenue("2026-01", "2026-02", test_db)
    figs = res["figures"]

    assert figs["month_a"]["net_revenue"] == 1950.0
    assert figs["month_b"]["net_revenue"] == 2900.0
    assert figs["absolute_change"] == 950.0
    # (950 / 1950) * 100 = 48.72%
    assert figs["percentage_change"] == 48.72
    assert figs["direction"] == "increased"

    # Test reverse direction
    rev_res = compare_monthly_revenue("2026-02", "2026-01", test_db)
    assert rev_res["figures"]["absolute_change"] == -950.0
    assert rev_res["figures"]["direction"] == "decreased"

    # Test missing month comparison (zero division safety)
    missing_res = compare_monthly_revenue("2026-01", "2026-99", test_db)
    assert missing_res["figures"]["month_b"]["net_revenue"] == 0.0
    assert missing_res["figures"]["direction"] == "decreased"
