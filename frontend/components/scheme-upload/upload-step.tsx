"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];

function formatSize(bytes: number): string {
  // Human-readable file size for the chosen-file line.
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Step 1: pick the original scheme document. Extraction runs when the admin continues.
export function UploadStep({
  file,
  extracting,
  onSelectFile,
  onExtract,
  onCancel,
}: {
  file: File | null;
  extracting: boolean;
  onSelectFile: (file: File | null) => void;
  onExtract: () => void;
  onCancel: () => void;
}) {
  const [typeError, setTypeError] = useState<string | null>(null);

  function handleChoose(chosen: File | null) {
    // Accepts only the formats the backend can read, and says why when it can't.
    if (!chosen) return;
    const dot = chosen.name.lastIndexOf(".");
    const extension = dot >= 0 ? chosen.name.slice(dot).toLowerCase() : "";
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setTypeError(`“${chosen.name}” can't be used. Choose a PDF or a Word (.docx) file.`);
      onSelectFile(null);
      return;
    }
    setTypeError(null);
    onSelectFile(chosen);
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-content">Upload the scheme document</h2>
        <p className="mt-1 text-sm text-content/70">
          PDF or Word (.docx). The text is read from the file so you can check it before entering course rows.
        </p>
      </div>

      <label
        className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-10 text-center transition-colors ${
          file ? "border-primary/50 bg-primary/5" : "border-content/20 bg-surface hover:border-primary/40"
        }`}
      >
        <span className="text-sm font-medium text-primary">{file ? "Choose a different file" : "Choose a file"}</span>
        <span className="break-all text-sm text-content">
          {file ? `${file.name} · ${formatSize(file.size)}` : "No file selected yet"}
        </span>
        <input
          type="file"
          accept=".pdf,.docx"
          className="sr-only"
          disabled={extracting}
          onChange={(event) => {
            handleChoose(event.target.files?.[0] ?? null);
            event.target.value = "";
          }}
        />
      </label>

      {typeError && <Alert tone="error">{typeError}</Alert>}

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel} disabled={extracting} className="w-full sm:w-auto">
          Cancel
        </Button>
        <Button onClick={onExtract} disabled={!file} loading={extracting} className="w-full sm:w-auto">
          {extracting ? "Reading the document…" : "Extract text"}
        </Button>
      </div>
    </section>
  );
}
