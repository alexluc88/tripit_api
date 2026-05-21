#!/usr/bin/env bash
# One-time setup for the alaska-account skill.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e .
# Patchright ships its own browser fetch; chromium is the safe default.
patchright install chromium

echo
echo "asaccount ready."
echo "  1) export AS_USERNAME=... AS_PASSWORD=...   (or create a .env file)"
echo "  2) . .venv/bin/activate"
echo "  3) python -m asaccount login        # headed first run recommended"
