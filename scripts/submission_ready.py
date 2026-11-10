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
  - every bib entry carries a DOI that resolves ONLINE to a BibTeX record whose
    title agrees (doi_gate's strict check; litcache + limiter, bounded budget).
    An offline/unreachable environment is NOT silently accepted: the run is
    disclosed as `doi_online_unverified` and the tier is capped at MINOR_REV.
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
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (REPO_ROOT / "kernel", REPO_ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

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


# ---------------------------------------------------------------------------
# strict-DOI verification at the FINAL tier (v1.7.3)
#
# The v1.7.1 strict-DOI gate was invoked with --offline here, so the final
# READY/MINOR_REV decision never actually resolved a DOI. We now run
# doi_gate.check(offline=False) with its resolver patched to go through
# litcache (30d verified / 6h failed TTL) and the kernel rate limiter
# (kernel/config/ratelimits.json: crossref spacing + 429 cooldown), bounded by
# a global wall-clock budget. The gate's own logic (BibTeX content
# negotiation, >=0.8 title-token overlap, classical/JMLR exceptions) is reused
# verbatim — only the transport changes.
#
# Offline semantics (project convention: "network can only downgrade PASS to
# WARN", skills/shared-references/figure-quality-review.md): when the network
# is unreachable or the budget is exhausted, unresolved DOIs are NOT hard
# failures, but the run is explicitly disclosed as `doi_online_unverified`
# and the tier is capped at MINOR_REV — never a silent READY.
# ---------------------------------------------------------------------------
def _extract_title(rec: str) -> str:
    m = re.search(r"title\s*=\s*[\{\"]([^\}\"]+)", rec or "", re.I)
    return m.group(1).strip() if m else ""


def _retry_after(headers) -> float | None:
    try:
        return float(headers.get("Retry-After"))
    except Exception:
        return None


def _make_resolver(state: dict, *, db, litcache_mod, limiter_mod, deadline: float):
    def resolve(doi: str, timeout: int = 20) -> str | None:
        doi = str(doi).strip()
        if litcache_mod is not None:
            try:
                hit = (litcache_mod.lookup(doi, "doi", db=db) if db
                       else litcache_mod.lookup(doi, "doi"))
            except Exception:
                hit = None
            if hit:
                payload = hit.get("payload") or {}
                if hit.get("status") == "verified":
                    bib = payload.get("bibtex")
                    if isinstance(bib, str) and bib.strip():
                        state["cache_hits"] += 1
                        return bib
                    title = payload.get("title")
                    if isinstance(title, str) and title.strip():
                        state["cache_hits"] += 1
                        return "@article{cached, title={%s}}" % title
                else:
                    state["cache_failed"] += 1
                    return None
        remaining = deadline - time.monotonic()
        if remaining <= 1:
            state["budget_exhausted"] = True
            return None
        if limiter_mod is not None:
            try:
                limiter_mod().acquire("crossref", timeout_s=min(remaining, 30.0))
            except Exception:
                state["budget_exhausted"] = True
                return None
        per = max(1.0, min(float(timeout or 20), 30.0))
        for attempt in (0, 1):
            left = deadline - time.monotonic()
            if left <= 1:
                state["budget_exhausted"] = True
                return None
            try:
                req = urllib.request.Request(
                    f"https://doi.org/{doi}",
                    headers={"Accept": "application/x-bibtex",
                             "User-Agent": "sciforge-submission-ready/1.7.3"})
                with urllib.request.urlopen(req, timeout=max(1.0, min(per, left))) as r:
                    rec = r.read().decode("utf-8", "replace")
                state["resolved"] += 1
                if litcache_mod is not None:
                    try:
                        kw = {"db": db} if db else {}
                        litcache_mod.put(doi, True,
                                         {"bibtex": rec,
                                          "title": _extract_title(rec),
                                          "source": "doi_gate"},
                                         kind="doi", **kw)
                    except Exception:
                        pass
                return rec
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    state["http_429"] += 1
                    if limiter_mod is not None:
                        try:
                            limiter_mod().report_upstream_429(
                                "crossref", _retry_after(e.headers))
                        except Exception:
                            pass
                    if attempt == 0:
                        if limiter_mod is not None:
                            try:
                                limiter_mod().acquire(
                                    "crossref",
                                    timeout_s=min(max(1.0, deadline - time.monotonic()), 120.0))
                            except Exception:
                                state["budget_exhausted"] = True
                                return None
                        continue
                    state["network_failures"] += 1
                    return None
                if e.code in (400, 404, 410):
                    state["dead_dois"].add(doi)
                    if litcache_mod is not None:
                        try:
                            kw = {"db": db} if db else {}
                            litcache_mod.put(doi, False, {"reason": f"http_{e.code}"},
                                             kind="doi", **kw)
                        except Exception:
                            pass
                    return None
                state["network_failures"] += 1
                state["last_error"] = f"HTTP {e.code}"
                if attempt == 0:
                    time.sleep(min(2.0, max(0.0, deadline - time.monotonic())))
                    continue
                return None
            except Exception as e:
                state["network_failures"] += 1
                state["last_error"] = f"{type(e).__name__}: {e}"
                if attempt == 0:
                    time.sleep(min(2.0, max(0.0, deadline - time.monotonic())))
                    continue
                return None
        return None
    return resolve


def _probe_network(limiter_mod=None, timeout: float = 5.0) -> bool:
    """True when doi.org is reachable (used to distinguish a dead DOI from an
    offline environment)."""
    if limiter_mod is not None:
        try:
            limiter_mod().acquire("crossref", timeout_s=timeout)
        except Exception:
            return False
    try:
        req = urllib.request.Request(
            "https://doi.org/api/handles/10.1000/182",
            headers={"Accept": "application/json",
                     "User-Agent": "sciforge-submission-ready/1.7.3"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= getattr(r, "status", 200) < 400
    except Exception:
        return False


def _online_doi_audit(ws: Path, *, offline: bool = False, db=None,
                      budget_s: float = 120.0, resolver=None, probe=None) -> dict:
    """Run the strict DOI gate online (default) or disclose that it was offline."""
    try:
        import doi_gate as dg
    except Exception as e:  # pragma: no cover - repo layout is fixed
        return {"mode": "unavailable", "hard": [],
                "disclosures": [f"doi_gate_import_failed:{type(e).__name__}"],
                "stats": {}, "problems": []}
    db = Path(db) if db else None
    structural_problems, structural_stats = dg.check(Path(ws), offline=True)
    if structural_stats.get("status") == "SKIP":
        return {"mode": "skipped", "hard": [], "disclosures": [],
                "stats": structural_stats, "problems": []}
    # missing-DOI / structural violations are hard in every mode
    hard = list(structural_problems)
    if offline:
        return {"mode": "offline", "hard": hard,
                "disclosures": ["doi_online_unverified"],
                "stats": structural_stats, "problems": list(structural_problems)}

    state = {"network_failures": 0, "http_429": 0, "cache_hits": 0,
             "cache_failed": 0, "resolved": 0, "budget_exhausted": False,
             "dead_dois": set(), "last_error": None}
    try:
        from sciforge import litcache as litcache_mod
    except Exception:
        litcache_mod = None
    try:
        from sciforge.limiter import limiter as limiter_mod
    except Exception:
        limiter_mod = None
    deadline = time.monotonic() + max(10.0, float(budget_s))
    if resolver is None:
        resolve = _make_resolver(state, db=db, litcache_mod=litcache_mod,
                                 limiter_mod=limiter_mod, deadline=deadline)
    else:
        def resolve(doi, timeout=20):
            try:
                return resolver(doi, timeout)
            except Exception as e:
                state["network_failures"] += 1
                state["last_error"] = f"{type(e).__name__}: {e}"
                return None
    original = dg.resolve_doi
    dg.resolve_doi = resolve
    online_error = None
    try:
        online_problems, online_stats = dg.check(Path(ws), offline=False)
    except Exception as e:  # a broken transport must degrade, not crash the gate
        online_error = f"{type(e).__name__}: {e}"
        online_problems, online_stats = [], {"status": "ERROR", "error": online_error}
    finally:
        dg.resolve_doi = original
    unresolved = [p for p in online_problems if "does not resolve" in p]
    mismatch = [p for p in online_problems if "title disagrees" in p]
    hard += mismatch
    mode = "online"
    disclosures: list[str] = []
    if online_error:
        mode = "offline_degraded"
        disclosures.append("doi_online_verification_error")
    elif unresolved:
        # If every failure is a clean HTTP 4xx, the DOIs are genuinely bad.
        # If transport failed or the budget ran out, ask doi.org whether the
        # network is actually reachable; an unreachable network degrades to a
        # disclosed WARN instead of blaming the author.
        degraded = False
        transport_trouble = (state["network_failures"] > 0 or
                             state["budget_exhausted"] or
                             state["cache_failed"] > 0)
        if transport_trouble:
            probe_fn = probe or (lambda: _probe_network(limiter_mod))
            try:
                reachable = bool(probe_fn())
            except Exception:
                reachable = False
            degraded = (not reachable) or state["budget_exhausted"]
        if degraded:
            mode = "offline_degraded"
            disclosures.append("doi_online_verification_incomplete")
            if state["budget_exhausted"]:
                disclosures.append("doi_network_budget_exhausted")
        else:
            hard += unresolved
    stats = {**structural_stats,
             "online": online_stats,
             "cache_hits": state["cache_hits"],
             "cache_failed": state["cache_failed"],
             "cache_db": str(db) if db else "default",
             "network_failures": state["network_failures"],
             "http_429": state["http_429"],
             "dead_dois": sorted(state["dead_dois"]),
             "budget_exhausted": state["budget_exhausted"],
             "last_error": online_error or state["last_error"]}
    return {"mode": mode, "hard": hard, "disclosures": disclosures,
            "stats": stats, "problems": list(structural_problems) + online_problems}


def _cap_tier_for_doi(tier: str, audit: dict) -> str:
    """An unverified DOI set can never yield a READY verdict (disclosure only)."""
    if audit.get("mode") in ("offline", "offline_degraded", "unavailable") and \
            tier == "READY":
        return "MINOR_REV"
    return tier


def check(ws: Path, *, offline: bool = False, doi_db=None,
          doi_budget_s: float = 120.0, doi_resolver=None,
          doi_probe=None) -> dict:
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
                          ("scripts/leakage_scan.py", "leakage")):
        if _run(script, ws) != 0:
            hard.append(f"{label} gate fails")
    # --- hard: strict DOI gate, ONLINE by default (v1.7.3). Offline/no-network
    # is disclosed and caps the tier at MINOR_REV instead of silently passing.
    doi_audit = _online_doi_audit(ws, offline=offline, db=doi_db,
                                  budget_s=doi_budget_s,
                                  resolver=doi_resolver, probe=doi_probe)
    if doi_audit["hard"]:
        hard.append(f"doi gate fails ({len(doi_audit['hard'])} problem(s))")
    disclosures = list(doi_audit.get("disclosures", []))
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
    pre_cap_tier = tier
    tier = _cap_tier_for_doi(tier, doi_audit)
    return {"tier": tier, "hard": hard, "soft": soft,
            "disclosures": disclosures,
            "doi_verification": {
                "mode": doi_audit.get("mode"),
                "problems": doi_audit.get("problems", [])[:20],
                "stats": doi_audit.get("stats", {}),
                "tier_capped": tier != pre_cap_tier,
            },
            "pages": pages, "abstract_words": words, "abstract_numbers": nums,
            "figures": len(figs), "visual_grammars": sorted(k for k in kinds if k),
            "claim_mode": claim_mode}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    ap.add_argument("--offline", action="store_true",
                    help="skip online DOI resolution; the tier is capped and "
                         "the disclosure doi_online_unverified is recorded")
    ap.add_argument("--doi-budget", type=float, default=120.0,
                    help="wall-clock budget for online DOI verification (s)")
    ap.add_argument("--doi-cache-db", type=Path, default=None,
                    help="litcache sqlite path (default kernel/sciforge/litcache)")
    args = ap.parse_args()
    offline = args.offline or os.environ.get("SCIFORGE_OFFLINE", "").lower() in \
        ("1", "true", "yes", "on")
    doc = check(args.workspace, offline=offline, doi_db=args.doi_cache_db,
                doi_budget_s=args.doi_budget)
    if args.write_verdict:
        vd = args.workspace / ".sciforge" / "verdicts"
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "SUBMISSION_READY.json").write_text(
            json.dumps({"schema_version": "1.0", **doc}, indent=2))
    print(f"submission_ready {doc['tier']}: hard={doc['hard']} soft={doc['soft']}"
          + (f" disclosures={doc['disclosures']}" if doc.get("disclosures") else "")
          + f" doi={doc.get('doi_verification', {}).get('mode')}")
    return {"READY": 0, "MINOR_REV": 0, "MAJOR_REV": 1, "NOT_READY": 2}[doc["tier"]]


if __name__ == "__main__":
    sys.exit(main())
