"""Data Ingestion and Quality Validation Module for AI Business Intelligence Assistant.

Enforces explicit revenue and data-quality policies:
- Reads the supplied CSV without modifying the source file.
- Normalizes column names internally.
- Parses dates formatted as DD-MM-YYYY into ISO YYYY-MM-DD and YYYY-MM.
- Validates required fields, numeric constraints, and transaction statuses.
- Enforces explicit exclusions:
  * Returned transactions (e.g. TXN0033) are excluded from completed sales revenue.
  * Zero or negative quantities (e.g. TXN0034) are excluded from sales revenue.
  * Missing unit prices (e.g. TXN0051) are excluded (NEVER silently replaced with 0).
- Calculates net revenue as: (Quantity × Unit_price) − Discount_amount.
- Deduplicates and guarantees idempotent ingestion into SQLite.
- Logs full data-quality audits with reasons for all excluded records.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.database import DEFAULT_DB_PATH, get_db_connection, init_db

DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "ai_bi_assistant_sales_data - GET.csv"
)


def normalize_column_name(col: str) -> str:
    """Normalizes raw CSV column names into clean snake_case."""
    return col.strip().lower().replace(" ", "_")


def parse_order_date(date_str: Any) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """Parses DD-MM-YYYY date string into (YYYY-MM-DD, YYYY-MM, YYYY).

    Returns (None, None, None) if parsing fails.
    """
    if pd.isna(date_str) or not str(date_str).strip():
        return None, None, None
    raw = str(date_str).strip()
    try:
        dt = datetime.strptime(raw, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m"), dt.year
    except ValueError:
        # Fallback if standard ISO YYYY-MM-DD was provided
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m"), dt.year
        except ValueError:
            return None, None, None


def validate_and_classify_record(row: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[float]]:
    """Evaluates a raw transaction row against business policies.

    Returns:
        (is_eligible, exclusion_reason, net_revenue)
    """
    # 1. Check Transaction ID presence
    txn_id = str(row.get("transaction_id", "")).strip()
    if not txn_id or pd.isna(row.get("transaction_id")):
        return False, "Missing Transaction ID", None

    # 2. Check Order Date validity
    iso_date, _, _ = parse_order_date(row.get("order_date"))
    if not iso_date:
        return False, f"Invalid or unparseable order date: '{row.get('order_date')}' (Expected DD-MM-YYYY)", None

    # 3. Check Unit Price: must not be null/NaN or empty (NEVER silently replace with 0)
    raw_price = row.get("unit_price")
    if raw_price is None or pd.isna(raw_price) or str(raw_price).strip() == "":
        return False, "Missing Unit Price (price is null or blank; policy excludes from revenue)", None
    try:
        unit_price = float(raw_price)
        if unit_price < 0:
            return False, f"Negative Unit Price ({unit_price}) is invalid", None
    except (ValueError, TypeError):
        return False, f"Unparseable Unit Price: '{raw_price}'", None

    # 4. Check Quantity: must be strictly positive (> 0)
    raw_qty = row.get("quantity")
    if raw_qty is None or pd.isna(raw_qty):
        return False, "Missing Quantity", None
    try:
        quantity = int(raw_qty)
        if quantity <= 0:
            return False, f"Zero or negative quantity ({quantity}); policy excludes from completed sales revenue", None
    except (ValueError, TypeError):
        return False, f"Unparseable Quantity: '{raw_qty}'", None

    # 5. Check Status: must be Completed
    status = str(row.get("status", "")).strip()
    if not status:
        return False, "Missing Transaction Status", None
    if status.lower() == "returned":
        return False, "Returned transaction; policy excludes returns from completed sales revenue", None
    if status.lower() != "completed":
        return False, f"Non-completed transaction status: '{status}'", None

    # 6. Check Discount Amount
    raw_discount = row.get("discount_amount", 0)
    try:
        discount = float(raw_discount) if not pd.isna(raw_discount) else 0.0
        if discount < 0:
            return False, f"Negative discount amount ({discount}) is invalid", None
    except (ValueError, TypeError):
        discount = 0.0

    # Calculate net revenue: (Quantity × Unit_price) − Discount_amount
    net_revenue = round((quantity * unit_price) - discount, 2)
    return True, None, net_revenue


def ingest_sales_csv(
    csv_path: Optional[str] = None,
    db_path: Optional[str] = None,
    clean_existing: bool = True
) -> Dict[str, Any]:
    """Ingests, cleans, validates, and stores sales transactions idempotently in SQLite.

    Preserves the original CSV unchanged.
    Returns a comprehensive ingestion summary.
    """
    path = csv_path or DEFAULT_CSV_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sales CSV file not found at: {path}")

    # Ensure database schema is ready
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Read CSV using pandas
    raw_df = pd.read_csv(path)
    raw_df.columns = [normalize_column_name(c) for c in raw_df.columns]

    total_records = len(raw_df)
    eligible_count = 0
    excluded_count = 0
    excluded_details: List[Dict[str, Any]] = []
    seen_txn_ids = set()

    # Clear existing data if requested for clean re-ingest
    if clean_existing:
        cursor.execute("DELETE FROM sales_transactions;")

    insert_sql = """
    INSERT INTO sales_transactions (
        transaction_id, order_date, raw_order_date, order_month, order_year,
        product, category, region, sales_channel, quantity, unit_price,
        discount_amount, net_revenue, status, is_eligible, exclusion_reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(transaction_id) DO UPDATE SET
        order_date = excluded.order_date,
        raw_order_date = excluded.raw_order_date,
        order_month = excluded.order_month,
        order_year = excluded.order_year,
        product = excluded.product,
        category = excluded.category,
        region = excluded.region,
        sales_channel = excluded.sales_channel,
        quantity = excluded.quantity,
        unit_price = excluded.unit_price,
        discount_amount = excluded.discount_amount,
        net_revenue = excluded.net_revenue,
        status = excluded.status,
        is_eligible = excluded.is_eligible,
        exclusion_reason = excluded.exclusion_reason;
    """

    for idx, raw_row in raw_df.iterrows():
        row_dict = raw_row.to_dict()
        txn_id = str(row_dict.get("transaction_id", "")).strip()

        # Handle duplicate transaction IDs within the same file
        if txn_id in seen_txn_ids:
            excluded_count += 1
            reason = f"Duplicate Transaction ID '{txn_id}' encountered at row {idx + 1}"
            excluded_details.append({
                "row_number": int(idx + 1),
                "transaction_id": txn_id,
                "reason": reason,
                "raw_data": {k: None if pd.isna(v) else v for k, v in row_dict.items()}
            })
            continue

        seen_txn_ids.add(txn_id)

        # Classify and validate
        is_eligible, exclusion_reason, net_revenue = validate_and_classify_record(row_dict)

        raw_order_date = str(row_dict.get("order_date", "")).strip()
        iso_date, order_month, order_year = parse_order_date(raw_order_date)

        # Quantity and prices
        qty = int(row_dict["quantity"]) if pd.notna(row_dict.get("quantity")) and str(row_dict.get("quantity")).isdigit() else 0
        try:
            unit_price = float(row_dict["unit_price"]) if pd.notna(row_dict.get("unit_price")) else None
        except (ValueError, TypeError):
            unit_price = None

        try:
            discount = float(row_dict["discount_amount"]) if pd.notna(row_dict.get("discount_amount")) else 0.0
        except (ValueError, TypeError):
            discount = 0.0

        if is_eligible:
            eligible_count += 1
        else:
            excluded_count += 1
            excluded_details.append({
                "row_number": int(idx + 1),
                "transaction_id": txn_id,
                "reason": exclusion_reason,
                "raw_data": {k: None if pd.isna(v) else v for k, v in row_dict.items()}
            })

        cursor.execute(
            insert_sql,
            (
                txn_id,
                iso_date or "",
                raw_order_date,
                order_month or "",
                order_year or 0,
                str(row_dict.get("product", "")).strip(),
                str(row_dict.get("category", "")).strip(),
                str(row_dict.get("region", "")).strip(),
                str(row_dict.get("sales_channel", "")).strip(),
                qty,
                unit_price,
                discount,
                net_revenue,
                str(row_dict.get("status", "")).strip(),
                1 if is_eligible else 0,
                exclusion_reason
            )
        )

    # Record data quality summary audit
    summary_details_json = json.dumps(excluded_details)
    cursor.execute("""
    INSERT INTO data_quality_summary (
        source_file, total_records, eligible_records, excluded_records, details_json
    ) VALUES (?, ?, ?, ?, ?)
    """, (os.path.basename(path), total_records, eligible_count, excluded_count, summary_details_json))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "source_file": os.path.basename(path),
        "total_records": total_records,
        "eligible_records": eligible_count,
        "excluded_records": excluded_count,
        "excluded_details": excluded_details,
    }


if __name__ == "__main__":
    result = ingest_sales_csv()
    print("Ingestion Result:")
    print(f"Total: {result['total_records']}, Eligible: {result['eligible_records']}, Excluded: {result['excluded_records']}")
    for ex in result["excluded_details"]:
        print(f" - {ex['transaction_id']}: {ex['reason']}")
