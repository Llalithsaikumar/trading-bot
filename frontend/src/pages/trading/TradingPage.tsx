import { useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../../components/ui/select";
import { PriceChart } from "../../components/charts/PriceChart";
import { OrderBook } from "../../components/charts/OrderBook";
import { OrderForm } from "../../components/trading/OrderForm";
import { PositionList } from "../../components/trading/PositionList";
import { useOHLCVQuery } from "../../hooks/useMarketData";
import { useTradingStore } from "../../stores/tradingStore";
import { mockTickers } from "../../lib/mockData";
import { formatCurrency, formatPercent } from "../../lib/formatters";
import { cn } from "../../lib/utils";
import { StrategyCard } from "../../components/trading/StrategyCard";
import { useStrategies } from "../../hooks/useStrategies";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];

export function TradingPage() {
  const { selectedSymbol, selectedExchange, selectedTimeframe, setTimeframe } = useTradingStore();
  const { data: candles = [], isLoading } = useOHLCVQuery(selectedExchange, selectedSymbol, selectedTimeframe);
  const { data: strategies = [] } = useStrategies();
  const ticker = mockTickers[selectedSymbol];
  const midPrice = ticker?.price ?? 0;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Ticker bar */}
      <div className="flex items-center gap-6 px-4 py-2 border-b border-border bg-card shrink-0 text-sm">
        <div>
          <span className="text-lg font-bold">{selectedSymbol}</span>
        </div>
        {ticker && (
          <>
            <div>
              <p className="num font-bold text-lg">{formatCurrency(ticker.price)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">24h Change</p>
              <p className={cn("num font-medium", ticker.change >= 0 ? "text-bull" : "text-bear")}>
                {formatPercent(ticker.change)}
              </p>
            </div>
            <div className="hidden sm:block">
              <p className="text-xs text-muted-foreground">24h Volume</p>
              <p className="num text-sm">{formatCurrency(ticker.volume, true)}</p>
            </div>
          </>
        )}
        <div className="ml-auto flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={cn(
                "px-2.5 py-1 rounded text-xs font-medium transition-colors",
                selectedTimeframe === tf ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >{tf}</button>
          ))}
        </div>
      </div>

      {/* Main grid */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chart area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 p-3">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                Loading chart...
              </div>
            ) : (
              <PriceChart candles={candles} symbol={selectedSymbol} />
            )}
          </div>

          {/* Positions / Orders tabs */}
          <div className="border-t border-border">
            <Tabs defaultValue="positions">
              <div className="px-4 pt-2">
                <TabsList>
                  <TabsTrigger value="positions">Positions</TabsTrigger>
                  <TabsTrigger value="orders">Open Orders</TabsTrigger>
                </TabsList>
              </div>
              <TabsContent value="positions" className="px-2 pb-3 max-h-44 overflow-y-auto">
                <PositionList />
              </TabsContent>
              <TabsContent value="orders" className="px-4 pb-3 text-sm text-muted-foreground">
                No open orders
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Right panel */}
        <div className="w-72 xl:w-80 shrink-0 border-l border-border flex flex-col overflow-hidden">
          <Tabs defaultValue="order">
            <div className="border-b border-border px-3 pt-2">
              <TabsList>
                <TabsTrigger value="order">Order</TabsTrigger>
                <TabsTrigger value="book">Book</TabsTrigger>
                <TabsTrigger value="strategy">Strategy</TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="order" className="overflow-y-auto flex-1">
              <OrderForm />
            </TabsContent>
            <TabsContent value="book" className="flex-1 overflow-hidden h-96">
              <OrderBook midPrice={midPrice} />
            </TabsContent>
            <TabsContent value="strategy" className="p-3 space-y-3 overflow-y-auto">
              {strategies.map((s) => <StrategyCard key={s.id} strategy={s} />)}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
