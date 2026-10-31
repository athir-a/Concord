import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button } from "../../components/Button";
import { DataTable, FilterSelect, SearchBox, TableToolbar, listProps } from "../../components/DataTable";
import { Dialog } from "../../components/Dialog";
import { CheckField, Field, TextArea } from "../../components/Field";
import { Card, EmptyState, ErrorState, Facts, PageHeader, PageLoading } from "../../components/Layout";
import { Notice } from "../../components/Notice";
import { InvoiceStatus, StatusPill } from "../../components/Status";
import { api } from "../../lib/api";
import { date, money } from "../../lib/format";
import { useAction, useListPage, useLocalList, useRecord } from "../../lib/hooks";
import { useForm } from "../../lib/useForm";

const LINK = "font-medium text-accent hover:underline";

function CustomerDialog({ customer, onClose, onSaved }) {
  const save = useAction(
    (body) => api(customer ? `/customers/${customer.id}` : "/customers", { method: customer ? "PATCH" : "POST", body }),
    { onSuccess: onSaved },
  );
  const form = useForm(
    customer ?? { name: "", company: "", email: "", phone: "", address: "", tax_id: "", is_active: true },
    ({ id, has_login, created_at, ...body }) => save.mutateAsync(body),
  );
  return (
    <Dialog title={customer ? `Edit ${customer.name}` : "New customer"} onClose={onClose} wide>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Contact name" required autoFocus {...form.field("name")} />
          <Field label="Company" {...form.field("company")} />
          <Field label="Email" type="email" required {...form.field("email")} />
          <Field label="Phone" type="tel" {...form.field("phone")} />
          <Field label="Tax ID" {...form.field("tax_id")} />
        </div>
        <TextArea label="Address" {...form.field("address")} />
        <CheckField label="Active" hint="Inactive customers can't start new subscriptions." {...form.check("is_active")} />
        <Button type="submit" loading={form.submitting}>{customer ? "Save changes" : "Add customer"}</Button>
      </form>
    </Dialog>
  );
}

export function CustomersPage() {
  const list = useListPage("/customers");
  const navigate = useNavigate();
  const [adding, setAdding] = useState(false);
  const add = <Button onClick={() => setAdding(true)}><Plus size={15} aria-hidden="true" /> New customer</Button>;
  const columns = [
    { header: "Name", sort: "name", render: (row) => <Link to={`/customers/${row.id}`} className={LINK}>{row.name}</Link> },
    { header: "Company", sort: "company", render: (row) => row.company || "–" },
    { header: "Email", render: (row) => row.email },
    { header: "Phone", render: (row) => row.phone || "–" },
    { header: "Portal login", render: (row) => (row.has_login ? "Yes" : "No") },
    { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
  ];
  return (
    <>
      <PageHeader title="Customers" subtitle="Everyone Brightloop bills, and their whole history." actions={add} />
      <Card padded={false}>
        <TableToolbar>
          <SearchBox value={list.params.search} onChange={(v) => list.setParam("search", v)} placeholder="Search name, company, email or phone" />
          <FilterSelect label="Status" value={list.params.is_active} onChange={(v) => list.setParam("is_active", v)} options={[["true", "Active"], ["false", "Inactive"]]} />
        </TableToolbar>
        <DataTable columns={columns} {...listProps(list)} empty={<EmptyState title="No customers match" action={add}>Try another search, or add a new customer.</EmptyState>} />
      </Card>
      {adding && <CustomerDialog onClose={() => setAdding(false)} onSaved={(created) => navigate(`/customers/${created.id}`)} />}
    </>
  );
}

export function CustomerDetailPage() {
  const { id } = useParams();
  const customer = useRecord(`/customers/${id}`);
  const summary = useRecord(`/customers/${id}/summary`);
  const subscriptions = useLocalList("/subscriptions", { customer: id });
  const invoices = useLocalList("/invoices", { customer: id });
  const [editing, setEditing] = useState(false);

  if (customer.isLoading) return <PageLoading />;
  if (customer.error) return <ErrorState error={customer.error} retry={customer.refetch} />;
  const c = customer.data;
  const s = summary.data;

  return (
    <>
      <PageHeader
        eyebrow={<Link to="/customers" className={LINK}>Customers</Link>}
        title={c.company || c.name}
        subtitle={c.company ? c.name : c.email}
        actions={
          <>
            <Button variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
            <Link to="/subscriptions/new"><Button><Plus size={15} aria-hidden="true" /> New quotation</Button></Link>
          </>
        }
      />
      <div className="space-y-4">
        <Card>
          <Facts items={[
            ["Email", c.email],
            ["Phone", c.phone || "–"],
            ["Tax ID", c.tax_id || "–"],
            ["Portal login", c.has_login ? "Yes" : "No"],
            ["Invoiced", s ? money(s.invoiced) : "…"],
            ["Collected", s ? money(s.collected) : "…"],
            ["Outstanding", s ? money(s.outstanding) : "…"],
            ["Overdue", s ? money(s.overdue) : "…"],
          ]} />
        </Card>
        <Card title="Subscriptions" padded={false}>
          <DataTable
            query={subscriptions}
            onPage={subscriptions.setPage}
            empty={<EmptyState title="No subscriptions yet" />}
            columns={[
              { header: "Number", render: (row) => <Link to={`/subscriptions/${row.id}`} className={LINK}>{row.number}</Link> },
              { header: "Plan", render: (row) => row.plan_name },
              { header: "Status", render: (row) => <StatusPill status={row.status} /> },
              { header: "Next billing", render: (row) => date(row.next_billing_date) },
              { header: "Expires", render: (row) => date(row.expiry_date) },
            ]}
          />
        </Card>
        <Card title="Invoices" padded={false}>
          <DataTable
            query={invoices}
            onPage={invoices.setPage}
            empty={<EmptyState title="No invoices yet" />}
            columns={[
              { header: "Number", render: (row) => <Link to={`/invoices/${row.id}`} className={LINK}>{row.number}</Link> },
              { header: "Status", render: (row) => <InvoiceStatus invoice={row} /> },
              { header: "Due", render: (row) => date(row.due_date) },
              { header: "Total", right: true, render: (row) => money(row.total) },
              { header: "Outstanding", right: true, render: (row) => (row.status === "confirmed" ? money(row.amount_due) : "–") },
            ]}
          />
        </Card>
      </div>
      {editing && <CustomerDialog customer={c} onClose={() => setEditing(false)} onSaved={() => setEditing(false)} />}
    </>
  );
}
