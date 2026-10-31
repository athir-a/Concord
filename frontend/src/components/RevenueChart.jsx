import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { compactMoney, money, month } from "../lib/format";

const INVOICED = "#3f3dbb";
const COLLECTED = "#d97706";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2 text-[13px] shadow-sm">
      <p className="mb-1 font-medium">{month(label)}</p>
      {payload.map((item) => (
        <p key={item.dataKey} className="tabular flex items-center justify-between gap-4 text-ink-muted">
          <span className="flex items-center gap-1.5">
            <span aria-hidden="true" className="size-2 rounded-sm" style={{ background: item.color }} />
            {item.name}
          </span>
          <span className="text-ink">{money(item.value)}</span>
        </p>
      ))}
    </div>
  );
}

/** Invoiced is what we asked for, collected is what arrived. One axis, because both are rupees. */
export function RevenueChart({ data, height = 260 }) {
  const rows = data.map((row) => ({ ...row, invoiced: Number(row.invoiced), collected: Number(row.collected) }));
  return (
    <figure>
      <figcaption className="mb-3 flex gap-4 text-[13px] text-ink-muted">
        <span className="flex items-center gap-1.5"><span aria-hidden="true" className="size-2.5 rounded-sm" style={{ background: INVOICED }} /> Invoiced</span>
        <span className="flex items-center gap-1.5"><span aria-hidden="true" className="size-2.5 rounded-sm" style={{ background: COLLECTED }} /> Collected</span>
      </figcaption>
      <div style={{ height }} role="img" aria-label="Bar chart of invoiced and collected revenue for each of the last 12 months. The same figures are in the monthly table.">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} barGap={2} barCategoryGap="28%" margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--color-line)" />
            <XAxis dataKey="month" tickFormatter={month} tickLine={false} axisLine={{ stroke: "var(--color-line-strong)" }} tick={{ fontSize: 12, fill: "var(--color-ink-muted)" }} minTickGap={12} />
            <YAxis tickFormatter={compactMoney} tickLine={false} axisLine={false} width={60} tick={{ fontSize: 12, fill: "var(--color-ink-muted)" }} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--color-canvas)" }} />
            <Bar dataKey="invoiced" name="Invoiced" fill={INVOICED} radius={[4, 4, 0, 0]} maxBarSize={18} isAnimationActive={false} />
            <Bar dataKey="collected" name="Collected" fill={COLLECTED} radius={[4, 4, 0, 0]} maxBarSize={18} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
