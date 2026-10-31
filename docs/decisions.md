# Decisions and what we learned

## Decisions we'd defend

| Decision | Why | What we gave up |
|---|---|---|
| A quotation is a stage of a subscription, not its own table | The statement describes one record moving through Draft, Quotation, Confirmed, Active and Closed | Quotation-only fields live on the subscription |
| Modular monolith | Invoices and payments must change together in one transaction | Can't scale parts separately, which we don't need |
| No Celery or Redis | Duplicate protection lives in the database, so a plain command is safe to run from cron | Billing runs while the admin waits |
| Sessions, not JWT | The browser sees one origin, and JavaScript can't read an HttpOnly cookie, so XSS can't steal it | Not suited to third-party API clients yet |
| Record payments, no gateway | It's what the statement asks for | No online payment |
| Database constraints as well as code checks | A bug in our code still can't double-bill | Slightly more schema work |
| Stored `amount_paid` and `recurring_subtotal` | Lists stay fast with thousands of rows | Must only change inside locked service functions |
| Print through the browser, no PDF library | The statement says "print", and this is simpler | No PDF file to attach |
| Someone else's record returns 404, not 403 | A 403 would confirm the record exists | Slightly less specific errors |
| JavaScript, not TypeScript | Faster for this team in a one-day build | Fewer compile-time checks |

## Assumptions where the statement is silent

- A product's sales price and a plan's price both apply: the plan price is its own fee line, and can be 0.
- Billing is in advance, and recurring invoices start as drafts for the team to confirm.
- A discount "use" is one invoice it changed. Cancelling that invoice gives the use back.
- A minimum purchase or quantity counts only the lines the discount covers.
- There's no separate finance role. Staff and admin both see reports.
- New signups never attach to an existing customer with the same email. Emails aren't verified, so that would let anyone claim someone else's invoices.

## Bugs that taught us something

**Every browser login would have failed while all the tests passed.** Vite's shorthand proxy setting changes the Host header, so Django saw a mismatch with the browser's Origin and rejected each form as a possible CSRF attack. The fix was to keep the original Host header, not to weaken the check. The test client doesn't use the proxy, so only testing the real route caught it.

**Our concurrency tests couldn't fail.** They passed with the locks removed, because each thread finished before the next one got going. We rewrote them so threads connect first, wait at a barrier, and hit a delay inside the critical section. With a lock removed, one invoice then received 4 payments and the test failed. With locks in place they pass reliably. The lesson is to check that a test *can* fail.

**The payments list took 15 seconds right after seeding.** Every other page was under 130 ms. After a huge bulk insert, Postgres didn't yet know how big the table was and chose a bad query plan. Its own records showed the background analyze ran moments later. `seed_demo` now refreshes statistics itself, and that page takes 14 ms. We only found this by measuring at scale.

**Switching catalog tabs could crash the page.** The table briefly kept the old tab's rows for a smooth transition but drew them with the new tab's columns. Each tab now has its own table state. A browser walk caught it, not the backend tests.

**Resuming a subscription could have charged twice.** Always restarting billing from today would bill the same days again if someone paused and resumed within a paid period. Resume now keeps the schedule if the billed period is still running.
