import { Brain, TrendingUp, ShieldAlert, Zap, Info, RefreshCw } from "lucide-react";
import { Badge } from "../ui/Badge";
import { formatTime } from "../../lib/formatters";
import type { AgentThought } from "../../lib/mockData";
import { cn } from "../../lib/utils";

const typeConfig = {
  analysis:  { icon: Brain,       color: "text-primary",  bg: "bg-primary/10",  label: "Analysis" },
  decision:  { icon: Zap,         color: "text-yellow-400", bg: "bg-yellow-500/10", label: "Decision" },
  warning:   { icon: ShieldAlert, color: "text-bear",      bg: "bg-bear/10",     label: "Warning"  },
  action:    { icon: TrendingUp,  color: "text-bull",      bg: "bg-bull/10",     label: "Action"   },
  info:      { icon: Info,        color: "text-neutral",   bg: "bg-secondary",   label: "Info"     },
};

function ThoughtCard({ thought }: { thought: AgentThought }) {
  const cfg = typeConfig[thought.type];
  const Icon = cfg.icon;

  return (
    <div className="flex gap-3 p-4 rounded-lg border border-border hover:border-ring/40 transition-colors">
      <div className={cn("flex items-center justify-center w-8 h-8 rounded-lg shrink-0 mt-0.5", cfg.bg)}>
        <Icon className={cn("w-4 h-4", cfg.color)} />
      </div>
      <div className="flex-1 min-w-0 space-y-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-foreground">{thought.agent}</span>
          <Badge variant={
            thought.type === "decision" ? "warning"
            : thought.type === "warning" ? "danger"
            : thought.type === "action" ? "success"
            : thought.type === "analysis" ? "default"
            : "secondary"
          } className="text-[10px]">
            {cfg.label}
          </Badge>
          {thought.confidence !== undefined && (
            <span className="text-[10px] text-muted-foreground ml-auto">
              {thought.confidence}% confidence
            </span>
          )}
        </div>
        <p className="text-sm text-foreground/90 leading-relaxed">{thought.message}</p>
        <p className="text-[10px] text-muted-foreground">{formatTime(thought.timestamp)}</p>
      </div>
    </div>
  );
}

export function AgentThoughts({ thoughts }: { thoughts: AgentThought[] }) {
  return (
    <div className="space-y-2">
      {thoughts.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
          <RefreshCw className="w-8 h-8 animate-spin opacity-30" />
          <p className="text-sm">Waiting for agent activity...</p>
        </div>
      ) : (
        thoughts.map((t) => <ThoughtCard key={t.id} thought={t} />)
      )}
    </div>
  );
}
