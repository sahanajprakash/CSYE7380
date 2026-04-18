"""Warren Buffett financial ratio analysis using yfinance."""

from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf
from typing import Optional


RATIO_DEFINITIONS: dict[str, dict] = {
    "Gross Margin": {
        "threshold": 0.40, "direction": "above", "rule": "≥ 40%",
        "logic": "Signals the company isn't competing on price.",
        "format": "pct", "group": "Income Statement",
    },
    "SG&A Expense Margin": {
        "threshold": 0.30, "direction": "below", "rule": "≤ 30%",
        "logic": "Wide-moat companies don't need to spend a lot on overhead to operate.",
        "format": "pct", "group": "Income Statement",
    },
    "R&D Expense Margin": {
        "threshold": 0.30, "direction": "below", "rule": "≤ 30%",
        "logic": "R&D expenses don't always create value for shareholders.",
        "format": "pct", "group": "Income Statement",
    },
    "Depreciation Margin": {
        "threshold": 0.10, "direction": "below", "rule": "≤ 10%",
        "logic": "Buffett doesn't like businesses that need depreciating assets to maintain their competitive advantage.",
        "format": "pct", "group": "Income Statement",
    },
    "Interest Expense Margin": {
        "threshold": 0.15, "direction": "below", "rule": "≤ 15%",
        "logic": "Great businesses don't need debt to finance themselves.",
        "format": "pct", "group": "Income Statement",
    },
    "Income Tax Rate": {
        "threshold": None, "direction": "info", "rule": "≈ 21% (Corp Rate)",
        "logic": "Great businesses are so profitable that they pay their full tax load.",
        "format": "pct", "group": "Income Statement",
    },
    "Net Profit Margin": {
        "threshold": 0.20, "direction": "above", "rule": "≥ 20%",
        "logic": "Great companies convert 20% or more of their revenue into net income.",
        "format": "pct", "group": "Income Statement",
    },
    "EPS Growth": {
        "threshold": 1.0, "direction": "above", "rule": "> 1.0x (growing YoY)",
        "logic": "Great companies increase profits every year.",
        "format": "ratio", "group": "Income Statement",
    },
    "Cash > Debt Ratio": {
        "threshold": 1.0, "direction": "above", "rule": "> 1.0x",
        "logic": "Great companies generate lots of cash without needing much debt.",
        "format": "ratio", "group": "Balance Sheet",
    },
    "Adjusted Debt to Equity": {
        "threshold": 0.80, "direction": "below", "rule": "< 0.80x",
        "logic": "Great companies finance themselves with equity.",
        "format": "ratio", "group": "Balance Sheet",
    },
    "CapEx Margin": {
        "threshold": 0.25, "direction": "below", "rule": "< 25%",
        "logic": "Great companies don't need much equipment to generate profits.",
        "format": "pct", "group": "Cash Flow",
    },
}


def passes_rule(ratio_name: str, value: float) -> Optional[bool]:
    """True = pass, False = fail, None = informational only."""
    defn = RATIO_DEFINITIONS.get(ratio_name)
    if defn is None or defn["direction"] == "info" or pd.isna(value):
        return None
    return value >= defn["threshold"] if defn["direction"] == "above" else value <= defn["threshold"]


def fmt(ratio_name: str, value: float) -> str:
    if pd.isna(value):
        return "N/A"
    defn = RATIO_DEFINITIONS.get(ratio_name, {})
    return f"{value:.1%}" if defn.get("format") == "pct" else f"{value:.2f}x"


def _get_row(df: pd.DataFrame, *names: str) -> Optional[pd.Series]:
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def compute_ratios(symbol: str) -> dict:
    """Fetch yfinance data and compute all Buffett financial ratios."""
    ticker = yf.Ticker(symbol.upper().strip())
    fin = ticker.financials
    bs = ticker.balancesheet
    cf = ticker.cashflow

    if fin is None or fin.empty:
        raise ValueError(f"No financial data for {symbol.upper()!r}. Check the ticker symbol.")

    ratios: dict[str, Optional[pd.Series]] = {}

    # Income Statement
    gross_profit  = _get_row(fin, "Gross Profit")
    total_revenue = _get_row(fin, "Total Revenue")
    sga           = _get_row(fin, "Selling General And Administration", "Selling General Administrative")
    rnd           = _get_row(fin, "Research And Development")
    depr          = _get_row(fin, "Reconciled Depreciation", "Depreciation And Amortization In Income Statement")
    interest_exp  = _get_row(fin, "Interest Expense", "Interest Expense Non Operating")
    operating_inc = _get_row(fin, "Operating Income")
    tax_prov      = _get_row(fin, "Tax Provision")
    pretax_inc    = _get_row(fin, "Pretax Income")
    net_income    = _get_row(fin, "Net Income")
    basic_eps     = _get_row(fin, "Basic EPS")

    if gross_profit is not None and total_revenue is not None:
        ratios["Gross Margin"] = gross_profit / total_revenue

    if sga is not None and gross_profit is not None:
        ratios["SG&A Expense Margin"] = sga / gross_profit

    if rnd is not None and gross_profit is not None:
        ratios["R&D Expense Margin"] = rnd / gross_profit

    if depr is not None and gross_profit is not None:
        ratios["Depreciation Margin"] = depr / gross_profit

    if interest_exp is not None and operating_inc is not None:
        ratios["Interest Expense Margin"] = interest_exp / operating_inc

    if tax_prov is not None and pretax_inc is not None:
        ratios["Income Tax Rate"] = tax_prov / pretax_inc

    if net_income is not None and total_revenue is not None:
        ratios["Net Profit Margin"] = net_income / total_revenue

    if basic_eps is not None and len(basic_eps) >= 2:
        vals = []
        for i in range(len(basic_eps)):
            if i < len(basic_eps) - 1 and basic_eps.iloc[i + 1] != 0:
                vals.append(basic_eps.iloc[i] / basic_eps.iloc[i + 1])
            else:
                vals.append(np.nan)
        ratios["EPS Growth"] = pd.Series(vals, index=basic_eps.index)

    # Balance Sheet
    cash         = _get_row(bs, "Cash And Cash Equivalents", "Cash Equivalents")
    current_debt = _get_row(bs, "Current Debt", "Short Long Term Debt", "Current Debt And Capital Lease Obligation")
    total_debt   = _get_row(bs, "Total Debt")
    total_assets = _get_row(bs, "Total Assets")

    if cash is not None and current_debt is not None:
        ratios["Cash > Debt Ratio"] = cash / current_debt.replace(0, np.nan)

    if total_debt is not None and total_assets is not None:
        denom = (total_assets - total_debt).replace(0, np.nan)
        ratios["Adjusted Debt to Equity"] = total_debt / denom

    # Cash Flow
    capex      = _get_row(cf, "Capital Expenditure", "Capital Expenditures", "Purchase Of Property Plant And Equipment")
    net_inc_cf = _get_row(cf, "Net Income From Continuing Operations", "Net Income")

    if capex is not None and net_inc_cf is not None:
        ratios["CapEx Margin"] = -capex / net_inc_cf.replace(0, np.nan)

    return {
        "symbol": symbol.upper().strip(),
        "ratios": ratios,
        "financials": fin,
        "balance_sheet": bs,
        "cashflow": cf,
        "info": ticker.info,
    }
