import { useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { TradeHistory } from "../../components/trading/TradeHistory";
import { PnLChart } from "../../components/charts/PnLChart";
import { useOrders } from "../../hooks/useOrders";
import { formatCurrency } from "../../lib/formatters";
import { generatePortfolioHistory, mockOrders } from "../../lib/mockData";
import { TrendingUp, Trophy, BarChart3, Activity } from "lucide-react";

export function HistoryPage() {
  const pnlData = useMemo(() => generatePortfolioHistory(30), []);
  const orders = mockOrders;
  const filled = orders.filter((o) => o.status === "filled");
  const wins = filled.filter((o) => o.side === "sell").length;
  const totalFees = filled.reduce((s, o) => s + (o.fee ?? 0), 0);
  const winRate = filled.length > 0 ? (wins / filled.length) * 100 : 0;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold">Trade History</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Full record of all executed and pending orders.</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Trades",   value: String(orders.length),           icon: Activity   },
          { label: "Filled",         value: String(filled.length),           icon: TrendingUp },
          { label: "Win Rate",       value: `${winRate.toFixed(1)}%`,        icon: Trophy     },
          { label: "Total Fees",     value: formatCurrency(totalFees),       icon: BarChart3  },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{s.label}</p>
                <s.icon className="w-4 h-4 text-primary/50" />
              </div>
              <p className="text-2xl font-bold num">{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* PnL chart */}
      <Card>
        <CardHeader><CardTitle>Daily PnL</CardTitle></CardHeader>
        <CardContent>
          <div className="h-36">
            <PnLChart data={pnlData} />
          </div>
        </CardContent>
      </Card>

      {/* Full history */}
      <Card>
        <CardHeader><CardTitle>All Orders</CardTitle></CardHeader>
        <CardContent>
          <TradeHistory />
        </CardContent>
      </Card>
    </div>
  );
}
