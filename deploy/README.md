# `deploy/` — Chanakya OSINT deploy runbook (Session SHIP)

One image holds the whole demo. `docker run` on a laptop is the same artifact the
EC2 box serves, so "deploy" is a fixed, proven pull/swap — never a first-time
integration (master plan §7; `md/07` "Clean-deploy strategy").

```
 local docker build ─► GHCR (public) ─► docker compose on EC2 ─► Cloudflare Tunnel ─► https://…
        (A)                 (B)                  (C)                    (D)              (E verify)
```

Nothing here needs a domain, DNS, or an open inbound port: the tunnel **dials
out**, so the EC2 security group's only inbound rule is SSH (or SSM).

Substitute your own values for `<...>`. Owner org: **`pragalbh-dev`**, image
**`ghcr.io/pragalbh-dev/osint:latest`**.

---

## The two reviewer paths (both give the identical artifact)

**1 · From a clone — one command:**

```bash
git clone https://github.com/pragalbh-dev/osint && cd osint
make run                      # builds the image, serves it, waits for /health
# → open http://127.0.0.1:8000
make stop                     # when you're done
```

`PORT=8010 make run` if 8000 is taken on your box.

**2 · From the published image — no clone, no build:**

```bash
docker run -d --name chanakya -p 127.0.0.1:8000:8000 ghcr.io/pragalbh-dev/osint:latest
curl -fsS http://127.0.0.1:8000/health
```

`make run` tags exactly `ghcr.io/pragalbh-dev/osint:latest`, so path 1 and path 2
are the same image by construction — not two things kept in sync by hand.

### What "it works" looks like

```bash
curl -sS http://127.0.0.1:8000/health
# {"status":"ok","rebuilt":true,"node_count":171,"edge_count":105,"config_version":1}

curl -sS http://127.0.0.1:8000/ | head -5     # the built SPA's index.html
curl -sS http://127.0.0.1:8000/view | head -c 200   # the rebuilt knowledge view as JSON
```

`/health` is **503 until the boot `rebuild()` lands**, then 200 — that transition
is the readiness gate the container healthcheck and the tunnel both poll.

### The worked query, end to end

The boot graph deliberately **does not hold** the two 2025 Rahwali overhead-pass
documents (`config/sources.yaml` → `withheld_from_seed`). That is the demo: the
analyst asks, gets an honest *insufficient evidence* answer, ingests the new
collection, and watches the tripwire fire and the answer become traceable.

```bash
# 1 — ask before the evidence exists: a first-class refusal, not a guess
make ask Q="Trace the long-range SAM battery now based at Rahwali back to its fire-control component and name the chokepoint."

# 2 — the new collection arrives (keyless: a frozen claim bundle, byte-for-byte
#     what live extraction over that document produces)
for d in d18_rahwali_pass1 d18_rahwali_pass1__basing d19_rahwali_confirm d19_rahwali_confirm__basing; do
  make ingest DOC=corpus/scenarios/hq9p_primary/claims/$d.json
done            # → "ALERTS FIRED: 1 → obs-basing-relocation"

# 3 — ask again: the 3-hop chain, every hop cited
make ask Q="Trace the long-range SAM battery now based at Rahwali back to its fire-control component and name the chokepoint."
```

`make ask` / `make ingest` talk to the **running app** over HTTP and need only
`python3` (stdlib) — no virtualenv, no installed backend. Add `PORT=…` if you
moved the port.

To boot with the full corpus already loaded (no live-ingest beat), set
`CHANAKYA_SEED_WITHHOLD=` (empty) — `/health` then reports 180 nodes / 114 edges.

---

## A. Build + run locally (prove the image)

From the repo root:

```bash
make run                               # == docker build . + docker run, then waits for /health
# or, via compose:
docker compose up --build app          # serves on 127.0.0.1:8000
./deploy/verify.sh                     # curls /health and /
docker compose down
```

`docker run` locally is byte-identical to what the EC2 box runs, so this is a
real proof of the runtime, not a stand-in.

---

## B. Push the image to GHCR (public)

GHCR push needs a token with the **`write:packages`** scope. Grant it once:

```bash
gh auth refresh -h github.com -s write:packages          # opens a browser once
# authenticate docker to GHCR using the gh token:
gh auth token | docker login ghcr.io -u pragalbh-dev --password-stdin
```

Build, tag, push:

```bash
make image                                               # tags ghcr.io/pragalbh-dev/osint:latest
docker tag ghcr.io/pragalbh-dev/osint:latest ghcr.io/pragalbh-dev/osint:$(date +%Y%m%d-%H%M)
make push                                                # pushes :latest
docker push ghcr.io/pragalbh-dev/osint:$(date +%Y%m%d-%H%M)   # the rollback anchor
```

