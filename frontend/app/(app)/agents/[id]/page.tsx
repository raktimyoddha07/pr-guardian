"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";
import type { Agent, PREvent } from "@/lib/types";

interface PRProcessingStatus {
  id: number;
  agent_id: number;
  pr_number: number;
  pr_url: string;
  pr_title: string;
  author_github: string;
  status: string;
  layer_results: any;
  final_decision: string | null;
  decline_reason: string | null;
  error_message: string | null;
  detected_at: string | null;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export default function AgentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const agentId = Number(params.id);

  const [agent, setAgent] = useState<Agent | null>(null);
  const [events, setEvents] = useState<PREvent[]>([]);
  const [processingStatuses, setProcessingStatuses] = useState<PRProcessingStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const processingPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadAgent = useCallback(async () => {
    try {
      const a = await api.getAgent(agentId);
      setAgent(a);
      // Stop polling when ingestion settles.
      if (a.ingestion_status === "done" || a.ingestion_status === "failed") {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load agent");
    }
  }, [agentId]);

  const loadProcessingStatus = useCallback(async () => {
    try {
      const statuses = await api.listProcessingStatus({ agent_id: agentId, limit: 50 });
      setProcessingStatuses(statuses);
      
      // Stop polling if all PRs are completed or failed
      const allComplete = statuses.every(
        s => s.status === "completed" || s.status === "failed"
      );
      if (allComplete && statuses.length > 0) {
        if (processingPollRef.current) {
          clearInterval(processingPollRef.current);
          processingPollRef.current = null;
        }
      }
    } catch (e) {
      console.error("Failed to load processing status:", e);
    }
  }, [agentId]);

  async function load() {
    try {
      const [a, evs, statuses] = await Promise.all([
        api.getAgent(agentId),
        api.listEvents({ agent_id: agentId, limit: 50 }),
        api.listProcessingStatus({ agent_id: agentId, limit: 50 }),
      ]);
      setAgent(a);
      setEvents(evs);
      setProcessingStatuses(statuses);
      
      // If ingestion is running, start polling.
      if (
        a.ingestion_status === "running" ||
        a.ingestion_status === "pending"
      ) {
        pollRef.current = setInterval(() => void loadAgent(), 3000);
      }
      
      // If there are PRs being processed, start polling for status
      const hasProcessing = statuses.some(
        s => s.status !== "completed" && s.status !== "failed"
      );
      if (hasProcessing) {
        processingPollRef.current = setInterval(() => void loadProcessingStatus(), 2000);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load agent");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (processingPollRef.current) clearInterval(processingPollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  async function handleToggle() {
    if (!agent) return;
    setToggling(true);
    try {
      const updated = await api.updateAgent(agent.id, {
        is_active: !agent.is_active,
      });
      setAgent(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to update agent");
    } finally {
      setToggling(false);
    }
  }

  async function handleDelete() {
    if (!agent) return;
    if (!window.confirm(`Delete agent "${agent.name}"? This cannot be undone.`)) {
      return;
    }
    try {
      await api.deleteAgent(agent.id);
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to delete agent");
    }
  }

  async function handleSync() {
    if (!agent) return;
    setSyncing(true);
    try {
      const updated = await api.syncAgent(agent.id);
      setAgent(updated);
      // Start polling for ingestion progress.
      if (updated.ingestion_status === "running" || updated.ingestion_status === "pending") {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = setInterval(() => void loadAgent(), 3000);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to sync");
    } finally {
      setSyncing(false);
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading…</p>;
  if (error && !agent) {
    return (
      <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
        {error}
      </div>
    );
  }
  if (!agent) return null;

  const ingestionRunning =
    agent.ingestion_status === "running" || agent.ingestion_status === "pending";

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/dashboard"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to agents
        </Link>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{agent.name}</h1>
            <Badge variant={agent.is_active ? "success" : "secondary"}>
              {agent.is_active ? "Active" : "Paused"}
            </Badge>
          </div>
          <p className="font-mono text-sm text-muted-foreground">
            {agent.repo_full_name}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleSync}
            disabled={syncing || ingestionRunning}
          >
            {syncing || ingestionRunning ? "Syncing…" : "Re-sync Knowledge Base"}
          </Button>
          <Button
            variant="outline"
            onClick={handleToggle}
            disabled={toggling}
          >
            {agent.is_active ? "Pause" : "Resume"}
          </Button>
          <Button asChild variant="outline">
            <Link href={`/agents/${agent.id}/settings`}>Settings</Link>
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>LLM</CardDescription>
            <CardTitle className="text-base capitalize">
              {agent.llm_provider}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Ingestion status</CardDescription>
            <div className="flex items-center gap-2">
              <CardTitle className="text-base capitalize">
                {agent.ingestion_status}
              </CardTitle>
              {ingestionRunning && (
                <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
              )}
            </div>
            {agent.last_ingested_at && (
              <p className="text-xs text-muted-foreground">
                Last synced{" "}
                {new Date(agent.last_ingested_at).toLocaleString()}
              </p>
            )}
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Knowledge chunks</CardDescription>
            <CardTitle className="text-base">{agent.chunk_count}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total events</CardDescription>
            <CardTitle className="text-base">{events.length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>PR Processing Status</CardTitle>
          <CardDescription>
            Real-time status of PRs being processed through the 4-layer pipeline.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {processingStatuses.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No PRs detected yet. The agent will automatically detect open PRs after ingestion completes.
            </p>
          ) : (
            <div className="space-y-4">
              {processingStatuses.map((status) => (
                <div key={status.id} className="rounded-lg border p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <a
                          href={status.pr_url}
                          target="_blank"
                          rel="noreferrer"
                          className="font-medium text-primary underline"
                        >
                          #{status.pr_number}
                        </a>
                        <span className="text-sm text-muted-foreground">
                          by {status.author_github}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground line-clamp-1">
                        {status.pr_title}
                      </p>
                    </div>
                    <Badge
                      variant={
                        status.status === "completed"
                          ? "success"
                          : status.status === "failed"
                          ? "destructive"
                          : status.status === "detected" || status.status === "queued"
                          ? "secondary"
                          : "default"
                      }
                    >
                      {status.status}
                    </Badge>
                  </div>
                  
                  {status.status !== "detected" && status.status !== "queued" && (
                    <div className="mt-3">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>Layers:</span>
                        <span className={status.layer_results?.hijack_proof ? "text-green-600" : "text-muted-foreground"}>
                          ✓ Hijack Proof
                        </span>
                        <span className={status.layer_results?.spam ? "text-green-600" : "text-muted-foreground"}>
                          ✓ Spam
                        </span>
                        <span className={status.layer_results?.malicious_code ? "text-green-600" : "text-muted-foreground"}>
                          ✓ Malicious Code
                        </span>
                        <span className={status.layer_results?.summary ? "text-green-600" : "text-muted-foreground"}>
                          ✓ Summary
                        </span>
                      </div>
                    </div>
                  )}
                  
                  {status.final_decision && (
                    <div className="mt-2 text-sm">
                      <span className="font-medium">Decision: </span>
                      <Badge
                        variant={status.final_decision === "approved" ? "success" : "destructive"}
                      >
                        {status.final_decision}
                      </Badge>
                      {status.decline_reason && (
                        <span className="ml-2 text-muted-foreground">- {status.decline_reason}</span>
                      )}
                    </div>
                  )}
                  
                  {status.error_message && (
                    <div className="mt-2 text-sm text-destructive">
                      Error: {status.error_message}
                    </div>
                  )}
                  
                  <div className="mt-2 text-xs text-muted-foreground">
                    Detected: {status.detected_at ? new Date(status.detected_at).toLocaleString() : "N/A"}
                    {status.started_at && ` • Started: ${new Date(status.started_at).toLocaleString()}`}
                    {status.completed_at && ` • Completed: ${new Date(status.completed_at).toLocaleString()}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>PR Events History</CardTitle>
          <CardDescription>
            Completed pipeline decisions for this agent. Each PR runs through spam →
            malicious code → hijack-proof → summary layers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No events yet. Install the GitHub App and open a PR on the
              connected repo.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">Date</th>
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
                      <td className="py-2 pr-4">
                        {ev.layer_caught ?? "—"}
                      </td>
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
