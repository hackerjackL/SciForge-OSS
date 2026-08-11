"""v1.4.0 hardening-round guarantees (float control, root deps, black ink).

These pin the structural fixes from the second eval-feedback round:
- the unified elsarticle template ships float-control (placeins/float/fractions)
  so figures stay in their section and never eat a whole page;
- render_figure emits [!htbp] (not the old free [htbp]);
- the repo root carries a pip-installable requirements.txt;
- the design system's text ink is pure black on a pure white ground.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import render_figure as rf
import sciforge_style as st

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (REPO_ROOT / "skills" / "support" / "paper-writing"
            / "templates" / "default" / "main.tex")


def test_template_ships_float_control():
    tex = TEMPLATE.read_text(encoding="utf-8")
    assert "placeins" in tex, "template must load placeins (per-section barriers)"
    assert "\\usepackage{float}" in tex
    for frac in ("topfraction", "bottomfraction", "textfraction",
                 "floatpagefraction"):
        assert frac in tex, f"template must tune {frac}"


def test_write_latex_include_uses_strong_float_specifier(tmp_path):
    rf.write_latex_include(tmp_path, "output", None, "fig_x")
    out = (tmp_path / "latex_include.tex").read_text(encoding="utf-8")
    assert "[!htbp]" in out and "[htbp]" not in out.replace("[!htbp]", "")


def test_write_latex_include_composite_uses_strong_float_specifier(tmp_path):
    rf.write_latex_include(tmp_path, "output", "cap", "fig_c", composite=True)
    out = (tmp_path / "latex_include.tex").read_text(encoding="utf-8")
    assert "[!htbp]" in out


def test_root_requirements_exists_and_parses():
    req = REPO_ROOT / "requirements.txt"
    assert req.is_file(), "repo root must ship requirements.txt"
    lines = [ln.strip() for ln in req.read_text().splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    assert any(ln.lower().startswith("matplotlib") for ln in lines)
    assert any(ln.lower().startswith("numpy") for ln in lines)


def test_text_ink_is_black_and_ground_white():
    assert st.INK_TEXT == "#000000"
    assert st.GROUND == "#FFFFFF"
    assert st.TOKENS["ink"] == "#000000"


def test_experience_replay_contract_present():
    p = REPO_ROOT / "skills" / "shared-references" / "experience-replay-contract.md"
    assert p.is_file()
    assert "LESSONS.json" in p.read_text(encoding="utf-8")
