"""SQL-Backed Analytics Engine for AI Business Intelligence Assistant.

All calculations use parameterized SQL queries on SQLite and strictly adhere
to the unified revenue policy:
- Excludes returned items, zero/negative quantities, and missing unit prices (is_eligible = 1).
- Net revenue = (quantity * unit_price) - discount_amount.
- Returns rich supporting figures, rankings, percentages, and breakdowns.
- Handles edge cases: division by zero, tied rankings, empty tables, missing months.
"""

from typing import Any, Dict, List, Optional
from app.database import DEFAULT_DB_PATH, get_db_connection


def format_currency(amount: float, symbol: str = "₹") -> str:
    """Formats numeric amounts as clean currency strings with commas."""
    if amount is None:
        return f"{symbol}0.00"
    return f"{symbol}{amount:,.2f}"


def get_total_revenue(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Calculates overall total net revenue and supporting volume metrics."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = """
    SELECT
        COALESCE(SUM(net_revenue), 0.0) AS total_net_revenue,
        COUNT(*) AS transaction_count,
        COALESCE(SUM(quantity), 0) AS total_units_sold,
        COALESCE(SUM(discount_amount), 0.0) AS total_discounts,
        COALESCE(AVG(net_revenue), 0.0) AS avg_order_value,
        COALESCE(MIN(order_date), '') AS first_order_date,
        COALESCE(MAX(order_date), '') AS last_order_date
    FROM sales_transactions
    WHERE is_eligible = 1;
    """
    cursor.execute(query)
    row = cursor.fetchone()

    # Category breakdown
    cat_query = """
    SELECT
        category,
        COALESCE(SUM(net_revenue), 0.0) AS revenue,
        COUNT(*) AS transactions,
        COALESCE(SUM(quantity), 0) AS units
    FROM sales_transactions
    WHERE is_eligible = 1
    GROUP BY category
    ORDER BY revenue DESC;
    """
    cursor.execute(cat_query)
    categories = [dict(r) for r in cursor.fetchall()]

    conn.close()

    total_rev = round(float(row["total_net_revenue"]), 2)
    tx_count = int(row["transaction_count"])
    units_sold = int(row["total_units_sold"])
    discounts = round(float(row["total_discounts"]), 2)
    aov = round(float(row["avg_order_value"]), 2)

    narrative = (
        f"The total net revenue across all {tx_count} eligible completed transactions is "
        f"{format_currency(total_rev)} (with {units_sold} total units sold, "
        f"{format_currency(discounts)} in discounts applied, and an average order value of {format_currency(aov)})."
    )

    return {
        "intent": "total_revenue",
        "title": "Total Net Revenue Analysis",
        "narrative": narrative,
        "figures": {
            "total_net_revenue": total_rev,
            "total_net_revenue_formatted": format_currency(total_rev),
            "transaction_count": tx_count,
            "total_units_sold": units_sold,
            "total_discounts_applied": discounts,
            "total_discounts_formatted": format_currency(discounts),
            "average_order_value": aov,
            "average_order_value_formatted": format_currency(aov),
            "date_range": {
                "start": row["first_order_date"],
                "end": row["last_order_date"]
            },
            "category_breakdown": categories
        }
    }


def get_product_revenue_ranking(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Ranks all products by net revenue and identifies the highest performer."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Total revenue for calculating share
    cursor.execute("SELECT COALESCE(SUM(net_revenue), 0.0) FROM sales_transactions WHERE is_eligible = 1;")
    total_revenue = cursor.fetchone()[0] or 0.0

    query = """
    SELECT
        product,
        category,
        COALESCE(SUM(net_revenue), 0.0) AS net_revenue,
        COALESCE(SUM(quantity), 0) AS units_sold,
        COUNT(*) AS transaction_count,
        COALESCE(AVG(unit_price), 0.0) AS avg_unit_price
    FROM sales_transactions
    WHERE is_eligible = 1
    GROUP BY product
    ORDER BY net_revenue DESC, units_sold DESC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "intent": "top_product",
            "title": "Product Revenue Ranking",
            "narrative": "No completed sales transactions are available to rank products.",
            "figures": {"top_product": None, "ranking": []}
        }

    ranking: List[Dict[str, Any]] = []
    for r in rows:
        rev = round(float(r["net_revenue"]), 2)
        share = round((rev / total_revenue * 100), 2) if total_revenue > 0 else 0.0
        ranking.append({
            "product": r["product"],
            "category": r["category"],
            "net_revenue": rev,
            "net_revenue_formatted": format_currency(rev),
            "units_sold": int(r["units_sold"]),
            "transaction_count": int(r["transaction_count"]),
            "avg_unit_price": round(float(r["avg_unit_price"]), 2),
            "revenue_share_percentage": share
        })

    top_item = ranking[0]
    # Check for ties
    top_ties = [p for p in ranking if p["net_revenue"] == top_item["net_revenue"]]
    if len(top_ties) > 1:
        tied_names = ", ".join(p["product"] for p in top_ties)
        narrative = (
            f"There is a tie for highest revenue: {tied_names} each generated "
            f"{top_item['net_revenue_formatted']} ({top_item['revenue_share_percentage']}% of total revenue)."
        )
    else:
        narrative = (
            f"The product with the highest revenue is '{top_item['product']}' ({top_item['category']}), "
            f"generating {top_item['net_revenue_formatted']} across {top_item['transaction_count']} transactions "
            f"({top_item['units_sold']} units sold), accounting for {top_item['revenue_share_percentage']}% of total sales."
        )

    return {
        "intent": "top_product",
        "title": "Product Revenue Ranking",
        "narrative": narrative,
        "figures": {
            "top_product": top_item,
            "tied_top_products": top_ties if len(top_ties) > 1 else [],
            "ranking": ranking
        }
    }


