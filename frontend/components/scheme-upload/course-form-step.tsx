"use client";

import { Button } from "@/components/ui/button";
import { CheckboxInput, NumberInput, SelectInput, TextInput } from "@/components/ui/field";
import { countCourses, emptyCourse, type CourseRow, type Program, type SemesterRows } from "@/lib/schemes";

export function CourseFormStep({
  programs,
  programId,
  schemeYear,
  semesters,
  rawText,
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
  onChangeProgram: (programId: number) => void;
  onChangeYear: (year: number) => void;
  onChangeSemesters: (semesters: SemesterRows[]) => void;
  onBack: () => void;
  onNext: () => void;
}) {
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

  // The backend accepts scheme years 2000-2100; catch a bad one here rather than on save.
  const yearIsValid = Number.isInteger(schemeYear) && schemeYear >= 2000 && schemeYear <= 2100;

  const canContinue =
    programId !== null &&
    yearIsValid &&
    countCourses(semesters) > 0 &&
    semesters.every((semester) => semester.courses.every((course) => course.code.trim() && course.name.trim()));

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-content">Enter the course rows</h2>
        <p className="mt-1 text-sm text-content/70">
          Fill these in from the extracted text. Leave credit hours empty for non-credit (NC) subjects.
        </p>
      </div>

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

      <details className="rounded-lg bg-surface p-3 ring-1 ring-content/15">
        <summary className="cursor-pointer text-sm font-medium text-primary">
          Show extracted text for reference
        </summary>
        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-content/80">
          {rawText}
        </pre>
      </details>

      {semesters.map((semester, semesterIndex) => (
        <div key={semester.semester} className="rounded-xl bg-surface p-4 ring-1 ring-content/15">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-content">Semester {semester.semester}</h3>
            <button
              type="button"
              className="min-h-11 text-sm font-medium text-status-conflict"
              onClick={() => removeSemester(semesterIndex)}
            >
              Remove semester
            </button>
          </div>

          <div className="mt-3 space-y-4">
            {semester.courses.map((course, courseIndex) => (
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
                    label="Lab credit hrs"
                    value={course.lab_credit_hours}
                    onChange={(value) => updateCourse(semesterIndex, courseIndex, { lab_credit_hours: value })}
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
                  <div className="sm:col-span-2">
                    <CheckboxInput
                      label="Has a lab"
                      checked={course.has_lab}
                      onChange={(checked) => updateCourse(semesterIndex, courseIndex, { has_lab: checked })}
                    />
                  </div>
                </div>

                <button
                  type="button"
                  className="mt-2 min-h-11 text-sm font-medium text-status-conflict"
                  onClick={() => removeCourse(semesterIndex, courseIndex)}
                >
                  Remove course
                </button>
              </div>
            ))}
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

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onBack} className="w-full sm:w-auto">
          Back
        </Button>
        <Button onClick={onNext} disabled={!canContinue} className="w-full sm:w-auto">
          Preview ({countCourses(semesters)} courses)
        </Button>
      </div>
    </section>
  );
}
