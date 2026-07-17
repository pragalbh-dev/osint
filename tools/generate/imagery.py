#!/usr/bin/env python3
"""Unified imagery module for the corpus (hybrid posture, see 10-data-generation-strategy §6 + 11 A1).

Three roles:
  * REAL Sentinel-2 (confirm/observable frames) — integrity=real, can't self-flag  -> copernicus_fetch
  * FABRICATED overhead (illustration / deception) — Nano Banana Pro, iterative refine
  * FABRICATED social ground-level (sighting convoy, recycled parade photo) — Nano Banana Pro
Then a VLM caption turns every image into the analyst evidence claim.

Image kinds: satellite_overhead | ground_convoy | parade | site_photo
Models: image = gemini-3-pro-image (Nano Banana Pro) -> gemini-3.1-flash-image fallback;
        VLM (caption+critique) = gemini-3.1-pro-preview -> gemini-3.5-flash / gemini-2.5-pro fallback.

CLI (test one image):  python tools/generate/imagery.py --kind ground_convoy --iters 3
"""
from __future__ import annotations
import argparse, base64, io, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMG_DIR = ROOT / "corpus" / "raw" / "imagery"
GEN_DIR = ROOT / "corpus" / "scenarios"        # generated corpus images live beside docs

IMG_MODELS = ["gemini-3-pro-image", "gemini-3.1-flash-image"]        # best first
VLM_MODELS = ["gemini-3.1-pro-preview", "gemini-3.5-flash", "gemini-2.5-pro"]

# base prompts per kind; the refine loop rewrites these toward realism
BASE_PROMPTS = {
    "satellite_overhead": (
        "A realistic TOP-DOWN nadir satellite image (commercial ~0.5 m / Sentinel-2-like look) of a "
        "surface-to-air missile battery in arid South-Asian terrain: a cleared circular/petal prepared "
        "pad, 4-6 long transporter-erector-launcher vehicles in a radial layout around a central "
        "engagement-radar vehicle, earthen revetments, perimeter track, a few support trucks. Muted "
        "natural desert palette, slight sensor blur, no text/labels/watermark."),
    "ground_convoy": (
        "A realistic grainy night-time smartphone photo taken from a roadside of a military road convoy: "
        "several large tarpaulin-covered transporter/launcher trucks with escort vehicles and headlights, "
        "motion blur, low light, slightly tilted framing, compression artefacts, as an amateur bystander "
        "would capture. No text/watermark."),
    "parade": (
        "A realistic daytime photo of a military parade: large transporter-erector-launcher (TEL) "
        "vehicles carrying long missile canisters driving past crowds and flags, telephoto compression, "
        "as press/spectator footage. No text/watermark."),
    "site_photo": (
        "A realistic ground-level photo of a fielded air-defence site: a phased-array radar vehicle and "
        "canister launcher on a cleared area with revetments, overcast light, as an amateur/OSINT photo. "
        "No text/watermark."),
}
REALISM_TARGET = {
    "satellite_overhead": "a real commercial/Sentinel-2 overhead satellite frame",
    "ground_convoy": "a real grainy bystander smartphone night photo",
    "parade": "a real press/spectator parade photograph",
    "site_photo": "a real amateur ground photo of a military site",
}


def _key(names):
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in names:
                    return v.strip().strip('"').strip("'")
    return None


def _client():
    from google import genai
    return genai.Client(api_key=_key(["GEMINI_API_KEY", "GOOGLE_API_KEY"]))


def _img_bytes(part_data):
    if isinstance(part_data, (bytes, bytearray)):
        return bytes(part_data)
    try:
        return base64.b64decode(part_data)
    except Exception:
        return None