def get_monthly_revenue_trend(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Computes month-by-month revenue trend, growth rates, and top month."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = """
    SELECT
        order_month,
        COALESCE(SUM(net_revenue), 0.0) AS net_revenue,
        COALESCE(SUM(quantity), 0) AS units_sold,
        COUNT(*) AS transaction_count,
        COALESCE(SUM(discount_amount), 0.0) AS total_discounts
    FROM sales_transactions
    WHERE is_eligible = 1
    GROUP BY order_month
    ORDER BY order_month ASC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "intent": "monthly_trend",
            "title": "Monthly Revenue Trend",
            "narrative": "No transaction data available for monthly trend analysis.",
            "figures": {"trend": [], "best_month": None, "lowest_month": None}
        }

    trend: List[Dict[str, Any]] = []
    prev_revenue: Optional[float] = None

    for r in rows:
        rev = round(float(r["net_revenue"]), 2)
        growth_amount = round(rev - prev_revenue, 2) if prev_revenue is not None else 0.0
        growth_pct = round(((rev - prev_revenue) / prev_revenue * 100), 2) if prev_revenue and prev_revenue > 0 else (0.0 if prev_revenue is None else 100.0)

        trend.append({
            "order_month": r["order_month"],
            "net_revenue": rev,
            "net_revenue_formatted": format_currency(rev),
            "units_sold": int(r["units_sold"]),
            "transaction_count": int(r["transaction_count"]),
            "total_discounts": round(float(r["total_discounts"]), 2),
            "growth_amount": growth_amount,
            "growth_amount_formatted": format_currency(growth_amount),
            "growth_percentage": growth_pct,
            "is_increase": growth_amount > 0 if prev_revenue is not None else None
        })
        prev_revenue = rev

    best_month = max(trend, key=lambda x: x["net_revenue"])
    lowest_month = min(trend, key=lambda x: x["net_revenue"])

    narrative = (
        f"Monthly revenue spans {len(trend)} months from {trend[0]['order_month']} to {trend[-1]['order_month']}. "
        f"The peak revenue occurred in {best_month['order_month']} with {best_month['net_revenue_formatted']} "
        f"({best_month['units_sold']} units), while {lowest_month['order_month']} was the lowest at {lowest_month['net_revenue_formatted']}."
    )

    return {
        "intent": "monthly_trend",
        "title": "Monthly Revenue Trend",
        "narrative": narrative,
        "figures": {
            "trend": trend,
            "best_month": best_month,
            "lowest_month": lowest_month,
            "total_months": len(trend)
        }
    }


