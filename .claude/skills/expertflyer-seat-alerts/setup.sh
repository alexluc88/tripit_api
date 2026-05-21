#!/usr/bin/env bash
# One-time setup for the expertflyer-seat-alerts skill.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e .
playwright install chromium

echo
echo "efalert ready."
echo "  1) export EF_EMAIL=... EF_PASSWORD=...   (or create a .env file)"
echo "  2) . .venv/bin/activate"
echo "  3) python -m efalert login"
