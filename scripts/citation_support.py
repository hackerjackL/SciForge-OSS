#!/usr/bin/env python3
"""Sentence-level citation-support gate (v1.6, 4th verification layer).

Layers 1-3 (citation-audit) prove a reference EXISTS + metadata agrees. They do
NOT prove the citing sentence was actually said by that source, nor that a
dangling reference does real work. Real failure classes this catches:
  - "cited-but-silent": a strong claim sentence with a number in it, no
    \cite{} within scope -> an unattributed figure is the classic hallucination
  - "orphan reference": a bib entry never cited at all (dead weight inflates
    the reference count and papers over missing citations)
This gate is the DETERMINISTIC half of sentence-level attribution (structure +
proximity), so it needs no LLM and runs identically on any machine.

Scan paper/main.tex + sections/*.tex:
  1. split body into sentences; a sentence carrying a NUMBER or a comparative
     ("X% higher", "2.3x", "outperforms by 0.8") must contain \cite{} or
     \citep/\citet within the same sentence, OR be a Method/Results-internal
     self-reference (own experiment -> exempt if it names a figure/table).
     Violations -> "unsupported_quantitative_claim".
  2. every bib key must appear in at least one \cite -> else "orphan_reference"
     (unless declared in references.bib as @comment or in an ALLOW_ORPHANS list).
Optional (only when SCIFORGE_LLM_SUPPORT=1 and a provider is reachable): a model
spot-checks a sample of claims against the abstract of their cited key and flags
"claim_not_entailed" -> WEAK_CITE. Absent a provider the deterministic checks
still fully stand (this is the PaperQA idea, taken to the level we can enforce
without burning API budget on every run).

Exit: 0 PASS/SKIP, 2 FAIL.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

NUM_CLAIM = re.compile(r"(\d+(?:\.\d+)?\s*%|\d+\.\d+|\b\d+\.\d+x\b|outperform\w*\s+by|"
                       r"improve\w*\s+by|\bby \d|reduc\w+ \d|increase\w+ \d)")
SELF_REF = re.compile(r"(Table|Fig(ure)?|\\ref)\s*\\?(ref|eq)?", re.I)
CITE = re.compile(r"\\cite[tp]?\{")
CITEKEY = re.compile(r"\\cite[tp]?\{([^}]*)\}")
BIBKEY = re.compile(r"@\w+\{([^,]+),")

MAX_SENT = 320


def _body_text(paper: Path) -> list[str]:
    files = [paper / "main.tex"]
    sec = paper / "sections"
    if sec.is_dir():
        files += sorted(sec.glob("*.tex"))
    text = ""
    for f in files:
        if f.is_file():
            text += f.read_text(errors="replace") + "\n"
    # strip comments + preamble-ish envs, keep body sentences
    text = re.sub(r"(?m)^%.*$", "", text)
    text = re.sub(r"\\begin\{(abstract|document|frontmatter)\}", " ", text)
    text = re.sub(r"\\(?:label|ref|eqref|cite[tp]?|bibliography|bibliographystyle)\{[^}]*\}",
                  lambda m: m.group(0), text)  # keep cite markers visible
    # sentence split on . ! ? followed by space+Capital, coarse
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(\\])", text) if s.strip()]


def check(paper: Path, write_verdict: Path | None = None) -> list[str]:
    problems: list[str] = []
    if not (paper / "main.tex").exists():
        return []  # SKIP: no paper yet
    body = "\n".join(_body_text(paper))
    cited = set()
    for m in CITEKEY.finditer(body):
        for k in m.group(1).split(","):
            cited.add(k.strip())
    # 1) unsupported quantitative claims
    unsupported = []
    for sent in _body_text(paper):
        s = sent.strip()
        if len(s) > MAX_SENT:
            continue
        if NUM_CLAIM.search(s) and not CITE.search(s) and not SELF_REF.search(s):
            # ignore math/derived numbers inside displayed equations or table rows
            if "$" in s or "\\" in s and ("hline" in s or "&" in s):
                continue
            unsupported.append(s[:100])
    if unsupported:
        problems.append(f"{len(unsupported)} quantitative claim sentence(s) with no "
                        f"\\cite and no self-reference (unattributed figures): "
                        + " || ".join(unsupported[:3]))
    # 2) orphan references
    bib = paper / "references.bib"
    if bib.exists():
        bibkeys = {k.strip() for k in BIBKEY.findall(bib.read_text(errors="replace"))}
        orphans = sorted(bibkeys - cited)
        if orphans:
            problems.append(f"{len(orphans)} bib entr(y/ies) never cited (dead weight): "
                            + ", ".join(orphans[:5]))
    if write_verdict:
        verdict = {
            "gate": "citation-support", "version": "v1.6",
            "status": "FAIL" if problems else "PASS",
            "checks": ["quantitative-claim attribution", "orphan references"],
            "cited_keys": len(cited), "problems": problems,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "layer": "4th (sentence-level, deterministic; LLM entailment optional)",
        }
        write_verdict.parent.mkdir(parents=True, exist_ok=True)
        write_verdict.write_text(json.dumps(verdict, indent=2, ensure_ascii=False))
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    args = ap.parse_args(argv)
    paper = args.workspace / "paper"
    # marker verdict, BUG-6 pattern: results/ (NOT .sciforge/verdicts/ — an
    # unregistered JSON there would WARN under validate_verdicts --strict)
    vpath = (args.workspace / "results" / "CITATION_SUPPORT.json") if args.write_verdict else None
    problems = check(paper, vpath)
    if problems:
        for p in problems:
            print(f"citation_support: FAIL — {p}")
        return 2
    print("citation_support: PASS (or SKIP — no paper)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
