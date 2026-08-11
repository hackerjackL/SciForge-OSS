#!/usr/bin/env python3
"""Deterministic figure-embedding gate (v1.4.0 hardening, discipline-agnostic).

Cures the "figures were rendered but never inserted into the manuscript"
failure: a model can generate N vector figures and still ship a paper with
zero \\begin{figure} environments.  This tool makes that impossible to miss by
mechanically cross-checking the manuscript against the figures directory.

Checks (FAIL => exit 2, so /paper-compile can refuse to compile):
  1. the manuscript contains at least --min-figures figure environments;
  2. every figure PDF on disk (figures/*.pdf or figures/<id>/output.pdf) is
     actually referenced by an \\includegraphics / \\input in main.tex or its
     \\input'ed section files.

Usage:
  python scripts/check_figure_embedding.py <paper_dir> \
         [--figures-dir <dir>] [--min-figures N]

<paper_dir> must contain main.tex (and optionally sections/*.tex).  The figures
directory defaults to <paper_dir>/../figures (the canonical workspace layout).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _tex_files(paper: Path) -> list[Path]:
    files = [paper / "main.tex"]
    sec = paper / "sections"
    if sec.is_dir():
        files += sorted(sec.glob("*.tex"))
    return [f for f in files if f.is_file()]


def _read(f: Path) -> str:
    return f.read_text(encoding="utf-8", errors="replace")


def collect_figure_refs(tex_files: list[Path]) -> set[str]:
    """Tokens that identify which figures the manuscript embeds."""
    tokens: set[str] = set()
    for tf in tex_files:
        t = _read(tf)
        for m in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", t):
            tokens.add(m)
            tokens.add(Path(m).name)
            tokens.add(Path(m).stem)
            # figures/<id>/output.pdf -> <id> (skip the bare "figures" root)
            if Path(m).parent.name not in ("", ".", "figures"):
                tokens.add(Path(m).parent.name)
        for m in re.findall(r"\\input\{([^}]*?)\}", t):
            if "figure" in m.lower() or "fig" in m.lower():
                tokens.add(m)
                tokens.add(Path(m).name)
                tokens.add(Path(m).stem)
                if Path(m).parent.name not in ("", ".", "figures"):
                    tokens.add(Path(m).parent.name)
    return tokens


def collect_figure_pdfs(fig: Path) -> list[Path]:
    if not fig.is_dir():
        return []
    return sorted(fig.rglob("*.pdf"))


def _referenced(pdf: Path, fig: Path, tokens: set[str]) -> bool:
    rel = pdf.relative_to(fig)
    cands = {pdf.name, pdf.stem, pdf.parent.name, str(rel), str(rel.with_suffix(""))}
    # a flat figures/foo.pdf is referenced if its stem/dir appears; a nested
    # figures/<id>/output.pdf is referenced if <id> or its latex_include is.
    return bool(cands & tokens)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper_dir", type=Path)
    ap.add_argument("--figures-dir", type=Path, default=None)
    ap.add_argument("--min-figures", type=int, default=1)
    args = ap.parse_args(argv)

    paper = args.paper_dir
    fig = args.figures_dir or (paper.parent / "figures")
    tex_files = _tex_files(paper)
    if not (paper / "main.tex").is_file():
        print(f"FIGURE-EMBEDDING FAIL: no main.tex in {paper}")
        return 2

    n_envs = sum(len(re.findall(r"\\begin\{figure\}", _read(f))) for f in tex_files)
    tokens = collect_figure_refs(tex_files)
    pdfs = collect_figure_pdfs(fig)
    missing = [str(p.relative_to(fig)) for p in pdfs
               if not _referenced(p, fig, tokens)]

    problems = []
    if n_envs < args.min_figures:
        problems.append(f"manuscript has {n_envs} figure environment(s) "
                        f"(< --min-figures {args.min_figures})")
    if missing:
        problems.append(f"figure PDF(s) on disk never embedded in the "
                        f"manuscript: {missing}")

    if problems:
        print("FIGURE-EMBEDDING FAIL")
        for p in problems:
            print("  -", p)
        return 2
    print(f"FIGURE-EMBEDDING PASS ({n_envs} figure environment(s); "
          f"{len(pdfs)} figure PDF(s), all referenced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
