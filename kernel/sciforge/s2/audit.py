"""Completeness audit (ScientistTwo §3.7): reward-hacking scan + method↔code parity.

Their audit bar (what makes 86/107 believable): re-run released code, hunt
spec violations / reward hacking, line-by-line compare the method section
against the implementation, 1814 references with zero hallucination. Our
citation layer already covers the reference half; this module adds the two
mechanical halves we were missing:

1. reward_hacking_scan — pure arithmetic/consistency checks a model cannot
   argue with: stated relative gain must equal the recomputed gain; the
   ladder's GOOD claim must survive re-derivation; the evaluation protocol
   must declare a held-out/split discipline when experiments exist.

2. method_code_parity — the method section (METHOD_REGISTRY.md / method
   text) names operations (`backticked`, snake_case, camelCase tokens);
   every such token must actually appear in the released code (src/,
   experiments/). The reverse direction (code symbols never mentioned) is
   reported for information. PASS requires >=80% of claimed tokens to land —
   a method paragraph describing machinery that does not exist is the
   classic reward-hacking surface.

Output: `.sciforge/audits/AUDIT_TRAIL.json`; enforced at wrap-up by
`scripts/s2_audit.py` (SKIP when no experiments — the audit is about claims
from experiment runs).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import ladder as ladder_mod

SCHEMA_VERSION = "1.0"
AUDIT_REL = Path(".sciforge") / "audits" / "AUDIT_TRAIL.json"
PARITY_MIN_RATIO = 0.8

_TOKEN_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]{3,})`|"
                       r"\b([a-z]+_[a-z0-9_]{3,})\b|"
                       r"\b([a-z]+[A-Z][A-Za-z0-9]+)\b")
# English connectives that trip the snake_case/camelCase patterns
_STOP = {"for_example", "in_order", "and_or", "if_and_only_if", "as_well_as",
         "note_that", "see_also", "for_instance", "such_as", "load_balancing"}


# ---------------------------------------------------------------------------
# 1. reward-hacking scan
# ---------------------------------------------------------------------------

def gain_arithmetic(ws: Path) -> dict:
    """Re-derive every stated gain; any mismatch = reward-hacking class."""
    doc = ladder_mod.load(ws)
    if doc is None:
        return {"status": "SKIP", "note": "no S2_LADDER.json"}
    problems = [p for p in ladder_mod.validate(doc)
                if "arithmetic" in p or "does not strictly beat" in p
                or "promotion without" in p]
    return {"status": "FAIL" if problems else "PASS", "problems": problems}


def protocol_split_declaration(ws: Path) -> dict:
    """Experiments exist => some evaluation protocol must declare the split
    discipline (held-out / test / seed) — silent resubstitution is the
    cheapest reward hack."""
    if not ladder_mod.experiment_markers(ws)["any"]:
        return {"status": "SKIP", "note": "no experiments"}
    candidates = [Path(ws) / ".sciforge" / "verdicts" / "EVALUATION_PROTOCOL.json",
                  Path(ws) / ".sciforge" / "audits" / "EVALUATION_PROTOCOL.md",
                  Path(ws) / "experiments" / "EVALUATION_PROTOCOL.md"]
    for p in candidates:
        if not p.exists():
            continue
        text = p.read_text(errors="replace").lower()
        if any(k in text for k in ("held-out", "held out", "test split", "test set",
                                   "seed", "split")):
            return {"status": "PASS", "source": str(p)}
        return {"status": "FAIL",
                "note": f"{p.name} exists but declares no split/held-out/seed discipline"}
    return {"status": "FAIL",
            "note": "experiments exist but no EVALUATION_PROTOCOL declares the "
                    "held-out/split discipline"}


def reward_hacking_scan(ws: Path) -> dict:
    checks = {"gain_arithmetic": gain_arithmetic(ws),
              "split_discipline": protocol_split_declaration(ws)}
    statuses = [c["status"] for c in checks.values()]
    overall = "FAIL" if "FAIL" in statuses else \
              ("PASS" if "PASS" in statuses else "SKIP")
    return {"overall": overall, "checks": checks}


# ---------------------------------------------------------------------------
# 2. method-section vs implementation parity
# ---------------------------------------------------------------------------

def _method_sources(ws: Path) -> list[Path]:
    ws = Path(ws)
    out = []
    for rel in ("methods/METHOD_REGISTRY.md",
                ".sciforge/audits/CLAIMS_FROM_RESULTS.md",
                "paper/main.tex"):
        p = ws / rel
        if p.exists():
            out.append(p)
    return out


def _code_corpus(ws: Path) -> str:
    ws = Path(ws)
    chunks = []
    for root in (ws / "src", ws / "experiments", ws / "toy_experiment"):
        if root.is_dir():
            for f in sorted(root.rglob("*.py")):
                try:
                    chunks.append(f.read_text(errors="replace"))
                except OSError:
                    continue
    return "\n".join(chunks)


def claimed_tokens(text: str) -> list[str]:
    """Machine-checkable operation names the method section asserts exist."""
    seen: list[str] = []
    for m in _TOKEN_RE.finditer(text):
        tok = next((g for g in m.groups() if g), "")
        if tok and tok not in _STOP and tok not in seen:
            seen.append(tok)
    return seen


def method_code_parity(ws: Path) -> dict:
    ws = Path(ws)
    sources = _method_sources(ws)
    if not sources:
        return {"status": "SKIP", "note": "no method/claims/paper source to audit"}
    code = _code_corpus(ws)
    if not code.strip():
        return {"status": "SKIP", "note": "no released code under src/experiments "
                                          "(nothing to compare against)"}
    text = "\n".join(s.read_text(errors="replace") for s in sources)
    tokens = claimed_tokens(text)
    if not tokens:
        return {"status": "SKIP", "note": "method section names no machine tokens",
                "sources": [str(s.relative_to(ws)) for s in sources]}
    matched, unmatched = [], []
    for t in tokens:
        if re.search(rf"\b{re.escape(t)}\b", code):
            matched.append(t)
        else:
            unmatched.append(t)
    ratio = len(matched) / len(tokens)
    # reverse direction: informational only
    code_funcs = sorted(set(re.findall(r"^def ([A-Za-z_][A-Za-z0-9_]+)",
                                       code, re.MULTILINE)))
    unmentioned = [f for f in code_funcs
                   if not re.search(rf"\b{re.escape(f)}\b", text)][:40]
    status = "PASS" if ratio >= PARITY_MIN_RATIO else "FAIL"
    return {"status": status, "ratio": round(ratio, 3),
            "claimed": len(tokens), "matched": len(matched),
            "unmatched": unmatched[:40],
            "unmentioned_functions": unmentioned,
            "sources": [str(s.relative_to(ws)) for s in sources]}


# ---------------------------------------------------------------------------
# full audit trail
# ---------------------------------------------------------------------------

def run_full_audit(ws: Path) -> dict:
    ws = Path(ws)
    hacking = reward_hacking_scan(ws)
    parity = method_code_parity(ws)
    statuses = [hacking["overall"], parity["status"]]
    overall = "FAIL" if "FAIL" in statuses else \
              ("PASS" if "PASS" in statuses else "SKIP")
    doc = {"schema_version": SCHEMA_VERSION, "overall": overall,
           "reward_hacking": hacking, "method_code_parity": parity,
           "ts": time.time(),
           "rule": "FAIL blocks wrap-up; SKIP only when no experiment claims exist"}
    p = ws / AUDIT_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return doc
