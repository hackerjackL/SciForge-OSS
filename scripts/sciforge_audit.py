#!/usr/bin/env python3
"""SciForge single-entry mechanical audit (v1.5.0) — condense the prose chain.

Long Markdown chains drift and hallucinate even at 1M context; the *verifiable*
part of the pipeline should therefore be ONE tool call that returns a hard
verdict, not N paragraphs the model has to interpret.  This CLI aggregates the
existing mechanical gates and emits one summary JSON + exit code:

  1. figure-embedding + renderer-produced  (check_figure_embedding.py --require-renderer)
  2. registered-verdict completeness       (validate_verdicts.py --strict --require-complete)
  3. LaTeX float-control template markers  (placeins/float fractions present)

Usage:
  python scripts/sciforge_audit.py <workspace> [--min-figures N]

<workspace> is the {problem_id}/ dir (contains paper/, figures/, .sciforge/verdicts/).
Exit 0 = all mechanical gates pass; 2 = at least one gate FAILed (do not compile/complete).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_figure_embedding as cfe
import validate_verdicts as vv

FLOAT_MARKERS = ("placeins", "floatpagefraction", "topfraction")


def template_check(paper: Path) -> list[str]:
    main = paper / "main.tex"
    if not main.is_file():
        return ["no paper/main.tex"]
    t = main.read_text(encoding="utf-8", errors="replace")
    missing = [m for m in FLOAT_MARKERS if m not in t]
    problems = []
    if missing:
        problems.append("main.tex missing float-control markers %s "
                        "(unified template not used; figures may drift/float-page)" % missing)
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--min-figures", type=int, default=2)
    args = ap.parse_args(argv)

    ws = args.workspace
    paper = ws / "paper"
    verdicts = ws / ".sciforge" / "verdicts"

    fig_rc = cfe.main([str(paper), "--min-figures", str(args.min_figures),
                       "--require-renderer"])
    val_rc = 0
    if verdicts.is_dir():
        val_rc = vv.main([str(verdicts), "--strict", "--require-complete"])
    else:
        val_rc = 2  # no verdicts dir at all => audit machinery absent
    tmpl = template_check(paper)

    ok = (fig_rc == 0 and val_rc == 0 and not tmpl)
    summary = {
        "gate": "sciforge_audit",
        "schema_version": "1.0",
        "figure_embedding": "PASS" if fig_rc == 0 else "FAIL",
        "verdict_completeness": "PASS" if val_rc == 0 else "FAIL",
        "template_float_control": "PASS" if not tmpl else "FAIL",
        "template_problems": tmpl,
        "overall": "PASS" if ok else "FAIL",
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
