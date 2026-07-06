import type { Portfolio, Order, OHLCVCandle } from "../types";

// ── Portfolio ─────────────────────────────────────────────────────────────────

export const mockPortfolio: Portfolio = {
  id: "port-1",
  name: "Main Portfolio",
  exchange: "binance",
  quote_currency: "USDT",
  total_value_usdt: 45_234.56,
  available_balance: 12_450.23,
  unrealized_pnl: 6_341.87,
  realized_pnl: 8_923.45,
  daily_pnl: 1_247.34,
  is_paper_trading: false,
  positions: [
    {
      id: "pos-1",
      symbol: "BTC/USDT",
      side: "long",
      quantity: 0.5,
      entry_price: 58_230,
      current_price: 67_450,
      leverage: 1,
      unrealized_pnl: 4_610,
      stop_loss: 55_000,
      take_profit: 75_000,
    },
    {
      id: "pos-2",
      symbol: "ETH/USDT",
      side: "long",
      quantity: 5,
      entry_price: 3_120,
      current_price: 3_456,
      leverage: 1,
      unrealized_pnl: 1_680,
      stop_loss: 2_800,
      take_profit: 4_000,
    },
    {
      id: "pos-3",
      symbol: "SOL/USDT",
      side: "short",
      quantity: 10,
      entry_price: 195,
      current_price: 188.5,
      leverage: 2,
      unrealized_pnl: 65,
      stop_loss: 210,
      take_profit: 170,
    },
  ],
};

// ── Orders ────────────────────────────────────────────────────────────────────

const now = Date.now();
const h = (n: number) => new Date(now - n * 3_600_000).toISOString();

export const mockOrders: Order[] = [
  { id: "ord-1", exchange_order_id: "BN-001", symbol: "BTC/USDT", side: "buy",  order_type: "market", status: "filled",    quantity: 0.5,  price: 58_230,  filled_quantity: 0.5,  fee: 14.56, agent_reasoning: "Strong breakout confirmed. RSI divergence + volume spike.", created_at: h(24), updated_at: h(23) },
  { id: "ord-2", exchange_order_id: "BN-002", symbol: "ETH/USDT", side: "buy",  order_type: "limit",  status: "filled",    quantity: 5,    price: 3_120,   filled_quantity: 5,    fee: 7.8,  agent_reasoning: "Accumulation zone. EMA golden cross on 4H.", created_at: h(18), updated_at: h(17) },
  { id: "ord-3", exchange_order_id: "BN-003", symbol: "SOL/USDT", side: "sell", order_type: "market", status: "filled",    quantity: 10,   price: 195,     filled_quantity: 10,   fee: 0.97, agent_reasoning: "Overbought. Risk agent triggered short at resistance.", created_at: h(12), updated_at: h(12) },
  { id: "ord-4", exchange_order_id: "BN-004", symbol: "BTC/USDT", side: "sell", order_type: "limit",  status: "open",      quantity: 0.25, price: 72_000,  filled_quantity: 0,    fee: 0,    agent_reasoning: "Take-profit level. Target based on Fibonacci extension.", created_at: h(6),  updated_at: h(6) },
  { id: "ord-5", exchange_order_id: "BN-005", symbol: "DOGE/USDT",side: "buy",  order_type: "limit",  status: "cancelled", quantity: 500,  price: 0.18,    filled_quantity: 0,    fee: 0,    agent_reasoning: "Speculative entry — cancelled on risk review.", created_at: h(8),  updated_at: h(7) },
  { id: "ord-6", exchange_order_id: "BN-006", symbol: "BNB/USDT", side: "buy",  order_type: "market", status: "filled",    quantity: 3,    price: 590,     filled_quantity: 3,    fee: 0.88, agent_reasoning: "Momentum trade. BNB strength vs BTC.", created_at: h(36), updated_at: h(36) },
  { id: "ord-7", exchange_order_id: "BN-007", symbol: "ETH/USDT", side: "sell", order_type: "limit",  status: "open",      quantity: 2,    price: 4_000,   filled_quantity: 0,    fee: 0,    agent_reasoning: "Partial take-profit at key resistance zone.", created_at: h(3),  updated_at: h(3) },
];

