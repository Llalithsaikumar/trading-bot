import { apiClient } from "./client";
import type { LoginRequest, LoginResponse, TokenResponse } from "@/types";

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>("/auth/login", data).then((r) => r.data),

  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    apiClient.post("/auth/register", data).then((r) => r.data),

  refresh: (refreshToken: string) =>
    apiClient
      .post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken })
      .then((r) => r.data),

  logout: () => apiClient.post("/auth/logout"),
};
