// Walks the whole demo path in a real browser. Every step checks the page, not just the click.
import { chromium } from "playwright-core";

const BASE = "http://localhost:5173";
const SHOTS = process.argv[2];
const PW = "Concord!demo1";
const stamp = Date.now();
const problems = [];
const passed = [];
const check = (name, ok, extra = "") => { (ok ? passed : problems).push(ok ? name : `${name} ${extra}`); console.log(`${ok ? "ok  " : "FAIL"} ${name} ${ok ? "" : extra}`); };

const browser = await chromium.launch({ channel: "msedge", headless: true });

async function session(label, viewport = { width: 1280, height: 860 }) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  page.on("pageerror", (e) => problems.push(`[${label}] page error: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error" && !/status of (400|401|403|404|409|422)/.test(m.text())) problems.push(`[${label}] console: ${m.text().slice(0, 200)}`); });
  page.on("response", (r) => { if (r.status() >= 500) problems.push(`[${label}] ${r.status()} ${r.url()}`); });
  return page;
}
const shot = (page, name, fullPage = true) => page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage });
const settled = async (page) => { await page.waitForTimeout(150); await page.waitForFunction(() => !document.querySelector(".animate-pulse"), null, { timeout: 15000 }); };
const heading = (page, text) => page.getByRole("heading", { name: text, exact: true }).first().waitFor({ timeout: 8000 });

async function login(page, email) {
  await page.goto(`${BASE}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PW);
  await page.getByRole("button", { name: "Log in" }).click();
}

