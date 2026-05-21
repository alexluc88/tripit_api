---
name: alaska-booking
description: >-
  Use this skill whenever the user wants to find, compare, or book flights on
  Alaska Airlines, mentions booking Alaska, references their Mileage Plan number,
  asks to fly out of Seattle/SEA, Portland/PDX, or Anchorage/ANC and Alaska is a
  natural fit, or asks Claude to handle their Alaska Airlines travel. Trigger on
  casual phrasings too — "get me to LA on Alaska next month", "find me an Alaska
  redeye home", "use my Companion Fare." Encodes the alaskaair.com booking
  workflow, the user's travel preferences, and the mandatory confirmation
  checkpoints, and orchestrates flight-search MCPs together with Claude for
  Chrome to do the actual booking.
---

# Alaska Airlines Booking

A skill for booking flights on Alaska Airlines through alaskaair.com via browser automation, with fare comparison through the Expedia MCP.

## Why this skill exists

Alaska Airlines does not expose a consumer booking API. The reliable path to "book me an Alaska flight" is to drive the alaskaair.com flow in a browser session where the user is already signed in. This skill encodes:

- the steps of that flow,
- the user's persistent travel preferences,
- the checkpoints where Claude must stop and confirm,
- how to use the Expedia MCP for a price sanity-check before committing.

## What this skill needs

- **Browser automation** — required for the actual booking. Two options:
  - **Playwright via Claude Code** (preferred for this user) — install `@playwright/mcp` or use Playwright CLI for ~4x token efficiency. Best for batch ops across multiple travelers, scripted bookings, and refreshing scraped account data. Persistent session state per account means one login per traveler, reusable across runs.
  - **Claude for Chrome extension** — alternative for one-off interactive bookings using your already-logged-in Chrome session. Better when you want to watch and approve each step in real time, worse for batch.
- **Expedia MCP** — used for fare comparison before booking. Tool: `search_flights`.
- A logged-in alaskaair.com session (either Chrome with you signed in, or Playwright with stored session state). Do not handle login credentials in chat.
- Local secure storage for scraped traveler data (Mileage Plan numbers, KTN/PreCheck, DOBs, seat prefs, saved travelers). Sensitive items like passport numbers and credit card numbers stay in a local encrypted file managed by Claude Code, NOT in conversation memory.

## Initial setup: scraping traveler accounts

For first-time setup with multiple travelers, use Claude Code + Playwright to capture profile data once instead of re-asking every booking.

