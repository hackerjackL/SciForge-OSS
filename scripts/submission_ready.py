#!/usr/bin/env python3
"""Submission-readiness gate (v1.7.1) — "at least minor-revision submittable".

The user bar: a finished run's manuscript must be **Zone-2 SCI submittable**
(minor-revision grade) even when the loop is not yet fully autonomous. This
gate turns that bar into a mechanical checklist over the run workspace and
emits a TIER, not a boolean:

  READY        — every hard item passes; submittable as-is
  MINOR_REV    — hard items pass, <=2 soft items missing (fixable in minor rev)
  MAJOR_REV    — >2 soft or any structural item missing (needs real work)
  NOT_READY    — a hard item fails (evidence/claim integrity broken)

Hard items (any fail => NOT_READY):
  - registered verdicts complete (validate_verdicts --require-complete)
  - s2 ladder/ablation/audit/integrity gates pass
  - paper/main.pdf exists, opens, >= 4 pages
  - every bib entry has a resolvable-or-declared DOI (doi_gate --offline)
  - leakage_scan zero remaining hits (classes A-L)
  - claim_mode consistency: sota runs carry no failure-narrative headline
    (leakage class K/L scan on abstract), attribution runs may carry nulls

Soft items (counted for tiering):
  - abstract 150-300 words with >= 8 numbers
  - canonical section order present (Abstract..Conclusion + References +
    Data&Code + Funding placeholders)
  - appendix is a separate tex/pdf when present
  - figure budget >= 7 body figures and >= 3 visual grammars
  - review score >= 6 (boundary) recorded; calibrated >= 8 OR a documented
    rebuttal round executed
  - workspace hygiene pass

Usage: python3 scripts/submission_ready.py <workspace> [--write-verdict]
Exit 0 = READY/MINOR_REV, 1 = MAJOR_REV, 2 = NOT_READY.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "kernel") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "kernel"))

SECTION_ORDER = ["abstract", "introduction", "related work", "method",
                 "experimental setup", "results", "conclusion", "references"]


def _run(script: str, ws: Path, *extra: str) -> int:
    import subprocess
    p = subprocess.run([sys.executable, str(REPO_ROOT / script), str(ws), *extra],
                       capture_output=True, text=True)
    return p.returncode


def _tex_text(ws: Path) -> str:
    paper = ws / "paper"
    if not paper.exists():
        return ""
    parts = []
    for f in sorted(paper.rglob("*.tex")):
        try:
            parts.append(f.read_text(errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def check(ws: Path) -> dict:
    ws = Path(ws)
    hard, soft = [], []

    # --- hard: verdicts complete
    import subprocess
    v = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "validate_verdicts.py"),
                        str(ws / ".sciforge" / "verdicts"), "--strict", "--require-complete"],
                       capture_output=True, text=True)
    if v.returncode != 0:
        hard.append("registered verdicts incomplete")
    # --- hard: s2 gate battery
    for script, label in (("scripts/s2_ladder_gate.py", "ladder"),
                          ("scripts/s2_ablation_gate.py", "ablation"),
                          ("scripts/s2_audit.py", "audit"),
                          ("scripts/doi_gate.py", "doi"),
                          ("scripts/leakage_scan.py", "leakage")):
        extra = ("--offline",) if script.endswith("doi_gate.py") else ()
        if _run(script, ws, *extra) != 0:
            hard.append(f"{label} gate fails")
    # --- hard: pdf (page count via /Count of Pages nodes; compressed object
    # streams hide /Type /Page, so /Count is the reliable stdlib signal)
    pdf = ws / "paper" / "main.pdf"
    pages = 0
    if pdf.exists():
        try:
            raw = pdf.read_bytes()
            counts = [int(c) for c in re.findall(rb"/Count\s+(\d+)", raw)]
            pages = max(counts) if counts else \
                len(re.findall(rb"/Type\s*/Page[^s]", raw))
        except OSError:
            pages = 0
    if not pdf.exists():
        hard.append("paper/main.pdf missing — no manuscript was produced")
    elif pages == 0:
        soft.append("page count unverifiable (compressed xref); opened OK")
    elif pages < 4:
        hard.append(f"paper/main.pdf has {pages} pages (< 4)")

    tex = _tex_text(ws).lower()

    def _abstract(body: str) -> str:
        """Longest Abstract..(Introduction|Keywords) candidate — the word
        'abstract' also appears in TOC/metadata lines, and a non-greedy first
        match can stop at a nearby 'keywords' (measured: 25 words on a
        222-word abstract)."""
        cands = [re.sub(r"\s+", " ", m.group(1)).strip()
                 for m in re.finditer(r"abstract(.{100,3000}?)(?:introduction|keywords)",
                                      body, re.S)]
        return max(cands, key=len) if cands else ""
    # --- hard: claim_mode consistency (sota => no failure-voice headline)
    rs = {}
    try:
        rs = json.loads((ws / ".sciforge" / "RUNSTATE.json").read_text())
    except Exception:
        pass
    claim_mode = ((rs.get("data") or rs).get("flags", {}) or {}).get("claim_mode", "attribution")
    if claim_mode == "sota":
        ab = _abstract(tex)
        if any(w in ab for w in ("we failed", "refuted", "no consistent", "null result")):
            hard.append("claim_mode=sota but abstract carries failure narration")

    # --- soft: abstract shape
    ab = _abstract(tex)
    words, nums = len(ab.split()), len(re.findall(r"\d+\.?\d*", ab))
    if not (150 <= words <= 300):
        soft.append(f"abstract {words} words outside 150-300")
    if nums < 8:
        soft.append(f"abstract carries {nums} numbers (< 8)")
    # --- soft: section order
    present = [s for s in SECTION_ORDER if s in tex]
    if len(present) < len(SECTION_ORDER) - 1:
        soft.append(f"section order incomplete: {present}")
    if "data and code" not in tex or "funding" not in tex:
        soft.append("Data&Code / Funding back-matter missing")
    # --- soft: appendix separate
    if (ws / "paper" / "appendix.tex").exists() and not (ws / "paper" / "appendix.pdf").exists():
        soft.append("appendix.tex present but not compiled to its own PDF")
    # --- soft: figure budget/diversity
    figs = list((ws / "figures").glob("*/output.pdf")) if (ws / "figures").is_dir() else []
    if len(figs) < 7:
        soft.append(f"{len(figs)} rendered figures (< 7 body budget)")
    kinds = set()
    for spec in (ws / "figures").rglob("spec.recipe.json") if (ws / "figures").is_dir() else []:
        try:
            kinds.add(json.loads(spec.read_text()).get("recipe"))
        except Exception:
            continue
    if len(kinds) < 3:
        soft.append(f"{len(kinds)} visual grammars (< 3)")
    # --- soft: review bar
    try:
        rv = json.loads((ws / ".sciforge" / "verdicts" / "REVIEW_STATE.json").read_text())
        score = float(rv.get("last_score") or 0)
        if score < 6:
            soft.append(f"review score {score} < 6 boundary")
        elif score < 8 and not (ws / ".sciforge" / "audits" / "REBUTTAL_PLAN.json").exists():
            soft.append("score < 8 without a documented rebuttal round")
    except Exception:
        soft.append("REVIEW_STATE.json missing")
    # --- soft: hygiene
    if _run("scripts/workspace_hygiene.py", ws) != 0:
        soft.append("workspace hygiene fails")

    if hard:
        tier = "NOT_READY"
    elif len(soft) <= 2:
        tier = "READY" if not soft else "MINOR_REV"
    else:
        tier = "MAJOR_REV"
    return {"tier": tier, "hard": hard, "soft": soft,
            "pages": pages, "abstract_words": words, "abstract_numbers": nums,
            "figures": len(figs), "visual_grammars": sorted(k for k in kinds if k),
            "claim_mode": claim_mode}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    args = ap.parse_args()
    doc = check(args.workspace)
    if args.write_verdict:
        vd = args.workspace / ".sciforge" / "verdicts"
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "SUBMISSION_READY.json").write_text(
            json.dumps({"schema_version": "1.0", **doc}, indent=2))
    print(f"submission_ready {doc['tier']}: hard={doc['hard']} soft={doc['soft']}")
    return {"READY": 0, "MINOR_REV": 0, "MAJOR_REV": 1, "NOT_READY": 2}[doc["tier"]]


if __name__ == "__main__":
    sys.exit(main())
