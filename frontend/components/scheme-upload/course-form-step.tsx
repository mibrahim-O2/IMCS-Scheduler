"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { CheckboxInput, NumberInput, TextInput } from "@/components/ui/field";
import { comparableProgramName, parseSchemeText } from "@/lib/scheme-text-parser";
import { emptyCourse, labBaseName, summarize, type CourseRow, type SemesterRows } from "@/lib/schemes";

const PART_LABELS = ["Part-I", "Part-II", "Part-III", "Part-IV"];

type FillMessage = { tone: "success" | "warning"; text: string } | null;

// Step 3: the structured course rows one row per course, with any lab recorded on that course.
// Program and Part arrive fixed (Phase 10): the admin chose them by which slot they clicked on
// the schemes page, so this step only ever fills in one specific slot, never picks a program.
export function CourseFormStep({
  programName,
  appliesToPart,
  schemeYear,
  semesters,
  rawText,
  onChangeYear,
  onChangeSemesters,
  onBack,
  onNext,
}: {
  programName: string;
  appliesToPart: number;
  schemeYear: number;
  semesters: SemesterRows[];
  rawText: string;
  onChangeYear: (year: number) => void;
  onChangeSemesters: (semesters: SemesterRows[]) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [fillMessage, setFillMessage] = useState<FillMessage>(null);
  const [confirmReplace, setConfirmReplace] = useState(false);
  // Null until a fill is attempted; then whether that attempt could read a year from the
  // text. Shown as a persistent prompt (not just the transient fillMessage above) so "enter
  // it manually" stays visible while the admin is doing exactly that.
  const [yearDetected, setYearDetected] = useState<boolean | null>(null);

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
    // The scheme year is auto-detected where the text names it clearly; when it can't be,
    // this says so plainly instead of silently keeping whatever the year field already
    // showed, which would look like a real (and possibly wrong) detected value.
    setYearDetected(parsed.schemeYear !== null);
    if (parsed.schemeYear) onChangeYear(parsed.schemeYear);

    const filled = summarize(parsed.semesters);
    // Warns if the text names a different program than the slot this upload is going
    // into a real mistake (wrong file picked) is worth flagging before it's saved.
    const nameMismatch =
      parsed.programLabel !== null && comparableProgramName(parsed.programLabel) !== comparableProgramName(programName);
    setFillMessage({
      tone: nameMismatch ? "warning" : "success",
      text: nameMismatch
        ? `Filled ${filled.courses} courses, but the document says "${parsed.programLabel}" check this is really meant for ${programName} before previewing.`
        : `Filled ${filled.courses} courses across ${parsed.semesters.length} semesters (${filled.labs} with a lab, merged onto their theory course). Check each row before previewing.`,
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
  const rowsComplete = semesters.every((semester) =>
    semester.courses.every((course) => course.code.trim() && course.name.trim()),
  );

  // The first problem that stops the admin from previewing, shown next to the button. A
  // same-slot conflict can't happen here any more: the schemes page only offers "Upload"
  // on an empty slot, so there is nothing to collide with by the time this step is reached.
  const blockingReason = !yearIsValid
    ? "Fix the scheme year."
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
          credit hours labs are not separate rows. Leave credit hours empty for non-credit (NC) subjects.
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
        <div className="rounded-lg bg-surface p-3 ring-1 ring-content/15">
          <p className="text-xs font-medium uppercase tracking-wide text-content/60">Uploading into</p>
          <p className="mt-1 text-sm font-medium text-content">
            {programName} · {PART_LABELS[appliesToPart - 1]}
          </p>
        </div>
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

      {yearDetected === false && (
        <Alert tone="warning">
          Couldn&apos;t detect the scheme year from the extracted text confidently. Enter it by hand above before
          previewing.
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
