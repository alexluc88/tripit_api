#!/usr/bin/env bash
# Idempotent, cloud-only provisioning so the tripit skill is usable without any
# manual install (e.g. when driving a session from mobile). Safe to run on every
# session start: it exits fast once the venv and the tripitcli package are
# present, and never fails the session.
set -uo pipefail
cd "$(dirname "$0")"

# Only provision in cloud sessions. Local users run setup.sh themselves.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

ready() {
  [ -x .venv/bin/python ] || return 1
  .venv/bin/python - <<'PY' >/dev/null 2>&1
import tripitcli  # noqa: F401
import requests   # noqa: F401
PY
}

ready && exit 0

bash setup.sh || true
exit 0