def generate_image(client, prompt):
    from google.genai import types
    for m in IMG_MODELS:
        try:
            resp = client.models.generate_content(
                model=m, contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
            for part in resp.candidates[0].content.parts:
                d = getattr(part, "inline_data", None)
                if d and d.data:
                    b = _img_bytes(d.data)
                    if b:
                        return b, m
        except Exception as e:  # noqa: BLE001
            last = f"{m}: {type(e).__name__}: {str(e)[:120]}"
    return None, last if 'last' in dir() else "no image model succeeded"


def _vlm(client, img, prompt):
    from google.genai import types
    for m in VLM_MODELS:
        try:
            r = client.models.generate_content(
                model=m, contents=[types.Part.from_bytes(data=img, mime_type="image/png"), prompt])
            if r.text and r.text.strip():
                return r.text.strip(), m
        except Exception:  # noqa: BLE001
            continue
    return None, None


def critique(client, img, target):
    txt, _ = _vlm(client, img,
        f"You are a strict image-forensics reviewer. Judge how convincingly this image passes as {target}. "
        "Return ONLY JSON: {\"realism\": <0.0-1.0>, \"issues\": [\"...\"], \"improved_prompt\": \"a rewritten "
        "generation prompt that would fix the issues and look more real\"}.")
    if not txt:
        return {"realism": 0.0, "issues": ["vlm critique failed"], "improved_prompt": None}
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        return json.loads(m.group(0)) if m else {"realism": 0.5, "issues": [], "improved_prompt": None}
    except Exception:
        return {"realism": 0.5, "issues": ["unparseable critique"], "improved_prompt": None}


def caption(client, img, kind):
    txt, model = _vlm(client, img,
        "You are an imagery analyst writing a source caption for an OSINT database. In 2-4 sentences "
        "describe ONLY what is visibly present (terrain, structures, vehicles/objects, count, layout, "
        "image quality). Do NOT name a specific real system, unit, or place; do not speculate beyond the "
        "pixels. Write it as a raw analyst observation, no headers.")
    return txt, model


def make_image(client, kind, iters=3, threshold=0.8, extra=""):
    """Iterative refine: generate -> critique -> rewrite prompt -> regenerate. Returns best."""
    prompt = BASE_PROMPTS[kind] + (f" {extra}" if extra else "")
    target = REALISM_TARGET[kind]
    best = None
    for i in range(max(1, iters)):
        img, imodel = generate_image(client, prompt)
        if not img:
            print(f"    iter {i}: gen failed: {imodel}")
            continue
        crit = critique(client, img, target)
        score = float(crit.get("realism", 0.0) or 0.0)
        print(f"    iter {i}: model={imodel} realism={score:.2f} issues={crit.get('issues')}")
        if best is None or score > best[2]:
            best = (img, prompt, score, imodel)
        if score >= threshold:
            break
        if crit.get("improved_prompt"):
            prompt = crit["improved_prompt"]
    return best  # (img, final_prompt, score, model) or None


def real_sentinel(site, frm="2024-01-01", to="2024-12-31", max_cloud=15):
    sys.path.insert(0, str(ROOT / "tools" / "gather"))
    import copernicus_fetch as cf
    cid, csec = cf.creds()
    if not (cid and csec):
        return None, "no copernicus creds"
    if site not in cf.SITES:
        return None, f"unknown site {site}"
    lon, lat = cf.SITES[site]
    tok = cf.token(cid, csec)
    return cf.fetch(tok, lon, lat, frm, to, max_cloud=max_cloud)


def real_esri(site, half=None, size=1024):
    """High-res (~0.5 m) Esri World Imagery frame for a named site (real SAM site,
    relabeled to a scenario site). Returns (png_bytes, status). Keyless."""
    sys.path.insert(0, str(ROOT / "tools" / "gather"))
    import esri_fetch as ef
    if site not in ef.SITES:
        return None, f"unknown esri site {site}"
    lon, lat, shalf = ef.SITES[site]
    try:
        return ef.pull(lon, lat, half or shalf, size), "ok"
    except Exception as e:  # noqa: BLE001
        return None, f"esri fetch failed: {type(e).__name__}: {str(e)[:120]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", choices=list(BASE_PROMPTS), default="ground_convoy")
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    client = _client()
    best = make_image(client, args.kind, iters=args.iters)
    if not best:
        print("FAILED to generate"); return 1
    img, prompt, score, model = best
    out = pathlib.Path(args.out) if args.out else IMG_DIR / f"fab_{args.kind}_test.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img)
    from PIL import Image
    dim = Image.open(io.BytesIO(img)).size
    cap, capmodel = caption(client, img, args.kind)
    print(f"\nBEST: {out.relative_to(ROOT)}  {dim}  realism={score:.2f}  imgmodel={model}")
    print(f"CAPTION (via {capmodel}):\n  {cap}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
