"use client";

import { Button } from "@/components/ui/button";
import type { ExtractionResponse } from "@/lib/schemes";

const METHOD_LABELS: Record<string, string> = {
  "pdf-text": "Read from the PDF text layer",
  ocr: "Read with OCR (scanned document)",
  word: "Read from the Word document",
};

export function TextReviewStep({
  extraction,
  rawText,
  onChangeText,
  onBack,
  onNext,
}: {
  extraction: ExtractionResponse;
  rawText: string;
  onChangeText: (text: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  // Step 2: the extracted text, editable. It is a reference for the admin, not auto-parsed.
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-content">Review the extracted text</h2>
        <p className="mt-1 text-sm text-content/70">
          {METHOD_LABELS[extraction.method] ?? extraction.method} · {extraction.page_count} page
          {extraction.page_count === 1 ? "" : "s"} · {extraction.character_count.toLocaleString()} characters
        </p>
      </div>

      {extraction.warnings.map((warning) => (
        <p
          key={warning}
          className="rounded-lg bg-status-busy/15 px-3 py-2 text-sm text-content ring-1 ring-status-busy/40"
        >
          {warning}
        </p>
      ))}

      <textarea
        className="h-72 w-full rounded-lg bg-surface p-3 font-mono text-xs leading-relaxed text-content ring-1 ring-content/20 focus:outline-none focus:ring-2 focus:ring-primary sm:text-sm"
        value={rawText}
        onChange={(event) => onChangeText(event.target.value)}
        spellCheck={false}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onBack} className="w-full sm:w-auto">
          Back
        </Button>
        <Button onClick={onNext} className="w-full sm:w-auto">
          Continue to course rows
        </Button>
      </div>
    </section>
  );
}
