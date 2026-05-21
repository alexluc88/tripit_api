#!/usr/bin/env bash
# One-time setup for the tripit skill.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e .

echo
echo "tripit ready."
echo "  1) export TRIPIT_API_KEY=... TRIPIT_API_SECRET=...   (or create a .env file)"
echo "  2) . .venv/bin/activate"
echo "  3) python -m tripitcli login          # prints an authorize URL"
echo "  4) # open the URL, click Authorize, then:"
echo "  5) python -m tripitcli login --complete"
