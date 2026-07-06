import { Bell, Search } from "lucide-react";
import { useTradingStore } from "../../stores/tradingStore";
import { mockTickers } from "../../lib/mockData";
import { formatCurrency, formatPercent } from "../../lib/formatters";
import { cn } from "../../lib/utils";

const SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"];
const EXCHANGES = ["binance", "bybit", "okx", "hyperliquid"];

export function TopBar() {
  const { selectedSymbol, selectedExchange, setSymbol, setExchange } = useTradingStore();
  const ticker = mockTickers[selectedSymbol];

  return (
    <header className="flex items-center h-14 px-4 border-b border-border bg-card shrink-0 gap-4">
      {/* Symbol quick-select */}
      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
        {SYMBOLS.map((sym) => {
          const t = mockTickers[sym];
          const active = sym === selectedSymbol;
          return (
            <button
              key={sym}
              onClick={() => setSymbol(sym)}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors",
                active ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <span className="font-semibold">{sym.replace("/USDT", "")}</span>
              {t && (
                <>
                  <span className="num">{formatCurrency(t.price, true)}</span>
                  <span className={t.change >= 0 ? "text-bull" : "text-bear"}>
                    {formatPercent(t.change)}
                  </span>
                </>
              )}
            </button>
          );
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Exchange selector */}
      <select
        value={selectedExchange}
        onChange={(e) => setExchange(e.target.value)}
        className="h-8 rounded-md border border-border bg-secondary px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring capitalize"
      >
        {EXCHANGES.map((ex) => (
          <option key={ex} value={ex} className="capitalize">{ex.charAt(0).toUpperCase() + ex.slice(1)}</option>
        ))}
      </select>

      {/* Search */}
      <button className="flex items-center gap-2 h-8 px-3 rounded-md border border-border bg-secondary text-xs text-muted-foreground hover:text-foreground hover:border-ring transition-colors">
        <Search className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Search...</span>
        <kbd className="hidden sm:inline text-[10px] bg-background px-1 rounded">⌘K</kbd>
      </button>

      {/* Notifications */}
      <button className="relative flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors">
        <Bell className="w-4 h-4" />
        <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-bear" />
      </button>
    </header>
  );
}
