"""Shared fixtures for the SciForge-OSS plotting-toolchain test suite.

Constraints honored here:
- stdlib + pytest + PIL only (no hypothesis in this environment, so the
  property-style tests in the suite use parametrize + seeded random).
- fully offline: no external tool is REQUIRED by any test; skipif marks
  for d2 / rsvg-convert / pdflatex are provided for optional end-to-end
  tests that exercise real binaries when they happen to be installed.

The modules under test live in scripts/plotting/ as flat modules (no
package), so that directory is placed on sys.path once at import time.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLOTTING_DIR = REPO_ROOT / "scripts" / "plotting"
if str(PLOTTING_DIR) not in sys.path:
    sys.path.insert(0, str(PLOTTING_DIR))

# ---------------------------------------------------------------------------
# skipif helpers for external tools (importable by the test modules)
# ---------------------------------------------------------------------------
requires_d2 = pytest.mark.skipif(
    shutil.which("d2") is None, reason="d2 is not installed")
requires_rsvg = pytest.mark.skipif(
    shutil.which("rsvg-convert") is None, reason="rsvg-convert is not installed")
requires_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None, reason="pdflatex is not installed")

# Fake but format-valid PDF bytes (magic is what the audit checks).
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def _minimal_svg(width: int = 1600, height: int = 900,
                 texts: tuple | None = None,
                 font_size: int = 26,
                 extra: str = "") -> str:
    """A minimal valid SVG document: viewBox, morandi-only colors, sane
    font sizes (>= Nature floor), approved font family."""
    if texts is None:
        texts = (("Encoder", 300, 370),)
    body = "\n".join(
        f'  <text x="{x}" y="{y}" font-size="{font_size}" '
        f'fill="#35322E">{label}</text>'
        for label, x, y in texts
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     width="{width}" height="{height}"
     font-family="Liberation Sans, sans-serif">
  <rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>
  <rect x="200" y="250" width="420" height="220" rx="8"
        fill="#EDE9E2" stroke="#665F57" stroke-width="2"/>
{body}
{extra}
</svg>
"""


@pytest.fixture
def make_svg():
    """Factory for minimal valid SVG document text (see _minimal_svg)."""
    return _minimal_svg


@pytest.fixture
def figure_dir(tmp_path):
    """Factory: create a figure directory populated with files.

    ``files`` maps filename -> str (written as UTF-8) or bytes.
    """
    def _make(files=None, name="fig"):
        d = tmp_path / name
        d.mkdir(parents=True, exist_ok=True)
        for fname, content in (files or {}).items():
            p = d / fname
            if isinstance(content, bytes):
                p.write_bytes(content)
            else:
                p.write_text(content, encoding="utf-8")
        return d
    return _make


@pytest.fixture
def valid_figure_dir(figure_dir, make_svg):
    """A fully valid minimal figure dir: fake-but-valid-magic output.pdf,
    output.svg with viewBox + morandi colors + sane fonts,
    latex_include.tex and a clean spec.d2."""
    return figure_dir(files={
        "output.pdf": PDF_BYTES,
        "output.svg": make_svg(),
        "latex_include.tex": "\\includegraphics{figures/fig/output.pdf}\n",
        "spec.d2": "encoder: Encoder\ndecoder: Decoder\nencoder -> decoder\n",
    })
