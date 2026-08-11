"""Round-5 hard gates (v1.4.0): renderer-produced figures + verdict completeness.

A. check_figure_embedding --require-renderer: figures must come from the unified
   renderer (per-id dir with figure_audit.json + latex_include.tex); flat
   hand-written pdfs or dirs missing the renderer artifacts FAIL.
B. validate_verdicts --require-complete: a run may not complete with registered
   verdicts still PENDING (audit machinery skipped).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
for p in (str(SCRIPTS), str(SCRIPTS / "plotting")):
    if p not in sys.path:
        sys.path.insert(0, p)

import check_figure_embedding as cfe
import validate_verdicts as vv

PDF = b"%PDF-1.4\n%%EOF\n"


def _paper(tmp_path, tex):
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    return paper


def test_require_renderer_rejects_flat_figures(tmp_path):
    paper = _paper(tmp_path, "\\begin{document}\\begin{figure}"
                   "\\includegraphics{figures/fig_a.pdf}\\end{figure}\\end{document}")
    fig = tmp_path / "figures"
    fig.mkdir()
    (fig / "fig_a.pdf").write_bytes(PDF)
    assert cfe.main([str(paper), "--require-renderer"]) == 2


def test_require_renderer_accepts_renderer_dir(tmp_path):
    paper = _paper(tmp_path, "\\begin{document}\\begin{figure}"
                   "\\input{figures/fig_a/latex_include}\\end{figure}\\end{document}")
    d = tmp_path / "figures" / "fig_a"
    d.mkdir(parents=True)
    (d / "output.pdf").write_bytes(PDF)
    (d / "figure_audit.json").write_text('{"verdict":"PASS"}', encoding="utf-8")
    (d / "latex_include.tex").write_text(
        "\\includegraphics{figures/fig_a/output.pdf}\n", encoding="utf-8")
    assert cfe.main([str(paper), "--require-renderer"]) == 0


def test_require_renderer_rejects_dir_missing_audit(tmp_path):
    paper = _paper(tmp_path, "\\begin{document}\\begin{figure}"
                   "\\input{figures/fig_a/latex_include}\\end{figure}\\end{document}")
    d = tmp_path / "figures" / "fig_a"
    d.mkdir(parents=True)
    (d / "output.pdf").write_bytes(PDF)
    (d / "latex_include.tex").write_text("x\n", encoding="utf-8")  # no audit
    assert cfe.main([str(paper), "--require-renderer"]) == 2


def test_without_flag_flat_figures_still_pass_if_embedded(tmp_path):
    # backward compat: the embedding check alone does not police provenance
    paper = _paper(tmp_path, "\\begin{document}\\begin{figure}"
                   "\\includegraphics{figures/fig_a.pdf}\\end{figure}\\end{document}")
    fig = tmp_path / "figures"
    fig.mkdir()
    (fig / "fig_a.pdf").write_bytes(PDF)
    assert cfe.main([str(paper)]) == 0


def test_validate_verdicts_require_complete(tmp_path):
    vd = tmp_path / "verdicts"
    vd.mkdir()
    # empty dir: everything registered is PENDING
    assert vv.main([str(vd)]) == 0                      # default: pending ok
    assert vv.main([str(vd), "--require-complete"]) == 1  # wrap-up: incomplete FAIL
