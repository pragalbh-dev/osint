"""Deterministic image integrity — the two-hash fingerprint frozen onto an image claim at ingest
(INGEST session, item 6).

An imagery claim is only as trustworthy as the pixels behind it, so before any VLM read we stamp a
small, **byte-deterministic** fingerprint of the raw image and freeze it (G1: computed once, upstream
of ``store.append``; ``rebuild()`` only ever *reads* it — nothing here re-fires on reload). The
fingerprint carries three independent integrity signals:

* **sha256** (stdlib, always present) — exact-byte identity: the same file twice is provably the same
  file. This is the floor the module never drops below, even if every optional imaging lib is absent.
* **PDQ** (Facebook's perceptual hash, 256-bit) + its quality score — *near*-duplicate identity: a
  re-encoded / lightly-edited copy of an image lands a small Hamming distance away, an unrelated image
  lands far. This is what catches a recycled "fresh satellite pass" that is really last year's frame.
* **pHash** (64-bit DCT) — an independent perceptual hash over the same pixels, both a cross-check on
  PDQ and the graceful-degradation path when ``pdqhash`` is unavailable.

Plus **EXIF** (capture-date / resolution / geo when the file carries them) — provenance metadata that
is *itself* a deception signal: a "too-clean" synthetic image typically carries no camera metadata.

This module decides nothing about *first-seen vs recycled* — that judgement (comparing a new
fingerprint against the corpus of already-seen ones) is SCORE's. Here we only compute and freeze; the
comparison primitive ``pdq_hamming`` is exposed so SCORE (or a test) can measure distance. Every
optional dependency is imported lazily and guarded, so a missing lib degrades one signal to ``None``
rather than taking the ingest path down.
"""

from __future__ import annotations

import hashlib
import io
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:  # import only for annotations — the runtime import is lazy + guarded below
    from PIL.Image import Image as PILImage

# ── the frozen fingerprint ───────────────────────────────────────────────────────────────────────


class ImageFingerprint(BaseModel):
    """The image-integrity stamp frozen onto an imagery claim's ``attributes`` at ingest.

    ``sha256`` is always populated; the perceptual/metadata fields are ``None`` / ``{}`` when the
    optional imaging libs cannot produce them (a missing lib or an undecodable byte blob), never a
    fabricated value — an absent signal is honestly absent (the anti-fabrication discipline).
    """

    model_config = ConfigDict(extra="forbid")

    sha256: str
    pdq_hash: str | None = None
    pdq_quality: int | None = None
    phash: str | None = None
    exif: dict[str, Any] = {}


# ── public API ───────────────────────────────────────────────────────────────────────────────────


def image_fingerprint(data: bytes) -> ImageFingerprint:
    """Compute the frozen integrity fingerprint for one image's raw bytes (deterministic, offline).

    sha256 is unconditional. The image is decoded once (via PIL); PDQ, pHash and EXIF are each derived
    from that single decode and each fail *independently* to ``None`` / ``{}`` so one missing lib or a
    partial decode never poisons the others.
    """
    sha256 = hashlib.sha256(data).hexdigest()
    image = _open_image(data)
    if image is None:
        return ImageFingerprint(sha256=sha256)
    pdq_hash, pdq_quality = _pdq(image)
    return ImageFingerprint(
        sha256=sha256,
        pdq_hash=pdq_hash,
        pdq_quality=pdq_quality,
        phash=_phash(image),
        exif=_exif(image),
    )


def pdq_hamming(a: str, b: str) -> int:
    """Bit (Hamming) distance between two equal-width hex hash strings (PDQ *or* pHash).

    The two hashes must be the same width (both 256-bit PDQ = 64 hex chars, or both 64-bit pHash =
    16 hex chars) — comparing a PDQ hash to a pHash hash is meaningless and raises ``ValueError``.
    A leading ``0x`` and surrounding whitespace are tolerated; comparison is case-insensitive.
    """
    na, nb = _normalize_hex(a), _normalize_hex(b)
    if len(na) != len(nb):
        raise ValueError(f"hash width mismatch: {len(na)} hex chars vs {len(nb)} (compare like with like)")
    return bin(int(na, 16) ^ int(nb, 16)).count("1")


# ── decode ───────────────────────────────────────────────────────────────────────────────────────


