#!/usr/bin/env python3
"""Claim→node anchor gate (v1.7.2, XScientist ARA claim.schema adapted).

A manuscript assertion must remain linked to the experiment node and evidence
bytes that produced it. The gate verifies, at wrap-up:

  1. every claim in `.sciforge/audits/CLAIMS_FROM_RESULTS.md` that entered the
     paper (polarity positive, cited in main.tex) has an anchor in
     `.sciforge/nodes/CLAIM_ANCHORS.json` with resolved=true;
  2. every anchor's node exists in `.sciforge/nodes/NODES.json`;
  3. the node's outputs still hash-match (a result edited after anchoring
     invalidates the claim — the drift class the anchor exists to kill).

SKIP when the run produced no claims file or no nodes yet (theory-only runs
anchor to derivation nodes the same way once recorded).

Usage: python3 scripts/claim_anchor_gate.py <workspace>
Exit 0 = PASS/SKIP, 2 = FAIL.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "kernel") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge import nodes as nodes_mod  # noqa: E402


def _paper_claims(ws: Path) -> list[str]:
    """claim ids cited by the manuscript.

    Deliberately strict (adversarial-review fix): a bare ``\\bC\\d+\\b`` matched
    figure-panel letters ("C1 panel") and prose ("at C3 times") and would
    fail honest papers. Accepted citation forms only:
      \\claimref{C1}   (preferred machine form)
      (C1)            (parenthesized claim reference)
      claim C1 / Claim C1
    """
    ids = set()
    paper = ws / "paper"
    if not paper.exists():
        return []
    for f in paper.rglob("*.tex"):
        text = f.read_text(errors="replace")
        ids.update(re.findall(r"\\claimref\{(C\d+)\}", text))
        ids.update(re.findall(r"\((C\d+)\)", text))
        ids.update(re.findall(r"[Cc]laim (C\d+)", text))
    return sorted(ids)


def check(ws: Path) -> tuple[str, list[str]]:
    ws = Path(ws)
    claims_md = ws / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md"
    registry = nodes_mod.load(ws)
    if not claims_md.exists() or not registry["nodes"]:
        return "SKIP", ["no claims file or no nodes recorded yet"]
    anchors = {a.get("claim_id"): a for a in nodes_mod.load_anchors(ws)}
    problems = []
    cited = _paper_claims(ws)
    if cited and not anchors:
        problems.append("manuscript cites claims but CLAIM_ANCHORS.json is empty")
    for cid in cited:
        a = anchors.get(cid)
        if a is None:
            problems.append(f"claim {cid} cited in paper but not anchored to a node")
    problems += nodes_mod.verify_anchors(ws)
    return ("FAIL" if problems else "PASS"), problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args()
    status, problems = check(args.workspace)
    if status == "SKIP":
        print(f"claim_anchor SKIP: {problems[0] if problems else 'n/a'}")
        return 0
    if problems:
        print(f"claim_anchor FAIL ({len(problems)}):")
        for p in problems[:15]:
            print(f"  - {p}")
        return 2
    print("claim_anchor PASS: every cited claim anchored to a hash-stable node")
    return 0


if __name__ == "__main__":
    sys.exit(main())
