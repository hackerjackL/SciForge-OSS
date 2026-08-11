"""Tests for scripts/detect_device.py — domain-driven device profiling (v1.4.0)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import detect_device as dd

VALID_BACKENDS = {"cuda", "rocm", "npu", "mps", "cpu"}


def test_detect_returns_valid_profile():
    p = dd.detect()
    assert p["backend"] in VALID_BACKENDS
    assert p["schema_version"] == "1.0"
    assert "recommendation" in p and p["recommendation"]
    assert isinstance(p["torch"], dict) and "installed" in p["torch"]


def test_main_writes_out_file(tmp_path):
    out = tmp_path / "DEVICE.json"
    rc = dd.main(["--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["backend"] in VALID_BACKENDS
