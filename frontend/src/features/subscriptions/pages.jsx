import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button } from "../../components/Button";
import { DataTable, FilterSelect, SearchBox, TableToolbar, listProps } from "../../components/DataTable";
import { Dialog } from "../../components/Dialog";
import { Field, SelectField } from "../../components/Field";
import { Card, EmptyState, ErrorState, Facts, PageHeader, PageLoading } from "../../components/Layout";
import { Notice } from "../../components/Notice";
import { InvoiceStatus, StatusPill, Stepper, SUBSCRIPTION_STEPS } from "../../components/Status";
import { api } from "../../lib/api";
import { addDays, date, dateTime, INTERVALS, money, today } from "../../lib/format";
import { useAction, useDebounced, useListPage, useLocalList, useOptions, useRecord } from "../../lib/hooks";
import { useForm } from "../../lib/useForm";

const LINK = "font-medium text-accent hover:underline";
const STATUSES = ["draft", "quotation", "confirmed", "active", "paused", "closed"].map((s) => [s, s[0].toUpperCase() + s.slice(1)]);

export function SubscriptionsPage() {
  const list = useListPage("/subscriptions");
  const plans = useOptions("/plans");
  const columns = [
    { header: "Number", sort: "number", render: (row) => <Link to={`/subscriptions/${row.id}`} className={LINK}>{row.number}</Link> },
    { header: "Customer", render: (row) => row.customer_name },
    { header: "Plan", render: (row) => row.plan_name },
    { header: "Status", render: (row) => <StatusPill status={row.status} /> },
    { header: "Next billing", sort: "next_billing_date", render: (row) => date(row.next_billing_date) },
    { header: "Expires", sort: "expiry_date", render: (row) => date(row.expiry_date) },
    { header: "Per period", right: true, sort: "recurring_subtotal", render: (row) => `${money(row.recurring_subtotal)} / ${INTERVALS[row.interval]}` },
  ];
  return (
    <>
      <PageHeader
        title="Subscriptions"
        subtitle={list.params.expires_by ? `Expiring by ${date(list.params.expires_by)}` : "Every customer's subscription and where it stands."}
        actions={<Link to="/subscriptions/new"><Button><Plus size={15} aria-hidden="true" /> New quotation</Button></Link>}
      />
      <Card padded={false}>
        <TableToolbar>
          <SearchBox value={list.params.search} onChange={(v) => list.setParam("search", v)} placeholder="Search number or customer" />
          <FilterSelect label="Status" value={list.params.status} onChange={(v) => list.setParam("status", v)} options={STATUSES} />
          <FilterSelect label="Plan" value={list.params.plan} onChange={(v) => list.setParam("plan", v)} options={plans.map((p) => [p.id, p.name])} />
          {list.params.expires_by && <Button variant="ghost" onClick={() => list.setParam("expires_by", "")}>Clear expiry filter</Button>}
        </TableToolbar>
        <DataTable
          columns={columns}
          {...listProps(list)}
          empty={<EmptyState title="No subscriptions match" action={<Link to="/subscriptions/new"><Button variant="secondary">New quotation</Button></Link>}>Try clearing the filters, or start a new quotation.</EmptyState>}
        />
      </Card>
    </>
  );
}

