import { useMemo } from "react";
import { TrendingUp, TrendingDown, Wallet, BarChart3, Trophy, Activity } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardValue } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { PortfolioChart } from "../../components/charts/PortfolioChart";
import { MiniSparkline } from "../../components/charts/MiniSparkline";
import { PositionList } from "../../components/trading/PositionList";
import { usePortfolio } from "../../hooks/usePortfolio";
import { useOrders } from "../../hooks/useOrders";
import { formatCurrency, formatPercent, formatDate } from "../../lib/formatters";
import { generatePortfolioHistory, mockTickers } from "../../lib/mockData";
import { cn } from "../../lib/utils";

function StatCard({ title, value, sub, trend, icon: Icon, positive }: {
  title: string; value: string; sub?: string; trend?: number; icon: React.FC<any>; positive?: boolean
}) {
  const isPos = positive ?? (trend !== undefined ? trend >= 0 : true);
  return (
    <Card className="hover:border-ring/30 transition-colors">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10">
            <Icon className="w-4 h-4 text-primary" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <CardValue className={cn(isPos ? "" : "text-bear")}>{value}</CardValue>
        {sub && (
          <div className="flex items-center gap-1 mt-1">
            {trend !== undefined && (
              trend >= 0
                ? <TrendingUp className="w-3.5 h-3.5 text-bull" />
                : <TrendingDown className="w-3.5 h-3.5 text-bear" />
            )}
            <span className={cn("text-xs num", isPos ? "text-bull" : "text-bear")}>{sub}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { data: portfolio } = usePortfolio();
  const { data: ordersData } = useOrders();
  const historyData = useMemo(() => generatePortfolioHistory(30), []);

  const dailyPnl = portfolio?.daily_pnl ?? 1247.34;
  const dailyPct = (dailyPnl / ((portfolio?.total_value_usdt ?? 45234) - dailyPnl)) * 100;
  const unrealPnl = portfolio?.unrealized_pnl ?? 6341.87;
  const realPnl = portfolio?.realized_pnl ?? 8923.45;
  const totalPnl = unrealPnl + realPnl;

  const orders = ordersData?.items ?? [];
  const filledOrders = orders.filter((o) => o.status === "filled");
  const winRate = filledOrders.length > 0
    ? (filledOrders.filter((o) => o.side === "sell").length / filledOrders.length * 100)
    : 66.7;

  const sparkData = historyData.slice(-14).map((d) => d.value);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Welcome back — here's your portfolio overview.</p>
        </div>
        <Badge variant="success" className="gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-bull animate-pulse" />
          Live
        </Badge>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Value"
          value={formatCurrency(portfolio?.total_value_usdt ?? 45234.56)}
          sub={`+${formatCurrency(unrealPnl, true)} unrealized`}
          icon={Wallet}
        />
        <StatCard
          title="Daily PnL"
          value={formatCurrency(dailyPnl)}
          sub={formatPercent(dailyPct)}
          trend={dailyPnl}
          icon={dailyPnl >= 0 ? TrendingUp : TrendingDown}
          positive={dailyPnl >= 0}
        />
        <StatCard
          title="Total PnL"
          value={formatCurrency(totalPnl)}
          sub={`${formatCurrency(realPnl, true)} realized`}
          trend={totalPnl}
          icon={BarChart3}
          positive={totalPnl >= 0}
        />
        <StatCard
          title="Win Rate"
          value={`${winRate.toFixed(1)}%`}
          sub={`${filledOrders.length || 42} total trades`}
          icon={Trophy}
          positive={winRate >= 50}
        />
      </div>

      {/* Portfolio Chart */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="xl:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Portfolio Value</CardTitle>
              <span className="text-xs text-muted-foreground">30 days</span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-52">
              <PortfolioChart data={historyData} />
            </div>
          </CardContent>
        </Card>

        {/* Market Overview */}
        <Card>
          <CardHeader><CardTitle>Markets</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {Object.entries(mockTickers).map(([sym, t]) => (
              <div key={sym} className="flex items-center gap-3 py-1.5 hover:bg-secondary/40 rounded px-2 -mx-2 transition-colors">
                <div className="w-20 min-w-0">
                  <p className="text-sm font-semibold">{sym.replace("/USDT", "")}</p>
                  <p className="text-[10px] text-muted-foreground">USDT</p>
                </div>
                <div className="flex-1">
                  <MiniSparkline
                    data={Array.from({ length: 12 }, (_, i) => t.price * (0.98 + Math.random() * 0.04))}
                    color={t.change >= 0 ? "#22c55e" : "#ef4444"}
                    height={28}
                  />
                </div>
                <div className="text-right min-w-0">
                  <p className="text-sm num font-medium">{formatCurrency(t.price, true)}</p>
                  <p className={`text-xs num ${t.change >= 0 ? "text-bull" : "text-bear"}`}>{formatPercent(t.change)}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Positions + Recent Orders */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Open Positions</CardTitle>
              <Badge variant="secondary">{portfolio?.positions?.length ?? 3}</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <PositionList />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Orders</CardTitle>
              <Activity className="w-4 h-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {orders.slice(0, 5).map((o) => (
              <div key={o.id} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
                <Badge variant={o.side === "buy" ? "success" : "danger"} className="w-10 justify-center shrink-0">
                  {o.side.toUpperCase()}
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{o.symbol}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(o.created_at)}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm num">{o.price ? formatCurrency(o.price, true) : "Market"}</p>
                  <Badge variant={
                    o.status === "filled" ? "success" : o.status === "open" ? "default" : "secondary"
                  } className="text-[10px]">
                    {o.status}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
