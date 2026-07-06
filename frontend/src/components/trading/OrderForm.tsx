import { useState } from "react";
import { Button } from "../ui/Button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/tabs";
import { Separator } from "../ui/separator";
import { formatCurrency, formatPrice } from "../../lib/formatters";
import { mockPortfolio, mockTickers } from "../../lib/mockData";
import { useTradingStore } from "../../stores/tradingStore";
import toast from "react-hot-toast";

export function OrderForm() {
  const { selectedSymbol } = useTradingStore();
  const ticker = mockTickers[selectedSymbol];
  const price = ticker?.price ?? 0;

  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState<"market" | "limit">("limit");
  const [amount, setAmount] = useState("");
  const [limitPrice, setLimitPrice] = useState(String(price.toFixed(2)));
  const [loading, setLoading] = useState(false);

  const total = parseFloat(amount || "0") * (orderType === "market" ? price : parseFloat(limitPrice || "0"));
  const fee = total * 0.001;
  const balance = mockPortfolio.available_balance;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) {
      toast.error("Enter a valid amount");
      return;
    }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    toast.success(`${side.toUpperCase()} order placed — ${amount} ${selectedSymbol.split("/")[0]}`);
    setAmount("");
  };

  const pcts = [25, 50, 75, 100];

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 p-4">
      {/* Side */}
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => setSide("buy")}
          className={`h-9 rounded-md text-sm font-semibold transition-colors ${side === "buy" ? "bg-bull text-white" : "border border-border text-muted-foreground hover:border-bull hover:text-bull"}`}
        >Buy</button>
        <button
          type="button"
          onClick={() => setSide("sell")}
          className={`h-9 rounded-md text-sm font-semibold transition-colors ${side === "sell" ? "bg-bear text-white" : "border border-border text-muted-foreground hover:border-bear hover:text-bear"}`}
        >Sell</button>
      </div>

      {/* Type */}
      <Tabs value={orderType} onValueChange={(v) => setOrderType(v as any)}>
        <TabsList className="w-full">
          <TabsTrigger value="market" className="flex-1">Market</TabsTrigger>
          <TabsTrigger value="limit" className="flex-1">Limit</TabsTrigger>
          <TabsTrigger value="stop" className="flex-1">Stop</TabsTrigger>
        </TabsList>
        <TabsContent value="market" />
        <TabsContent value="limit">
          <div className="mt-2 space-y-1">
            <Label>Limit Price</Label>
            <Input type="number" value={limitPrice} onChange={(e) => setLimitPrice(e.target.value)} suffix="USDT" className="num" />
          </div>
        </TabsContent>
        <TabsContent value="stop">
          <div className="mt-2 space-y-1">
            <Label>Stop Price</Label>
            <Input type="number" placeholder="0.00" suffix="USDT" className="num" />
          </div>
        </TabsContent>
      </Tabs>

      {/* Market price display */}
      {orderType === "market" && (
        <div className="flex items-center justify-between rounded-md bg-secondary px-3 py-2 text-sm">
          <span className="text-muted-foreground">Market price</span>
          <span className="num font-medium">{formatPrice(price)} USDT</span>
        </div>
      )}

      {/* Amount */}
      <div className="space-y-1">
        <Label>Amount ({selectedSymbol.split("/")[0]})</Label>
        <Input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.0000"
          className="num"
          step="0.0001"
          min="0"
        />
        <div className="grid grid-cols-4 gap-1 mt-1">
          {pcts.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setAmount(((balance * p / 100) / price).toFixed(4))}
              className="h-6 rounded text-[10px] text-muted-foreground border border-border hover:border-ring hover:text-foreground transition-colors"
            >{p}%</button>
          ))}
        </div>
      </div>

      <Separator />

      {/* Summary */}
      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between text-muted-foreground">
          <span>Available</span>
          <span className="num">{formatCurrency(balance)}</span>
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Total</span>
          <span className="num text-foreground">{formatCurrency(total)}</span>
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>Fee (0.1%)</span>
          <span className="num">{formatCurrency(fee)}</span>
        </div>
      </div>

      <Button
        type="submit"
        variant={side === "buy" ? "bull" : "bear"}
        size="lg"
        loading={loading}
        className="w-full font-bold"
      >
        {loading ? "Placing..." : `${side === "buy" ? "Buy" : "Sell"} ${selectedSymbol.split("/")[0]}`}
      </Button>
    </form>
  );
}
