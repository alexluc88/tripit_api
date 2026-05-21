"""asaccount: read-only Alaska / Atmos Rewards account scraping (browser-driven).

Pulls Mileage Plan / Atmos Rewards miles, elite status, Wallet balance/credits,
and recent account activity from alaskaair.com. Uses Patchright (an undetected
Playwright fork) because alaskaair.com sits behind an Akamai-style bot challenge
that blocks vanilla Playwright.
"""

__version__ = "0.1.0"
