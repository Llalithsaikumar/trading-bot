import { useQuery } from "@tanstack/react-query";
import { getTicker, getOHLCV, getOrderBook } from "../api/market";
import { mockTickers, generateOHLCV } from "../lib/mockData";
import { useTradingStore } from "../stores/tradingStore";

export function useTickerQuery(exchange: string, symbol: string) {
  return useQuery({
    queryKey: ["ticker", exchange, symbol],
    queryFn: async () => {
      try {
        return await getTicker(exchange, symbol);
      } catch {
        const t = mockTickers[symbol];
        return t ? { symbol, last: t.price, percentage: t.change, quoteVolume: t.volume } : null;
      }
    },
    refetchInterval: 5_000,
    staleTime: 3_000,
  });
}

export function useOHLCVQuery(exchange: string, symbol: string, timeframe = "1h", limit = 100) {
  return useQuery({
    queryKey: ["ohlcv", exchange, symbol, timeframe, limit],
    queryFn: async () => {
      try {
        return await getOHLCV(exchange, symbol, timeframe, limit);
      } catch {
        return generateOHLCV(symbol, limit);
      }
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

export function useOrderBookQuery(exchange: string, symbol: string) {
  const price = mockTickers[symbol]?.price ?? 0;
  return useQuery({
    queryKey: ["orderbook", exchange, symbol],
    queryFn: async () => {
      try {
        return await getOrderBook(exchange, symbol);
      } catch {
        return { symbol, midPrice: price };
      }
    },
    refetchInterval: 3_000,
    staleTime: 2_000,
  });
}

export function useMarketData() {
  const { selectedExchange, selectedSymbol, selectedTimeframe } = useTradingStore();
  const ticker = useTickerQuery(selectedExchange, selectedSymbol);
  const ohlcv = useOHLCVQuery(selectedExchange, selectedSymbol, selectedTimeframe);
  return { ticker, ohlcv, symbol: selectedSymbol, exchange: selectedExchange };
}
