import Image from "next/image";
import Link from "next/link";

import { API_BASE_URL } from "@/lib/api-client";

const statusTokens = [
  { label: "Available", dotClass: "bg-status-available" },
  { label: "Busy", dotClass: "bg-status-busy" },
  { label: "Conflict", dotClass: "bg-status-conflict" },
] as const;

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-8 px-6 py-12 text-center">
      <Image
        src="/imcs-logo.png"
        alt="Institute of Mathematics & Computer Science, University of Sindh"
        width={180}
        height={180}
        priority
      />

      <section className="w-full rounded-xl bg-card p-8 shadow-sm ring-1 ring-content/10">
        <p className="text-sm font-medium uppercase tracking-wide text-primary">
          Phase 0 · Scaffold
        </p>
        <h1 className="mt-2 text-3xl font-semibold">IMCS Scheduler</h1>
        <p className="mt-3 text-content/70">
          Scaffold running. Timetable generation, course schemes and the live dashboard
          arrive in later phases.
        </p>

        <ul className="mt-6 flex flex-wrap justify-center gap-3">
          {statusTokens.map(({ label, dotClass }) => (
            <li
              key={label}
              className="inline-flex items-center gap-2 rounded-full bg-surface px-3 py-1 text-sm"
            >
              <span className={`h-2.5 w-2.5 rounded-full ${dotClass}`} aria-hidden />
              {label}
            </li>
          ))}
        </ul>

        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            href="/schemes"
            className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary/90"
          >
            Course schemes
          </Link>
          <a
            href={`${API_BASE_URL}/docs`}
            className="inline-flex min-h-11 items-center justify-center rounded-lg bg-surface px-5 py-2.5 text-sm font-medium text-content ring-1 ring-content/20 hover:bg-content/5"
          >
            Backend API docs
          </a>
        </div>
      </section>
    </main>
  );
}
