/**
 * Reads course rows out of text extracted from a University of Sindh course
 * scheme page. It only pre-fills the form the admin still checks every row.
 */

import { pairLabRows, type SemesterRows } from "@/lib/schemes";

export type ParsedScheme = {
  semesters: SemesterRows[];
  schemeYear: number | null;
  programLabel: string | null;
};

const ORDINALS = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH", "EIGHTH"];
const SEMESTER_HEADING = /^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH)\s+SEMESTER$/i;
// "1 CSPF302 PROGRAMMING FUNDAMENTALS 3 50 100" serial, code, name, credits (or NC), min, max.
const COURSE_LINE = /^\d+\s+([A-Z]{3,5}\d{3})\s+(.+?)\s+(NC|\d+)\s+(\d+)\s+(\d+)$/i;
const SCHEME_YEAR = /Scheme\s+Year\s+(\d{4})/i;
const PROGRAM_LINE = /^Program\s+(.+)$/im;

export function parseSchemeText(text: string): ParsedScheme {
  // Walks the text line by line: a "FIRST SEMESTER" heading opens a semester, and matching
  // lines under it become course rows. The portal prints the whole scheme twice, so parsing
  // stops as soon as a semester number repeats. Lab rows are paired onto their theory course.
  const semesters: SemesterRows[] = [];
  let current: SemesterRows | null = null;

  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim().replace(/\s+/g, " ");

    const heading = SEMESTER_HEADING.exec(line);
    if (heading) {
      const number = ORDINALS.indexOf(heading[1].toUpperCase()) + 1;
      if (semesters.some((semester) => semester.semester === number)) break;
      current = { semester: number, courses: [] };
      semesters.push(current);
      continue;
    }

    const row = current ? COURSE_LINE.exec(line) : null;
    if (current && row) {
      const [, code, name, credits, minMarks, maxMarks] = row;
      current.courses.push({
        code: code.toUpperCase(),
        name: name.trim(),
        credit_hours: credits.toUpperCase() === "NC" ? null : Number(credits),
        has_lab: false,
        lab_credit_hours: null,
        min_marks: Number(minMarks),
        max_marks: Number(maxMarks),
      });
    }
  }

  const year = SCHEME_YEAR.exec(text);
  const program = PROGRAM_LINE.exec(text);
  return {
    semesters: semesters
      .filter((semester) => semester.courses.length > 0)
      .map((semester) => ({ ...semester, courses: pairLabRows(semester.courses) })),
    schemeYear: year ? Number(year[1]) : null,
    programLabel: program ? program[1].trim() : null,
  };
}

export function comparableProgramName(name: string): string {
  // "BS (COMPUTER SCIENCE)" and "BS Computer Science" both become "BS COMPUTER SCIENCE" so
  // two spellings of the same program can be compared for equality.
  return name.replace(/[^A-Za-z0-9]+/g, " ").trim().toUpperCase();
}
