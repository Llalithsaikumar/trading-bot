import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, TrendingUp, Wallet, Bot, History, Settings, Zap, ChevronRight,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useAuthStore } from "../../stores/authStore";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/trading",   icon: TrendingUp,      label: "Trading"   },
  { to: "/portfolio", icon: Wallet,           label: "Portfolio" },
  { to: "/agent",     icon: Bot,             label: "Agent AI"  },
  { to: "/history",   icon: History,          label: "History"   },
];

export function Sidebar() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <aside className="flex flex-col w-60 shrink-0 h-full border-r border-border bg-card">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-14 border-b border-border">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/20">
          <Zap className="w-4 h-4 text-primary" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight">MiroFish</p>
          <p className="text-[10px] text-muted-foreground">AI Trading</p>
        </div>
      </div>

      {/* Live indicator */}
      <div className="mx-4 mt-3 mb-1 flex items-center gap-2 rounded-md bg-bull/10 border border-bull/20 px-3 py-1.5">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-bull opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-bull" />
        </span>
        <span className="text-xs text-bull font-medium">Agent Running</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
        <p className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mt-2">
          Platform
        </p>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={cn("w-4 h-4 shrink-0", isActive ? "text-primary" : "")} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight className="w-3 h-3 opacity-60" />}
              </>
            )}
          </NavLink>
        ))}

        <p className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mt-4">
          Account
        </p>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            )
          }
        >
          <Settings className="w-4 h-4 shrink-0" />
          <span>Settings</span>
        </NavLink>
      </nav>

      {/* User footer */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-3 rounded-md px-2 py-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/20 text-primary text-xs font-bold uppercase shrink-0">
            {user?.username?.[0] ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.username ?? "Trader"}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email ?? ""}</p>
          </div>
          <button
            onClick={logout}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors p-1 rounded"
            title="Log out"
          >
            ↪
          </button>
        </div>
      </div>
    </aside>
  );
}
