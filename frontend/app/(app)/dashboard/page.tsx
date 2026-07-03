"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Agent, AgentStats, DashboardStats, FlaggedAccount } from "@/lib/types";

export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [perAgent, setPerAgent] = useState<AgentStats[]>([]);
  const [flagged, setFlagged] = useState<FlaggedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter by agent
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");

  const loadStats = () => {
    setLoading(true);
    Promise.all([
      api.listAgents(),
      api.getStats(selectedAgentId ? parseInt(selectedAgentId) : undefined),
      api.getPerAgentStats(),
      api.listFlaggedAccounts(selectedAgentId ? parseInt(selectedAgentId) : undefined),
    ])
      .then(([a, s, pa, f]) => {
        setAgents(a);
        setStats(s);
        setPerAgent(pa);
        setFlagged(f);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStats();
  }, [selectedAgentId]);

  const pct = (v: number) => `${Math.round(v * 100)}%`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of PRs processed across all your agents.
          </p>
        </div>
        <div className="flex gap-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="agent-filter">Filter by Agent:</Label>
            <Select value={selectedAgentId} onValueChange={setSelectedAgentId}>
              <SelectTrigger id="agent-filter" className="w-[200px]">
                <SelectValue placeholder="All agents" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All agents</SelectItem>
                {agents.map((a) => (
                  <SelectItem key={a.id} value={String(a.id)}>
                    {a.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button asChild>
            <Link href="/agents/new">New agent</Link>
          </Button>
        </div>
      </div>

      {loading && <p className="text-muted-foreground">Loading…</p>}
      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {!loading && stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total PRs" value={String(stats.total_prs)} />
          <StatCard label="Approved" value={String(stats.approved)} tone="success" />
          <StatCard label="Declined" value={String(stats.declined)} tone="destructive" />
          <StatCard
            label="Flagged accounts"
            value={String(stats.flagged_accounts)}
            hint={stats.banned_accounts > 0 ? `${stats.banned_accounts} banned` : undefined}
          />
          <StatCard label="Errors" value={String(stats.errors)} />
          <StatCard label="Approval rate" value={pct(stats.approval_rate)} />
          <StatCard label="Active agents" value={String(agents.filter((a) => a.is_active).length)} />
          <StatCard label="Total agents" value={String(agents.length)} />
        </div>
      )}

      {!loading && agents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your agents</CardTitle>
            <CardDescription>
              Each agent guards one GitHub repository.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => {
                const s = perAgent.find((p) => p.agent_id === agent.id);
                return (
                  <Link key={agent.id} href={`/agents/${agent.id}`} className="block">
                    <Card className="h-full transition-colors hover:border-primary/50">
                      <CardHeader>
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-1">
                            <CardTitle className="text-lg">{agent.name}</CardTitle>
                            <CardDescription className="font-mono">
                              {agent.repo_full_name}
                            </CardDescription>
                          </div>
                          <Badge variant={agent.is_active ? "success" : "secondary"}>
                            {agent.is_active ? "Active" : "Paused"}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <div className="flex justify-between">
                          <span>PRs</span>
                          <span className="font-medium text-foreground">
                            {s ? `${s.approved}/${s.total_prs} approved` : "—"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>LLM</span>
                          <span className="font-medium text-foreground">
                            {agent.llm_provider}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Ingestion</span>
                          <span className="font-medium text-foreground capitalize">
                            {agent.ingestion_status}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && agents.length === 0 && !error && (
        <Card>
          <CardHeader>
            <CardTitle>No agents yet</CardTitle>
            <CardDescription>
              Create your first agent to start reviewing PRs automatically.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/agents/new">Create agent</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {!loading && (
        <Card>
          <CardHeader>
            <CardTitle>Flagged accounts</CardTitle>
            <CardDescription>
              GitHub accounts flagged by your agents&apos; pipelines.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {flagged.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No flagged accounts yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 pr-4 font-medium">Username</th>
                      <th className="pb-2 pr-4 font-medium">Flags</th>
                      <th className="pb-2 pr-4 font-medium">Status</th>
                      <th className="pb-2 font-medium">First seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {flagged.map((f) => (
                      <tr key={f.github_username} className="border-b last:border-0">
                        <td className="py-2 pr-4 font-medium">
                          <a
                            href={`https://github.com/${f.github_username}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary underline"
                          >
                            {f.github_username}
                          </a>
                        </td>
                        <td className="py-2 pr-4">{f.flag_count}</td>
                        <td className="py-2 pr-4">
                          <Badge
                            variant={f.account_status === "banned" ? "destructive" : "secondary"}
                          >
                            {f.account_status}
                          </Badge>
                        </td>
                        <td className="py-2 text-muted-foreground">
                          {new Date(f.first_seen).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "success" | "destructive";
}) {
  const valueClass =
    tone === "success"
      ? "text-emerald-500"
      : tone === "destructive"
        ? "text-destructive"
        : "text-foreground";
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className={`text-2xl ${valueClass}`}>{value}</CardTitle>
      </CardHeader>
      {hint && (
        <CardContent className="pt-0 text-xs text-muted-foreground">{hint}</CardContent>
      )}
    </Card>
  );
}
