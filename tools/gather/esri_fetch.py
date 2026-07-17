#!/usr/bin/env python3
"""Pull HIGH-RESOLUTION basemap imagery of a site via Esri World Imagery (ArcGIS REST
export) — the sub-meter tier of the hybrid imagery posture.

Why this exists: Sentinel-2 (copernicus_fetch.py) caps at 10 m GSD — it resolves an
airfield footprint but NOT launchers / TELs / radars. Esri World Imagery aggregates
commercial sub-meter sources (Maxar / Airbus), typically ~0.3-0.6 m in populated areas,
which DOES resolve vehicles, revetments, and the petal/ring launcher layout of a SAM
battery — so a VLM can honestly describe the site shape. Keyless, no OAuth.

Posture note: for a FABRICATED demo scenario, the "confirm" frames point at a REAL,
publicly-documented SAM site (petal/ring layout) and are RELABELED to the scenario site;
the answer key records both the real source and the scenario label (integrity: real,
provenance_note: relabeled). We keep Sentinel-2 for the deliberately-low-res beats
(cloud gap, wide-area) where "cannot resolve launcher count" is the point.

Run: python tools/gather/esri_fetch.py --site rahwali_sam --half 0.004
     python tools/gather/esri_fetch.py --lon 73.09972 --lat 33.61639 --half 0.004 --out /tmp/x.png
"""
from __future__ import annotations
import argparse, pathlib, sys
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPORT_URL = ("https://services.arcgisonline.com/arcgis/rest/services/"
              "World_Imagery/MapServer/export")

# Named sites (lon, lat, half-span in degrees). REAL SAM-site coords (petal/ring layout,
# publicly documented) go here once verified, then get RELABELED to scenario sites in the
# scenario YAML / answer key. half=0.004 deg ~ 890 m span -> ~0.87 m/px at 1024 px.
SITES: dict[str, tuple[float, float, float]] = {
    # validation anchor (real airbase, not a SAM site) — proves the resolution upgrade:
    "nurkhan_ref": (73.09972, 33.61639, 0.004),
    # --- real SAM sites (petal/ring), verified in current Esri imagery, RELABELED to
    #     scenario sites in hq9p_primary.yaml (answer key records real_source). ---
    "karachi_sam":    (108.70656, 34.62061, 0.005),  # REAL: HQ-9 nr Xi'an, CN (occupied petal)     -> Karachi (d07, confirmed HERO)
    "forward_empty":  (104.14286, 36.53728, 0.005),  # REAL: HQ-9 nr Lanzhou, CN (EMPTY petal)       -> forward site (d17b, no-TELs gap)
    "rawalpindi_sam": (118.99917, 31.60444, 0.006),  # REAL: PLA air-defense garrison nr Nanjing, CN -> Rawalpindi (d17, 2021 baseline)
    "rahwali_sam":    (35.39810,  45.01050, 0.005),  # REAL: S-400 site nr Feodosia, Crimea (dispersed/occupied) -> Rahwali (d18, single-pass PROBABLE)
}


def pull(lon: float, lat: float, half: float = 0.004, size: int = 1024,
         image_sr: int = 3857) -> bytes:
    """Return PNG bytes for the bbox centered on (lon,lat). image_sr=3857 keeps the
    familiar web-mercator look; use 4326 for equirectangular."""
    bbox = f"{lon - half},{lat - half},{lon + half},{lat + half}"
    r = requests.get(EXPORT_URL, params={
        "bbox": bbox, "bboxSR": "4326", "imageSR": str(image_sr),
        "size": f"{size},{size}", "format": "png", "f": "image",
    }, timeout=60)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    if "image" not in ct:
        raise RuntimeError(f"non-image response ({ct}): {r.text[:200]}")
    return r.content


def resolve_site(name: str) -> tuple[float, float, float]:
    if name not in SITES:
        raise SystemExit(f"unknown site '{name}'. known: {', '.join(SITES) or '(none)'}")
    return SITES[name]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", help="named site from SITES")
    ap.add_argument("--lon", type=float)
    ap.add_argument("--lat", type=float)
    ap.add_argument("--half", type=float, default=0.004, help="bbox half-span in degrees")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--out", help="output png path")
    args = ap.parse_args()

    if args.site:
        lon, lat, half = resolve_site(args.site)
        if args.half != 0.004:
            half = args.half
        default_out = ROOT / "corpus" / "raw" / "imagery" / f"esri_{args.site}.png"
    elif args.lon is not None and args.lat is not None:
        lon, lat, half = args.lon, args.lat, args.half
        default_out = ROOT / "corpus" / "raw" / "imagery" / f"esri_{lon}_{lat}.png"
    else:
        ap.error("provide --site or (--lon and --lat)")

    img = pull(lon, lat, half, args.size)
    out = pathlib.Path(args.out) if args.out else default_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img)
    span_m = half * 2 * 111_000
    print(f"{len(img)} bytes  span~{span_m:.0f}m -> ~{span_m/args.size:.2f} m/px  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
