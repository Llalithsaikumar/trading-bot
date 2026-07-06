import { apiClient } from "./client";
import type { OHLCVCandle, Ticker } from "@/types";

export const marketApi = {
  getTicker: (exchange: string, symbol: string) =>
    apiClient.get<Ticker>(`/market/ticker/${exchange}/${symbol}`).then((r) => r.data),

  getOHLCV: (exchange: string, symbol: string, timeframe = "1h", limit = 100) =>
    apiClient
      .get<OHLCVCandle[]>(`/market/ohlcv/${exchange}/${symbol}`, { params: { timeframe, limit } })
      .then((r) => r.data),

  getOrderBook: (exchange: string, symbol: string, depth = 20) =>
    apiClient
      .get(`/market/orderbook/${exchange}/${symbol}`, { params: { depth } })
      .then((r) => r.data),

  getMarketSummary: (exchange = "binance", symbols = ["BTC/USDT", "ETH/USDT"]) =>
    apiClient
      .get("/market/summary", { params: { exchange, symbols } })
      .then((r) => r.data),
};

// Named exports for hook imports
export const getTicker = marketApi.getTicker;
export const getOHLCV = marketApi.getOHLCV;
export const getOrderBook = marketApi.getOrderBook;
export const getMarketSummary = marketApi.getMarketSummary;
