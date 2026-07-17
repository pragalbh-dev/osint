#!/usr/bin/env python3
"""Pull REAL Sentinel-2 true-color imagery of a site via the Copernicus Data Space
Sentinel Hub Process API (OAuth client-credentials with CLIENT_ID / CLIENT_SECRET).

These frames are the *real* tier of the hybrid imagery posture: integrity = unaltered,
so the pipeline can confirm on them (a fabricated image would be self-flagged synthetic).
10 m Sentinel-2 shows the site footprint (cleared pad / revetments / vehicles-as-blobs),
not launcher-level detail — which is honest and matches the insufficient-evidence flex.

Run: python tools/gather/copernicus_fetch.py            # all sites
     python tools/gather/copernicus_fetch.py --site karachi --from 2024-01-01 --to 2024-12-31
"""
from __future__ import annotations
import argparse, json, os, pathlib, sys
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Site centers (lon, lat), WGS84. Base/airfield coords are REAL/public (Wikipedia/OSM/aviation DBs);
# the Karachi SAM pad is SYNTHETIC (we do not publish real battery fixes). See config/places.yaml +
# artifacts/md/13-location-normalization.md for canonical values, aliases, and provenance.
SITES = {
    "karachi":     (67.2034, 24.9012),   # SYNTHETIC notional Army AD site, Malir area, Karachi
    "rawalpindi":  (73.09972, 33.61639), # REAL: PAF Base Nur Khan (fmr Chaklala), OPRN — relocation baseline (2021)
    "rahwali":     (74.131, 32.239),     # REAL: Rahwali airfield, ~10 km NW of Gujranwala — relocation dest (2025)
}

EVALSCRIPT = """//VERSION=3
function setup(){return {input:["B02","B03","B04"],output:{bands:3}};}
function evaluatePixel(s){return [2.5*s.B04, 2.5*s.B03, 2.5*s.B02];}
"""


def creds():
    def frm(name):
        if os.environ.get(name):
            return os.environ[name]
        envf = ROOT / ".env"
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return None
    return frm("CLIENT_ID"), frm("CLIENT_SECRET")


def token(cid, csec):
    r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials",
                                       "client_id": cid, "client_secret": csec}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def fetch(tok, lon, lat, frm, to, half=0.03, px=1024, max_cloud=20):
    bbox = [lon - half, lat - half, lon + half, lat + half]
    payload = {
        "input": {
            "bounds": {"bbox": bbox,
                       "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
            "data": [{"type": "sentinel-2-l2a",
                      "dataFilter": {"timeRange": {"from": f"{frm}T00:00:00Z", "to": f"{to}T23:59:59Z"},
                                     "maxCloudCoverage": max_cloud,
                                     "mosaickingOrder": "leastCC"}}],
        },
        "output": {"width": px, "height": px,
                   "responses": [{"identifier": "default", "format": {"type": "image/png"}}]},
        "evalscript": EVALSCRIPT,
    }
    r = requests.post(PROCESS_URL, headers={"Authorization": f"Bearer {tok}"},
                      json=payload, timeout=90)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:300]}"
    if not r.content or len(r.content) < 500:
        return None, f"empty/tiny response ({len(r.content)} bytes)"
    return r.content, "ok"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", choices=list(SITES) + ["all"], default="all")
    ap.add_argument("--from", dest="frm", default="2024-01-01")
    ap.add_argument("--to", default="2024-12-31")
    ap.add_argument("--max-cloud", type=int, default=20)
    args = ap.parse_args()

    cid, csec = creds()
    print("CLIENT_ID present:", bool(cid), "| CLIENT_SECRET present:", bool(csec))
    if not (cid and csec):
        print("missing creds — abort"); return 1
    try:
        tok = token(cid, csec)
    except Exception as e:  # noqa: BLE001
        print("TOKEN FAILED:", type(e).__name__, str(e)[:300]); return 1
    print("token OK")

    out_dir = ROOT / "corpus" / "raw" / "imagery"
    out_dir.mkdir(parents=True, exist_ok=True)
    sites = SITES if args.site == "all" else {args.site: SITES[args.site]}
    for name, (lon, lat) in sites.items():
        img, status = fetch(tok, lon, lat, args.frm, args.to, max_cloud=args.max_cloud)
        if img:
            p = out_dir / f"sentinel2_{name}_{args.frm}_{args.to}.png"
            p.write_bytes(img)
            print(f"  ✓ {name}: {p.relative_to(ROOT)} ({len(img)} bytes)")
        else:
            print(f"  ✗ {name}: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
