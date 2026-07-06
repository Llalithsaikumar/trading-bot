import { ResponsiveContainer, LineChart, Line } from "recharts";

interface Props {
  data: number[];
  color?: string;
  height?: number;
}

export function MiniSparkline({ data, color = "#22c55e", height = 40 }: Props) {
  const chartData = data.map((v, i) => ({ v, i }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
