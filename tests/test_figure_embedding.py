"""Tests for scripts/check_figure_embedding.py — the v1.4.0 figure-embedding gate.

The gate must catch the "figures rendered but never inserted into the
manuscript" failure regardless of which model assembled the paper.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_figure_embedding as cfe


def _mk(tmp_path, main_tex, figures):
    paper = tmp_path / "paper"
    fig = tmp_path / "figures"
    paper.mkdir()
    fig.mkdir()
    (paper / "main.tex").write_text(main_tex, encoding="utf-8")
    for name in figures:
        (fig / name).write_bytes(b"%PDF-1.4\n%%EOF\n")
    return paper, fig


def test_dropped_figures_fail(tmp_path):
    paper, fig = _mk(tmp_path, "\\begin{document}no figures\\end{document}",
                     ["fig_a.pdf", "fig_b.pdf"])
    assert cfe.main([str(paper)]) == 2


def test_all_figures_embedded_pass(tmp_path):
    tex = ("\\begin{document}\n"
           "\\begin{figure}\\includegraphics{figures/fig_a.pdf}\\end{figure}\n"
           "\\begin{figure}\\includegraphics{figures/fig_b.pdf}\\end{figure}\n"
           "\\end{document}")
    paper, fig = _mk(tmp_path, tex, ["fig_a.pdf", "fig_b.pdf"])
    assert cfe.main([str(paper)]) == 0


def test_partial_embedding_fails(tmp_path):
    tex = ("\\begin{document}\n"
           "\\begin{figure}\\includegraphics{figures/fig_a.pdf}\\end{figure}\n"
           "\\end{document}")
    paper, fig = _mk(tmp_path, tex, ["fig_a.pdf", "fig_b.pdf"])
    assert cfe.main([str(paper)]) == 2


def test_min_figures_enforced(tmp_path):
    tex = ("\\begin{document}\n"
           "\\begin{figure}\\includegraphics{figures/fig_a.pdf}\\end{figure}\n"
           "\\end{document}")
    paper, fig = _mk(tmp_path, tex, ["fig_a.pdf"])
    assert cfe.main([str(paper), "--min-figures", "2"]) == 2


def test_nested_output_pdf_referenced_via_dir(tmp_path):
    paper = tmp_path / "paper"
    figdir = tmp_path / "figures" / "fig_x"
    paper.mkdir()
    figdir.mkdir(parents=True)
    (figdir / "output.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    tex = ("\\begin{document}\n"
           "\\begin{figure}\\input{figures/fig_x/latex_include}\\end{figure}\n"
           "\\end{document}")
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    assert cfe.main([str(paper)]) == 0
