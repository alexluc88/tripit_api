#!/usr/bin/env node
/*
 * scrape_alaska_account.js — extract a traveler's Alaska profile into YAML.
 *
 * Reads a saved Playwright session (storage-state-<name>.json from
 * save_session.js) and pulls profile data off the signed-in account pages,
 * writing travelers/<name>.yaml.
 *
 * Usage:
 *   node scrape_alaska_account.js <name> [--show]
 *     <name>   matches storage-state-<name>.json
 *     --show   run headed so you can watch / re-auth if the session expired
 *
 * IMPORTANT — read before trusting the output:
 *   The PAGES and SELECTORS below are BEST-EFFORT. They were written without
 *   access to a live signed-in alaskaair.com DOM, so treat the first run as a
 *   tuning pass: every run also saves a screenshot + raw HTML per page under
 *   out/, and prints which fields it could NOT find. Open the out/*.html files,
 *   correct the selectors in the SELECTORS map, and re-run until the YAML is
 *   complete. Fields that stay null just mean "selector not matched yet".
 *
 * SENSITIVE DATA POLICY:
 *   This script intentionally does NOT scrape passport numbers or full payment
 *   card numbers. Saved cards are recorded as last-4 + brand only. Keep the
 *   truly sensitive items in a separate encrypted file or a password manager —
 *   never in travelers/<name>.yaml and never in chat.
 */
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { chromium } = require('playwright');

// --- Account pages to visit. Verify/adjust against your real account. ---
const PAGES = {
  dashboard: 'https://www.alaskaair.com/account/dashboard',
  profile:   'https://www.alaskaair.com/account/profile',
  travelers: 'https://www.alaskaair.com/account/saved-travelers',
  payment:   'https://www.alaskaair.com/account/payment-methods',
};

// --- Best-effort selectors. CSS or XPath. Tune using the out/*.html dumps. ---
// Each value is an array of candidates; the first one that matches wins.
const SELECTORS = {
  fullName:        ['[data-testid="profile-name"]', 'h1.account-name', '.profile-header__name'],
  dob:             ['[data-testid="date-of-birth"]', '#dateOfBirth', '.profile-dob'],
  mileagePlanNum:  ['[data-testid="mileage-plan-number"]', '.mileage-plan-number', '#mpNumber'],
  mileagePlanTier: ['[data-testid="elite-tier"]', '.tier-status', '.mvp-status'],
  knownTraveler:   ['[data-testid="known-traveler-number"]', '#ktn', '.ktn-value'],
  globalEntry:     ['[data-testid="global-entry"]', '#globalEntry', '.global-entry-value'],
  redress:         ['[data-testid="redress-number"]', '#redress', '.redress-value'],
  seatPreference:  ['[data-testid="seat-preference"]', '#seatPref', '.seat-preference-value'],
  companionFare:   ['[data-testid="companion-fare-status"]', '.companion-fare-status', '.visa-companion'],
};

// Saved-travelers list rows (each row -> a name). Tune against out/travelers.html.
const TRAVELER_ROW_SELECTORS = ['[data-testid="saved-traveler-row"]', '.saved-traveler', '.traveler-card'];
const TRAVELER_NAME_WITHIN   = ['.traveler-name', '[data-testid="traveler-name"]', 'h3'];

// Saved-payment rows -> brand + last4 ONLY (never the full PAN).
const PAYMENT_ROW_SELECTORS  = ['[data-testid="payment-method-row"]', '.payment-method', '.card-row'];
const PAYMENT_BRAND_WITHIN   = ['.card-brand', '[data-testid="card-brand"]'];
const PAYMENT_LAST4_WITHIN   = ['.card-last4', '[data-testid="card-last4"]', '.card-ending'];

const OUT_DIR = path.join(__dirname, 'out');

async function firstText(scope, candidates) {
  for (const sel of candidates) {
    const loc = scope.locator(sel).first();
    if (await loc.count().catch(() => 0)) {
      const t = (await loc.textContent().catch(() => null)) || '';
      const clean = t.replace(/\s+/g, ' ').trim();
      if (clean) return clean;
    }
  }
  return null;
}

async function dumpPage(page, label) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(OUT_DIR, `${label}.png`), fullPage: true }).catch(() => {});
  const html = await page.content().catch(() => '');
  fs.writeFileSync(path.join(OUT_DIR, `${label}.html`), html);
}

async function gotoSafe(page, url, label) {
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1500); // let client-rendered profile widgets settle
  } catch (e) {
    console.warn(`  ! could not load ${label} (${url}): ${e.message}`);
  }
  await dumpPage(page, label);
  // Heuristic: bounced back to a login form means the saved session expired.
  if (/log ?in|sign ?in|password/i.test(await page.title().catch(() => ''))) {
    console.warn(`  ! ${label} looks like a login page — session may have expired. Re-run save_session.js.`);
  }
}

