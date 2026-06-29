"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError, api } from "@/lib/api";
import type { Agent, LlmProvider, VectorDbType } from "@/lib/types";

export default function AgentSettingsPage() {
  const params = useParams<{ id: string }>();
  const agentId = Number(params.id);

  const [agent, setAgent] = useState<Agent | null>(null);
  const [name, setName] = useState("");
  const [provider, setProvider] = useState<LlmProvider>("ollama");
  const [vectorDb, setVectorDb] = useState<VectorDbType>("pgvector");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getAgent(agentId)
      .then((a) => {
        setAgent(a);
        setName(a.name);
        setProvider(a.llm_provider);
        setVectorDb(a.vector_db_type);
      })
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Failed to load agent"),
      );
  }, [agentId]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!agent) return;
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.updateAgent(agent.id, {
        name,
        llm_provider: provider,
        vector_db_type: vectorDb,
      });
      setAgent(updated);
      setSaved(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (!agent && !error) return <p className="text-muted-foreground">Loading…</p>;
  if (error && !agent) {
    return (
      <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
        {error}
      </div>
    );
  }
  if (!agent) return null;

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/agents/${agent.id}`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to agent
        </Link>
      </div>

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agent settings</h1>
        <p className="text-muted-foreground">
          Configure how this agent runs reviews.
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}
      {saved && (
        <div className="rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-600">
          Settings saved.
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
          <CardDescription>Identity and provider configuration.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="name">
                Agent name
              </label>
              <input
                id="name"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">LLM provider</label>
              <Select value={provider} onValueChange={(v) => setProvider(v as LlmProvider)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ollama">ollama (local)</SelectItem>
                  <SelectItem value="gemini">gemini (cloud)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Vector DB</label>
              <Select value={vectorDb} onValueChange={(v) => setVectorDb(v as VectorDbType)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pgvector">pgvector</SelectItem>
                  <SelectItem value="chromadb">chromadb</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Knowledge base</CardTitle>
          <CardDescription>
            Re-ingest the repo and issues from GitHub.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <span className="capitalize">{agent.ingestion_status}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Chunks</span>
            <span>{agent.chunk_count}</span>
          </div>
          {agent.last_ingested_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last synced</span>
              <span>{new Date(agent.last_ingested_at).toLocaleString()}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
