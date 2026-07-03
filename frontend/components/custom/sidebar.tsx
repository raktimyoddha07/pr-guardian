"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { GitHubConnection } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { 
  LayoutDashboard, 
  GitBranch, 
  Settings, 
  Plus,
  Github,
  LogOut,
  ChevronDown,
  ChevronRight
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const [connections, setConnections] = useState<GitHubConnection[]>([]);
  const [showConnections, setShowConnections] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      const conns = await api.listGitHubConnections();
      setConnections(conns);
    } catch (error) {
      console.error("Failed to load GitHub connections:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectGitHub = async () => {
    try {
      const { authorization_url } = await api.getGitHubAuthUrl();
      window.location.href = authorization_url;
    } catch (error) {
      console.error("Failed to get GitHub auth URL:", error);
    }
  };

  const handleDeleteConnection = async (connectionId: number) => {
    try {
      await api.deleteGitHubConnection(connectionId);
      setConnections(connections.filter(c => c.id !== connectionId));
    } catch (error) {
      console.error("Failed to delete connection:", error);
    }
  };

  const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/agents", icon: GitBranch, label: "Agents" },
  ];

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <aside className="w-64 border-r bg-card h-screen flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b">
        <Link href="/dashboard" className="flex items-center gap-2 font-bold text-xl">
          <GitBranch className="h-6 w-6" />
          PR Guardian
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                    isActive(item.href)
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* GitHub Connections */}
        <div className="mt-8">
          <button
            onClick={() => setShowConnections(!showConnections)}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground w-full"
          >
            {showConnections ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Github className="h-4 w-4" />
            GitHub Accounts
          </button>

          {showConnections && (
            <div className="mt-2 space-y-2 pl-4">
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : connections.length === 0 ? (
                <Button
                  onClick={handleConnectGitHub}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Connect Account
                </Button>
              ) : (
                <>
                  {connections.map((conn) => (
                    <div
                      key={conn.id}
                      className="flex items-center justify-between p-2 rounded bg-muted text-sm"
                    >
                      <span className="font-medium">{conn.github_username}</span>
                      <button
                        onClick={() => handleDeleteConnection(conn.id)}
                        className="text-muted-foreground hover:text-destructive"
                      >
                        <LogOut className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  <Button
                    onClick={handleConnectGitHub}
                    variant="outline"
                    size="sm"
                    className="w-full"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Account
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      </nav>

      {/* User Actions */}
      <div className="p-4 border-t">
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={() => {
            if (typeof window !== "undefined") {
              localStorage.removeItem("prguardian.token");
              window.location.href = "/login";
            }
          }}
        >
          <LogOut className="h-4 w-4 mr-2" />
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