def _open_image(data: bytes) -> PILImage | None:
    """Decode ``data`` to a PIL image, or ``None`` if PIL is absent / the bytes are not an image."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        image = Image.open(io.BytesIO(data))
        image.load()  # force full decode now so a truncated file fails here, not mid-hash
    except Exception:  # noqa: BLE001 — any decode failure degrades to "no perceptual signal"
        return None
    return image


# ── perceptual hashes ────────────────────────────────────────────────────────────────────────────


def _pdq(image: PILImage) -> tuple[str | None, int | None]:
    """256-bit PDQ hash (hex) + quality score over the RGB pixels, or ``(None, None)`` on failure."""
    try:
        import numpy as np
        import pdqhash
    except ImportError:
        return None, None
    try:
        arr = np.ascontiguousarray(np.asarray(image.convert("RGB"), dtype=np.uint8))
        vector, quality = pdqhash.compute(arr)
        bits = "".join("1" if int(b) else "0" for b in vector)  # 256 bits, MSB-first
        return format(int(bits, 2), "064x"), int(quality)
    except Exception:  # noqa: BLE001 — a hash we cannot compute is honestly absent, not fabricated
        return None, None


def _phash(image: PILImage, *, hash_size: int = 8, highfreq_factor: int = 4) -> str | None:
    """64-bit DCT perceptual hash (hex) via PIL + numpy, or ``None`` on failure.

    Standard low-frequency-DCT pHash: greyscale → resize to ``hash_size*highfreq_factor`` square →
    2-D DCT-II → keep the top-left ``hash_size`` block → threshold each coefficient against the block
    median. The DCT is done with a plain cosine matrix (unnormalised); the median comparison is
    scale-invariant so the exact normalisation does not matter — only that it is deterministic.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    try:
        size = hash_size * highfreq_factor
        small = image.convert("L").resize((size, size), Image.Resampling.LANCZOS)
        pixels = np.asarray(small, dtype=np.float64)
        k = np.arange(size).reshape(-1, 1)
        n = np.arange(size).reshape(1, -1)
        dct_matrix = np.cos(np.pi * (2 * n + 1) * k / (2 * size))
        transformed = dct_matrix @ pixels @ dct_matrix.T
        low = transformed[:hash_size, :hash_size]
        median = float(np.median(low))
        bits = "".join("1" if v > median else "0" for v in low.flatten())
        width = (hash_size * hash_size + 3) // 4  # hex digits for the bit count (64 bits → 16)
        return format(int(bits, 2), f"0{width}x")
    except Exception:  # noqa: BLE001
        return None


# ── EXIF ─────────────────────────────────────────────────────────────────────────────────────────

# Numeric EXIF tag ids (avoid a PIL.ExifTags import in the hot path; these are stable ids).
_TAG_DATETIME = 306
_TAG_DATETIME_ORIGINAL = 36867
_TAG_MAKE = 271
_TAG_MODEL = 272
_TAG_ORIENTATION = 274
_TAG_X_RES = 282
_TAG_Y_RES = 283
_GPS_IFD = 0x8825
_GPS_LAT_REF = 1
_GPS_LAT = 2
_GPS_LON_REF = 3
_GPS_LON = 4
_GPS_ALT_REF = 5
_GPS_ALT = 6


def _exif(image: PILImage) -> dict[str, Any]:
    """Extract capture-date / resolution / geo from EXIF, JSON-safe. ``{}`` when the file carries none.

    Only fields the file actually states are emitted (no image dimensions injected as pseudo-EXIF):
    an image with no metadata returns ``{}``, which is itself a signal downstream (a synthetic /
    scrubbed image is "too clean").
    """
    try:
        raw = image.getexif()
    except Exception:  # noqa: BLE001 — no readable EXIF is a valid, common state
        return {}
    if not raw:
        return {}

    out: dict[str, Any] = {}
    capture = raw.get(_TAG_DATETIME_ORIGINAL) or raw.get(_TAG_DATETIME)
    if capture:
        out["capture_date"] = _jsonable(capture)
    for tag, key in (
        (_TAG_MAKE, "make"),
        (_TAG_MODEL, "model"),
        (_TAG_ORIENTATION, "orientation"),
        (_TAG_X_RES, "x_resolution"),
        (_TAG_Y_RES, "y_resolution"),
    ):
        if tag in raw:
            out[key] = _jsonable(raw[tag])

    gps = _gps(raw)
    if gps:
        out["gps"] = gps
    return out


def _gps(raw: Any) -> dict[str, Any]:
    """Decode the GPS IFD to decimal-degree ``{lat, lon[, altitude]}``, or ``{}`` if absent/unparseable."""
    try:
        ifd = raw.get_ifd(_GPS_IFD)
    except Exception:  # noqa: BLE001
        return {}
    if not ifd:
        return {}
    out: dict[str, Any] = {}
    lat = _dms_to_decimal(ifd.get(_GPS_LAT), ifd.get(_GPS_LAT_REF), negative_refs=("S",))
    lon = _dms_to_decimal(ifd.get(_GPS_LON), ifd.get(_GPS_LON_REF), negative_refs=("W",))
    if lat is not None:
        out["lat"] = lat
    if lon is not None:
        out["lon"] = lon
    alt = ifd.get(_GPS_ALT)
    if alt is not None:
        try:
            altitude = float(alt)
            if ifd.get(_GPS_ALT_REF) in (1, b"\x01"):  # below sea level
                altitude = -altitude
            out["altitude"] = altitude
        except (TypeError, ValueError):
            pass
    return out


def _dms_to_decimal(dms: Any, ref: Any, *, negative_refs: tuple[str, ...]) -> float | None:
    """Convert an EXIF (degrees, minutes, seconds) triple + hemisphere ref to signed decimal degrees."""
    if not dms:
        return None
    try:
        degrees, minutes, seconds = (float(x) for x in dms)
    except (TypeError, ValueError):
        return None
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if isinstance(ref, str) and ref.strip().upper() in negative_refs:
        decimal = -decimal
    return decimal


# ── small helpers ────────────────────────────────────────────────────────────────────────────────


def _jsonable(value: Any) -> Any:
    """Coerce an EXIF value (IFDRational, bytes, tuple, …) to a JSON-serialisable scalar/list."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip("\x00").strip()
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (int, str)):
        return value
    try:
        return float(value)  # IFDRational and other rationals coerce cleanly
    except (TypeError, ValueError):
        return str(value)


def _normalize_hex(value: str) -> str:
    """Canonicalise a hex hash string for comparison (strip whitespace / ``0x``, lowercase)."""
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    if not text:
        raise ValueError("empty hash string")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"not a hex hash string: {value!r}") from exc
    return text
