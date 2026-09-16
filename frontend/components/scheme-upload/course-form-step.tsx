"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { CheckboxInput, NumberInput, SelectInput, TextInput } from "@/components/ui/field";
import { matchProgramId, parseSchemeText } from "@/lib/scheme-text-parser";
import {
  emptyCourse,
  labBaseName,
  summarize,
  type CourseRow,
  type Program,
  type SchemeSummary,
  type SemesterRows,
} from "@/lib/schemes";

type FillMessage = { tone: "success" | "warning"; text: string } | null;

// Step 3: the structured course rows — one row per course, with any lab recorded on that course.
export function CourseFormStep({
  programs,
  programId,
  schemeYear,
  semesters,
  rawText,
  existingSchemes,
  onChangeProgram,
  onChangeYear,
  onChangeSemesters,
  onBack,
  onNext,
}: {
  programs: Program[];
  programId: number | null;
  schemeYear: number;
  semesters: SemesterRows[];
  rawText: string;
  existingSchemes: SchemeSummary[];
  onChangeProgram: (programId: number) => void;
  onChangeYear: (year: number) => void;
  onChangeSemesters: (semesters: SemesterRows[]) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [fillMessage, setFillMessage] = useState<FillMessage>(null);
  const [confirmReplace, setConfirmReplace] = useState(false);

  function updateCourse(semesterIndex: number, courseIndex: number, patch: Partial<CourseRow>) {
    // Applies one field edit without mutating the existing state objects.
    onChangeSemesters(
      semesters.map((semester, sIndex) =>
        sIndex !== semesterIndex
          ? semester
          : {
              ...semester,
              courses: semester.courses.map((course, cIndex) =>
                cIndex === courseIndex ? { ...course, ...patch } : course,
              ),
            },
      ),
    );
  }

  function toggleLab(semesterIndex: number, courseIndex: number, course: CourseRow, checked: boolean) {
    // Ticking "Has a lab" suggests 1 lab credit hour; unticking clears the lab hours.
    updateCourse(semesterIndex, courseIndex, {
      has_lab: checked,
      lab_credit_hours: checked ? (course.lab_credit_hours ?? 1) : null,
    });
  }

  function addCourse(semesterIndex: number) {
    // Appends a blank course row to one semester.
    onChangeSemesters(
      semesters.map((semester, index) =>
        index === semesterIndex ? { ...semester, courses: [...semester.courses, emptyCourse()] } : semester,
      ),
    );
  }

  function removeCourse(semesterIndex: number, courseIndex: number) {
    // Drops a single course row.
    onChangeSemesters(
      semesters.map((semester, index) =>
        index === semesterIndex
          ? { ...semester, courses: semester.courses.filter((_, cIndex) => cIndex !== courseIndex) }
          : semester,
      ),
    );
  }

  function addSemester() {
    // Adds the next semester number, starting with one empty row.
    const nextNumber = Math.max(0, ...semesters.map((semester) => semester.semester)) + 1;
    onChangeSemesters([...semesters, { semester: nextNumber, courses: [emptyCourse()] }]);
  }

  function removeSemester(semesterIndex: number) {
    // Removes a whole semester block.
    onChangeSemesters(semesters.filter((_, index) => index !== semesterIndex));
  }

  function fillFromText() {
    // Replaces the rows with what the extracted text contains, and picks up the program and
    // year when the document names them. The admin still reviews every row afterwards.
    setConfirmReplace(false);
    const parsed = parseSchemeText(rawText);
    if (parsed.semesters.length === 0) {
      setFillMessage({
        tone: "warning",
        text: "No course table was recognised in the extracted text. Enter the rows by hand, using the text below as a reference.",
      });
      return;
    }

    onChangeSemesters(parsed.semesters);
    if (parsed.schemeYear) onChangeYear(parsed.schemeYear);
    const matchedProgram = matchProgramId(parsed.programLabel, programs);
    if (matchedProgram !== null) onChangeProgram(matchedProgram);

    const filled = summarize(parsed.semesters);
    setFillMessage({
      tone: "success",
      text: `Filled ${filled.courses} courses across ${parsed.semesters.length} semesters (${filled.labs} with a lab, merged onto their theory course). Check each row before previewing.`,
    });
  }

  function handleFillClick() {
    // Asks before overwriting rows the admin has already typed.
    const hasEnteredRows = semesters.some((semester) =>
      semester.courses.some((course) => course.code.trim() || course.name.trim()),
    );
    if (hasEnteredRows) setConfirmReplace(true);
    else fillFromText();
  }

  const totals = summarize(semesters);
  const yearIsValid = Number.isInteger(schemeYear) && schemeYear >= 2000 && schemeYear <= 2100;
  const conflict = existingSchemes.find(
    (scheme) => scheme.program_id === programId && scheme.scheme_year === schemeYear,
  );
  const rowsComplete = semesters.every((semester) =>
    semester.courses.every((course) => course.code.trim() && course.name.trim()),
  );

  // The first problem that stops the admin from previewing, shown next to the button.
  const blockingReason =
    programId === null
      ? "Choose a program."
      : !yearIsValid
        ? "Fix the scheme year."
        : conflict
          ? "This program already has a scheme for that year."
          : totals.courses === 0
            ? "Add at least one course."
            : !rowsComplete
              ? "Every course needs a code and a name."
              : null;

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-content">Enter the course rows</h2>
        <p className="mt-1 text-sm text-content/70">
          One row per course. If a course has a lab, tick “Has a lab” on that course and enter the lab&apos;s
          credit hours — labs are not separate rows. Leave credit hours empty for non-credit (NC) subjects.
        </p>
      </div>

      <div className="flex flex-col gap-3 rounded-xl bg-primary/5 p-4 ring-1 ring-primary/20 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-content">
          Scheme pages from the university portal can be read straight into rows.
        </p>
        <Button
          variant="secondary"
          onClick={handleFillClick}
          disabled={!rawText.trim()}
          className="w-full shrink-0 sm:w-auto"
        >
          Fill rows from extracted text
        </Button>
      </div>

      {fillMessage && (
        <Alert tone={fillMessage.tone} onDismiss={() => setFillMessage(null)}>
          {fillMessage.text}
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SelectInput
          label="Program"
          value={programId ?? ""}
          onChange={(value) => onChangeProgram(Number(value))}
          options={programs.map((program) => ({ value: program.id, label: program.display_name }))}
        />
        <div>
          <NumberInput
            label="Scheme year (admission year)"
            value={schemeYear}
            onChange={(value) => onChangeYear(value ?? schemeYear)}
          />
          {!yearIsValid && (
            <p className="mt-1 text-xs text-status-conflict">Enter a scheme year between 2000 and 2100.</p>
          )}
        </div>
      </div>

      {conflict && (
        <Alert tone="error">
          {conflict.program_name} already has an active {conflict.scheme_year} scheme. Delete it from the saved
          schemes list first, or choose a different year.
        </Alert>
      )}

      <details className="rounded-lg bg-surface p-3 ring-1 ring-content/15">
        <summary className="min-h-8 cursor-pointer text-sm font-medium text-primary">
          Show extracted text for reference
        </summary>
        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-content/80">
          {rawText || "No text was extracted."}
        </pre>
      </details>

      {semesters.map((semester, semesterIndex) => (
        <div key={semester.semester} className="rounded-xl bg-surface p-4 ring-1 ring-content/15">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-content">
              Semester {semester.semester} · {semester.courses.length} course
              {semester.courses.length === 1 ? "" : "s"}
            </h3>
            <button
              type="button"
              className="min-h-11 text-sm font-medium text-status-conflict"
              onClick={() => removeSemester(semesterIndex)}
            >
              Remove semester
            </button>
          </div>

          <div className="mt-3 space-y-4">
            {semester.courses.map((course, courseIndex) => {
              const labOf = labBaseName(course.name);
              return (
                <div key={courseIndex} className="rounded-lg bg-card p-3 ring-1 ring-content/10">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-6">
                    <div className="sm:col-span-2">
                      <TextInput
                        label="Course code"
                        value={course.code}
                        placeholder="CSOO303"
                        onChange={(value) => updateCourse(semesterIndex, courseIndex, { code: value })}
                      />
                    </div>
                    <div className="sm:col-span-4">
                      <TextInput
                        label="Course name"
                        value={course.name}
                        placeholder="OBJECT ORIENTED PROGRAMMING"
                        onChange={(value) => updateCourse(semesterIndex, courseIndex, { name: value })}
                      />
                    </div>
                    <NumberInput
                      label="Credit hrs"
                      value={course.credit_hours}
                      placeholder="NC"
                      onChange={(value) => updateCourse(semesterIndex, courseIndex, { credit_hours: value })}
                    />
                    <NumberInput
                      label="Min marks"
                      value={course.min_marks}
                      onChange={(value) => updateCourse(semesterIndex, courseIndex, { min_marks: value })}
                    />
                    <NumberInput
                      label="Max marks"
                      value={course.max_marks}
                      onChange={(value) => updateCourse(semesterIndex, courseIndex, { max_marks: value })}
                    />
                    <div className="sm:self-end">
                      <CheckboxInput
                        label="Has a lab"
                        checked={course.has_lab}
                        onChange={(checked) => toggleLab(semesterIndex, courseIndex, course, checked)}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      {course.has_lab && (
                        <NumberInput
                          label="Lab credit hrs"
                          value={course.lab_credit_hours}
                          onChange={(value) =>
                            updateCourse(semesterIndex, courseIndex, { lab_credit_hours: value })
                          }
                        />
                      )}
                    </div>
                  </div>

                  {labOf && (
                    <p className="mt-2 text-xs text-content/70">
                      This is a lab row. On save it is merged into the course named “{labOf}” as its lab. You can
                      instead tick “Has a lab” on that course and remove this row.
                    </p>
                  )}

                  <button
                    type="button"
                    className="mt-1 min-h-11 text-sm font-medium text-status-conflict"
                    onClick={() => removeCourse(semesterIndex, courseIndex)}
                  >
                    Remove course
                  </button>
                </div>
              );
            })}
          </div>

          <Button
            variant="secondary"
            onClick={() => addCourse(semesterIndex)}
            className="mt-3 w-full sm:w-auto"
          >
            Add course
          </Button>
        </div>
      ))}

      <Button variant="secondary" onClick={addSemester} className="w-full sm:w-auto">
        Add semester
      </Button>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
        {blockingReason && (
          <p className="text-center text-xs text-content/70 sm:mr-auto sm:text-left">{blockingReason}</p>
        )}
        <Button variant="secondary" onClick={onBack} className="w-full sm:w-auto">
          Back
        </Button>
        <Button onClick={onNext} disabled={blockingReason !== null} className="w-full sm:w-auto">
          Preview ({totals.courses} course{totals.courses === 1 ? "" : "s"})
        </Button>
      </div>

      {confirmReplace && (
        <ConfirmDialog
          title="Replace the rows you've entered?"
          message="Filling from the extracted text replaces every course row currently in the form."
          confirmLabel="Replace rows"
          onConfirm={fillFromText}
          onCancel={() => setConfirmReplace(false)}
        />
      )}
    </section>
  );
}
