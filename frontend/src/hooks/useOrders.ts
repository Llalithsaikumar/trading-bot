import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listOrders, placeOrder, cancelOrder } from "../api/trading";
import { mockOrders } from "../lib/mockData";

export function useOrders(params?: { portfolio_id?: string; status?: string; symbol?: string }) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: async () => {
      try {
        return await listOrders(params ?? {});
      } catch {
        const filtered = params?.status && params.status !== "all"
          ? mockOrders.filter((o) => o.status === params.status)
          : params?.symbol
          ? mockOrders.filter((o) => o.symbol === params.symbol)
          : mockOrders;
        return { items: filtered, total: filtered.length, page: 1, page_size: 50 };
      }
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function usePlaceOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: placeOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}

export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: string }) => cancelOrder(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });
}