// ── Portfolio history (30d PnL) ───────────────────────────────────────────────

export interface PnLDataPoint { date: string; value: number; pnl: number }

export function generatePortfolioHistory(days = 30): PnLDataPoint[] {
  const data: PnLDataPoint[] = [];
  let value = 38_000;
  for (let i = days; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86_400_000);
    const change = (Math.random() - 0.42) * 1_200;
    value = Math.max(30_000, value + change);
    data.push({
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      value: Math.round(value * 100) / 100,
      pnl: Math.round(change * 100) / 100,
    });
  }
  return data;
}

// ── OHLCV candles ─────────────────────────────────────────────────────────────

export function generateOHLCV(symbol: string, count = 100): OHLCVCandle[] {
  const basePrice = symbol.startsWith("BTC") ? 67_450 : symbol.startsWith("ETH") ? 3_456 : 188;
  const candles: OHLCVCandle[] = [];
  let price = basePrice * 0.92;
  const intervalMs = 3_600_000;

  for (let i = count; i >= 0; i--) {
    const ts = Date.now() - i * intervalMs;
    const open = price;
    const change = (Math.random() - 0.47) * basePrice * 0.02;
    const close = Math.max(open * 0.97, open + change);
    const high = Math.max(open, close) * (1 + Math.random() * 0.008);
    const low = Math.min(open, close) * (1 - Math.random() * 0.008);
    const volume = basePrice * (50 + Math.random() * 200);
    candles.push({ timestamp: ts, open, high, low, close, volume });
    price = close;
  }
  return candles;
}

// ── Agent thoughts ────────────────────────────────────────────────────────────

export interface AgentThought {
  id: string;
  agent: string;
  type: "analysis" | "decision" | "warning" | "action" | "info";
  message: string;
  confidence?: number;
  timestamp: string;
}

export const mockAgentThoughts: AgentThought[] = [
  { id: "at-1", agent: "Technical Agent",  type: "analysis",  message: "BTC/USDT showing bullish divergence on RSI (4H). MACD histogram increasing. EMA 20 crossed above EMA 50. Volume profile supports continuation.", confidence: 82, timestamp: h(0.1) },
  { id: "at-2", agent: "Market Agent",     type: "info",      message: "Funding rate on BTC perpetuals: +0.0083%. Open interest increased 12% in last 4 hours. Spot premium positive — institutional demand.", confidence: 78, timestamp: h(0.2) },
  { id: "at-3", agent: "Risk Agent",       type: "warning",   message: "Portfolio exposure to BTC/USDT is 52.3% — approaching 55% cap. Recommend sizing down next BTC position or increasing hedge.", confidence: 95, timestamp: h(0.3) },
  { id: "at-4", agent: "Decision Agent",  type: "decision",  message: "Signal: STRONG_BUY on ETH/USDT. Target entry: $3,420–$3,440 range. Stop: $3,280. R:R = 1:2.8. Position size: 4% of portfolio.", confidence: 77, timestamp: h(0.4) },
  { id: "at-5", agent: "Execution Agent", type: "action",    message: "Placing limit order: ETH/USDT BUY 2.0 @ $3,435. Order ID: BN-008. Monitoring for fill...", confidence: undefined, timestamp: h(0.5) },
  { id: "at-6", agent: "Memory Agent",    type: "info",      message: "Pattern recognition: Similar setup occurred 2024-03-12. Previous result: +8.4% in 48h. Confidence adjusted +5%.", confidence: 70, timestamp: h(0.6) },
  { id: "at-7", agent: "News Agent",      type: "analysis",  message: "Positive macro: Fed minutes indicate pause in rate hikes. Bitcoin ETF inflows: $420M yesterday. Sentiment: bullish.", confidence: 68, timestamp: h(1) },
  { id: "at-8", agent: "Reflection Agent",type: "info",      message: "Last 5 trades: 4W 1L (80% win rate). Average R:R achieved: 1:2.4. Drawdown from peak: -3.2%. Strategy performing within parameters.", confidence: undefined, timestamp: h(2) },
];

