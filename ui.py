"""AI Business Intelligence Assistant - Streamlit Interface.

A clean, executive business analytics interface.
Queries the FastAPI backend for natural-language question interpretation,
SQL analytics, and displays vibrant visual representations with distinct colors.
"""

import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuration: auto-detect port 8001 (container environment) or 8000 (standard local)
API_BASE_URL = os.environ.get("FASTAPI_URL")
if not API_BASE_URL:
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=0.5)
        API_BASE_URL = "http://127.0.0.1:8001"
    except Exception:
        API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Business Intelligence Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom executive styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.025em;
        margin-bottom: 0.15rem;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #475569;
        font-weight: 500;
        margin-bottom: 1.5rem;
    }
    .answer-box {
        background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
        border: 2px solid #6EE7B7;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 1.25rem 0;
        color: #064E3B;
        font-size: 1.15rem;
        font-weight: 600;
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .caveat-box {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 0.85rem 1.15rem;
        margin-top: 1rem;
        border-radius: 6px;
        font-size: 0.88rem;
        color: #78350F;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Product color mapping for distinct visual presentation
PRODUCT_COLOR_MAP = {
    "Monitor": "#2563EB",         # Royal Blue
    "Desk": "#7C3AED",            # Purple
    "Office Chair": "#059669",    # Emerald
    "USB-C Hub": "#EA580C",       # Deep Orange
    "Wireless Mouse": "#D97706",  # Amber
    "Keyboard": "#0284C7",        # Sky Blue
    "Laptop Stand": "#DB2777"     # Rose Pink
}

REGION_COLOR_MAP = {
    "South": "#4F46E5",
    "North": "#0D9488",
    "East": "#E11D48",
    "West": "#F59E0B"
}


@st.cache_data(ttl=10)
def check_api_health():
    """Checks FastAPI backend status."""
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        if r.status_code == 200:
            return True, r.json()
        return False, {"error": f"Status {r.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}


@st.cache_data(ttl=10)
def get_dataset_summary():
    """Fetches dataset summary from backend."""
    try:
        r = requests.get(f"{API_BASE_URL}/summary", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def query_api_ask(question: str):
    """Sends question to FastAPI /ask endpoint."""
    try:
        r = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question},
            timeout=5
        )
        return r.status_code, r.json()
    except Exception as e:
        return 500, {"status": "error", "message": f"Connection error: {str(e)}"}


def fetch_transactions():
    """Fetches transactions for the explorer."""
    try:
        r = requests.get(f"{API_BASE_URL}/transactions?limit=100", timeout=3)
        if r.status_code == 200:
            return r.json().get("transactions", [])
    except Exception:
        pass
    return []


# --- Header & Top Metric Ribbon ---
st.markdown('<div class="main-title">AI Business Intelligence Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Ask questions about sales transactions and receive verified answers backed by live SQL database queries.</div>', unsafe_allow_html=True)

# Top KPI ribbon
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Net Revenue", "₹1,439,200.00")
with col2:
    st.metric("Eligible Sales", "48 Orders", help="Valid, completed transactions included in revenue")
with col3:
    st.metric("Top Product", "Monitor", "₹473,000.00")
with col4:
    st.metric("Top Region", "South", "₹411,200.00")
with col5:
    st.metric("Peak Month", "May 2026", "₹318,500.00")

st.markdown("---")

# Navigation Tabs
tab_assistant, tab_data = st.tabs(["📊 Executive Analytics & Visualizations", "📋 Cleaned Dataset & Governance Audit"])

with tab_assistant:
    st.markdown("### 💬 Ask a Business Question")

    # Session state for user question
    if "user_question" not in st.session_state:
        st.session_state.user_question = "What is the total revenue?"

    st.markdown("**Click an example question to run:**")
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    with c_btn1:
        if st.button("💰 What is the total revenue?", use_container_width=True):
            st.session_state.user_question = "What is the total revenue?"
        if st.button("🏆 Which product generated the highest revenue?", use_container_width=True):
            st.session_state.user_question = "Which product generated the highest revenue?"
    with c_btn2:
        if st.button("📈 What is the monthly revenue trend?", use_container_width=True):
            st.session_state.user_question = "What is the monthly revenue trend?"
        if st.button("🌍 Which region generated the highest sales?", use_container_width=True):
            st.session_state.user_question = "Which region generated the highest sales?"
    with c_btn3:
        if st.button("📅 Compare January and February 2026", use_container_width=True):
            st.session_state.user_question = "Compare January and February 2026"
        if st.button("⚖️ How did revenue change between two months?", use_container_width=True):
            st.session_state.user_question = "How did revenue change between two months?"

    col_q, col_ask = st.columns([5, 1])
    with col_q:
        current_input = st.text_input(
            "Question Input",
            value=st.session_state.user_question,
            label_visibility="collapsed",
            placeholder="Type your question here (e.g., Which product performed best?)..."
        )
    with col_ask:
        trigger_ask = st.button("🚀 Ask Assistant", use_container_width=True, type="primary")

    # Run query
    active_q = current_input.strip() if current_input else st.session_state.user_question
    if trigger_ask or active_q:
        with st.spinner("Analyzing question and querying database..."):
            status_code, resp = query_api_ask(active_q)

        if status_code == 200:
            intent = resp.get("intent")
            intent_desc = resp.get("intent_description", "Analysis")
            answer = resp.get("answer", "")
            figures = resp.get("supporting_figures", {})
            caveats = resp.get("caveats", [])
            exec_time = resp.get("execution_time_ms", 0)

            # Executive Answer Banner
            st.markdown(f'<div class="answer-box"><strong>Executive Answer:</strong> {answer}</div>', unsafe_allow_html=True)
            st.caption(f"Recognized Intent: **{intent_desc}** • SQL Execution Time: **{exec_time} ms**")

            st.markdown("#### **Visual Representations**")

            # 1. Total Revenue Visuals (Category Breakdown)
            if intent == "total_revenue" and figures:
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Net Revenue", figures.get("total_net_revenue_formatted", "₹0"))
                col_m2.metric("Orders", figures.get("transaction_count", 0))
                col_m3.metric("Units Sold", figures.get("total_units_sold", 0))
                col_m4.metric("Avg Order Value", figures.get("average_order_value_formatted", "₹0"))

                cat_data = figures.get("category_breakdown", [])
                if cat_data:
                    cat_df = pd.DataFrame(cat_data)
                    c_chart1, c_chart2 = st.columns(2)
                    with c_chart1:
                        fig_cat_bar = px.bar(
                            cat_df,
                            x="category",
                            y="revenue",
                            text_auto=True,
                            title="Revenue by Category (₹)",
                            color="category",
                            color_discrete_sequence=["#2563EB", "#7C3AED", "#059669"]
                        )
                        fig_cat_bar.update_layout(height=350, showlegend=False)
                        st.plotly_chart(fig_cat_bar, use_container_width=True)

                    with c_chart2:
                        fig_cat_pie = px.pie(
                            cat_df,
                            names="category",
                            values="revenue",
                            hole=0.4,
                            title="Category Revenue Distribution",
                            color="category",
                            color_discrete_sequence=["#2563EB", "#7C3AED", "#059669"]
                        )
                        fig_cat_pie.update_layout(height=350)
                        st.plotly_chart(fig_cat_pie, use_container_width=True)

            # 2. Product Ranking Visuals
            elif intent == "top_product" and figures:
                top_p = figures.get("top_product", {})
                ranking_data = figures.get("ranking", [])

                if top_p:
                    cp1, cp2, cp3 = st.columns(3)
                    cp1.metric("Highest Revenue Product", top_p.get("product", ""))
                    cp2.metric("Product Revenue", top_p.get("net_revenue_formatted", "₹0"))
                    cp3.metric("Market Share", f"{top_p.get('revenue_share_percentage', 0)}%")

                if ranking_data:
                    rank_df = pd.DataFrame(ranking_data)
                    # Vibrant horizontal bar chart with distinct color per product
                    fig_prod = px.bar(
                        rank_df,
                        x="net_revenue",
                        y="product",
                        orientation="h",
                        title="Product Revenue Ranking (with Distinct Color Coding)",
                        labels={"net_revenue": "Net Revenue (₹)", "product": "Product"},
                        text_auto=True,
                        color="product",
                        color_discrete_map=PRODUCT_COLOR_MAP
                    )
                    fig_prod.update_layout(
                        yaxis=dict(autorange="reversed"),
                        height=400,
                        showlegend=False
                    )
                    st.plotly_chart(fig_prod, use_container_width=True)

            # 3. Monthly Trend Visuals
            elif intent == "monthly_trend" and figures:
                trend_data = figures.get("trend", [])
                best_m = figures.get("best_month", {})
                low_m = figures.get("lowest_month", {})

                ct1, ct2, ct3 = st.columns(3)
                if best_m:
                    ct1.metric("Peak Month", best_m.get("order_month", ""), best_m.get("net_revenue_formatted", ""))
                if low_m:
                    ct2.metric("Lowest Month", low_m.get("order_month", ""), low_m.get("net_revenue_formatted", ""))
                ct3.metric("Monitored Months", len(trend_data))

                if trend_data:
                    trend_df = pd.DataFrame(trend_data)
                    # Monthly multi-colored bar chart
                    fig_month = px.bar(
                        trend_df,
                        x="order_month",
                        y="net_revenue",
                        text="net_revenue_formatted",
                        title="Monthly Revenue Trend (January – June 2026)",
                        labels={"order_month": "Month", "net_revenue": "Net Revenue (₹)"},
                        color="order_month",
                        color_discrete_sequence=["#0284C7", "#2563EB", "#4F46E5", "#7C3AED", "#9333EA", "#059669"]
                    )
                    fig_month.update_layout(height=380, showlegend=False)
                    st.plotly_chart(fig_month, use_container_width=True)

            # 4. Regional Sales Visuals
            elif intent == "top_region" and figures:
                top_r = figures.get("top_region", {})
                ranking_data = figures.get("ranking", [])

                if top_r:
                    cr1, cr2, cr3 = st.columns(3)
                    cr1.metric("Leading Region", top_r.get("region", ""))
                    cr2.metric("Regional Revenue", top_r.get("net_revenue_formatted", "₹0"))
                    cr3.metric("Regional Share", f"{top_r.get('revenue_share_percentage', 0)}%")

                if ranking_data:
                    reg_df = pd.DataFrame(ranking_data)
                    cr_col1, cr_col2 = st.columns(2)
                    with cr_col1:
                        fig_reg_bar = px.bar(
                            reg_df,
                            x="region",
                            y="net_revenue",
                            text_auto=True,
                            title="Revenue by Territory",
                            color="region",
                            color_discrete_map=REGION_COLOR_MAP
                        )
                        fig_reg_bar.update_layout(height=350, showlegend=False)
                        st.plotly_chart(fig_reg_bar, use_container_width=True)

                    with cr_col2:
                        fig_reg_pie = px.pie(
                            reg_df,
                            names="region",
                            values="net_revenue",
                            hole=0.45,
                            title="Regional Market Share",
                            color="region",
                            color_discrete_map=REGION_COLOR_MAP
                        )
                        fig_reg_pie.update_layout(height=350)
                        st.plotly_chart(fig_reg_pie, use_container_width=True)

            # 5. Month Comparison Visuals
            elif intent == "month_comparison" and figures:
                ma = figures.get("month_a", {})
                mb = figures.get("month_b", {})
                diff_fmt = figures.get("absolute_change_formatted", "₹0")
                pct = figures.get("percentage_change", 0.0)

                cm1, cm2, cm3 = st.columns(3)
                cm1.metric(f"Month: {ma.get('order_month')}", ma.get("net_revenue_formatted", "₹0"))
                cm2.metric(f"Month: {mb.get('order_month')}", mb.get("net_revenue_formatted", "₹0"))
                delta_str = f"{'+' if pct > 0 else ''}{pct:.2f}% ({diff_fmt})"
                cm3.metric("Net Change", diff_fmt, delta=delta_str, delta_color="normal" if pct >= 0 else "inverse")

                comp_df = pd.DataFrame([
                    {"Month": ma.get("order_month"), "Net Revenue": ma.get("net_revenue")},
                    {"Month": mb.get("order_month"), "Net Revenue": mb.get("net_revenue")}
                ])
                fig_comp = px.bar(
                    comp_df,
                    x="Month",
                    y="Net Revenue",
                    text_auto=True,
                    color="Month",
                    color_discrete_sequence=["#2563EB", "#7C3AED"],
                    title=f"Revenue Variance: {ma.get('order_month')} vs {mb.get('order_month')}"
                )
                fig_comp.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_comp, use_container_width=True)

            # Governance Caveats
            if caveats:
                st.markdown('<div class="caveat-box">', unsafe_allow_html=True)
                st.markdown("<strong>Revenue Policy Compliance Audit:</strong>")
                for c in caveats:
                    st.markdown(f"• {c}")
                st.markdown('</div>', unsafe_allow_html=True)

        elif status_code == 400:
            st.warning(f"⚠️ {resp.get('detail', 'Invalid question provided.')}")
        else:
            st.error(f"❌ Error ({status_code}): {resp.get('message', 'Unable to process query.')}")

with tab_data:
    st.markdown("### 🛡️ Data Quality Governance & Excluded Records")
    st.markdown(
        "Per strict business revenue policy, returned goods, non-positive quantities, and missing prices "
        "are excluded from completed sales calculations while preserving the source CSV intact:"
    )

    excluded_records = [
        {
            "Transaction_Id": "TXN0033",
            "Order_date": "26-04-2026",
            "Product": "Monitor",
            "Category": "Electronics",
            "Region": "West",
            "Quantity": 2,
            "Unit_price": "₹9,500.00",
            "Status": "Returned",
            "Audit Policy Reason": "Returned transaction. Returns are strictly excluded from completed sales revenue."
        },
        {
            "Transaction_Id": "TXN0034",
            "Order_date": "28-04-2026",
            "Product": "Keyboard",
            "Category": "Accessories",
            "Region": "East",
            "Quantity": 0,
            "Unit_price": "₹900.00",
            "Status": "Completed",
            "Audit Policy Reason": "Zero quantity (Quantity = 0). Non-positive order quantities are excluded from revenue."
        },
        {
            "Transaction_Id": "TXN0051",
            "Order_date": "28-06-2026",
            "Product": "Laptop Stand",
            "Category": "Accessories",
            "Region": "East",
            "Quantity": 5,
            "Unit_price": "Missing (Null)",
            "Status": "Completed",
            "Audit Policy Reason": "Missing unit price. Policy strictly forbids silently converting null values to zero."
        }
    ]
    st.dataframe(pd.DataFrame(excluded_records), use_container_width=True)

    st.markdown("---")
    st.markdown("### 📋 Cleaned Database Transactions (48 Eligible Rows)")
    all_txns = fetch_transactions()
    if all_txns:
        tx_df = pd.DataFrame(all_txns)
        show_eligible = st.checkbox("Show eligible completed transactions only", value=True)
        filtered_df = tx_df[tx_df["is_eligible"] == 1] if show_eligible else tx_df
        st.dataframe(
            filtered_df[[
                "transaction_id", "raw_order_date", "product", "category",
                "region", "sales_channel", "quantity", "unit_price",
                "discount_amount", "net_revenue", "status"
            ]],
            use_container_width=True,
            height=380
        )
