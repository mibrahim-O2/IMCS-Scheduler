export function StatCard({ label, value, detail }: { label: string; value: number; detail: string }) {
  // One count with its label and a short explanation. A zero is shown plainly, not hidden.
  return (
    <div className="rounded-xl bg-card p-5 shadow-sm ring-1 ring-content/10">
      <p className="text-xs font-medium uppercase tracking-wide text-content/60">{label}</p>
      <p className={`mt-2 text-3xl font-semibold ${value === 0 ? "text-content/40" : "text-content"}`}>
        {value.toLocaleString()}
      </p>
      <p className="mt-1 text-sm text-content/70">{detail}</p>
    </div>
  );
}

export function StatCardSkeleton() {
  // Placeholder with the same footprint while the numbers load, so the grid doesn't jump.
  return (
    <div className="animate-pulse rounded-xl bg-card p-5 shadow-sm ring-1 ring-content/10" aria-hidden>
      <div className="h-3 w-24 rounded bg-content/10" />
      <div className="mt-3 h-8 w-16 rounded bg-content/10" />
      <div className="mt-3 h-3 w-40 rounded bg-content/10" />
    </div>
  );
}
