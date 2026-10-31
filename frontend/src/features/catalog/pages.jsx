import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/auth";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Dialog } from "../../components/Dialog";
import { CheckField, Field, SelectField, TextArea } from "../../components/Field";
import { Card, EmptyState, PageHeader } from "../../components/Layout";
import { Notice } from "../../components/Notice";
import { api } from "../../lib/api";
import { date, INTERVALS, money, titleCase } from "../../lib/format";
import { useAction, useLocalList, useOptions } from "../../lib/hooks";
import { useForm } from "../../lib/useForm";

const nullIfEmpty = (value) => (value === "" ? null : value);

/** Saves a record, and lets the admin delete it unless other records use it. */
function useSave(path, record, onClose) {
  const save = useAction(
    (body) => api(record?.id ? `${path}/${record.id}` : path, { method: record?.id ? "PATCH" : "POST", body }),
    { onSuccess: onClose },
  );
  const remove = useAction(() => api(`${path}/${record.id}`, { method: "DELETE" }), { onSuccess: onClose });
  return { save, remove };
}

function FormFooter({ form, record, remove }) {
  return (
    <>
      {remove.error && <Notice>{remove.error.message}</Notice>}
      <div className="flex items-center justify-between gap-2">
        <Button type="submit" loading={form.submitting}>{record?.id ? "Save changes" : "Create"}</Button>
        {record?.id && <Button variant="ghost" loading={remove.isPending} onClick={() => remove.mutate()}>Delete</Button>}
      </div>
    </>
  );
}

