import { useState } from "react";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../ui/table";
import { Badge } from "../ui/Badge";
import { Input } from "../ui/input";
import { Button } from "../ui/Button";
import { formatCurrency, formatDate, formatNumber } from "../../lib/formatters";
import { mockOrders } from "../../lib/mockData";
import type { Order } from "../../types";
import { Search, ChevronDown } from "lucide-react";

const statusVariant = (s: Order["status"]) =>
  s === "filled" ? "success" : s === "open" ? "default" : s === "cancelled" ? "secondary" : "warning";

export function TradeHistory() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = mockOrders.filter((o) => {
    const matchSearch = !search || o.symbol.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || o.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="flex flex-col gap-3">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder="Search symbol..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 w-40 h-8 text-xs"
          />
        </div>
        {["all", "filled", "open", "cancelled"].map((s) => (
          <Button
            key={s}
            size="sm"
            variant={statusFilter === s ? "default" : "outline"}
            onClick={() => setStatusFilter(s)}
            className="capitalize h-8"
          >{s}</Button>
        ))}
        <span className="text-xs text-muted-foreground ml-auto">{filtered.length} orders</span>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Symbol</TableHead>
            <TableHead>Side</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="text-right">Price</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead>Status</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((order) => (
            <>
              <TableRow key={order.id} className="cursor-pointer" onClick={() => setExpanded(expanded === order.id ? null : order.id)}>
                <TableCell className="text-xs text-muted-foreground">{formatDate(order.created_at)}</TableCell>
                <TableCell className="font-medium">{order.symbol}</TableCell>
                <TableCell>
                  <Badge variant={order.side === "buy" ? "success" : "danger"}>{order.side.toUpperCase()}</Badge>
                </TableCell>
                <TableCell className="capitalize text-xs text-muted-foreground">{order.order_type.replace("_", " ")}</TableCell>
                <TableCell className="text-right num text-xs">{order.price ? formatCurrency(order.price) : "Market"}</TableCell>
                <TableCell className="text-right num text-xs">{formatNumber(order.filled_quantity || order.quantity, 4)}</TableCell>
                <TableCell className="text-right num text-xs">{order.price ? formatCurrency((order.filled_quantity || order.quantity) * order.price) : "—"}</TableCell>
                <TableCell><Badge variant={statusVariant(order.status)}>{order.status}</Badge></TableCell>
                <TableCell>
                  <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${expanded === order.id ? "rotate-180" : ""}`} />
                </TableCell>
              </TableRow>
              {expanded === order.id && order.agent_reasoning && (
                <TableRow key={`${order.id}-detail`}>
                  <TableCell colSpan={9} className="py-3 px-4">
                    <div className="rounded-lg bg-secondary/50 border border-border p-3 text-xs">
                      <p className="text-muted-foreground font-medium mb-1">🤖 Agent Reasoning</p>
                      <p className="text-foreground/90">{order.agent_reasoning}</p>
                      {order.fee > 0 && (
                        <p className="text-muted-foreground mt-1">Fee: {formatCurrency(order.fee)}</p>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
