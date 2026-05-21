"""All DOM selectors in one place, so tuning against the live site is a one-file job.

NONE of these are VERIFIED: alaskaair.com's account pages sit behind login AND an
Akamai-style bot challenge, so the real markup could not be inspected. They are
best-effort guesses. Run `asaccount dump-dom <url>` while logged in (headed) to
capture the real HTML/elements, then correct the values below. The scrapers in
account.py also fall back to scanning page text, so balances may resolve even
when a selector is stale.
"""

# --- Login form (NEEDS-VERIFICATION) ----------------------------------------
LOGIN = {
    "username": (
        'input[name="username"], input#username, input[name="loginField"], '
        'input[type="email"]'
    ),
    "password": 'input[name="password"], input#password, input[type="password"]',
    "submit": (
        'button[type="submit"], button:has-text("Sign in"), '
        'button:has-text("Log in")'
    ),
}

# Alaska emails a one-time code on new devices. The input is sometimes a single
# field, sometimes per-digit boxes (handled in auth.py).
TWO_FA = {
    "prompt": 'text=/verification code|security code|one-time|enter the code/i',
    "code_single": (
        'input[name="code"], input#code, input[autocomplete="one-time-code"], '
        'input[name*="otp" i]'
    ),
    "code_digits": 'input[inputmode="numeric"], input[maxlength="1"]',
    "submit": (
        'button[type="submit"], button:has-text("Verify"), '
        'button:has-text("Continue"), button:has-text("Submit")'
    ),
}

# Akamai / WAF "Client Challenge" interstitial. If we land here, patchright should
# clear it; we just detect it to warn.
CHALLENGE_MARKERS = [
    "text=/client challenge/i",
    "text=/verifying you are human/i",
    "#challenge-running",
]

# Heuristic markers that mean "we are logged in" once on the account portal.
AUTHED_MARKERS = [
    'a[href*="logout" i]',
    'text=/sign ?out|log ?out/i',
    'text=/mileage plan|atmos rewards/i',
]

# --- Account overview: miles + elite status (NEEDS-VERIFICATION) ------------
BALANCE = {
    "miles": (
        '[data-testid*="miles" i], [class*="miles" i], [class*="balance" i], '
        '[aria-label*="miles" i]'
    ),
    "status": (
        '[data-testid*="status" i], [data-testid*="tier" i], [class*="tier" i], '
        '[class*="elite" i], [class*="status" i]'
    ),
}

# --- Wallet: cash-like balance + list of credits/certificates ---------------
WALLET = {
    "balance": (
        '[data-testid*="wallet" i] [class*="balance" i], [class*="wallet" i] '
        '[class*="balance" i], [class*="walletBalance" i]'
    ),
    "items": (
        '[data-testid*="wallet" i] li, [class*="wallet" i] [class*="item" i], '
        '[class*="credit" i][class*="card" i]'
    ),
}

# --- Account activity / transaction history ---------------------------------
ACTIVITY = {
    "rows": (
        'table tbody tr, [data-testid*="activity" i] [role="row"], '
        '[class*="activity" i] [class*="row" i], [class*="transaction" i]'
    ),
}
