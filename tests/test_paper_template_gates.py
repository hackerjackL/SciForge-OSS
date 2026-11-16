"""Regressions from the first real end-to-end paper (S01, v1.8.0).

Phases 12-16 had only ever run against the fixture. Producing an actual 15-page
PDF from real experimental data exposed three defects that a fixture cannot
show, because the fixture has no manuscript and no renderer-produced figures.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

TEMPLATE_DIR = REPO / "skills" / "support" / "paper-writing" / "templates" / "default"


# ---------------------------------------------------------------------------
# 1. the shipped template must not leak the framework brand into a manuscript
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["main.tex", "math_commands.tex"])
def test_template_has_no_brand_leak(name):
    """leakage_scan class I flags the framework name anywhere in the paper
    tree. The template itself carried it in a comment, so EVERY paper produced
    from it failed the leak gate before the author wrote a single word."""
    text = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    assert not re.search(r"sciforge", text, re.I), f"{name} leaks the framework name"


def test_template_declares_lmodern():
    """Without lmodern, elsarticle + Computer Modern emits ten font-shape
    substitution warnings on every compile — measured on a minimal frontmatter
    with no math at all — making the zero-warning requirement unreachable."""
    text = (TEMPLATE_DIR / "main.tex").read_text(encoding="utf-8")
    assert "\\usepackage{lmodern}" in text


def test_template_strips_corref_from_pdf_strings():
    """elsarticle's \\corref/\\cnotenum are typesetting marks; hyperref warns
    'Token not allowed in a PDF string' for each unless they are disabled in
    the PDF-string context."""
    text = (TEMPLATE_DIR / "main.tex").read_text(encoding="utf-8")
    assert "\\pdfstringdefDisableCommands" in text
    assert "\\def\\corref" in text


# ---------------------------------------------------------------------------
# 2. figure embedding must follow the renderer's \input chain
# ---------------------------------------------------------------------------
def _paper_with_input_chain(tmp_path: Path) -> Path:
    """Reproduce the canonical layout: the renderer writes the figure
    environment into figures/<id>/latex_include.tex and a section \\inputs it."""
    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True)
    fig = tmp_path / "figures" / "fig_a"
    fig.mkdir(parents=True)
    (fig / "output.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (fig / "figure_audit.json").write_text(json.dumps({"verdict": "PASS"}))
    (fig / "latex_include.tex").write_text(
        "\\begin{figure}[!htbp]\n\\centering\n"
        "\\includegraphics[width=0.9\\textwidth]{figures/fig_a/output.pdf}\n"
        "\\caption{A real figure.}\n\\label{fig:a}\n\\end{figure}\n")
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "\\input{sections/1_body}\n\\end{document}\n")
    (paper / "sections" / "1_body.tex").write_text(
        "See Figure~\\ref{fig:a}.\n\\input{../figures/fig_a/latex_include.tex}\n")
    return paper


def test_figure_embedding_follows_nested_input(tmp_path):
    """The gate stopped at sections/*.tex, so it counted zero figure
    environments for a paper that embedded a figure through the renderer's own
    latex_include.tex — contradicting the project's only legal figure channel."""
    import check_figure_embedding as cfe

    paper = _paper_with_input_chain(tmp_path)
    files = cfe._tex_files(paper)
    names = {f.name for f in files}
    assert "latex_include.tex" in names, names
    refs = cfe.collect_figure_refs(files)
    assert "fig_a" in refs or "output" in refs, refs


def test_figure_embedding_gate_passes_on_nested_input(tmp_path):
    paper = _paper_with_input_chain(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_figure_embedding.py"),
         str(paper), "--require-renderer"],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 figure environment" in proc.stdout


def test_figure_embedding_still_fails_when_figure_unreferenced(tmp_path):
    """Following \\input must not weaken the gate: a figure on disk that the
    manuscript never pulls in is still a violation."""
    paper = _paper_with_input_chain(tmp_path)
    (paper / "sections" / "1_body.tex").write_text("No figures here.\n")
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_figure_embedding.py"),
         str(paper), "--require-renderer"],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_input_cycle_does_not_hang(tmp_path):
    paper = tmp_path / "paper"
    (paper / "sections").mkdir(parents=True)
    (paper / "main.tex").write_text("\\input{sections/a}\n")
    (paper / "sections" / "a.tex").write_text("\\input{b}\n")
    (paper / "sections" / "b.tex").write_text("\\input{a}\n")
    import check_figure_embedding as cfe
    files = cfe._tex_files(paper)
    assert len(files) == 3          # terminates, each file visited once


# ---------------------------------------------------------------------------
# 3. no invalid escape sequences in shipped scripts
# ---------------------------------------------------------------------------
def test_shipped_scripts_have_no_syntax_warnings():
    """citation_support.py's docstring contained a bare \\cite, which Python
    reports as SyntaxWarning and will reject in a future release."""
    import py_compile
    import tempfile

    bad = []
    targets = list((REPO / "scripts").rglob("*.py")) + \
              list((REPO / "kernel").rglob("*.py"))
    with tempfile.TemporaryDirectory() as td:
        for p in targets:
            try:
                py_compile.compile(str(p), cfile=str(Path(td) / "x.pyc"),
                                   doraise=True)
            except py_compile.PyCompileError as exc:
                if "escape" in str(exc):
                    bad.append(str(p.relative_to(REPO)))
    assert not bad, bad

# ---------------------------------------------------------------------------
# 4. submission_ready must not fail on its own telemetry or on modern PDFs
# ---------------------------------------------------------------------------
def test_submission_ready_quarantines_its_own_telemetry(tmp_path, monkeypatch):
    """DOI_GATE.json / SUBMISSION_READY.json are unregistered telemetry.
    validate_verdicts --strict reports them as WARN, so the gate failed its own
    completeness check on files it had just written. The kernel already
    quarantines them; this gate must too, and must put them back.

    Observed through validate_verdicts' own view of the directory rather than by
    patching subprocess, which the page-count probe also uses.
    """
    import submission_ready as sr

    vd = tmp_path / ".sciforge" / "verdicts"
    vd.mkdir(parents=True)
    for name in ("DOI_GATE.json", "SUBMISSION_READY.json"):
        (vd / name).write_text('{"tier": "READY"}')

    seen = {}
    real_run = sr.subprocess.run

    def spy(cmd, *a, **kw):
        if any("validate_verdicts.py" in str(c) for c in cmd):
            seen["at_validation"] = sorted(q.name for q in vd.glob("*.json"))
            class _P:
                returncode = 0
                stdout = ""
                stderr = ""
            return _P()
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(sr.subprocess, "run", spy)
    sr.check(tmp_path, offline=True)
    assert seen.get("at_validation") == [], seen
    assert (vd / "DOI_GATE.json").is_file(), "telemetry must be restored"
    assert (vd / "SUBMISSION_READY.json").is_file(), "telemetry must be restored"


def test_method_parity_ignores_matrix_and_config_labels():
    """group_baseline_t / budget_scale are experiment-matrix row ids and config
    keys, not claims that machinery exists. Counting them dropped S01's parity
    to 0.70 and failed an audit whose every real operation was implemented."""
    sys.path.insert(0, str(REPO / "kernel"))
    from sciforge.s2 import audit

    text = ("| Baseline | group_baseline_t | control | src/run.py (t_mean) |\n"
            "| Ablation | group_ablation_bca | BCa | src/run.py |\n"
            "budget_scale: **lite**\n"
            "We implement `percentile_bootstrap` and `trimmed_mean`.\n")
    toks = audit.claimed_tokens(text)
    assert "percentile_bootstrap" in toks and "trimmed_mean" in toks
    for bad in ("group_baseline_t", "group_ablation_bca", "budget_scale"):
        assert bad not in toks, toks


def test_page_count_reads_compressed_xref_pdf(tmp_path):
    """Modern pdflatex writes /ObjStm object streams: neither /Count nor
    /Type /Page appears in the raw bytes. pdfinfo reads it fine, so the gate
    must ask it rather than reporting 'page count unverifiable'."""
    import shutil
    import submission_ready as sr

    if not shutil.which("pdfinfo") or not shutil.which("pdflatex"):
        pytest.skip("pdf toolchain unavailable")
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(
        "\\documentclass{article}\\usepackage{lmodern}\n"
        "\\begin{document}\n" + "\\newpage\n".join(["page"] * 5) +
        "\\end{document}\n")
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "main.tex"],
                   cwd=str(paper), capture_output=True, timeout=180)
    pdf = paper / "main.pdf"
    if not pdf.is_file():
        pytest.skip("pdflatex could not produce a PDF here")
    raw = pdf.read_bytes()
    if b"/ObjStm" not in raw:
        pytest.skip("this pdflatex did not emit object streams")
    assert not re.findall(rb"/Count\s+(\d+)", raw)
    doc = sr.check(tmp_path, offline=True)
    assert doc["pages"] >= 4, doc.get("pages")