def get_regional_revenue_ranking(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Computes sales breakdown across geographic regions and ranks them."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(SUM(net_revenue), 0.0) FROM sales_transactions WHERE is_eligible = 1;")
    total_revenue = cursor.fetchone()[0] or 0.0

    query = """
    SELECT
        region,
        COALESCE(SUM(net_revenue), 0.0) AS net_revenue,
        COALESCE(SUM(quantity), 0) AS units_sold,
        COUNT(*) AS transaction_count,
        COALESCE(AVG(net_revenue), 0.0) AS avg_order_value
    FROM sales_transactions
    WHERE is_eligible = 1
    GROUP BY region
    ORDER BY net_revenue DESC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "intent": "top_region",
            "title": "Regional Sales Breakdown",
            "narrative": "No transaction data available for regional ranking.",
            "figures": {"top_region": None, "ranking": []}
        }

    ranking: List[Dict[str, Any]] = []
    for r in rows:
        rev = round(float(r["net_revenue"]), 2)
        share = round((rev / total_revenue * 100), 2) if total_revenue > 0 else 0.0
        ranking.append({
            "region": r["region"],
            "net_revenue": rev,
            "net_revenue_formatted": format_currency(rev),
            "units_sold": int(r["units_sold"]),
            "transaction_count": int(r["transaction_count"]),
            "avg_order_value": round(float(r["avg_order_value"]), 2),
            "revenue_share_percentage": share
        })

    top_region = ranking[0]
    ties = [reg for reg in ranking if reg["net_revenue"] == top_region["net_revenue"]]

    if len(ties) > 1:
        tied_names = " and ".join(r["region"] for r in ties)
        narrative = (
            f"There is a tie for top region between {tied_names}, each generating "
            f"{top_region['net_revenue_formatted']} ({top_region['revenue_share_percentage']}% share)."
        )
    else:
        narrative = (
            f"The region generating the highest sales is '{top_region['region']}', "
            f"contributing {top_region['net_revenue_formatted']} across {top_region['transaction_count']} transactions "
            f"({top_region['units_sold']} units), representing {top_region['revenue_share_percentage']}% of overall revenue."
        )

    return {
        "intent": "top_region",
        "title": "Regional Sales Breakdown",
        "narrative": narrative,
        "figures": {
            "top_region": top_region,
            "ranking": ranking
        }
    }


def compare_monthly_revenue(
    month_a: str,
    month_b: str,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Compares revenue performance between two specific months using parameterized SQL.

    Handles identical months, non-existent months, zero-revenue base, and edge cases.
    """
    month_a = month_a.strip()
    month_b = month_b.strip()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = """
    SELECT
        order_month,
        COALESCE(SUM(net_revenue), 0.0) AS net_revenue,
        COALESCE(SUM(quantity), 0) AS units_sold,
        COUNT(*) AS transaction_count
    FROM sales_transactions
    WHERE is_eligible = 1 AND order_month IN (?, ?)
    GROUP BY order_month;
    """
    cursor.execute(query, (month_a, month_b))
    rows = {r["order_month"]: dict(r) for r in cursor.fetchall()}
    conn.close()

    # Retrieve data for each month (default to 0 if no records exist)
    data_a = rows.get(month_a, {
        "order_month": month_a,
        "net_revenue": 0.0,
        "units_sold": 0,
        "transaction_count": 0
    })
    data_b = rows.get(month_b, {
        "order_month": month_b,
        "net_revenue": 0.0,
        "units_sold": 0,
        "transaction_count": 0
    })

    rev_a = round(float(data_a["net_revenue"]), 2)
    rev_b = round(float(data_b["net_revenue"]), 2)
    diff = round(rev_b - rev_a, 2)

    # Percentage change calculation with zero division safety
    if rev_a > 0:
        pct_change = round((diff / rev_a) * 100, 2)
    elif rev_a == 0 and rev_b > 0:
        pct_change = 100.0  # From zero to positive
    elif rev_a == 0 and rev_b == 0:
        pct_change = 0.0
    else:
        pct_change = 0.0

    if diff > 0:
        direction = "increased"
        trend_symbol = "+"
    elif diff < 0:
        direction = "decreased"
        trend_symbol = "-"
    else:
        direction = "remained identical"
        trend_symbol = ""

    # Human-readable narrative
    if month_a == month_b:
        narrative = (
            f"Comparing {month_a} with itself: net revenue is {format_currency(rev_a)} "
            f"across {data_a['transaction_count']} transactions with 0% change."
        )
    else:
        abs_diff_formatted = format_currency(abs(diff))
        if direction == "remained identical":
            narrative = (
                f"Revenue between {month_a} ({format_currency(rev_a)}) and {month_b} ({format_currency(rev_b)}) "
                f"remained identical at {format_currency(rev_a)}."
            )
        else:
            narrative = (
                f"Revenue {direction} by {abs_diff_formatted} ({trend_symbol}{abs(pct_change):.2f}%) "
                f"from {month_a} ({format_currency(rev_a)}) to {month_b} ({format_currency(rev_b)})."
            )

    return {
        "intent": "month_comparison",
        "title": f"Month-over-Month Comparison: {month_a} vs {month_b}",
        "narrative": narrative,
        "figures": {
            "month_a": {
                "order_month": month_a,
                "net_revenue": rev_a,
                "net_revenue_formatted": format_currency(rev_a),
                "units_sold": data_a["units_sold"],
                "transaction_count": data_a["transaction_count"]
            },
            "month_b": {
                "order_month": month_b,
                "net_revenue": rev_b,
                "net_revenue_formatted": format_currency(rev_b),
                "units_sold": data_b["units_sold"],
                "transaction_count": data_b["transaction_count"]
            },
            "absolute_change": diff,
            "absolute_change_formatted": format_currency(abs(diff)),
            "percentage_change": pct_change,
            "direction": direction,
            "is_increase": diff > 0
        }
    }


def get_data_quality_report(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves full audit breakdown of eligible and excluded transactions."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM sales_transactions;")
    total = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM sales_transactions WHERE is_eligible = 1;")
    eligible = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM sales_transactions WHERE is_eligible = 0;")
    excluded = cursor.fetchone()[0] or 0

    cursor.execute("""
    SELECT
        transaction_id,
        raw_order_date,
        product,
        quantity,
        unit_price,
        status,
        exclusion_reason
    FROM sales_transactions
    WHERE is_eligible = 0
    ORDER BY transaction_id;
    """)
    excluded_rows = [dict(r) for r in cursor.fetchall()]

    conn.close()

    caveats = [
        f"{len(excluded_rows)} transaction(s) excluded from completed sales revenue per policy:",
    ]
    for row in excluded_rows:
        caveats.append(f"• Transaction {row['transaction_id']}: {row['exclusion_reason']}")

    return {
        "total_records": total,
        "eligible_records": eligible,
        "excluded_records": excluded,
        "excluded_details": excluded_rows,
        "caveats": caveats
    }
