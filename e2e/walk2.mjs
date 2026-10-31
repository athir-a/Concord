// The statement's other scenes: discounts, editing, lifecycle actions, cancel and reissue, password reset.
import { readFileSync } from "node:fs";
import { chromium } from "playwright-core";

const BASE = "http://localhost:5173";
const SHOTS = process.argv[2];
const SERVER_LOG = process.argv[3];
const PW = "Concord!demo1";
const stamp = Date.now();
const problems = [];
let passed = 0;
const check = (name, ok, extra = "") => { if (ok) passed++; else problems.push(`${name} ${extra}`); console.log(`${ok ? "ok  " : "FAIL"} ${name} ${ok ? "" : extra}`); };

const browser = await chromium.launch({ channel: "msedge", headless: true });
async function session(label) {
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
  page.on("pageerror", (e) => problems.push(`[${label}] page error: ${e.message}`));
  page.on("response", (r) => { if (r.status() >= 500) problems.push(`[${label}] ${r.status()} ${r.url()}`); });
  return page;
}
const settled = async (page) => { await page.waitForTimeout(150); await page.waitForFunction(() => !document.querySelector(".animate-pulse"), null, { timeout: 15000 }); };
const shot = (page, name, fullPage = false) => page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage });
async function login(page, email, password = PW) {
  await page.goto(`${BASE}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
}
const catalogTab = async (page, name) => { await page.goto(`${BASE}/catalog`); await page.getByRole("tab", { name }).click(); await settled(page); };

try {
  const admin = await session("admin");
  await login(admin, "admin@concord.test");
  await admin.getByRole("heading", { name: "Overview" }).waitFor();
  await settled(admin);
  await shot(admin, "30-overview");

  // A plan with the admin's per-plan choices.
  await catalogTab(admin, "Plans");
  await admin.getByRole("button", { name: "New plan" }).click();
  let d = admin.locator("dialog");
  const planName = `Seats ${stamp}`;
  await d.getByLabel("Name").fill(planName);
  await d.getByLabel("Minimum quantity").fill("5");
  await d.getByLabel("Plan price", { exact: true }).fill("100");
  await d.getByLabel("Tax on plan price").selectOption({ label: "GST 18%" });
  await d.getByLabel("Available from").fill("2026-12-01");
  await d.getByLabel("Available until").fill("2026-01-01");
  await d.getByRole("button", { name: "Create" }).click();
  await d.getByText("on or after the start date").waitFor({ timeout: 8000 });
  check("plan with backwards dates refused on the field", true);
  await d.getByLabel("Available from").fill("");
  await d.getByLabel("Available until").fill("");
  await d.getByLabel("Can be paused").uncheck();
  await d.getByRole("button", { name: "Create" }).click();
  await admin.getByRole("button", { name: planName }).waitFor({ timeout: 8000 });
  check("plan created with its own rules", true);

  // Admin-only discount: percent, minimum quantity, usage limit of one.
  await catalogTab(admin, "Discounts");
  await admin.getByRole("button", { name: "New discount rule" }).click();
  d = admin.locator("dialog");
  const ruleName = `Better price ${stamp}`;
  await d.getByLabel("Name").fill(ruleName);
  await d.getByLabel("Percent off").fill("10");
  await d.getByLabel("Usage limit").fill("1");
  await d.getByLabel("Minimum quantity").fill("5");
  await d.getByLabel("Starts").fill("2026-01-01");
  await d.getByLabel("Applies to").selectOption("products");
  await d.getByRole("button", { name: "Create" }).click();
  await d.getByText("Choose at least one product").waitFor({ timeout: 8000 });
  check("product discount with no products refused", true);
  await d.getByLabel("Applies to").selectOption("subscription");
  await shot(admin, "31-discount-form");
  await d.getByRole("button", { name: "Create" }).click();
  await admin.getByRole("button", { name: ruleName }).waitFor({ timeout: 8000 });
  check("discount rule created", true);

  // Template.
  await catalogTab(admin, "Templates");
  await admin.getByRole("button", { name: "New template" }).click();
  d = admin.locator("dialog");
  const templateName = `Offer ${stamp}`;
  await d.getByLabel("Name").fill(templateName);
  await d.getByLabel(/^Plan/).selectOption({ label: planName });
  await d.getByLabel("Valid for (days)").fill("20");
  await d.getByRole("button", { name: "Add line" }).click();
  await d.getByLabel("Product").selectOption({ label: "Concord Suite" });
  await d.getByLabel("Variant").selectOption({ label: "Odoo" });
  await d.getByLabel("Qty").fill("5");
  await d.getByRole("button", { name: "Create" }).click();
  await admin.getByRole("button", { name: templateName }).waitFor({ timeout: 8000 });
  check("template with a variant line created", true);

  // In-use records can't be deleted, and the message says why.
  await admin.getByRole("button", { name: templateName }).click();
  await catalogTab(admin, "Taxes");
  await admin.getByRole("button", { name: "GST 18%" }).click();
  await admin.locator("dialog").getByRole("button", { name: "Delete" }).click();
  await admin.locator("dialog").getByText("in use").waitFor({ timeout: 8000 });
  check("deleting a tax rule in use is refused clearly", true);

  // Quote by hand with a variant: minimum quantity is enforced.
  await admin.goto(`${BASE}/subscriptions/new`);
  await admin.getByLabel("Customer").fill("customer@concord.test");
  await admin.getByRole("button", { name: /customer@concord.test/ }).click();
  await admin.getByLabel(/^Plan/).selectOption({ label: `${planName} (₹100.00 / month)` });
  await admin.getByRole("button", { name: "Add line" }).click();
  await admin.getByLabel("Product").selectOption({ label: "Concord Suite (₹999.00)" });
  await admin.getByLabel("Variant").selectOption({ label: "Odoo (+₹560.00)" });
  await admin.getByLabel("Qty").fill("2");
  await admin.getByRole("button", { name: "Create draft" }).click();
  await admin.getByText("needs a quantity of at least 5").waitFor({ timeout: 8000 });
  check("minimum quantity refused on screen", true);
  await admin.getByLabel("Qty").fill("5");
  await admin.getByRole("button", { name: "Create draft" }).click();
  await admin.getByRole("button", { name: "Send quotation" }).waitFor({ timeout: 8000 });
  await settled(admin);
  // 100 + 5 x (999 + 560) = 7,895. Tax 18% = 1,421.10. Total 9,316.10.
  check("variant price and plan fee in the total", await admin.getByText("₹9,316.10").count() > 0);
  const url = admin.url();

  // Edit the draft.
  await admin.getByRole("button", { name: "Edit" }).click();
  d = admin.locator("dialog");
  await d.getByLabel("Payment terms (days)").fill("15");
  await d.getByRole("button", { name: "Save changes" }).click();
  await d.waitFor({ state: "detached", timeout: 8000 });
  await settled(admin);
  check("draft edit saved", await admin.getByText("15 days").count() > 0);

  // Attach the discount: appears by itself. 7,895 - 10% of the covered 7,895 = 7,105.50; +18% = 8,384.49.
  await admin.getByRole("button", { name: "Discount" }).click();
  d = admin.locator("dialog");
  await d.getByLabel("Discount rule").selectOption({ label: ruleName });
  await d.getByRole("button", { name: "Save" }).click();
  await d.waitFor({ state: "detached", timeout: 8000 });
  await settled(admin);
  check("preview shows the discount", await admin.getByText("₹8,384.49").count() > 0);
  await shot(admin, "32-discounted", true);

  // Back and forth through the quotation stage.
  await admin.getByRole("button", { name: "Send quotation" }).click();
  await admin.getByRole("button", { name: "Back to draft" }).click();
  await admin.getByRole("button", { name: "Send quotation" }).waitFor({ timeout: 8000 });
  check("quotation can go back to draft", true);
  await admin.getByRole("button", { name: "Send quotation" }).click();
  await admin.getByRole("button", { name: "Confirm", exact: true }).click();
  await admin.getByRole("button", { name: "Activate" }).click();
  await admin.locator("dialog").getByRole("button", { name: "Activate" }).click();
  await admin.getByRole("button", { name: "Renew" }).waitFor({ timeout: 8000 });
  await settled(admin);
  check("plan that can't pause offers no Pause button", await admin.getByRole("button", { name: "Pause" }).count() === 0);

  const expiry = () => admin.locator("dt", { hasText: "Expires" }).locator("..").locator("dd").innerText();
  const before = await expiry();
  await admin.getByRole("button", { name: "Renew" }).click();
  await admin.getByText("Renewed: expiry moved").waitFor({ timeout: 8000 });
  check("renew moved the expiry", (await expiry()) !== before, `${before} -> ${await expiry()}`);

  // The discount was used once on the first invoice, and the limit was one.
  await catalogTab(admin, "Discounts");
  check("discount shows one use out of one", await admin.locator("tr", { hasText: ruleName }).getByText("1 / 1").count() > 0);

  // Cancel gives the use back, and the period can be reissued with the discount again.
  await admin.goto(url);
  await settled(admin);
  await admin.locator("section", { hasText: "Invoices" }).getByRole("link", { name: /^INV-/ }).first().click();
  await admin.getByRole("button", { name: "Cancel invoice" }).click();
  await admin.locator("dialog").getByRole("button", { name: "Cancel invoice" }).click();
  await admin.getByRole("button", { name: "Reissue" }).waitFor({ timeout: 8000 });
  check("invoice cancelled", true);
  await shot(admin, "33-cancelled");
  const cancelled = await admin.locator("h1").innerText();
  await admin.getByRole("button", { name: "Reissue" }).click();
  await admin.waitForFunction((old) => document.querySelector("h1")?.innerText !== old, cancelled, { timeout: 8000 });
  await admin.getByRole("button", { name: "Confirm", exact: true }).waitFor({ timeout: 8000 });
  await settled(admin);
  check("reissued as a new number, with the discount", await admin.getByText("₹8,384.49").count() > 0);

  // Bulk confirm drafts.
  await admin.goto(`${BASE}/invoices?status=draft`);
  await settled(admin);
  const bulk = admin.getByRole("button", { name: /^Confirm \d+ on this page/ });
  check("bulk confirm is offered", await bulk.count() === 1);
  await bulk.click();
  await settled(admin);
  await admin.waitForTimeout(800);
  check("bulk confirm leaves no error", await admin.getByRole("alert").count() === 0);

  // Lists: search, filter and paging stay in the URL.
  await admin.goto(`${BASE}/subscriptions`);
  await settled(admin);
  await admin.getByLabel("Status").selectOption("paused");
  await settled(admin);
  check("status filter in the URL", admin.url().includes("status=paused"));
  await admin.getByRole("button", { name: "Next page" }).click();
  await settled(admin);
  check("paging in the URL", admin.url().includes("page=2"));
  await admin.reload();
  await settled(admin);
  check("filter and page survive a reload", await admin.getByText("Page 2 of").count() > 0);
  await admin.goto(`${BASE}/customers`);
  await admin.getByRole("searchbox").fill("zzzznotreal");
  await admin.getByText("No customers match").waitFor({ timeout: 8000 });
  check("empty search result has a helpful message", true);
  await admin.getByRole("button", { name: "New customer" }).first().click();
  d = admin.locator("dialog");
  await d.getByLabel("Contact name").fill("New Person");
  await d.getByLabel("Email").fill("not-an-email");
  await d.getByRole("button", { name: "Add customer" }).click();
  await d.getByText(/valid email/).waitFor({ timeout: 8000 });
  check("invalid customer email refused", true);
  await d.getByLabel("Email").fill(`new${stamp}@example.com`);
  await d.getByRole("button", { name: "Add customer" }).click();
  await admin.getByRole("heading", { name: "New Person" }).waitFor({ timeout: 8000 });
  check("customer created by staff with no login", true);

  // Only the admin adds staff, and the password rules apply.
  await admin.goto(`${BASE}/team`);
  await admin.getByRole("button", { name: "Add staff" }).first().click();
  d = admin.locator("dialog");
  await d.getByLabel("Name").fill("New Staff");
  await d.getByLabel("Email").fill(`staff${stamp}@concord.test`);
  await d.getByLabel("Temporary password").fill("Str0ng!pass");
  await shot(admin, "34-add-staff");
  await d.getByRole("button", { name: "Add staff member" }).click();
  await admin.getByText(`staff${stamp}@concord.test`).waitFor({ timeout: 8000 });
  check("admin added a staff member", true);

  // Customer pauses and resumes from the portal.
  const portal = await session("portal");
  await login(portal, "customer@concord.test");
  await portal.getByRole("heading", { name: /Welcome/ }).waitFor();
  await settled(portal);
  await portal.getByRole("link", { name: "SUB-000002" }).click();
  await portal.getByRole("button", { name: "Pause" }).click();
  await portal.getByRole("button", { name: "Resume" }).waitFor({ timeout: 8000 });
  check("customer paused their subscription", true);
  await portal.getByRole("button", { name: "Resume" }).click();
  await portal.getByRole("button", { name: "Pause" }).waitFor({ timeout: 8000 });
  check("customer resumed it", true);
  await portal.getByRole("button", { name: "Close subscription" }).click();
  check("closing asks first", await portal.locator("dialog").getByText("can't be undone").count() > 0);
  await portal.locator("dialog").getByRole("button", { name: "Keep as it is" }).click();

  // Password reset, using the link from the backend's email output.
  const owner = `reset${stamp}@example.com`;
  const fresh = await session("reset");
  await fresh.goto(`${BASE}/signup`);
  await fresh.getByLabel("Your name").fill("Reset Tester");
  await fresh.getByLabel("Email").fill(owner);
  await fresh.getByLabel("Password").fill("Str0ng!pass");
  await fresh.getByRole("button", { name: "Create account" }).click();
  await fresh.getByRole("heading", { name: /Welcome/ }).waitFor();
  await fresh.getByRole("button", { name: "Log out" }).click();
  await fresh.getByRole("link", { name: "Forgot password?" }).click();
  await fresh.getByLabel("Email").fill(owner);
  await fresh.getByRole("button", { name: "Send reset link" }).click();
  await fresh.getByText("a reset link is on its way").waitFor({ timeout: 8000 });
  await fresh.waitForTimeout(500);
  const links = [...readFileSync(SERVER_LOG, "utf8").matchAll(/http:\/\/localhost:5173\/reset-password\/\S+/g)];
  const link = links.at(-1)?.[0];
  check("reset email was produced", Boolean(link));
  await fresh.goto(link);
  await fresh.getByLabel("New password").fill("weak");
  await fresh.getByRole("button", { name: "Change password" }).click();
  await fresh.getByText(/too short|at least 9/).waitFor({ timeout: 8000 });
  check("weak new password refused", true);
  await fresh.getByLabel("New password").fill("N3w!password");
  await fresh.getByRole("button", { name: "Change password" }).click();
  await fresh.getByText("Your password has been changed").waitFor({ timeout: 8000 });
  await fresh.goto(link);
  await fresh.getByLabel("New password").fill("An0ther!pass");
  await fresh.getByRole("button", { name: "Change password" }).click();
  await fresh.getByText(/invalid or has expired/).waitFor({ timeout: 8000 });
  check("a used reset link stops working", true);
  await login(fresh, owner, "N3w!password");
  await fresh.getByRole("heading", { name: /Welcome/ }).waitFor({ timeout: 8000 });
  check("logged in with the new password", true);
} catch (error) {
  problems.push(`STOPPED: ${error.message.split("\n").slice(0, 3).join(" | ")}`);
  for (const context of browser.contexts()) for (const page of context.pages()) await page.screenshot({ path: `${SHOTS}/failure-${Date.now()}.png` }).catch(() => {});
}
await browser.close();
console.log(`\n${passed} passed, ${problems.length} problems`);
for (const problem of problems) console.log("PROBLEM:", problem);
process.exit(problems.length ? 1 : 0);
