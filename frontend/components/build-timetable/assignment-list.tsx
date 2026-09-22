"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { SelectInput } from "@/components/ui/field";
import type { Classroom, CourseAssignment, Teacher } from "@/lib/build-timetable";

// Step 9: the division's current draft list, live every row the admin has added so far,
// each one editable (teacher/rooms) or removable, until the division is finalized.
export function AssignmentList({
  assignments,
  teachers,
  lectureRooms,
  labRooms,
  locked,
  onUpdate,
  onRemove,
}: {
  assignments: CourseAssignment[];
  teachers: Teacher[];
  lectureRooms: Classroom[];
  labRooms: Classroom[];
  locked: boolean;
  onUpdate: (assignmentId: number, patch: { teacher_id?: number; lecture_room_id?: number; lab_room_id?: number }) => Promise<void>;
  onRemove: (assignmentId: number) => Promise<void>;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  if (assignments.length === 0) {
    return (
      <p className="rounded-lg bg-surface p-4 text-sm text-content/60 ring-1 ring-content/15">
        No courses added yet use the form above to add the first one.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {assignments.map((assignment) => (
        <li key={assignment.id} className="rounded-lg bg-surface p-3 ring-1 ring-content/15">
          {editingId === assignment.id ? (
            <EditRow
              assignment={assignment}
              teachers={teachers}
              lectureRooms={lectureRooms}
              labRooms={labRooms}
              saving={busyId === assignment.id}
              onCancel={() => setEditingId(null)}
              onSave={async (patch) => {
                setBusyId(assignment.id);
                try {
                  await onUpdate(assignment.id, patch);
                  setEditingId(null);
                } finally {
                  setBusyId(null);
                }
              }}
            />
          ) : (
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="font-medium text-content">
                  {assignment.course_code} {assignment.course_name}
                </p>
                <p className="text-xs text-content/70">
                  {assignment.teacher_name} · {assignment.weekly_theory_periods} theory/wk
                  {assignment.has_lab && ` + ${assignment.weekly_lab_periods} lab/wk`}
                  {assignment.has_lab && assignment.lab_room_id && " (lab room fixed)"}
                </p>
              </div>
              {!locked && (
                <div className="flex shrink-0 gap-2">
                  <Button variant="secondary" onClick={() => setEditingId(assignment.id)} className="min-h-9 px-3 py-1 text-xs">
                    Edit
                  </Button>
                  <Button
                    variant="danger"
                    loading={busyId === assignment.id}
                    onClick={async () => {
                      setBusyId(assignment.id);
                      try {
                        await onRemove(assignment.id);
                      } finally {
                        setBusyId(null);
                      }
                    }}
                    className="min-h-9 px-3 py-1 text-xs"
                  >
                    Remove
                  </Button>
                </div>
              )}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

function EditRow({
  assignment,
  teachers,
  lectureRooms,
  labRooms,
  saving,
  onSave,
  onCancel,
}: {
  assignment: CourseAssignment;
  teachers: Teacher[];
  lectureRooms: Classroom[];
  labRooms: Classroom[];
  saving: boolean;
  onSave: (patch: { teacher_id?: number; lecture_room_id?: number; lab_room_id?: number }) => Promise<void>;
  onCancel: () => void;
}) {
  // A small inline form replacing the row's display while it's being edited teacher and
  // room only, since the course itself isn't editable this way (remove and re-add instead).
  const [teacherId, setTeacherId] = useState(assignment.teacher_id);
  const [lectureRoomId, setLectureRoomId] = useState(assignment.lecture_room_id ?? "");
  const [labRoomId, setLabRoomId] = useState(assignment.lab_room_id ?? "");

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-content">
        Editing {assignment.course_code} {assignment.course_name}
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SelectInput
          label="Teacher"
          value={teacherId}
          onChange={(value) => setTeacherId(Number(value))}
          options={teachers.map((teacher) => ({ value: teacher.id, label: teacher.full_name }))}
        />
        <SelectInput
          label="Lecture room"
          value={lectureRoomId}
          onChange={(value) => setLectureRoomId(Number(value))}
          options={lectureRooms.map((room) => ({ value: room.id, label: room.name }))}
        />
        {assignment.has_lab && (
          <SelectInput
            label="Lab room"
            value={labRoomId}
            onChange={(value) => setLabRoomId(Number(value))}
            options={labRooms.map((room) => ({ value: room.id, label: room.name }))}
          />
        )}
      </div>
      <div className="flex gap-2">
        <Button
          loading={saving}
          onClick={() =>
            onSave({
              teacher_id: teacherId,
              lecture_room_id: lectureRoomId === "" ? undefined : Number(lectureRoomId),
              lab_room_id: labRoomId === "" ? undefined : Number(labRoomId),
            })
          }
        >
          Save
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
