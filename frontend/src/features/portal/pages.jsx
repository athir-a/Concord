import { Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../app/auth";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Card, EmptyState, ErrorState, Facts, PageHeader, PageLoading } from "../../components/Layout";
import { INVOICE_STEPS, InvoiceStatus, StatusPill, Stepper, SUBSCRIPTION_STEPS } from "../../components/Status";
import { date, INTERVALS, money } from "../../lib/format";
import { useLocalList, useRecord } from "../../lib/hooks";
import { InvoiceDocument, PaymentHistory } from "../invoices/pages";
import { InvoicePreview, LinesTable, SubscriptionActions, Timeline } from "../subscriptions/pages";

const LINK = "font-medium text-accent hover:underline";
const PORTAL_LABELS = { confirm: "Accept quotation", close: "Close subscription" };

export function PortalHomePage() {
  const { user } = useAuth();
  const subscriptions = useLocalList("/subscriptions");
  const invoices = useLocalList("/invoices");
  return (
    <>
      <PageHeader title={`Welcome, ${(user.name || user.email).split(" ")[0]}`} subtitle="Your subscriptions and invoices, without having to email anyone." />
      <div className="space-y-4">
        <Card title="Your subscriptions" padded={false}>
          <DataTable
            query={subscriptions}
            onPage={subscriptions.setPage}
            empty={<EmptyState title="No subscriptions yet">Quotations from Brightloop will appear here for you to accept.</EmptyState>}
            columns={[
              { header: "Number", render: (row) => <Link to={`/portal/subscriptions/${row.id}`} className={LINK}>{row.number}</Link> },
              { header: "Plan", render: (row) => row.plan_name },
              { header: "Status", render: (row) => <StatusPill status={row.status} /> },
              { header: "Next billing", render: (row) => date(row.next_billing_date) },
              { header: "Per period", right: true, render: (row) => `${money(row.recurring_subtotal)} / ${INTERVALS[row.interval]}` },
            ]}
          />
        </Card>
        <Card title="Your invoices" padded={false}>
          <DataTable
            query={invoices}
            onPage={invoices.setPage}
            empty={<EmptyState title="No invoices yet" />}
            columns={[
              { header: "Number", render: (row) => <Link to={`/portal/invoices/${row.id}`} className={LINK}>{row.number}</Link> },
              { header: "Status", render: (row) => <InvoiceStatus invoice={row} /> },
              { header: "Issued", render: (row) => date(row.issue_date) },
              { header: "Due", render: (row) => date(row.due_date) },
              { header: "Total", right: true, render: (row) => money(row.total, row.currency) },
              { header: "To pay", right: true, render: (row) => (row.status === "confirmed" ? money(row.amount_due, row.currency) : "–") },
            ]}
          />
        </Card>
      </div>
    </>
  );
}

export function PortalSubscriptionPage() {
  const { id } = useParams();
  const subscription = useRecord(`/subscriptions/${id}`);
  const invoices = useLocalList("/invoices", { subscription: id });
  if (subscription.isLoading) return <PageLoading />;
  if (subscription.error) return <ErrorState error={subscription.error} retry={subscription.refetch} />;
  const s = subscription.data;
  return (
    <>
      <PageHeader
        eyebrow={<Link to="/portal" className={LINK}>Your account</Link>}
        title={s.number}
        subtitle={s.plan_name}
        actions={<SubscriptionActions subscription={s} labels={PORTAL_LABELS} />}
      />
      <div className="space-y-4">
        <Card>
          <Stepper steps={SUBSCRIPTION_STEPS} current={s.status === "paused" ? "active" : s.status} note={s.status === "paused" ? "Paused: not billing" : null} />
        </Card>
        <Card>
          <Facts items={[
            ["Billed every", INTERVALS[s.interval]],
            ["Start", date(s.start_date)],
            ["Expires", date(s.expiry_date)],
            ["Next billing", date(s.next_billing_date)],
            ["Payment terms", `${s.payment_terms_days} days`],
            ["Discount", s.discount_name ?? "None"],
            ...(s.quote_valid_until ? [["Offer valid until", date(s.quote_valid_until)]] : []),
          ]} />
        </Card>
        <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-3">
          <Card title="What's included" padded={false} className="md:col-span-2"><LinesTable lines={s.lines} /></Card>
          {s.status !== "closed" && <Card title="Each invoice"><InvoicePreview subscriptionId={s.id} /></Card>}
        </div>
        <Card title="Invoices" padded={false}>
          <DataTable
            query={invoices}
            onPage={invoices.setPage}
            empty={<EmptyState title="No invoices yet" />}
            columns={[
              { header: "Number", render: (row) => <Link to={`/portal/invoices/${row.id}`} className={LINK}>{row.number}</Link> },
              { header: "Status", render: (row) => <InvoiceStatus invoice={row} /> },
              { header: "Due", render: (row) => date(row.due_date) },
              { header: "Total", right: true, render: (row) => money(row.total, row.currency) },
            ]}
          />
        </Card>
        <Card title="History"><Timeline events={s.events} /></Card>
      </div>
    </>
  );
}

export function PortalInvoicePage() {
  const { id } = useParams();
  const invoice = useRecord(`/invoices/${id}`);
  if (invoice.isLoading) return <PageLoading />;
  if (invoice.error) return <ErrorState error={invoice.error} retry={invoice.refetch} />;
  const inv = invoice.data;
  return (
    <>
      <PageHeader
        eyebrow={<Link to="/portal" className={LINK}>Your account</Link>}
        title={inv.number}
        actions={<Link to={`/invoices/${inv.id}/print`} target="_blank"><Button variant="secondary"><Printer size={15} aria-hidden="true" /> Print</Button></Link>}
      />
      <div className="space-y-4">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            {inv.status !== "cancelled" && <Stepper steps={INVOICE_STEPS} current={inv.status} />}
            <InvoiceStatus invoice={inv} />
          </div>
        </Card>
        <Card><InvoiceDocument invoice={inv} /></Card>
        <Card title="Payments"><PaymentHistory invoice={inv} /></Card>
      </div>
    </>
  );
}
