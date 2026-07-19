#!/usr/bin/env python3
"""Vendor CARTO dark_matter basemap tiles for the Pakistan AOI so the demo map is
fully offline (zero network dependency on the graded call). Downloads a padded AOI
across zoom 3-7 into public/tiles/dark/{z}/{x}/{y}.png. Idempotent (skips existing).

Re-run:  cd frontend && python3 scripts/vendor_tiles.py
"""
import math
import os
import sys
import time
import urllib.request

# Padded AOI (minlat, minlon, maxlat, maxlon) — Pakistan + generous roam/fit margin
# (the fitted view overshoots the AOI vertically on a tall container).
BBOX = (15.0, 52.0, 43.0, 86.0)
ZMIN, ZMAX = 3, 7
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "tiles", "dark")
SRC = "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
UA = "chanakya-osint-demo/0.1 (offline tile vendoring; contact: repo owner)"


def deg2num(lat, lon, z):
    lat_r = math.radians(lat)
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def main():
    total, fetched, bytes_ = 0, 0, 0
    for z in range(ZMIN, ZMAX + 1):
        xt, yt = deg2num(BBOX[2], BBOX[1], z)  # top-left
        xb, yb = deg2num(BBOX[0], BBOX[3], z)  # bottom-right
        n = 2 ** z
        xs = range(max(0, min(xt, xb)), min(n - 1, max(xt, xb)) + 1)
        ys = range(max(0, min(yt, yb)), min(n - 1, max(yt, yb)) + 1)
        for x in xs:
            for y in ys:
                total += 1
                dest_dir = os.path.join(OUT, str(z), str(x))
                dest = os.path.join(dest_dir, f"{y}.png")
                if os.path.exists(dest) and os.path.getsize(dest) > 0:
                    bytes_ += os.path.getsize(dest)
                    continue
                os.makedirs(dest_dir, exist_ok=True)
                url = SRC.format(z=z, x=x, y=y)
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                try:
                    with urllib.request.urlopen(req, timeout=20) as r:
                        data = r.read()
                    with open(dest, "wb") as f:
                        f.write(data)
                    fetched += 1
                    bytes_ += len(data)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {z}/{x}/{y} failed: {e}", file=sys.stderr)
                time.sleep(0.02)
        print(f"z{z}: {len(xs)}x{len(ys)} = {len(xs) * len(ys)} tiles")
    print(f"done: {total} tiles ({fetched} newly fetched), {bytes_ / 1024:.0f} KB total")


if __name__ == "__main__":
    main()
