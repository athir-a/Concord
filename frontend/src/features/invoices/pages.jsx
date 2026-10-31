import { Printer } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button } from "../../components/Button";
import { DataTable, FilterSelect, SearchBox, TableToolbar, listProps } from "../../components/DataTable";
import { Dialog } from "../../components/Dialog";
import { Field, SelectField } from "../../components/Field";
import { Card, EmptyState, ErrorState, PageHeader, PageLoading } from "../../components/Layout";
import { Logo } from "../../components/Logo";
import { Notice } from "../../components/Notice";
import { INVOICE_STEPS, InvoiceStatus, Stepper } from "../../components/Status";
import { api } from "../../lib/api";
import { date, dateTime, money, newKey, PAYMENT_METHODS, titleCase, today } from "../../lib/format";
import { useAction, useListPage, useRecord } from "../../lib/hooks";
import { useForm } from "../../lib/useForm";

const LINK = "font-medium text-accent hover:underline";
const STATUSES = [["draft", "Draft"], ["confirmed", "Confirmed"], ["paid", "Paid"], ["cancelled", "Cancelled"]];

export function InvoicesPage() {
  const list = useListPage("/invoices");
  const drafts = (list.data?.results ?? []).filter((row) => row.status === "draft").map((row) => row.id);
  const confirmAll = useAction(() => api("/invoices/bulk-confirm", { method: "POST", body: { invoices: drafts } }));
  const columns = [
    { header: "Number", sort: "number", render: (row) => <Link to={`/invoices/${row.id}`} className={LINK}>{row.number}</Link> },
    { header: "Customer", render: (row) => row.customer_name },
    { header: "Status", sort: "status", render: (row) => <InvoiceStatus invoice={row} /> },
    { header: "Issued", sort: "issue_date", render: (row) => date(row.issue_date) },
    { header: "Due", sort: "due_date", render: (row) => date(row.due_date) },
    { header: "Total", right: true, sort: "total", render: (row) => money(row.total, row.currency) },
    { header: "Outstanding", right: true, render: (row) => (row.status === "confirmed" ? money(row.amount_due, row.currency) : "–") },
  ];
  return (
    <>
      <PageHeader
        title="Invoices"
        subtitle="Created from subscriptions by billing runs. Nobody types them by hand."
        actions={drafts.length > 0 && list.params.status === "draft" && (
          <Button loading={confirmAll.isPending} onClick={() => confirmAll.mutate()}>Confirm {drafts.length} on this page</Button>
        )}
      />
      <Card padded={false}>
        <TableToolbar>
          <SearchBox value={list.params.search} onChange={(v) => list.setParam("search", v)} placeholder="Search number or customer" />
          <FilterSelect label="Status" value={list.params.status} onChange={(v) => list.setParam("status", v)} options={STATUSES} />
          <FilterSelect label="Overdue" value={list.params.overdue} onChange={(v) => list.setParam("overdue", v)} options={[["true", "Overdue only"], ["false", "Not overdue"]]} />
          {list.params.billing_run && <Button variant="ghost" onClick={() => list.setParam("billing_run", "")}>Clear billing run filter</Button>}
        </TableToolbar>
        {confirmAll.error && <div className="p-3"><Notice>{confirmAll.error.message}</Notice></div>}
        <DataTable columns={columns} {...listProps(list)} empty={<EmptyState title="No invoices match">Try clearing the filters.</EmptyState>} />
      </Card>
    </>
  );
}

