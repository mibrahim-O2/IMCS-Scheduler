import type { ButtonHTMLAttributes } from "react";

import { Spinner } from "@/components/ui/spinner";

type Variant = "primary" | "secondary" | "danger";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary/90",
  secondary: "bg-surface text-content ring-1 ring-content/20 hover:bg-content/5",
  danger: "bg-status-conflict text-white hover:bg-status-conflict/90",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
};

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  className = "",
  children,
  ...props
}: ButtonProps) {
  // One button style for the whole app. min-h-11 keeps it a comfortable tap target on phones,
  // and `loading` disables it and shows a spinner so it never looks dead mid-request.
  return (
    <button
      disabled={disabled || loading}
      aria-busy={loading}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}
