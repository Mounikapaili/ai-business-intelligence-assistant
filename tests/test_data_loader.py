"""Unit tests for CSV data ingestion, validation rules, and idempotency."""

import os
import sqlite3
import tempfile
import pytest

from app.data_loader import ingest_sales_csv
from app.database import get_db_connection, init_db


@pytest.fixture
def temp_csv_and_db():
    """Creates a temporary custom CSV and SQLite DB for controlled ingestion tests."""
    csv_fd, csv_path = tempfile.mkstemp(suffix=".csv")
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(csv_fd)
    os.close(db_fd)

    # Sample CSV with valid rows and specific test anomalies:
    # 1. Valid row: TXN1
    # 2. Returned row: TXN2
    # 3. Zero quantity: TXN3
    # 4. Missing unit price: TXN4 (empty value)
    # 5. Negative quantity: TXN5
    # 6. Valid row: TXN6
    content = (
        "Transaction_Id,Order_date,Product,Category,Region,Sales_channel,Quantity,Unit_price,Discount_amount,Status\n"
        "TXN1,01-01-2026,Keyboard,Accessories,North,Online,10,500,0,Completed\n"
        "TXN2,02-01-2026,Monitor,Electronics,West,Retail,2,9500,0,Returned\n"
        "TXN3,03-01-2026,Mouse,Accessories,East,Online,0,250,0,Completed\n"
        "TXN4,04-01-2026,Laptop Stand,Accessories,South,Online,5,,0,Completed\n"
        "TXN5,05-01-2026,Desk,Furniture,North,Retail,-2,1000,0,Completed\n"
        "TXN6,06-01-2026,Office Chair,Furniture,West,Retail,4,3000,200,Completed\n"
    )
    with open(csv_path, "w") as f:
        f.write(content)

    yield csv_path, db_path

    if os.path.exists(csv_path):
        os.remove(csv_path)
    if os.path.exists(db_path):
        os.remove(db_path)


def test_data_ingestion_and_policy_exclusions(temp_csv_and_db):
    """Tests 6, 7, 8, 9: Verifies missing prices, zero quantities, and returned transactions."""
    csv_path, db_path = temp_csv_and_db
    report = ingest_sales_csv(csv_path=csv_path, db_path=db_path)

    # 6 total rows in CSV: 2 eligible (TXN1, TXN6), 4 excluded (TXN2, TXN3, TXN4, TXN5)
    assert report["total_records"] == 6
    assert report["eligible_records"] == 2
    assert report["excluded_records"] == 4

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Verify TXN2 is marked ineligible due to status 'Returned'
    cursor.execute("SELECT is_eligible, exclusion_reason, net_revenue FROM sales_transactions WHERE transaction_id = 'TXN2';")
    r2 = cursor.fetchone()
    assert r2["is_eligible"] == 0
    assert "returned" in r2["exclusion_reason"].lower()
    assert r2["net_revenue"] is None

    # Verify TXN3 is marked ineligible due to zero quantity
    cursor.execute("SELECT is_eligible, exclusion_reason, net_revenue FROM sales_transactions WHERE transaction_id = 'TXN3';")
    r3 = cursor.fetchone()
    assert r3["is_eligible"] == 0
    assert "quantity" in r3["exclusion_reason"].lower()
    assert r3["net_revenue"] is None

    # Verify TXN4 is marked ineligible due to missing unit price (NEVER silently converted to zero!)
    cursor.execute("SELECT is_eligible, unit_price, exclusion_reason, net_revenue FROM sales_transactions WHERE transaction_id = 'TXN4';")
    r4 = cursor.fetchone()
    assert r4["is_eligible"] == 0
    assert r4["unit_price"] is None
    assert "missing unit price" in r4["exclusion_reason"].lower()
    assert r4["net_revenue"] is None

    # Verify eligible transactions calculation
    # TXN1: 10 * 500 - 0 = 5000.0
    # TXN6: 4 * 3000 - 200 = 11800.0
    cursor.execute("SELECT SUM(net_revenue) FROM sales_transactions WHERE is_eligible = 1;")
    total_rev = cursor.fetchone()[0]
    assert total_rev == (5000.0 + 11800.0)

    conn.close()


def test_repeated_csv_ingestion_idempotency(temp_csv_and_db):
    """Test 10: Repeated CSV ingestion must be idempotent and never duplicate records."""
    csv_path, db_path = temp_csv_and_db

    # Ingest 1st time
    rep1 = ingest_sales_csv(csv_path=csv_path, db_path=db_path)
    assert rep1["total_records"] == 6

    conn = get_db_connection(db_path)
    c1 = conn.execute("SELECT COUNT(*) FROM sales_transactions;").fetchone()[0]
    assert c1 == 6
    conn.close()

    # Ingest 2nd time without clean_existing to test ON CONFLICT deduplication
    rep2 = ingest_sales_csv(csv_path=csv_path, db_path=db_path, clean_existing=False)
    assert rep2["total_records"] == 6

    conn = get_db_connection(db_path)
    c2 = conn.execute("SELECT COUNT(*) FROM sales_transactions;").fetchone()[0]
    # Record count must strictly remain 6
    assert c2 == 6
    conn.close()


def test_real_dataset_known_cases():
    """Verifies the actual supplied dataset contains exactly the expected known cases."""
    from app.data_loader import DEFAULT_CSV_PATH
    fd, test_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    report = ingest_sales_csv(csv_path=DEFAULT_CSV_PATH, db_path=test_db)
    assert report["total_records"] == 51
    assert report["eligible_records"] == 48
    assert report["excluded_records"] == 3

    conn = get_db_connection(test_db)
    cursor = conn.cursor()

    # Check TXN0033
    t33 = cursor.execute("SELECT status, is_eligible FROM sales_transactions WHERE transaction_id = 'TXN0033';").fetchone()
    assert t33["status"] == "Returned"
    assert t33["is_eligible"] == 0

    # Check TXN0034
    t34 = cursor.execute("SELECT quantity, is_eligible FROM sales_transactions WHERE transaction_id = 'TXN0034';").fetchone()
    assert t34["quantity"] == 0
    assert t34["is_eligible"] == 0

    # Check TXN0051
    t51 = cursor.execute("SELECT unit_price, is_eligible FROM sales_transactions WHERE transaction_id = 'TXN0051';").fetchone()
    assert t51["unit_price"] is None
    assert t51["is_eligible"] == 0

    conn.close()
    if os.path.exists(test_db):
        os.remove(test_db)
