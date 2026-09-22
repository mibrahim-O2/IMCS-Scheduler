/**
 * Types and API calls for the Phase 9 data-entry dashboard: teachers, classrooms,
 * divisions, and the draft course assignments that get finalized into a real GA run.
 * See docs/PROJECT_ARCHITECTURE.md §3.2, §3.3, §3.4 and docs/PROJECT_AUDIT.md Phase 9.
 */

import { API_BASE_URL, apiFetch } from "@/lib/api-client";

export type Teacher = {
  id: number;
  full_name: string;
  designation: string | null;
  home_program_id: number | null;
  availability: { days?: string[] };
};

export type Classroom = {
  id: number;
  name: string;
  type: string;
  capacity: number | null;
};

export type Division = {
  id: number;
  program_id: number;
  part: number;
  semester: number | null;
  shift: string | null;
  group: string | null;
  label: string;
  home_room_id: number | null;
  assignments_locked_at: string | null;
};

export type CourseListItem = {
  id: number;
  scheme_id: number;
  code: string;
  name: string;
  credit_hours: number | null;
  semester: number | null;
  has_lab: boolean;
  lab_credit_hours: number | null;
};

export type CourseAssignment = {
  id: number;
  division_id: number;
  course_id: number;
  course_code: string;
  course_name: string;
  teacher_id: number;
  teacher_name: string;
  weekly_theory_periods: number;
  has_lab: boolean;
  lab_teacher_id: number | null;
  weekly_lab_periods: number | null;
  lecture_room_id: number | null;
  lab_room_id: number | null;
  joint_division_id: number | null;
};

export type TeacherConflict = { conflict: boolean; message: string | null };

export type FinalizeResult = {
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

export function fetchTeachers(programId?: number): Promise<Teacher[]> {
  // Every teacher on record, optionally narrowed to one home program for the dropdown.
  const query = programId ? `?program_id=${programId}` : "";
  return apiFetch<Teacher[]>(`/api/v1/teachers${query}`);
}

export function createTeacher(fullName: string, days: string[]): Promise<Teacher> {
  // The dashboard's inline "add new teacher" a plain create, no program pinned yet.
  return apiFetch<Teacher>("/api/v1/teachers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, availability: { days } }),
  });
}

export function fetchClassrooms(type?: string): Promise<Classroom[]> {
  // Every classroom, optionally narrowed by type ("lab" for the Lab A-E dropdown).
  const query = type ? `?type=${type}` : "";
  return apiFetch<Classroom[]>(`/api/v1/classrooms${query}`);
}

export function createClassroom(name: string, type: string): Promise<Classroom> {
  // The dashboard's inline "add new room" for a lecture room the list doesn't have yet.
  return apiFetch<Classroom>("/api/v1/classrooms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, type }),
  });
}

export function fetchCourses(programId: number, semester: number): Promise<CourseListItem[]> {
  // A program's course list for one semester, from its active Course Scheme plus anything
  // added through the "add a new subject" quick-create below.
  return apiFetch<CourseListItem[]>(`/api/v1/courses?program_id=${programId}&semester=${semester}`);
}

export function addSubject(
  programId: number,
  semester: number,
  name: string,
  creditHours: number | null,
  hasLab: boolean,
  labCreditHours: number | null,
): Promise<CourseListItem> {
  // Creates a minimal Course row without a full Course Scheme upload, for when the official
  // document hasn't been uploaded yet (docs/PROJECT_ARCHITECTURE.md §11.2).
  return apiFetch<CourseListItem>("/api/v1/courses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      program_id: programId, semester, name, credit_hours: creditHours,
      has_lab: hasLab, lab_credit_hours: labCreditHours,
    }),
  });
}

export function findOrCreateDivision(
  programId: number, part: number, semester: number, shift: string, group: string | null,
): Promise<Division> {
  // Get-or-create: re-selecting the same program/part/semester/shift/group combination
  // always returns the same division instead of failing on a duplicate.
  return apiFetch<Division>("/api/v1/divisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ program_id: programId, part, semester, shift, group }),
  });
}

export function fetchDivision(divisionId: number): Promise<Division> {
  // One division's own record, used after finalizing to confirm it's now locked.
  return apiFetch<Division>(`/api/v1/divisions/${divisionId}`);
}

export function fetchAssignments(divisionId: number): Promise<CourseAssignment[]> {
  // The division's current draft (or finalized) course list.
  return apiFetch<CourseAssignment[]>(`/api/v1/divisions/${divisionId}/courses`);
}

export function checkTeacherConflict(divisionId: number, teacherId: number, courseId: number): Promise<TeacherConflict> {
  // Constraint 9's live pre-check called as the admin picks a teacher, before "Add to list".
  return apiFetch<TeacherConflict>(
    `/api/v1/divisions/${divisionId}/courses/check-teacher?teacher_id=${teacherId}&course_id=${courseId}`,
  );
}

export function addAssignment(
  divisionId: number, courseId: number, teacherId: number, lectureRoomId: number, labRoomId: number | null,
): Promise<CourseAssignment> {
  // Adds one course+teacher+rooms row to the division's draft list.
  return apiFetch<CourseAssignment>(`/api/v1/divisions/${divisionId}/courses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      course_id: courseId, teacher_id: teacherId, lecture_room_id: lectureRoomId, lab_room_id: labRoomId,
    }),
  });
}

export function updateAssignment(
  divisionId: number,
  assignmentId: number,
  patch: { teacher_id?: number; lecture_room_id?: number; lab_room_id?: number },
): Promise<CourseAssignment> {
  // Edits a draft row's teacher and/or rooms only allowed before the division is finalized.
  return apiFetch<CourseAssignment>(`/api/v1/divisions/${divisionId}/courses/${assignmentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}

export function removeAssignment(divisionId: number, assignmentId: number): Promise<void> {
  // Drops one draft row only allowed before the division is finalized.
  return apiFetch<void>(`/api/v1/divisions/${divisionId}/courses/${assignmentId}`, { method: "DELETE" });
}

export function finalizeDivision(divisionId: number): Promise<FinalizeResult> {
  // Locks the assignment list and runs the real GA for this division.
  return apiFetch<FinalizeResult>(`/api/v1/divisions/${divisionId}/finalize`, { method: "POST" });
}

export function exportUrl(timetableId: number): string {
  // The direct download link for a finalized timetable's Word export a plain URL (not a
  // fetch call), since the browser should handle the file download itself. Built from the
  // same API_BASE_URL every other call in this app resolves to (api-client.ts), so it still
  // points at the right host when opened from another device on the LAN.
  return `${API_BASE_URL}/api/v1/timetables/${timetableId}/export`;
}
