#!/usr/bin/env bash
# Chanakya OSINT X0 — one-command LIVE proof on any single box, via an EPHEMERAL
# Cloudflare tunnel (throwaway https://<random>.trycloudflare.com, real TLS, no
# Cloudflare account/token). This is the fastest way to a public https URL; the
# PERSISTENT demo URL uses the token-based named tunnel in docker-compose.yml.
#
# Fully isolated: its own docker network + named containers and NO host port
# publish, so it cannot collide with anything else already on the box. Idempotent.
# Needs Docker present — run deploy/bootstrap-ec2.sh first if it isn't.
#
#   Run on the box:  ./deploy/prove-live.sh
#   Or over SSH:     ssh <box> 'bash -s' < deploy/prove-live.sh
set -euo pipefail

IMAGE="${IMAGE:-ghcr.io/pragalbh-dev/osint:skeleton}"
NET="chanakya-x0"; APP="chanakya-x0-app"; TUN="chanakya-x0-tunnel"

# --- resolve how to call docker (direct, or via passwordless sudo) ---
command -v docker >/dev/null 2>&1 || {
  echo "ERROR: docker not installed on this box. Run deploy/bootstrap-ec2.sh first."; exit 1; }
if docker info >/dev/null 2>&1; then DOCKER="docker"
elif sudo -n docker info >/dev/null 2>&1; then DOCKER="sudo -n docker"
else echo "ERROR: cannot use docker as $(whoami) — not in the docker group and no passwordless sudo."; exit 1; fi
echo "[docker] $($DOCKER --version)  (via: $DOCKER)"

echo "[1/5] pulling the public image ($IMAGE)…"
$DOCKER pull "$IMAGE"

echo "[2/5] (re)creating isolated network + containers (no host port -> no collisions)…"
$DOCKER rm -f "$APP" "$TUN" >/dev/null 2>&1 || true
$DOCKER network create "$NET" >/dev/null 2>&1 || true
$DOCKER run -d --name "$APP" --network "$NET" --restart unless-stopped "$IMAGE" >/dev/null
$DOCKER run -d --name "$TUN" --network "$NET" --restart unless-stopped \
  cloudflare/cloudflared:latest tunnel --no-autoupdate --url "http://$APP:8000" >/dev/null

echo "[3/5] waiting for the app to be healthy…"
st=none
for _ in $(seq 1 25); do
  st=$($DOCKER inspect -f '{{.State.Health.Status}}' "$APP" 2>/dev/null || echo none)
  [ "$st" = "healthy" ] && break; sleep 1
done
echo "    app health = $st"

echo "[4/5] waiting for the tunnel URL…"
URL=""
for _ in $(seq 1 40); do
  URL=$($DOCKER logs "$TUN" 2>&1 | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1 || true)
  [ -n "$URL" ] && break; sleep 1
done
[ -n "$URL" ] || { echo "ERROR: no tunnel URL in cloudflared logs:"; $DOCKER logs "$TUN" 2>&1 | tail -20; exit 1; }
echo "    tunnel URL = $URL"

echo "[5/5] verifying over the public https URL (edge propagation can take ~30s)…"
code=000
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$URL/health" 2>/dev/null || echo 000)
  [ "$code" = "200" ] && break; sleep 2
done
health=$(curl -s --max-time 10 "$URL/health" 2>/dev/null || echo "<pending>")
spa=$(curl -s --max-time 10 "$URL/" 2>/dev/null | grep -qi '<!doctype html' && echo 'HTML served (it boots)' || echo 'pending')

echo
echo "==================== X0 LIVE PROOF ===================="
echo "  public URL : $URL"
if [ "$code" = "200" ]; then
  echo "  /health    : HTTP 200  body=$health"
  echo "  SPA (/)    : $spa"
  echo "  STATUS     : LIVE ✅"
else
  echo "  /health    : HTTP $code (local check hasn't propagated yet)"
  echo "  STATUS     : tunnel registered — verify from another host:"
  echo "               curl $URL/health"
fi
echo "======================================================="
echo "  teardown:  $DOCKER rm -f $APP $TUN && $DOCKER network rm $NET"
