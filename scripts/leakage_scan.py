#!/usr/bin/env python3
"""Machine pipeline-leakage + AIGC-trace scan (S26) — the code-enforced v3.5 scrub gate.

paper-writing Step 3.5 defines the 8 (+1) leakage classes as prose; low-capability
hosts run the greps inconsistently. This script implements the SAME classes as a
mechanical scanner (stdlib regex only) and writes the registered verdict file
paper/LEAKAGE_SCRUB.json + .sciforge/verdicts/LEAKAGE_SCRUB.json so:
  - the kernel boundary gate (phase 13) refuses to advance while hits remain,
  - validate_verdicts checks the machine verdict against the schema,
  - paper-compile's existing contract (status != PASS => refuse) now has teeth.

Class J (NEW): AIGC trace phrases ("delve", "tapestry", "It is worth noting that
...") — the human-voice gate's lexical half (grammar/readability stay in the
LLM self-review; these are pure regex, deterministic).

Usage:
    python3 scripts/leakage_scan.py <workspace> [--write-verdict] [--dry-run]
Exit: 0 clean, 2 hits remaining (BLOCKED per contract).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

CLASSES = {
    "A": r"(?:\\(?:path|texttt|verb)\{?)[^}\n]*"
         r"(?:derivations/|experiments/|methods/|refine-logs|\.sciforge|literature/|src/|\.py|RESULT\.json|STATUS\.json|DISPATCH\.json|METHOD_REGISTRY|REGISTRY_HASH|APPROVAL_LOG|FRONTIER_MAP|BLINDSPOT_CHECK|SMOKE\.json|PIPELINE_STATUS)",
    "B": r"\bPhase\s+[0-9][0-9ab.]*\b|\btoy[_ ]stage\b|\btoy_gate\b|background dispatch|\bnohup\b|\bMCTS\b|\bDAG\b|\bevidence_type\b|\bverification_type\b|\btest_mode\b|effort:\s?(lite|balanced|max|beast)|role[_ -]switch|senior[_ -]reviewer|adversarial[_ -]falsification",
    "C": r"Type I (LEAKY|CLEAN|WEAK)|Type IV \(ESCAPE|INV-G\d|0 FATAL|0 CRITICAL|6 dimensions.{0,40}20.category|fidelity.{0,30}(symbolic|numerical|qualitative)|assurance[_ -]contract",
    "D": r"\bQ-[A-Z]+-[A-Z0-9]+\b|problem[_ -]anchor|\bQ-id\b|domain[_ -]signature",
    "E": r"\bMorandi\b|\bmorandi\b|\bviridis\b|\bmagma colormap\b|\b16:9\b|render\.py|input_data\.json|color[_ -]palette|\bchroma\b",
    "F": r"hbox_warnings|overfull.{0,10}pt|font_embedding|microtypesetup|COMPILE_REPORT|PAPER_PLAN",
    "G": r"^\s*%.*(?:\bQ-|Phase|\bverification_type\b|\bevidence_type\b|mode:|INV-)",
    "H": r"(?m)^%.*(?:verification_type|evidence_type|mode:|INV-G)",
    "I": r"\bSciForge\b|sci[- ]?forge|AutoFigure|render_figure|AtomCode|AgentRxiv",
    "J": r"\bdelve[sd]?\b|\btapestry\b|\bIt is worth noting\b|\bIn conclusion, this comprehensive\b|\bnavigate the complexities\b|\bAs an AI\b|\bstem from\b(?=.*\bmoreover\b)|\bunlock(?:ing|s)? (?:the )?(?:power|potential|secret)",
}

FABRICATED_AUTHOR = re.compile(
    r"\\author\{[^}]*\}\s*\\affiliation\{([^}]*)\}", re.S)


def scan_tex_files(paper_dir: Path) -> list[dict]:
    hits = []
    targets = sorted(paper_dir.rglob("*.tex"))
    for f in targets:
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("%") and re.match(r"%\s*(section|subsection|title|author|figure|table|begin|end|label|caption|todo|note)", stripped, re.I):
                pass  # standard comment prefixes still scanned by class G regex
            for cls, pat in CLASSES.items():
                if re.search(pat, line):
                    hits.append({"class": cls, "file": str(f.relative_to(paper_dir.parent)),
                                 "line": line_no, "match": line.strip()[:120]})
                    break  # first class wins for this line
    return hits


def check_frontmatter(paper_dir: Path) -> list[dict]:
    out = []
    main = paper_dir / "main.tex"
    if not main.exists():
        return out
    text = main.read_text(errors="replace")
    placeholders = ("[... to be completed", "to be completed at submission",
                    "Anonymous", "\\author{}")
    for m in FABRICATED_AUTHOR.finditer(text):
        aff = m.group(1)
        if aff and not any(ph.lower() in aff.lower() for ph in placeholders) \
           and not aff.strip().startswith("%"):
            out.append({"class": "I-frontmatter", "file": "paper/main.tex",
                        "match": aff[:80]})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    ws = args.workspace
    paper = ws / "paper"
    if not paper.exists():
        print(f"leakage_scan: no paper/ in {ws} — SKIP (not yet at phase 12)")
        return 0
    hits = scan_tex_files(paper) + check_frontmatter(paper)
    classes = sorted({h["class"] for h in hits})
    verdict = {
        "gate": "pipeline-leakage-scrub", "version": "v3.5-mech",
        "status": "PASS" if not hits else "FAIL",
        "hits_found": len(hits), "hits_scrubbed": 0,
        "hits_remaining": len(hits), "classes_seen": classes,
        "scrubbed_to": "neutral academic prose (host must rewrite, then rescan)",
        "checked_files": [str(p.relative_to(ws)) for p in sorted(paper.rglob("*.tex"))][:30],
        "generated_by": "scripts/leakage_scan.py",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    print(json.dumps({"verdict": verdict["status"], "remaining": len(hits),
                      "classes": classes,
                      "samples": hits[:5]}, ensure_ascii=False, indent=2))
    if args.write_verdict:
        (paper / "LEAKAGE_SCRUB.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False))
        vdir = ws / ".sciforge" / "verdicts"
        if vdir.exists():
            (vdir / "LEAKAGE_SCRUB.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False))
    if args.dry_run:
        return 0
    return 0 if not hits else 2


if __name__ == "__main__":
    sys.exit(main())
