#!/usr/bin/env node
/*
 * save_session.js — one-time interactive login for a single traveler.
 *
 * Opens a real (headed) browser, navigates to alaskaair.com, and waits while
 * YOU log in by hand: type the password, clear any CAPTCHA, complete 2FA.
 * Claude never sees or handles your credentials. When you've reached your
 * signed-in account dashboard, press Enter in the terminal and the session
 * cookies are saved to storage-state-<name>.json.
 *
 * Usage:
 *   node save_session.js <name>
 *   # e.g. node save_session.js alex
 *
 * Must run on a machine with a display (not a headless sandbox), because the
 * login is interactive by design.
 */
const { chromium } = require('playwright');
const readline = require('readline');

const SIGN_IN_URL = 'https://www.alaskaair.com/account/login';

function waitForEnter(prompt) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(prompt, () => { rl.close(); resolve(); }));
}

(async () => {
  const name = (process.argv[2] || '').trim().toLowerCase();
  if (!name) {
    console.error('Usage: node save_session.js <name>   (e.g. node save_session.js alex)');
    process.exit(1);
  }
  const statePath = `storage-state-${name}.json`;

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log(`\nOpening ${SIGN_IN_URL}`);
  console.log('Log in by hand in the browser window:');
  console.log('  - type your password yourself (Claude never sees it)');
  console.log('  - solve any CAPTCHA / complete 2FA');
  console.log('  - land on your signed-in account dashboard\n');

  await page.goto(SIGN_IN_URL, { waitUntil: 'domcontentloaded' }).catch(() => {});

  await waitForEnter('Press Enter here ONCE you are fully signed in... ');

  await context.storageState({ path: statePath });
  console.log(`\nSaved session -> ${statePath}`);
  console.log('This file holds live auth cookies. It is gitignored — keep it private.');
  console.log(`Next: node scrape_alaska_account.js ${name}\n`);

  await browser.close();
})().catch((err) => {
  console.error('Login helper failed:', err);
  process.exit(1);
});