// ── Live logs ─────────────────────────────────────────────────────────────────

export interface LogEntry {
  id: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
  component: string;
  message: string;
  timestamp: string;
}

export const mockLogs: LogEntry[] = [
  { id: "l-1",  level: "INFO",    component: "Exchange",        message: "WebSocket connected to Binance spot stream", timestamp: h(0.05) },
  { id: "l-2",  level: "INFO",    component: "MarketAgent",     message: "Fetching ticker data for BTC/USDT, ETH/USDT, SOL/USDT", timestamp: h(0.08) },
  { id: "l-3",  level: "DEBUG",   component: "TechAgent",       message: "Computing RSI(14): 62.4. MACD: bullish. BB: price near upper band", timestamp: h(0.1) },
  { id: "l-4",  level: "INFO",    component: "RiskAgent",       message: "Portfolio check passed. BTC exposure: 52.3%. Max allowed: 55%", timestamp: h(0.12) },
  { id: "l-5",  level: "WARNING", component: "RiskAgent",       message: "SOL position leverage at 2x — monitoring volatility", timestamp: h(0.15) },
  { id: "l-6",  level: "INFO",    component: "DecisionAgent",   message: "Generating signal for ETH/USDT based on 6 indicator confluence", timestamp: h(0.18) },
  { id: "l-7",  level: "INFO",    component: "ExecutionAgent",  message: "Order placed: ETH/USDT BUY LIMIT 2.0 @ 3435.00 [BN-008]", timestamp: h(0.2) },
  { id: "l-8",  level: "DEBUG",   component: "OrderRepository", message: "Order BN-008 persisted to database. Status: pending", timestamp: h(0.22) },
  { id: "l-9",  level: "INFO",    component: "Exchange",        message: "Order BN-008 acknowledged by exchange. Status: open", timestamp: h(0.25) },
  { id: "l-10", level: "ERROR",   component: "NewsAgent",       message: "CryptoPanic API rate limit exceeded. Retrying in 60s", timestamp: h(0.3) },
  { id: "l-11", level: "INFO",    component: "MemoryAgent",     message: "Retrieved 8 similar historical patterns. Highest match: 2024-03-12 (87%)", timestamp: h(0.35) },
  { id: "l-12", level: "INFO",    component: "GraphOrchestrator", message: "Cycle complete. Next execution in 15 minutes", timestamp: h(0.4) },
];

// ── Tickers ───────────────────────────────────────────────────────────────────

export const mockTickers: Record<string, { price: number; change: number; volume: number }> = {
  "BTC/USDT": { price: 67_450,  change: 2.84,  volume: 23_456_789 },
  "ETH/USDT": { price: 3_456,   change: 1.23,  volume: 12_345_678 },
  "SOL/USDT": { price: 188.5,   change: -1.45, volume: 4_567_890  },
  "BNB/USDT": { price: 592.4,   change: 0.87,  volume: 2_345_678  },
  "DOGE/USDT":{ price: 0.1823,  change: -2.31, volume: 1_234_567  },
};

// ── Current reasoning snapshot ────────────────────────────────────────────────

export const mockReasoning = {
  signal: "BUY" as const,
  confidence: 77,
  symbol: "ETH/USDT",
  timeframe: "4h",
  summary: "Multi-indicator confluence on ETH/USDT 4H. RSI recovering from oversold with bullish divergence. Price holding above key EMA support. Volume confirms buyer interest.",
  factors: [
    { label: "RSI Divergence",     value: "Bullish", weight: 25 },
    { label: "EMA Alignment",      value: "20 > 50 > 200", weight: 20 },
    { label: "Volume Profile",     value: "+34% above avg", weight: 20 },
    { label: "Funding Rate",       value: "+0.0083% (bullish)", weight: 15 },
    { label: "Market Sentiment",   value: "Greed (72/100)", weight: 10 },
    { label: "Historical Pattern", value: "87% match 2024-03", weight: 10 },
  ],
  risks: ["BTC dominance rising — altcoin rotation risk", "ETH approaching supply zone at $3,500"],
  action: "Place limit buy ETH/USDT @ $3,435 with 4% portfolio allocation",
};
