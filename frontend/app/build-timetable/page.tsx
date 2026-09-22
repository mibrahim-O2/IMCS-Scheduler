"use client";

import { useCallback, useEffect, useState } from "react";

import { AssignmentList } from "@/components/build-timetable/assignment-list";
import { CourseAssignmentForm } from "@/components/build-timetable/course-assignment-form";
import { FinalizePanel } from "@/components/build-timetable/finalize-panel";
import { SelectionStep } from "@/components/build-timetable/selection-step";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api-client";
import {
  addAssignment,
  addSubject,
  checkTeacherConflict,
  createClassroom,
  createTeacher,
  fetchAssignments,
  fetchClassrooms,
  fetchCourses,
  fetchDivision,
  fetchTeachers,
  finalizeDivision,
  findOrCreateDivision,
  removeAssignment,
  updateAssignment,
  type Classroom,
  type CourseAssignment,
  type CourseListItem,
  type Division,
  type FinalizeResult,
  type Teacher,
} from "@/lib/build-timetable";
import { fetchDepartments, type Program } from "@/lib/schemes";
import { fetchTimetable, type TimetableDetail } from "@/lib/timetables";

type Notice = { tone: "success" | "error" | "warning"; text: string } | null;

// The Phase 9 data-entry dashboard: build up one division's course/teacher/room
// assignments by hand, for any schedulable program, then finalize into a real GA run.
export default function BuildTimetablePage() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [notice, setNotice] = useState<Notice>(null);

  const [programId, setProgramId] = useState<number | null>(null);
  const [shift, setShift] = useState("Morning");
  const [part, setPart] = useState(1);
  const [semesterHalf, setSemesterHalf] = useState<"first" | "second">("first");
  const [group, setGroup] = useState("PM");
  const [starting, setStarting] = useState(false);

  const [division, setDivision] = useState<Division | null>(null);
  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [rooms, setRooms] = useState<Classroom[]>([]);
  const [assignments, setAssignments] = useState<CourseAssignment[]>([]);

  const [finalizing, setFinalizing] = useState(false);
  const [finalizeResult, setFinalizeResult] = useState<FinalizeResult | null>(null);
  const [timetableDetail, setTimetableDetail] = useState<TimetableDetail | null>(null);

  useEffect(() => {
    // Loads every schedulable program once, for the Program picker non-schedulable
    // levels (Master, PhD, ...) never get a Division, so they're left out.
    fetchDepartments()
      .then((departments) => setPrograms(departments.flatMap((d) => d.programs).filter((p) => p.is_schedulable)))
      .catch((cause) => setNotice({ tone: "error", text: `Couldn't load programs. ${errorMessage(cause)}` }));
  }, []);

  const loadDivisionData = useCallback(async (target: Division) => {
    // Everything the assignment form and list need for this division: its semester's
    // courses, every teacher and classroom, and its current draft assignment list.
    try {
      const [courseList, teacherList, roomList, assignmentList] = await Promise.all([
        fetchCourses(target.program_id, target.semester ?? 1),
        fetchTeachers(),
        fetchClassrooms(),
        fetchAssignments(target.id),
      ]);
      setCourses(courseList);
      setTeachers(teacherList);
      setRooms(roomList);
      setAssignments(assignmentList);
    } catch (cause) {
      setNotice({ tone: "error", text: `Couldn't load this division's data. ${errorMessage(cause)}` });
    }
  }, []);

  async function handleStart() {
    // Creates (or finds) the division for the chosen combination and loads its data.
    if (programId === null) return;
    const selectedProgram = programs.find((program) => program.id === programId);
    const usesGroup = selectedProgram !== undefined && !selectedProgram.display_name.includes("Mathematics");
    const semester = part * 2 - (semesterHalf === "first" ? 1 : 0);

    setStarting(true);
    setNotice(null);
    try {
      const created = await findOrCreateDivision(programId, part, semester, shift, usesGroup ? group : null);
      setDivision(created);
      setFinalizeResult(null);
      setTimetableDetail(null);
      await loadDivisionData(created);
    } catch (cause) {
      setNotice({ tone: "error", text: errorMessage(cause) });
    } finally {
      setStarting(false);
    }
  }

  function handleStartOver() {
    // Drops back to the selection step for a different division, keeping the picked
    // program/shift/part around since the admin is often about to do the sibling group next.
    setDivision(null);
    setAssignments([]);
    setFinalizeResult(null);
    setTimetableDetail(null);
  }

  async function handleAddAssignment(courseId: number, teacherId: number, lectureRoomId: number, labRoomId: number | null) {
    // Adds one row, then refreshes the draft list from the server (the source of truth).
    if (!division) return;
    await addAssignment(division.id, courseId, teacherId, lectureRoomId, labRoomId);
    setAssignments(await fetchAssignments(division.id));
  }

  async function handleUpdateAssignment(assignmentId: number, patch: { teacher_id?: number; lecture_room_id?: number; lab_room_id?: number }) {
    // Edits one row's teacher and/or rooms, then refreshes the draft list from the server.
    if (!division) return;
    await updateAssignment(division.id, assignmentId, patch);
    setAssignments(await fetchAssignments(division.id));
  }

  async function handleRemoveAssignment(assignmentId: number) {
    // Drops one draft row, then refreshes the list from the server.
    if (!division) return;
    await removeAssignment(division.id, assignmentId);
    setAssignments(await fetchAssignments(division.id));
  }

  async function handleFinalize() {
    // Locks the list, runs the real GA, and loads the result for display.
    if (!division) return;
    setFinalizing(true);
    setNotice(null);
    try {
      const result = await finalizeDivision(division.id);
      setFinalizeResult(result);
      setTimetableDetail(await fetchTimetable(result.timetable_id));
      // Re-fetches the division rather than hand-constructing the locked state locally, so
      // what the page shows is exactly what the server now has, not an optimistic guess.
      setDivision(await fetchDivision(division.id));
    } catch (cause) {
      setNotice({ tone: "error", text: `Finalize failed. ${errorMessage(cause)}` });
    } finally {
      setFinalizing(false);
    }
  }

  const lectureRooms = rooms.filter((room) => room.type !== "lab");
  const labRooms = rooms.filter((room) => room.type === "lab");
  const locked = division?.assignments_locked_at != null;

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-content">Build a timetable</h1>
        <p className="mt-1 text-sm text-content/70">
          Enter courses, teachers and rooms by hand for any program, then generate a real
          GA timetable for that one division. For BSCS Morning, the existing seed data
          already covers this use this page for BS(AI), Mathematics, or the Evening shift.
        </p>
      </header>

      {notice && (
        <div className="mb-4">
          <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
            {notice.text}
          </Alert>
        </div>
      )}

      {!division ? (
        <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
          <SelectionStep
            programs={programs}
            programId={programId}
            shift={shift}
            part={part}
            semesterHalf={semesterHalf}
            group={group}
            onChangeProgram={setProgramId}
            onChangeShift={setShift}
            onChangePart={setPart}
            onChangeSemesterHalf={setSemesterHalf}
            onChangeGroup={setGroup}
            onStart={handleStart}
            starting={starting}
          />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-col gap-3 rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:flex-row sm:items-center sm:justify-between sm:p-6">
            <div>
              <p className="font-semibold text-content">{division.label}</p>
              <p className="text-sm text-content/70">
                Semester {division.semester} · {assignments.length} course{assignments.length === 1 ? "" : "s"} added
                {locked && " · Locked"}
              </p>
            </div>
            <Button variant="secondary" onClick={handleStartOver} className="w-full sm:w-auto">
              Build a different division
            </Button>
          </div>

          {!locked && (
            <CourseAssignmentForm
              courses={courses}
              teachers={teachers}
              lectureRooms={lectureRooms}
              labRooms={labRooms}
              onAddSubject={async (name, creditHours, hasLab, labCreditHours) => {
                const created = await addSubject(division.program_id, division.semester ?? 1, name, creditHours, hasLab, labCreditHours);
                setCourses((current) => [...current, created]);
                return created;
              }}
              onAddTeacher={async (name, days) => {
                const created = await createTeacher(name, days);
                setTeachers((current) => [...current, created]);
                return created;
              }}
              onAddRoom={async (name) => {
                const created = await createClassroom(name, "lecture");
                setRooms((current) => [...current, created]);
                return created;
              }}
              onCheckConflict={(teacherId, courseId) => checkTeacherConflict(division.id, teacherId, courseId)}
              onAdd={handleAddAssignment}
            />
          )}

          <div>
            <h2 className="mb-2 text-sm font-semibold text-content">9. Draft assignments</h2>
            <AssignmentList
              assignments={assignments}
              teachers={teachers}
              lectureRooms={lectureRooms}
              labRooms={labRooms}
              locked={locked}
              onUpdate={handleUpdateAssignment}
              onRemove={handleRemoveAssignment}
            />
          </div>

          <FinalizePanel
            assignmentCount={assignments.length}
            locked={locked}
            finalizing={finalizing}
            result={finalizeResult}
            detail={timetableDetail}
            onFinalize={handleFinalize}
          />
        </div>
      )}
    </main>
  );
}
