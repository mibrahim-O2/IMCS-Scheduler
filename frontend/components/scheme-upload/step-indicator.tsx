const STEPS = ["Upload", "Review text", "Course rows", "Preview"] as const;

export function StepIndicator({ current }: { current: number }) {
  // Shows which of the four steps is active. Labels hide on phones so the row never overflows.
  return (
    <ol className="flex items-center gap-2 text-sm" aria-label="Progress">
      {STEPS.map((label, index) => {
        const stepNumber = index + 1;
        const isActive = stepNumber === current;
        const isDone = stepNumber < current;
        return (
          <li key={label} className="flex min-w-0 items-center gap-2">
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                isActive || isDone ? "bg-primary text-white" : "bg-content/10 text-content/60"
              }`}
              aria-current={isActive ? "step" : undefined}
            >
              {stepNumber}
            </span>
            <span className={`hidden truncate sm:inline ${isActive ? "text-content" : "text-content/60"}`}>
              {label}
            </span>
            {stepNumber < STEPS.length && <span className="h-px w-4 bg-content/20 sm:w-8" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
