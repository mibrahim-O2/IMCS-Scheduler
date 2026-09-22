"use client";

import { Calendar, Clock } from "lucide-react";
import { useEffect, useState } from "react";

export function LiveClock() {
  // A small card that ticks the current date/time client-side, once a second, with no
  // page reload styled like the other stat cards so it reads as part of the same page,
  // not a bolted-on widget.
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    // Starting the clock only after mount (not during server render) avoids the server and
    // the browser ever disagreeing about "now" and causing a hydration mismatch.
    setNow(new Date());
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="rounded-xl bg-card p-5 shadow-sm ring-1 ring-content/10">
      <p className="text-xs font-medium uppercase tracking-wide text-content/60">Right now</p>
      <div className="mt-2 flex items-center gap-2 text-3xl font-semibold text-content">
        <Clock className="h-7 w-7 shrink-0 text-primary" aria-hidden />
        <span suppressHydrationWarning>{now ? formatTime(now) : "--:--:--"}</span>
      </div>
      <p className="mt-1 flex items-center gap-1.5 text-sm text-content/70">
        <Calendar className="h-4 w-4 shrink-0" aria-hidden />
        <span suppressHydrationWarning>{now ? formatDate(now) : "Loading…"}</span>
      </p>
    </div>
  );
}

function formatTime(date: Date): string {
  // "14:05:09" 24-hour, seconds included since this is a live-updating display.
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

function formatDate(date: Date): string {
  // "Tue, 22 Sep 2026" short enough to sit on one line next to the calendar icon.
  return date.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}
