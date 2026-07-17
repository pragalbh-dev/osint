#!/usr/bin/env python3
"""Image-attach pass: for every scenario doc carrying an `image:` block, produce the image
(real Sentinel-2 OR fabricated Nano-Banana-Pro w/ iterative refine), VLM-caption it, save
<id>.png beside the doc, and record image metadata (source/integrity/caption/sha/realism)
into answer_key.json. Separate from text generation so neither re-spends the other.

Recycled/echo cluster: docs sharing `shared_id` reuse ONE image (same sha = the shared-image
provenance signal M4 keys on).

Run: python tools/generate/attach_images.py tools/generate/scenarios/hq9p_primary.yaml
"""
from __future__ import annotations
import hashlib, json, pathlib, sys
import yaml
import imagery   # same directory

ROOT = pathlib.Path(__file__).resolve().parents[2]


def run(spec_path, only=None):
    only = set(only) if only else None
    spec = yaml.safe_load(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    name = spec["meta"]["name"]
    out = ROOT / "corpus" / "scenarios" / name
    docs_dir = out / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    ak_path = out / "answer_key.json"
    ak = json.loads(ak_path.read_text(encoding="utf-8")) if ak_path.exists() else None

    client = imagery._client()
    shared = {}      # shared_id -> (img, caption, realism, model)
    updates = {}
    sdir = ROOT / "corpus" / "raw" / "imagery"     # persisted shared images (cross-scenario)

    def load_shared(sid):
        p, c = sdir / f"shared_{sid}.png", sdir / f"shared_{sid}.caption.txt"
        if p.exists() and c.exists():
            return p.read_bytes(), c.read_text(encoding="utf-8"), 1.0, "cached-shared"
        return None

    def save_shared(sid, img, cap):
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / f"shared_{sid}.png").write_bytes(img)
        (sdir / f"shared_{sid}.caption.txt").write_text(cap or "", encoding="utf-8")

    img_docs = [d for d in spec["documents"] if d.get("image")]
    if only:
        img_docs = [d for d in img_docs if d["id"] in only]
    print(f"{name}: {len(img_docs)} docs with image blocks{' (filtered)' if only else ''}")
    for d in img_docs:
        did, blk = d["id"], d["image"]
        kind = blk["kind"]; src = blk.get("source", "fabricated")
        sid = blk.get("shared_id")
        try:
            got = shared.get(sid) if sid else None
            if got is None and sid:
                got = load_shared(sid)     # cross-scenario reuse -> identical bytes/sha
            if got is not None:
                img, cap, realism, model = got
                model = str(model) + " [shared]"
            elif src == "real_sentinel":
                img, status = imagery.real_sentinel(
                    blk["site"], blk.get("from", "2024-01-01"), blk.get("to", "2024-12-31"),
                    max_cloud=blk.get("max_cloud", 15))
                if not img:
                    print(f"  ✗ {did}: sentinel {status}"); continue
                cap, _ = imagery.caption(client, img, kind); realism = 1.0; model = "sentinel-2"
            elif src == "real_esri":
                img, status = imagery.real_esri(blk["site"], half=blk.get("half"))
                if not img:
                    print(f"  ✗ {did}: esri {status}"); continue
                cap, _ = imagery.caption(client, img, kind); realism = 1.0; model = "esri-world-imagery"
            else:
                best = imagery.make_image(client, kind, iters=blk.get("iters", 2),
                                          extra=blk.get("extra", ""))
                if not best:
                    print(f"  ✗ {did}: fabrication failed"); continue
                img, _, realism, model = best
                cap, _ = imagery.caption(client, img, kind)
            if sid and sid not in shared:
                clean = (img, cap, realism, str(model).replace(" [shared]", ""))
                shared[sid] = clean
                if got is None:                     # freshly generated -> persist for other scenarios
                    save_shared(sid, img, cap)
            (docs_dir / f"{did}.png").write_bytes(img)
            sha = hashlib.sha256(img).hexdigest()[:16]
            updates[did] = {"image_file": f"{did}.png", "kind": kind, "source": src,
                            "integrity": blk.get("integrity", "synthetic"),
                            "provenance": blk.get("provenance"),      # e.g. 'relabeled'
                            "real_source": blk.get("real_source"),    # the true site behind a relabeled real frame
                            "shared_id": sid, "first_seen": blk.get("first_seen"),
                            "sha256_16": sha, "realism": round(realism, 2), "model": model,
                            "caption": cap}
            print(f"  ✓ {did}: {kind}/{src} integrity={blk.get('integrity','synthetic')} "
                  f"realism={realism:.2f} sha={sha}{' [shared]' if sid else ''}")
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {did}: {type(e).__name__}: {str(e)[:140]}")

    if ak and updates:
        for entry in ak.get("documents", []):
            if entry["id"] in updates:
                entry["image"] = updates[entry["id"]]
        ak_path.write_text(json.dumps(ak, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"attached {len(updates)} images -> {docs_dir.relative_to(ROOT)}/*.png; "
          f"metadata -> {ak_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        only = argv[i + 1:]
        argv = argv[:i]
    sys.exit(run(argv[0], only=only))
