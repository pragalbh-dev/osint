"""Hashing tests — the two-hash image fingerprint frozen at ingest (INGEST item 6).

The load-bearing invariants: sha256 is byte-exact + always present; the perceptual hashes place a
re-encoded near-duplicate a *small* Hamming distance away and an unrelated image a *large* one (so
SCORE can tell "recycled last-year's frame" from "genuinely new pass"); EXIF is extracted when a file
carries it and is ``{}`` (never fabricated) when it does not. All offline + deterministic — images are
synthesised with PIL, nothing hits the network.
"""

from __future__ import annotations

import hashlib
import io

import numpy as np
import pytest
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from chanakya.ingest.hashing import (
    ImageFingerprint,
    image_fingerprint,
    pdq_hamming,
)

# ── image builders (deterministic) ─────────────────────────────────────────────────────────────


def _structured_png(seed: int = 7, *, size: int = 128) -> bytes:
    """A gradient + fixed-seed noise image (high PDQ quality) encoded as PNG."""
    rng = np.random.default_rng(seed)
    xs = np.linspace(0, 255, size).astype(int)
    arr = np.zeros((size, size, 3), int)
    arr[:, :, 0] = xs[None, :]
    arr[:, :, 1] = xs[:, None]
    arr[:, :, 2] = (xs[None, :] + xs[:, None]) // 2
    arr = (arr + rng.integers(-15, 15, arr.shape)).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return buf.getvalue()


