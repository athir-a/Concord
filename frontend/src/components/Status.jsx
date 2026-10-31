import { Check, CircleAlert } from "lucide-react";

const TONE = {
  draft: "bg-canvas text-ink-muted border-line-strong",
  quotation: "bg-accent-soft text-accent border-transparent",
  confirmed: "bg-accent-soft text-accent border-transparent",
  active: "bg-success-soft text-success border-transparent",
  paused: "bg-warning-soft text-warning border-transparent",
  closed: "bg-canvas text-ink-muted border-line-strong",
  paid: "bg-success-soft text-success border-transparent",
  cancelled: "bg-canvas text-ink-muted border-line-strong",
  overdue: "bg-danger-soft text-danger border-transparent",
};

/** The same status looks the same everywhere, and is always a word, never colour alone. */
export function StatusPill({ status }) {
  return (
    <span className={`inline-flex h-6 items-center rounded-full border px-2.5 text-xs font-medium capitalize ${TONE[status] ?? TONE.draft}`}>
      {status}
    </span>
  );
}

export function InvoiceStatus({ invoice }) {
  return <StatusPill status={invoice.is_overdue ? "overdue" : invoice.status} />;
}

/** Where a record stands in its life, for anyone on the team to see at a glance. */
export function Stepper({ steps, current, note }) {
  const index = steps.findIndex((step) => step.value === current);
  return (
    <ol className="flex flex-wrap items-center gap-y-2" aria-label="Progress">
      {steps.map((step, position) => {
        const done = position < index || (position === index && step.terminal);
        const here = position === index;
        return (
          <li key={step.value} aria-current={here ? "step" : undefined} className="flex items-center">
            {position > 0 && <span aria-hidden="true" className={`mx-2 h-px w-5 sm:w-9 ${position <= index ? "bg-accent" : "bg-line-strong"}`} />}
            <span className={`flex items-center gap-1.5 ${here ? "font-semibold" : done ? "" : "text-ink-faint"}`}>
              <span
                aria-hidden="true"
                className={`flex size-5 items-center justify-center rounded-full border text-[11px] ${
                  done ? "border-accent bg-accent text-white" : here ? "border-accent text-accent" : "border-line-strong"
                }`}
              >
                {done ? <Check size={12} strokeWidth={3} /> : position + 1}
              </span>
              {step.label}
            </span>
          </li>
        );
      })}
      {note && (
        <li className="ml-3 flex items-center gap-1.5 text-warning">
          <CircleAlert size={14} aria-hidden="true" /> {note}
        </li>
      )}
    </ol>
  );
}

export const SUBSCRIPTION_STEPS = [
  { value: "draft", label: "Draft" },
  { value: "quotation", label: "Quotation" },
  { value: "confirmed", label: "Confirmed" },
  { value: "active", label: "Active" },
  { value: "closed", label: "Closed", terminal: true },
];

export const INVOICE_STEPS = [
  { value: "draft", label: "Draft" },
  { value: "confirmed", label: "Confirmed" },
  { value: "paid", label: "Paid", terminal: true },
];
