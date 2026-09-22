/**
 * Types and API calls for the Phase 10 teacher lookup page: search by name, then view one
 * teacher's full record their Division assignments and, if one exists, their real
 * generated weekly schedule. See docs/PROJECT_ARCHITECTURE.md §3.4.
 */

import { apiFetch } from "@/lib/api-client";

export type Teacher = {
  id: number;
  full_name: string;
  designation: string | null;
  home_program_id: number | null;
  availability: { days?: string[] };
};

export type TeacherAssignment = {
  division_id: number;
  division_label: string;
  program_name: string;
  part: number;
  semester: number | null;
  shift: string | null;
  group: string | null;
  course_name: string;
  is_lab: boolean;
  weekly_periods: number;
};

export type TeacherScheduleSession = {
  day: string;
  start_time: string;
  end_time: string;
  course_name: string;
  room_name: string;
  division_labels: string[];
  is_lab: boolean;
};

export type TeacherDetail = Teacher & {
  assignments: TeacherAssignment[];
  schedule: TeacherScheduleSession[];
  schedule_timetable_id: number | null;
  schedule_timetable_label: string | null;
};

export function searchTeachers(query: string): Promise<Teacher[]> {
  // The lookup page's type-ahead: a blank query returns every teacher (used to show a
  // starting list before the admin types anything).
  const params = query.trim() ? `?search=${encodeURIComponent(query.trim())}` : "";
  return apiFetch<Teacher[]>(`/api/v1/teachers${params}`);
}

export function fetchTeacherDetail(id: number): Promise<TeacherDetail> {
  // One teacher's combined record: profile, assignments, and real schedule if one exists.
  return apiFetch<TeacherDetail>(`/api/v1/teachers/${id}`);
}
