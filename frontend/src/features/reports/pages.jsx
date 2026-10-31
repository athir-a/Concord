import { ChevronRight } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/auth";
import { Field, SelectField } from "../../components/Field";
import { Card, ErrorState, PageHeader, PageLoading } from "../../components/Layout";
import { RevenueChart } from "../../components/RevenueChart";
import { addDays, money, month, today, wholeMoney } from "../../lib/format";
import { useOptions, useRecord } from "../../lib/hooks";

function withParams(path, params) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value)).toString();
  return query ? `${path}?${query}` : path;
}

function Figure({ label, value, note, title }) {
  return (
    <div title={title}>
      <p className="text-[13px] text-ink-muted">{label}</p>
      <p className="tabular mt-0.5 text-xl font-semibold tracking-tight">{value}</p>
      {note && <p className="mt-0.5 text-[13px] text-ink-muted">{note}</p>}
    </div>
  );
}

function AttentionRow({ to, count, label, detail }) {
  return (
    <li>
      <Link to={to} className="flex items-center gap-3 px-4 py-3 transition-colors duration-150 hover:bg-canvas/70">
        <span className={`tabular w-10 text-right text-lg font-semibold ${count ? "" : "text-ink-faint"}`}>{count.toLocaleString("en-IN")}</span>
        <span className="min-w-0 flex-1">
          <span className="block font-medium">{label}</span>
          {detail && <span className="block text-[13px] text-ink-muted">{detail}</span>}
        </span>
        <ChevronRight size={16} aria-hidden="true" className="shrink-0 text-ink-faint" />
      </Link>
    </li>
  );
}

const MRR_NOTE = "Active subscriptions converted to a month. Excludes tax, before discounts.";

/** Leads with what needs doing today rather than with a row of numbers. */
export function OverviewPage() {
  const { user } = useAuth();
  const summary = useRecord("/reports/summary");
  const series = useRecord("/reports/revenue-series");

  if (summary.isLoading || series.isLoading) return <PageLoading />;
  const error = summary.error || series.error;
  if (error) return <ErrorState error={error} retry={() => { summary.refetch(); series.refetch(); }} />;
  const s = summary.data;

  return (
    <>
      <PageHeader title="Overview" subtitle={`Good to see you, ${(user.name || user.email).split(" ")[0]}. Here's what needs attention.`} />
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-5">
        <Card title="Needs attention" padded={false} className="lg:col-span-2">
          <ul className="divide-y divide-line">
            <AttentionRow to="/invoices?overdue=true&ordering=due_date" count={s.overdue_count} label="Overdue invoices" detail={`${money(s.overdue)} to chase`} />
            <AttentionRow to={withParams("/subscriptions", { status: "active", expires_by: addDays(today(), 30), ordering: "expiry_date" })} count={s.renewals_due} label="Renewals due" detail="Expiring within 30 days" />
            <AttentionRow to="/invoices?status=draft" count={s.draft_invoices} label="Draft invoices" detail="Waiting to be confirmed" />
            <AttentionRow to="/subscriptions?status=quotation" count={s.quotations_awaiting_reply} label="Quotations out" detail="Waiting on the customer" />
            <AttentionRow to="/subscriptions?status=confirmed" count={s.confirmed_awaiting_activation} label="Ready to activate" detail="Confirmed, not started" />
          </ul>
        </Card>
        <div className="space-y-4 lg:col-span-3">
          <Card>
            <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
              <Figure label="MRR" value={wholeMoney(s.mrr)} title={MRR_NOTE} />
              <Figure label="Active" value={s.active_subscriptions.toLocaleString("en-IN")} note={`${s.paused_subscriptions} paused`} />
              <Figure label="Collected" value={wholeMoney(s.collected)} note="All time" />
              <Figure label="Outstanding" value={wholeMoney(s.outstanding)} note={`${s.outstanding_count.toLocaleString("en-IN")} invoices`} />
            </div>
          </Card>
          <Card title="Invoiced and collected" actions={<Link to="/reports" className="text-[13px] font-medium text-accent hover:underline">Open reports</Link>}>
            <RevenueChart data={series.data} height={220} />
          </Card>
        </div>
      </div>
    </>
  );
}

