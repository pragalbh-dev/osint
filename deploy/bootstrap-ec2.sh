#!/usr/bin/env bash
# Chanakya OSINT — EC2 bring-up (Session X0 shape; unchanged by SHIP — it only installs Docker).
# Installs Docker Engine + the compose plugin on a fresh Ubuntu or Amazon Linux
# 2023 box. Safe to run as EC2 user-data at launch, or by hand over SSH.
# Idempotent: re-running is a no-op if Docker is already present.
set -euo pipefail

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "[bootstrap] Docker + compose already installed:"
  docker --version && docker compose version
  exit 0
fi

echo "[bootstrap] installing Docker via get.docker.com (works on Ubuntu + AL2023)…"
curl -fsSL https://get.docker.com | sh

# Let the login user run docker without sudo (ubuntu / ec2-user, whoever invoked).
TARGET_USER="${SUDO_USER:-${USER:-}}"
if [ -n "${TARGET_USER}" ] && [ "${TARGET_USER}" != "root" ]; then
  sudo usermod -aG docker "${TARGET_USER}" || true
  echo "[bootstrap] added ${TARGET_USER} to the docker group (re-login to take effect)."
fi

sudo systemctl enable --now docker

echo "[bootstrap] done:"
docker --version
docker compose version

cat <<'NEXT'

Next:
  1) Put docker-compose.yml (+ a gitignored .env with ANTHROPIC_API_KEY and
     TUNNEL_TOKEN) on this box, OR: git clone https://github.com/pragalbh-dev/osint
  2) docker compose pull app          # or: docker compose build app
  3) docker compose --profile tunnel up -d
  4) docker compose ps && docker compose logs -f cloudflared
See deploy/README.md §D–E.
NEXT
