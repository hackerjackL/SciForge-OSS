#!/usr/bin/env python3
"""Figure presentation gate (v1.7.1) — Nature-grade presentation rules.

Three mechanical checks the user mandate made load-bearing (observed defects
in two ARC-Bench generations: figures floating far from their citation,
raster previews embedded in the body, and five bar-charts in a row):

  1. figures-follow-text — every figure's FIRST \\ref/\\Cref in the manuscript
     source must appear BEFORE the figure environment that renders it, and
     in the same or an earlier section (a figure cited only in the appendix
     while floating in the body is a placement bug).
  2. vector-only — the body must embed renderer-produced vector output
     (\\input{figures/<id>/latex_include.tex} or \\includegraphics{*.pdf});
     any \\includegraphics of .png/.jpg/.jpeg in the BODY is FAIL (raster
     previews are audit-only artifacts).
  3. type diversity — the run's figures must span >= 3 distinct recipe kinds
     (bar-grouped / line-comparison / scatter-fit / heatmap / hist-dist /
     forest-plot / method-d2 …). A paper of five identical bar charts is the
     "ugly basic figure" failure class.

Usage: python3 scripts/figure_style_gate.py <workspace>
Exit 0 = PASS/SKIP (no paper yet), 2 = FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MIN_RECIPE_KINDS = 3
RASTER_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\.(?:png|jpg|jpeg|gif)\}",
                       re.I)
FIG_ENV_RE = re.compile(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", re.S)
REF_RE = re.compile(r"\\(?:C?ref|autoref)\{([^}]+)\}")


def _tex_sources(ws: Path) -> list[Path]:
    paper = ws / "paper"
    if not paper.exists():
        return []
    out = [p for p in sorted(paper.rglob("*.tex")) if "appendix" not in p.name]
    return out


def check_placement(sources: list[Path]) -> list[str]:
    problems = []
    for src in sources:
        text = src.read_text(errors="replace")
        # label -> position of first reference and of the figure env holding it
        labels = {}
        for m in re.finditer(r"\\label\{(fig:[^}]+)\}", text):
            labels[m.group(1)] = {"label_at": m.start(), "first_ref": None}
        for m in REF_RE.finditer(text):
            lab = m.group(1)
            if lab in labels and labels[lab]["first_ref"] is None:
                labels[lab]["first_ref"] = m.start()
        for lab, pos in labels.items():
            if pos["first_ref"] is None:
                problems.append(f"{src.name}: figure '{lab}' never referenced in text")
            elif pos["first_ref"] > pos["label_at"]:
                problems.append(
                    f"{src.name}: figure '{lab}' appears BEFORE its first citation "
                    f"(figures must follow the text that references them)")
    return problems


def check_vector(sources: list[Path]) -> list[str]:
    problems = []
    for src in sources:
        text = src.read_text(errors="replace")
        for m in RASTER_RE.finditer(text):
            problems.append(f"{src.name}: raster embed {m.group(0)[:80]} — "
                            f"body figures must be vector (renderer PDF)")
    return problems


def check_diversity(ws: Path) -> list[str]:
    kinds = set()
    figs = ws / "figures"
    if not figs.is_dir():
        return []
    for spec in list(figs.rglob("spec.recipe.json")) + list(figs.rglob("*.method.json")):
        try:
            d = json.loads(spec.read_text())
        except Exception:
            continue
        kinds.add(d.get("recipe") or "method-d2")
    for d in sorted(figs.iterdir()):
        if d.is_dir() and (d / "output.pdf").exists() and not (d / "spec.recipe.json").exists() \
           and not list(d.glob("*.method.json")):
            kinds.add("handwritten-svg")
    if len(kinds) < MIN_RECIPE_KINDS:
        return [f"figure type diversity = {len(kinds)} ({sorted(kinds)}) < "
                f"{MIN_RECIPE_KINDS} — vary the visual grammar (bars+lines+scatter/"
                f"heatmap/forest/method diagram), a paper of identical bar charts "
                f"is the basic-figure failure class"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args()
    sources = _tex_sources(args.workspace)
    if not sources:
        print("figure_style SKIP: no manuscript yet")
        return 0
    problems = (check_placement(sources) + check_vector(sources)
                + check_diversity(args.workspace))
    if problems:
        print(f"figure_style FAIL ({len(problems)} problem(s)):")
        for p in problems[:15]:
            print(f"  - {p}")
        return 2
    print("figure_style PASS: placement follows text, vector-only, diverse types")
    return 0


if __name__ == "__main__":
    sys.exit(main())
