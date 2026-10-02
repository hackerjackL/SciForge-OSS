#!/usr/bin/env python3
"""Run-workspace hygiene gate (v1.7.1) — a run must read like a GitHub repo.

Two rounds of ARC-Bench evaluation showed agents leaking cwd-relative junk
into run roots and repo roots: stray `compile_attempt*.log`, `texput.log`,
top-level `logs/`, ad-hoc `*.json` dumps, `__pycache__` inside src/, empty
skeleton dirs left behind. A human opening a finished run should see a
coherent repository, not a workshop floor.

Checks (against a run workspace):
  1. no stray top-level logs (*.log outside paper/ logs/ output/ .sciforge/)
  2. no stray top-level json/txt dumps outside their canonical homes
     (canonical: results.json, AGENT_DOC.md, PROBLEM.md, README.md, …)
  3. no __pycache__ / .pytest_cache / .DS_Store anywhere in the run
  4. no empty directories (skeleton leftovers)
  5. a run README index exists (kernel writes it at phase 16; this gate
     verifies) listing the deliverables a human opens first

Exit 0 = PASS (or SKIP when the workspace has no .sciforge/ yet),
2 = FAIL with the offending paths listed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

CANONICAL_TOP = {
    "PROBLEM.md", "AGENT_DOC.md", "README.md", "results.json", "LESSONS.json",
    "RUN_NOTES.md", "briefing.md", "math_commands.tex",
}
CANONICAL_TOP_DIRS = {
    "src", "experiments", "figures", "paper", "methods", "literature",
    "derivations", "output", "results", "tables", "submission", "report",
    "bench", "logs", "supplementary", "scratch", ".sciforge",
    # output-protocol.md canonical stage dirs (visible research trail)
    "refine-logs", "data", "data_analysis", "intake",
}
JUNK_NAMES = {".DS_Store", ".pytest_cache", "texput.log"}


def check(ws: Path) -> list[str]:
    ws = Path(ws)
    if not (ws / ".sciforge").exists():
        return []  # SKIP: not a run workspace yet
    problems: list[str] = []

    # 1+2 stray top-level files
    for p in sorted(ws.iterdir()):
        if p.name.startswith(".") or p.name in CANONICAL_TOP:
            continue
        if p.is_file():
            if p.suffix in (".log", ".json", ".txt", ".csv") and \
               p.name not in CANONICAL_TOP:
                problems.append(f"stray top-level artifact: {p.name} "
                                f"(move it under results/ output/ or tables/)")
        elif p.is_dir() and p.name not in CANONICAL_TOP_DIRS:
            problems.append(f"non-canonical top-level dir: {p.name}/")

    # 3 caches / OS junk anywhere
    for pat in ("**/__pycache__", "**/.pytest_cache", "**/.DS_Store",
                "**/*.pyc", "**/texput.log"):
        for hit in ws.glob(pat):
            problems.append(f"cache/junk in run: {hit.relative_to(ws)}")

    # 4 empty dirs
    for d in sorted(ws.rglob("*")):
        if d.is_dir() and not any(d.iterdir()) and ".sciforge" not in d.parts:
            problems.append(f"empty directory left behind: {d.relative_to(ws)}/")

    # 5 run README index
    readme = ws / "README.md"
    if not readme.exists():
        problems.append("run README.md index missing (kernel writes it at "
                        "phase 16; a human must be able to navigate the run)")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args()
    if not (args.workspace / ".sciforge").exists():
        print("workspace_hygiene SKIP: not a run workspace yet")
        return 0
    problems = check(args.workspace)
    if problems:
        print(f"workspace_hygiene FAIL ({len(problems)} problem(s)):")
        for p in problems[:25]:
            print(f"  - {p}")
        return 2
    print("workspace_hygiene PASS: run reads like a repository")
    return 0


if __name__ == "__main__":
    sys.exit(main())
