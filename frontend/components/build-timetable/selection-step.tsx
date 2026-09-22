"use client";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { SelectInput } from "@/components/ui/field";
import type { Program } from "@/lib/schemes";

const PART_OPTIONS = [
  { value: 1, label: "Part-I" },
  { value: 2, label: "Part-II" },
  { value: 3, label: "Part-III" },
  { value: 4, label: "Part-IV" },
];

const SEMESTER_HALF_OPTIONS = [
  { value: "first", label: "First semester of this Part" },
  { value: "second", label: "Second semester of this Part" },
];

const SHIFT_TIME_RANGES: Record<string, string> = {
  Morning: "08:30 – 13:30",
  // Evening scheduling isn't implemented yet (no real teacher-availability data exists for
  // it) — this placeholder range is shown, not invented as if it were real, per the
  // dashboard's design: say so plainly rather than pretending Evening already works.
  Evening: "not yet scheduled — placeholder only",
};

// Step 1-2: pick which division this session is building, and see its shift's time range.
// Group (PM/PE) is hidden for Mathematics, which has no confirmed PM/PE split
// (docs/PROJECT_ARCHITECTURE.md §11.1 — still an open question, not silently assumed either way).
export function SelectionStep({
  programs,
  programId,
  shift,
  part,
  semesterHalf,
  group,
  onChangeProgram,
  onChangeShift,
  onChangePart,
  onChangeSemesterHalf,
  onChangeGroup,
  onStart,
  starting,
}: {
  programs: Program[];
  programId: number | null;
  shift: string;
  part: number;
  semesterHalf: "first" | "second";
  group: string;
  onChangeProgram: (id: number) => void;
  onChangeShift: (shift: string) => void;
  onChangePart: (part: number) => void;
  onChangeSemesterHalf: (half: "first" | "second") => void;
  onChangeGroup: (group: string) => void;
  onStart: () => void;
  starting: boolean;
}) {
  const selectedProgram = programs.find((program) => program.id === programId) ?? null;
  // Mathematics has no confirmed PM/PE split; every other schedulable program does.
  const showGroup = selectedProgram !== null && !selectedProgram.display_name.includes("Mathematics");
  const semester = part * 2 - (semesterHalf === "first" ? 1 : 0);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-content">1. Choose what you're building</h2>
        <p className="mt-1 text-sm text-content/70">
          One division at a time — a specific Program + Part + Semester + Shift (+ Group).
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SelectInput
          label="Program"
          value={programId ?? ""}
          onChange={(value) => onChangeProgram(Number(value))}
          options={[
            { value: "", label: "Choose a program…" },
            ...programs.map((program) => ({ value: program.id, label: program.display_name })),
          ]}
        />
        <SelectInput
          label="Shift"
          value={shift}
          onChange={onChangeShift}
          options={[
            { value: "Morning", label: "Morning" },
            { value: "Evening", label: "Evening" },
          ]}
        />
        <SelectInput
          label="Part"
          value={part}
          onChange={(value) => onChangePart(Number(value))}
          options={PART_OPTIONS}
        />
        <SelectInput
          label="Semester"
          value={semesterHalf}
          onChange={(value) => onChangeSemesterHalf(value as "first" | "second")}
          options={SEMESTER_HALF_OPTIONS}
        />
        {showGroup && (
          <SelectInput
            label="Group"
            value={group}
            onChange={onChangeGroup}
            options={[
              { value: "PM", label: "Pre-Medical (PM)" },
              { value: "PE", label: "Pre-Engineering (PE)" },
            ]}
          />
        )}
      </div>

      <div className="rounded-lg bg-surface p-3 text-sm text-content/80 ring-1 ring-content/15">
        <span className="font-medium text-content">{shift} shift class times: </span>
        {SHIFT_TIME_RANGES[shift]}
      </div>

      {shift === "Evening" && (
        <Alert tone="warning">
          Evening shift has no real teacher-availability data behind it yet. You can still build
          and finalize a division here, but a generated result won't reflect real constraints
          the way Morning does.
        </Alert>
      )}

      <p className="text-xs text-content/60">This will be semester {semester} overall.</p>

      <Button onClick={onStart} loading={starting} disabled={programId === null} className="w-full sm:w-auto">
        Start this division
      </Button>
    </section>
  );
}
