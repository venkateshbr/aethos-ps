// Step 1: UI signup + auth guard verification (Issue #111).
const { chromium } = require('playwright');
const { FRONTEND, API, shotPath, writeEvidence } = require('./helpers');

const TS = Date.now();
const EMAIL = `aksha-pilot-${TS}@aethos-qa.dev`;
const PASSWORD = 'Aksha-pilot-2026!';
const TENANT_NAME = `Aksha Pilot ${TS}`;
const COUNTRY = 'US';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  const results = {
    run_id: TS,
    email: EMAIL,
    password: PASSWORD,
    tenant_name: TENANT_NAME,
    steps: [],
  };

  // ===== AUTH GUARD CHECK (Issue #111) =====
  console.log('=== AUTH GUARD CHECK (#111) ===');
  await page.goto(`${FRONTEND}/app/inbox`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const guardPath = new URL(page.url()).pathname;
  const guardPassed = guardPath === '/' || guardPath.startsWith('/login') || guardPath === '/auth/login';
  console.log(`/app/inbox without token → ${guardPath} (pass=${guardPassed})`);
  await page.screenshot({ path: shotPath('step1-01-authguard-redirect') });
  results.steps.push({ name: 'auth_guard_redirect_111', expected: '/ or /login', actual: guardPath, pass: guardPassed });

  // ===== SIGNUP =====
  console.log('=== SIGNUP ===');
  await page.goto(`${FRONTEND}/`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: shotPath('step1-02-landing') });

  // Try multiple CTAs to find signup
  const ctaCandidates = [
    'a[href*="signup" i]',
    'a:has-text("Get started")',
    'a:has-text("Sign up")',
    'a:has-text("Start free")',
    'a:has-text("Start trial")',
    'a:has-text("Create account")',
    'button:has-text("Get started")',
    'button:has-text("Sign up")',
  ];
  let ctaClicked = null;
  for (const sel of ctaCandidates) {
    const loc = page.locator(sel).first();
    if (await loc.count()) {
      try {
        await loc.click({ timeout: 2000 });
        ctaClicked = sel;
        console.log(`Clicked CTA: ${sel}`);
        break;
      } catch (e) {}
    }
  }
  if (!ctaClicked) {
    console.log('No CTA found — direct nav /signup');
    await page.goto(`${FRONTEND}/signup`, { waitUntil: 'networkidle' });
  }
  await page.waitForTimeout(2500);
  await page.screenshot({ path: shotPath('step1-03-signup-form') });

  // Dump all inputs/buttons on the page for diagnostics
  const formInfo = await page.evaluate(() => {
    const all = Array.from(document.querySelectorAll('input, button, select, mat-select, [formcontrolname]'));
    return all.map((el) => ({
      tag: el.tagName,
      type: el.type || null,
      name: el.name || el.getAttribute('formcontrolname') || null,
      id: el.id || null,
      placeholder: el.placeholder || null,
      label: el.getAttribute('aria-label') || null,
      text: ((el.innerText || el.value || '') + '').substring(0, 100),
    }));
  });
  writeEvidence('step1-signup-form-inputs.json', JSON.stringify(formInfo, null, 2));
  console.log(`Form has ${formInfo.length} inputs/buttons`);

  // Fill via candidate selectors
  async function fillByAny(value, names) {
    for (const n of names) {
      const lower = n.toLowerCase();
      for (const attr of ['name', 'formcontrolname', 'id', 'placeholder', 'type', 'aria-label']) {
        const variants = [
          `input[${attr}="${n}"]`,
          `input[${attr}="${lower}"]`,
          `input[${attr}*="${n}" i]`,
        ];
        for (const sel of variants) {
          const loc = page.locator(sel).first();
          if (await loc.count()) {
            try { await loc.fill(value, { timeout: 2000 }); return sel; } catch (e) {}
          }
        }
      }
    }
    return null;
  }

  const emailSel = await fillByAny(EMAIL, ['email', 'username']);
  const pwSel = await fillByAny(PASSWORD, ['password', 'passwd']);
  const tenantSel = await fillByAny(TENANT_NAME, ['tenant_name', 'tenantName', 'company', 'workspace', 'organization', 'firm']);

  // Country may be a select
  let countrySel = await fillByAny(COUNTRY, ['country']);
  if (!countrySel) {
    // Try mat-select / select
    const selectCandidates = ['mat-select[formcontrolname*="country" i]', 'select[name*="country" i]', 'select[formcontrolname*="country" i]'];
    for (const sel of selectCandidates) {
      const loc = page.locator(sel).first();
      if (await loc.count()) {
        try {
          await loc.click({ timeout: 1500 });
          await page.waitForTimeout(500);
          // Try clicking US option
          const opt = page.locator('mat-option:has-text("United States"), option:has-text("United States"), mat-option:has-text("US")').first();
          if (await opt.count()) {
            await opt.click({ timeout: 1500 });
            countrySel = sel + ' (mat-select)';
            break;
          }
        } catch (e) {}
      }
    }
  }

  results.steps.push({
    name: 'signup_form_fill',
    selectors: { email: emailSel, password: pwSel, tenant: tenantSel, country: countrySel },
  });

  await page.waitForTimeout(800);
  await page.screenshot({ path: shotPath('step1-04-signup-filled') });

  // Hook into network for signup response
  const signupResponses = [];
  page.on('response', async (resp) => {
    if (resp.url().includes('/api/v1/auth/signup') || resp.url().includes('/auth/signup')) {
      try {
        signupResponses.push({
          url: resp.url(),
          status: resp.status(),
          body: (await resp.text()).substring(0, 2000),
        });
      } catch (e) {}
    }
  });

  // Submit
  const submitCandidates = [
    'button[type="submit"]',
    'button:has-text("Sign up")',
    'button:has-text("Create account")',
    'button:has-text("Create")',
    'button:has-text("Get started")',
    'button:has-text("Start")',
    'button:has-text("Continue")',
  ];
  let submitted = null;
  for (const sel of submitCandidates) {
    const loc = page.locator(sel).first();
    if (await loc.count()) {
      try {
        await loc.click({ timeout: 2000 });
        submitted = sel;
        console.log(`Clicked submit: ${sel}`);
        break;
      } catch (e) {}
    }
  }

  await page.waitForTimeout(7000);
  const postPath = new URL(page.url()).pathname;
  console.log(`After submit → ${postPath}`);
  await page.screenshot({ path: shotPath('step1-05-post-signup') });

  // Capture token + storage
  const post = await page.evaluate(() => {
    const ls = {};
    try { Object.keys(localStorage).forEach(k => ls[k] = localStorage.getItem(k)); } catch (e) {}
    const ss = {};
    try { Object.keys(sessionStorage).forEach(k => ss[k] = sessionStorage.getItem(k)); } catch (e) {}
    return {
      url: window.location.href,
      title: document.title,
      localStorage: ls,
      sessionStorage: ss,
      cookies: document.cookie,
      bodyText: document.body.innerText.substring(0, 2000),
    };
  });
  writeEvidence('step1-post-signup-page-state.json', JSON.stringify(post, null, 2));
  writeEvidence('step1-signup-network.json', JSON.stringify(signupResponses, null, 2));

  // Pull out any token-shaped value
  const tokenKey = Object.keys(post.localStorage).find(k => /token|jwt|session|auth/i.test(k));
  const access = tokenKey ? post.localStorage[tokenKey] : null;

  results.steps.push({
    name: 'signup_submit',
    submitted_via: submitted,
    post_path: postPath,
    token_key: tokenKey,
    token_present: !!access,
    signup_api_responses: signupResponses.map(r => ({ url: r.url, status: r.status })),
  });

  writeEvidence('step1-results.json', JSON.stringify(results, null, 2));
  console.log('=== STEP 1 RESULTS ===');
  console.log(JSON.stringify(results, null, 2));

  await browser.close();
}

main().catch((e) => { console.error('FATAL:', e); process.exit(1); });
