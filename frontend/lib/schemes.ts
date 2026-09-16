/**
 * Types, lab pairing and API calls for the Course Scheme feature
 * (docs/PROJECT_ARCHITECTURE.md §3.5 and §7).
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
  lab_course_count: number;
};

export type SchemeDetail = SchemeSummary & {
  content: { semesters: SemesterRows[]; raw_text?: string };
  semesters: SemesterRows[];
};

const LAB_SUFFIX = /\s*\(\s*LAB\s*\)\s*$/i;

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

function normalizeName(name: string): string {
  // Case- and spacing-insensitive course name, used to match a lab row to its theory course.
  return name.trim().replace(/\s+/g, " ").toUpperCase();
}

export function labBaseName(name: string): string | null {
  // For a "NAME (LAB)" row, the theory course name it belongs to; null for an ordinary course.
  const match = LAB_SUFFIX.exec(name);
  return match ? normalizeName(name.slice(0, match.index)) : null;
}

export function pairLabRows(courses: CourseRow[]): CourseRow[] {
  // The same rule the backend applies on save: a "(LAB)" row is folded into the theory course
  // with the same name, becoming has_lab + lab_credit_hours there. A lab with no matching
  // theory course is kept as its own row rather than dropped.
  const rows = courses.map((course) => ({ ...course }));
  const theoryByName = new Map<string, CourseRow>();
  for (const row of rows) {
    const key = normalizeName(row.name);
    if (labBaseName(row.name) === null && !theoryByName.has(key)) theoryByName.set(key, row);
  }

  const paired: CourseRow[] = [];
  for (const row of rows) {
    const baseName = labBaseName(row.name);
    const theory = baseName === null ? undefined : theoryByName.get(baseName);
    if (baseName === null) {
      paired.push(row);
    } else if (theory) {
      theory.has_lab = true;
      theory.lab_credit_hours = row.credit_hours;
    } else {
      paired.push({ ...row, has_lab: true, lab_credit_hours: row.lab_credit_hours ?? row.credit_hours });
    }
  }
  return paired;
}

export function pairSemesters(semesters: SemesterRows[]): SemesterRows[] {
  // Applies lab pairing inside each semester; a lab never pairs across semesters.
  return semesters.map((semester) => ({ ...semester, courses: pairLabRows(semester.courses) }));
}

export function summarize(semesters: SemesterRows[]): { courses: number; labs: number; creditHours: number } {
  // Course count, lab-bearing course count and total credit hours (lab credits included).
  let courses = 0;
  let labs = 0;
  let creditHours = 0;
  for (const semester of semesters) {
    for (const course of semester.courses) {
      courses += 1;
      creditHours += course.credit_hours ?? 0;
      if (course.has_lab) {
        labs += 1;
        creditHours += course.lab_credit_hours ?? 0;
      }
    }
  }
  return { courses, labs, creditHours };
}

export function fetchDepartments(): Promise<Department[]> {
  // Departments with their programs; the form only offers the schedulable ones.
  return apiFetch<Department[]>("/api/v1/programs");
}

export function extractSchemeText(file: File): Promise<ExtractionResponse> {
  // Step 1: send the document up and get its text back. Nothing is saved yet.
  const form = new FormData();
  form.append("file", file);
  return apiUpload<ExtractionResponse>("/api/v1/course-schemes/extract", form);
}

export function saveScheme(params: {
  file: File;
  programId: number;
  schemeYear: number;
  semesters: SemesterRows[];
  rawText: string;
}): Promise<SchemeDetail> {
  // Final confirm: uploads the original file and saves the rows as entered in one request.
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

export function fetchSchemes(): Promise<SchemeSummary[]> {
  // Saved schemes for the list view, newest first.
  return apiFetch<SchemeSummary[]>("/api/v1/course-schemes");
}

export function fetchScheme(id: number): Promise<SchemeDetail> {
  // One saved scheme with its courses grouped by semester, labs already paired.
  return apiFetch<SchemeDetail>(`/api/v1/course-schemes/${id}`);
}

export function deleteScheme(id: number): Promise<SchemeSummary> {
  // Soft-deletes one scheme; the backend refuses if a published timetable uses it.
  return apiFetch<SchemeSummary>(`/api/v1/course-schemes/${id}`, { method: "DELETE" });
}
