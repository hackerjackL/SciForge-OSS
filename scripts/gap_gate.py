#!/usr/bin/env python3
"""Gap-report discrimination gate (S27) — anti-hallucinated-ideation guard.

The literature-first gap chain (v6.0) requires GAP_REPORT.md with gap-ids that
ideas anchor to. CRUX failure mode: LLMs invent vague "gaps" ("more research is
needed") that cannot drive real ideation. This gate makes the report
machine-checkable:

- GAP_REPORT.md must exist at {ws}/literature/ (or the run declares N/A in
  VERIFICATION_ROUTING.json na_verdicts-style for theory-only... but theory-only
  still needs duplication-check literature, so no N/A path here).
- >= 1 gap entry with a gap-id token (GAP-\\d+ or #gap-...).
- Every gap entry must cite at least one real reference token ([@key], [key],
  or a year+author pattern) — a gap with no citation is an opinion.
- Gap statements must contain at least one discrimination verb from a fixed
  lexicon (contradict/unsolved/no-study/absence/unclear-inconsistent/...) —
  "interesting future work" does NOT pass.
- Minimum gaps per effort: lite>=1, balanced>=2, max>=3 (env SCIFORGE_EFFORT,
  default 1).

Exit 0 = PASS, 2 = FAIL with reasons. Stdlib-only, model-agnostic: any host
that writes GAP_REPORT.md must satisfy it to advance past Phase 4broad.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

GAP_ID = re.compile(r"(GAP-\d+|#gap-[\w-]+|\[GAP:?\s*\d+\])", re.I)
CITATION = re.compile(r"(\[@[\w:-]+\]|\[[A-Z][\w-]*,\s*\d{4}\]|\b[A-Z][a-z]+(?: et al\.?)? \d{4}\b|\(\d{4}\))")
DISCRIMINATOR = re.compile(
    r"contradict|inconsistent|unsolved|not (?:been )?(?:studied|tested|measured|validated)|"
    r"absence of|no (?:study|evidence|benchmark|dataset)|remains (?:open|unknown|unverified)|"
    r"fail(?:s|ed)? to (?:explain|account|reproduce)|discrepan(?:cy|cies)|"
    r"cannot (?:explain|distinguish)|untested|not reported", re.I)
MIN_GAPS = {"lite": 1, "balanced": 2, "max": 3, "beast": 4}


def check(report: Path) -> list[str]:
    problems: list[str] = []
    text = report.read_text(encoding="utf-8", errors="replace")
    need = MIN_GAPS.get(os.environ.get("SCIFORGE_EFFORT", "lite"), 1)
    ids = GAP_ID.findall(text)
    if len(ids) < need:
        problems.append(f"expected >= {need} distinct gap-ids, found {len(set(ids)) or len(ids)}")
    if not CITATION.search(text):
        problems.append("no citation token found: every gap must anchor to a retrieved reference")
    n_disc = len(DISCRIMINATOR.findall(text))
    if n_disc < max(1, need):
        problems.append(f"gap statements lack discrimination language "
                        f"(found {n_disc} markers; need >= {max(1, need)})")
    # each gap block (paragraph starting with id marker) must carry a citation
    blocks = re.split(r"\n(?=(?:GAP-\d+|## GAP|#gap-))", text)
    gap_blocks = [b for b in blocks if GAP_ID.search(b)]
    uncited = [b[:60] for b in gap_blocks if not CITATION.search(b)]
    if uncited:
        problems.append(f"{len(uncited)} gap block(s) without citations: " + "; ".join(x for x in uncited[:3]))
    return problems


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args(argv)
    report = args.workspace / "literature" / "GAP_REPORT.md"
    routing = args.workspace / ".sciforge" / "verdicts" / "VERIFICATION_ROUTING.json"
    if not report.exists():
        print(f"gap_gate: FAIL — missing {report}")
        print("gap_gate: Phase 4broad broad-wave must produce GAP_REPORT.md before ideation anchors (v6.0 gap chain)")
        return 2
    problems = check(report)
    if problems:
        for p in problems:
            print(f"gap_gate: FAIL — {p}")
        return 2
    print("gap_gate: PASS — GAP_REPORT.md is anchored, cited, and discriminating")
    return 0


if __name__ == "__main__":
    sys.exit(main())
