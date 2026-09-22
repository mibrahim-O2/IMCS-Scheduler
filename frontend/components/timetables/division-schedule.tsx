import type { DivisionSchedule } from "@/lib/timetables";

export function DivisionScheduleTable({ schedule }: { schedule: DivisionSchedule }) {
  // One division's whole week as a single table, flattened day by day (each day's rows
  // already come pre-sorted by time from the backend). A flat table scrolls sideways
  // inside its own box on a phone instead of forcing a rigid day/period grid to fit 
  // same pattern as the Course Scheme feature's SemesterTable.
  const totalSessions = schedule.days.reduce((sum, day) => sum + day.sessions.length, 0);

  return (
    <div className="rounded-xl bg-surface ring-1 ring-content/15">
      <h3 className="px-4 py-3 text-sm font-semibold text-content">
        {schedule.division_label} · {totalSessions} session{totalSessions === 1 ? "" : "s"}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[38rem] text-left text-sm">
          <thead className="bg-content/5 text-xs uppercase tracking-wide text-content/60">
            <tr>
              <th className="px-4 py-2 font-medium">Day</th>
              <th className="px-4 py-2 font-medium">Time</th>
              <th className="px-4 py-2 font-medium">Course</th>
              <th className="px-4 py-2 font-medium">Teacher</th>
              <th className="px-4 py-2 font-medium">Room</th>
            </tr>
          </thead>
          <tbody>
            {schedule.days.map((day) =>
              day.sessions.map((session, index) => (
                <tr key={`${day.day}-${index}`} className="border-t border-content/10">
                  <td className="whitespace-nowrap px-4 py-2">{index === 0 ? day.day : ""}</td>
                  <td className="whitespace-nowrap px-4 py-2 font-mono text-xs">
                    {session.start_time.slice(0, 5)}–{session.end_time.slice(0, 5)}
                  </td>
                  <td className="px-4 py-2">
                    {session.course_code} {session.course_name}
                    {session.is_lab && (
                      <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-content">
                        Lab
                      </span>
                    )}
                    {session.division_labels.length > 1 && (
                      <span className="ml-2 text-xs text-content/60">(joint session)</span>
                    )}
                  </td>
                  <td className="px-4 py-2">{session.teacher_name}</td>
                  <td className="px-4 py-2">{session.room_name}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
