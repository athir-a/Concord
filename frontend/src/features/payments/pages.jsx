import { Link } from "react-router-dom";
import { DataTable, FilterSelect, SearchBox, TableToolbar, listProps } from "../../components/DataTable";
import { Card, EmptyState, PageHeader } from "../../components/Layout";
import { date, money, PAYMENT_METHODS, titleCase } from "../../lib/format";
import { useListPage } from "../../lib/hooks";

const LINK = "font-medium text-accent hover:underline";

export function PaymentsPage() {
  const list = useListPage("/payments");
  const columns = [
    { header: "Date", sort: "paid_on", render: (row) => date(row.paid_on) },
    { header: "Invoice", render: (row) => <Link to={`/invoices/${row.invoice}`} className={LINK}>{row.invoice_number}</Link> },
    { header: "Customer", render: (row) => row.customer_name },
    { header: "Method", render: (row) => titleCase(row.method) },
    { header: "Note", nowrap: false, render: (row) => row.note || "–" },
    { header: "Amount", right: true, sort: "amount", render: (row) => money(row.amount) },
  ];
  return (
    <>
      <PageHeader title="Payments" subtitle="Money received, recorded against invoices. To record one, open its invoice." />
      <Card padded={false}>
        <TableToolbar>
          <SearchBox value={list.params.search} onChange={(v) => list.setParam("search", v)} placeholder="Search invoice, customer or note" />
          <FilterSelect label="Method" value={list.params.method} onChange={(v) => list.setParam("method", v)} options={PAYMENT_METHODS} />
        </TableToolbar>
        <DataTable columns={columns} {...listProps(list)} empty={<EmptyState title="No payments match" />} />
      </Card>
    </>
  );
}
