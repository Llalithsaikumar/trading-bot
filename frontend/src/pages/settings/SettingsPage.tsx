import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Separator } from "../../components/ui/separator";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { Badge } from "../../components/ui/Badge";
import { useAuthStore } from "../../stores/authStore";
import toast from "react-hot-toast";
import { Key, Bell, Palette, Shield, User, Zap } from "lucide-react";

function Section({ title, description, icon: Icon, children }: {
  title: string; description?: string; icon: React.FC<any>; children: React.ReactNode
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10">
          <Icon className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

function ToggleSetting({ label, description, defaultChecked = false }: {
  label: string; description?: string; defaultChecked?: boolean
}) {
  const [checked, setChecked] = useState(defaultChecked);
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <div>
        <p className="text-sm">{label}</p>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      <Switch checked={checked} onCheckedChange={setChecked} />
    </div>
  );
}

const EXCHANGES = ["binance", "bybit", "okx", "hyperliquid"];

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 600));
    setSaving(false);
    toast.success("Settings saved");
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage your account, API keys, and preferences.</p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="w-full sm:w-auto">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="exchanges">Exchanges</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="risk">Risk</TabsTrigger>
        </TabsList>

        {/* ── Profile ─── */}
        <TabsContent value="profile">
          <Card>
            <CardContent className="pt-6 space-y-5">
              <Section title="Account" description="Your personal information" icon={User}>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="username">Username</Label>
                    <Input id="username" defaultValue={user?.username ?? "trader"} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" type="email" defaultValue={user?.email ?? "trader@example.com"} />
                  </div>
                  <div className="space-y-1.5 sm:col-span-2">
                    <Label htmlFor="fullname">Full Name</Label>
                    <Input id="fullname" defaultValue={user?.full_name ?? ""} placeholder="Your name" />
                  </div>
                </div>
              </Section>
              <Separator />
              <Section title="Security" description="Password and two-factor authentication" icon={Key}>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label>Current Password</Label>
                    <Input type="password" placeholder="••••••••" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>New Password</Label>
                    <Input type="password" placeholder="••••••••" />
                  </div>
                </div>
                <ToggleSetting label="Two-Factor Authentication" description="Require 2FA on every login" />
              </Section>
              <Button onClick={handleSave} loading={saving}>Save Changes</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Exchanges ─── */}
        <TabsContent value="exchanges">
          <div className="space-y-4">
            {EXCHANGES.map((ex) => (
              <Card key={ex}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="capitalize">{ex}</CardTitle>
                    <Badge variant="outline">Not connected</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1.5">
                    <Label>API Key</Label>
                    <Input type="password" placeholder={`${ex} API key`} />
                  </div>
                  {ex === "okx" && (
                    <div className="space-y-1.5">
                      <Label>Passphrase</Label>
                      <Input type="password" placeholder="OKX trading passphrase" />
                    </div>
                  )}
                  {ex === "hyperliquid" ? (
                    <div className="space-y-1.5">
                      <Label>Wallet Address</Label>
                      <Input placeholder="0x..." />
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <Label>API Secret</Label>
                      <Input type="password" placeholder={`${ex} API secret`} />
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline">Test Connection</Button>
                    <Button size="sm" onClick={handleSave}>Save</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* ── Notifications ─── */}
        <TabsContent value="notifications">
          <Card>
            <CardContent className="pt-6 space-y-5">
              <Section title="Alerts" description="Choose what triggers notifications" icon={Bell}>
                <ToggleSetting label="Order fills" description="Notify when an order is filled or cancelled" defaultChecked />
                <ToggleSetting label="Position alerts" description="Notify when stop-loss or take-profit is hit" defaultChecked />
                <ToggleSetting label="Price alerts" description="Notify when price crosses alert thresholds" defaultChecked />
                <ToggleSetting label="Agent signals" description="Notify when the AI generates a trading signal" />
                <ToggleSetting label="Risk warnings" description="Notify on risk limit breaches" defaultChecked />
              </Section>
              <Separator />
              <Section title="Channels" icon={Zap}>
                <ToggleSetting label="In-app notifications" defaultChecked />
                <ToggleSetting label="Email notifications" />
                <ToggleSetting label="Telegram bot" />
              </Section>
              <Button onClick={handleSave} loading={saving}>Save</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Risk ─── */}
        <TabsContent value="risk">
          <Card>
            <CardContent className="pt-6 space-y-5">
              <Section title="Position Limits" description="Maximum size and exposure constraints" icon={Shield}>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    { label: "Max Position Size (%)",   placeholder: "10", hint: "% of portfolio per trade" },
                    { label: "Max Daily Loss (%)",       placeholder: "5",  hint: "Auto-pause at this loss" },
                    { label: "Default Stop Loss (%)",    placeholder: "2",  hint: "Auto stop-loss percentage" },
                    { label: "Default Take Profit (%)", placeholder: "4",  hint: "Auto take-profit percentage" },
                  ].map((f) => (
                    <div key={f.label} className="space-y-1.5">
                      <Label>{f.label}</Label>
                      <Input type="number" placeholder={f.placeholder} />
                      <p className="text-xs text-muted-foreground">{f.hint}</p>
                    </div>
                  ))}
                </div>
              </Section>
              <Separator />
              <Section title="Agent Controls" icon={Zap}>
                <ToggleSetting label="Require confirmation for large orders" description="Orders > 2% portfolio require manual confirm" defaultChecked />
                <ToggleSetting label="Paper trading mode" description="Execute all strategies in paper mode" />
                <ToggleSetting label="Emergency stop" description="Halt all agent activity immediately" />
              </Section>
              <Button onClick={handleSave} loading={saving}>Save Risk Settings</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
