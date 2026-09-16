/**
 * Types and API calls for the Course Scheme feature (docs/PROJECT_ARCHITECTURE.md §7).
 */

import { apiFetch, apiUpload } from "@/lib/api-client";

export type Program = {
  id: number;
  level: string;
  display_name: string;
  total_semesters: number | null;
  is_schedulable: boolean;
};

export type Department = {
  id: number;
  name: string;
  short_code: string;
  display_order: number;
  programs: Program[];
};

export type ExtractionResponse = {
  filename: string;
  method: string;
  page_count: number;
  character_count: number;
  text: string;
  warnings: string[];
};

export type CourseRow = {
  code: string;
  name: string;
  credit_hours: number | null;
  has_lab: boolean;
  lab_credit_hours: number | null;
  min_marks: number | null;
  max_marks: number | null;
};

export type SemesterRows = {
  semester: number;
  courses: CourseRow[];
};

export type SchemeSummary = {
  id: number;
  program_id: number;
  program_name: string;
  scheme_year: number;
  source_filename: string | null;
  file_url: string | null;
  uploaded_at: string;
  is_active: boolean;
  course_count: number;
};

export type SchemeDetail = SchemeSummary & {
  content: { semesters: SemesterRows[]; raw_text?: string };
};

export function emptyCourse(): CourseRow {
  // A blank row for the structured form to start from.
  return {
    code: "",
    name: "",
    credit_hours: null,
    has_lab: false,
    lab_credit_hours: null,
    min_marks: 50,
    max_marks: 100,
  };
}

export function countCourses(semesters: SemesterRows[]): number {
  // Total course rows across every semester, used in the preview and save button.
  return semesters.reduce((total, semester) => total + semester.courses.length, 0);
}

export async function fetchDepartments(): Promise<Department[]> {
  // Departments with their programs; the form only offers the schedulable ones.
  return apiFetch<Department[]>("/api/v1/programs");
}

export async function extractSchemeText(file: File): Promise<ExtractionResponse> {
  // Step 1: send the document up and get its text back. Nothing is saved yet.
  const form = new FormData();
  form.append("file", file);
  return apiUpload<ExtractionResponse>("/api/v1/course-schemes/extract", form);
}

export async function saveScheme(params: {
  file: File;
  programId: number;
  schemeYear: number;
  semesters: SemesterRows[];
  rawText: string;
}): Promise<SchemeDetail> {
  // Final confirm: uploads the original file and saves the structured rows in one request.
  const form = new FormData();
  form.append("file", params.file);
  form.append(
    "payload",
    JSON.stringify({
      program_id: params.programId,
      scheme_year: params.schemeYear,
      content: { semesters: params.semesters },
      raw_text: params.rawText,
    }),
  );
  return apiUpload<SchemeDetail>("/api/v1/course-schemes", form);
}

export async function fetchSchemes(): Promise<SchemeSummary[]> {
  // Saved schemes for the list view, newest first.
  return apiFetch<SchemeSummary[]>("/api/v1/course-schemes");
}

export async function deleteScheme(id: number): Promise<SchemeSummary> {
  // Soft-deletes one scheme; the backend refuses if a published timetable uses it.
  return apiFetch<SchemeSummary>(`/api/v1/course-schemes/${id}`, { method: "DELETE" });
}
