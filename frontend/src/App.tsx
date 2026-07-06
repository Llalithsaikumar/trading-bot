import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthLayout } from "./components/layout/AuthLayout";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import { LoginPage } from "./pages/auth/LoginPage";
import { RegisterPage } from "./pages/auth/RegisterPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { TradingPage } from "./pages/trading/TradingPage";
import { PortfolioPage } from "./pages/portfolio/PortfolioPage";
import { SettingsPage } from "./pages/settings/SettingsPage";
import { AgentPage } from "./pages/agent/AgentPage";
import { HistoryPage } from "./pages/history/HistoryPage";
import { useAuthStore } from "./stores/authStore";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  // During development allow access without login
  if (!isAuthenticated) return <>{children}</>;
  return <>{children}</>;
}

export default function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "hsl(222 47% 9%)",
            color: "hsl(213 31% 91%)",
            border: "1px solid hsl(222 47% 14%)",
            fontSize: "14px",
          },
        }}
      />
      <Routes>
        {/* Public auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Protected app routes */}
        <Route
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/trading" element={<TradingPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </>
  );
}