1. Create a project directory with one `storage-state-<name>.json` per traveler (Playwright's saved session file).
1. For each traveler, run an interactive Playwright session: log in to alaskaair.com manually, then save the session state. One-time step per traveler.
1. Write a `scrape_alaska_account.js` script that takes a storage state file and extracts: full legal name, DOB, Mileage Plan number + tier, Known Traveler Number, Global Entry / Redress numbers, default seat preference, saved travelers list, Companion Fare status (if Alaska Visa), saved payment methods (last 4 only).
1. Output to a structured local file per traveler (e.g., `travelers/<name>.yaml`). Keep these files out of any cloud sync that isn't encrypted.
1. For sensitive items (passport numbers, full card numbers), use a separately-encrypted file or a password manager. NEVER put these in conversation memory.

Once the initial scrape is done, future bookings read from the local traveler files and only need trip-specific details from the user.

## Workflow

### 1. Gather trip details

Before touching the browser, collect everything in one pass. Ask only what isn't already known from the conversation or memory.

Required:

- Origin airport (IATA code preferred, city otherwise)
- Destination airport
- Departure date — and return date if roundtrip
- Number of passengers (adults, children, infants)
- Cabin: Main, Premium Class, or First Class

Helpful if available:

- Preferred time of day (morning / midday / evening / redeye)
- Nonstop only vs. connections OK
- Mileage Plan number (verify it's attached at checkout)
- Seat preference (aisle/window, forward cabin, exit row)
- Bag count
- Avoid Saver fare? (Saver doesn't allow changes and boards last)
- Companion Fare available? (annual Alaska Visa benefit)
- Paying with cash or miles?

Summarize the trip back in one short sentence and ask for confirmation before proceeding. Don't make the user type the same thing twice.

### 2. Optional: comparison shopping with Expedia

To confirm Alaska is competitive on price, call the Expedia MCP's `search_flights` tool with the same origin, destination, dates, and passenger count. Filter or scan the results for Alaska Airlines specifically, and surface:

- Alaska's best matching fare on Expedia
- The next cheapest carrier and its price delta
- Any nonstop options the user might prefer

Show the top 2–3 results in a short comparison. If the user switches carriers, hand off — this skill is Alaska-specific. Skip this step entirely if the user said "just book Alaska" or already knows what they want.

Note: Expedia is a search/compare tool here, not a booking tool — the actual booking still happens on alaskaair.com in step 3, because that's where Mileage Plan miles, Companion Fare, and Alaska Visa benefits apply correctly.

### 3. Drive the alaskaair.com booking flow

1. **Search.** On the homepage booking widget (Flights tab), fill From, To, Depart, Return, passenger count, and cabin. For award travel, toggle "Use miles" BEFORE searching. For multi-city, switch to the Multi-city tab — the UI is different.
1. **Departing flight.** On the results page, pick the flight that matches the stated preferences. Avoid Saver fare unless the user OK'd it. Read out the choice and price before clicking.
1. **Returning flight.** Same logic for the return leg.
1. **Review price.** Confirm the total matches what the user expected. If it's far off from the MCP comparison, stop and flag it.
1. **Passenger info.** If signed in, info prefills. Verify name matches government ID, DOB is correct, Mileage Plan number is attached. Do NOT modify silently — pause and ask if a field looks wrong.
1. **Seats.** Apply preferences if known; otherwise leave default and tell the user they can pick at checkout.
1. **Bags.** Add only if the user explicitly mentioned them. Alaska charges per bag per direction.
1. **STOP at the payment page.** Read the final itinerary and total back to the user. Do not enter payment, do not click Purchase. Hand control back: "Ready to pay — I'll let you confirm and submit."

### 4. After the user pays

Once they confirm payment is done, capture the confirmation code if visible and offer to:

- Add the trip to their calendar
- Save the confirmation code to a reminder
- Set a check-in reminder for 24 hours before departure

## Mandatory checkpoints — never skip

- **Before "Find Flights":** confirm route and dates back to the user.
- **Before selecting each leg:** state which flight and why.
- **Before the payment page:** show full itinerary and total.
- **At the payment page:** STOP. User submits payment themselves.

These exist because most Alaska fares are non-refundable and a wrong-airport mistake costs hundreds to fix. The friction is the feature.

## Things to watch for

- **Saver fares:** no seat selection, no changes, board last, middle seats common. Only book if user accepted this.
- **Mileage earnings on Saver:** fewer miles than Main. Mention if user is points-motivated.
- **Upgrade offers:** Alaska often shows a paid First/Premium upgrade after flight selection. Don't accept without asking.
- **Travel insurance prompt:** decline by default unless the user opted in.
- **CAPTCHA / 2FA:** pause and let the user solve it. Never attempt to bypass.
- **Companion Fare:** appears as a discount line item at checkout. Verify it applied before stopping at payment.
- **Award travel:** award availability is separate from cash inventory. Toggle "Use miles" on the search widget before searching.

## Anti-patterns

- Do not invent flight numbers, prices, or times. If you can't read the page, say so and ask the user.
- Do not click through dialogs the user hasn't seen — read them out first.
- Do not store payment info anywhere.
- Do not retry a failed step more than twice without checking in.
- Do not assume "book it" means "and pay." Booking ends at the payment page.

## Examples

**Example 1 — simple round trip:**
User: "Book me on Alaska from SEA to LAX next Friday, returning Sunday evening."

- Confirm: "SEA → LAX Fri departing, Sun evening returning, 1 pax Main — right?"
- (Optional) Run a flight-search MCP to sanity-check Alaska's price.
- Open alaskaair.com, search, pick best matching flights, pause at payment.

**Example 2 — points-aware:**
User: "Find me an Alaska redeye home from JFK Thursday. I have a Companion Fare to use."

- Confirm route, date, Companion Fare applies, get second passenger name.
- Search, filter for evening/overnight departures, verify Companion Fare discount line at checkout.
- Stop at payment.

**Example 3 — comparison first:**
User: "I need to get to Boise next weekend, what's cheapest?"

- Not Alaska-specific — start with a flight-search MCP across carriers.
- If Alaska wins or is close, offer it and trigger this skill on confirmation.
- If another carrier wins by a lot, hand off. Don't push Alaska just because this skill is loaded.