def _reencode_jpeg(png: bytes, *, quality: int = 95) -> bytes:
    """Re-encode a PNG as JPEG — a lightly-lossy near-duplicate of the same pixels."""
    buf = io.BytesIO()
    Image.open(io.BytesIO(png)).convert("RGB").save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def _noise_png(seed: int, *, size: int = 128) -> bytes:
    """An unrelated pure-noise image."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 255, (size, size, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return buf.getvalue()


def _jpeg_with_exif() -> bytes:
    """A tiny JPEG carrying DateTime + Make + XResolution + a GPS IFD (31.5N, 74.2E)."""
    img = Image.new("RGB", (40, 30), (9, 9, 9))
    exif = img.getexif()
    exif[306] = "2021:06:15 09:30:00"  # DateTime
    exif[271] = "OrbCam"  # Make
    exif[282] = IFDRational(72, 1)  # XResolution
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (IFDRational(31, 1), IFDRational(30, 1), IFDRational(0, 1))
    gps[3] = "E"
    gps[4] = (IFDRational(74, 1), IFDRational(12, 1), IFDRational(0, 1))
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


# ── sha256 ─────────────────────────────────────────────────────────────────────────────────────


def test_sha256_is_exact_and_always_present() -> None:
    data = _structured_png()
    fp = image_fingerprint(data)
    assert fp.sha256 == hashlib.sha256(data).hexdigest()
    # Stable across calls on identical bytes.
    assert image_fingerprint(data).sha256 == fp.sha256


def test_sha256_present_even_for_non_image_bytes() -> None:
    junk = b"not an image at all"
    fp = image_fingerprint(junk)
    assert fp.sha256 == hashlib.sha256(junk).hexdigest()
    # No perceptual signal from undecodable bytes — honestly absent, never fabricated.
    assert fp.pdq_hash is None
    assert fp.pdq_quality is None
    assert fp.phash is None
    assert fp.exif == {}


def test_different_bytes_differ_in_sha256() -> None:
    a = image_fingerprint(_structured_png(seed=1))
    b = image_fingerprint(_structured_png(seed=2))
    assert a.sha256 != b.sha256


# ── PDQ ──────────────────────────────────────────────────────────────────────────────────────────


def test_pdq_present_and_well_formed() -> None:
    fp = image_fingerprint(_structured_png())
    assert fp.pdq_hash is not None
    assert len(fp.pdq_hash) == 64  # 256-bit hash → 64 hex chars
    int(fp.pdq_hash, 16)  # valid hex
    assert fp.pdq_quality is not None and 0 <= fp.pdq_quality <= 100


def test_pdq_is_deterministic() -> None:
    data = _structured_png()
    assert image_fingerprint(data).pdq_hash == image_fingerprint(data).pdq_hash


def test_pdq_near_duplicate_is_close_original_is_far() -> None:
    png = _structured_png()
    orig = image_fingerprint(png).pdq_hash
    near = image_fingerprint(_reencode_jpeg(png, quality=95)).pdq_hash
    far = image_fingerprint(_noise_png(seed=999)).pdq_hash
    assert orig is not None and near is not None and far is not None
    near_dist = pdq_hamming(orig, near)
    far_dist = pdq_hamming(orig, far)
    # A re-encode moves only a few bits; PDQ's canonical match threshold is ~90/256.
    assert near_dist < 40, near_dist
    assert far_dist > 90, far_dist
    assert near_dist < far_dist


# ── pHash ──────────────────────────────────────────────────────────────────────────────────────


def test_phash_present_and_well_formed() -> None:
    fp = image_fingerprint(_structured_png())
    assert fp.phash is not None
    assert len(fp.phash) == 16  # 64-bit hash → 16 hex chars
    int(fp.phash, 16)


def test_phash_near_duplicate_is_close_original_is_far() -> None:
    png = _structured_png()
    orig = image_fingerprint(png).phash
    near = image_fingerprint(_reencode_jpeg(png, quality=95)).phash
    far = image_fingerprint(_noise_png(seed=123)).phash
    assert orig is not None and near is not None and far is not None
    assert pdq_hamming(orig, near) < pdq_hamming(orig, far)


# ── pdq_hamming primitive ────────────────────────────────────────────────────────────────────────


def test_pdq_hamming_counts_bit_differences() -> None:
    assert pdq_hamming("00", "00") == 0
    assert pdq_hamming("00", "01") == 1
    assert pdq_hamming("00", "ff") == 8
    assert pdq_hamming("0f", "f0") == 8


def test_pdq_hamming_tolerates_prefix_case_and_whitespace() -> None:
    assert pdq_hamming("0xFF", " ff ") == 0
    assert pdq_hamming("0x00", "FF") == 8


def test_pdq_hamming_rejects_width_mismatch() -> None:
    with pytest.raises(ValueError, match="width mismatch"):
        pdq_hamming("ff", "ffff")  # pHash-width vs a longer string


def test_pdq_hamming_rejects_non_hex() -> None:
    with pytest.raises(ValueError, match="hex"):
        pdq_hamming("zz", "00")


# ── EXIF ─────────────────────────────────────────────────────────────────────────────────────────


def test_exif_extracted_when_present() -> None:
    fp = image_fingerprint(_jpeg_with_exif())
    assert fp.exif["capture_date"] == "2021:06:15 09:30:00"
    assert fp.exif["make"] == "OrbCam"
    assert fp.exif["x_resolution"] == pytest.approx(72.0)
    gps = fp.exif["gps"]
    assert gps["lat"] == pytest.approx(31.5)
    assert gps["lon"] == pytest.approx(74.2)


def test_exif_empty_for_metadata_free_image() -> None:
    # A freshly-synthesised PNG carries no EXIF — "too clean" is honestly represented as {}.
    fp = image_fingerprint(_structured_png())
    assert fp.exif == {}


def test_exif_is_json_serialisable() -> None:
    import json

    fp = image_fingerprint(_jpeg_with_exif())
    json.dumps(fp.exif)  # must not raise (IFDRational/tuples were coerced)


# ── model shape ────────────────────────────────────────────────────────────────────────────────


def test_fingerprint_is_strict_and_round_trips() -> None:
    fp = image_fingerprint(_structured_png())
    dumped = fp.model_dump()
    assert set(dumped) == {"sha256", "pdq_hash", "pdq_quality", "phash", "exif"}
    assert ImageFingerprint(**dumped) == fp
    with pytest.raises(Exception):  # noqa: B017,PT011 — extra field forbidden (strict model)
        ImageFingerprint(sha256="x", unexpected=1)
