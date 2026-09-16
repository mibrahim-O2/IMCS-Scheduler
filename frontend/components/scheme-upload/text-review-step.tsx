"use client";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ExtractionResponse } from "@/lib/schemes";

const METHOD_LABELS: Record<string, string> = {
  "pdf-text": "Read from the PDF's text",
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
  // Step 2: the extracted text, editable. It is a reference for the next step, not saved as rows.
  const pages = extraction.page_count;
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-content">Review the extracted text</h2>
        <p className="mt-1 text-sm text-content/70">
          {METHOD_LABELS[extraction.method] ?? extraction.method}
          {pages > 0 && ` · ${pages} page${pages === 1 ? "" : "s"}`} ·{" "}
          {extraction.character_count.toLocaleString()} characters. Correct anything that was misread — the
          next step can fill course rows from this text.
        </p>
      </div>

      {extraction.warnings.map((warning) => (
        <Alert key={warning} tone="warning">
          {warning}
        </Alert>
      ))}

      {!rawText.trim() && (
        <Alert tone="warning">
          No text was found in this file. You can still continue and enter the course rows by hand.
        </Alert>
      )}

      <textarea
        aria-label="Extracted text"
        className="h-80 w-full rounded-lg bg-surface p-3 font-mono text-xs leading-relaxed text-content ring-1 ring-content/20 focus:outline-none focus:ring-2 focus:ring-primary sm:text-sm"
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