try {
  const admin = await session("admin");

  // Bad login first: the form must show the server's message.
  await admin.goto(`${BASE}/login`);
  await admin.getByLabel("Email").fill("admin@concord.test");
  await admin.getByLabel("Password").fill("wrong");
  await admin.getByRole("button", { name: "Log in" }).click();
  await admin.getByText("Incorrect email or password.").waitFor({ timeout: 8000 });
  check("wrong password shows a clear message", true);

  await login(admin, "admin@concord.test");
  await heading(admin, "Overview");
  await settled(admin);
  check("admin login reaches Overview", true);
  await shot(admin, "01-overview");

  // Launch a product with the statement's own example, Brand: Odoo +560.
  await admin.getByRole("link", { name: "Catalog" }).click();
  await heading(admin, "Catalog");
  await settled(admin);
  await shot(admin, "02-catalog");
  await admin.getByRole("button", { name: "New product" }).click();
  await admin.getByRole("button", { name: "Create" }).click();
  await admin.locator("dialog").getByText(/required|may not be blank|This field/).first().waitFor({ timeout: 8000 });
  check("empty product form shows field errors", true);
  const productName = `Launch Suite ${stamp}`;
  await admin.locator("dialog").getByLabel("Name").fill(productName);
  await admin.locator("dialog").getByLabel("Sales price").fill("1000");
  await admin.locator("dialog").getByLabel("Tax rule").selectOption({ label: "GST 18%" });
  await admin.getByRole("button", { name: "Add variant" }).click();
  await admin.locator("dialog").getByLabel("Value").fill("Odoo");
  await admin.locator("dialog").getByLabel("Adds to price").fill("560");
  await shot(admin, "03-product-form", false);
  await admin.getByRole("button", { name: "Create" }).click();
  await admin.getByRole("button", { name: productName }).waitFor({ timeout: 8000 });
  check("product with Odoo +560 variant created", true);

  // Quote from a template.
  await admin.getByRole("link", { name: "Subscriptions" }).click();
  await heading(admin, "Subscriptions");
  await settled(admin);
  await shot(admin, "04-subscriptions");
  await admin.getByRole("link", { name: "New quotation" }).click();
  await heading(admin, "New quotation");
  await admin.getByRole("button", { name: "Create draft" }).click();
  await admin.getByText(/This field|may not be null/).first().waitFor({ timeout: 8000 });
  check("empty quotation shows errors", true);
  await admin.getByLabel("Customer").fill("customer@concord.test");
  await admin.getByRole("button", { name: /customer@concord.test/ }).click();
  await admin.getByLabel("Quotation template").selectOption({ label: "Small shop starter (valid 14 days)" });
  await shot(admin, "05-new-quotation", false);
  await admin.getByRole("button", { name: "Create draft" }).click();
  await admin.getByRole("button", { name: "Send quotation" }).waitFor({ timeout: 8000 });
  await settled(admin);
  const subscriptionUrl = admin.url();
  const subscriptionId = subscriptionUrl.split("/").pop();
  const number = await admin.locator("h1").innerText();
  check("draft created from template", /^SUB-/.test(number), number);
  await shot(admin, "06-draft");
  // 2 x 999 + 299 = 2297, plus 18% = 2710.46.
  check("preview total is the hand-worked 2,710.46", await admin.getByText("₹2,710.46").count() > 0);
  await admin.getByRole("button", { name: "Send quotation" }).click();
  await admin.getByRole("button", { name: "Back to draft" }).waitFor({ timeout: 8000 });
  check("quotation sent", true);

  // The customer accepts in the portal.
  const portal = await session("portal");
  await login(portal, "customer@concord.test");
  await portal.getByRole("heading", { name: /Welcome/ }).waitFor({ timeout: 8000 });
  await settled(portal);
  await shot(portal, "07-portal");
  check("customer lands on portal", portal.url().endsWith("/portal"));
  await portal.goto(`${BASE}/portal/subscriptions/${subscriptionId}`);
  await portal.getByRole("button", { name: "Accept quotation" }).click();
  await portal.getByRole("button", { name: "Close subscription" }).first().waitFor({ state: "attached", timeout: 8000 });
  await settled(portal);
  await shot(portal, "08-portal-accepted");
  check("customer accepted the quotation", await portal.getByText("confirmed to").count() + await portal.getByText("Quotation to confirmed", { exact: false }).count() > 0);
  check("customer has no activate button", await portal.getByRole("button", { name: "Activate" }).count() === 0);

  // Access control in the UI: staff pages and someone else's records.
  await portal.goto(`${BASE}/customers`);
  await portal.getByRole("heading", { name: /Welcome/ }).waitFor({ timeout: 8000 });
  check("customer sent away from staff pages", portal.url().endsWith("/portal"));
  await portal.goto(`${BASE}/portal/invoices/999999`);
  await portal.getByText("We couldn't find that.").waitFor({ timeout: 8000 });
  check("unknown or other customer's invoice shows not found", true);

  // Activate: stepper moves and the first invoice appears.
  await admin.reload();
  await admin.getByRole("button", { name: "Activate" }).click();
  await admin.locator("dialog").getByRole("button", { name: "Activate" }).click();
  await admin.getByRole("button", { name: "Pause" }).waitFor({ timeout: 8000 });
  await settled(admin);
  await shot(admin, "09-active");
  check("activated", true);

  await admin.locator("section", { hasText: "Invoices" }).getByRole("link", { name: /^INV-/ }).first().click();
  await admin.getByRole("button", { name: "Confirm" }).waitFor({ timeout: 8000 });
  await settled(admin);
  await shot(admin, "10-invoice-draft");
  check("invoice shows hand-worked total", await admin.getByText("₹2,710.46").count() > 0);
  await admin.getByRole("button", { name: "Confirm" }).click();
  await admin.getByRole("button", { name: "Record payment" }).waitFor({ timeout: 8000 });
  check("invoice confirmed", true);

  await admin.getByRole("button", { name: "Send", exact: true }).click();
  await admin.getByText(/Sent to/).waitFor({ timeout: 10000 });
  check("invoice sent", true);

  // Payments: too much is refused, partial stays open, the rest settles it.
  await admin.getByRole("button", { name: "Record payment" }).click();
  const dialog = admin.locator("dialog");
  await dialog.getByLabel("Amount").fill("99999");
  await dialog.getByRole("button", { name: "Record payment" }).click();
  await dialog.getByText(/exceeds/).first().waitFor({ timeout: 8000 });
  check("overpayment refused on screen", true);
  await shot(admin, "11-overpayment", false);
  await dialog.getByLabel("Amount").fill("1000");
  await dialog.getByLabel("Note").fill("UTR 4471");
  await dialog.getByRole("button", { name: "Record payment" }).click();
  await admin.getByText("UTR 4471").waitFor({ timeout: 8000 });
  await settled(admin);
  check("partial payment leaves ₹1,710.46 due", await admin.getByText("₹1,710.46").count() > 0);
  await admin.getByRole("button", { name: "Record payment" }).click();
  await dialog.getByRole("button", { name: "Record payment" }).click();
  await admin.getByRole("button", { name: "Record payment" }).waitFor({ state: "detached", timeout: 8000 });
  await settled(admin);
  await shot(admin, "12-invoice-paid");
  check("second payment settles it", await admin.getByText("paid", { exact: true }).count() > 0);

  // Print view.
  const invoiceId = admin.url().split("/").pop();
  const printPage = await admin.context().newPage();
  await printPage.goto(`${BASE}/invoices/${invoiceId}/print`);
  await printPage.getByText("Paid in full").waitFor({ timeout: 8000 });
  await printPage.screenshot({ path: `${SHOTS}/13-print.png`, fullPage: true });
  await printPage.close();
  check("print view renders", true);

  // Billing day, twice. The moment that matters most.
  await admin.getByRole("link", { name: "Billing" }).click();
  await heading(admin, "Billing");
  const future = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  await admin.getByLabel("Bill everything due by").fill(future);
  await settled(admin);
  await admin.getByText("Demo control").waitFor({ timeout: 8000 });
  await admin.getByRole("button", { name: "Run billing" }).click();
  await admin.getByText(/new draft invoices|Nothing was due/).waitFor({ timeout: 150000 });
  await settled(admin);
  await shot(admin, "14-billing-first-run");
  const created = await admin.locator("dt", { hasText: "Created" }).locator("..").locator("dd").innerText();
  check("first run created invoices", Number(created.replace(/,/g, "")) > 0, `created=${created}`);
  await admin.getByRole("button", { name: "Run billing" }).click();
  await admin.getByText("Nothing was due").waitFor({ timeout: 150000 });
  await settled(admin);
  await shot(admin, "15-billing-second-run");
  const again = await admin.locator("dt", { hasText: "Created" }).locator("..").locator("dd").innerText();
  check("second run created nothing", again === "0", `created=${again}`);

  // Finance.
  await admin.getByRole("link", { name: "Reports" }).click();
  await heading(admin, "Reports");
  await settled(admin);
  await shot(admin, "16-reports");
  check("reports show figures", await admin.getByText("How late is the overdue money?").count() > 0);
  await admin.getByLabel("Plan").selectOption({ label: "Enterprise Yearly" });
  await settled(admin);
  check("report filter goes in the URL", admin.url().includes("plan="));

  await admin.goto(`${BASE}/invoices?overdue=true`);
  await settled(admin);
  await shot(admin, "17-overdue");
  check("overdue list has rows", await admin.getByRole("link", { name: /^INV-/ }).count() > 0);
  await admin.goto(`${BASE}/customers`);
  await settled(admin);
  await admin.getByRole("link", { name: /Menon|Nair|Sharma|Iyer|Reddy|Kapoor|Das|Pillai|Gupta|Thomas|Rao|Joshi/ }).first().click();
  await settled(admin);
  await shot(admin, "18-customer");
  check("customer page shows outstanding", await admin.getByText("Outstanding").count() > 0);
  await admin.goto(`${BASE}/team`);
  await settled(admin);
  await shot(admin, "19-team");
  check("team page lists staff", await admin.getByText("staff@concord.test").count() > 0);

  // Staff are limited.
  const staff = await session("staff");
  await login(staff, "staff@concord.test");
  await heading(staff, "Overview");
  check("staff have no Billing link", await staff.getByRole("link", { name: "Billing" }).count() === 0);
  await staff.goto(`${BASE}/catalog`);
  await heading(staff, "Catalog");
  await settled(staff);
  check("staff can't add products", await staff.getByRole("button", { name: "New product" }).count() === 0);
  await staff.goto(`${BASE}/team`);
  await heading(staff, "Overview");
  check("staff sent away from Team", true);

  // Signup, with the live password checklist.
  const fresh = await session("signup");
  await fresh.goto(`${BASE}/signup`);
  await fresh.getByLabel("Your name").fill("Test Owner");
  await fresh.getByLabel("Email").fill(`owner${stamp}@example.com`);
  await fresh.getByLabel("Password").fill("weak");
  await fresh.getByRole("button", { name: "Create account" }).click();
  await fresh.getByText(/too short|at least 9/).waitFor({ timeout: 8000 });
  check("weak password refused on screen", true);
  await shot(fresh, "20-signup-weak", false);
  await fresh.getByLabel("Password").fill("Str0ng!pass");
  await fresh.getByRole("button", { name: "Create account" }).click();
  await fresh.getByRole("heading", { name: /Welcome/ }).waitFor({ timeout: 8000 });
  await settled(fresh);
  check("signup lands on an empty portal", await fresh.getByText("No subscriptions yet").count() > 0);
  await shot(fresh, "21-portal-empty");

  // Phone width: nothing may scroll the whole page sideways.
  const phone = await session("phone", { width: 390, height: 800 });
  await login(phone, "admin@concord.test");
  await heading(phone, "Overview");
  for (const path of ["/", "/subscriptions", `/subscriptions/${subscriptionId}`, `/invoices/${invoiceId}`, "/billing", "/reports", "/catalog", "/customers"]) {
    await phone.goto(`${BASE}${path}`);
    await settled(phone);
    const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    check(`phone ${path} has no sideways scroll`, overflow <= 0, `overflow=${overflow}px`);
  }
  await phone.goto(`${BASE}/`);
  await settled(phone);
  await shot(phone, "22-phone-overview");
  await phone.goto(`${BASE}/subscriptions/${subscriptionId}`);
  await settled(phone);
  await shot(phone, "23-phone-subscription");
} catch (error) {
  problems.push(`STOPPED: ${error.message.split("\n").slice(0, 3).join(" | ")}`);
  for (const context of browser.contexts()) for (const page of context.pages()) await page.screenshot({ path: `${SHOTS}/failure-${Date.now()}.png` }).catch(() => {});
}
await browser.close();
console.log(`\n${passed.length} passed, ${problems.length} problems`);
for (const problem of problems) console.log("PROBLEM:", problem);
process.exit(problems.length ? 1 : 0);
