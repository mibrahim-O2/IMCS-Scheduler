import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ChatWidget } from "@/components/chat/chat-widget";
import { SiteHeader } from "@/components/ui/site-header";

import "./globals.css";

export const metadata: Metadata = {
  title: "IMCS Scheduler",
  description:
    "Timetable generation and scheduling for the Institute of Mathematics & Computer Science, University of Sindh.",
  icons: { icon: "/imcs-logo.png" },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  // Shared shell: palette-driven page background with the site header above every page.
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface text-content antialiased">
        <SiteHeader />
        {children}
        <ChatWidget />
      </body>
    </html>
  );
}
