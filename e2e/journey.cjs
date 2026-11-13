// Browser journey against a running CRM (started by scripts/e2e.sh).
// Runs the whole journey at a desktop viewport, then checks key screens at a phone viewport.
// Usage: CRM_URL=http://127.0.0.1:8765 CRM_DEMO_PASSWORD=... node e2e/journey.cjs
const { chromium } = require("playwright");
const { execFileSync } = require("node:child_process");
const { mkdirSync } = require("node:fs");
const assert = require("node:assert/strict");

const BASE = process.env.CRM_URL || "http://127.0.0.1:8765";
const PASSWORD = process.env.CRM_DEMO_PASSWORD;
const OUT = process.env.E2E_OUT || "var/e2e-artifacts";
const PY = process.env.CRM_PYTHON || ".venv/bin/python";
assert.ok(PASSWORD, "CRM_DEMO_PASSWORD is required");
mkdirSync(OUT, { recursive: true });

const results = [];
function step(name) { results.push(name); console.log(`  ✓ ${name}`); }

async function login(page, email) {
  await page.goto(`${BASE}/accounts/login/`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/accounts/login"));
}

async function logout(page) {
  await page.getByRole("button", { name: "Sign out" }).first().click();
  await page.waitForURL(/\/accounts\/login\//);
}

function consoleGuard(page, errors) {
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
}

async function desktopJourney(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 } });
  const page = await ctx.newPage();
  const errors = [];
  consoleGuard(page, errors);
  const name = `E2E Customer ${Date.now()}`;

  // Anonymous access is redirected to login.
  await page.goto(`${BASE}/contacts/`);
  assert.match(page.url(), /\/accounts\/login\//);
  step("anonymous user is sent to sign-in");

  // Wrong password is rejected.
  await page.getByLabel("Email").fill("cora@demo.example.test");
  await page.getByLabel("Password").fill("definitely-wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Email or password is incorrect").waitFor();
  step("wrong password rejected");

  // 1. Coordinator captures a customer into the shared pool.
  await login(page, "cora@demo.example.test");
  await page.goto(`${BASE}/contacts/new/`);
  await page.getByLabel("Name").fill(name);
  await page.getByLabel("Email").fill("e2e.customer@example.test");
  await page.getByLabel("Put in a shared pool").check();
  await page.getByLabel("Pool", { exact: true }).selectOption({ label: "North team pool" });
  await page.getByLabel("Inquiry (optional)").fill("Looking for a 2-bedroom near the park.");
  await page.screenshot({ path: `${OUT}/00-capture-form.png`, fullPage: true });
  await page.getByRole("button", { name: "Save contact" }).click();
  await page.getByRole("heading", { name }).waitFor();
  await page.screenshot({ path: `${OUT}/01-captured.png`, fullPage: true });
  step("coordinator captures customer into the pool");
  await logout(page);

  // 2. Agent claims it from shared work.
  await login(page, "ana@demo.example.test");
  await page.goto(`${BASE}/work/shared/`);
  await page.getByRole("button", { name: `Claim ${name}` }).click();
  await page.getByText(`You are now responsible for ${name}`).waitFor();
  step("agent claims the customer");

  // 3. Record the tour, linked to the inquiry.
  if (!(await page.getByRole("heading", { name }).isVisible())) {
    await page.goto(`${BASE}/contacts/?q=${encodeURIComponent(name)}`);
    await page.getByRole("link", { name }).first().click();
    await page.getByRole("heading", { name }).waitFor();
  }
  await page.getByLabel("What happened").selectOption("meeting_tour");
  await page.getByRole("textbox", { name: "Summary" }).fill("Toured unit 4B; liked the light, asked about parking.");
  const inquirySelect = page.getByLabel("Responds to inquiry");
  const options = await inquirySelect.locator("option").allTextContents();
  if (options.length > 1) await inquirySelect.selectOption({ index: 1 });
  await page.getByRole("button", { name: "Log interaction" }).click();
  await page.getByText("Interaction logged.").waitFor();
  await page.getByText("Toured unit 4B").first().waitFor();
  step("agent records the tour");

  // 4. Create the next action, already due (so attention picks it up).
  await page.getByText("Add next action").click();
  await page.getByRole("textbox", { name: "Next action" }).fill("Send floor plans and parking info");
  const due = new Date(Date.now() - 60 * 60 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  // Workspace timezone default is Asia/Shanghai (UTC+8).
  const local = new Date(due.getTime() + 8 * 3600 * 1000);
  const dueText = `${local.getUTCFullYear()}-${pad(local.getUTCMonth() + 1)}-${pad(local.getUTCDate())}T${pad(local.getUTCHours())}:${pad(local.getUTCMinutes())}`;
  await page.getByLabel("Due", { exact: true }).fill(dueText);
  await page.getByRole("button", { name: "Create task" }).click();
  await page.getByText("Next action created.").waitFor();
  step("agent creates the next action");

  // 5. Attention shows it as due.
  await page.goto(`${BASE}/attention/?scope=mine`);
  await page.getByText(name).first().waitFor();
  await page.getByText("Task overdue").first().waitFor();
  await page.screenshot({ path: `${OUT}/02-attention.png`, fullPage: true });
  step("attention queue shows the overdue next action");

  // 6. The durable worker runs the reminder sweep.
  execFileSync(PY, ["manage.py", "run_worker", "--once", "--sweep-now"], { stdio: "ignore", env: process.env });
  await page.goto(`${BASE}/automation/notifications/`);
  await page.getByText("Send floor plans and parking info").first().waitFor();
  step("worker reminder reaches the agent's notifications");

  // 7. Agent requests a handover to Ben; she stays responsible until he accepts.
  await page.goto(`${BASE}/contacts/`);
  await page.getByRole("link", { name }).first().click();
  await page.getByRole("link", { name: "Hand over / release" }).click();
  await page.getByLabel("Colleague", { exact: true }).selectOption({ label: "Ben Santos" });
  await page.getByRole("textbox", { name: "Reason" }).fill("Ben covers the park district");
  await page.getByLabel("Task: Send floor plans and parking info").selectOption("transfer");
  await page.getByRole("button", { name: "Request handover" }).click();
  await page.getByText("You remain responsible until it is accepted").waitFor();
  step("agent requests handover; remains responsible");
  await logout(page);

  // 8. Ben accepts.
  await login(page, "ben@demo.example.test");
  await page.goto(`${BASE}/work/shared/`);
  const row = page.locator("tr, .att-item, li, article").filter({ hasText: name }).first();
  await row.getByRole("button", { name: "Accept" }).click();
  await page.getByText("Accepted. You are now responsible.").waitFor();
  step("recipient accepts the handover");

  // 9. Reports reflect the source facts and drill down to them.
  await page.goto(`${BASE}/reports/`);
  await page.getByRole("heading", { name: "By acquisition source" }).waitFor();
  await page.goto(`${BASE}/reports/drill/?metric=acquisitions`);
  await page.getByText(name).first().waitFor();
  await page.screenshot({ path: `${OUT}/03-report-drill.png`, fullPage: true });
  step("reports drill down to the captured customer");

  // Sandbox messages are labelled as not sent.
  await page.goto(`${BASE}/messages/`);
  await page.getByText("not sent", { exact: false }).first().waitFor();
  step("customer messages are labelled as sandbox (not sent)");

  assert.deepEqual(errors, [], `browser console errors: ${errors.join("\n")}`);
  step("no browser console errors (CSP-clean)");
  await ctx.close();
}

async function narrowChecks(browser) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  const errors = [];
  consoleGuard(page, errors);
  await login(page, "ana@demo.example.test");
  for (const path of ["/", "/attention/", "/contacts/", "/work/shared/", "/work/tasks/", "/reports/", "/messages/"]) {
    await page.goto(`${BASE}${path}`);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (overflow > 1) {
      const culprits = await page.evaluate(() => {
        const w = document.documentElement.clientWidth;
        return [...document.querySelectorAll("body *")]
          .filter((el) => el.getBoundingClientRect().right > w + 1 && !(el.parentElement && el.parentElement.closest(".table-scroll")))
          .slice(-5).map((el) => `${el.tagName.toLowerCase()}.${[...el.classList].join(".")} right=${Math.round(el.getBoundingClientRect().right)}`);
      });
      assert.fail(`${path} scrolls sideways by ${overflow}px at 390px: ${culprits.join(" | ")}`);
    }
  }
  step("no horizontal page scroll at 390px on main screens");
  await page.goto(`${BASE}/`);
  await page.getByText("Menu").click();
  await page.locator(".mobile-nav__panel").getByRole("link", { name: /Contacts/ }).click();
  await page.waitForURL(/\/contacts\//);
  await page.screenshot({ path: `${OUT}/04-narrow-contacts.png`, fullPage: true });
  step("mobile menu navigates");
  assert.deepEqual(errors, [], `browser console errors: ${errors.join("\n")}`);
  await ctx.close();
}

(async () => {
  const browser = await chromium.launch(process.env.CRM_CHROMIUM_PATH
    ? { executablePath: process.env.CRM_CHROMIUM_PATH } : {});
  try {
    console.log("Desktop journey (1280px)");
    await desktopJourney(browser);
    console.log("Narrow viewport (390px)");
    await narrowChecks(browser);
    console.log(`E2E passed: ${results.length} checks`);
  } finally {
    await browser.close();
  }
})().catch((err) => { console.error(err); process.exit(1); });
