"use client";

import { useCallback, useEffect, useState } from "react";

import { CourseFormStep } from "@/components/scheme-upload/course-form-step";
import { PreviewStep } from "@/components/scheme-upload/preview-step";
import { SchemeList } from "@/components/scheme-upload/scheme-list";
import { StepIndicator } from "@/components/scheme-upload/step-indicator";
import { TextReviewStep } from "@/components/scheme-upload/text-review-step";
import { UploadStep } from "@/components/scheme-upload/upload-step";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { errorMessage } from "@/lib/api-client";
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
type Notice = { tone: "success" | "error"; text: string } | null;

const STEP_NUMBERS: Record<Exclude<Stage, "list">, number> = {
  upload: 1,
  review: 2,
  form: 3,
  preview: 4,
};

function blankSemesters(): SemesterRows[] {
  // The form's starting point: one semester with one empty course row.
  return [{ semester: 1, courses: [emptyCourse()] }];
}

// Course schemes page: the saved-scheme list, swapped for the four-step upload flow while it runs.
export default function SchemesPage() {
  const [stage, setStage] = useState<Stage>("list");
  const [schemes, setSchemes] = useState<SchemeSummary[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  // Each network action has its own flag, so one never makes another look busy.
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResponse | null>(null);
  const [rawText, setRawText] = useState("");
  const [programId, setProgramId] = useState<number | null>(null);
  const [schemeYear, setSchemeYear] = useState(new Date().getFullYear());
  const [semesters, setSemesters] = useState<SemesterRows[]>(blankSemesters);
  const [pendingDelete, setPendingDelete] = useState<SchemeSummary | null>(null);

  const loadSchemes = useCallback(async () => {
    // Refreshes the saved-scheme list; used on first render, after saves and deletes, and by Retry.
    setLoadingList(true);
    setListError(null);
    try {
      setSchemes(await fetchSchemes());
    } catch (cause) {
      setListError(`Couldn't load the saved schemes. ${errorMessage(cause)}`);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    // On mount, load the saved schemes and the programs a new scheme can belong to.
    void loadSchemes();
    fetchDepartments()
      .then((departments) => {
        const schedulable = departments.flatMap((department) =>
          department.programs.filter((program) => program.is_schedulable),
        );
        setPrograms(schedulable);
        setProgramId((current) => current ?? schedulable[0]?.id ?? null);
      })
      .catch((cause) =>
        setNotice({
          tone: "error",
          text: `Couldn't load the program list, so a new scheme can't be assigned to a program. ${errorMessage(cause)}`,
        }),
      );
  }, [loadSchemes]);

  useEffect(() => {
    // Every step starts at the top otherwise on a phone the next step opens mid-page.
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [stage]);

  function goTo(next: Stage) {
    // Moves to another step and clears the message that belonged to the previous one.
    setNotice(null);
    setStage(next);
  }

  function resetWizard() {
    // Forgets everything the wizard collected and returns to the list.
    setFile(null);
    setExtraction(null);
    setRawText("");
    setSemesters(blankSemesters());
    goTo("list");
  }

  async function handleExtract() {
    // Sends the chosen file for text extraction and moves on to the review step.
    if (!file) return;
    setExtracting(true);
    setNotice(null);
    try {
      const result = await extractSchemeText(file);
      setExtraction(result);
      setRawText(result.text);
      goTo("review");
      const pages = result.page_count ? `${result.page_count} page${result.page_count === 1 ? "" : "s"} of ` : "";
      setNotice({
        tone: "success",
        text: `Read ${result.character_count.toLocaleString()} characters from ${pages}“${result.filename}”.`,
      });
    } catch (cause) {
      setNotice({ tone: "error", text: `Couldn't read “${file.name}”. ${errorMessage(cause)}` });
    } finally {
      setExtracting(false);
    }
  }

  async function handleConfirmSave() {
    // Final step: upload the document and save the rows, then show the refreshed list.
    if (!file || programId === null) return;
    setSaving(true);
    setNotice(null);
    try {
      const saved = await saveScheme({ file, programId, schemeYear, semesters, rawText });
      resetWizard();
      setNotice({
        tone: "success",
        text: `Saved ${saved.program_name}, scheme year ${saved.scheme_year}: ${saved.course_count} courses, ${saved.lab_course_count} with a lab.`,
      });
      await loadSchemes();
    } catch (cause) {
      setNotice({ tone: "error", text: `The scheme was not saved. ${errorMessage(cause)}` });
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    // Soft-deletes the scheme the admin confirmed in the dialog.
    if (!pendingDelete) return;
    const target = pendingDelete;
    setDeleting(true);
    setNotice(null);
    try {
      await deleteScheme(target.id);
      setNotice({
        tone: "success",
        text: `Deleted the ${target.scheme_year} scheme for ${target.program_name}. It is kept as an inactive record.`,
      });
      await loadSchemes();
    } catch (cause) {
      setNotice({ tone: "error", text: `The scheme was not deleted. ${errorMessage(cause)}` });
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  }

  const selectedProgram = programs.find((program) => program.id === programId);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-content">Course schemes</h1>
        <p className="mt-1 text-sm text-content/70">
          Upload a scheme document, check the text read from it, confirm the course rows, then save.
        </p>
      </header>

      {stage !== "list" && (
        <div className="mb-6">
          <StepIndicator current={STEP_NUMBERS[stage]} />
        </div>
      )}

      <div className="mb-4 space-y-3 empty:hidden">
        {notice && (
          <Alert tone={notice.tone} onDismiss={() => setNotice(null)}>
            {notice.text}
          </Alert>
        )}
        {stage === "list" && listError && (
          <Alert
            tone="error"
            action={
              <Button variant="secondary" onClick={loadSchemes} loading={loadingList}>
                Retry
              </Button>
            }
          >
            {listError}
          </Alert>
        )}
      </div>

      <div className="rounded-2xl bg-card p-4 shadow-sm ring-1 ring-content/10 sm:p-6">
        {stage === "list" && (
          <SchemeList
            schemes={schemes}
            loading={loadingList}
            onUploadNew={() => goTo("upload")}
            onRequestDelete={setPendingDelete}
          />
        )}

        {stage === "upload" && (
          <UploadStep
            file={file}
            extracting={extracting}
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
            onBack={() => goTo("upload")}
            onNext={() => goTo("form")}
          />
        )}

        {stage === "form" && (
          <CourseFormStep
            programs={programs}
            programId={programId}
            schemeYear={schemeYear}
            semesters={semesters}
            rawText={rawText}
            existingSchemes={schemes}
            onChangeProgram={setProgramId}
            onChangeYear={setSchemeYear}
            onChangeSemesters={setSemesters}
            onBack={() => goTo("review")}
            onNext={() => goTo("preview")}
          />
        )}

        {stage === "preview" && (
          <PreviewStep
            programName={selectedProgram?.display_name ?? "No program selected"}
            schemeYear={schemeYear}
            fileName={file?.name ?? "No file"}
            semesters={semesters}
            saving={saving}
            onBack={() => goTo("form")}
            onConfirm={handleConfirmSave}
          />
        )}
      </div>

      {pendingDelete && (
        <ConfirmDialog
          title="Delete this course scheme?"
          message={`${pendingDelete.program_name}, scheme year ${pendingDelete.scheme_year}. It stays in the database as an inactive record, and deletion is refused if a published timetable uses it.`}
          confirmLabel="Delete scheme"
          busyLabel="Deleting…"
          busy={deleting}
          onConfirm={handleDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </main>
  );
}
