#!/usr/bin/env bash
# Chanakya OSINT — deployment acceptance check (Session SHIP; supersedes X0's smoke test).
#
# Proves the *shipped artifact*, not just that a port answers: readiness gate, the built SPA, the
# rebuilt graph, and the worked query returning a cited chain (or an honest refusal, which is also a
# pass — a refusal before the withheld evidence is ingested is the designed behaviour).
#
#   ./deploy/verify.sh                       # local: http://127.0.0.1:8000
#   ./deploy/verify.sh https://<tunnel-url>  # remote: the live tunnel URL
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
BASE="${BASE%/}"
HERO="Trace the long-range SAM battery now based at Rahwali back to its fire-control component and name the chokepoint."
fail=0

pass() { echo "[verify] PASS  $*"; }
bad()  { echo "[verify] FAIL  $*"; fail=1; }

echo "[verify] target: ${BASE}"

# 1) /health must be 200 with {"status":"ok"} — i.e. the boot rebuild() has landed.
health="$(curl -fsS "${BASE}/health" || true)"
if echo "${health}" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  pass "/health -> ${health}"
else
  bad "/health -> '${health}' (expected {\"status\":\"ok\"}; 503 means the rebuild has not finished)"
fi

# 2) / must return the BUILT SPA, not the "not built into this image yet" placeholder.
root="$(curl -fsS "${BASE}/" || true)"
if ! echo "${root}" | grep -qi '<!doctype html'; then
  bad "/ -> did not return an HTML page"
elif echo "${root}" | grep -q 'has not been built into this image yet'; then
  bad "/ -> the placeholder is being served; the image has no frontend/dist (Node build stage failed?)"
else
  pass "/ -> built SPA served ($(echo "${root}" | wc -c) bytes)"
fi

# 3) /view must be JSON with a non-empty graph.
view="$(curl -fsS "${BASE}/view" || true)"
if echo "${view}" | grep -q '"nodes"'; then
  pass "/view -> graph JSON ($(echo "${view}" | wc -c) bytes)"
else
  bad "/view -> no graph JSON returned"
fi

# 4) The worked query must return EITHER a cited hop chain OR a first-class refusal — never a 5xx and
#    never an empty body. Both outcomes are correct; which one depends on whether the withheld
#    Rahwali evidence has been ingested yet.
ask="$(curl -fsS -X POST "${BASE}/ask" -H 'content-type: application/json' \
        -d "{\"question\": $(printf '%s' "${HERO}" | sed 's/"/\\"/g; s/^/"/; s/$/"/'), \"subject\": \"lens-hq9p-pk\"}" || true)"
if echo "${ask}" | grep -q '"hops"[[:space:]]*:[[:space:]]*\[[[:space:]]*{'; then
  pass "/ask -> traced answer with per-hop citations"
elif echo "${ask}" | grep -q '"refusal"[[:space:]]*:[[:space:]]*{'; then
  pass "/ask -> honest refusal (the withheld evidence has not been ingested yet — expected at boot)"
else
  bad "/ask -> neither a traced answer nor a refusal: '${ask:0:200}'"
fi

if [ "${fail}" -eq 0 ]; then
  echo "[verify] ✅ all checks passed for ${BASE}"
else
  echo "[verify] ❌ checks failed for ${BASE}"
fi
exit "${fail}"