/** The invoice itself. Used by staff, the customer portal and the printed page. */
export function InvoiceDocument({ invoice }) {
  const period = `${date(invoice.period_start)} to ${date(invoice.period_end)}`;
  return (
    <article>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Logo className="text-base" />
          <p className="mt-2 text-[13px] text-ink-muted">Brightloop Software</p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold tracking-tight">{invoice.number}</p>
          <p className="text-[13px] text-ink-muted">Issued {date(invoice.issue_date)}</p>
          <p className="text-[13px] text-ink-muted">Due {date(invoice.due_date)}</p>
        </div>
      </header>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-[13px] text-ink-muted">Billed to</p>
          <p className="font-medium">{invoice.customer_name}</p>
          <p className="text-ink-muted">{invoice.customer_email}</p>
          {invoice.customer_address && <p className="whitespace-pre-line text-ink-muted">{invoice.customer_address}</p>}
        </div>
        <div className="sm:text-right">
          <p className="text-[13px] text-ink-muted">Billing period</p>
          <p className="font-medium">{period}</p>
          <p className="text-ink-muted">{invoice.subscription_number}</p>
        </div>
      </div>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[560px] text-left">
          <thead>
            <tr className="border-b border-line-strong text-[13px] text-ink-muted">
              <th scope="col" className="py-2 pr-3 font-medium">Item</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Qty</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Unit price</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Discount</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Tax</th>
              <th scope="col" className="py-2 pl-3 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="tabular">
            {invoice.lines.map((line) => (
              <tr key={line.id} className="border-b border-line">
                <td className="py-2.5 pr-3">{line.description}</td>
                <td className="px-3 py-2.5 text-right">{line.quantity}</td>
                <td className="px-3 py-2.5 text-right">{money(line.unit_price, invoice.currency)}</td>
                <td className="px-3 py-2.5 text-right">{Number(line.discount_amount) > 0 ? `-${money(line.discount_amount, invoice.currency)}` : "–"}</td>
                <td className="px-3 py-2.5 text-right">
                  {money(line.tax_amount, invoice.currency)}
                  {line.tax_name && <span className="block text-xs text-ink-muted">{line.tax_name}</span>}
                </td>
                <td className="py-2.5 pl-3 text-right">{money(line.line_total, invoice.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="tabular mt-4 ml-auto max-w-xs space-y-1.5">
        <Total label="Subtotal" value={money(invoice.subtotal, invoice.currency)} />
        {Number(invoice.discount_total) > 0 && <Total label="Discount" value={`-${money(invoice.discount_total, invoice.currency)}`} />}
        <Total label="Tax" value={money(invoice.tax_total, invoice.currency)} />
        <div className="flex justify-between border-t border-line-strong pt-1.5 font-semibold"><dt>Total</dt><dd>{money(invoice.total, invoice.currency)}</dd></div>
        <Total label="Paid" value={money(invoice.amount_paid, invoice.currency)} />
        <div className="flex justify-between font-semibold"><dt>Balance due</dt><dd>{money(invoice.status === "cancelled" ? 0 : invoice.amount_due, invoice.currency)}</dd></div>
      </dl>
    </article>
  );
}

function Total({ label, value }) {
  return <div className="flex justify-between"><dt className="text-ink-muted">{label}</dt><dd>{value}</dd></div>;
}

export function PaymentHistory({ invoice }) {
  if (invoice.payments.length === 0) return <p className="text-ink-muted">No payments recorded yet.</p>;
  return (
    <ul className="space-y-3">
      {invoice.payments.map((payment) => (
        <li key={payment.id}>
          <p className="tabular flex justify-between gap-3 font-medium">
            <span>{titleCase(payment.method)}</span>
            <span>{money(payment.amount, invoice.currency)}</span>
          </p>
          <p className="text-[13px] text-ink-muted">
            {date(payment.paid_on)}{payment.recorded_by_name ? ` by ${payment.recorded_by_name}` : ""}
          </p>
          {payment.note && <p className="text-[13px] text-ink-muted">{payment.note}</p>}
        </li>
      ))}
    </ul>
  );
}

function RecordPaymentDialog({ invoice, onClose }) {
  // One key per dialog: a double click or a retry can't record the same payment twice.
  const key = useMemo(newKey, []);
  const save = useAction((body) => api(`/invoices/${invoice.id}/payments`, { method: "POST", body }), { onSuccess: onClose });
  const form = useForm(
    { amount: invoice.amount_due, method: "bank_transfer", paid_on: today(), note: "" },
    (values) => save.mutateAsync({ ...values, idempotency_key: key }),
  );
  return (
    <Dialog title={`Record payment on ${invoice.number}`} onClose={onClose}>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <Field label="Amount" type="number" step="0.01" min="0.01" max={invoice.amount_due} required hint={`${money(invoice.amount_due, invoice.currency)} outstanding`} {...form.field("amount")} />
        <SelectField label="Method" required {...form.field("method")}>
          {PAYMENT_METHODS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </SelectField>
        <Field label="Payment date" type="date" max={today()} required {...form.field("paid_on")} />
        <Field label="Note" placeholder="For example, a bank reference" {...form.field("note")} />
        <Button type="submit" loading={form.submitting} className="w-full">Record payment</Button>
      </form>
    </Dialog>
  );
}

export function InvoiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const invoice = useRecord(`/invoices/${id}`);
  const [dialog, setDialog] = useState(null);
  const act = useAction((name) => api(`/invoices/${id}/${name}`, { method: "POST" }), {
    onSuccess: (data) => {
      setDialog(null);
      if (String(data.id) !== String(id)) navigate(`/invoices/${data.id}`);
    },
  });

  if (invoice.isLoading) return <PageLoading />;
  if (invoice.error) return <ErrorState error={invoice.error} retry={invoice.refetch} />;
  const inv = invoice.data;
  const { status } = inv;
  const canCancel = ["draft", "confirmed"].includes(status) && Number(inv.amount_paid) === 0;

  return (
    <>
      <PageHeader
        eyebrow={<Link to="/invoices" className={LINK}>Invoices</Link>}
        title={inv.number}
        subtitle={<Link to={`/subscriptions/${inv.subscription}`} className={LINK}>{inv.subscription_number}</Link>}
        actions={
          <>
            <Link to={`/invoices/${inv.id}/print`} target="_blank"><Button variant="secondary"><Printer size={15} aria-hidden="true" /> Print</Button></Link>
            {canCancel && <Button variant="secondary" onClick={() => setDialog("cancel")}>Cancel invoice</Button>}
            {status === "cancelled" && <Button variant="secondary" loading={act.isPending} onClick={() => act.mutate("reissue")}>Reissue</Button>}
            {["confirmed", "paid"].includes(status) && <Button variant="secondary" loading={act.isPending && act.variables === "send"} onClick={() => act.mutate("send")}>{inv.sent_at ? "Send again" : "Send"}</Button>}
            {status === "draft" && <Button loading={act.isPending} onClick={() => act.mutate("confirm")}>Confirm</Button>}
            {status === "confirmed" && <Button onClick={() => setDialog("pay")}>Record payment</Button>}
          </>
        }
      />
      {act.error && !dialog && <div className="mb-4"><Notice>{act.error.message}</Notice></div>}
      <div className="space-y-4">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            {status === "cancelled"
              ? <p className="text-ink-muted">Cancelled {dateTime(inv.cancelled_at)}. This period can be reissued.</p>
              : <Stepper steps={INVOICE_STEPS} current={status} />}
            <InvoiceStatus invoice={inv} />
          </div>
        </Card>
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2"><InvoiceDocument invoice={inv} /></Card>
          <div className="space-y-4">
            <Card title="Payments"><PaymentHistory invoice={inv} /></Card>
            <Card title="Sent">
              <p className={inv.sent_at ? "" : "text-ink-muted"}>{inv.sent_at ? `Sent to ${inv.customer_email}, ${dateTime(inv.sent_at)}` : "Not sent yet."}</p>
            </Card>
          </div>
        </div>
      </div>
      {dialog === "pay" && <RecordPaymentDialog invoice={inv} onClose={() => setDialog(null)} />}
      {dialog === "cancel" && (
        <Dialog title={`Cancel ${inv.number}?`} onClose={() => { setDialog(null); act.reset(); }}>
          <p className="text-ink-muted">It stays on record as cancelled, and the billing period can be reissued afterwards.</p>
          {act.error && <div className="mt-3"><Notice>{act.error.message}</Notice></div>}
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => { setDialog(null); act.reset(); }}>Keep it</Button>
            <Button loading={act.isPending} onClick={() => act.mutate("cancel")}>Cancel invoice</Button>
          </div>
        </Dialog>
      )}
    </>
  );
}

export function InvoicePrintPage() {
  const { id } = useParams();
  const invoice = useRecord(`/invoices/${id}`);
  useEffect(() => {
    if (invoice.data) window.print();
  }, [invoice.data]);

  if (invoice.isLoading) return <div className="p-8"><PageLoading /></div>;
  if (invoice.error) return <ErrorState error={invoice.error} />;
  return (
    <main className="mx-auto max-w-3xl bg-surface p-8 print:max-w-none print:p-0">
      <div className="no-print mb-6 flex justify-end">
        <Button variant="secondary" onClick={() => window.print()}><Printer size={15} aria-hidden="true" /> Print</Button>
      </div>
      <InvoiceDocument invoice={invoice.data} />
      {invoice.data.status === "paid" && <p className="mt-6 font-semibold text-success">Paid in full</p>}
      {invoice.data.status === "cancelled" && <p className="mt-6 font-semibold text-danger">Cancelled</p>}
    </main>
  );
}
