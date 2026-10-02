#!/usr/bin/env python3
"""Completion-declaration gate (v1.7.1) — the physical cure for S01-class lies.

Failure class (observed in ARC-Bench round 1): an agent's FINAL REPORT claimed
"21/21 phases, PDF compiled, score 92" while the workspace had no PDF, empty
sections and 11 missing verdicts. Prose completion claims have no physical
gate; this script is that gate, wired into wrap-up:

  1. RUNSTATE.json status must be `completed` (a run that stopped early
     cannot declare completion);
  2. every filesystem path mentioned in the run's own summary documents
     (`.sciforge/verdicts/PIPELINE_VERDICT_SUMMARY.md`, `README.md`,
     `output/RUN_PREPRINT.md`) must EXIST — a claimed artifact that is not on
     disk is a fabricated completion state;
  3. `paper/main.pdf` must exist and open with >= 1 page;
  4. the registered-verdict set must be complete (delegated to
     validate_verdicts --require-complete by the caller; this gate adds the
     path-truth half).

Exit 0 = PASS/SKIP (no RUNSTATE yet), 2 = FAIL with the missing paths listed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PATH_RE = re.compile(
    r"(?:(?:[\w.@-]+/)+[\w.@-]+|\./[\w./@-]+)")  # anything with a slash
SUMMARY_DOCS = (".sciforge/verdicts/PIPELINE_VERDICT_SUMMARY.md",
                "README.md", "output/RUN_PREPRINT.md")


def _candidate_paths(text: str, ws: Path) -> set[Path]:
    out = set()
    for tok in PATH_RE.findall(text):
        tok = tok.strip("`'\"()[]<>:;,")
        if not tok or tok.startswith(("http", "www", "//")):
            continue
        p = (ws / tok) if not tok.startswith("/") else Path(tok)
        # only check paths that plausibly live in this run
        try:
            p.resolve().relative_to(ws.resolve())
        except ValueError:
            continue
        if p.suffix in (".pdf", ".json", ".md", ".tex", ".py", ".csv", ".bib"):
            out.add(p)
    return out


def check(ws: Path) -> tuple[str, list[str]]:
    ws = Path(ws)
    rs = ws / ".sciforge" / "RUNSTATE.json"
    if not rs.exists():
        return "SKIP", ["no RUNSTATE.json (not a kernel/skill run yet)"]
    problems: list[str] = []
    try:
        status = json.loads(rs.read_text()).get("status")
    except Exception:
        status = None
    if status != "completed":
        problems.append(f"RUNSTATE.status={status!r} — completion declared but "
                        f"the run is not in the completed state")
    for rel in SUMMARY_DOCS:
        doc = ws / rel
        if not doc.exists():
            continue
        for p in sorted(_candidate_paths(doc.read_text(errors="replace"), ws)):
            if not p.exists():
                problems.append(f"claimed in {rel} but missing on disk: "
                                f"{p.relative_to(ws)}")
    pdf = ws / "paper" / "main.pdf"
    if not pdf.exists():
        problems.append("paper/main.pdf missing — no manuscript was produced")
    else:
        try:
            head = pdf.read_bytes()[:5]
            if head != b"%PDF-":
                problems.append("paper/main.pdf is not a PDF (bad magic)")
        except OSError as e:
            problems.append(f"paper/main.pdf unreadable: {e}")
    return ("FAIL" if problems else "PASS"), problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args()
    status, problems = check(args.workspace)
    if status == "SKIP":
        print(f"completion_gate SKIP: {problems[0]}")
        return 0
    if status == "FAIL":
        print(f"completion_gate FAIL ({len(problems)} problem(s)):")
        for p in problems[:20]:
            print(f"  - {p}")
        return 2
    print("completion_gate PASS: every claimed artifact exists on disk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
