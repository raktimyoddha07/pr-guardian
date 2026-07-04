import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/custom/theme-provider";

export const metadata: Metadata = {
  title: "PR Guardian",
  description: "RAG-powered agentic GitHub PR management.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <ThemeProvider defaultTheme="system" storageKey="prguardian-theme">
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
