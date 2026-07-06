import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine } from "recharts";
import { formatCurrency } from "../../lib/formatters";
import type { PnLDataPoint } from "../../lib/mockData";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const v = payload[0].value;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-muted-foreground mb-1">{label}</p>
      <p className={`font-bold num ${v >= 0 ? "text-bull" : "text-bear"}`}>
        {v >= 0 ? "+" : ""}{formatCurrency(v)}
      </p>
    </div>
  );
};

export function PnLChart({ data }: { data: PnLDataPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 47% 14%)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "hsl(215 20% 55%)", fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fill: "hsl(215 20% 55%)", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => formatCurrency(v, true)} width={60} orientation="right" />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="hsl(222 47% 14%)" />
        <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.pnl >= 0 ? "rgba(34,197,94,0.7)" : "rgba(239,68,68,0.7)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
