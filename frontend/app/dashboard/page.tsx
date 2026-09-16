"use client";

import { useCallback, useEffect, useState } from "react";

import { StatCard, StatCardSkeleton } from "@/components/dashboard/stat-card";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api-client";
import { fetchDashboardStats, type DashboardStats } from "@/lib/dashboard";

const CARD_COUNT = 6;

// A counts-only overview of what is stored today. It deliberately says nothing about
// teacher or room availability, which needs generated timetables.
export default function StatsOverviewPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    // Fetches fresh counts; the page keeps showing the previous numbers while it refreshes.
    setLoading(true);
    setError(null);
    try {
      setStats(await fetchDashboardStats());
    } catch (cause) {
      setError(`Couldn't load the stats. ${errorMessage(cause)}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load once when the page opens.
    void load();
  }, [load]);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-content">Stats overview</h1>
          <p className="mt-1 text-sm text-content/70">
            Counts read from the database each time this page loads.
            {stats && ` Last updated ${new Date(stats.generated_at).toLocaleTimeString()}.`}
          </p>
        </div>
        <Button variant="secondary" onClick={load} loading={loading} className="w-full sm:w-auto">
          {loading ? "Refreshing…" : "Refresh"}
        </Button>
      </header>

      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      <section aria-label="Counts" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {stats ? (
          <>
            <StatCard
              label="Departments"
              value={stats.departments}
              detail="Computer Science, Artificial Intelligence and Mathematics"
            />
            <StatCard
              label="Programs"
              value={stats.programs.total}
              detail={`${stats.programs.schedulable} schedulable (BS) · ${stats.programs.not_yet_schedulable} listed, not yet schedulable`}
            />
            <StatCard
              label="Course schemes"
              value={stats.course_schemes}
              detail={stats.course_schemes === 0 ? "None saved yet" : "Active schemes saved"}
            />
            <StatCard
              label="Courses"
              value={stats.courses.total}
              detail={`Across active schemes · ${stats.courses.with_lab} with a lab`}
            />
            <StatCard
              label="Classrooms"
              value={stats.classrooms}
              detail={stats.classrooms === 0 ? "None entered yet" : "Rooms, labs and halls on record"}
            />
            <StatCard
              label="Teachers"
              value={stats.teachers}
              detail={stats.teachers === 0 ? "None entered yet" : "Teachers on record"}
            />
          </>
        ) : (
          Array.from({ length: CARD_COUNT }, (_, index) => <StatCardSkeleton key={index} />)
        )}
      </section>

      {stats && (
        <section className="mt-8 rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
          <h2 className="text-lg font-semibold text-content">Saved schemes by program and year</h2>
          {stats.scheme_breakdown.length === 0 ? (
            <p className="mt-3 text-sm text-content/60">No course schemes saved yet.</p>
          ) : (
            <ul className="mt-4 divide-y divide-content/10">
              {stats.scheme_breakdown.map((item) => (
                <li
                  key={item.scheme_id}
                  className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <p className="font-medium text-content">
                    {item.program_name}
                    <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium">
                      Scheme year {item.scheme_year}
                    </span>
                  </p>
                  <p className="text-sm text-content/70">
                    {item.course_count} courses · {item.lab_course_count} with a lab
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
