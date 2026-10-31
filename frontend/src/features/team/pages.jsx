import { Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Dialog } from "../../components/Dialog";
import { Field } from "../../components/Field";
import { Card, EmptyState, PageHeader } from "../../components/Layout";
import { Notice } from "../../components/Notice";
import { PasswordChecklist } from "../auth/pages";
import { api } from "../../lib/api";
import { date } from "../../lib/format";
import { useAction, useLocalList } from "../../lib/hooks";
import { useForm } from "../../lib/useForm";

function AddStaffDialog({ onClose }) {
  const save = useAction((body) => api("/users/staff", { method: "POST", body }), { onSuccess: onClose });
  const form = useForm({ name: "", email: "", password: "" }, (values) => save.mutateAsync(values));
  return (
    <Dialog title="Add a member of staff" onClose={onClose}>
      <form onSubmit={form.handleSubmit} className="space-y-4" noValidate>
        {form.formError && <Notice>{form.formError}</Notice>}
        <Field label="Name" required autoFocus {...form.field("name")} />
        <Field label="Email" type="email" required autoComplete="off" {...form.field("email")} />
        <div>
          <Field label="Temporary password" type="password" required autoComplete="new-password" {...form.field("password")} />
          <PasswordChecklist password={form.values.password} />
        </div>
        <Button type="submit" loading={form.submitting}>Add staff member</Button>
      </form>
    </Dialog>
  );
}

export function TeamPage() {
  const list = useLocalList("/users/staff");
  const [adding, setAdding] = useState(false);
  const add = <Button onClick={() => setAdding(true)}><Plus size={15} aria-hidden="true" /> Add staff</Button>;
  return (
    <>
      <PageHeader title="Team" subtitle="Staff handle customers, subscriptions, invoices and payments. Only you can add them." actions={add} />
      <Card padded={false}>
        <DataTable
          query={list}
          onPage={list.setPage}
          empty={<EmptyState title="No staff yet" action={add}>Add someone to help with the day-to-day work.</EmptyState>}
          columns={[
            { header: "Name", render: (row) => <span className="font-medium">{row.name || "–"}</span> },
            { header: "Email", render: (row) => row.email },
            { header: "Added", render: (row) => date(row.date_joined) },
            { header: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
          ]}
        />
      </Card>
      {adding && <AddStaffDialog onClose={() => setAdding(false)} />}
    </>
  );
}
