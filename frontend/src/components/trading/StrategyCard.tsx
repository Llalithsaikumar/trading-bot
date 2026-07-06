import { Play, Pause, TrendingUp, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { formatPercent } from "../../lib/formatters";
import type { Strategy } from "../../types";
import toast from "react-hot-toast";

interface Props { strategy: Strategy }

export function StrategyCard({ strategy }: Props) {
  const isActive = strategy.status === "active";

  const toggle = () => {
    toast.success(isActive ? `Paused ${strategy.name}` : `Started ${strategy.name}`);
  };

  return (
    <Card className="hover:border-ring/50 transition-colors">
      <CardHeader className="flex-row items-start justify-between gap-2">
        <div>
          <CardTitle>{strategy.name}</CardTitle>
          <p className="text-sm font-medium mt-0.5">{strategy.name}</p>
        </div>
        <Badge
          variant={
            strategy.status === "active" ? "success"
            : strategy.status === "error" ? "danger"
            : "secondary"
          }
        >
          {strategy.status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-1">
          {strategy.symbols.map((s) => <Badge key={s} variant="outline">{s}</Badge>)}
          <Badge variant="outline">{strategy.timeframe}</Badge>
        </div>
        {strategy.total_trades !== undefined && (
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center">
              <p className="text-muted-foreground">Trades</p>
              <p className="font-semibold num">{strategy.total_trades}</p>
            </div>
            <div className="text-center">
              <p className="text-muted-foreground">Win Rate</p>
              <p className="font-semibold num text-bull">{formatPercent(strategy.win_rate ?? 0)}</p>
            </div>
            <div className="text-center">
              <p className="text-muted-foreground">Total PnL</p>
              <p className={`font-semibold num ${(strategy.total_pnl ?? 0) >= 0 ? "text-bull" : "text-bear"}`}>
                {formatPercent(strategy.total_pnl ?? 0)}
              </p>
            </div>
          </div>
        )}
        <Button size="sm" variant={isActive ? "outline" : "default"} onClick={toggle} className="w-full gap-2">
          {isActive ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {isActive ? "Pause Strategy" : "Start Strategy"}
        </Button>
      </CardContent>
    </Card>
  );
}
