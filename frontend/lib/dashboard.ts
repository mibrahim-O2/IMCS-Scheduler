/**
 * Types and API call for the stats overview (docs/PROJECT_ARCHITECTURE.md §8).
 * Counts only — this is not a teacher or room availability view.
 */

import { apiFetch } from "@/lib/api-client";

export type SchemeBreakdown = {
  scheme_id: number;
  program_name: string;
  scheme_year: number;
  course_count: number;
  lab_course_count: number;
};

export type DashboardStats = {
  departments: number;
  programs: { total: number; schedulable: number; not_yet_schedulable: number };
  course_schemes: number;
  scheme_breakdown: SchemeBreakdown[];
  courses: { total: number; with_lab: number };
  classrooms: number;
  teachers: number;
  generated_at: string;
};

export function fetchDashboardStats(): Promise<DashboardStats> {
  // Current counts, computed by the backend when this is called.
  return apiFetch<DashboardStats>("/api/v1/dashboard/stats");
}
