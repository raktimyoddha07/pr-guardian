"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useSession } from "@/lib/auth";

const DEMO_KEY = "prguardian.demo";

export function isDemoMode(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(DEMO_KEY) === "true";
}

export function enterDemoMode(): void {
  window.localStorage.setItem(DEMO_KEY, "true");
}

export function exitDemoMode(): void {
  window.localStorage.removeItem(DEMO_KEY);
}

/**
 * Client-side route guard for the protected area. While the session is
 * resolving we show a minimal loader; if there's no token/user we redirect to
 * /login (with a `next` param to bounce back).
 *
 * When demo mode is active (localStorage prguardian.demo = "true") the guard
 * is bypassed so an unauthenticated visitor can browse the UI.
 *
 * Note: this is a UX guard only — the backend enforces real authorization on
 * every request via the JWT.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useSession();
  const router = useRouter();
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    setDemo(isDemoMode());
  }, []);

  useEffect(() => {
    if (!loading && !user && !demo) {
      router.replace("/login?next=" + window.location.pathname);
    }
  }, [loading, user, router, demo]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (!user && !demo) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  return <>{children}</>;
}
