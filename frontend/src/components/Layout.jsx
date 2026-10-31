import { Button } from "./Button";

export function PageHeader({ title, subtitle, actions, eyebrow }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1 text-[13px] text-ink-muted">{eyebrow}</div>}
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-ink-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, actions, className = "", padded = true, children }) {
  return (
    <section className={`rounded-lg border border-line bg-surface ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="font-semibold">{title}</h2>
          {actions}
        </div>
      )}
      <div className={padded ? "p-4" : ""}>{children}</div>
    </section>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="px-4 py-12 text-center">
      <p className="font-medium">{title}</p>
      {children && <p className="mx-auto mt-1 max-w-sm text-ink-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, retry }) {
  return (
    <div role="alert" className="px-4 py-12 text-center">
      <p className="font-medium">{error?.status === 404 ? "We couldn't find that." : "This didn't load."}</p>
      <p className="mt-1 text-ink-muted">{error?.message}</p>
      {retry && error?.status !== 404 && (
        <Button variant="secondary" className="mt-4" onClick={retry}>Try again</Button>
      )}
    </div>
  );
}

export function Skeleton({ className = "" }) {
  return <div aria-hidden="true" className={`animate-pulse rounded bg-line/70 ${className}`} />;
}

export function PageLoading() {
  return (
    <div role="status" aria-label="Loading" className="space-y-4">
      <Skeleton className="h-7 w-56" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

/** Label and value pairs for detail pages. */
export function Facts({ items }) {
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-4">
      {items.map(([label, value]) => (
        <div key={label} className="min-w-0">
          <dt className="text-[13px] text-ink-muted">{label}</dt>
          <dd className="mt-0.5 break-words font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
