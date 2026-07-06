import { useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, CartesianGrid, Tooltip,
  Area, ReferenceLine,
} from "recharts";
import { formatPrice, formatNumber } from "../../lib/formatters";
import type { OHLCVCandle } from "../../types";

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const isUp = d.close >= d.open;
  return (
    <div className="bg-card border border-border rounded-lg p-3 text-xs space-y-1 shadow-xl">
      <p className="text-muted-foreground">{new Date(d.timestamp).toLocaleString()}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        <span className="text-muted-foreground">O</span><span className="num">{formatPrice(d.open)}</span>
        <span className="text-muted-foreground">H</span><span className="num text-bull">{formatPrice(d.high)}</span>
        <span className="text-muted-foreground">L</span><span className="num text-bear">{formatPrice(d.low)}</span>
        <span className="text-muted-foreground">C</span>
        <span className={`num font-bold ${isUp ? "text-bull" : "text-bear"}`}>{formatPrice(d.close)}</span>
        <span className="text-muted-foreground">Vol</span><span className="num">{formatNumber(d.volume, 0)}</span>
      </div>
    </div>
  );
};

export function PriceChart({ candles, symbol: _symbol }: { candles: OHLCVCandle[]; symbol: string }) {
  const data = useMemo(() =>
    candles.map((c) => ({
      ...c,
      time: new Date(c.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    })), [candles]);

  const prices = candles.map((c) => c.close);
  const minP = Math.min(...prices) * 0.999;
  const maxP = Math.max(...prices) * 1.001;
  const lastClose = candles[candles.length - 1]?.close ?? 0;
  const firstClose = candles[0]?.close ?? 0;
  const isUp = lastClose >= firstClose;

  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={isUp ? "#22c55e" : "#ef4444"} stopOpacity={0.2} />
              <stop offset="100%" stopColor={isUp ? "#22c55e" : "#ef4444"} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 14%)" vertical={false} />
          <XAxis dataKey="time" tick={{ fill: "hsl(215 20% 55%)", fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis domain={[minP, maxP]} tick={{ fill: "hsl(215 20% 55%)", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={formatPrice} width={72} orientation="right" />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={lastClose} stroke="hsl(217 91% 60%)" strokeDasharray="4 4" strokeWidth={1} />
          <Area type="monotone" dataKey="close" stroke={isUp ? "#22c55e" : "#ef4444"} strokeWidth={2} fill="url(#priceGrad)" dot={false} activeDot={{ r: 3 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
