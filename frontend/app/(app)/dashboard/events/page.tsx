"use client";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { PREvent, Agent } from "@/lib/types";

export default function EventsPage() {
  const [events, setEvents] = useState<PREvent[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [agentId, setAgentId] = useState<string>("");
  const [decision, setDecision] = useState<string>("");
  const [layerCaught, setLayerCaught] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  const loadEvents = () => {
    setLoading(true);
    api
      .listEvents({
        limit: 100,
        agent_id: agentId ? parseInt(agentId) : undefined,
        decision: decision || undefined,
        layer_caught: layerCaught || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      })
      .then(setEvents)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load events"),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    Promise.all([api.listAgents(), api.listEvents({ limit: 100 })])
      .then(([a, e]) => {
        setAgents(a);
        setEvents(e);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load data"),
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Events</h1>
        <p className="text-muted-foreground">
          Recent PR events across all your agents.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Filter events by agent, decision, layer, and date range.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-2">
              <Label htmlFor="agent">Agent</Label>
              <Select value={agentId} onValueChange={setAgentId}>
                <SelectTrigger id="agent">
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
            <div className="space-y-2">
              <Label htmlFor="decision">Decision</Label>
              <Select value={decision} onValueChange={setDecision}>
                <SelectTrigger id="decision">
                  <SelectValue placeholder="All decisions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All decisions</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="declined">Declined</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="layer">Layer</Label>
              <Select value={layerCaught} onValueChange={setLayerCaught}>
                <SelectTrigger id="layer">
                  <SelectValue placeholder="All layers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All layers</SelectItem>
                  <SelectItem value="spam">Spam</SelectItem>
                  <SelectItem value="malicious_code">Malicious Code</SelectItem>
                  <SelectItem value="hijack_proof">Hijack Proof</SelectItem>
                  <SelectItem value="summary">Summary</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="start-date">Start Date</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end-date">End Date</Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <Button onClick={loadEvents}>Apply Filters</Button>
            <Button
              variant="outline"
              onClick={() => {
                setAgentId("");
                setDecision("");
                setLayerCaught("");
                setStartDate("");
                setEndDate("");
                loadEvents();
              }}
            >
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Event log</CardTitle>
          <CardDescription>
            Immutable record of every PR decision. Most recent first.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-muted-foreground">Loading…</p>}
          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          {!loading && events.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No events yet.
            </p>
          )}
          {!loading && events.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Date</th>
                    <th className="pb-2 pr-4 font-medium">Agent</th>
                    <th className="pb-2 pr-4 font-medium">PR #</th>
                    <th className="pb-2 pr-4 font-medium">Author</th>
                    <th className="pb-2 pr-4 font-medium">Decision</th>
                    <th className="pb-2 pr-4 font-medium">Layer</th>
                    <th className="pb-2 font-medium">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev) => (
                    <tr key={ev.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 text-muted-foreground">
                        {new Date(ev.created_at).toLocaleString()}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {agents.find((a) => a.id === ev.agent_id)?.name || `#${ev.agent_id}`}
                      </td>
                      <td className="py-2 pr-4">
                        <a
                          href={ev.pr_url}
                          target="_blank"
                          rel="noreferrer"
                          className="font-medium text-primary underline"
                        >
                          #{ev.pr_number}
                        </a>
                      </td>
                      <td className="py-2 pr-4">{ev.author_github}</td>
                      <td className="py-2 pr-4">
                        <Badge
                          variant={
                            ev.decision === "approved"
                              ? "success"
                              : "destructive"
                          }
                        >
                          {ev.decision}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">{ev.layer_caught ?? "—"}</td>
                      <td className="py-2 text-muted-foreground">
                        {ev.reason ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
