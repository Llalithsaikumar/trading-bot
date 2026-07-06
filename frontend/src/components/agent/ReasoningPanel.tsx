import { TrendingUp, TrendingDown, Minus, AlertTriangle, Target } from "lucide-react";
import { mockReasoning } from "../../lib/mockData";
import { Badge } from "../ui/Badge";
import { cn } from "../../lib/utils";

const signalConfig = {
  STRONG_BUY: { label: "STRONG BUY",  color: "text-bull",    bg: "bg-bull/15",    icon: TrendingUp   },
  BUY:        { label: "BUY",         color: "text-bull",    bg: "bg-bull/10",    icon: TrendingUp   },
  NEUTRAL:    { label: "NEUTRAL",     color: "text-neutral", bg: "bg-secondary",  icon: Minus        },
  SELL:       { label: "SELL",        color: "text-bear",    bg: "bg-bear/10",    icon: TrendingDown },
  STRONG_SELL:{ label: "STRONG SELL", color: "text-bear",    bg: "bg-bear/15",    icon: TrendingDown },
};

export function ReasoningPanel() {
  const r = mockReasoning;
  const cfg = signalConfig[r.signal as keyof typeof signalConfig] ?? signalConfig.NEUTRAL;
  const Icon = cfg.icon;

  return (
    <div className="p-4 space-y-4">
      {/* Signal badge */}
      <div className={cn("flex items-center gap-3 p-4 rounded-xl border border-border", cfg.bg)}>
        <div className={cn("flex items-center justify-center w-12 h-12 rounded-xl bg-background/50")}>
          <Icon className={cn("w-6 h-6", cfg.color)} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={cn("text-xl font-bold", cfg.color)}>{cfg.label}</span>
            <Badge variant="outline" className="text-xs">{r.symbol}</Badge>
            <Badge variant="outline" className="text-xs">{r.timeframe}</Badge>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-2 bg-background rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all", r.confidence >= 70 ? "bg-bull" : r.confidence >= 50 ? "bg-yellow-400" : "bg-bear")}
                style={{ width: `${r.confidence}%` }}
              />
            </div>
            <span className="text-xs font-semibold num">{r.confidence}%</span>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="rounded-lg border border-border p-3 text-sm text-foreground/90 leading-relaxed bg-secondary/20">
        {r.summary}
      </div>

      {/* Factors */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Key Factors</p>
        <div className="space-y-2">
          {r.factors.map((f, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="flex-1 flex items-center justify-between gap-2 min-w-0">
                <span className="text-xs text-muted-foreground truncate">{f.label}</span>
                <span className="text-xs font-medium text-foreground whitespace-nowrap">{f.value}</span>
              </div>
              <div className="w-16 h-1.5 bg-secondary rounded-full overflow-hidden shrink-0">
                <div className="h-full bg-primary rounded-full" style={{ width: `${f.weight * 3}%` }} />
              </div>
              <span className="text-[10px] text-muted-foreground w-8 text-right">{f.weight}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Risks */}
      {r.risks.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" /> Risks
          </p>
          <ul className="space-y-1.5">
            {r.risks.map((risk, i) => (
              <li key={i} className="flex gap-2 text-xs text-foreground/80">
                <span className="text-yellow-400 shrink-0">•</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action */}
      <div className="flex items-start gap-2 rounded-lg border border-bull/30 bg-bull/5 p-3">
        <Target className="w-4 h-4 text-bull shrink-0 mt-0.5" />
        <p className="text-sm text-foreground/90">{r.action}</p>
      </div>
    </div>
  );
}
