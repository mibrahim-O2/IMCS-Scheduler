"use client";

import { Button } from "@/components/ui/button";

export function UploadStep({
  file,
  busy,
  onSelectFile,
  onExtract,
  onCancel,
}: {
  file: File | null;
  busy: boolean;
  onSelectFile: (file: File | null) => void;
  onExtract: () => void;
  onCancel: () => void;
}) {
  // Step 1: pick the original scheme document. Extraction happens when the admin continues.
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-content">Upload the scheme document</h2>
        <p className="mt-1 text-sm text-content/70">
          PDF or Word (.docx). Scanned PDFs are read with OCR automatically.
        </p>
      </div>

      <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-content/20 bg-surface px-4 py-10 text-center">
        <span className="text-sm font-medium text-primary">Choose a file</span>
        <span className="break-all text-xs text-content/60">
          {file ? `${file.name} (${Math.round(file.size / 1024)} KB)` : "No file selected"}
        </span>
        <input
          type="file"
          accept=".pdf,.docx"
          className="sr-only"
          onChange={(event) => onSelectFile(event.target.files?.[0] ?? null)}
        />
      </label>

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel} className="w-full sm:w-auto">
          Cancel
        </Button>
        <Button onClick={onExtract} disabled={!file || busy} className="w-full sm:w-auto">
          {busy ? "Extracting…" : "Extract text"}
        </Button>
      </div>
    </section>
  );
}
