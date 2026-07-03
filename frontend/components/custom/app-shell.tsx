"use client";

import { Sidebar } from "./sidebar";

/** Sidebar navigation shell shown on every authenticated page. */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="container py-8">{children}</div>
      </main>
    </div>
  );
}
