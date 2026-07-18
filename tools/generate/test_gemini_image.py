#!/usr/bin/env python3
"""Feasibility test: fabricate a synthetic overhead SAM-site image (Nano Banana 2 via
Gemini API) + VLM-caption it (Gemini, Claude fallback). Answers: can we substitute
fabricated imagery + a real VLM call for hard-to-get real imagery?

Run: python tools/generate/test_gemini_image.py
"""
from __future__ import annotations
import base64, os, pathlib, sys

ROOT = pathlib.Path("/home/synaptic/data-science/research/rough/osint/osint")


def key_from(names):
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


def as_bytes(data):
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    try:
        return base64.b64decode(data)
    except Exception:
        return None


def main():
    gkey = key_from(["GEMINI_API_KEY", "GOOGLE_API_KEY"])
    print("gemini key present:", bool(gkey))
    if not gkey:
        print("NO GEMINI KEY — abort"); return

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=gkey)

    prompt = (
        "Synthetic, illustrative TOP-DOWN satellite/aerial view for a computer-vision TEST dataset "
        "(not a real location): a surface-to-air missile battery in arid terrain — a cleared "
        "circular/petal-shaped prepared pad with 4-6 long transporter-erector-launcher vehicles "
        "arranged radially around a central engagement-radar vehicle, earthen revetments, a perimeter "
        "track and a few support trucks. Overhead nadir perspective, muted natural colors, roughly "
        "0.5 m resolution look, no text or labels."
    )

    img_models = ["gemini-3.1-flash-image", "gemini-3-pro-image", "gemini-2.5-flash-image",
                  "gemini-2.0-flash-preview-image-generation"]
    img, used, errs = None, None, {}
    for m in img_models:
        for mods in (["IMAGE"], ["TEXT", "IMAGE"]):
            try:
                resp = client.models.generate_content(
                    model=m, contents=prompt,
                    config=types.GenerateContentConfig(response_modalities=mods))
                for part in resp.candidates[0].content.parts:
                    idata = getattr(part, "inline_data", None)
                    if idata and idata.data:
                        img = as_bytes(idata.data); used = f"{m} {mods}"; break
                if img:
                    break
            except Exception as e:  # noqa: BLE001
                errs[f"{m}/{mods}"] = f"{type(e).__name__}: {str(e)[:160]}"
        if img:
            break

    if not img:
        print("IMAGE GEN FAILED. Errors:")
        for k, v in errs.items():
            print(" ", k, "->", v)
        return

    out = ROOT / "corpus" / "raw" / "imagery" / "synth_sam_site_test.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img)
    print(f"IMAGE OK via {used} -> {out.relative_to(ROOT)} ({len(img)} bytes)")

    # caption with Gemini vision
    cap, capmodel, caperr = None, None, {}
    caption_prompt = ("You are an imagery analyst. In 2-3 sentences describe ONLY what is visibly "
                      "present in this overhead image: terrain, structures, vehicles/objects, layout. "
                      "Do not speculate beyond what is visible; do not name a specific real system/site.")
    for m in ["gemini-3.1-flash", "gemini-2.5-flash", "gemini-3-pro"]:
        try:
            r = client.models.generate_content(
                model=m, contents=[types.Part.from_bytes(data=img, mime_type="image/png"),
                                   caption_prompt])
            if r.text and r.text.strip():
                cap, capmodel = r.text.strip(), m; break
        except Exception as e:  # noqa: BLE001
            caperr[m] = f"{type(e).__name__}: {str(e)[:120]}"

    if not cap:
        # Claude vision fallback
        akey = key_from(["ANTHROPIC_API_KEY"])  # CLAUDE_API_KEY dropped (stack locked on ANTHROPIC_API_KEY)
        if akey:
            try:
                import anthropic
                ac = anthropic.Anthropic(api_key=akey)
                b64 = base64.b64encode(img).decode()
                r = ac.messages.create(model="claude-sonnet-5", max_tokens=300,
                    messages=[{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": caption_prompt}]}])
                cap = "".join(b.text for b in r.content if b.type == "text").strip()
                capmodel = "claude-sonnet-5 (fallback)"
            except Exception as e:  # noqa: BLE001
                caperr["claude"] = f"{type(e).__name__}: {str(e)[:120]}"

    print("\nCAPTION via", capmodel or "FAILED")
    print("  gemini caption errs:", caperr if not (cap and "gemini" in (capmodel or "")) else "n/a")
    print("  ---")
    print(" ", (cap or "(no caption)")[:800])


if __name__ == "__main__":
    main()
