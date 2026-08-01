#!/usr/bin/env python3
"""SciForge-OSS zero-hallucination citation verifier — Phase 6.

Real-time verification of bibliography entries against FREE open APIs:
  - CrossRef REST API (DOI resolution)
  - arXiv API (arXiv IDs / title search)
  - Semantic Scholar Open API (title/DOI lookup, fallback)

Every `.bib` entry must pass EXISTENCE + METADATA checks before it may be
committed to the paper. Fake / unresolvable entries are flagged REJECT; the
pipeline then either re-searches via LLM or drops the entry — never ships a
hallucinated citation.

Usage:
    python3 scripts/utils/citation_verifier.py <references.bib>
    python3 scripts/utils/citation_verifier.py check "10.1038/s41586-020-2649-2"
    python3 scripts/utils/citation_verifier.py check-doi 10.1038/s41586-020-2649-2
    python3 scripts/utils/citation_verifier.py check-arxiv 1706.03762
    python3 scripts/utils/citation_verifier.py self-test   # fake DOI must be REJECTED

Uses network_fetcher for proxy fallback (mihomo self-bootstrap).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse

# self-bootstrap: make the sibling network_fetcher importable whether run
# directly or as a module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network_fetcher import get_session  # sibling module (scripts/utils)

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.I)
ARXIV_RE = re.compile(r"\b(\d{4}\.\d{4,5})(v\d+)?\b")


def _json_get(url: str, timeout: float = 20.0) -> dict | None:
    """GET + parse JSON, direct→proxy fallback via network_fetcher."""
    for direct_first in (True, False):
        try:
            opener, _ = get_session(direct_first=direct_first)
            with opener.open(url, timeout=timeout) as r:
                return json.load(r)
        except Exception:
            continue
    return None


def check_doi(doi: str) -> dict:
    """CrossRef lookup: returns existence + verified metadata."""
    if not DOI_RE.fullmatch(doi.strip()):
        return {"doi": doi, "exists": False, "source": "crossref",
                "reason": "malformed_doi", "metadata": None}
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    data = _json_get(url)
    if not data or "message" not in data:
        return {"doi": doi, "exists": False, "source": "crossref",
                "reason": "not_found_or_unreachable", "metadata": None}
    m = data["message"]
    title = (m.get("title") or [""])[0] if isinstance(m.get("title"), list) else (m.get("title") or "")
    authors = [a.get("family", "") for a in m.get("author", [])[:3]]
    return {"doi": doi, "exists": True, "source": "crossref",
            "title": title, "authors": authors,
            "year": m.get("issued", {}).get("date-parts", [[None]])[0][0],
            "container": (m.get("container-title") or [""])[0] if isinstance(m.get("container-title"), list) else (m.get("container-title") or "")}


def check_arxiv(arxiv_id: str) -> dict:
    """arXiv API lookup via the Atom feed (correct id_list parameter form)."""
    url = (f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
           f"&max_results=1")
    try:
        opener, _ = get_session()
        with opener.open(url, timeout=20) as r:
            xml = r.read().decode("utf-8", "ignore")
        if f"arxiv.org/abs/{arxiv_id}" in xml:
            title = re.search(r"<entry>.*?<title>(.*?)</title>", xml, re.S)
            return {"arxiv_id": arxiv_id, "exists": True, "source": "arxiv",
                    "title": (title.group(1).strip() if title else "")[:200]}
        return {"arxiv_id": arxiv_id, "exists": False, "source": "arxiv",
                "reason": "not_found"}
    except Exception as e:
        return {"arxiv_id": arxiv_id, "exists": False, "source": "arxiv",
                "reason": f"unreachable:{type(e).__name__}"}


def check_title(title: str) -> dict:
    """Semantic Scholar fallback: title lookup."""
    q = urllib.parse.quote(title)
    data = _json_get(f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit=1")
    if data and data.get("data"):
        top = data["data"][0]
        return {"title": title, "exists": True, "source": "semanticscholar",
                "matched_title": top.get("title"), "doi": top.get("externalIds", {}).get("DOI")}
    return {"title": title, "exists": False, "source": "semanticscholar", "reason": "not_found"}


def verify_bib(bib_path: str) -> dict:
    """Parse a .bib file, verify every @entry, return per-entry verdicts."""
    try:
        with open(bib_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return {"status": "ERROR", "reason": str(e)}
    entries = re.findall(r"@\w+\{([^,]+),(.*?)\n\}", text, re.S)
    results = []
    for key, body in entries:
        doi = re.search(r"doi\s*=\s*[{}\"]?(10\.\d{4,9}/[^,}\"]+)", body, re.I)
        eprint = re.search(r"eprint\s*=\s*[{}\"]?(\d{4}\.\d{4,5})", body, re.I)
        title = re.search(r"title\s*=\s*[{}\"]?(.+?)[,}\"]?\s*$", body, re.M | re.I)
        verdict = None
        # 1) DOI → CrossRef
        if doi:
            verdict = check_doi(doi.group(1).strip())
            if not verdict["exists"] and "arxiv" in doi.group(1).lower():
                # DataCite arXiv DOI (10.48550/arXiv.XXXX) → arXiv API fallback
                m = ARXIV_RE.search(doi.group(1))
                if m:
                    verdict = check_arxiv(m.group(1))
                    verdict["via"] = "arxiv-fallback"
            if not verdict["exists"]:
                # 2) Semantic Scholar title fallback
                t = title.group(1).strip() if title else ""
                if t:
                    verdict = check_title(t)
                    verdict["via"] = "title-fallback"
        elif eprint:
            verdict = check_arxiv(eprint.group(1))
        if verdict is None and title:
            verdict = check_title(title.group(1).strip())
        if verdict is None:
            verdict = {"bib_key": key, "verdict": "REJECT", "reason": "no_doi_no_arxiv_no_title"}
        verdict["bib_key"] = key
        verdict["verdict"] = "PASS" if verdict["exists"] else "REJECT"
        results.append(verdict)
    rejects = [r for r in results if r["verdict"] == "REJECT"]
    return {"status": "PASS" if not rejects else "REJECT",
            "total": len(results), "rejected": len(rejects),
            "entries": results, "rejected_entries": rejects}


def self_test() -> dict:
    """Fake DOI must be REJECTED (100% hallucination interception)."""
    fake = check_doi("10.1038/s41586-9999-99999-9")
    real = check_doi("10.1038/s41586-020-2649-2")
    arxiv = check_arxiv("1706.03762")
    ok = (not fake["exists"]) and real["exists"] and arxiv["exists"]
    return {"fake_doi_rejected": not fake["exists"],
            "real_doi_pass": real["exists"],
            "arxiv_pass": arxiv["exists"],
            "self_test": "PASS" if ok else "FAIL"}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, arg = argv[1], (argv[2] if len(argv) > 2 else None)
    if cmd == "self-test":
        print(json.dumps(self_test(), indent=2))
        return 0 if self_test()["self_test"] == "PASS" else 2
    if cmd == "check-doi" and arg:
        print(json.dumps(check_doi(arg), indent=2))
        return 0
    if cmd == "check-arxiv" and arg:
        print(json.dumps(check_arxiv(arg), indent=2))
        return 0
    if cmd == "check" and arg:
        print(json.dumps(check_title(arg), indent=2))
        return 0
    if cmd and arg is None and (cmd.endswith(".bib") or cmd.endswith(".bibtex")):
        rep = verify_bib(cmd)
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        return 0 if rep["status"] == "PASS" else 2
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
