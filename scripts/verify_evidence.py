"""Verify the captured evidence bundle without changing its contents."""
import hashlib
import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "docs" / "evidence"
manifest = json.loads((root / "reports" / "capture-manifest.json").read_text(encoding="utf-8"))
items = manifest["screenshots"]
desktop = [item for item in items if item["file"].startswith("screenshots/desktop/")]
mobile = [item for item in items if item["file"].startswith("screenshots/mobile/")]
assert len(desktop) == 27, f"Expected 27 desktop screenshots, found {len(desktop)}"
assert len(mobile) == 9, f"Expected 9 mobile screenshots, found {len(mobile)}"

for item in items:
    path = root / item["file"]
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG: {path}"
    width, height = struct.unpack(">II", data[16:24])
    assert width > 0 and height > 0, f"Invalid dimensions: {path}"
    assert hashlib.sha256(data).hexdigest() == item["sha256"], f"SHA mismatch: {path}"

assert not list((root / "videos").iterdir()), "Video directory must contain no valid evidence"
print(f"PASS: {len(desktop)} desktop PNG, {len(mobile)} mobile PNG; SHA-256 OK")