(async () => {
  const name = (process.argv[2] || '').trim().toLowerCase();
  const show = process.argv.includes('--show');
  if (!name) {
    console.error('Usage: node scrape_alaska_account.js <name> [--show]');
    process.exit(1);
  }
  const statePath = path.join(__dirname, `storage-state-${name}.json`);
  if (!fs.existsSync(statePath)) {
    console.error(`No session for "${name}". Run:  node save_session.js ${name}`);
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: !show });
  const context = await browser.newContext({ storageState: statePath });
  const page = await context.newPage();

  const profile = {
    name: null, dob: null,
    mileage_plan: { number: null, tier: null },
    known_traveler_number: null, global_entry: null, redress_number: null,
    seat_preference: null, companion_fare: null,
    saved_travelers: [],
    saved_payment_methods: [], // brand + last4 only
    _meta: { source: 'alaskaair.com', scraped_at: new Date().toISOString(), needs_review: [] },
  };

  console.log('Visiting account pages (dumps -> out/) ...');
  await gotoSafe(page, PAGES.dashboard, 'dashboard');
  await gotoSafe(page, PAGES.profile, 'profile');

  profile.name              = await firstText(page, SELECTORS.fullName);
  profile.dob               = await firstText(page, SELECTORS.dob);
  profile.mileage_plan.number = await firstText(page, SELECTORS.mileagePlanNum);
  profile.mileage_plan.tier   = await firstText(page, SELECTORS.mileagePlanTier);
  profile.known_traveler_number = await firstText(page, SELECTORS.knownTraveler);
  profile.global_entry      = await firstText(page, SELECTORS.globalEntry);
  profile.redress_number    = await firstText(page, SELECTORS.redress);
  profile.seat_preference   = await firstText(page, SELECTORS.seatPreference);
  profile.companion_fare    = await firstText(page, SELECTORS.companionFare);

  await gotoSafe(page, PAGES.travelers, 'travelers');
  for (const rowSel of TRAVELER_ROW_SELECTORS) {
    const rows = page.locator(rowSel);
    const n = await rows.count().catch(() => 0);
    if (!n) continue;
    for (let i = 0; i < n; i++) {
      const nm = await firstText(rows.nth(i), TRAVELER_NAME_WITHIN);
      if (nm) profile.saved_travelers.push(nm);
    }
    break;
  }

  await gotoSafe(page, PAGES.payment, 'payment');
  for (const rowSel of PAYMENT_ROW_SELECTORS) {
    const rows = page.locator(rowSel);
    const n = await rows.count().catch(() => 0);
    if (!n) continue;
    for (let i = 0; i < n; i++) {
      const brand = await firstText(rows.nth(i), PAYMENT_BRAND_WITHIN);
      const last4raw = await firstText(rows.nth(i), PAYMENT_LAST4_WITHIN);
      const last4 = last4raw ? (last4raw.match(/\d{4}(?!.*\d)/) || [last4raw])[0] : null;
      if (brand || last4) profile.saved_payment_methods.push({ brand, last4 });
    }
    break;
  }

  // Flag everything that didn't resolve so the tuning pass is obvious.
  const flat = {
    name: profile.name, dob: profile.dob,
    'mileage_plan.number': profile.mileage_plan.number,
    'mileage_plan.tier': profile.mileage_plan.tier,
    known_traveler_number: profile.known_traveler_number,
    global_entry: profile.global_entry, redress_number: profile.redress_number,
    seat_preference: profile.seat_preference, companion_fare: profile.companion_fare,
  };
  profile._meta.needs_review = Object.entries(flat).filter(([, v]) => !v).map(([k]) => k);
  if (!profile.saved_travelers.length) profile._meta.needs_review.push('saved_travelers');
  if (!profile.saved_payment_methods.length) profile._meta.needs_review.push('saved_payment_methods');

  fs.mkdirSync(path.join(__dirname, 'travelers'), { recursive: true });
  const outPath = path.join(__dirname, 'travelers', `${name}.yaml`);
  fs.writeFileSync(outPath, yaml.dump(profile, { lineWidth: 100 }));

  console.log(`\nWrote ${outPath}`);
  if (profile._meta.needs_review.length) {
    console.log('Fields NOT found (tune selectors using out/*.html, then re-run):');
    for (const f of profile._meta.needs_review) console.log(`  - ${f}`);
  } else {
    console.log('All target fields resolved.');
  }
  console.log('\nReminder: passport + full card numbers are intentionally NOT here. Store those encrypted.');

  await browser.close();
})().catch((err) => {
  console.error('Scrape failed:', err);
  process.exit(1);
});
