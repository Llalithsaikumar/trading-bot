/**
 * Shared TypeScript types mirroring the backend Pydantic schemas.
 * Numeric fields use `number` for frontend convenience; API responses
 * with string decimals are coerced at the API layer.
 */

// ─── Auth ──────────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  tokens: TokenResponse;
  user: User;
}

// ─── User ──────────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: "admin" | "trader" | "viewer";
  status: "active" | "inactive" | "suspended" | "pending_verification";
  is_active: boolean;
  is_email_verified: boolean;
  two_fa_enabled: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Portfolio ─────────────────────────────────────────────────────────────────
export interface Portfolio {
  id: string;
  name: string;
  exchange: string;
  quote_currency: string;
  total_value_usdt: number;
  available_balance: number;
  unrealized_pnl: number;
  realized_pnl: number;
  daily_pnl: number;
  is_paper_trading: boolean;
  positions: Position[];
  created_at?: string;
  updated_at?: string;
}

export interface Position {
  id: string;
  symbol: string;
  side: "long" | "short" | "both";
  quantity: number;
  entry_price: number;
  current_price: number;
  leverage: number;
  unrealized_pnl: number;
  stop_loss: number | null;
  take_profit: number | null;
}

// ─── Orders ───────────────────────────────────────────────────────────────────
export type OrderSide = "buy" | "sell";
export type OrderType =
  | "market"
  | "limit"
  | "stop_loss"
  | "stop_loss_limit"
  | "take_profit"
  | "trailing_stop";
export type OrderStatus =
  | "pending"
  | "open"
  | "partially_filled"
  | "filled"
  | "cancelled"
  | "rejected"
  | "expired";

export interface Order {
  id: string;
  exchange_order_id: string | null;
  symbol: string;
  exchange?: string;
  side: OrderSide;
  order_type: OrderType;
  status: OrderStatus;
  quantity: number;
  price: number | null;
  filled_quantity: number;
  average_fill_price?: number | null;
  fee: number;
  agent_reasoning: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderCreate {
  portfolio_id: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: number;
  price?: number;
  stop_price?: number;
  time_in_force?: "GTC" | "IOC" | "FOK";
  reduce_only?: boolean;
}

// ─── Strategy ─────────────────────────────────────────────────────────────────
export type StrategyStatus = "active" | "paused" | "stopped" | "error";

export interface Strategy {
  id: string;
  name: string;
  description: string | null;
  exchange: string;
  symbols: string[];
  timeframe: string;
  status: StrategyStatus;
  max_position_size_pct: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  max_open_positions: number;
  config: Record<string, unknown>;
  total_trades?: number;
  winning_trades?: number;
  win_rate?: number;
  total_pnl?: number;
  sharpe_ratio?: number | null;
  created_at?: string;
  updated_at?: string;
}

// ─── Market Data ───────────────────────────────────────────────────────────────
export interface Ticker {
  exchange: string;
  symbol: string;
  timestamp: string;
  bid: number;
  ask: number;
  last: number;
  volume_24h: number;
  change_24h_pct: number | null;
  high_24h: number | null;
  low_24h: number | null;
  funding_rate: number | null;
}

export interface OHLCVCandle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// ─── Pagination ────────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages?: number;
}

// ─── WebSocket messages ────────────────────────────────────────────────────────
export interface WSMessage<T = unknown> {
  type: string;
  channel: string;
  payload: T;
  timestamp: string;
}
