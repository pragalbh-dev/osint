# `deploy/` — Chanakya OSINT walking-skeleton runbook (Session X0)

Stand up the **hosted deploy pipeline end to end with a trivial payload** so that
from here on "deploy" is a fixed, proven, byte-identical pull/swap — never a
first-time integration (master plan §7; `md/07` "Clean-deploy strategy", Stage 0).

```
 local docker build ─► GHCR (public) ─► docker compose on EC2 ─► Cloudflare Tunnel ─► https://…
        (A)                 (B)                  (C)                    (D)              (E verify)
```

Nothing here needs a domain, DNS, or an open inbound port: the tunnel **dials
out**, so the EC2 security group's only inbound rule is SSH (or SSM).

Substitute your own values for `<...>`. Owner org: **`pragalbh-dev`**, image
**`ghcr.io/pragalbh-dev/osint:skeleton`** (SHIP later owns `:latest`).

> **Fastest live URL (ephemeral, zero Cloudflare account):** on any box with
> Docker, `./deploy/prove-live.sh` pulls the public image, runs it isolated (own
> network, no host port), and brings up a throwaway `trycloudflare` https URL in
> one command. Use the token-based tunnel (§D) for the *persistent* demo URL.

---

## A. Build + run locally (prove the image)

From the repo root:

```bash
docker compose up --build app          # builds the multi-stage image, serves on 127.0.0.1:8000
./deploy/verify.sh                     # curls /health and / (expects 200 + "it boots")
# or manually:
curl -fsS http://127.0.0.1:8000/health         # -> {"status":"ok"}
curl -fsS http://127.0.0.1:8000/ | head        # -> the placeholder SPA HTML
docker compose down
```

`docker run` locally is byte-identical to what the EC2 box runs, so this is a
real proof of the runtime, not a stand-in.

---

## B. Push the image to GHCR (public)

GHCR push needs a token with the **`write:packages`** scope. The repo's `gh`
login currently lacks it — grant it once:

```bash
gh auth refresh -h github.com -s write:packages          # opens a browser once
# authenticate docker to GHCR using the gh token:
gh auth token | docker login ghcr.io -u pragalbh-dev --password-stdin
```

Build, tag, push:

```bash
docker build -f Dockerfile -t ghcr.io/pragalbh-dev/osint:skeleton app_skeleton
docker push ghcr.io/pragalbh-dev/osint:skeleton
```

Then make the package **public** (one time): GitHub → your profile → Packages →
`osint` → Package settings → Change visibility → **Public**. Verify anyone can
pull:

```bash
docker logout ghcr.io
docker run --rm -p 8000:8000 ghcr.io/pragalbh-dev/osint:skeleton   # then curl /health
```

---

## C. EC2 bring-up (one always-on box)

Launch one small always-on instance (t3.small is plenty for the skeleton),
Ubuntu 22.04/24.04 or Amazon Linux 2023. **Security group: inbound = SSH only**
(better: no inbound, use SSM Session Manager). No HTTP/HTTPS ports — the tunnel
dials out.

SSH in and install Docker + the compose plugin:

```bash
# copy deploy/bootstrap-ec2.sh to the box, or paste it as EC2 user-data at launch
curl -fsSL https://raw.githubusercontent.com/pragalbh-dev/osint/main/deploy/bootstrap-ec2.sh | bash
# (or scp deploy/bootstrap-ec2.sh ubuntu@<ip>: && bash bootstrap-ec2.sh)
```

Put the app on the box. Two options:

- **Pull the GHCR image (fast):** copy just `docker-compose.yml` + a `.env`, then
  `docker compose pull app`.
- **Build on the box (transparent):** `git clone https://github.com/pragalbh-dev/osint && cd osint`.

Create `.env` on the box (never committed) — see §Secrets below.

---

## D. Cloudflare Tunnel (real https, no domain)

Token-based ("remote-managed") tunnel — no `cert.pem`, no `config.yml` on the box:

1. Cloudflare **Zero Trust dashboard** → Networks → **Tunnels** → *Create a
   tunnel* → **Cloudflared** → name it (e.g. `chanakya-osint`).
2. Add a **public hostname**: it gives you a free `*.trycloudflare`-style or a
   `<name>.cfargotunnel.com` URL (or map a Cloudflare-managed hostname if you
   have one). Service = `http://app:8000` (the compose service name) — the
   `cloudflared` container reaches `app` on the compose network.
3. Copy the **tunnel token** and add it to the box's `.env`:
   ```
   TUNNEL_TOKEN=<the-long-token-string>
   ```
4. Start both services:
   ```bash
   docker compose --profile tunnel up -d
   docker compose ps           # app healthy + cloudflared running
   docker compose logs -f cloudflared   # confirms "Registered tunnel connection"
   ```

> Quick-and-dirty alternative (ephemeral, no account/token): run
> `cloudflared tunnel --url http://localhost:8000` on the box — it prints a
> throwaway `https://<random>.trycloudflare.com` URL. Fine for a smoke test;
> use the token-based tunnel above for the always-on demo URL.

---

## E. Verify it live

```bash
./deploy/verify.sh https://<your-tunnel-url>
# checks: /health -> 200 {"status":"ok"}  and  / -> the "it boots" page
```

Acceptance = the same "it boots" page + `200 /health` from **all three**: local
image, the public GHCR pull, and the tunnel URL.

---

## Fallback ladder (if the tunnel snags) — `md/07` "Hosting architecture"

Caddy reverse-proxy + auto-TLS (needs a domain) → bare HTTP on the EC2 public IP
for the call → an SSH tunnel (`ssh -L 8000:localhost:8000 <box>`). **The image is
unchanged in every case** — only the front door moves.

---

## Secrets

- `.env` is **gitignored** (repo `.gitignore` commits `.env`); it is never baked
  into the image and never logged. Compose injects it via `env_file`.
- Keys: `ANTHROPIC_API_KEY` (+ optional `GEMINI_API_KEY`) for the app;
  `TUNNEL_TOKEN` for `cloudflared`. The skeleton doesn't *use* the API key yet —
  X0 proves the **injection path**; the real app (SHIP) consumes it.
- `APP_PORT` (optional) — host-side debug port; set it (e.g. `APP_PORT=8010`) when
  **co-locating** on a box where `8000` is already taken. The tunnel is unaffected
  (it reaches `app:8000` over the compose network, not the host port).
- Prod endgame (design note): swap the key for an **EC2 instance-role** granted
  `bedrock:InvokeModel` — no stored secret.

---

## What SHIP changes (out of scope for X0)

Repoints the build context to the repo root; bakes `config/` + corpus + the
seeded SQLite baseline + the real `backend/` + `frontend/` SPA; adds the real
`make {extract,build,ingest,ask,run}` targets; owns the `:latest` tag; adds the
rollback drill (pin the previous GHCR tag).
