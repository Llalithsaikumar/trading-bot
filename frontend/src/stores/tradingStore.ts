/**
 * Trading UI state — selected symbol, exchange, real-time ticks.
 */
import { create } from "zustand";
import type { Ticker } from "@/types";

interface TradingState {
  selectedExchange: string;
  selectedSymbol: string;
  selectedTimeframe: string;
  tickers: Record<string, Ticker>;

  setExchange: (exchange: string) => void;
  setSymbol: (symbol: string) => void;
  setTimeframe: (tf: string) => void;
  updateTicker: (symbol: string, ticker: Ticker) => void;
}

export const useTradingStore = create<TradingState>((set) => ({
  selectedExchange: "binance",
  selectedSymbol: "BTC/USDT",
  selectedTimeframe: "1h",
  tickers: {},

  setExchange: (selectedExchange) => set({ selectedExchange }),
  setSymbol: (selectedSymbol) => set({ selectedSymbol }),
  setTimeframe: (selectedTimeframe) => set({ selectedTimeframe }),
  updateTicker: (symbol, ticker) =>
    set((state) => ({ tickers: { ...state.tickers, [symbol]: ticker } })),
}));
