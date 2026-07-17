from __future__ import annotations
import io, os, pathlib
from PIL import Image
from google import genai
from google.genai import types

ROOT = pathlib.Path("/home/synaptic/data-science/research/rough/osint/osint")


def key_from(names):
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in names:
                return v.strip().strip('"').strip("'")
    return None


client = genai.Client(api_key=key_from(["GEMINI_API_KEY", "GOOGLE_API_KEY"]))

print("=== generateContent-capable models ===")
cand = []
for m in client.models.list():
    acts = list(getattr(m, "supported_actions", []) or [])
    if "generateContent" in acts:
        nm = m.name.split("/")[-1]
        print(" ", nm)
        if ("flash" in nm or "pro" in nm) and not any(x in nm for x in ("image", "tts", "embedding", "live", "audio")):
            cand.append(nm)

img = (ROOT / "corpus/raw/imagery/synth_sam_site_test.png").read_bytes()
im = Image.open(io.BytesIO(img))
print("\nimage:", im.size, im.mode, len(img), "bytes")

prompt = ("You are an imagery analyst. In 2-3 sentences describe ONLY what is visibly present in this "
          "overhead image: terrain, structures, vehicles/objects, layout. No speculation; do not name a "
          "real system or site.")
print("\ncaption candidates:", cand[:6])
for nm in cand[:6]:
    try:
        r = client.models.generate_content(
            model=nm, contents=[types.Part.from_bytes(data=img, mime_type="image/png"), prompt])
        if r.text and r.text.strip():
            print(f"\nCAPTION via {nm}:\n{r.text.strip()[:800]}")
            break
    except Exception as e:  # noqa: BLE001
        print("  fail", nm, type(e).__name__, str(e)[:90])
