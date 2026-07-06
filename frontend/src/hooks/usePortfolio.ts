import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listPortfolios, getPortfolio, createPortfolio } from "../api/trading";
import { mockPortfolio } from "../lib/mockData";

export function usePortfolioList() {
  return useQuery({
    queryKey: ["portfolios"],
    queryFn: async () => {
      try {
        return await listPortfolios();
      } catch {
        return { items: [mockPortfolio], total: 1, page: 1, page_size: 20 };
      }
    },
    staleTime: 30_000,
  });
}

export function usePortfolio(id?: string) {
  return useQuery({
    queryKey: ["portfolio", id],
    queryFn: async () => {
      if (!id) return mockPortfolio;
      try {
        return await getPortfolio(id);
      } catch {
        return mockPortfolio;
      }
    },
    enabled: true,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useCreatePortfolio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createPortfolio,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolios"] }),
  });
}
