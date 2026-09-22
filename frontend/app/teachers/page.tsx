"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/lib/api-client";
import {
  fetchTeacherDetail,
  searchTeachers,
  type Teacher,
  type TeacherDetail,
} from "@/lib/teachers";

const DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri"];

function sortByDay<T extends { day: string; start_time: string }>(sessions: T[]): T[] {
  // Real weekly-schedule rows in Mon-Fri order, then by start time within a day.
  return [...sessions].sort((a, b) => {
    const dayDiff = DAY_ORDER.indexOf(a.day) - DAY_ORDER.indexOf(b.day);
    return dayDiff !== 0 ? dayDiff : a.start_time.localeCompare(b.start_time);
  });
}

// Teacher lookup: search by name, see one teacher's declared availability, every division
// they're assigned to, and their real generated schedule where one exists. Shared by admin
// and teacher alike no separate permission layer for this page.
export default function TeachersPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Teacher[]>([]);
  const [searching, setSearching] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<TeacherDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const runSearch = useCallback(async (text: string) => {
    // Fetches the matching teacher list for whatever is currently typed.
    setSearching(true);
    setListError(null);
    try {
      setResults(await searchTeachers(text));
    } catch (cause) {
      setListError(`Couldn't search teachers. ${errorMessage(cause)}`);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    // Debounced type-ahead: waits for a short pause in typing before calling the API, so
    // every keystroke doesn't fire its own request.
    const timer = setTimeout(() => void runSearch(query), 300);
    return () => clearTimeout(timer);
  }, [query, runSearch]);

  async function handleSelect(id: number) {
    // Loads one teacher's full combined record.
    setSelectedId(id);
    setLoadingDetail(true);
    setDetailError(null);
    try {
      setDetail(await fetchTeacherDetail(id));
    } catch (cause) {
      setDetailError(`Couldn't load this teacher. ${errorMessage(cause)}`);
      setDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-content">Teachers</h1>
        <p className="mt-1 text-sm text-content/70">
          Search for a teacher to see their availability, assigned divisions, and real
          generated schedule.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[20rem_1fr]">
        <section className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-content/60">Search by name</span>
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="e.g. Gulsher"
              className="w-full min-h-11 rounded-lg bg-surface px-3 py-2 text-sm text-content ring-1 ring-content/20 focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </label>

          {listError && (
            <div className="mt-3">
              <Alert tone="error">{listError}</Alert>
            </div>
          )}

          <ul className="mt-4 space-y-1">
            {searching && (
              <li className="flex items-center gap-2 py-2 text-sm text-content/60">
                <Spinner /> Searching…
              </li>
            )}
            {!searching && results.length === 0 && (
              <li className="py-2 text-sm text-content/60">No teachers match &quot;{query}&quot;.</li>
            )}
            {!searching &&
              results.map((teacher) => (
                <li key={teacher.id}>
                  <button
                    type="button"
                    onClick={() => void handleSelect(teacher.id)}
                    className={`flex min-h-11 w-full items-center rounded-lg px-3 text-left text-sm font-medium ${
                      selectedId === teacher.id
                        ? "bg-primary text-white"
                        : "text-content hover:bg-content/5"
                    }`}
                  >
                    {teacher.full_name}
                  </button>
                </li>
              ))}
          </ul>
        </section>

        <section className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
          {selectedId === null && (
            <p className="text-sm text-content/60">Pick a teacher from the list to see their record.</p>
          )}

          {loadingDetail && (
            <p className="flex items-center gap-2 text-sm text-content/60">
              <Spinner /> Loading…
            </p>
          )}

          {detailError && <Alert tone="error">{detailError}</Alert>}

          {detail && !loadingDetail && <TeacherDetailView detail={detail} />}
        </section>
      </div>
    </main>
  );
}

function TeacherDetailView({ detail }: { detail: TeacherDetail }) {
  // The right-hand panel once a teacher is selected: profile, then every division they're
  // assigned to, then their real schedule (or a plain "none generated yet" message).
  const days = detail.availability.days ?? [];
  const sortedSchedule = sortByDay(detail.schedule);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-content">{detail.full_name}</h2>
        <p className="mt-1 text-sm text-content/70">
          {detail.designation ?? "No designation on record"} · Available{" "}
          {days.length ? days.join(", ") : "no days declared"}
        </p>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-content">Division assignments</h3>
        {detail.assignments.length === 0 ? (
          <p className="mt-2 text-sm text-content/60">Not assigned to any division yet.</p>
        ) : (
          <div className="mt-2 overflow-x-auto rounded-xl ring-1 ring-content/15">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead className="bg-content/5 text-xs uppercase tracking-wide text-content/60">
                <tr>
                  <th className="px-4 py-2 font-medium">Division</th>
                  <th className="px-4 py-2 font-medium">Subject</th>
                  <th className="px-4 py-2 font-medium">Weekly classes</th>
                </tr>
              </thead>
              <tbody>
                {detail.assignments.map((assignment, index) => (
                  <tr key={index} className="border-t border-content/10">
                    <td className="px-4 py-2">
                      {assignment.program_name} · Part-{assignment.part}
                      {assignment.semester ? ` (sem ${assignment.semester})` : ""} · {assignment.shift ?? "?"}
                      {assignment.group ? ` · ${assignment.group}` : ""}
                    </td>
                    <td className="px-4 py-2">
                      {assignment.course_name}
                      {assignment.is_lab && (
                        <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-content">
                          Lab
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2">{assignment.weekly_periods}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-content">Real weekly schedule</h3>
        {detail.schedule.length === 0 ? (
          <p className="mt-2 text-sm text-content/60">
            No timetable has been generated yet for any division this teacher is assigned to.
          </p>
        ) : (
          <>
            <p className="mt-1 text-xs text-content/60">
              From &quot;{detail.schedule_timetable_label}&quot; (timetable #{detail.schedule_timetable_id}), the
              most recently generated run that includes this teacher.
            </p>
            <div className="mt-2 overflow-x-auto rounded-xl ring-1 ring-content/15">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead className="bg-content/5 text-xs uppercase tracking-wide text-content/60">
                  <tr>
                    <th className="px-4 py-2 font-medium">Day</th>
                    <th className="px-4 py-2 font-medium">Time</th>
                    <th className="px-4 py-2 font-medium">Subject</th>
                    <th className="px-4 py-2 font-medium">Room</th>
                    <th className="px-4 py-2 font-medium">Division</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedSchedule.map((session, index) => (
                    <tr key={index} className="border-t border-content/10">
                      <td className="whitespace-nowrap px-4 py-2">{session.day}</td>
                      <td className="whitespace-nowrap px-4 py-2 font-mono text-xs">
                        {session.start_time.slice(0, 5)} - {session.end_time.slice(0, 5)}
                      </td>
                      <td className="px-4 py-2">
                        {session.course_name}
                        {session.is_lab && (
                          <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-content">
                            Lab
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2">{session.room_name}</td>
                      <td className="px-4 py-2">{session.division_labels.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
