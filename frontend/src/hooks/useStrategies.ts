import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listStrategies, createStrategy, startStrategy, stopStrategy } from "../api/trading";
import type { Strategy } from "../types";

const mockStrategies: Strategy[] = [
  {
    id: "str-1",
    name: "BTC Momentum",
    description: "EMA crossover + RSI momentum on BTC/USDT",
    exchange: "binance",
    symbols: ["BTC/USDT"],
    timeframe: "4h",
    status: "active",
    max_position_size_pct: 5,
    stop_loss_pct: 2,
    take_profit_pct: 4,
    max_open_positions: 1,
    config: {},
    total_trades: 42,
    winning_trades: 28,
    win_rate: 66.7,
    total_pnl: 18.4,
    sharpe_ratio: 1.87,
  },
  {
    id: "str-2",
    name: "ETH/SOL Pair",
    description: "Multi-asset momentum with mean reversion",
    exchange: "bybit",
    symbols: ["ETH/USDT", "SOL/USDT"],
    timeframe: "1h",
    status: "paused",
    max_position_size_pct: 4,
    stop_loss_pct: 2.5,
    take_profit_pct: 5,
    max_open_positions: 2,
    config: {},
    total_trades: 18,
    winning_trades: 11,
    win_rate: 61.1,
    total_pnl: 7.2,
    sharpe_ratio: 1.34,
  },
];

export function useStrategies() {
  return useQuery<Strategy[]>({
    queryKey: ["strategies"],
    queryFn: async () => {
      try {
        return await listStrategies();
      } catch {
        return mockStrategies;
      }
    },
    staleTime: 60_000,
  });
}

export function useStartStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => startStrategy(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useStopStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => stopStrategy(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}
