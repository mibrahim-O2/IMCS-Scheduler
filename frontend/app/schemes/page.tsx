"use client";

import { useCallback, useEffect, useState } from "react";

import { CourseFormStep } from "@/components/scheme-upload/course-form-step";
import { PreviewStep } from "@/components/scheme-upload/preview-step";
import { SchemeList } from "@/components/scheme-upload/scheme-list";
import { StepIndicator } from "@/components/scheme-upload/step-indicator";
import { TextReviewStep } from "@/components/scheme-upload/text-review-step";
import { UploadStep } from "@/components/scheme-upload/upload-step";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  deleteScheme,
  emptyCourse,
  extractSchemeText,
  fetchDepartments,
  fetchSchemes,
  saveScheme,
  type ExtractionResponse,
  type Program,
  type SchemeSummary,
  type SemesterRows,
} from "@/lib/schemes";

type Stage = "list" | "upload" | "review" | "form" | "preview";

const STEP_NUMBERS: Record<Exclude<Stage, "list">, number> = {
  upload: 1,
  review: 2,
  form: 3,
  preview: 4,
};

export default function SchemesPage() {
  const [stage, setStage] = useState<Stage>("list");
  const [schemes, setSchemes] = useState<SchemeSummary[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [busy, setBusy] = useState(false);
  // Delete has its own flag so the confirm dialog never looks busy because of a list refresh.
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResponse | null>(null);
  const [rawText, setRawText] = useState("");
  const [programId, setProgramId] = useState<number | null>(null);
  const [schemeYear, setSchemeYear] = useState(new Date().getFullYear());
  const [semesters, setSemesters] = useState<SemesterRows[]>([{ semester: 1, courses: [emptyCourse()] }]);
  const [pendingDelete, setPendingDelete] = useState<SchemeSummary | null>(null);

  const loadSchemes = useCallback(async () => {
    // Refreshes the saved-scheme list; used on first render and after every save or delete.
    setLoadingList(true);
    try {
      setSchemes(await fetchSchemes());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load course schemes.");
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    // On mount, load both the saved schemes and the programs the form can target.
    void loadSchemes();
    void fetchDepartments()
      .then((departments) => {
        const schedulable = departments.flatMap((department) =>
          department.programs.filter((program) => program.is_schedulable),
        );
        setPrograms(schedulable);
        setProgramId((current) => current ?? schedulable[0]?.id ?? null);
      })
      .catch(() => setError("Could not load the program list."));
  }, [loadSchemes]);

  function resetWizard() {
    // Clears everything the wizard collected and returns to the list.
    setFile(null);
    setExtraction(null);
    setRawText("");
    setSemesters([{ semester: 1, courses: [emptyCourse()] }]);
    setStage("list");
    setError(null);
  }

  async function handleExtract() {
    // Sends the chosen file for text extraction and moves to the review step.
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await extractSchemeText(file);
      setExtraction(result);
      setRawText(result.text);
      setStage("review");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Extraction failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmSave() {
    // Final step: upload the document and save the structured rows.
    if (!file || programId === null) return;
    setBusy(true);
    setError(null);
    try {
      const saved = await saveScheme({ file, programId, schemeYear, semesters, rawText });
      setNotice(`Saved ${saved.program_name} ${saved.scheme_year} with ${saved.course_count} courses.`);
      resetWizard();
      await loadSchemes();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Saving failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    // Soft-deletes the scheme the admin confirmed in the dialog.
    if (!pendingDelete) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteScheme(pendingDelete.id);
      setNotice(`Deleted the ${pendingDelete.scheme_year} scheme for ${pendingDelete.program_name}.`);
      setPendingDelete(null);
      await loadSchemes();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  }

  const selectedProgram = programs.find((program) => program.id === programId);

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-content">Course scheme management</h1>
        <p className="mt-1 text-sm text-content/70">
          Upload a scheme document, review what was read from it, enter the course rows, then save.
        </p>
      </header>

      {stage !== "list" && (
        <div className="mb-6 overflow-x-auto pb-1">
          <StepIndicator current={STEP_NUMBERS[stage]} />
        </div>
      )}

      {notice && (
        <p className="mb-4 rounded-lg bg-status-available/15 px-3 py-2 text-sm text-content ring-1 ring-status-available/40">
          {notice}
        </p>
      )}
      {error && (
        <p className="mb-4 rounded-lg bg-status-conflict/15 px-3 py-2 text-sm text-content ring-1 ring-status-conflict/40">
          {error}
        </p>
      )}

      <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
        {stage === "list" && (
          <SchemeList
            schemes={schemes}
            loading={loadingList}
            onUploadNew={() => {
              setNotice(null);
              setStage("upload");
            }}
            onRequestDelete={setPendingDelete}
          />
        )}

        {stage === "upload" && (
          <UploadStep
            file={file}
            busy={busy}
            onSelectFile={setFile}
            onExtract={handleExtract}
            onCancel={resetWizard}
          />
        )}

        {stage === "review" && extraction && (
          <TextReviewStep
            extraction={extraction}
            rawText={rawText}
            onChangeText={setRawText}
            onBack={() => setStage("upload")}
            onNext={() => setStage("form")}
          />
        )}

        {stage === "form" && (
          <CourseFormStep
            programs={programs}
            programId={programId}
            schemeYear={schemeYear}
            semesters={semesters}
            rawText={rawText}
            onChangeProgram={setProgramId}
            onChangeYear={setSchemeYear}
            onChangeSemesters={setSemesters}
            onBack={() => setStage("review")}
            onNext={() => setStage("preview")}
          />
        )}

        {stage === "preview" && (
          <PreviewStep
            programName={selectedProgram?.display_name ?? "Unknown program"}
            schemeYear={schemeYear}
            fileName={file?.name ?? "No file"}
            semesters={semesters}
            busy={busy}
            onBack={() => setStage("form")}
            onConfirm={handleConfirmSave}
          />
        )}
      </div>

      {pendingDelete && (
        <ConfirmDialog
          title="Delete this course scheme?"
          message={`${pendingDelete.program_name} — scheme year ${pendingDelete.scheme_year}. It is kept in the database as inactive, and deletion is refused if a published timetable uses it.`}
          confirmLabel="Delete scheme"
          busy={deleting}
          onConfirm={handleDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </main>
  );
}
