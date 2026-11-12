#!/usr/bin/env python3
"""One-shot gate battery for Mode A (skills-only) runs — v1.7.3.

Mode A agents execute the 26-node DAG themselves and are expected to call the
mechanical gates at the right moments. Remembering a dozen scripts is exactly
the failure mode this tool removes: one command runs every gate that applies
to the workspace and prints one table.

This does NOT turn Mode A into Mode B. The kernel enforces gates inside
`commit_boundary()` and refuses transitions; this script reports after the
fact. It exists so that "self-run scripts/*" costs one call instead of one call
per gate, and so that gates which CANNOT run under Mode A are reported as
UNPROTECTED rather than silently skipped.

Status vocabulary
-----------------
PASS         the gate ran and passed
WARN         the gate ran but a layer of it did not: integrity_monitor passed
             the deterministic core without the semantic D1 tier (run
             --integrity-llm to include it)
SKIP         the gate's own SKIP/NOT_APPLICABLE condition held (theory-only
             route, phase not reached, no paper yet, ...)
UNPROTECTED  the gate cannot provide assurance in this workspace because the
             artifact it checks is produced only by the runtime kernel
             (NODES.json / REP.json / RUNSTATE.problem_hash), or because a
             self-reported ledger has no co-located raw evidence to check
             against (fairness_gate scope=ledger_only). This is NOT a pass and
             NOT a normal skip: the corresponding guarantee is absent.
INFO         a computed diagnostic, not a gate (TDAL score)
FAIL         the gate ran and failed
BLOCKED      the gate refused a dispatch (security_scan BLOCKED class)
ERROR        the gate could not run (timeout, unreadable workspace, ...)

Exit codes: 0 = no FAIL/BLOCKED/ERROR, 1 = at least one, 2 = usage error.

Usage:
    python3 scripts/gate_all.py <workspace> [--json] [--only A,B] [--skip C]
                                [--offline] [--integrity-llm] [--timeout S]
                                [--list]

The workspace must be a run workspace (contains .sciforge/ or run artifacts).
Stdlib only, no third-party imports.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"

# Fallback phase order (kernel/config/phasegraph.json is authoritative when
# present; this list mirrors it so the tool still works from a partial tree).
FALLBACK_PHASE_ORDER = [
    "0", "1", "1a", "1b", "4broad", "2", "2.5", "2.5b", "3", "4targeted",
    "5", "6", "6a", "6b", "6c", "7", "8", "9", "10", "11", "12", "13", "14",
    "15", "15.5", "16",
]

STATUSES = ("PASS", "WARN", "SKIP", "UNPROTECTED", "INFO", "FAIL", "BLOCKED", "ERROR")
FAILING = ("FAIL", "BLOCKED", "ERROR")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _phase_order() -> list[str]:
    try:
        spec = json.loads((REPO_ROOT / "kernel" / "config" / "phasegraph.json").read_text())
        order = [p["id"] for p in spec["phases"]]
        return order or FALLBACK_PHASE_ORDER
    except Exception:
        return FALLBACK_PHASE_ORDER


PHASE_ORDER = _phase_order()
PHASE_RANK = {pid: i for i, pid in enumerate(PHASE_ORDER)}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception:
        return None


def _runstate(ws: Path) -> dict:
    """RUNSTATE payload (v1.0 flat and v2.0 both tolerated)."""
    d = _read_json(ws / ".sciforge" / "RUNSTATE.json")
    if not isinstance(d, dict):
        return {}
    return d.get("data") if isinstance(d.get("data"), dict) else d


def _detect_mode(ws: Path) -> str:
    """A workspace driven by the kernel carries its event log; report the mode
    so an UNPROTECTED row is not misread on a kernel run."""
    ev = ws / ".sciforge" / "events.ndjson"
    if ev.is_file():
        for line in ev.read_text(errors="replace").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("kind") in ("boundary_committed", "phase_entered"):
                return "B-kernel-workspace"
    return "A-skills-only"


# Artifacts that can only exist once a phase has actually run. Used to
# cross-check the declared RUNSTATE cursor: in Mode A the orchestrator is a
# host agent writing RUNSTATE by hand, so the cursor can lag the real work.
_EVIDENCE_PROBES = (
    ("6",    (".sciforge/verdicts/VERIFICATION_ROUTING.json",)),
    ("6b",   ("experiments/toy/RESULT.json",)),
    ("6c",   ("experiments/full/group_*/RESULT.json", "experiments/full/RESULT.json")),
    ("10",   ("results.json", "results/metrics.json")),
    ("11",   ("figures/*/output.pdf",)),
    ("12",   ("paper/main.tex",)),
    ("13",   ("paper/main.pdf",)),
    ("14",   (".sciforge/verdicts/REVIEW_STATE.json",)),
    ("15",   (".sciforge/verdicts/CITATION_AUDIT.json",)),
    ("15.5", (".sciforge/verdicts/PUBLISHABILITY_SCORE.json",)),
)


def _evidence_rank(ws: Path) -> int | None:
    """Highest phase with on-disk proof that it ran, or None."""
    best = None
    for pid, probes in _EVIDENCE_PROBES:
        if pid not in PHASE_RANK:
            continue
        if any(ws.glob(p) and next(iter(ws.glob(p)), None) is not None
               for p in probes):
            r = PHASE_RANK[pid]
            best = r if best is None else max(best, r)
    return best


def _declared_rank(ws: Path) -> int | None:
    rs = _runstate(ws)
    if not rs:
        return None
    if rs.get("status") == "completed":
        return max(PHASE_RANK.values())
    ranks = [PHASE_RANK[str(rs.get(key))]
             for key in ("last_completed_boundary", "current_phase")
             if str(rs.get(key) or "") in PHASE_RANK]
    return max(ranks) if ranks else None


def _current_rank(ws: Path) -> int | None:
    """Highest phase the workspace has demonstrably reached, or None.

    Takes the max of the declared RUNSTATE cursor and the on-disk artifact
    evidence. RUNSTATE alone is not enough: Mode A rewrites it by hand, so a
    stale cursor made every gate report `phase_not_reached` on a workspace that
    already held experiments, figures and a manuscript — the whole battery
    silently skipped, which is exactly what this script exists to prevent.
    Absent both signals, return None so each gate's own SKIP semantics decide.
    """
    declared = _declared_rank(ws)
    evidenced = _evidence_rank(ws)
    if declared is None and evidenced is None:
        return None
    return max(x for x in (declared, evidenced) if x is not None)


def _cursor_stale(ws: Path) -> bool:
    """True when artifacts prove more progress than RUNSTATE declares."""
    d, e = _declared_rank(ws), _evidence_rank(ws)
    return e is not None and (d is None or e > d)


def _rank(pid: str) -> int:
    return PHASE_RANK.get(pid, len(PHASE_ORDER))


def _run(script: str, args: list[str], timeout: int) -> tuple[int, str, float]:
    """Run one scripts/*.py gate. Returns (exit, combined output, seconds)."""
    t0 = time.time()
    try:
        p = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or ""), time.time() - t0
    except subprocess.TimeoutExpired:
        return -9, f"TIMEOUT after {timeout}s", time.time() - t0
    except OSError as exc:
        return -1, f"cannot run {script}: {exc}", time.time() - t0


def _clip(text: str, limit: int = 700) -> str:
    text = " ".join(text.split())
    return text[-limit:] if len(text) > limit else text


def _result(name: str, phase: str, status: str, reason: str, detail: str = "",
            duration: float = 0.0) -> dict:
    assert status in STATUSES, status
    return {"gate": name, "phase": phase, "status": status,
            "reason_code": reason, "detail": _clip(detail), "duration_s": round(duration, 3)}


def _exit_status(rc: int, out: str) -> str:
    if rc == -9 or rc == -1:
        return "ERROR"
    if rc == 0:
        return "SKIP" if "SKIP" in out else "PASS"
    return "FAIL"


def _std_result(name: str, phase: str, rc: int, out: str, duration: float,
                fail_reason: str) -> dict:
    """Map a gate's own exit/output semantics to a report row."""
    status = _exit_status(rc, out)
    reason = {"PASS": "ok", "SKIP": "skipped_by_gate",
              "ERROR": "gate_unavailable"}.get(status, fail_reason)
    return _result(name, phase, status, reason, out, duration)


def _has_paper(ws: Path) -> bool:
    return (ws / "paper" / "main.tex").is_file()


def _has_experiment_evidence(ws: Path) -> bool:
    exp = ws / "experiments"
    if not exp.is_dir():
        return False
    return any(exp.rglob("RESULT.json")) or any(exp.rglob("STATUS.json")) \
        or any(exp.rglob("DISPATCH.json"))


def _has_claim_evidence(ws: Path) -> bool:
    if (ws / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md").is_file():
        return True
    paper = ws / "paper"
    if paper.is_dir() and any(paper.rglob("*.tex")):
        return True
    return _has_experiment_evidence(ws)


def _parse_json_tail(out: str):
    """Last parseable JSON object in noisy output (gates print prose too)."""
    dec = json.JSONDecoder()
    best = None
    i = 0
    while True:
        i = out.find("{", i)
        if i < 0:
            return best
        try:
            obj, end = dec.raw_decode(out[i:])
            best = obj
            i += end
        except json.JSONDecodeError:
            i += 1


# ---------------------------------------------------------------------------
# per-gate runners
# ---------------------------------------------------------------------------

def gate_validate_verdicts(ws: Path, opts) -> dict:
    vd = ws / ".sciforge" / "verdicts"
    if not vd.is_dir():
        return _result("validate_verdicts", "0", "SKIP", "no_verdicts_dir",
                       f"{vd} does not exist yet")
    args = [str(vd), "--strict"]
    if _runstate(ws).get("status") == "completed":
        args.append("--require-complete")  # wrap-up parity
    rc, out, dur = _run("validate_verdicts.py", args, opts.timeout)
    return _result("validate_verdicts", "0",
                   "PASS" if rc == 0 else "FAIL",
                   "ok" if rc == 0 else "verdict_violations", out, dur)


def gate_rep_plan_present(ws: Path, opts) -> dict:
    """The kernel compiles REP.json at phase 1 and requires it from phase 2."""
    rep = _read_json(ws / ".sciforge" / "audits" / "REP.json")
    if isinstance(rep, dict):
        if not isinstance(rep.get("objectives"), list) or not rep["objectives"]:
            return _result("rep_plan_present", "2", "FAIL", "rep_malformed",
                           "REP.json has no objectives[]")
        return _result("rep_plan_present", "2", "PASS", "ok",
                       f"{len(rep['objectives'])} objectives, "
                       f"{len(rep.get('fallbacks') or {})} fallbacks declared")
    rank = _current_rank(ws)
    reached = (rank is not None and rank >= _rank("2")) or \
        (ws / "literature" / "GAP_REPORT.md").is_file() or \
        (ws / ".sciforge" / "refine-logs" / "FINAL_PROPOSAL.json").is_file() or \
        (ws / "methods" / "METHOD_REGISTRY.md").is_file() or \
        _has_experiment_evidence(ws)
    if reached:
        if _detect_mode(ws) == "B-kernel-workspace":
            return _result("rep_plan_present", "2", "FAIL",
                           "rep_plan_absent_in_kernel_run",
                           "the kernel-event log shows phase 1 was entered but "
                           "REP.json is missing — a planless run violates the phase-1 "
                           "compile contract")
        return _result("rep_plan_present", "2", "UNPROTECTED", "rep_plan_absent",
                       "REP.json is compiled only by the runtime kernel at phase 1; "
                       "with no plan, loopback-vs-plan checks (rep.fallback_consumed) "
                       "do not run in Mode A")
    return _result("rep_plan_present", "2", "SKIP", "phase_1_not_reached",
                   "no phase-2 artifacts and no RUNSTATE cursor")


def gate_gap_gate(ws: Path, opts) -> dict:
    rc, out, dur = _run("gap_gate.py", [str(ws)], opts.timeout)
    return _result("gap_gate", "4broad", "PASS" if rc == 0 else "FAIL",
                   "ok" if rc == 0 else "gap_report_missing_or_invalid", out, dur)


def gate_citation_relevance(ws: Path, opts) -> dict:
    """Topic-relevance of the reference corpus against the Phase-1b domain
    signature. Runs at 4broad — the moment references.bib is finalized — so an
    off-domain entry (the BCa/BCA sputtering collision) is caught before it
    anchors a gap or reaches the manuscript. WARN (uncertain / cross-domain
    disclosure) is not a failure: interdisciplinary citations are legal.
    SKIP when no domain-signature exists (pre-Phase-1b runs)."""
    rc, out, dur = _run("citation_relevance_gate.py", [str(ws), "--json"], opts.timeout)
    if rc == -9 or rc == -1:
        return _result("citation_relevance", "4broad", "ERROR", "gate_unavailable", out, dur)
    doc = _parse_json_tail(out) or {}
    status = doc.get("status")
    if status == "SKIP":
        return _result("citation_relevance", "4broad", "SKIP", "no_domain_signature",
                       doc.get("note", out), dur)
    if status == "WARN":
        return _result("citation_relevance", "4broad", "WARN", "citation_relevance_uncertain",
                       out, dur)
    if status == "FAIL" or rc == 2:
        return _result("citation_relevance", "4broad", "FAIL", "citation_off_domain", out, dur)
    if status == "PASS" or rc == 0:
        return _result("citation_relevance", "4broad", "PASS", "ok", out, dur)
    return _result("citation_relevance", "4broad", "ERROR", "gate_unavailable", out, dur)


def gate_registry_hash(ws: Path, opts) -> dict:
    """Phase 5 hash lock (kernel gate `hash`). Mode A skills write the same
    artifact, so this is enforceable in both modes."""
    cands = (ws / ".sciforge" / "verdicts" / "REGISTRY_HASH.txt",
             ws / "methods" / "REGISTRY_HASH.txt")
    p = next((c for c in cands if c.is_file()), None)
    if p is None:
        if _current_rank(ws) is not None:
            return _result("registry_hash", "5", "FAIL", "registry_hash_missing",
                           "REGISTRY_HASH.txt absent although the run passed phase 5")
        return _result("registry_hash", "5", "SKIP", "no_registry_hash_yet",
                       "REGISTRY_HASH.txt not written yet")
    txt = p.read_text(errors="replace").strip()
    if txt.startswith("BLOCKED"):
        return _result("registry_hash", "5", "FAIL", "registry_hash_blocked", txt)
    ok = len(txt) == 64 and all(ch in "0123456789abcdef" for ch in txt)
    return _result("registry_hash", "5", "PASS" if ok else "FAIL",
                   "ok" if ok else "registry_hash_malformed",
                   f"{p.relative_to(ws)}: {txt[:64]}")


def gate_inv_g1(ws: Path, opts) -> dict:
    """Phase 9 INV-G1 hash match. The kernel freezes `problem_hash` in
    RUNSTATE; Mode A workspaces usually carry only the hash file, in which
    case the comparison has no reference value — report that honestly."""
    hp = ws / ".sciforge" / "verdicts" / "PROBLEM_HASH.txt"
    locked = str(_runstate(ws).get("problem_hash") or "")
    if not hp.is_file():
        if _current_rank(ws) is not None:
            return _result("inv_g1", "9", "FAIL", "problem_hash_file_missing",
                           "PROBLEM_HASH.txt absent although the run passed phase 9")
        return _result("inv_g1", "9", "SKIP", "no_problem_hash_yet",
                       "PROBLEM_HASH.txt not written yet")
    actual = hp.read_text(errors="replace").strip()
    if not locked:
        if _detect_mode(ws) == "B-kernel-workspace":
            return _result("inv_g1", "9", "FAIL", "frozen_hash_missing",
                           "RUNSTATE carries no problem_hash although the kernel "
                           "writes it at start")
        return _result("inv_g1", "9", "UNPROTECTED", "no_frozen_reference_hash",
                       "RUNSTATE carries no problem_hash; the anchor file exists but "
                       "there is no frozen reference to compare it against in Mode A")
    ok = actual == locked and len(actual) == 64
    return _result("inv_g1", "9", "PASS" if ok else "FAIL",
                   "ok" if ok else "problem_anchor_drift",
                   f"file={actual[:12]} lock={locked[:12]}")


def gate_security_scan(ws: Path, opts) -> dict:
    """Same scope as the kernel gate: src/**/*.py + experiments/**/*.py."""
    roots = [ws / "src", ws / "experiments"]
    files = sorted({p for r in roots if r.is_dir() for p in r.rglob("*.py")})
    if not files:
        return _result("security_scan", "6b/6c", "SKIP", "no_agent_scripts",
                       "no .py under src/ or experiments/")
    bad, dur = [], 0.0
    for f in files:
        rc, out, d = _run("security_scan.py", [str(f)], opts.timeout)
        dur += d
        if rc != 0:
            bad.append({"script": str(f.relative_to(ws)),
                        "exit": rc, "detail": _clip(out, 300)})
    if not bad:
        return _result("security_scan", "6b/6c", "PASS", "ok",
                       f"{len(files)} script(s) scanned, no BLOCKED-class finding", dur)
    return _result("security_scan", "6b/6c", "BLOCKED", "security_scan_blocked",
                   json.dumps(bad[:5], ensure_ascii=False), dur)


def gate_dep_gate(ws: Path, opts) -> dict:
    rc, out, dur = _run("dep_gate.py", [str(ws)], opts.timeout)
    return _std_result("dep_gate", "6b/6c", rc, out, dur, "undeclared_import")


def gate_integrity_monitor(ws: Path, opts) -> dict:
    args = [str(ws)] + (["--strict-llm"] if opts.integrity_llm else [])
    rc, out, dur = _run("s2_integrity_gate.py", args, opts.timeout)
    status = _exit_status(rc, out)
    reason = {"PASS": "ok", "SKIP": "skipped_by_gate",
              "ERROR": "gate_unavailable"}.get(status, "integrity_violation")
    if status == "PASS" and not opts.integrity_llm:
        # D2/D3 deterministic core only; the semantic D1 tier is not enforced.
        status, reason = "WARN", "semantic_d1_not_run"
    return _result("integrity_monitor", "6b/6c", status, reason, out, dur)


def gate_smoke_gate(ws: Path, opts) -> dict:
    rc, out, dur = _run("smoke_gate.py", [str(ws)], opts.timeout)
    return _std_result("smoke_gate", "6c", rc, out, dur, "smoke_missing_or_failed")


def gate_s2_ladder(ws: Path, opts) -> dict:
    rc, out, dur = _run("s2_ladder_gate.py", [str(ws)], opts.timeout)
    return _std_result("s2_ladder", "6c", rc, out, dur, "ladder_missing_or_invalid")


def gate_s2_ablation(ws: Path, opts) -> dict:
    rc, out, dur = _run("s2_ablation_gate.py", [str(ws)], opts.timeout)
    return _std_result("s2_ablation", "10", rc, out, dur,
                       "ablation_missing_or_invalid")


def gate_arb_verify(ws: Path, opts) -> dict:
    rc, out, dur = _run("arb_verify.py", [str(ws)], opts.timeout)
    return _std_result("arb_verify", "10", rc, out, dur, "arb_claim_invalid")


def gate_tdal(ws: Path, opts) -> dict:
    """Computed diagnostic, not a gate: no kernel boundary consumes TDAL."""
    rc, out, dur = _run("tdal_compute.py", [str(ws), "--json"], opts.timeout)
    if rc != 0:
        return _result("tdal_compute", "10", "ERROR", "workspace_unreadable", out, dur)
    doc = _parse_json_tail(out) or {}
    tdal = doc.get("tdal") or (doc if "joint" in doc else {})
    verdict = tdal.get("verdict", "UNKNOWN")
    return _result("tdal_compute", "10", "INFO", f"tdal_{str(verdict).lower()}",
                   f"joint={tdal.get('joint')} dims={tdal.get('dims')} "
                   f"missing={tdal.get('missing_inputs')}", dur)


def gate_figure_embedding(ws: Path, opts) -> dict:
    if not _has_paper(ws):
        return _result("figure_embedding", "11", "SKIP", "no_manuscript",
                       "paper/main.tex absent")
    rc, out, dur = _run("check_figure_embedding.py",
                        [str(ws / "paper"), "--require-renderer",
                         "--figures-dir", str(ws / "figures")], opts.timeout)
    return _result("figure_embedding", "11", "PASS" if rc == 0 else "FAIL",
                   "ok" if rc == 0 else "figure_embedding_or_renderer_violation",
                   out, dur)


def gate_figure_style(ws: Path, opts) -> dict:
    rc, out, dur = _run("figure_style_gate.py", [str(ws)], opts.timeout)
    return _std_result("figure_style", "11", rc, out, dur, "figure_style_violation")


def gate_fantasy_gate(ws: Path, opts) -> dict:
    rc, out, dur = _run("fantasy_gate.py", [str(ws)], opts.timeout)
    return _std_result("fantasy_gate", "12", rc, out, dur, "fantasy_or_mostly_fantasy")


def _find_verdict(ws: Path, name: str) -> Path | None:
    """Mirror kernel/sciforge/gates.py::_find_verdict for marker verdicts."""
    for base in (ws / ".sciforge" / "verdicts", ws / "results", ws / "paper",
                 ws / "logs", ws / "experiments"):
        if not base.is_dir():
            continue
        p = base / name
        if p.exists():
            return p
        if base.name == "experiments":
            hits = sorted(base.rglob(name))
            if hits:
                return hits[0]
    return None


def gate_quality_gate(ws: Path, opts) -> dict:
    """Phase 12 marker gate: the host must run /quality-gate and write the
    verdict; a missing marker FAILs the boundary in the kernel."""
    p = _find_verdict(ws, "QUALITY_GATE.json")
    if p is None:
        return _result("quality_gate", "12", "FAIL", "quality_gate_verdict_absent",
                       "QUALITY_GATE.json not found (host must run the quality-gate "
                       "skill and write the verdict)")
    return _result("quality_gate", "12", "PASS", "ok", str(p.relative_to(ws)))


def gate_compile_audit(ws: Path, opts) -> dict:
    """Phase 13 marker gate. Mirrors kernel/sciforge/gates.py::compile_audit:
    PAPER_COMPILE.json required; compile warnings are hard only under
    discipline=strict (balanced/lean disclose them)."""
    lv = _find_verdict(ws, "LEAKAGE_SCRUB.json")
    if lv is not None:
        doc = _read_json(lv) or {}
        if doc.get("status") != "PASS":
            return _result("compile_audit", "13", "FAIL", "leakage_scrub_not_pass",
                           f"LEAKAGE_SCRUB.json status={doc.get('status')!r}; "
                           f"compile refuses")
    pc = _find_verdict(ws, "PAPER_COMPILE.json")
    if pc is None:
        return _result("compile_audit", "13", "FAIL", "paper_compile_verdict_absent",
                       "PAPER_COMPILE.json not found (host must compile and write "
                       "the verdict)")
    doc = _read_json(pc) or {}
    try:
        warnings = int(doc.get("warnings") or 0)
    except (TypeError, ValueError):
        warnings = 0
    flags = _runstate(ws).get("flags") or {}
    discipline = flags.get("discipline", "strict")
    if warnings and discipline == "strict":
        return _result("compile_audit", "13", "FAIL", "compile_warnings_strict",
                       f"{warnings} compile warning(s) under discipline=strict")
    return _result("compile_audit", "13", "PASS", "ok",
                   f"PAPER_COMPILE.json present, warnings={warnings}, "
                   f"discipline={discipline}")


def gate_citation_audit(ws: Path, opts) -> dict:
    """Phase 15 marker gate: CITATION_AUDIT.json must exist."""
    p = _find_verdict(ws, "CITATION_AUDIT.json")
    if p is None:
        return _result("citation_audit", "15", "FAIL", "citation_audit_verdict_absent",
                       "CITATION_AUDIT.json not found (host must run the "
                       "citation-audit skill and write the verdict)")
    return _result("citation_audit", "15", "PASS", "ok", str(p.relative_to(ws)))


def gate_leakage_scan(ws: Path, opts) -> dict:
    rc, out, dur = _run("leakage_scan.py", [str(ws)], opts.timeout)
    return _std_result("leakage_scan", "13", rc, out, dur, "leakage_hits_remaining")


def gate_citation_support(ws: Path, opts) -> dict:
    rc, out, dur = _run("citation_support.py", [str(ws)], opts.timeout)
    return _std_result("citation_support", "15", rc, out, dur,
                       "unsupported_or_orphan_citation")


def gate_doi_gate(ws: Path, opts) -> dict:
    args = [str(ws)] + (["--offline"] if opts.offline else [])
    rc, out, dur = _run("doi_gate.py", args, opts.timeout)
    row = _std_result("doi_gate", "15", rc, out, dur, "doi_unresolvable_or_missing")
    if opts.offline and row["status"] in ("PASS", "SKIP"):
        row["reason_code"] += "_offline_structure_only"
    return row


# Gate-produced telemetry that legitimately lives beside the evidence. Writing
# these is the gate's job, not evidence tampering.
_GATE_OWN_PRODUCTS = frozenset({
    "FANTASY_GATE.json", "TDAL.json", "CITATION_SUPPORT.json",
    "LEAKAGE_SCRUB.json", "DOI_GATE.json", "SUBMISSION_READY.json",
    "CITATION_RELEVANCE.json", "FAIRNESS.json", "S2_LADDER.json",
    "ABLATION_LEDGER.json", "AUDIT_TRAIL.json", "INTEGRITY_MONITOR.json",
})


def _evidence_files(ws: Path) -> list[Path]:
    """Result evidence no gate may alter while auditing it.

    Covers experiments/ plus the canonical results.json and results/*.json:
    the ARC-Bench requirements make results.json the authoritative carrier of
    the hypothesis verdicts and metrics, so a gate that rewrote it would be
    just as destructive as the smoke slice that clobbered RESULT.json.
    """
    out: list[Path] = []
    root = ws / "experiments"
    if root.is_dir():
        out.extend(p for p in root.rglob("*.json") if p.is_file())
    top = ws / "results.json"
    if top.is_file():
        out.append(top)
    res = ws / "results"
    if res.is_dir():
        out.extend(p for p in res.rglob("*.json") if p.is_file())
    return sorted(p for p in set(out) if p.name not in _GATE_OWN_PRODUCTS)


def _evidence_snapshot(ws: Path) -> dict[Path, bytes]:
    out = {}
    for p in _evidence_files(ws):
        try:
            out[p] = p.read_bytes()
        except OSError:
            continue
    return out


def _restore_evidence(ws: Path, before: dict[Path, bytes]) -> list[str]:
    """Undo evidence writes and report what was touched (changed or created)."""
    touched: list[str] = []
    for p, blob in before.items():
        try:
            if not p.exists() or p.read_bytes() != blob:
                touched.append(str(p.relative_to(ws)))
                p.write_bytes(blob)
        except OSError:
            continue
    for p in _evidence_files(ws):
        if p not in before:
            touched.append(str(p.relative_to(ws)))
            try:
                p.unlink()
            except OSError:
                pass
    return sorted(set(touched))


def _fairness_scope(out: str) -> str | None:
    """Read `evidence_crossvalidation.scope` out of fairness_gate's stdout JSON.
    Returns None when the payload cannot be parsed, so a malformed run is never
    mistaken for an evidence-free one."""
    try:
        doc = json.loads(out[out.index("{"):out.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return None
    cv = doc.get("evidence_crossvalidation")
    return cv.get("scope") if isinstance(cv, dict) else None


def gate_fairness_gate(ws: Path, opts) -> dict:
    rc, out, dur = _run("fairness_gate.py", [str(ws)], opts.timeout)
    if rc == 3:
        return _result("fairness_gate", "15.5", "SKIP", "no_fairness_ledger",
                       out, dur)
    if rc != 0:
        return _result("fairness_gate", "15.5", "FAIL", "fairness_violation",
                       out, dur)
    # A ledger with no co-located raw evidence is scored `ledger_only`: the six
    # self-report checks ran but the cross-validation layer could not, so the
    # fairness guarantee is absent here rather than satisfied. Mode B never
    # reaches this branch (RUNSTATE/events always exist); in Mode A this is how
    # an evidence-free ledger would otherwise read as a clean PASS.
    if _fairness_scope(out) == "ledger_only":
        return _result("fairness_gate", "15.5", "UNPROTECTED",
                       "fairness_crossvalidation_no_raw_evidence", out, dur)
    return _result("fairness_gate", "15.5", "PASS", "ok", out, dur)


def gate_submission_ready(ws: Path, opts) -> dict:
    """Wrap-up composite gate. Both MAJOR_REV (exit 1) and NOT_READY (exit 2)
    fail here, matching the kernel: gates.py maps exit 1 to WARN, and WARN is
    not in commit_boundary's pass set {PASS, SKIP, NOT_APPLICABLE}, so Mode B
    blocks the 15.5 boundary on MAJOR_REV too. Reporting it as a non-failing
    WARN would tell a Mode A user their run is submittable when the same run
    would be refused under Mode B. The reason_code keeps the two tiers
    distinguishable."""
    if not ((ws / "paper" / "main.pdf").is_file()
            or _runstate(ws).get("status") == "completed"):
        return _result("submission_ready", "15.5", "SKIP", "pre_submission_workspace",
                       "paper/main.pdf absent and RUNSTATE not completed")
    rc, out, dur = _run("submission_ready.py", [str(ws)], opts.timeout)
    if rc == 0:
        status, reason = "PASS", "ok"
    elif rc == 1:
        status, reason = "FAIL", "major_revision_required"
    else:
        status, reason = "FAIL", "not_submission_ready"
    return _result("submission_ready", "15.5", status, reason, out, dur)


def gate_sciforge_audit(ws: Path, opts) -> dict:
    """Composite figure+verdict+template audit. The kernel does not invoke it
    (wrap_up defers pipeline_audit to the host), so gate_all is its only
    mechanical entry point in either mode."""
    if not _has_paper(ws):
        return _result("sciforge_audit", "16", "SKIP", "no_manuscript",
                       "paper/main.tex absent")
    rc, out, dur = _run("sciforge_audit.py", [str(ws)], opts.timeout)
    return _result("sciforge_audit", "16", "PASS" if rc == 0 else "FAIL",
                   "ok" if rc == 0 else "audit_failed", out, dur)


def gate_completion_gate(ws: Path, opts) -> dict:
    rc, out, dur = _run("completion_gate.py", [str(ws)], opts.timeout)
    return _std_result("completion_gate", "16", rc, out, dur, "claimed_artifact_missing")


def gate_workspace_hygiene(ws: Path, opts) -> dict:
    rc, out, dur = _run("workspace_hygiene.py", [str(ws)], opts.timeout)
    return _std_result("workspace_hygiene", "16", rc, out, dur,
                       "workspace_hygiene_violation")


def gate_s2_audit(ws: Path, opts) -> dict:
    rc, out, dur = _run("s2_audit.py", [str(ws), "--quiet"], opts.timeout)
    return _std_result("s2_audit", "16", rc, out, dur, "completeness_audit_failed")


def gate_claim_anchor(ws: Path, opts) -> dict:
    """Kernel registers nodes at 6b/6c and anchors claims at 10. Mode A has no
    equivalent, so a missing registry is UNPROTECTED, never a quiet SKIP."""
    reg = _read_json(ws / ".sciforge" / "nodes" / "NODES.json")
    nodes = (reg or {}).get("nodes") if isinstance(reg, dict) else None
    if not nodes:
        if _has_claim_evidence(ws):
            return _result(
                "claim_anchor", "10", "UNPROTECTED", "nodes_registry_absent",
                "NODES.json is written by the kernel at the 6b/6c experiment "
                "boundaries (nodes.auto_register) and claims are anchored at phase 10; "
                "with no registry the claim→node→hash triangle is not enforced")
        return _result("claim_anchor", "10", "SKIP", "no_claims_or_experiment_evidence",
                       "no claims file, manuscript, or experiment result yet")
    rc, out, dur = _run("claim_anchor_gate.py", [str(ws)], opts.timeout)
    return _std_result("claim_anchor", "10", rc, out, dur, "claim_anchor_violation")


# ---------------------------------------------------------------------------
# registry (pipeline order)
# ---------------------------------------------------------------------------

GATES = [
    ("validate_verdicts", "0", gate_validate_verdicts),
    ("rep_plan_present", "2", gate_rep_plan_present),
    ("gap_gate", "4broad", gate_gap_gate),
    ("citation_relevance", "4broad", gate_citation_relevance),
    ("registry_hash", "5", gate_registry_hash),
    ("security_scan", "6b/6c", gate_security_scan),
    ("dep_gate", "6b/6c", gate_dep_gate),
    ("integrity_monitor", "6b/6c", gate_integrity_monitor),
    ("smoke_gate", "6c", gate_smoke_gate),
    ("s2_ladder", "6c", gate_s2_ladder),
    ("inv_g1", "9", gate_inv_g1),
    ("claim_anchor", "10", gate_claim_anchor),
    ("s2_ablation", "10", gate_s2_ablation),
    ("arb_verify", "10", gate_arb_verify),
    ("tdal_compute", "10", gate_tdal),
    ("figure_embedding", "11", gate_figure_embedding),
    ("figure_style", "11", gate_figure_style),
    ("quality_gate", "12", gate_quality_gate),
    ("fantasy_gate", "12", gate_fantasy_gate),
    ("leakage_scan", "13", gate_leakage_scan),
    ("compile_audit", "13", gate_compile_audit),
    ("citation_audit", "15", gate_citation_audit),
    ("citation_support", "15", gate_citation_support),
    ("doi_gate", "15", gate_doi_gate),
    ("fairness_gate", "15.5", gate_fairness_gate),
    ("submission_ready", "15.5", gate_submission_ready),
    ("sciforge_audit", "16", gate_sciforge_audit),
    ("completion_gate", "16", gate_completion_gate),
    ("workspace_hygiene", "16", gate_workspace_hygiene),
    ("s2_audit", "16", gate_s2_audit),
]
GATE_NAMES = [name for name, _phase, _fn in GATES]

# Gate names whose phase is an interval ("6b/6c") use the earliest boundary.
_EARLIEST = {"6b/6c": "6b"}


def _gate_phase_rank(phase: str) -> int:
    return _rank(_EARLIEST.get(phase, phase))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def run_all(ws: Path, opts) -> dict:
    ws = Path(ws)
    rank = _current_rank(ws)
    stale = _cursor_stale(ws)
    only = set(opts.only or [])
    skip = set(opts.skip or [])
    unknown = sorted((only | skip) - set(GATE_NAMES))
    if unknown:
        raise ValueError(f"unknown gate name(s) in --only/--skip: {unknown}; "
                         f"known: {GATE_NAMES}")

    rows = []
    if stale:
        d, e = _declared_rank(ws), _evidence_rank(ws)
        rows.append(_result(
            "runstate_cursor", "0", "WARN", "runstate_cursor_stale",
            "RUNSTATE declares phase "
            f"{PHASE_ORDER[d] if d is not None else '(none)'} but on-disk "
            f"artifacts prove {PHASE_ORDER[e]}; the cursor is not trustworthy "
            "in this workspace, so gates run on artifact evidence instead. "
            "Rewrite RUNSTATE at every boundary to restore a real cursor."))
    for name, phase, fn in GATES:
        if only and name not in only:
            continue
        if name in skip:
            continue
        if rank is not None and rank < _gate_phase_rank(phase):
            rows.append(_result(name, phase, "SKIP", "phase_not_reached",
                                f"workspace cursor is below phase {phase}"))
            continue
        # Per-gate evidence guard. smoke_gate learned this the hard way: its
        # re-execution overwrote a 60-cell result with a 1-replicate slice.
        # Any gate that runs code can do the same, so the battery enforces the
        # invariant centrally and names the offending gate rather than
        # trusting each one to police itself.
        before = _evidence_snapshot(ws)
        try:
            row = fn(ws, opts)
        except Exception as exc:  # a broken gate must not abort the battery
            row = _result(name, phase, "ERROR", "gate_crashed",
                          f"{type(exc).__name__}: {exc}")
        touched = _restore_evidence(ws, before)
        if touched:
            row = _result(name, phase, "FAIL", "gate_mutated_evidence",
                          "this gate changed experiment evidence while auditing "
                          "it; the files were restored: " + ", ".join(touched[:8]))
        rows.append(row)

    counts = {s: 0 for s in STATUSES}
    for r in rows:
        counts[r["status"]] += 1
    failed = [r["gate"] for r in rows if r["status"] in FAILING]
    unprotected = [{"gate": r["gate"], "reason_code": r["reason_code"],
                    "detail": r["detail"]} for r in rows if r["status"] == "UNPROTECTED"]
    return {
        "workspace": str(ws),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "mode": _detect_mode(ws),
        "phase_cursor": rank,
        "gates": rows,
        "summary": {
            "counts": counts,
            "ok": not failed,
            "failed_gates": failed,
            "unprotected_gates": unprotected,
        },
        "exit_code": 1 if failed else 0,
    }


def _print_table(report: dict) -> None:
    rows = report["gates"]
    w = max([len("GATE")] + [len(r["gate"]) for r in rows] + [14])
    print(f"{'GATE'.ljust(w)}  {'STATUS':<11}  {'PHASE':<7}  {'TIME':>7}  REASON")
    print("-" * (w + 46))
    for r in rows:
        print(f"{r['gate'].ljust(w)}  {r['status']:<11}  {r['phase']:<7}  "
              f"{r['duration_s']:>6.2f}s  {r['reason_code']}")
    c = report["summary"]["counts"]
    order = ["PASS", "WARN", "SKIP", "UNPROTECTED", "INFO", "FAIL", "BLOCKED", "ERROR"]
    print()
    print("Summary: " + " | ".join(f"{s} {c[s]}" for s in order if c[s]))
    failed = report["summary"]["failed_gates"]
    if failed:
        print("Failing gates: " + ", ".join(failed))
    unprotected = report["summary"]["unprotected_gates"]
    if unprotected:
        print()
        print("UNPROTECTED — guarantees NOT in force for this run:")
        for u in unprotected:
            print(f"  - {u['gate']} ({u['reason_code']}): {u['detail']}")
    elif not failed:
        print("All applicable gates passed or legitimately skipped.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Run every applicable SciForge mechanical gate against a "
                    "run workspace and print one report (Mode A entry point).")
    ap.add_argument("workspace", type=Path, nargs="?")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument("--only", default="", help="comma-separated gate names to run")
    ap.add_argument("--skip", default="", help="comma-separated gate names to skip")
    ap.add_argument("--offline", action="store_true",
                    help="doi_gate: structure-only, no network resolution")
    ap.add_argument("--integrity-llm", action="store_true",
                    help="integrity_monitor: also run the semantic D1 tier "
                         "(requires configured providers)")
    ap.add_argument("--timeout", type=int, default=600,
                    help="per-gate timeout in seconds (default 600)")
    ap.add_argument("--list", action="store_true", help="list gate names and exit")
    args = ap.parse_args(argv)

    if args.list:
        for name, phase, _fn in GATES:
            print(f"{name}\t{phase}")
        return 0

    if args.workspace is None:
        print("gate_all: a workspace path is required (or use --list)", file=sys.stderr)
        return 2
    ws = args.workspace
    if not ws.is_dir():
        print(f"gate_all: workspace not found: {ws}", file=sys.stderr)
        return 2
    if not (ws / ".sciforge").exists() and not any(ws.iterdir()):
        print(f"gate_all: {ws} is empty and not a run workspace", file=sys.stderr)
        return 2

    args.only = [s.strip() for s in args.only.split(",") if s.strip()]
    args.skip = [s.strip() for s in args.skip.split(",") if s.strip()]
    try:
        report = run_all(ws, args)
    except ValueError as exc:
        print(f"gate_all: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_table(report)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())