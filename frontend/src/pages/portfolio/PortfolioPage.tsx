import { useMemo } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Card, CardHeader, CardTitle, CardContent, CardValue } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { PortfolioChart } from "../../components/charts/PortfolioChart";
import { PnLChart } from "../../components/charts/PnLChart";
import { PositionList } from "../../components/trading/PositionList";
import { usePortfolio } from "../../hooks/usePortfolio";
import { formatCurrency, formatPercent } from "../../lib/formatters";
import { generatePortfolioHistory } from "../../lib/mockData";
import { cn } from "../../lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899"];

export function PortfolioPage() {
  const { data: portfolio } = usePortfolio();
  const history = useMemo(() => generatePortfolioHistory(30), []);
  const totalValue = portfolio?.total_value_usdt ?? 45234.56;
  const unrealPnl = portfolio?.unrealized_pnl ?? 6341.87;
  const realPnl = portfolio?.realized_pnl ?? 8923.45;
  const dailyPnl = portfolio?.daily_pnl ?? 1247.34;

  const allocation = useMemo(() => {
    const positions = portfolio?.positions ?? [];
    const total = positions.reduce((s, p) => s + p.current_price * p.quantity, 0);
    return positions.map((p, i) => ({
      name: p.symbol.replace("/USDT", ""),
      value: Math.round((p.current_price * p.quantity / total) * 100),
      amount: p.current_price * p.quantity,
      color: COLORS[i % COLORS.length],
    }));
  }, [portfolio]);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold">Portfolio</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Overview of your holdings and performance.</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Value",      value: formatCurrency(totalValue),  positive: true  },
          { label: "Unrealized PnL",   value: formatCurrency(unrealPnl),  positive: unrealPnl >= 0  },
          { label: "Realized PnL",     value: formatCurrency(realPnl),    positive: realPnl >= 0    },
          { label: "Daily PnL",        value: formatCurrency(dailyPnl),   positive: dailyPnl >= 0  },
        ].map((s) => (
          <Card key={s.label}>
            <CardHeader><CardTitle>{s.label}</CardTitle></CardHeader>
            <CardContent>
              <CardValue className={cn(!s.positive && "text-bear")}>{s.value}</CardValue>
              {s.label !== "Total Value" && (
                <div className="flex items-center gap-1 mt-1">
                  {s.positive
                    ? <TrendingUp className="w-3 h-3 text-bull" />
                    : <TrendingDown className="w-3 h-3 text-bear" />
                  }
                  <span className={cn("text-xs", s.positive ? "text-bull" : "text-bear")}>
                    {formatPercent(((s.positive ? 1 : -1) * Math.random() * 5 + 1))}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="xl:col-span-2">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>Portfolio Value (30d)</CardTitle>
              <span className="text-xs text-bull num">
                {formatPercent(((history[history.length - 1]?.value - history[0]?.value) / history[0]?.value) * 100)}
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-52">
              <PortfolioChart data={history} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Allocation</CardTitle></CardHeader>
          <CardContent>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={allocation} cx="50%" cy="50%" innerRadius={40} outerRadius={64} dataKey="value" paddingAngle={2}>
                    {allocation.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v, n) => [`${v}%`, n]}
                    contentStyle={{ background: "hsl(222 47% 9%)", border: "1px solid hsl(222 47% 14%)", borderRadius: 8, fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-1.5 mt-2">
              {allocation.map((a, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: a.color }} />
                  <span className="flex-1 text-muted-foreground">{a.name}</span>
                  <span className="num">{a.value}%</span>
                  <span className="num text-muted-foreground">{formatCurrency(a.amount, true)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Daily PnL bar chart */}
      <Card>
        <CardHeader><CardTitle>Daily PnL (30d)</CardTitle></CardHeader>
        <CardContent>
          <div className="h-40">
            <PnLChart data={history} />
          </div>
        </CardContent>
      </Card>

      {/* Positions table */}
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
    </div>
  );
}
