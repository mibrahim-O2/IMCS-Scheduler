export function Spinner({ className = "" }: { className?: string }) {
  // Small rotating ring shown while a request is in flight; it inherits the text colour.
  return (
    <span
      aria-hidden
      className={`inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-r-transparent ${className}`}
    />
  );
}
