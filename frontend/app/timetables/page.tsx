"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { DivisionScheduleTable } from "@/components/timetables/division-schedule";
import { TimetableList } from "@/components/timetables/timetable-list";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api-client";
import {
  fetchTimetable,
  fetchTimetables,
  generateTimetable,
  type TimetableDetail,
  type TimetableSummary,
} from "@/lib/timetables";

type Stage = "list" | "detail";
type Notice = { tone: "success" | "error" | "warning"; text: string } | null;

// With the greedy starting population the full BSCS problem normally comes back in a few
// seconds, but a case the search can't solve cleanly still keeps trying for minutes before
// it gives up — so the note promises neither extreme and the elapsed timer covers the rest.
const EXPECTED_WAIT_NOTE =
  "This schedules all of BSCS Part-I to Part-IV at once — usually a few seconds, though a hard case can take a few minutes.";

function formatElapsed(seconds: number): string {
  // Turns a running second count into "1m 42s" for the generating indicator.
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}

export default function TimetablesPage() {
  const [stage, setStage] = useState<Stage>("list");
  const [timetables, setTimetables] = useState<TimetableSummary[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [detail, setDetail] = useState<TimetableDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [notice, setNotice] = useState<Notice>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadTimetables = useCallback(async () => {
    // Refreshes the saved-timetable list; used on first load and after every generation.
    setLoadingList(true);
    try {
      setTimetables(await fetchTimetables());
    } catch (cause) {
      setNotice({ tone: "error", text: `Couldn't load saved timetables. ${errorMessage(cause)}` });
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    // Load the saved-timetable list once the page mounts.
    void loadTimetables();
  }, [loadTimetables]);

  useEffect(() => {
    // Ticks a visible "how long has this been running" counter while generation is in
    // flight, so the button stays informative instead of just frozen on "Generating…".
    if (!generating) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    setElapsedSeconds(0);
    timerRef.current = setInterval(() => setElapsedSeconds((value) => value + 1), 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [generating]);

  async function handleGenerate() {
    // Kicks off a real GA run for every BSCS division and waits for the backend to finish.
    setGenerating(true);
    setNotice(null);
    try {
      const result = await generateTimetable();
      const outcome = result.converged
        ? `converged in ${result.generation_count} generations`
        : result.stagnated
          ? `stopped early — progress stalled after ${result.generation_count} generations`
          : `did not converge within ${result.generation_count} generations`;
      setNotice({
        tone: result.converged ? "success" : "warning",
        text: `Generation finished: ${outcome}, ${result.session_count} sessions placed in ${Math.round(result.wall_seconds)}s.${
          result.conflict_list.length > 0 ? ` ${result.conflict_list.length} conflict(s) remain — open it to review them.` : ""
        }`,
      });
      await loadTimetables();
      void handleView(result.timetable_id);
    } catch (cause) {
      setNotice({ tone: "error", text: `Generation failed. ${errorMessage(cause)}` });
    } finally {
      setGenerating(false);
    }
  }

  async function handleView(id: number) {
    // Loads one timetable's full schedule and switches to the detail view.
    setStage("detail");
    setLoadingDetail(true);
    setDetail(null);
    try {
      setDetail(await fetchTimetable(id));
    } catch (cause) {
      setNotice({ tone: "error", text: `Couldn't load that timetable. ${errorMessage(cause)}` });
      setStage("list");
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-content">Timetables</h1>
        <p className="mt-1 text-sm text-content/70">
          Generate a Genetic Algorithm timetable for BSCS Part-I to Part-IV, and browse what's been generated.
        </p>
      </header>

      {notice && (
        <div className="mb-4">
          <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
            {notice.text}
          </Alert>
        </div>
      )}

      {stage === "list" && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-content">Generate a new timetable</h2>
                <p className="mt-1 text-sm text-content/70">{EXPECTED_WAIT_NOTE}</p>
              </div>
              <Button onClick={handleGenerate} loading={generating} className="w-full sm:w-auto">
                {generating ? `Generating… ${formatElapsed(elapsedSeconds)}` : "Generate BSCS timetable"}
              </Button>
            </div>
          </div>

          <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
            <TimetableList timetables={timetables} loading={loadingList} onView={handleView} />
          </div>
        </div>
      )}

      {stage === "detail" && (
        <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
          <Button variant="secondary" onClick={() => setStage("list")} className="mb-4">
            ← Back to timetables
          </Button>

          {loadingDetail && <p className="text-sm text-content/60">Loading…</p>}

          {detail && (
            <div className="space-y-5">
              <div>
                <h2 className="text-lg font-semibold text-content">{detail.label}</h2>
                <p className="mt-1 text-sm text-content/70">
                  {detail.status} · {detail.converged ? "converged" : "not converged"} ·{" "}
                  {detail.session_count} sessions · {detail.generation_count ?? "?"} generations
                  {detail.fitness_score !== null && ` · fitness ${detail.fitness_score}`}
                </p>
              </div>

              {detail.conflict_list.length > 0 && (
                <Alert tone="warning">
                  {detail.conflict_list.length} unresolved conflict(s):
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {detail.conflict_list.slice(0, 10).map((line, index) => (
                      <li key={index}>{line}</li>
                    ))}
                  </ul>
                  {detail.conflict_list.length > 10 && (
                    <p className="mt-1 text-xs text-content/60">
                      +{detail.conflict_list.length - 10} more not shown.
                    </p>
                  )}
                </Alert>
              )}

              <div className="space-y-4">
                {detail.divisions.map((schedule) => (
                  <DivisionScheduleTable key={schedule.division_id} schedule={schedule} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
