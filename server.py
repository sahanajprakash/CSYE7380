"""
server.py -- FastAPI wrapper around the existing RAG pipeline.

Run with:  uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Buffett RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str


PORTFOLIO_TICKERS = ["AAPL", "BAC", "AXP", "KO", "CVX", "OXY", "KHC", "MCO", "DVA", "VRSN"]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/portfolio/prices")
def portfolio_prices():
    """Fetch live prices for all portfolio holdings from Yahoo Finance."""
    import yfinance as yf

    tickers = yf.Tickers(" ".join(PORTFOLIO_TICKERS))
    prices = {}
    for symbol in PORTFOLIO_TICKERS:
        try:
            info = tickers.tickers[symbol].info
            prices[symbol] = {
                "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
                "change24h": info.get("regularMarketChangePercent"),
            }
        except Exception:
            prices[symbol] = None
    return prices


@app.get("/api/portfolio/activity")
def portfolio_activity():
    """Fetch latest investment activity from SEC 13F filings."""
    from sec_filings import fetch_investment_activity

    result = fetch_investment_activity()
    if result is None:
        return {"error": "Could not fetch filing data"}
    return result


@app.post("/api/chat")
def chat(req: QuestionRequest):
    from rag_chain import ask

    return ask(req.question)


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str
    startDate: str = "2018-01-01"
    endDate: str | None = None
    shortWindow: int = 20
    longWindow: int = 50


@app.post("/api/backtest")
def backtest(req: BacktestRequest):
    from trading_backtest import run_moving_average_crossover, run_rsi_strategy

    symbol = req.symbol.strip().upper()

    if req.strategy == "ma_crossover":
        result = run_moving_average_crossover(symbol, short_window=req.shortWindow, long_window=req.longWindow, start=req.startDate, end=req.endDate)
    elif req.strategy == "rsi":
        result = run_rsi_strategy(symbol, rsi_period=14, oversold=30, overbought=70, start=req.startDate, end=req.endDate)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}")

    df = result.data
    equity_curve = [
        {
            "date": df.index[i].strftime("%Y-%m-%d"),
            "equity": round(float(df["Equity_Curve"].iloc[i]), 4),
            "drawdown": round(float(df["Drawdown"].iloc[i]), 4),
        }
        for i in range(0, len(df), 5)
    ]

    trades = [
        {
            "id": i + 1,
            "type": "LONG",
            "entryDate": row["Entry_Date"].strftime("%Y-%m-%d"),
            "exitDate": row["Exit_Date"].strftime("%Y-%m-%d"),
            "entryPrice": round(float(row["Entry_Price"]), 2),
            "exitPrice": round(float(row["Exit_Price"]), 2),
            "pnl": round(float(row["PnL"]), 4),
            "shares": 100,
        }
        for i, row in result.trades.iterrows()
    ]

    return {
        "result": {
            "symbol": result.symbol,
            "strategyName": result.strategy_name,
            "totalReturn": round(result.total_return, 4),
            "annualizedReturn": round(result.annualized_return, 4),
            "sharpeRatio": round(result.sharpe_ratio, 4),
            "maxDrawdown": round(result.max_drawdown, 4),
            "winRate": round(result.win_rate, 4),
            "numTrades": result.num_trades,
            "startDate": df.index[0].strftime("%Y-%m-%d"),
            "endDate": df.index[-1].strftime("%Y-%m-%d"),
        },
        "equityCurve": equity_curve,
        "trades": trades,
    }
