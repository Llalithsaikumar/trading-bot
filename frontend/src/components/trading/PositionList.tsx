import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../ui/table";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { formatCurrency, formatNumber, formatPercent } from "../../lib/formatters";
import { mockPortfolio } from "../../lib/mockData";
import type { Position } from "../../types";
import toast from "react-hot-toast";

function PnLBadge({ value }: { value: number }) {
  return (
    <span className={`num font-medium ${value >= 0 ? "text-bull" : "text-bear"}`}>
      {value >= 0 ? "+" : ""}{formatCurrency(value)}
    </span>
  );
}

export function PositionList() {
  const positions = mockPortfolio.positions;

  const handleClose = (p: Position) => {
    toast.success(`Closing ${p.symbol} position...`);
  };

  if (!positions.length) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-muted-foreground text-sm">
        No open positions
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Side</TableHead>
          <TableHead className="text-right">Size</TableHead>
          <TableHead className="text-right">Entry</TableHead>
          <TableHead className="text-right">Mark</TableHead>
          <TableHead className="text-right">PnL</TableHead>
          <TableHead className="text-right">SL / TP</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((p) => {
          const pnlPct = ((p.current_price - p.entry_price) / p.entry_price) * (p.side === "short" ? -100 : 100);
          return (
            <TableRow key={p.id}>
              <TableCell className="font-medium">{p.symbol}</TableCell>
              <TableCell>
                <Badge variant={p.side === "long" ? "success" : p.side === "short" ? "danger" : "secondary"}>
                  {p.side.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell className="text-right num">{formatNumber(p.quantity, 4)}</TableCell>
              <TableCell className="text-right num">{formatCurrency(p.entry_price)}</TableCell>
              <TableCell className="text-right num">{formatCurrency(p.current_price)}</TableCell>
              <TableCell className="text-right">
                <div className="flex flex-col items-end">
                  <PnLBadge value={p.unrealized_pnl} />
                  <span className={`text-[10px] ${pnlPct >= 0 ? "text-bull" : "text-bear"}`}>
                    {formatPercent(pnlPct)}
                  </span>
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div className="text-xs num text-muted-foreground">
                  <div><span className="text-bear">SL</span> {p.stop_loss ? formatCurrency(p.stop_loss) : "—"}</div>
                  <div><span className="text-bull">TP</span> {p.take_profit ? formatCurrency(p.take_profit) : "—"}</div>
                </div>
              </TableCell>
              <TableCell>
                <Button size="sm" variant="outline" onClick={() => handleClose(p)}>Close</Button>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
