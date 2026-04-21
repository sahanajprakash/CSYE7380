import { mockPriceDataBySymbol, mockFundamentals } from "../data/mockStockData";

export async function sendMessage(question) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchPortfolioPrices() {
  const res = await fetch("/api/portfolio/prices");
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchInvestmentActivity() {
  const res = await fetch("/api/portfolio/activity");
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getStockFundamentals(symbol) {
  const res = await fetch(`/api/stock/fundamentals/${symbol}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getStockPrices(symbol, period = "6mo") {
  const res = await fetch(`/api/stock/prices/${symbol}?period=${period}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getBacktestBuffettTake(payload) {
  const res = await fetch("/api/backtest/buffett-take", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function runBacktest(symbol, strategy, params = {}) {
  const res = await fetch("/api/backtest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, strategy, ...params }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
