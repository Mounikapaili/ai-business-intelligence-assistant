/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  DollarSign,
  Package,
  MapPin,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Database,
  Search,
  ArrowRight,
  ShieldAlert,
  BarChart3,
  RefreshCw,
  PieChart as PieIcon,
  Table,
  Filter,
  Sparkles
} from 'lucide-react';

interface HealthData {
  status: string;
  database: {
    connected: boolean;
    total_records: number;
    eligible_records: number;
    excluded_records: number;
  };
}

interface SummaryData {
  metrics: {
    total_transactions: number;
    eligible_transactions: number;
    excluded_transactions: number;
    unique_products: number;
    unique_regions: number;
  };
}

interface AskResponse {
  status: string;
  original_question: string;
  intent: string;
  intent_description: string;
  answer: string;
  supporting_figures: Record<string, any>;
  currency: string;
  currency_symbol: string;
  caveats: string[];
  execution_time_ms: number;
  suggested_questions?: string[];
}

export default function App() {
  const [activeView, setActiveView] = useState<'analytics' | 'dataset'>('analytics');
  const [health, setHealth] = useState<HealthData | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [question, setQuestion] = useState('What is the total revenue?');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [filterEligible, setFilterEligible] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Product colors for visual distinction
  const productColors: Record<string, string> = {
    'Monitor': '#2563EB',         // Vibrant Royal Blue
    'Desk': '#7C3AED',            // Rich Purple
    'Office Chair': '#059669',    // Emerald Green
    'USB-C Hub': '#EA580C',       // Warm Orange
    'Wireless Mouse': '#D97706',  // Amber Gold
    'Keyboard': '#0284C7',        // Sky Cyan
    'Laptop Stand': '#DB2777',    // Vibrant Magenta
  };

  const regionColors: Record<string, string> = {
    'South': '#4F46E5',  // Indigo
    'North': '#0D9488',  // Teal
    'East': '#E11D48',   // Crimson Rose
    'West': '#F59E0B',   // Warm Gold
  };

  useEffect(() => {
    fetchInitialData();
    handleAsk("What is the total revenue?");
  }, []);

  const fetchInitialData = async () => {
    try {
      const hRes = await fetch('/api/health');
      if (hRes.ok) setHealth(await hRes.json());

      const sRes = await fetch('/api/summary');
      if (sRes.ok) setSummary(await sRes.json());

      const tRes = await fetch('/api/transactions?limit=100');
      if (tRes.ok) {
        const tData = await tRes.json();
        setTransactions(tData.transactions || []);
      }
    } catch (e) {
      console.warn("Backend connection:", e);
    }
  };

  const handleAsk = async (queryToAsk?: string) => {
    const q = (queryToAsk || question).trim();
    if (!q) return;
    setLoading(true);
    setQuestion(q);
    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      if (res.ok) {
        const data = await res.json();
        setResponse(data);
      } else {
        const err = await res.json();
        setResponse({
          status: 'error',
          original_question: q,
          intent: 'error',
          intent_description: 'Query Error',
          answer: err.detail || 'Could not process question.',
          supporting_figures: {},
          currency: 'INR',
          currency_symbol: '₹',
          caveats: [],
          execution_time_ms: 0,
        });
      }
    } catch (e) {
      setResponse({
        status: 'error',
        original_question: q,
        intent: 'network_error',
        intent_description: 'Backend Offline',
        answer: 'Cannot connect to backend server. Make sure FastAPI is running.',
        supporting_figures: {},
        currency: 'INR',
        currency_symbol: '₹',
        caveats: [],
        execution_time_ms: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const sampleQuestions = [
    { label: "Total Revenue", q: "What is the total revenue?", icon: DollarSign, color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
    { label: "Top Product", q: "Which product generated the highest revenue?", icon: Package, color: "text-blue-600 bg-blue-50 border-blue-200" },
    { label: "Monthly Trend", q: "What is the monthly revenue trend?", icon: TrendingUp, color: "text-purple-600 bg-purple-50 border-purple-200" },
    { label: "Top Region", q: "Which region generated the highest sales?", icon: MapPin, color: "text-indigo-600 bg-indigo-50 border-indigo-200" },
    { label: "Compare Jan & Feb", q: "Compare January and February 2026", icon: Calendar, color: "text-amber-600 bg-amber-50 border-amber-200" },
    { label: "Between Months", q: "How did revenue change between two months?", icon: BarChart3, color: "text-rose-600 bg-rose-50 border-rose-200" },
  ];

  const excludedTransactions = [
    {
      id: "TXN0033",
      date: "26-04-2026",
      product: "Monitor",
      category: "Electronics",
      region: "West",
      qty: 2,
      price: "₹9,500",
      status: "Returned",
      reason: "Status is Returned. All customer returns are strictly excluded from completed revenue."
    },
    {
      id: "TXN0034",
      date: "28-04-2026",
      product: "Keyboard",
      category: "Accessories",
      region: "East",
      qty: 0,
      price: "₹900",
      status: "Completed",
      reason: "Quantity = 0. Non-positive order quantities are excluded from sales revenue calculations."
    },
    {
      id: "TXN0051",
      date: "28-06-2026",
      product: "Laptop Stand",
      category: "Accessories",
      region: "East",
      qty: 5,
      price: "Missing (Empty)",
      status: "Completed",
      reason: "Missing unit price. Business policy forbids silently converting null values to zero."
    }
  ];

  const filteredTransactions = transactions.filter((t) => {
    const matchesEligible = !filterEligible || t.is_eligible === 1;
    const matchesSearch = searchTerm === '' ||
      t.transaction_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.product.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.region.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.category.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesEligible && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100/70 to-indigo-50/30 text-slate-800 font-sans flex flex-col">
      {/* Executive Header */}
      <header className="bg-white/90 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 text-white flex items-center justify-center font-bold shadow-md shadow-blue-500/20">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
                  AI Business Intelligence Assistant
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700 tracking-wide uppercase">
                  Sales Analytics
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Accurate Natural Language Query Engine Backed by SQL
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Live SQL Database
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium">
              <Database className="w-3.5 h-3.5 text-slate-500" />
              48 Eligible Sales (51 Total)
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex gap-6 text-sm border-t border-slate-100">
          <button
            onClick={() => setActiveView('analytics')}
            className={`py-3 font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeView === 'analytics'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            Executive Query &amp; Visualizations
          </button>
          <button
            onClick={() => setActiveView('dataset')}
            className={`py-3 font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeView === 'dataset'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Table className="w-4 h-4" />
            Transactions &amp; Policy Governance
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full space-y-6">
        {activeView === 'analytics' ? (
          <>
            {/* Executive KPI Ribbon */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-shadow">
                <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
                  <span>Total Net Revenue</span>
                  <DollarSign className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="text-2xl font-black text-slate-900 mt-1.5 tracking-tight">₹1,439,200.00</div>
                <div className="text-xs text-emerald-600 font-medium mt-1">48 eligible transactions</div>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-shadow">
                <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
                  <span>Top Product</span>
                  <Package className="w-4 h-4 text-blue-500" />
                </div>
                <div className="text-2xl font-black text-slate-900 mt-1.5 tracking-tight">Monitor</div>
                <div className="text-xs text-blue-600 font-medium mt-1">₹473,000.00 (32.87% share)</div>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-shadow">
                <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
                  <span>Top Sales Region</span>
                  <MapPin className="w-4 h-4 text-indigo-500" />
                </div>
                <div className="text-2xl font-black text-slate-900 mt-1.5 tracking-tight">South</div>
                <div className="text-xs text-indigo-600 font-medium mt-1">₹411,200.00 (28.57% share)</div>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-shadow">
                <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider">
                  <span>Peak Month</span>
                  <Calendar className="w-4 h-4 text-purple-500" />
                </div>
                <div className="text-2xl font-black text-slate-900 mt-1.5 tracking-tight">May 2026</div>
                <div className="text-xs text-purple-600 font-medium mt-1">₹318,500.00 (116 units)</div>
              </div>
            </div>

            {/* Natural Language Query Bar */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600" />
                  <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Ask Any Sales Question</h2>
                </div>
                <span className="text-xs text-slate-500">Fast, accurate answers computed directly via SQL queries</span>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="w-5 h-5 absolute left-3.5 top-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                    placeholder="Ask about sales, top products, monthly trends, regions, or comparisons..."
                    className="w-full pl-11 pr-4 py-3 bg-slate-50 hover:bg-slate-50/80 border border-slate-300 rounded-xl text-slate-800 text-sm font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-inner"
                  />
                </div>
                <button
                  onClick={() => handleAsk()}
                  disabled={loading}
                  className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl text-sm flex items-center justify-center gap-2 shadow-md shadow-blue-500/20 active:scale-98 transition-all disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Querying Database...
                    </>
                  ) : (
                    <>
                      Ask Assistant
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              {/* Clickable Quick Sample Question Chips */}
              <div className="pt-2">
                <div className="text-xs font-semibold text-slate-500 mb-2">Click any supported question to test:</div>
                <div className="flex flex-wrap gap-2">
                  {sampleQuestions.map((sq, idx) => {
                    const Icon = sq.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleAsk(sq.q)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all hover:scale-[1.02] active:scale-98 cursor-pointer ${sq.color}`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        {sq.q}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Answer Display */}
            {response && (
              <div className="space-y-6">
                {/* Highlighted Narrative Answer */}
                <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50 border-2 border-emerald-300/80 p-5 rounded-2xl shadow-sm">
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-600 text-white text-xs font-bold uppercase tracking-wider shadow-xs">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {response.intent_description}
                    </span>
                    <span className="text-xs font-mono font-semibold text-emerald-800 bg-emerald-100/80 px-2 py-0.5 rounded-md">
                      SQL Query Time: {response.execution_time_ms} ms
                    </span>
                  </div>
                  <div className="text-base sm:text-lg font-bold text-emerald-950 leading-relaxed">
                    {response.answer}
                  </div>
                </div>

                {/* VISUAL REPRESENTATIONS (GRAPHS WITH DISTINCT VIBRANT COLOURS) */}
                <div className="space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-indigo-600" />
                      <h3 className="text-base font-bold text-slate-900 tracking-tight">
                        Interactive Visual Representations
                      </h3>
                    </div>
                    <span className="text-xs font-medium text-slate-500">Computed live from verified database transactions</span>
                  </div>

                  {/* 1. If Intent is Total Revenue: Category Breakdown with Vibrant Color Blocks */}
                  {response.intent === 'total_revenue' && response.supporting_figures.category_breakdown && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                      <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                        <div className="flex justify-between items-center">
                          <h4 className="font-bold text-slate-900 text-sm">Revenue by Category</h4>
                          <span className="text-xs text-slate-500">Accessories, Electronics &amp; Furniture</span>
                        </div>

                        {/* Category Progress Bars with Distinct Colors */}
                        <div className="space-y-4 pt-2">
                          {response.supporting_figures.category_breakdown.map((cat: any, i: number) => {
                            const colors = ['#2563EB', '#7C3AED', '#059669'];
                            const bgColors = ['bg-blue-600', 'bg-purple-600', 'bg-emerald-600'];
                            const share = ((cat.revenue / response.supporting_figures.total_net_revenue) * 100).toFixed(1);
                            return (
                              <div key={i} className="space-y-1.5">
                                <div className="flex justify-between items-center text-xs font-semibold">
                                  <span className="text-slate-800">{cat.category}</span>
                                  <span className="text-slate-900 font-bold">₹{cat.revenue.toLocaleString()} ({share}%)</span>
                                </div>
                                <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden p-0.5">
                                  <div
                                    className={`h-full rounded-full ${bgColors[i % bgColors.length]} transition-all duration-500`}
                                    style={{ width: `${share}%` }}
                                  ></div>
                                </div>
                                <div className="flex justify-between text-[11px] text-slate-500">
                                  <span>{cat.transactions} transactions</span>
                                  <span>{cat.units} units sold</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-indigo-900 via-blue-900 to-slate-900 text-white p-5 rounded-2xl shadow-sm flex flex-col justify-between">
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-blue-300">Executive Revenue Snapshot</span>
                          <div className="text-3xl font-extrabold mt-2 text-white">
                            {response.supporting_figures.total_net_revenue_formatted}
                          </div>
                          <p className="text-xs text-blue-200/80 mt-1">Across 48 eligible completed orders</p>
                        </div>

                        <div className="space-y-3 pt-4 border-t border-white/10 text-xs">
                          <div className="flex justify-between">
                            <span className="text-blue-200">Total Units Sold:</span>
                            <span className="font-bold text-white">{response.supporting_figures.total_units_sold}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-200">Total Discounts:</span>
                            <span className="font-bold text-white">{response.supporting_figures.total_discounts_formatted}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-blue-200">Average Order Value:</span>
                            <span className="font-bold text-white">{response.supporting_figures.average_order_value_formatted}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 2. If Intent is Top Product: Multi-colored Horizontal Ranking Bars */}
                  {response.intent === 'top_product' && response.supporting_figures.ranking && (
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
                      <div className="flex flex-wrap justify-between items-center gap-2">
                        <div>
                          <h4 className="font-bold text-slate-900 text-base">Full Product Revenue Ranking &amp; Shares</h4>
                          <p className="text-xs text-slate-500">Each product rendered in a distinct high-contrast color palette</p>
                        </div>
                        <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-xs font-bold">
                          Leading: {response.supporting_figures.top_product.product} (32.87%)
                        </span>
                      </div>

                      <div className="space-y-4">
                        {response.supporting_figures.ranking.map((prod: any, idx: number) => {
                          const barColor = productColors[prod.product] || '#4F46E5';
                          return (
                            <div key={idx} className="p-3.5 rounded-xl bg-slate-50 hover:bg-slate-100/70 transition-all border border-slate-200/60 space-y-2">
                              <div className="flex flex-wrap justify-between items-center text-xs font-bold">
                                <div className="flex items-center gap-2">
                                  <span
                                    className="w-5 h-5 rounded-full text-white flex items-center justify-center text-[10px] font-black"
                                    style={{ backgroundColor: barColor }}
                                  >
                                    {idx + 1}
                                  </span>
                                  <span className="text-slate-900 text-sm">{prod.product}</span>
                                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-200 text-slate-700">
                                    {prod.category}
                                  </span>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span className="text-slate-900 text-sm font-extrabold">{prod.net_revenue_formatted}</span>
                                  <span
                                    className="px-2 py-0.5 rounded-full text-xs font-bold text-white shadow-xs"
                                    style={{ backgroundColor: barColor }}
                                  >
                                    {prod.revenue_share_percentage}%
                                  </span>
                                </div>
                              </div>

                              {/* Vibrant Progress Bar */}
                              <div className="w-full bg-slate-200/80 h-3.5 rounded-full overflow-hidden p-0.5 shadow-inner">
                                <div
                                  className="h-full rounded-full transition-all duration-700"
                                  style={{
                                    width: `${prod.revenue_share_percentage}%`,
                                    backgroundColor: barColor
                                  }}
                                ></div>
                              </div>

                              <div className="flex justify-between text-[11px] text-slate-500 font-medium">
                                <span>{prod.transaction_count} orders completed</span>
                                <span>{prod.units_sold} units sold</span>
                                <span>Avg Price: ₹{prod.avg_unit_price.toLocaleString()}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* 3. If Intent is Monthly Trend: Vibrant Month-by-Month Column Visualization */}
                  {response.intent === 'monthly_trend' && response.supporting_figures.trend && (
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
                      <div className="flex flex-wrap justify-between items-center gap-2">
                        <div>
                          <h4 className="font-bold text-slate-900 text-base">Monthly Revenue Trend (January – June 2026)</h4>
                          <p className="text-xs text-slate-500">Visual comparison of revenue performance and monthly volume</p>
                        </div>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="flex items-center gap-1.5 font-semibold text-purple-700 bg-purple-50 px-2.5 py-1 rounded-lg border border-purple-200">
                            ★ Peak Month: May 2026 (₹318,500)
                          </span>
                        </div>
                      </div>

                      {/* Month Column Cards with Colors and Visual Height */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
                        {response.supporting_figures.trend.map((m: any, idx: number) => {
                          const monthColors = ['#0284C7', '#2563EB', '#4F46E5', '#7C3AED', '#9333EA', '#059669'];
                          const color = monthColors[idx % monthColors.length];
                          const maxRev = 318500.0;
                          const heightPct = Math.round((m.net_revenue / maxRev) * 100);

                          return (
                            <div
                              key={idx}
                              className={`p-4 rounded-xl border flex flex-col justify-between transition-all hover:-translate-y-1 shadow-xs ${
                                m.order_month === '2026-05'
                                  ? 'bg-purple-50/70 border-purple-300 ring-2 ring-purple-400/50'
                                  : 'bg-white border-slate-200 hover:border-slate-300'
                              }`}
                            >
                              <div className="text-center">
                                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                                  {m.order_month}
                                </span>
                                <div className="text-base font-extrabold text-slate-900 mt-1">
                                  {m.net_revenue_formatted}
                                </div>
                              </div>

                              {/* Visual Height Gauge */}
                              <div className="h-28 flex items-end justify-center my-3 bg-slate-100 rounded-lg p-1.5">
                                <div
                                  className="w-full rounded-md transition-all duration-700 shadow-sm"
                                  style={{
                                    height: `${heightPct}%`,
                                    backgroundColor: color
                                  }}
                                ></div>
                              </div>

                              <div className="text-center text-[11px] space-y-1">
                                <div className="text-slate-600 font-medium">{m.units_sold} units sold</div>
                                {idx > 0 ? (
                                  <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    m.growth_amount >= 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                                  }`}>
                                    {m.growth_amount >= 0 ? '+' : ''}{m.growth_percentage}%
                                  </span>
                                ) : (
                                  <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">
                                    Base Month
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* 4. If Intent is Top Region: Colorful Territory Cards & Market Share Bars */}
                  {response.intent === 'top_region' && response.supporting_figures.ranking && (
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
                      <div className="flex justify-between items-center">
                        <div>
                          <h4 className="font-bold text-slate-900 text-base">Regional Sales Breakdown &amp; Market Distribution</h4>
                          <p className="text-xs text-slate-500">Sales territory performance with color-coded rankings</p>
                        </div>
                        <span className="px-3 py-1 rounded-full bg-indigo-100 text-indigo-800 text-xs font-bold">
                          Top: {response.supporting_figures.top_region.region} (28.57%)
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {response.supporting_figures.ranking.map((reg: any, idx: number) => {
                          const col = regionColors[reg.region] || '#4F46E5';
                          return (
                            <div
                              key={idx}
                              className="p-5 rounded-2xl border border-slate-200 bg-white hover:shadow-md transition-all space-y-3"
                              style={{ borderTop: `4px solid ${col}` }}
                            >
                              <div className="flex justify-between items-center">
                                <span className="text-sm font-bold text-slate-900">{reg.region} Region</span>
                                <span
                                  className="px-2 py-0.5 rounded-full text-xs font-bold text-white shadow-xs"
                                  style={{ backgroundColor: col }}
                                >
                                  Rank #{idx + 1}
                                </span>
                              </div>

                              <div className="text-2xl font-black text-slate-900">{reg.net_revenue_formatted}</div>

                              <div className="space-y-1">
                                <div className="flex justify-between text-xs font-semibold text-slate-600">
                                  <span>Market Share:</span>
                                  <span className="font-bold text-slate-900">{reg.revenue_share_percentage}%</span>
                                </div>
                                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{
                                      width: `${reg.revenue_share_percentage}%`,
                                      backgroundColor: col
                                    }}
                                  ></div>
                                </div>
                              </div>

                              <div className="pt-2 border-t border-slate-100 flex justify-between text-[11px] text-slate-500">
                                <span>{reg.transaction_count} transactions</span>
                                <span>{reg.units_sold} units sold</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* 5. If Intent is Month Comparison: Visual Delta Cards & Comparison Chart */}
                  {response.intent === 'month_comparison' && response.supporting_figures.month_a && (
                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
                      <div className="flex justify-between items-center">
                        <h4 className="font-bold text-slate-900 text-base">
                          Month-to-Month Variance: {response.supporting_figures.month_a.order_month} vs {response.supporting_figures.month_b.order_month}
                        </h4>
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                          response.supporting_figures.is_increase ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {response.supporting_figures.is_increase ? 'Revenue Growth' : 'Revenue Contraction'}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="p-5 rounded-2xl bg-blue-50/70 border border-blue-200 text-center space-y-1">
                          <span className="text-xs font-bold text-blue-700 uppercase tracking-wider">
                            Base Month ({response.supporting_figures.month_a.order_month})
                          </span>
                          <div className="text-2xl font-black text-slate-900">
                            {response.supporting_figures.month_a.net_revenue_formatted}
                          </div>
                          <div className="text-xs text-slate-600 font-medium">
                            {response.supporting_figures.month_a.transaction_count} orders completed
                          </div>
                        </div>

                        <div className="p-5 rounded-2xl bg-purple-50/70 border border-purple-200 text-center space-y-1">
                          <span className="text-xs font-bold text-purple-700 uppercase tracking-wider">
                            Comparison Month ({response.supporting_figures.month_b.order_month})
                          </span>
                          <div className="text-2xl font-black text-slate-900">
                            {response.supporting_figures.month_b.net_revenue_formatted}
                          </div>
                          <div className="text-xs text-slate-600 font-medium">
                            {response.supporting_figures.month_b.transaction_count} orders completed
                          </div>
                        </div>

                        <div className={`p-5 rounded-2xl border text-center space-y-1 ${
                          response.supporting_figures.is_increase
                            ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
                            : 'bg-rose-50 border-rose-300 text-rose-950'
                        }`}>
                          <span className="text-xs font-bold uppercase tracking-wider opacity-80">
                            Net Absolute Difference
                          </span>
                          <div className="text-2xl font-black">
                            {response.supporting_figures.is_increase ? '+' : '-'}{response.supporting_figures.absolute_change_formatted}
                          </div>
                          <div className="text-xs font-bold">
                            {response.supporting_figures.percentage_change}% {response.supporting_figures.direction}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Revenue Governance Caveats Banner */}
                  {response.caveats && response.caveats.length > 0 && (
                    <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-200 text-amber-900 text-xs space-y-1.5 shadow-xs">
                      <div className="font-bold flex items-center gap-1.5 text-amber-900">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        Revenue Policy Compliance Audit:
                      </div>
                      {response.caveats.map((c, i) => (
                        <div key={i} className="pl-5 text-amber-800">{c}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        ) : (
          /* View 2: Complete Dataset & Policy Governance */
          <div className="space-y-6">
            {/* Excluded Records Table */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Data Governance: Verified Excluded Transactions (3 Records)
                </h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Per business policy, returned goods, non-positive quantities, and missing prices are excluded from completed sales revenue calculations without altering the original raw CSV:
              </p>

              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="p-3">Txn ID</th>
                      <th className="p-3">Order Date</th>
                      <th className="p-3">Product</th>
                      <th className="p-3">Region</th>
                      <th className="p-3">Quantity</th>
                      <th className="p-3">Unit Price</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Policy Audit Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {excludedTransactions.map((ex, idx) => (
                      <tr key={idx} className="bg-amber-50/30 hover:bg-amber-50/70 transition-colors">
                        <td className="p-3 font-mono font-bold text-slate-900">{ex.id}</td>
                        <td className="p-3">{ex.date}</td>
                        <td className="p-3 font-semibold text-slate-800">{ex.product}</td>
                        <td className="p-3">{ex.region}</td>
                        <td className={`p-3 font-bold ${ex.qty === 0 ? 'text-rose-600' : ''}`}>{ex.qty}</td>
                        <td className={`p-3 font-bold ${ex.price.includes('Missing') ? 'text-rose-600' : ''}`}>{ex.price}</td>
                        <td className={`p-3 font-bold ${ex.status === 'Returned' ? 'text-rose-600' : ''}`}>{ex.status}</td>
                        <td className="p-3 text-slate-700 font-medium">{ex.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Filterable Clean Transactions Table */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <h3 className="text-base font-bold text-slate-900">
                  Cleaned Sales Database ({filteredTransactions.length} of {transactions.length} transactions)
                </h3>

                <div className="flex flex-wrap items-center gap-3">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Search transactions..."
                      className="pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filterEligible}
                      onChange={(e) => setFilterEligible(e.target.checked)}
                      className="rounded text-blue-600"
                    />
                    Eligible only (48)
                  </label>
                </div>
              </div>

              <div className="overflow-x-auto max-h-96 border border-slate-200 rounded-xl">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-100 text-slate-700 font-semibold sticky top-0 border-b border-slate-200">
                    <tr>
                      <th className="p-2.5">ID</th>
                      <th className="p-2.5">Date</th>
                      <th className="p-2.5">Product</th>
                      <th className="p-2.5">Category</th>
                      <th className="p-2.5">Region</th>
                      <th className="p-2.5">Channel</th>
                      <th className="p-2.5">Qty</th>
                      <th className="p-2.5">Price</th>
                      <th className="p-2.5">Discount</th>
                      <th className="p-2.5">Net Revenue</th>
                      <th className="p-2.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {filteredTransactions.map((t, idx) => (
                      <tr key={idx} className={t.is_eligible === 0 ? 'bg-amber-50/50' : 'hover:bg-slate-50'}>
                        <td className="p-2.5 font-bold text-slate-900">{t.transaction_id}</td>
                        <td className="p-2.5">{t.raw_order_date}</td>
                        <td className="p-2.5 font-sans font-medium text-slate-800">{t.product}</td>
                        <td className="p-2.5 font-sans">{t.category}</td>
                        <td className="p-2.5 font-sans">{t.region}</td>
                        <td className="p-2.5 font-sans">{t.sales_channel}</td>
                        <td className="p-2.5">{t.quantity}</td>
                        <td className="p-2.5">{t.unit_price ? `₹${t.unit_price.toLocaleString()}` : '—'}</td>
                        <td className="p-2.5">₹{t.discount_amount}</td>
                        <td className="p-2.5 font-bold text-slate-900">{t.net_revenue ? `₹${t.net_revenue.toLocaleString()}` : '—'}</td>
                        <td className="p-2.5 font-sans">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            t.status === 'Completed' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                          }`}>
                            {t.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200/80 py-4 text-center text-xs text-slate-500 font-medium">
        AI Business Intelligence Assistant • SQL Analytics Engine
      </footer>
    </div>
  );
}
