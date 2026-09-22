/**
 * Types and API calls for triggering and viewing GA-generated timetables
 * (docs/PROJECT_ARCHITECTURE.md §6).
 */

import { apiFetch } from "@/lib/api-client";

export type GenerateResult = {
  timetable_id: number;
  label: string;
  status: string;
  converged: boolean;
  stagnated: boolean;
  fitness_score: number;
  generation_count: number;
  wall_seconds: number;
  session_count: number;
  conflict_list: string[];
};

export type TimetableSummary = {
  id: number;
  label: string;
  status: string;
  converged: boolean;
  fitness_score: number | null;
  generation_count: number | null;
  session_count: number;
  division_labels: string[];
  created_at: string;
};

export type SessionEntry = {
  start_time: string;
  end_time: string;
  course_code: string;
  course_name: string;
  teacher_name: string;
  room_name: string;
  is_lab: boolean;
  division_labels: string[];
};

export type DaySchedule = {
  day: string;
  sessions: SessionEntry[];
};

export type DivisionSchedule = {
  division_id: number;
  division_label: string;
  days: DaySchedule[];
};

export type TimetableDetail = TimetableSummary & {
  generation_params: Record<string, unknown>;
  conflict_list: string[];
  divisions: DivisionSchedule[];
};

export function generateTimetable(): Promise<GenerateResult> {
  // Triggers a real GA run for every BSCS Part-I to Part-IV division (the backend's
  // default when no division_ids are given) and waits for it to finish this can
  // genuinely take a while, which is why the caller shows a real waiting state.
  return apiFetch<GenerateResult>("/api/v1/timetables/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function fetchTimetables(): Promise<TimetableSummary[]> {
  // Every generated timetable, newest first.
  return apiFetch<TimetableSummary[]>("/api/v1/timetables");
}

export function fetchTimetable(id: number): Promise<TimetableDetail> {
  // One timetable's full schedule, already grouped by division/day/time by the backend.
  return apiFetch<TimetableDetail>(`/api/v1/timetables/${id}`);
}
