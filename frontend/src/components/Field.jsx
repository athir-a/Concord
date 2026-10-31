import { useId } from "react";

const CONTROL = "w-full rounded-md border bg-surface px-3 transition-colors duration-150 placeholder:text-ink-faint";

function Wrapper({ id, label, required, error, hint, className, children }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block font-medium">
        {label}
        {required && <span className="text-danger" aria-hidden="true"> *</span>}
      </label>
      {children}
      {(error || hint) && (
        <p id={`${id}-note`} className={`mt-1.5 text-[13px] ${error ? "text-danger" : "text-ink-muted"}`}>
          {error || hint}
        </p>
      )}
    </div>
  );
}

function controlProps(id, error, hint, required) {
  return {
    id,
    required,
    "aria-invalid": Boolean(error),
    "aria-describedby": error || hint ? `${id}-note` : undefined,
    className: `${CONTROL} ${error ? "border-danger" : "border-line-strong"}`,
  };
}

export function Field({ label, error, hint, className = "", required, ...inputProps }) {
  const id = useId();
  const { className: control, ...props } = controlProps(id, error, hint, required);
  return (
    <Wrapper {...{ id, label, required, error, hint, className }}>
      <input {...props} className={`h-9 ${control}`} {...inputProps} />
    </Wrapper>
  );
}

export function TextArea({ label, error, hint, className = "", required, ...inputProps }) {
  const id = useId();
  const { className: control, ...props } = controlProps(id, error, hint, required);
  return (
    <Wrapper {...{ id, label, required, error, hint, className }}>
      <textarea rows={3} {...props} className={`py-2 ${control}`} {...inputProps} />
    </Wrapper>
  );
}

export function SelectField({ label, error, hint, className = "", required, children, ...inputProps }) {
  const id = useId();
  const { className: control, ...props } = controlProps(id, error, hint, required);
  return (
    <Wrapper {...{ id, label, required, error, hint, className }}>
      <select {...props} className={`h-9 ${control}`} {...inputProps}>
        {children}
      </select>
    </Wrapper>
  );
}

export function CheckField({ label, hint, className = "", ...inputProps }) {
  return (
    <label className={`flex items-start gap-2.5 ${className}`}>
      <input type="checkbox" className="mt-0.5 size-4 accent-accent" {...inputProps} />
      <span>
        <span className="font-medium">{label}</span>
        {hint && <span className="block text-[13px] text-ink-muted">{hint}</span>}
      </span>
    </label>
  );
}