/** Searches the server, because there can be thousands of customers. */
export function CustomerPicker({ value, onChange, error }) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const search = useDebounced(text);
  const options = useOptions("/customers", { search, is_active: true, page_size: 8 });
  return (
    <div className="relative">
      <Field
        label="Customer"
        required
        autoComplete="off"
        placeholder="Search by name, company or email"
        value={value ? value.label : text}
        error={error}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onChange={(event) => {
          onChange(null);
          setText(event.target.value);
          setOpen(true);
        }}
      />
      {open && !value && options.length > 0 && (
        <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-line bg-surface shadow-sm">
          {options.map((customer) => {
            const label = customer.company || customer.name;
            return (
              <li key={customer.id}>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left hover:bg-canvas"
                  onClick={() => onChange({ id: customer.id, label })}
                >
                  <span className="font-medium">{label}</span>
                  <span className="block text-[13px] text-ink-muted">{customer.email}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function LinesEditor({ lines, onChange, products, error }) {
  const update = (index, patch) => onChange(lines.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  return (
    <fieldset>
      <legend className="mb-1.5 font-medium">Product lines</legend>
      <div className="space-y-2">
        {lines.map((line, index) => {
          const product = products.find((p) => String(p.id) === String(line.product));
          return (
            <div key={index} className="flex flex-wrap items-end gap-2 rounded-md border border-line p-2.5">
              <SelectField
                label="Product" className="min-w-40 flex-1" value={line.product} required
                onChange={(e) => update(index, { product: e.target.value, variant: "" })}
              >
                <option value="">Choose</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({money(p.sales_price)})</option>)}
              </SelectField>
              {product?.variants.length > 0 && (
                <SelectField label="Variant" className="min-w-32" value={line.variant} onChange={(e) => update(index, { variant: e.target.value })}>
                  <option value="">None</option>
                  {product.variants.map((v) => <option key={v.id} value={v.id}>{v.value} (+{money(v.extra_price)})</option>)}
                </SelectField>
              )}
              <Field label="Qty" type="number" min="1" className="w-20" value={line.quantity} required onChange={(e) => update(index, { quantity: e.target.value })} />
              <Button variant="ghost" aria-label={`Remove line ${index + 1}`} onClick={() => onChange(lines.filter((_, i) => i !== index))}>
                <Trash2 size={15} aria-hidden="true" />
              </Button>
            </div>
          );
        })}
      </div>
      {error && <p className="mt-1.5 text-[13px] text-danger">{error}</p>}
      <Button variant="secondary" className="mt-2" onClick={() => onChange([...lines, { product: "", variant: "", quantity: 1 }])}>
        <Plus size={15} aria-hidden="true" /> Add line
      </Button>
    </fieldset>
  );
}

const specsFrom = (lines) => lines.filter((l) => l.product).map((l) => ({
  product: Number(l.product), variant: l.variant ? Number(l.variant) : null, quantity: Number(l.quantity),
}));

export function NewSubscriptionPage() {
  const navigate = useNavigate();
  const templates = useOptions("/quotation-templates");
  const plans = useOptions("/plans", { is_active: true });
  const products = useOptions("/products", { is_active: true });
  const [customer, setCustomer] = useState(null);
  const [lines, setLines] = useState([]);
  const form = useForm({ template: "", plan: "", start_date: today(), payment_terms_days: 30 }, async (values) => {
    const base = { customer: customer?.id ?? null, start_date: values.start_date };
    const created = values.template
      ? await api("/subscriptions/from-template", { method: "POST", body: { ...base, template: Number(values.template) } })
      : await api("/subscriptions", {
          method: "POST",
          body: { ...base, plan: values.plan || null, payment_terms_days: Number(values.payment_terms_days), lines: specsFrom(lines) },
        });
    navigate(`/subscriptions/${created.id}`);
  });
  const usingTemplate = Boolean(form.values.template);

  return (
    <>
      <PageHeader title="New quotation" eyebrow={<Link to="/subscriptions" className={LINK}>Subscriptions</Link>} subtitle="Start from a template, or build it line by line. Totals are calculated on the next screen." />
      <Card className="max-w-2xl">
        <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
          {form.formError && <Notice>{form.formError}</Notice>}
          <CustomerPicker value={customer} onChange={setCustomer} error={form.fieldErrors.customer} />
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField label="Quotation template" {...form.field("template")}>
              <option value="">None: build it myself</option>
              {templates.map((t) => <option key={t.id} value={t.id}>{t.name} (valid {t.validity_days} days)</option>)}
            </SelectField>
            <Field label="Start date" type="date" required {...form.field("start_date")} />
          </div>
          {usingTemplate ? (
            <p className="rounded-md bg-canvas px-3 py-2 text-ink-muted">
              {templates.find((t) => String(t.id) === form.values.template)?.lines.map((l) => `${l.quantity} x ${l.product_name}`).join(", ")}
            </p>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <SelectField label="Plan" required {...form.field("plan")}>
                  <option value="">Choose a plan</option>
                  {plans.map((p) => <option key={p.id} value={p.id}>{p.name} ({money(p.price)} / {INTERVALS[p.interval]})</option>)}
                </SelectField>
                <Field label="Payment terms (days)" type="number" min="0" max="365" {...form.field("payment_terms_days")} />
              </div>
              <LinesEditor lines={lines} onChange={setLines} products={products} error={form.fieldErrors.lines} />
            </>
          )}
          <Button type="submit" loading={form.submitting}>Create draft</Button>
        </form>
      </Card>
    </>
  );
}

const ACTION_LABELS = {
  send: "Send quotation", confirm: "Confirm", revise: "Back to draft", activate: "Activate",
  pause: "Pause", resume: "Resume", renew: "Renew", close: "Close",
};
const CONFIRM_FIRST = {
  close: "No more invoices will be created. Existing invoices stay as they are, and this can't be undone.",
  activate: "This starts billing and creates the first invoice if the start date has arrived.",
};
const PRIMARY = new Set(["send", "confirm", "activate", "resume"]);

export function SubscriptionActions({ subscription, labels = {} }) {
  const [pending, setPending] = useState(null);
  const run = useAction((name) => api(`/subscriptions/${subscription.id}/${name}`, { method: "POST" }), {
    onSuccess: () => setPending(null),
  });
  const trigger = (name) => (CONFIRM_FIRST[name] ? setPending(name) : run.mutate(name));
  const label = (name) => labels[name] ?? ACTION_LABELS[name];

  return (
    <>
      {subscription.actions.map((name) => (
        <Button key={name} variant={PRIMARY.has(name) ? "primary" : "secondary"} loading={run.isPending && run.variables === name} onClick={() => trigger(name)}>
          {label(name)}
        </Button>
      ))}
      {run.error && !pending && <div className="w-full"><Notice>{run.error.message}</Notice></div>}
      {pending && (
        <Dialog title={`${label(pending)} ${subscription.number}?`} onClose={() => { setPending(null); run.reset(); }}>
          <p className="text-ink-muted">{CONFIRM_FIRST[pending]}</p>
          {run.error && <div className="mt-3"><Notice>{run.error.message}</Notice></div>}
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => { setPending(null); run.reset(); }}>Keep as it is</Button>
            <Button loading={run.isPending} onClick={() => run.mutate(pending)}>{label(pending)}</Button>
          </div>
        </Dialog>
      )}
    </>
  );
}

/** What the next invoice would be. The server calculates it, with the same code as real invoices. */
export function InvoicePreview({ subscriptionId }) {
  const preview = useRecord(`/subscriptions/${subscriptionId}/preview`);
  if (preview.isLoading) return <p className="text-ink-muted">Calculating…</p>;
  if (preview.error) return <ErrorState error={preview.error} retry={preview.refetch} />;
  const { subtotal, discount_total: discount, tax_total: tax, total } = preview.data;
  return (
    <dl className="tabular space-y-2">
      <Row label="Subtotal" value={money(subtotal)} />
      {Number(discount) > 0 && <Row label="Discount" value={`-${money(discount)}`} />}
      <Row label="Tax" value={money(tax)} />
      <div className="flex justify-between border-t border-line pt-2 font-semibold"><dt>Total per period</dt><dd>{money(total)}</dd></div>
    </dl>
  );
}

function Row({ label, value }) {
  return <div className="flex justify-between"><dt className="text-ink-muted">{label}</dt><dd>{value}</dd></div>;
}

export function LinesTable({ lines }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[420px] text-left">
        <thead>
          <tr className="border-b border-line text-[13px] text-ink-muted">
            <th scope="col" className="px-4 py-2.5 font-medium">Item</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Qty</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Unit price</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Amount</th>
          </tr>
        </thead>
        <tbody className="tabular">
          {lines.map((line) => (
            <tr key={line.id} className="border-b border-line last:border-0">
              <td className="px-4 py-3">{line.description}</td>
              <td className="px-4 py-3 text-right">{line.quantity}</td>
              <td className="px-4 py-3 text-right">{money(line.unit_price)}</td>
              <td className="px-4 py-3 text-right">{money(line.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Timeline({ events }) {
  return (
    <ol className="space-y-3">
      {[...events].reverse().map((event) => (
        <li key={event.id} className="flex gap-3">
          <span aria-hidden="true" className="mt-1.5 size-2 shrink-0 rounded-full bg-line-strong" />
          <div className="min-w-0">
            <p className="font-medium first-letter:uppercase">{event.from_status && event.from_status !== event.to_status ? `${event.from_status} to ${event.to_status}` : event.note || event.to_status}</p>
            <p className="text-[13px] text-ink-muted">
              {dateTime(event.created_at)} by {event.actor_name}
              {event.note && event.from_status && event.from_status !== event.to_status ? `. ${event.note}` : ""}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function DiscountDialog({ subscription, onClose }) {
  const rules = useOptions("/discount-rules", { is_active: true });
  const form = useForm({ discount: subscription.discount ?? "" }, async (values) => {
    await save.mutateAsync(values.discount ? Number(values.discount) : null);
  });
  const save = useAction((discount) => api(`/subscriptions/${subscription.id}/discount`, { method: "POST", body: { discount } }), { onSuccess: onClose });
  return (
    <Dialog title="Discount" onClose={onClose}>
      <form onSubmit={form.handleSubmit} className="space-y-4">
        {form.formError && <Notice>{form.formError}</Notice>}
        <SelectField label="Discount rule" hint="Applies to the next invoice by itself, and stops when it expires or runs out." {...form.field("discount")}>
          <option value="">No discount</option>
          {rules.map((rule) => <option key={rule.id} value={rule.id}>{rule.name}</option>)}
        </SelectField>
        <Button type="submit" loading={form.submitting}>Save</Button>
      </form>
    </Dialog>
  );
}

function EditDraftDialog({ subscription, onClose }) {
  const products = useOptions("/products", { is_active: true });
  const plans = useOptions("/plans", { is_active: true });
  const [lines, setLines] = useState(() =>
    subscription.lines.filter((l) => l.product).map((l) => ({ product: l.product, variant: l.variant ?? "", quantity: l.quantity })),
  );
  const form = useForm(
    {
      plan: subscription.plan,
      start_date: subscription.start_date,
      expiry_date: subscription.expiry_date,
      payment_terms_days: subscription.payment_terms_days,
      quote_valid_until: subscription.quote_valid_until ?? "",
    },
    async (values) => {
      await api(`/subscriptions/${subscription.id}`, {
        method: "PATCH",
        body: {
          ...values,
          plan: Number(values.plan),
          payment_terms_days: Number(values.payment_terms_days),
          quote_valid_until: values.quote_valid_until || null,
          lines: specsFrom(lines),
        },
      });
      await refresh.mutateAsync();
      onClose();
    },
  );
  const refresh = useAction(async () => null);
  return (
    <Dialog title={`Edit ${subscription.number}`} onClose={onClose} wide>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField label="Plan" required {...form.field("plan")}>
            {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </SelectField>
          <Field label="Payment terms (days)" type="number" min="0" {...form.field("payment_terms_days")} />
          <Field label="Start date" type="date" required {...form.field("start_date")} />
          <Field label="Expiry date" type="date" required {...form.field("expiry_date")} />
          <Field label="Quotation valid until" type="date" {...form.field("quote_valid_until")} />
        </div>
        <LinesEditor lines={lines} onChange={setLines} products={products} error={form.fieldErrors.lines} />
        <Button type="submit" loading={form.submitting}>Save changes</Button>
      </form>
    </Dialog>
  );
}

export function SubscriptionDetailPage() {
  const { id } = useParams();
  const subscription = useRecord(`/subscriptions/${id}`);
  const invoices = useLocalList("/invoices", { subscription: id });
  const [dialog, setDialog] = useState(null);

  if (subscription.isLoading) return <PageLoading />;
  if (subscription.error) return <ErrorState error={subscription.error} retry={subscription.refetch} />;
  const s = subscription.data;
  const closed = s.status === "closed";
  const expiringSoon = s.status === "active" && s.expiry_date <= addDays(today(), 30);

  return (
    <>
      <PageHeader
        eyebrow={<Link to="/subscriptions" className={LINK}>Subscriptions</Link>}
        title={s.number}
        subtitle={<Link to={`/customers/${s.customer}`} className={LINK}>{s.customer_name}</Link>}
        actions={
          <>
            {s.status === "draft" && <Button variant="secondary" onClick={() => setDialog("edit")}>Edit</Button>}
            {!closed && <Button variant="secondary" onClick={() => setDialog("discount")}>Discount</Button>}
            <SubscriptionActions subscription={s} />
          </>
        }
      />
      <div className="space-y-4">
        <Card>
          <Stepper
            steps={SUBSCRIPTION_STEPS}
            current={s.status === "paused" ? "active" : s.status}
            note={s.status === "paused" ? "Paused: not billing" : expiringSoon ? "Renewal due soon" : null}
          />
        </Card>
        <Card>
          <Facts items={[
            ["Plan", `${s.plan_name} (billed every ${INTERVALS[s.interval]})`],
            ["Start", date(s.start_date)],
            ["Expires", date(s.expiry_date)],
            ["Next billing", date(s.next_billing_date)],
            ["Payment terms", `${s.payment_terms_days} days`],
            ["Discount", s.discount_name ?? "None"],
            ...(s.quote_valid_until ? [["Quotation valid until", date(s.quote_valid_until)]] : []),
            ...(s.closed_at ? [["Closed", dateTime(s.closed_at)]] : []),
          ]} />
        </Card>
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-3">
          <Card title="Lines" padded={false} className="lg:col-span-2">
            {s.lines.length ? <LinesTable lines={s.lines} /> : <EmptyState title="No lines yet" action={<Button variant="secondary" onClick={() => setDialog("edit")}>Add lines</Button>}>Add a product before sending this quotation.</EmptyState>}
          </Card>
          {!closed && <Card title="Next invoice"><InvoicePreview subscriptionId={s.id} /></Card>}
        </div>
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-3">
          <Card title="Invoices" padded={false} className="lg:col-span-2">
            <DataTable
              query={invoices}
              onPage={invoices.setPage}
              empty={<EmptyState title="No invoices yet">The first invoice is created when this subscription becomes active.</EmptyState>}
              columns={[
                { header: "Number", render: (row) => <Link to={`/invoices/${row.id}`} className={LINK}>{row.number}</Link> },
                { header: "Period", render: (row) => `${date(row.period_start)} to ${date(row.period_end)}` },
                { header: "Status", render: (row) => <InvoiceStatus invoice={row} /> },
                { header: "Total", right: true, render: (row) => money(row.total) },
              ]}
            />
          </Card>
          <Card title="History"><Timeline events={s.events} /></Card>
        </div>
      </div>
      {dialog === "edit" && <EditDraftDialog subscription={s} onClose={() => setDialog(null)} />}
      {dialog === "discount" && <DiscountDialog subscription={s} onClose={() => setDialog(null)} />}
    </>
  );
}
