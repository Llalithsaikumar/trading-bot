import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { AgentThoughts } from "../../components/agent/AgentThoughts";
import { LiveLogs } from "../../components/agent/LiveLogs";
import { ReasoningPanel } from "../../components/agent/ReasoningPanel";
import { mockAgentThoughts, mockReasoning } from "../../lib/mockData";
import { Brain, ScrollText } from "lucide-react";

const signalBadgeVariant = (s: string) => {
  if (s.includes("BUY")) return "success";
  if (s.includes("SELL")) return "danger";
  return "secondary";
};

export function AgentPage() {
  return (
    <div className="p-6 space-y-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-bold">Agent AI</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Real-time AI agent reasoning, decisions, and logs.</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="success" className="gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-bull animate-pulse" />
            Active
          </Badge>
          <Badge variant={signalBadgeVariant(mockReasoning.signal)}>
            {mockReasoning.signal}
          </Badge>
        </div>
      </div>

      {/* Main layout */}
      <div className="flex-1 grid grid-cols-1 xl:grid-cols-2 gap-4 min-h-0">
        {/* Left: Reasoning + Thoughts */}
        <div className="flex flex-col gap-4 min-h-0">
          <Card className="shrink-0">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-primary" />
                <CardTitle>Current Reasoning</CardTitle>
                <Badge variant="outline" className="ml-auto text-[10px]">{mockReasoning.symbol} · {mockReasoning.timeframe}</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <ReasoningPanel />
            </CardContent>
          </Card>

          <Card className="flex-1 min-h-0 flex flex-col">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-primary" />
                <CardTitle>Agent Thoughts</CardTitle>
                <Badge variant="secondary" className="ml-auto">{mockAgentThoughts.length}</Badge>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto space-y-2 max-h-80">
              <AgentThoughts thoughts={mockAgentThoughts} />
            </CardContent>
          </Card>
        </div>

        {/* Right: Live Logs */}
        <Card className="flex flex-col min-h-0">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ScrollText className="w-4 h-4 text-primary" />
              <CardTitle>Live System Logs</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-0 overflow-hidden">
            <div className="h-full min-h-96">
              <LiveLogs />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
