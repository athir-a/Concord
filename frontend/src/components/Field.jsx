import { useId } from "react";

export function Field({ label, error, hint, className = "", ...inputProps }) {
  const id = useId();
  const describedBy = error || hint ? `${id}-note` : undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block font-medium">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        className={`h-9 w-full rounded-md border bg-surface px-3 transition-colors duration-150 placeholder:text-ink-faint ${
          error ? "border-danger" : "border-line-strong"
        }`}
        {...inputProps}
      />
      {(error || hint) && (
        <p id={describedBy} className={`mt-1.5 text-[13px] ${error ? "text-danger" : "text-ink-muted"}`}>
          {error || hint}
        </p>
      )}
    </div>
  );
}
