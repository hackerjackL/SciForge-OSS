"""Tests for scripts/sciforge_audit.py — the v1.5.0 single-entry mechanical audit."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import sciforge_audit as sa

PDF = b"%PDF-1.4\n%%EOF\n"
GOOD_TEX = ("\\documentclass{elsarticle}\\usepackage[section]{placeins}"
            "\\usepackage{float}\\renewcommand{\\topfraction}{0.85}"
            "\\renewcommand{\\floatpagefraction}{0.75}"
            "\\begin{document}\\begin{figure}"
            "\\input{figures/fig_a/latex_include}\\end{figure}\\end{document}")


def _ws(tmp_path, tex=GOOD_TEX, verdicts=True):
    ws = tmp_path / "Q"
    paper = ws / "paper"
    fig = ws / "figures" / "fig_a"
    paper.mkdir(parents=True)
    fig.mkdir(parents=True)
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    (fig / "output.pdf").write_bytes(PDF)
    (fig / "figure_audit.json").write_text('{"verdict":"PASS"}', encoding="utf-8")
    (fig / "latex_include.tex").write_text(
        "\\includegraphics{figures/fig_a/output.pdf}\n", encoding="utf-8")
    if verdicts:
        (ws / ".sciforge" / "verdicts").mkdir(parents=True)
    return ws


def test_template_check_markers():
    ws = _ws_tmp = None
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        good = p / "good"; good.mkdir(); (good / "main.tex").write_text(GOOD_TEX)
        bad = p / "bad"; bad.mkdir()
        (bad / "main.tex").write_text("\\begin{document}x\\end{document}")
        assert sa.template_check(good) == []
        assert sa.template_check(bad) != []


def test_audit_fails_when_verdicts_absent(tmp_path):
    ws = _ws(tmp_path, verdicts=False)
    assert sa.main([str(ws)]) == 2  # figure+template ok but audit machinery absent


def test_audit_verdict_gate_still_enforced(tmp_path):
    # empty verdicts dir => require-complete FAILs => overall FAIL
    ws = _ws(tmp_path, verdicts=True)
    assert sa.main([str(ws)]) == 2
