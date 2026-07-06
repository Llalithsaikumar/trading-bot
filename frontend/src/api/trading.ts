import { apiClient } from "./client";
import type { Order, OrderCreate, PaginatedResponse, Portfolio, Strategy } from "@/types";

export const tradingApi = {
  // Portfolios
  listPortfolios: () =>
    apiClient.get<PaginatedResponse<Portfolio>>("/portfolios").then((r) => r.data),

  getPortfolio: (id: string) =>
    apiClient.get<Portfolio>(`/portfolios/${id}`).then((r) => r.data),

  createPortfolio: (data: { name: string; exchange: string; is_paper_trading?: boolean }) =>
    apiClient.post<Portfolio>("/portfolios", data).then((r) => r.data),

  // Orders
  listOrders: (params?: { portfolio_id?: string; status?: string; symbol?: string; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<Order>>("/orders", { params }).then((r) => r.data),

  placeOrder: (data: OrderCreate) =>
    apiClient.post<Order>("/orders", data).then((r) => r.data),

  cancelOrder: (id: string) =>
    apiClient.delete<void>(`/orders/${id}`).then((r) => r.data),

  // Strategies
  listStrategies: () =>
    apiClient.get<Strategy[]>("/strategies").then((r) => r.data),

  createStrategy: (data: Partial<Strategy>) =>
    apiClient.post<Strategy>("/strategies", data).then((r) => r.data),

  startStrategy: (id: string) =>
    apiClient.post(`/strategies/${id}/execute`).then((r) => r.data),

  stopStrategy: (id: string) =>
    apiClient.put(`/strategies/${id}`, { status: "paused" }).then((r) => r.data),
};

// Named exports for hook imports
export const listPortfolios = tradingApi.listPortfolios;
export const getPortfolio = tradingApi.getPortfolio;
export const createPortfolio = tradingApi.createPortfolio;
export const listOrders = tradingApi.listOrders;
export const placeOrder = tradingApi.placeOrder;
export const cancelOrder = tradingApi.cancelOrder;
export const listStrategies = tradingApi.listStrategies;
export const createStrategy = tradingApi.createStrategy;
export const startStrategy = tradingApi.startStrategy;
export const stopStrategy = tradingApi.stopStrategy;