function RowEditor({ legend, rows, onChange, blank, addLabel, error, children }) {
  const update = (index, patch) => onChange(rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  return (
    <fieldset>
      <legend className="mb-1.5 font-medium">{legend}</legend>
      <div className="space-y-2">
        {rows.map((row, index) => (
          <div key={index} className="flex flex-wrap items-end gap-2 rounded-md border border-line p-2.5">
            {children(row, (patch) => update(index, patch))}
            <Button variant="ghost" aria-label={`Remove row ${index + 1}`} onClick={() => onChange(rows.filter((_, i) => i !== index))}>
              <Trash2 size={15} aria-hidden="true" />
            </Button>
          </div>
        ))}
      </div>
      {error && <p className="mt-1.5 text-[13px] text-danger">{typeof error === "string" ? error : "Please check these rows."}</p>}
      <Button variant="secondary" className="mt-2" onClick={() => onChange([...rows, { ...blank }])}>
        <Plus size={15} aria-hidden="true" /> {addLabel}
      </Button>
    </fieldset>
  );
}

function ProductDialog({ record, onClose }) {
  const taxes = useOptions("/tax-rules");
  const { save, remove } = useSave("/products", record, onClose);
  const [variants, setVariants] = useState(record?.variants ?? []);
  const form = useForm(
    record ?? { name: "", type: "software", sales_price: "", cost_price: "0.00", notes: "", tax_rule: "", is_active: true },
    (values) => save.mutateAsync({
      name: values.name, type: values.type, sales_price: values.sales_price, cost_price: values.cost_price,
      notes: values.notes, tax_rule: nullIfEmpty(values.tax_rule ?? ""), is_active: values.is_active,
      variants: variants.map(({ attribute, value, extra_price }) => ({ attribute, value, extra_price })),
    }),
  );
  return (
    <Dialog title={record ? `Edit ${record.name}` : "New product"} onClose={onClose} wide>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" required {...form.field("name")} />
          <SelectField label="Type" required {...form.field("type")}>
            <option value="software">Software</option>
            <option value="addon">Add-on</option>
            <option value="service">Service</option>
          </SelectField>
          <Field label="Sales price" type="number" min="0" step="0.01" required {...form.field("sales_price")} />
          <Field label="Cost price" type="number" min="0" step="0.01" {...form.field("cost_price")} />
          <SelectField label="Tax rule" hint="Applied automatically on invoices." {...form.field("tax_rule")}>
            <option value="">No tax</option>
            {taxes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </SelectField>
        </div>
        <TextArea label="Notes" {...form.field("notes")} />
        <RowEditor legend="Variants" rows={variants} onChange={setVariants} blank={{ attribute: "Brand", value: "", extra_price: "0.00" }} addLabel="Add variant" error={form.fieldErrors.variants}>
          {(row, update) => (
            <>
              <Field label="Attribute" className="min-w-28 flex-1" value={row.attribute} onChange={(e) => update({ attribute: e.target.value })} />
              <Field label="Value" className="min-w-28 flex-1" value={row.value} onChange={(e) => update({ value: e.target.value })} />
              <Field label="Adds to price" type="number" min="0" step="0.01" className="w-32" value={row.extra_price} onChange={(e) => update({ extra_price: e.target.value })} />
            </>
          )}
        </RowEditor>
        <CheckField label="Active" hint="Inactive products can't be added to new quotations." {...form.check("is_active")} />
        <FormFooter {...{ form, record, remove }} />
      </form>
    </Dialog>
  );
}

function PlanDialog({ record, onClose }) {
  const taxes = useOptions("/tax-rules");
  const { save, remove } = useSave("/plans", record, onClose);
  const form = useForm(
    record ?? {
      name: "", price: "0.00", interval: "monthly", min_quantity: 1, term_periods: 12, available_from: "", available_to: "",
      tax_rule: "", auto_close: false, closable: true, pausable: true, renewable: true, is_active: true,
    },
    ({ id, ...values }) => save.mutateAsync({
      ...values,
      available_from: nullIfEmpty(values.available_from ?? ""),
      available_to: nullIfEmpty(values.available_to ?? ""),
      tax_rule: nullIfEmpty(values.tax_rule ?? ""),
    }),
  );
  return (
    <Dialog title={record ? `Edit ${record.name}` : "New plan"} onClose={onClose} wide>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" required {...form.field("name")} />
          <SelectField label="Bills" required {...form.field("interval")}>
            {Object.keys(INTERVALS).map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}
          </SelectField>
          <Field label="Plan price" type="number" min="0" step="0.01" hint="Billed each period, on top of product lines. Can be 0." {...form.field("price")} />
          <SelectField label="Tax on plan price" {...form.field("tax_rule")}>
            <option value="">No tax</option>
            {taxes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </SelectField>
          <Field label="Minimum quantity" type="number" min="1" {...form.field("min_quantity")} />
          <Field label="Term length (billing periods)" type="number" min="1" hint="Sets the default expiry, and how far a renewal extends it." {...form.field("term_periods")} />
          <Field label="Available from" type="date" {...form.field("available_from")} />
          <Field label="Available until" type="date" {...form.field("available_to")} />
        </div>
        <fieldset className="grid gap-3 sm:grid-cols-2">
          <legend className="mb-2 font-medium">What this plan allows</legend>
          <CheckField label="Closes on its own at expiry" {...form.check("auto_close")} />
          <CheckField label="Can be closed early" {...form.check("closable")} />
          <CheckField label="Can be paused" {...form.check("pausable")} />
          <CheckField label="Can be renewed" {...form.check("renewable")} />
          <CheckField label="Active" hint="Offered on new quotations." {...form.check("is_active")} />
        </fieldset>
        <FormFooter {...{ form, record, remove }} />
      </form>
    </Dialog>
  );
}

function TaxDialog({ record, onClose }) {
  const { save, remove } = useSave("/tax-rules", record, onClose);
  const form = useForm(record ?? { name: "", rate_percent: "", is_active: true }, ({ id, ...body }) => save.mutateAsync(body));
  return (
    <Dialog title={record ? `Edit ${record.name}` : "New tax rule"} onClose={onClose}>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <Field label="Name" required {...form.field("name")} />
        <Field label="Rate (%)" type="number" min="0" max="100" step="0.01" required {...form.field("rate_percent")} />
        <CheckField label="Active" hint="Inactive rules aren't applied to new invoices." {...form.check("is_active")} />
        <FormFooter {...{ form, record, remove }} />
      </form>
    </Dialog>
  );
}

function DiscountDialog({ record, onClose }) {
  const products = useOptions("/products");
  const { save, remove } = useSave("/discount-rules", record, onClose);
  const [chosen, setChosen] = useState(record?.products ?? []);
  const form = useForm(
    record ?? {
      name: "", kind: "percent", value: "", min_amount: "0.00", min_quantity: 0, starts_on: "", ends_on: "",
      usage_limit: "", scope: "subscription", is_active: true,
    },
    ({ id, times_used, products: _, ...values }) => save.mutateAsync({
      ...values,
      ends_on: nullIfEmpty(values.ends_on ?? ""),
      usage_limit: nullIfEmpty(values.usage_limit ?? ""),
      products: values.scope === "products" ? chosen : [],
    }),
  );
  const toggle = (productId) => setChosen((current) => current.includes(productId) ? current.filter((v) => v !== productId) : [...current, productId]);
  return (
    <Dialog title={record ? `Edit ${record.name}` : "New discount rule"} onClose={onClose} wide>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" required {...form.field("name")} />
          <SelectField label="Type" required {...form.field("kind")}>
            <option value="percent">Percentage</option>
            <option value="fixed">Fixed amount</option>
          </SelectField>
          <Field label={form.values.kind === "percent" ? "Percent off" : "Amount off"} type="number" min="0.01" step="0.01" required {...form.field("value")} />
          <Field label="Usage limit" type="number" min="1" hint={record ? `Used ${record.times_used} times so far. Empty means no limit.` : "Empty means no limit."} {...form.field("usage_limit")} />
          <Field label="Minimum purchase" type="number" min="0" step="0.01" {...form.field("min_amount")} />
          <Field label="Minimum quantity" type="number" min="0" {...form.field("min_quantity")} />
          <Field label="Starts" type="date" required {...form.field("starts_on")} />
          <Field label="Ends" type="date" hint="Empty means it doesn't expire." {...form.field("ends_on")} />
          <SelectField label="Applies to" {...form.field("scope")}>
            <option value="subscription">Whole subscription</option>
            <option value="products">Specific products</option>
          </SelectField>
        </div>
        {form.values.scope === "products" && (
          <fieldset>
            <legend className="mb-1.5 font-medium">Products</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {products.map((p) => <CheckField key={p.id} label={p.name} checked={chosen.includes(p.id)} onChange={() => toggle(p.id)} />)}
            </div>
            {form.fieldErrors.products && <p className="mt-1.5 text-[13px] text-danger">{form.fieldErrors.products}</p>}
          </fieldset>
        )}
        <CheckField label="Active" {...form.check("is_active")} />
        <FormFooter {...{ form, record, remove }} />
      </form>
    </Dialog>
  );
}

function TemplateDialog({ record, onClose }) {
  const plans = useOptions("/plans");
  const products = useOptions("/products", { is_active: true });
  const { save, remove } = useSave("/quotation-templates", record, onClose);
  const [lines, setLines] = useState(record?.lines ?? []);
  const form = useForm(record ?? { name: "", plan: "", validity_days: 30, notes: "" }, (values) => save.mutateAsync({
    name: values.name, plan: nullIfEmpty(values.plan), validity_days: values.validity_days, notes: values.notes,
    lines: lines.filter((l) => l.product).map((l) => ({ product: Number(l.product), variant: l.variant ? Number(l.variant) : null, quantity: Number(l.quantity) })),
  }));
  return (
    <Dialog title={record ? `Edit ${record.name}` : "New quotation template"} onClose={onClose} wide>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" required {...form.field("name")} />
          <SelectField label="Plan" required {...form.field("plan")}>
            <option value="">Choose a plan</option>
            {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </SelectField>
          <Field label="Valid for (days)" type="number" min="1" {...form.field("validity_days")} />
        </div>
        <TextArea label="Notes" {...form.field("notes")} />
        <RowEditor legend="Product lines" rows={lines} onChange={setLines} blank={{ product: "", variant: "", quantity: 1 }} addLabel="Add line" error={form.fieldErrors.lines}>
          {(row, update) => {
            const product = products.find((p) => String(p.id) === String(row.product));
            return (
              <>
                <SelectField label="Product" className="min-w-40 flex-1" value={row.product} onChange={(e) => update({ product: e.target.value, variant: "" })}>
                  <option value="">Choose</option>
                  {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </SelectField>
                {product?.variants.length > 0 && (
                  <SelectField label="Variant" className="min-w-32" value={row.variant ?? ""} onChange={(e) => update({ variant: e.target.value })}>
                    <option value="">None</option>
                    {product.variants.map((v) => <option key={v.id} value={v.id}>{v.value}</option>)}
                  </SelectField>
                )}
                <Field label="Qty" type="number" min="1" className="w-20" value={row.quantity} onChange={(e) => update({ quantity: e.target.value })} />
              </>
            );
          }}
        </RowEditor>
        <FormFooter {...{ form, record, remove }} />
      </form>
    </Dialog>
  );
}

const yesNo = (value) => (value ? "Yes" : "No");

const TABS = {
  products: {
    label: "Products", path: "/products", dialog: ProductDialog, noun: "product", hint: "What Brightloop sells, with prices, variants and tax.",
    columns: [
      { header: "Type", render: (r) => titleCase(r.type) },
      { header: "Variants", render: (r) => r.variants.map((v) => v.value).join(", ") || "–" },
      { header: "Tax", render: (r) => r.tax_rule_name ?? "–" },
      { header: "Sales price", right: true, render: (r) => money(r.sales_price) },
      { header: "Cost price", right: true, render: (r) => money(r.cost_price) },
    ],
  },
  plans: {
    label: "Plans", path: "/plans", dialog: PlanDialog, noun: "plan", hint: "What a subscription costs, how often it bills, and what it allows.",
    columns: [
      { header: "Bills", render: (r) => titleCase(r.interval) },
      { header: "Min. qty", right: true, render: (r) => r.min_quantity },
      { header: "Auto-close", render: (r) => yesNo(r.auto_close) },
      { header: "Close early", render: (r) => yesNo(r.closable) },
      { header: "Pause", render: (r) => yesNo(r.pausable) },
      { header: "Renew", render: (r) => yesNo(r.renewable) },
      { header: "Price", right: true, render: (r) => money(r.price) },
    ],
  },
  taxes: {
    label: "Taxes", path: "/tax-rules", dialog: TaxDialog, noun: "tax rule", hint: "Applied automatically when invoices are created.",
    columns: [
      { header: "Active", render: (r) => yesNo(r.is_active) },
      { header: "Rate", right: true, render: (r) => `${r.rate_percent}%` },
    ],
  },
  discounts: {
    label: "Discounts", path: "/discount-rules", dialog: DiscountDialog, noun: "discount rule", hint: "Only the admin can create these. They stop by themselves when they expire or run out.",
    columns: [
      { header: "Value", render: (r) => (r.kind === "percent" ? `${r.value}%` : money(r.value)) },
      { header: "Applies to", render: (r) => titleCase(r.scope) },
      { header: "Dates", render: (r) => `${date(r.starts_on)} to ${r.ends_on ? date(r.ends_on) : "no end"}` },
      { header: "Used", right: true, render: (r) => `${r.times_used}${r.usage_limit ? ` / ${r.usage_limit}` : ""}` },
    ],
  },
  templates: {
    label: "Templates", path: "/quotation-templates", dialog: TemplateDialog, noun: "template", hint: "Starting points for quotations, so sales reps don't build them from scratch.",
    columns: [
      { header: "Plan", render: (r) => r.plan_name },
      { header: "Lines", render: (r) => r.lines.map((l) => `${l.quantity} x ${l.product_name}`).join(", "), nowrap: false },
      { header: "Valid for", right: true, render: (r) => `${r.validity_days} days` },
    ],
  },
};

/** Keyed by tab in the parent, so one tab's rows are never drawn with another tab's columns. */
function CatalogTab({ tab, isAdmin }) {
  const list = useLocalList(tab.path);
  const [editing, setEditing] = useState(null);
  const TabDialog = tab.dialog;
  const add = isAdmin && <Button onClick={() => setEditing({})}><Plus size={15} aria-hidden="true" /> New {tab.noun}</Button>;
  const columns = [
    {
      header: "Name",
      render: (row) => isAdmin
        ? <button type="button" className="font-medium text-accent hover:underline" onClick={() => setEditing(row)}>{row.name}</button>
        : <span className="font-medium">{row.name}</span>,
    },
    ...tab.columns,
  ];
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-ink-muted">{tab.hint}</p>
        {add}
      </div>
      <Card padded={false}>
        <DataTable query={list} onPage={list.setPage} columns={columns} empty={<EmptyState title={`No ${tab.noun}s yet`} action={add} />} />
      </Card>
      {editing && <TabDialog key={editing.id ?? "new"} record={editing.id ? editing : null} onClose={() => setEditing(null)} />}
    </>
  );
}

export function CatalogPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabKey = TABS[searchParams.get("tab")] ? searchParams.get("tab") : "products";
  const isAdmin = user.role === "admin";

  return (
    <>
      <PageHeader title="Catalog" subtitle={isAdmin ? "Everything that defines what's for sale." : "Read-only. Only the admin can change the catalog."} />
      <div role="tablist" aria-label="Catalog sections" className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
        {Object.entries(TABS).map(([key, value]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={key === tabKey}
            onClick={() => setSearchParams({ tab: key })}
            className={`-mb-px border-b-2 px-3 py-2 whitespace-nowrap transition-colors duration-150 ${key === tabKey ? "border-accent font-medium text-accent" : "border-transparent text-ink-muted hover:text-ink"}`}
          >
            {value.label}
          </button>
        ))}
      </div>
      <CatalogTab key={tabKey} tab={TABS[tabKey]} isAdmin={isAdmin} />
    </>
  );
}
