"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LogIn } from "lucide-react";

import { Sidebar } from "./sidebar";
import { isDemoMode, exitDemoMode } from "./auth-guard";

/** Sidebar navigation shell shown on every authenticated page. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    setDemo(isDemoMode());
  }, []);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {demo && (
          <div className="sticky top-0 z-40 flex items-center justify-center gap-3 border-b border-border bg-warning/10 px-4 py-2.5 text-sm">
            <span className="text-muted-foreground">
              You&apos;re viewing a demo. Data shown is for illustration only.
            </span>
            <Link
              href="/login"
              onClick={() => exitDemoMode()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-colors hover:opacity-90"
            >
              <LogIn className="h-3.5 w-3.5" />
              Sign in
            </Link>
          </div>
        )}
        <div className="container py-8">{children}</div>
      </main>
    </div>
  );
}
