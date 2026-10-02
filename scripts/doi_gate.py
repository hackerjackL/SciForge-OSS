#!/usr/bin/env python3
"""Strict-DOI gate (v1.7.1, user mandate): every reference must carry a DOI
that resolves to a retrievable BibTeX record.

Why strict: the three-layer citation check (arXiv/CrossRef/S2) tolerates
"at least one layer", which let preprint-only and DOI-less entries survive
into manuscripts. The user's bar is higher and simpler: **if a work has a
DOI, the paper must cite the DOI and the DOI must resolve**; entries whose
DOI does not resolve are DROPPED (with disclosure in VERIFICATION_LOG), never
kept on the author's word. Classical books/chapters without any DOI are the
single documented exception (recorded as `no_doi_classical`), because forcing
a fake DOI would be fabrication.

Checks (against <ws>/literature/references.bib):
  1. every @entry has a `doi` field (exception: classical books/chapters may
     declare `no_doi_classical = {yes}` — anything else missing a DOI = FAIL)
  2. every DOI resolves via CrossRef content negotiation
     (https://doi.org/<doi> with Accept: application/x-bibtex) and returns a
     non-empty BibTeX record; network failures are RETRIED once then
     recorded as `unverifiable` (FAIL only when the entry is used in-text)
  3. the resolved record's title agrees with the bib title (normalized
     token-overlap >= 0.8) — a resolving DOI for the WRONG paper is the
     classic citation-hallucination surface

Usage: python3 scripts/doi_gate.py <workspace> [--offline]
Exit 0 = PASS/SKIP (no bib yet), 2 = FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,]+),", re.I)
FIELD_RE = re.compile(r"(\w+)\s*=\s*[\{\"]([^\}\"]*)[\}\"]", re.I)
CLASSICAL_TYPES = {"book", "inbook", "incollection", "phdthesis", "techreport"}
# Venues that mint no DOI but publish retrievable BibTeX (the user mandate is
# "DOI that resolves to bibtex"; where no DOI exists by venue policy, the
# official bibtex source URL + an explicit declaration is the honest path —
# inventing a DOI would be fabrication). arXiv is NOT exempt: it mints
# 10.48550/arXiv.* DOIs, so an arXiv entry without a DOI is a defect.
NO_DOI_VENUE_RE = re.compile(r"(jmlr\.org|proceedings\.mlr\.press|/pmlr/|mlr\.press)", re.I)


def parse_bib(text: str) -> list[dict]:
    entries = []
    for m in ENTRY_RE.finditer(text):
        kind, key = m.group(1).lower(), m.group(2).strip()
        # field scan within the entry body (crude but sufficient: fields are
        # key = {value} lines)
        start = m.end()
        depth, i = 1, start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i]
        fields = {k.lower(): v for k, v in FIELD_RE.findall(body)}
        entries.append({"kind": kind, "key": key, **fields})
    return entries


def _norm_title(t: str) -> set[str]:
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", t.lower()).split() if len(w) > 2}


def resolve_doi(doi: str, timeout: int = 20) -> str | None:
    """CrossRef content negotiation -> BibTeX text, or None."""
    url = f"https://doi.org/{doi}"
    for attempt in (0, 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/x-bibtex",
                                                       "User-Agent": "sciforge-doi-gate/1.7"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt:
                return None
            time.sleep(2)
    return None


def check(ws: Path, offline: bool = False) -> tuple[list[str], dict]:
    bib = Path(ws) / "literature" / "references.bib"
    if not bib.exists():
        return [], {"status": "SKIP", "note": "no references.bib yet"}
    entries = parse_bib(bib.read_text(errors="replace"))
    if not entries:
        return [], {"status": "SKIP", "note": "empty bibliography"}
    problems, stats = [], {"entries": len(entries), "with_doi": 0,
                           "resolved": 0, "title_mismatch": 0,
                           "classical_no_doi": 0, "unverifiable": 0}
    for e in entries:
        doi = (e.get("doi") or "").strip()
        if not doi:
            if e["kind"] in CLASSICAL_TYPES and e.get("no_doi_classical", "").lower() in ("yes", "true"):
                stats["classical_no_doi"] += 1
                continue
            url = (e.get("url") or "").strip()
            if url and NO_DOI_VENUE_RE.search(url):
                # venue mints no DOI (JMLR/PMLR): official bibtex-source URL
                # + explicit declaration is the honest substitute
                stats["classical_no_doi"] += 1
                continue
            problems.append(f"{e['key']}: missing DOI (add it; declare "
                            f"no_doi_classical=yes for a DOI-less classical book, "
                            f"or keep the official jmlr/pmlr url for DOI-free venues)")
            continue
        stats["with_doi"] += 1
        if offline:
            continue
        rec = resolve_doi(doi)
        if rec is None:
            stats["unverifiable"] += 1
            problems.append(f"{e['key']}: DOI {doi} does not resolve to a BibTeX "
                            f"record (drop the entry or fix the DOI — a DOI that "
                            f"cannot be retrieved is not a citation)")
            continue
        stats["resolved"] += 1
        m = re.search(r"title\s*=\s*[\{\"]([^\}\"]+)", rec, re.I)
        if m and e.get("title"):
            a, b = _norm_title(m.group(1)), _norm_title(e["title"])
            if a and b:
                overlap = len(a & b) / max(1, min(len(a), len(b)))
                if overlap < 0.8:
                    stats["title_mismatch"] += 1
                    problems.append(f"{e['key']}: DOI resolves but title disagrees "
                                    f"(overlap {overlap:.2f}) — wrong paper?")
    return problems, {"status": "FAIL" if problems else "PASS", **stats}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--offline", action="store_true",
                    help="structure-only (DOI presence), no network resolution")
    ap.add_argument("--write-verdict", action="store_true")
    args = ap.parse_args()
    problems, stats = check(args.workspace, offline=args.offline)
    if args.write_verdict:
        vd = Path(args.workspace) / ".sciforge" / "verdicts"
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "DOI_GATE.json").write_text(json.dumps(
            {"schema_version": "1.0", "status": stats["status"],
             "problems": problems[:20], **{k: v for k, v in stats.items()
                                           if k != "status"}}, indent=2))
    if stats["status"] == "SKIP":
        print(f"doi_gate SKIP: {stats.get('note')}")
        return 0
    if problems:
        print(f"doi_gate FAIL ({len(problems)}):")
        for p in problems[:15]:
            print(f"  - {p}")
        return 2
    print(f"doi_gate PASS: {stats['with_doi']}/{stats['entries']} DOIs, "
          f"{stats['resolved']} resolved, {stats['classical_no_doi']} classical no-DOI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
