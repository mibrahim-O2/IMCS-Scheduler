"use client";

import { useEffect, useState } from "react";

import { SemesterTable } from "@/components/scheme-upload/semester-table";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/lib/api-client";
import { fetchScheme, type Program, type SchemeDetail, type SchemeSummary } from "@/lib/schemes";

const PART_LABELS = ["Part-I", "Part-II", "Part-III", "Part-IV"];

function formatUploadedAt(value: string): string {
  // Upload timestamps come back as ISO strings; show a short readable date.
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// Phase 10: replaces the old flat "Upload new scheme" button with a 4-slot grid
// (Part-I..Part-IV) per schedulable program. An empty slot offers "Upload"; a filled
// slot shows its year/status and offers "View courses" and "Delete" (the same
// soft-delete-then-replace flow as before deleting empties the slot again).
export function SchemeSlots({
  programs,
  schemes,
  loading,
  onUpload,
  onRequestDelete,
}: {
  programs: Program[];
  schemes: SchemeSummary[];
  loading: boolean;
  onUpload: (programId: number, part: number) => void;
  onRequestDelete: (scheme: SchemeSummary) => void;
}) {
  const [openId, setOpenId] = useState<number | null>(null);
  const [details, setDetails] = useState<Record<number, SchemeDetail>>({});
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    // A save or delete refreshes the scheme list; cached course lists may be stale after that.
    setDetails({});
    setOpenId(null);
  }, [schemes]);

  async function toggleCourses(id: number) {
    // Opens or closes a slot's course list, fetching it the first time it is opened.
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

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-content/60">
        <Spinner /> Loading saved schemes…
      </p>
    );
  }

  return (
    <section className="space-y-8">
      {programs.map((program) => {
        // Only this program's active schemes, one per Part slot (at most).
        const byPart = new Map(
          schemes
            .filter((scheme) => scheme.program_id === program.id && scheme.is_active)
            .map((scheme) => [scheme.applies_to_part, scheme]),
        );

        return (
          <div key={program.id}>
            <h2 className="text-lg font-semibold text-content">{program.display_name}</h2>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {PART_LABELS.map((label, index) => {
                const part = index + 1;
                const scheme = byPart.get(part);
                const isOpen = scheme && openId === scheme.id;
                const detail = scheme ? details[scheme.id] : undefined;

                return (
                  <div key={part} className="rounded-xl bg-surface p-4 ring-1 ring-content/15">
                    <p className="font-semibold text-content">{label}</p>
                    {scheme ? (
                      <>
                        <p className="mt-1 text-sm text-content/70">
                          Scheme year {scheme.scheme_year} · {scheme.course_count} course
                          {scheme.course_count === 1 ? "" : "s"}
                        </p>
                        <p className="text-xs text-content/60">Uploaded {formatUploadedAt(scheme.uploaded_at)}</p>
                        {scheme.file_url && (
                          <a
                            href={scheme.file_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1 inline-flex min-h-8 items-center break-all text-xs font-medium text-primary underline"
                          >
                            {scheme.source_filename ?? "Original document"}
                          </a>
                        )}
                        <div className="mt-3 flex flex-col gap-2">
                          <Button
                            variant="secondary"
                            onClick={() => toggleCourses(scheme.id)}
                            loading={loadingId === scheme.id}
                            aria-expanded={isOpen}
                            className="w-full text-xs"
                          >
                            {isOpen ? "Hide courses" : "View courses"}
                          </Button>
                          <Button variant="danger" onClick={() => onRequestDelete(scheme)} className="w-full text-xs">
                            Delete
                          </Button>
                        </div>
                      </>
                    ) : (
                      <>
                        <p className="mt-1 text-sm text-content/60">Empty no scheme uploaded yet</p>
                        <Button onClick={() => onUpload(program.id, part)} className="mt-3 w-full text-xs">
                          Upload
                        </Button>
                      </>
                    )}

                    {isOpen && (
                      <div className="mt-4 space-y-4 border-t border-content/10 pt-4">
                        {detailError && <Alert tone="error">{detailError}</Alert>}
                        {detail?.semesters.map((semester) => (
                          <SemesterTable key={semester.semester} semester={semester} />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </section>
  );
}
