import { useMemo } from "react";
import { formatPrice } from "../../lib/formatters";
import { cn } from "../../lib/utils";

interface Level { price: number; size: number; total: number }

function generateLevels(midPrice: number, isBids: boolean, count = 12): Level[] {
  const levels: Level[] = [];
  let total = 0;
  for (let i = 0; i < count; i++) {
    const offset = (isBids ? -(i + 1) : (i + 1)) * midPrice * 0.0003;
    const price = midPrice + offset;
    const size = 0.1 + Math.random() * 3;
    total += size;
    levels.push({ price, size, total });
  }
  return levels;
}

export function OrderBook({ midPrice }: { midPrice: number }) {
  const bids = useMemo(() => generateLevels(midPrice, true), [midPrice]);
  const asks = useMemo(() => generateLevels(midPrice, false), [midPrice]);
  const maxTotal = Math.max(...[...bids, ...asks].map((l) => l.total));

  const Row = ({ level, side }: { level: Level; side: "bid" | "ask" }) => (
    <div className="relative flex items-center justify-between px-3 py-0.5 text-xs num hover:bg-secondary/40 transition-colors">
      <div
        className={cn("absolute inset-y-0 right-0 opacity-15", side === "bid" ? "bg-bull" : "bg-bear")}
        style={{ width: `${(level.total / maxTotal) * 100}%` }}
      />
      <span className={side === "bid" ? "text-bull" : "text-bear"}>{formatPrice(level.price)}</span>
      <span className="text-foreground">{level.size.toFixed(4)}</span>
      <span className="text-muted-foreground">{level.total.toFixed(2)}</span>
    </div>
  );

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="flex justify-between px-3 py-1.5 text-muted-foreground uppercase tracking-wide border-b border-border">
        <span>Price</span><span>Size</span><span>Total</span>
      </div>
      <div className="flex-1 overflow-hidden">
        <div className="flex flex-col-reverse">
          {asks.slice(0, 10).map((l, i) => <Row key={i} level={l} side="ask" />)}
        </div>
        <div className="flex items-center justify-center py-2 border-y border-border bg-secondary/20">
          <span className="num font-bold text-sm text-foreground">{formatPrice(midPrice)}</span>
        </div>
        {bids.slice(0, 10).map((l, i) => <Row key={i} level={l} side="bid" />)}
      </div>
    </div>
  );
}
