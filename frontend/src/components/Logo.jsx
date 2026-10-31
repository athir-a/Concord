/** Two overlapping circles: separate things, in sync. */
export function Logo({ className = "" }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-tight ${className}`}>
      <svg width="22" height="14" viewBox="0 0 22 14" fill="none" aria-hidden="true">
        <circle cx="7" cy="7" r="6" stroke="var(--color-accent)" strokeWidth="2" />
        <circle cx="15" cy="7" r="6" stroke="currentColor" strokeWidth="2" />
      </svg>
      Concord
    </span>
  );
}
