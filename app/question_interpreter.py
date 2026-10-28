"""Safe Question Interpretation Module for AI Business Intelligence Assistant.

Interprets natural language business questions using robust deterministic matching,
keyword heuristics, and regex parameter extraction. Maps questions exclusively to
approved analytics functions.

Design Highlights:
- No arbitrary SQL generation or execution (completely SQL-injection proof).
- Robust recognition of common phrasings and variations for the 5 core questions.
- Month parameter extractor for comparison questions (e.g. "January vs February 2026").
- Clear handling and guidance for ambiguous or unsupported queries.
- Modular architecture allowing optional future LLM plugin integration.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntentType(str, Enum):
    TOTAL_REVENUE = "total_revenue"
    TOP_PRODUCT = "top_product"
    MONTHLY_TREND = "monthly_trend"
    TOP_REGION = "top_region"
    MONTH_COMPARISON = "month_comparison"
    UNKNOWN = "unknown"


@dataclass
class InterpretationResult:
    original_question: str
    intent: IntentType
    confidence: float
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    matched_rule: str = ""
    error_message: Optional[str] = None
    suggested_questions: List[str] = field(default_factory=list)


MONTH_NAME_TO_NUMBER = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12"
}

EXAMPLE_QUESTIONS = [
    "What is the total revenue?",
    "Which product generated the highest revenue?",
    "What is the monthly revenue trend?",
    "Which region generated the highest sales?",
    "How did revenue change between two months?",
    "Compare January and February 2026",
    "Show sales month by month",
    "Which product performed best?",
    "Which region performed best?",
    "Compare 2026-01 to 2026-02"
]


def extract_months_from_query(text: str, default_year: int = 2026) -> List[str]:
    """Extracts up to 2 distinct YYYY-MM formatted month strings from free text.

    Supports:
    - 'January 2026', 'Jan 2026', 'February', etc.
    - '2026-01', '2026-02', etc.
    - '01/2026', '02-2026'
    """
    clean_text = text.lower()
    found_months: List[str] = []

    # 1. Match ISO YYYY-MM
    iso_matches = re.findall(r"\b(20\d\d)[-/](0[1-9]|1[0-2])\b", clean_text)
    for year, m in iso_matches:
        month_str = f"{year}-{m}"
        if month_str not in found_months:
            found_months.append(month_str)

    # 2. Match MM-YYYY or MM/YYYY
    rev_matches = re.findall(r"\b(0[1-9]|1[0-2])[-/](20\d\d)\b", clean_text)
    for m, year in rev_matches:
        month_str = f"{year}-{m}"
        if month_str not in found_months:
            found_months.append(month_str)

    # 3. Match month names with optional explicit year (e.g. "January 2026" or just "January")
    # Pattern looks for month name followed optionally by 4-digit year
    month_names_pattern = r"\b(" + "|".join(MONTH_NAME_TO_NUMBER.keys()) + r")\b(?:\s+(20\d\d))?"
    matches = re.findall(month_names_pattern, clean_text)

    # Detect if a standalone year is mentioned in the sentence
    general_year_match = re.search(r"\b(20\d\d)\b", clean_text)
    fallback_year = int(general_year_match.group(1)) if general_year_match else default_year

    for name, explicit_year in matches:
        month_num = MONTH_NAME_TO_NUMBER[name]
        yr = explicit_year if explicit_year else str(fallback_year)
        month_str = f"{yr}-{month_num}"
        if month_str not in found_months:
            found_months.append(month_str)

    return found_months


class SafeQuestionInterpreter:
    """Interprets business user questions into sanctioned analytics queries."""

    def __init__(self):
        # Regex and keyword rules ranked by specificity
        self.rules = [
            # 1. Month-over-Month Comparison
            {
                "intent": IntentType.MONTH_COMPARISON,
                "description": "Month-to-Month Revenue Comparison",
                "patterns": [
                    r"\bcompare\b.*\b(month|january|february|march|april|may|june|2026)\b",
                    r"\bchange between (two )?months\b",
                    r"\bchange (from|between)\b.*\b(to|and)\b",
                    r"\bmonth[- ]over[- ]month\b",
                    r"\bhow did revenue change\b",
                    r"\brevenue (difference|growth|shift) between\b",
                    r"\b(january|february|march|april|may|june|2026-\d\d)\s+(vs|versus|and|to)\s+(january|february|march|april|may|june|2026-\d\d)\b"
                ],
                "keywords": ["compare", "change between", "vs", "versus"]
            },
            # 2. Product Ranking
            {
                "intent": IntentType.TOP_PRODUCT,
                "description": "Product Revenue Ranking",
                "patterns": [
                    r"\b(which|what|top|highest|best|leading|most)\s+product\b",
                    r"\bproduct\s+(generated|produced|had|brought)\s+(the\s+)?(highest|most|top|best)\b",
                    r"\bproduct.*(revenue|sales|ranking|breakdown|performance)\b",
                    r"\bbest[- ]selling product\b",
                    r"\bhighest[- ]grossing product\b",
                    r"\bwhich item (made|generated|sold)\b",
                    r"\bproduct performed best\b"
                ],
                "keywords": ["product", "item", "laptop stand", "monitor", "keyboard", "desk", "chair"]
            },
            # 3. Monthly Trend
            {
                "intent": IntentType.MONTHLY_TREND,
                "description": "Monthly Revenue Trend",
                "patterns": [
                    r"\bmonthly\s+(revenue|sales|trend|performance|breakdown)\b",
                    r"\bmonth\s+by\s+month\b",
                    r"\b(revenue|sales)\s+over\s+time\b",
                    r"\bmonthly trend\b",
                    r"\bsales trend\b",
                    r"\beach month\b",
                    r"\btrend of (sales|revenue)\b",
                    r"\bby month\b"
                ],
                "keywords": ["monthly", "month by month", "trend", "over time"]
            },
            # 4. Regional Ranking
            {
                "intent": IntentType.TOP_REGION,
                "description": "Regional Sales Ranking",
                "patterns": [
                    r"\b(which|what|top|highest|best|leading)\s+(region|area|territory|zone|location)\b",
                    r"\bregion\s+(generated|produced|had|brought)\s+(the\s+)?(highest|most|top|best)\b",
                    r"\b(sales|revenue)\s+by\s+region\b",
                    r"\bregional\s+(sales|revenue|breakdown|performance|ranking)\b",
                    r"\bregion performed best\b",
                    r"\bwhich region\b"
                ],
                "keywords": ["region", "regional", "north", "south", "east", "west", "territory"]
            },
            # 5. Total Revenue
            {
                "intent": IntentType.TOTAL_REVENUE,
                "description": "Total Net Revenue Analysis",
                "patterns": [
                    r"\btotal\s+(net\s+)?(revenue|sales|turnover|income|earnings)\b",
                    r"\bhow much (money|revenue|sales)\s+(did we make|was generated|total)\b",
                    r"\boverall\s+(revenue|sales|performance)\b",
                    r"\bnet\s+sales\b",
                    r"\bnet\s+revenue\b",
                    r"\bsum of (all\s+)?sales\b",
                    r"\bwhat is our total revenue\b",
                    r"\bwhat is the total revenue\b"
                ],
                "keywords": ["total revenue", "total sales", "overall sales", "net revenue", "how much"]
            }
        ]

    def interpret(self, raw_question: str) -> InterpretationResult:
        """Interprets the given user question into an approved intent with validated parameters."""
        if not raw_question or not raw_question.strip():
            return InterpretationResult(
                original_question="",
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                description="Empty Question",
                error_message="Question is empty. Please enter a natural-language business question.",
                suggested_questions=EXAMPLE_QUESTIONS[:5]
            )

        q = raw_question.strip()
        q_lower = q.lower()

        # Check for Month Comparison first (takes precedence if two months or comparison keywords exist)
        extracted_months = extract_months_from_query(q)
        is_comparison_keyword = any(k in q_lower for k in ["compare", "change between", "vs", "versus", "between two months", "from", "to"])

        if len(extracted_months) >= 2 or (is_comparison_keyword and len(extracted_months) >= 1) or "between two months" in q_lower:
            month_a = extracted_months[0] if len(extracted_months) >= 1 else "2026-01"
            month_b = extracted_months[1] if len(extracted_months) >= 2 else ("2026-02" if month_a != "2026-02" else "2026-03")
            return InterpretationResult(
                original_question=q,
                intent=IntentType.MONTH_COMPARISON,
                confidence=0.95,
                description="Month-to-Month Revenue Comparison",
                parameters={"month_a": month_a, "month_b": month_b},
                matched_rule="month_comparison_extractor",
                suggested_questions=[
                    "Compare January and February 2026",
                    "Compare 2026-04 to 2026-05"
                ]
            )

        # Evaluate pattern rules
        for rule in self.rules:
            # Check regex patterns
            for pattern in rule["patterns"]:
                if re.search(pattern, q_lower):
                    params = {}
                    if rule["intent"] == IntentType.MONTH_COMPARISON:
                        m_list = extract_months_from_query(q)
                        params = {
                            "month_a": m_list[0] if len(m_list) > 0 else "2026-01",
                            "month_b": m_list[1] if len(m_list) > 1 else "2026-02"
                        }

                    return InterpretationResult(
                        original_question=q,
                        intent=rule["intent"],
                        confidence=0.90,
                        description=rule["description"],
                        parameters=params,
                        matched_rule=pattern
                    )

        # Fallback keyword scoring
        scores: Dict[IntentType, int] = {}
        for rule in self.rules:
            intent = rule["intent"]
            score = sum(1 for kw in rule["keywords"] if kw in q_lower)
            if score > 0:
                scores[intent] = score

        if scores:
            best_intent = max(scores, key=scores.get)
            matched_rule_def = next(r for r in self.rules if r["intent"] == best_intent)
            params = {}
            if best_intent == IntentType.MONTH_COMPARISON:
                m_list = extract_months_from_query(q)
                params = {
                    "month_a": m_list[0] if len(m_list) > 0 else "2026-01",
                    "month_b": m_list[1] if len(m_list) > 1 else "2026-02"
                }

            return InterpretationResult(
                original_question=q,
                intent=best_intent,
                confidence=0.75,
                description=matched_rule_def["description"],
                parameters=params,
                matched_rule=f"keyword_match_score_{scores[best_intent]}"
            )

        # If completely unrecognized or ambiguous
        return InterpretationResult(
            original_question=q,
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            description="Unsupported or Ambiguous Question",
            error_message=(
                f"Could not reliably determine the intent for question: '{q}'. "
                "The assistant supports questions regarding total revenue, product performance, "
                "monthly trends, regional sales, and month-over-month comparisons."
            ),
            suggested_questions=[
                "What is the total revenue?",
                "Which product generated the highest revenue?",
                "What is the monthly revenue trend?",
                "Which region generated the highest sales?",
                "How did revenue change between two months?"
            ]
        )


# Singleton instance for application use
interpreter = SafeQuestionInterpreter()


def interpret_question(question: str) -> InterpretationResult:
    """Convenience functional wrapper for question interpretation."""
    return interpreter.interpret(question)