Always push a **dated tag alongside `:latest`** — that dated tag *is* the rollback
target (see below). Then make the package **public** (one time): GitHub → your
profile → Packages → `osint` → Package settings → Change visibility → **Public**.
Verify anyone can pull:

```bash
docker logout ghcr.io
docker run --rm -p 8000:8000 ghcr.io/pragalbh-dev/osint:latest   # then curl /health
```

---

## C. EC2 bring-up (one always-on box)

Launch one small always-on instance (t3.small suffices; the image needs ~1 GB of
disk and a few hundred MB of RAM), Ubuntu 22.04/24.04 or Amazon Linux 2023.
**Security group: inbound = SSH only** (better: no inbound, use SSM Session
Manager). No HTTP/HTTPS ports — the tunnel dials out.

SSH in and install Docker + the compose plugin:

```bash
# copy deploy/bootstrap-ec2.sh to the box, or paste it as EC2 user-data at launch
curl -fsSL https://raw.githubusercontent.com/pragalbh-dev/osint/main/deploy/bootstrap-ec2.sh | bash
# (or scp deploy/bootstrap-ec2.sh ubuntu@<ip>: && bash bootstrap-ec2.sh)
```

Put the app on the box. Two options:

- **Pull the GHCR image (fast):** copy just `docker-compose.yml` + a `.env`, then
  `docker compose pull app`.
- **Build on the box (transparent):** `git clone https://github.com/pragalbh-dev/osint && cd osint && make run`.

`.env` is optional — the app boots fully keyless. See §Secrets.

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

`cloudflared` waits on the app's healthcheck (`condition: service_healthy`), so
the tunnel never routes to a half-initialised app.

> Quick-and-dirty alternative (ephemeral, no account/token): run
> `cloudflared tunnel --url http://localhost:8000` on the box — it prints a
> throwaway `https://<random>.trycloudflare.com` URL. Fine for a smoke test;
> use the token-based tunnel above for the always-on demo URL.

---

## E. Verify it live

```bash
./deploy/verify.sh https://<your-tunnel-url>
```

Acceptance = `200 /health`, the SPA at `/`, and the worked query above returning
its 3-hop cited chain from **all three**: the local image, the public GHCR pull,
and the tunnel URL.

---

## Rollback

Rollback is a **tag pin**, not a rebuild:

```bash
IMAGE_TAG=<previous-dated-tag> docker compose up -d app    # on the box
docker compose ps                                          # healthy again
```

Nothing else about the deployment changes — same compose file, same tunnel, same
`.env`. This is why §B always pushes a dated tag next to `:latest`.

---

## Fallback ladder (if the tunnel snags) — `md/07` "Hosting architecture"

Caddy reverse-proxy + auto-TLS (needs a domain) → bare HTTP on the EC2 public IP
for the call → an SSH tunnel (`ssh -L 8000:localhost:8000 <box>`). **The image is
unchanged in every case** — only the front door moves.

---

## Secrets, and what happens without them

The image boots **fully keyless, offline, with no volume**. Everything it needs is
baked in: `config/*.yaml`, the frozen `corpus/**`, the pre-extracted claim bundles
that seed the evidence log, and the built SPA including its vendored map tiles.
Nothing is fetched at runtime.

| Not provided | What degrades |
|---|---|
| `ANTHROPIC_API_KEY` | The scripted worked query still runs (it is a deterministic tool plan, no LLM). Free-form questions outside it return an honest **capability refusal** naming the missing key — never a fabricated answer. |
| `GEMINI_API_KEY` | Nothing at runtime. It is only used to *re-record* claim bundles (`make extract`). |
| `CHANAKYA_ENABLE_EXTRACTION=1` | Off by default. Live extraction of a **raw** document is refused with a pointer to the keyless bundle lane, so public visitors cannot burn model quota. Ingesting frozen bundles always works. |
| `TUNNEL_TOKEN` | No public https URL; the app still serves on `127.0.0.1:8000`. |
| `.env` at all | Nothing — `env_file` is marked `required: false` and `make run` omits `--env-file` when there is no `.env`. |

Other notes:

- `.env` is **gitignored**; it is never baked into the image and never logged.
- `APP_PORT` (compose) / `PORT` (make) — host-side debug port; set it when
  co-locating on a box where `8000` is taken. The tunnel is unaffected (it reaches
  `app:8000` over the compose network, not the host port).
- **Runtime writes are container-local by design** (`md/07` "Runtime writes"):
  ingests, HITL overrides and config edits live in the in-process append-only logs
  and reset to the clean baseline on restart. No managed DB, no volume, no VPC —
  and `docker restart chanakya` is a guaranteed clean demo reset.
- Prod endgame (design note): swap the key for an **EC2 instance-role** granted
  `bedrock:InvokeModel` on the inference-profile ARNs — no stored secret anywhere.
