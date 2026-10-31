import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Field } from "../../components/Field";
import { Card, EmptyState, PageHeader } from "../../components/Layout";
import { Notice } from "../../components/Notice";
import { api } from "../../lib/api";
import { date, dateTime, today } from "../../lib/format";
import { useAction, useLocalList, useRecord } from "../../lib/hooks";

const LINK = "font-medium text-accent hover:underline";

function Outcome({ run }) {
  return (
    <div className="space-y-3" role="status">
      <dl className="grid grid-cols-3 gap-3">
        {[["Created", run.created_count], ["Skipped", run.skipped_count], ["Failed", run.failed_count]].map(([label, value]) => (
          <div key={label} className="rounded-md bg-canvas px-3 py-2.5">
            <dt className="text-[13px] text-ink-muted">{label}</dt>
            <dd className="tabular text-xl font-semibold">{value.toLocaleString("en-IN")}</dd>
          </div>
        ))}
      </dl>
      <p>
        {run.created_count > 0 && <Link to={`/invoices?billing_run=${run.id}`} className={LINK}>See the {run.created_count} new draft invoices. </Link>}
        {run.created_count === 0 && run.failed_count === 0 && "Nothing was due, so nothing was created. Every subscription is already billed up to this date, and running again can never bill it twice."}
      </p>
      {run.errors.length > 0 && (
        <details>
          <summary className="cursor-pointer font-medium">{run.errors.length} problems</summary>
          <ul className="mt-2 space-y-1 text-[13px] text-ink-muted">
            {run.errors.slice(0, 20).map((error, i) => (
              <li key={i}>
                <Link to={`/subscriptions/${error.subscription}`} className={LINK}>Subscription {error.subscription}</Link>: {error.error}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

export function BillingPage() {
  const [asOf, setAsOf] = useState(today());
  const due = useRecord(`/billing/due?as_of=${asOf}`, { enabled: Boolean(asOf) });
  const runs = useLocalList("/billing/runs");
  const [result, setResult] = useState(null);
  const run = useAction(() => api("/billing/run", { method: "POST", body: { as_of: asOf } }), { onSuccess: setResult });
  const future = asOf > today();

  return (
    <>
      <PageHeader title="Billing" subtitle="Creates an invoice for every subscription that's due. Safe to run as often as you like." />
      <div className="space-y-4">
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
          <Card title="Run billing">
            <div className="space-y-4">
              <Field
                label="Bill everything due by"
                type="date"
                value={asOf}
                onChange={(event) => { setAsOf(event.target.value); setResult(null); }}
                hint={future ? "Demo control: a future date shows what that billing day would do. Production refuses future dates." : "Normally today."}
              />
              <p className="tabular text-2xl font-semibold tracking-tight">
                {due.data ? due.data.due.toLocaleString("en-IN") : "–"}
                <span className="ml-2 text-sm font-normal text-ink-muted">subscriptions due</span>
              </p>
              <Button loading={run.isPending} disabled={!asOf} onClick={() => run.mutate()}>Run billing</Button>
              {run.error && <Notice>{run.error.message}</Notice>}
            </div>
          </Card>
          <Card title={result ? `Result for ${date(result.as_of)}` : "Result"}>
            {result ? <Outcome run={result} /> : <p className="text-ink-muted">Run billing to see what it created.</p>}
          </Card>
        </div>
        <Card title="Past runs" padded={false}>
          <DataTable
            query={runs}
            onPage={runs.setPage}
            empty={<EmptyState title="No billing runs yet" />}
            columns={[
              { header: "Started", render: (row) => dateTime(row.started_at) },
              { header: "As of", render: (row) => date(row.as_of) },
              { header: "By", render: (row) => row.triggered_by_name ?? "Command line" },
              { header: "Created", right: true, render: (row) => row.created_count > 0 ? <Link to={`/invoices?billing_run=${row.id}`} className={LINK}>{row.created_count}</Link> : 0 },
              { header: "Skipped", right: true, render: (row) => row.skipped_count },
              { header: "Failed", right: true, render: (row) => row.failed_count },
            ]}
          />
        </Card>
      </div>
    </>
  );
}