export function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = Object.fromEntries(searchParams);
  const plans = useOptions("/plans");
  const summary = useRecord(withParams("/reports/summary", params));
  const series = useRecord(withParams("/reports/revenue-series", { plan: params.plan }));
  const ageing = useRecord(withParams("/reports/overdue-ageing", { plan: params.plan }));

  const setParam = (name, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(name, value);
    else next.delete(name);
    setSearchParams(next, { replace: true });
  };
  const s = summary.data;
  const error = summary.error || series.error || ageing.error;

  return (
    <>
      <PageHeader title="Reports" subtitle="Active subscriptions, revenue, payments and overdue invoices, calculated live from the records." />
      <Card className="mb-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="From" type="date" value={params.date_from ?? ""} onChange={(e) => setParam("date_from", e.target.value)} error={summary.error?.fields?.date_from} />
          <Field label="To" type="date" value={params.date_to ?? ""} onChange={(e) => setParam("date_to", e.target.value)} error={summary.error?.fields?.date_to} />
          <SelectField label="Plan" value={params.plan ?? ""} onChange={(e) => setParam("plan", e.target.value)}>
            <option value="">All plans</option>
            {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </SelectField>
        </div>
        <p className="mt-3 text-[13px] text-ink-muted">Dates narrow invoiced and collected. The rest shows the position today.</p>
      </Card>
      {error && !s ? <ErrorState error={error} retry={summary.refetch} /> : !s ? <PageLoading /> : (
        <div className="space-y-4">
          <Card title="Summary">
            <div className="grid grid-cols-2 gap-5 md:grid-cols-4">
              <Figure label="Invoiced" value={wholeMoney(s.invoiced)} note="What we asked for" />
              <Figure label="Collected" value={wholeMoney(s.collected)} note="What arrived" />
              <Figure label="Outstanding" value={wholeMoney(s.outstanding)} note={`${s.outstanding_count.toLocaleString("en-IN")} invoices`} />
              <Figure label="Overdue" value={wholeMoney(s.overdue)} note={`${s.overdue_count.toLocaleString("en-IN")} invoices`} />
              <Figure label="Active subscriptions" value={s.active_subscriptions.toLocaleString("en-IN")} note={`${s.paused_subscriptions} paused`} />
              <Figure label="MRR" value={wholeMoney(s.mrr)} note="Before discounts, excl. tax" title={MRR_NOTE} />
              <Figure label="ARR" value={wholeMoney(s.arr)} note="MRR x 12" />
              <Figure label="Renewals due" value={s.renewals_due.toLocaleString("en-IN")} note="Within 30 days" />
            </div>
          </Card>
          <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-3">
            <Card title="Last 12 months" className="lg:col-span-2">
              {series.data ? <RevenueChart data={series.data} /> : <PageLoading />}
            </Card>
            <Card title="How late is the overdue money?" padded={false}>
              {ageing.data && (
                <ul className="divide-y divide-line">
                  {ageing.data.map((bucket) => (
                    <li key={bucket.label} className="tabular flex items-center justify-between gap-3 px-4 py-3">
                      <span>
                        <span className="block font-medium">{bucket.label}</span>
                        <span className="block text-[13px] text-ink-muted">{bucket.count.toLocaleString("en-IN")} invoices</span>
                      </span>
                      <span className="font-semibold">{money(bucket.amount)}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="border-t border-line px-4 py-3">
                <Link to="/invoices?overdue=true&ordering=due_date" className="text-[13px] font-medium text-accent hover:underline">See overdue invoices</Link>
              </div>
            </Card>
          </div>
          {series.data && (
            <Card title="By month" padded={false}>
              <div className="overflow-x-auto">
                <table className="tabular w-full min-w-[420px] text-left">
                  <thead>
                    <tr className="border-b border-line text-[13px] text-ink-muted">
                      <th scope="col" className="px-4 py-2.5 font-medium">Month</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-medium">Invoiced</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-medium">Collected</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...series.data].reverse().map((row) => (
                      <tr key={row.month} className="border-b border-line last:border-0">
                        <td className="px-4 py-2.5">{month(row.month)}</td>
                        <td className="px-4 py-2.5 text-right">{money(row.invoiced)}</td>
                        <td className="px-4 py-2.5 text-right">{money(row.collected)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </>
  );
}
