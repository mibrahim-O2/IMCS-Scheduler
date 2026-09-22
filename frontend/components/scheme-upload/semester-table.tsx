import type { SemesterRows } from "@/lib/schemes";

export function SemesterTable({ semester }: { semester: SemesterRows }) {
  // One semester's courses as a table. On a narrow screen the table scrolls sideways inside
  // its own box, so the page itself never does.
  const count = semester.courses.length;
  return (
    <div className="rounded-xl bg-surface ring-1 ring-content/15">
      <h3 className="px-4 py-3 text-sm font-semibold text-content">
        Semester {semester.semester} · {count} course{count === 1 ? "" : "s"}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead className="bg-content/5 text-xs uppercase tracking-wide text-content/60">
            <tr>
              <th className="px-4 py-2 font-medium">Code</th>
              <th className="px-4 py-2 font-medium">Course</th>
              <th className="px-4 py-2 font-medium">Credit hrs</th>
              <th className="px-4 py-2 font-medium">Lab</th>
              <th className="px-4 py-2 font-medium">Marks</th>
            </tr>
          </thead>
          <tbody>
            {semester.courses.map((course, index) => (
              <tr key={`${course.code}-${index}`} className="border-t border-content/10">
                <td className="whitespace-nowrap px-4 py-2 font-mono text-xs">{course.code}</td>
                <td className="px-4 py-2">{course.name}</td>
                <td className="px-4 py-2">{course.credit_hours ?? "NC"}</td>
                <td className="whitespace-nowrap px-4 py-2">
                  {course.has_lab ? (
                    <span className="rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-content">
                      Lab · {course.lab_credit_hours ?? "?"} cr
                    </span>
                  ) : (
                    <span className="text-content/40"> </span>
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-2">
                  {course.min_marks ?? " "} / {course.max_marks ?? " "}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
