import { useEffect, useRef, useState } from "react";
import { formatTime } from "../../lib/formatters";
import { mockLogs, type LogEntry } from "../../lib/mockData";
import { cn } from "../../lib/utils";
import { Button } from "../ui/Button";
import { Pause, Play, Trash2 } from "lucide-react";

const levelColor: Record<LogEntry["level"], string> = {
  DEBUG:   "text-muted-foreground",
  INFO:    "text-blue-400",
  WARNING: "text-yellow-400",
  ERROR:   "text-bear",
};

const levelBg: Record<LogEntry["level"], string> = {
  DEBUG:   "",
  INFO:    "",
  WARNING: "bg-yellow-500/5",
  ERROR:   "bg-bear/5",
};

const NEW_LOG_TEMPLATES: Omit<LogEntry, "id" | "timestamp">[] = [
  { level: "INFO",    component: "Exchange",       message: "Heartbeat ping acknowledged" },
  { level: "DEBUG",   component: "TechAgent",      message: "Recalculating indicators — BTC/USDT 1H" },
  { level: "INFO",    component: "MarketAgent",     message: "Ticker update: BTC +0.12%, ETH +0.08%" },
  { level: "DEBUG",   component: "RiskAgent",       message: "Portfolio risk check: OK" },
  { level: "INFO",    component: "GraphOrchestrator", message: "Agent cycle started" },
  { level: "WARNING", component: "Exchange",        message: "Rate limit at 85% — throttling requests" },
  { level: "INFO",    component: "ExecutionAgent",  message: "Monitoring BN-008 fill status: pending" },
  { level: "DEBUG",   component: "MemoryAgent",     message: "Embedding 4 new market observations" },
];

let idCounter = 100;

export function LiveLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([...mockLogs].reverse());
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState<LogEntry["level"] | "ALL">("ALL");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      const tpl = NEW_LOG_TEMPLATES[Math.floor(Math.random() * NEW_LOG_TEMPLATES.length)];
      const newEntry: LogEntry = {
        ...tpl,
        id: `l-${++idCounter}`,
        timestamp: new Date().toISOString(),
      };
      setLogs((prev) => [newEntry, ...prev.slice(0, 199)]);
    }, 2500);
    return () => clearInterval(interval);
  }, [paused]);

  const filtered = filter === "ALL" ? logs : logs.filter((l) => l.level === filter);

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center gap-2 p-3 border-b border-border shrink-0">
        <div className="flex gap-1">
          {(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"] as const).map((lv) => (
            <button
              key={lv}
              onClick={() => setFilter(lv)}
              className={cn(
                "px-2 py-0.5 rounded text-[10px] font-medium transition-colors",
                filter === lv ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
                lv !== "ALL" && levelColor[lv as LogEntry["level"]],
              )}
            >{lv}</button>
          ))}
        </div>
        <div className="flex-1" />
        <Button size="icon" variant="ghost" onClick={() => setPaused((p) => !p)} className="w-7 h-7">
          {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
        </Button>
        <Button size="icon" variant="ghost" onClick={() => setLogs([])} className="w-7 h-7">
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Log stream */}
      <div className="flex-1 overflow-y-auto font-mono text-xs p-2 space-y-px">
        {filtered.map((log) => (
          <div key={log.id} className={cn("flex gap-2 px-2 py-0.5 rounded hover:bg-secondary/40", levelBg[log.level])}>
            <span className="text-muted-foreground shrink-0 tabular-nums">{formatTime(log.timestamp)}</span>
            <span className={cn("w-16 shrink-0 font-semibold", levelColor[log.level])}>{log.level}</span>
            <span className="text-primary/70 w-32 shrink-0 truncate">{log.component}</span>
            <span className="text-foreground/80 flex-1">{log.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {paused && (
        <div className="text-center py-1 text-xs text-yellow-400 border-t border-border bg-yellow-500/5 shrink-0">
          ⏸ Log stream paused
        </div>
      )}
    </div>
  );
}
