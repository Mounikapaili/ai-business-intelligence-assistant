"""Database connection and schema management for AI Business Intelligence Assistant.

Uses SQLite with WAL mode for concurrency, foreign keys, and indexes
to support fast, parameterized business analytics queries.
"""

import os
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sales_bi.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates and returns a sqlite3 connection configured with Row factory."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes tables and indexes for sales transactions and data quality logs."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Table 1: Cleaned and normalized sales transactions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE NOT NULL,
        order_date TEXT NOT NULL,         -- ISO format: YYYY-MM-DD for sorting/indexing
        raw_order_date TEXT NOT NULL,     -- Original CSV string: DD-MM-YYYY
        order_month TEXT NOT NULL,        -- Year-Month: YYYY-MM for trend aggregations
        order_year INTEGER NOT NULL,      -- Year integer (e.g., 2026)
        product TEXT NOT NULL,
        category TEXT NOT NULL,
        region TEXT NOT NULL,
        sales_channel TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL,                  -- NULL if missing in source CSV
        discount_amount REAL NOT NULL DEFAULT 0.0,
        net_revenue REAL,                 -- (quantity * unit_price) - discount_amount
        status TEXT NOT NULL,
        is_eligible INTEGER NOT NULL DEFAULT 1, -- 1 = included in completed sales, 0 = excluded
        exclusion_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indexes for fast aggregations on business dimensions
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_eligible ON sales_transactions(is_eligible);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_month ON sales_transactions(order_month);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales_transactions(product);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_region ON sales_transactions(region);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_status ON sales_transactions(status);")

    # Table 2: Data quality audit log per ingestion run
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_quality_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_file TEXT NOT NULL,
        total_records INTEGER NOT NULL,
        eligible_records INTEGER NOT NULL,
        excluded_records INTEGER NOT NULL,
        details_json TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DEFAULT_DB_PATH)
