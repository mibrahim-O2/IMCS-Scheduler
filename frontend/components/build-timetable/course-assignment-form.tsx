"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { CheckboxInput, NumberInput, SelectInput, TextInput } from "@/components/ui/field";
import { errorMessage } from "@/lib/api-client";
import type { Classroom, CourseListItem, Teacher } from "@/lib/build-timetable";

const DAY_OPTIONS = ["Mon", "Tue", "Wed", "Thu", "Fri"];

// Steps 3-8: pick (or quick-create) a course and teacher, pick rooms, add the row to the
// division's draft list. Everything the admin needs for one course lives in this one form;
// they repeat it once per course in the division.
export function CourseAssignmentForm({
  courses,
  teachers,
  lectureRooms,
  labRooms,
  onAddSubject,
  onAddTeacher,
  onAddRoom,
  onCheckConflict,
  onAdd,
}: {
  courses: CourseListItem[];
  teachers: Teacher[];
  lectureRooms: Classroom[];
  labRooms: Classroom[];
  onAddSubject: (name: string, creditHours: number | null, hasLab: boolean, labCreditHours: number | null) => Promise<CourseListItem>;
  onAddTeacher: (name: string, days: string[]) => Promise<Teacher>;
  onAddRoom: (name: string) => Promise<Classroom>;
  onCheckConflict: (teacherId: number, courseId: number) => Promise<{ conflict: boolean; message: string | null }>;
  onAdd: (courseId: number, teacherId: number, lectureRoomId: number, labRoomId: number | null) => Promise<void>;
}) {
  const [courseId, setCourseId] = useState<number | "">("");
  const [teacherId, setTeacherId] = useState<number | "">("");
  const [lectureRoomId, setLectureRoomId] = useState<number | "">("");
  const [labRoomId, setLabRoomId] = useState<number | "">("");
  const [conflictMessage, setConflictMessage] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showNewSubject, setShowNewSubject] = useState(false);
  const [newSubjectName, setNewSubjectName] = useState("");
  const [newSubjectCredits, setNewSubjectCredits] = useState<number | null>(3);
  const [newSubjectHasLab, setNewSubjectHasLab] = useState(false);
  const [newSubjectLabCredits, setNewSubjectLabCredits] = useState<number | null>(1);

  const [showNewTeacher, setShowNewTeacher] = useState(false);
  const [newTeacherName, setNewTeacherName] = useState("");
  const [newTeacherDays, setNewTeacherDays] = useState<string[]>([]);

  const [showNewRoom, setShowNewRoom] = useState(false);
  const [newRoomName, setNewRoomName] = useState("");

  const selectedCourse = courses.find((course) => course.id === courseId) ?? null;

  async function handleCreateSubject() {
    // Quick-creates a Course row for a subject that isn't in the dropdown yet (no official
    // Course Scheme uploaded), then selects it immediately.
    if (!newSubjectName.trim()) return;
    setError(null);
    try {
      const created = await onAddSubject(
        newSubjectName.trim(), newSubjectCredits, newSubjectHasLab, newSubjectHasLab ? newSubjectLabCredits : null,
      );
      setCourseId(created.id);
      setShowNewSubject(false);
      setNewSubjectName("");
      setNewSubjectCredits(3);
      setNewSubjectHasLab(false);
      setNewSubjectLabCredits(1);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  async function handleCreateTeacher() {
    // Quick-creates a Teacher row, then selects it immediately.
    if (!newTeacherName.trim()) return;
    setError(null);
    try {
      const created = await onAddTeacher(newTeacherName.trim(), newTeacherDays);
      setTeacherId(created.id);
      setShowNewTeacher(false);
      setNewTeacherName("");
      setNewTeacherDays([]);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  async function handleCreateRoom() {
    // Quick-creates a lecture-type Classroom row for a brand-new program that has no rooms
    // entered yet, then selects it immediately.
    if (!newRoomName.trim()) return;
    setError(null);
    try {
      const created = await onAddRoom(newRoomName.trim());
      setLectureRoomId(created.id);
      setShowNewRoom(false);
      setNewRoomName("");
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  async function handleTeacherChange(value: string) {
    // Picking a teacher immediately checks constraint 9 against this division, so the
    // warning shows before the admin even tries to add the row.
    const id = value === "" ? "" : Number(value);
    setTeacherId(id);
    setConflictMessage(null);
    if (id === "" || courseId === "") return;
    try {
      const result = await onCheckConflict(id, courseId as number);
      if (result.conflict) setConflictMessage(result.message);
    } catch {
      // A failed live check isn't worth blocking the form over the server still enforces
      // constraint 9 for real when "Add to list" is pressed.
    }
  }

  async function handleAdd() {
    if (courseId === "" || teacherId === "" || lectureRoomId === "") return;
    setError(null);
    setAdding(true);
    try {
      await onAdd(courseId, teacherId, lectureRoomId, selectedCourse?.has_lab ? (labRoomId || null) : null);
      setCourseId("");
      setTeacherId("");
      setLectureRoomId("");
      setLabRoomId("");
      setConflictMessage(null);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setAdding(false);
    }
  }

  const canAdd = courseId !== "" && teacherId !== "" && lectureRoomId !== "" && (!selectedCourse?.has_lab || labRoomId !== "");

  return (
    <section className="space-y-4 rounded-xl bg-surface p-4 ring-1 ring-content/15">
      <h3 className="text-sm font-semibold text-content">Add a course</h3>

      {error && (
        <Alert tone="error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SelectInput
          label="Course"
          value={courseId}
          onChange={(value) => {
            setCourseId(value === "" ? "" : Number(value));
            setLabRoomId("");
            setConflictMessage(null);
          }}
          options={[
            { value: "", label: courses.length ? "Choose a course…" : "No courses yet for this semester" },
            ...courses.map((course) => ({ value: course.id, label: `${course.code} ${course.name}` })),
          ]}
        />
        <div className="flex items-end">
          <Button variant="secondary" className="w-full" onClick={() => setShowNewSubject((value) => !value)}>
            {showNewSubject ? "Cancel new subject" : "+ Add a new subject"}
          </Button>
        </div>
      </div>

      {showNewSubject && (
        <div className="grid grid-cols-1 gap-3 rounded-lg bg-card p-3 ring-1 ring-content/10 sm:grid-cols-2">
          <TextInput label="Subject name" value={newSubjectName} onChange={setNewSubjectName} placeholder="e.g. Linear Algebra" />
          <NumberInput label="Credit hours" value={newSubjectCredits} onChange={setNewSubjectCredits} />
          <CheckboxInput label="Has a lab" checked={newSubjectHasLab} onChange={setNewSubjectHasLab} />
          {newSubjectHasLab && (
            <NumberInput label="Lab credit hours" value={newSubjectLabCredits} onChange={setNewSubjectLabCredits} />
          )}
          <Button className="sm:col-span-2" onClick={handleCreateSubject} disabled={!newSubjectName.trim()}>
            Create subject
          </Button>
        </div>
      )}

      {selectedCourse && (
        <p className="text-xs text-content/70">
          Number of classes: <span className="font-medium text-content">{selectedCourse.credit_hours ?? 0} theory / week</span>
          {selectedCourse.has_lab && (
            <span className="font-medium text-content"> + {selectedCourse.lab_credit_hours ?? 1} lab / week</span>
          )}{" "}
 from the course's credit hours, not typed by hand.
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SelectInput
          label="Teacher"
          value={teacherId}
          onChange={handleTeacherChange}
          options={[
            { value: "", label: "Choose a teacher…" },
            ...teachers.map((teacher) => ({ value: teacher.id, label: teacher.full_name })),
          ]}
        />
        <div className="flex items-end">
          <Button variant="secondary" className="w-full" onClick={() => setShowNewTeacher((value) => !value)}>
            {showNewTeacher ? "Cancel new teacher" : "+ Add a new teacher"}
          </Button>
        </div>
      </div>

      {conflictMessage && <Alert tone="warning">{conflictMessage}</Alert>}

      {showNewTeacher && (
        <div className="space-y-3 rounded-lg bg-card p-3 ring-1 ring-content/10">
          <TextInput label="Teacher name" value={newTeacherName} onChange={setNewTeacherName} placeholder="e.g. Dr. Jane Smith" />
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-content/60">Available days</p>
            <div className="mt-1 flex flex-wrap gap-3">
              {DAY_OPTIONS.map((day) => (
                <CheckboxInput
                  key={day}
                  label={day}
                  checked={newTeacherDays.includes(day)}
                  onChange={(checked) =>
                    setNewTeacherDays((days) => (checked ? [...days, day] : days.filter((d) => d !== day)))
                  }
                />
              ))}
            </div>
          </div>
          <Button onClick={handleCreateTeacher} disabled={!newTeacherName.trim()}>
            Create teacher
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SelectInput
          label="Lecture room"
          value={lectureRoomId}
          onChange={(value) => setLectureRoomId(value === "" ? "" : Number(value))}
          options={[
            { value: "", label: lectureRooms.length ? "Choose a room…" : "No rooms entered yet" },
            ...lectureRooms.map((room) => ({ value: room.id, label: room.name })),
          ]}
        />
        <div className="flex items-end">
          <Button variant="secondary" className="w-full" onClick={() => setShowNewRoom((value) => !value)}>
            {showNewRoom ? "Cancel new room" : "+ Add a new room"}
          </Button>
        </div>
      </div>

      {showNewRoom && (
        <div className="flex flex-col gap-3 rounded-lg bg-card p-3 ring-1 ring-content/10 sm:flex-row sm:items-end">
          <div className="flex-1">
            <TextInput label="Room name" value={newRoomName} onChange={setNewRoomName} placeholder="e.g. AI Room 01" />
          </div>
          <Button onClick={handleCreateRoom} disabled={!newRoomName.trim()}>
            Create room
          </Button>
        </div>
      )}

      {selectedCourse?.has_lab && (
        <SelectInput
          label="Lab room (fixes this session's lab ahead of generation)"
          value={labRoomId}
          onChange={(value) => setLabRoomId(value === "" ? "" : Number(value))}
          options={[
            { value: "", label: "Choose a lab…" },
            ...labRooms.map((room) => ({ value: room.id, label: room.name })),
          ]}
        />
      )}

      <Button onClick={handleAdd} loading={adding} disabled={!canAdd} className="w-full sm:w-auto">
        Add to list
      </Button>
    </section>
  );
}
