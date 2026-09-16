import type { ReactNode } from "react";

const CONTROL_CLASSES =
  "w-full min-h-11 rounded-lg bg-surface px-3 py-2 text-sm text-content ring-1 ring-content/20 focus:outline-none focus:ring-2 focus:ring-primary";

export function Field({ label, children }: { label: string; children: ReactNode }) {
  // Label stacked above its control, which is what keeps the form readable on a narrow screen.
  return (
    <label className="flex w-full flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wide text-content/60">{label}</span>
      {children}
    </label>
  );
}

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  // Plain text field used for course code and name.
  return (
    <Field label={label}>
      <input
        type="text"
        className={CONTROL_CLASSES}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </Field>
  );
}

export function NumberInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  placeholder?: string;
}) {
  // Numeric field that reports null when cleared, which is how "NC" / not-applicable is stored.
  return (
    <Field label={label}>
      <input
        type="number"
        inputMode="numeric"
        className={CONTROL_CLASSES}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(event) => {
          const next = event.target.value;
          onChange(next === "" ? null : Number(next));
        }}
      />
    </Field>
  );
}

export function CheckboxInput({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  // Checkbox with a large hit area so it is usable with a thumb.
  return (
    <label className="flex min-h-11 items-center gap-2 text-sm text-content">
      <input
        type="checkbox"
        className="h-5 w-5 rounded accent-primary"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label}
    </label>
  );
}

export function SelectInput<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: string) => void;
}) {
  // Dropdown used for the program picker.
  return (
    <Field label={label}>
      <select className={CONTROL_CLASSES} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );
}
