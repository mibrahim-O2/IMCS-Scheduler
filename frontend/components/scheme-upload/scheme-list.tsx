"use client";

import { Button } from "@/components/ui/button";
import type { SchemeSummary } from "@/lib/schemes";

function formatUploadedAt(value: string): string {
  // Upload timestamps come back as ISO strings; show a short readable date.
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function SchemeList({
  schemes,
  loading,
  onUploadNew,
  onRequestDelete,
}: {
  schemes: SchemeSummary[];
  loading: boolean;
  onUploadNew: () => void;
  onRequestDelete: (scheme: SchemeSummary) => void;
}) {
  // Saved schemes as stacked cards — no wide table, so nothing overflows on a phone.
  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-content">Course schemes</h2>
          <p className="mt-1 text-sm text-content/70">Uploaded schemes, newest first.</p>
        </div>
        <Button onClick={onUploadNew} className="w-full sm:w-auto">
          Upload new scheme
        </Button>
      </div>

      {loading && <p className="text-sm text-content/60">Loading…</p>}

      {!loading && schemes.length === 0 && (
        <p className="rounded-xl bg-surface p-6 text-center text-sm text-content/60 ring-1 ring-content/15">
          No course schemes saved yet.
        </p>
      )}

      <ul className="space-y-3">
        {schemes.map((scheme) => (
          <li key={scheme.id} className="rounded-xl bg-surface p-4 ring-1 ring-content/15">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 space-y-1">
                <p className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-content">{scheme.program_name}</span>
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    Scheme year {scheme.scheme_year}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      scheme.is_active
                        ? "bg-status-available/15 text-content"
                        : "bg-status-conflict/15 text-content"
                    }`}
                  >
                    {scheme.is_active ? "Active" : "Deleted"}
                  </span>
                </p>
                <p className="text-sm text-content/70">
                  {scheme.course_count} course{scheme.course_count === 1 ? "" : "s"} · uploaded{" "}
                  {formatUploadedAt(scheme.uploaded_at)}
                </p>
                {scheme.file_url && (
                  <a
                    href={scheme.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block break-all text-sm font-medium text-primary underline"
                  >
                    {scheme.source_filename ?? "Original document"}
                  </a>
                )}
              </div>

              {scheme.is_active && (
                <Button
                  variant="danger"
                  onClick={() => onRequestDelete(scheme)}
                  className="w-full sm:w-auto"
                >
                  Delete
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
