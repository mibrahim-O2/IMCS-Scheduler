"use client";

import { useEffect, useState } from "react";

import { SemesterTable } from "@/components/scheme-upload/semester-table";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/lib/api-client";
import { fetchScheme, type SchemeDetail, type SchemeSummary } from "@/lib/schemes";

function formatUploadedAt(value: string): string {
  // Upload timestamps come back as ISO strings; show a short readable date.
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// Saved schemes as stacked cards, each able to expand into its per-semester course tables.
// No wide table at the top level, so nothing overflows on a phone.
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
  const [openId, setOpenId] = useState<number | null>(null);
  const [details, setDetails] = useState<Record<number, SchemeDetail>>({});
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    // A save or delete refreshes the list; cached course lists may be stale after that.
    setDetails({});
  }, [schemes]);

  async function toggleCourses(id: number) {
    // Opens or closes a scheme's course list, fetching it the first time it is opened.
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    setDetailError(null);
    if (details[id]) return;

    setLoadingId(id);
    try {
      const detail = await fetchScheme(id);
      setDetails((previous) => ({ ...previous, [id]: detail }));
    } catch (cause) {
      setDetailError(`Couldn't load the courses for this scheme. ${errorMessage(cause)}`);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-content">Saved schemes</h2>
          <p className="mt-1 text-sm text-content/70">Newest upload first. Deleted schemes are kept as inactive records.</p>
        </div>
        <Button onClick={onUploadNew} className="w-full sm:w-auto">
          Upload new scheme
        </Button>
      </div>

      {loading && (
        <p className="flex items-center gap-2 text-sm text-content/60">
          <Spinner /> Loading saved schemes…
        </p>
      )}

      {!loading && schemes.length === 0 && (
        <div className="rounded-xl bg-surface p-8 text-center ring-1 ring-content/15">
          <p className="font-medium text-content">No course schemes saved yet</p>
          <p className="mt-1 text-sm text-content/60">
            Upload a program&apos;s scheme document to add the first one.
          </p>
        </div>
      )}

      <ul className="space-y-3">
        {schemes.map((scheme) => {
          const isOpen = openId === scheme.id;
          const detail = details[scheme.id];
          return (
            <li key={scheme.id} className="rounded-xl bg-surface p-4 ring-1 ring-content/15">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <p className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-content">{scheme.program_name}</span>
                    <span className="rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-content">
                      Scheme year {scheme.scheme_year}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium text-content ${
                        scheme.is_active ? "bg-status-available/20" : "bg-status-conflict/20"
                      }`}
                    >
                      {scheme.is_active ? "Active" : "Deleted"}
                    </span>
                  </p>
                  <p className="text-sm text-content/70">
                    {scheme.course_count} course{scheme.course_count === 1 ? "" : "s"} ·{" "}
                    {scheme.lab_course_count} with a lab · uploaded {formatUploadedAt(scheme.uploaded_at)}
                  </p>
                  {scheme.file_url && (
                    <a
                      href={scheme.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex min-h-8 items-center break-all text-sm font-medium text-primary underline"
                    >
                      {scheme.source_filename ?? "Original document"}
                    </a>
                  )}
                </div>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button
                    variant="secondary"
                    onClick={() => toggleCourses(scheme.id)}
                    loading={loadingId === scheme.id}
                    aria-expanded={isOpen}
                    className="w-full sm:w-auto"
                  >
                    {isOpen ? "Hide courses" : "View courses"}
                  </Button>
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
              </div>

              {isOpen && (
                <div className="mt-4 space-y-4">
                  {detailError && <Alert tone="error">{detailError}</Alert>}
                  {detail?.semesters.map((semester) => (
                    <SemesterTable key={semester.semester} semester={semester} />
                  ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
