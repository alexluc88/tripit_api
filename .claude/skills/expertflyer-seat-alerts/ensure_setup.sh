#!/usr/bin/env bash
# Idempotent, cloud-only provisioning so the expertflyer-seat-alerts skill is
# usable without any manual install (e.g. when driving a session from mobile).
# Safe to run on every session start: it exits fast once the venv, the efalert
# package, and a Chromium build are present, and never fails the session.
set -uo pipefail
cd "$(dirname "$0")"

# Only provision in cloud sessions. Local users run setup.sh themselves so we
# never install a heavyweight browser toolchain on their machine unprompted.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

# Ready = venv exists, efalert importable, and Playwright's Chromium is on disk
# (its path varies, e.g. PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers in cloud).
ready() {
  [ -x .venv/bin/python ] || return 1
  .venv/bin/python - <<'PY' >/dev/null 2>&1
import os, sys
import efalert  # noqa: F401
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    sys.exit(0 if os.path.exists(p.chromium.executable_path) else 1)
PY
}

ready && exit 0

bash setup.sh || true
exit 0
