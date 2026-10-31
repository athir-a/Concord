# How Concord's numbers are calculated

Every number comes from the database at the moment you ask. None of them is profit.

| Metric | Definition |
|---|---|
| **Active subscriptions** | Status is Active. Paused ones are counted separately. |
| **MRR** (monthly recurring revenue) | The recurring subtotal of active subscriptions, converted to a month: yearly ÷ 12, weekly × 52 ÷ 12, daily × 365 ÷ 12. Excludes tax and is **before discounts**. |
| **ARR** (annual recurring revenue) | MRR × 12. |
| **Invoiced** | Total of Confirmed and Paid invoices, by issue date. Includes tax. |
| **Collected** | Total of payments, by payment date. Includes tax, because it's the cash that arrived. |
| **Outstanding** | Total minus amount paid, on Confirmed invoices. |
| **Overdue** | Outstanding on invoices whose due date has passed. Worked out each time, never stored, so it can't go stale. |

**How they relate:** invoiced is what we asked for, collected is what arrived, and outstanding is the gap. MRR is a run rate that looks forward, not money received.

**Filters:** the date range narrows invoiced and collected. The other numbers describe the position today, so a date range doesn't change them. Plan and customer filters apply to everything.

**Known limit:** MRR is before discounts, so it can be higher than what active subscriptions are actually billed.
