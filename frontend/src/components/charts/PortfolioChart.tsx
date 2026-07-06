import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { formatCurrency } from "../../lib/formatters";
import type { PnLDataPoint } from "../../lib/mockData";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const v: number = payload[0].value;
  const pnl: number = payload[1]?.value ?? 0;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-muted-foreground mb-1">{label}</p>
      <p className="font-bold num">{formatCurrency(v)}</p>
      <p className={pnl >= 0 ? "text-bull" : "text-bear"}>
        {pnl >= 0 ? "+" : ""}{formatCurrency(pnl)} daily
      </p>
    </div>
  );
};

export function PortfolioChart({ data }: { data: PnLDataPoint[] }) {
  const minV = Math.min(...data.map((d) => d.value)) * 0.99;
  const maxV = Math.max(...data.map((d) => d.value)) * 1.01;
  const isUp = (data[data.length - 1]?.value ?? 0) >= (data[0]?.value ?? 0);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="portGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={isUp ? "#22c55e" : "#ef4444"} stopOpacity={0.25} />
            <stop offset="100%" stopColor={isUp ? "#22c55e" : "#ef4444"} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 14%)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "hsl(215 20% 55%)", fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis domain={[minV, maxV]} tick={{ fill: "hsl(215 20% 55%)", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => formatCurrency(v, true)} width={60} orientation="right" />
        <Tooltip content={<CustomTooltip />} />
        <Area type="monotone" dataKey="value" stroke={isUp ? "#22c55e" : "#ef4444"} strokeWidth={2} fill="url(#portGrad)" dot={false} activeDot={{ r: 4 }} />
        <Area type="monotone" dataKey="pnl" hide />
      </AreaChart>
    </ResponsiveContainer>
  );
}
