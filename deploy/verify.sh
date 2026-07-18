#!/usr/bin/env bash
# Chanakya OSINT — walking-skeleton acceptance check (Session X0).
# Verifies /health -> 200 {"status":"ok"} and / -> the "it boots" page.
#
#   ./deploy/verify.sh                       # local: http://127.0.0.1:8000
#   ./deploy/verify.sh https://<tunnel-url>  # remote: the live tunnel URL
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
BASE="${BASE%/}"
fail=0

echo "[verify] target: ${BASE}"

# 1) /health must be 200 with {"status":"ok"}
health="$(curl -fsS "${BASE}/health" || true)"
if echo "${health}" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  echo "[verify] PASS  /health -> ${health}"
else
  echo "[verify] FAIL  /health -> '${health}' (expected {\"status\":\"ok\"})"
  fail=1
fi

# 2) / must return HTML (the placeholder SPA)
root="$(curl -fsS "${BASE}/" || true)"
if echo "${root}" | grep -qi '<!doctype html'; then
  echo "[verify] PASS  / -> HTML page served ($(echo "${root}" | wc -c) bytes)"
else
  echo "[verify] FAIL  / -> did not return an HTML page"
  fail=1
fi

if [ "${fail}" -eq 0 ]; then
  echo "[verify] ✅ all checks passed for ${BASE}"
else
  echo "[verify] ❌ checks failed for ${BASE}"
fi
exit "${fail}"
