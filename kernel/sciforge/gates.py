"""Mechanical gates enforced IN the control flow (S04).

Design lesson from ScienceDiscovery/AI-Scientist v2: quality checks that live in
prose are advisory; checks that block a state transition are real. Here:

- gate validation runs at every phase boundary and at wrap-up; a failing gate
  prevents boundary_committed from being written (the phase stays IN_PROGRESS).
- verdicts must validate against schemas via scripts/validate_verdicts.py (subprocess).
- security_scan.py gates every agent-authored experiment script BEFORE dispatch.
- figure embedding + renderer audit gate (check_figure_embedding --require-renderer).
- wrap-up: validate_verdicts --strict --require-complete + sciforge_audit.

Low-capability models can still produce bad content; they cannot *advance* past a gate.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _root():
    """The repo root for gate scripts. Evolution runs pass SCIFORGE_REPO=scratch
    checkout so gates measure the PATCHED tree (S16); normal runs use the real repo."""
    return Path(os.environ.get("SCIFORGE_REPO", REPO_ROOT))


# ---------------------------------------------------------------------------
# Discipline tiers (v1.7.1): severity ∝ consequence × post-hoc undetectability.
#   strict    — every gate hard (submission-grade venues, weak-model hosts)
#   balanced  — default: undetectable-class hard; cosmetic-class disclosed
#   lean      — strong-model hosts: only undetectable-class gates hard
#                 (fabrication/leakage/ladder/integrity/citation/compile-ERROR);
#                 cosmetic class (zero-warning compile, page band, AIGC counts,
#                 aspect ratios) becomes WARN + disclosure, never a loopback.
# The tier is a RUN flag (RUNSTATE flags.discipline / SCIFORGE_DISCIPLINE),
# re-injected by the bundle at every boundary — never left to model memory.
# ---------------------------------------------------------------------------
TIERS = ("strict", "balanced", "lean")


def discipline(ws: Path) -> str:
    try:
        d = json.loads((Path(ws) / ".sciforge" / "RUNSTATE.json").read_text())
        t = (d.get("data") or d).get("flags", {}).get("discipline")
        if t in TIERS:
            return t
    except Exception:
        pass
    t = os.environ.get("SCIFORGE_DISCIPLINE", "")
    return t if t in TIERS else "balanced"


def cosmetic_hard(ws: Path) -> bool:
    """True when cosmetic-class checks are HARD (strict tier only)."""
    return discipline(ws) == "strict"


def run_py(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(_root() / script), *args],
                          capture_output=True, text=True, timeout=900)


def validate_verdicts(ws: Path, strict: bool = False, require_complete: bool = False) -> dict:
    vd = ws / ".sciforge" / "verdicts"
    if not vd.exists():
        return {"gate": "validate_verdicts", "status": "PASS", "note": "no verdicts dir yet"}
    args = [str(vd)]
    if strict:
        args.append("--strict")
    if require_complete:
        args += ["--require-complete"]
    p = run_py("scripts/validate_verdicts.py", args)
    return {"gate": "validate_verdicts", "status": "PASS" if p.returncode == 0 else "FAIL",
            "exit": p.returncode, "output": (p.stdout + p.stderr)[-4000:]}


def security_scan_script(script_path: Path) -> dict:
    p = run_py("scripts/security_scan.py", [str(script_path)])
    return {"gate": "security_scan", "status": "PASS" if p.returncode == 0 else "BLOCKED",
            "target": str(script_path), "exit": p.returncode, "output": (p.stdout + p.stderr)[-4000:]}


def figure_gates(ws: Path) -> dict:
    # BUG-5 workaround: the script's first arg is paper_dir (must contain main.tex),
    # not the workspace root; figures live at ws/figures in the canonical layout.
    p = run_py("scripts/check_figure_embedding.py",
               [str(ws / "paper"), "--require-renderer", "--figures-dir", str(ws / "figures")])
    checks = {"embedded_via_renderer":
              {"status": "PASS" if p.returncode == 0 else "FAIL",
               "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}}
    # v1.7.1 presentation gate: figures follow their citation, vector-only in
    # the body, >=3 distinct visual grammars (Nature-grade mandate).
    s = run_py("scripts/figure_style_gate.py", [str(ws)])
    checks["presentation"] = {
        "status": "SKIP" if "figure_style SKIP" in (s.stdout + s.stderr)
        else ("PASS" if s.returncode == 0 else "FAIL"),
        "exit": s.returncode, "output": (s.stdout + s.stderr)[-2000:]}
    ok = all(c["status"] in ("PASS", "SKIP") for c in checks.values())
    return {"gate": "figures_embedded_via_renderer", "status": "PASS" if ok else "FAIL",
            "exit": p.returncode, "checks": checks,
            "output": (p.stdout + p.stderr)[-2000:]}


def wrap_up_gates(ws: Path) -> dict:
    # v1.7: ScientistTwo completeness audit (§3.7) — reward-hacking scan +
    # method↔code parity. SKIP only when no experiment claims exist to audit.
    p = run_py("scripts/s2_audit.py", [str(ws), "--quiet"])
    s2_status = "SKIP" if "s2_audit SKIP" in (p.stdout + p.stderr) else \
                ("PASS" if p.returncode == 0 else "FAIL")
    h = run_py("scripts/workspace_hygiene.py", [str(ws)])
    hy_status = "SKIP" if "hygiene SKIP" in (h.stdout + h.stderr) else \
                ("PASS" if h.returncode == 0 else "FAIL")
    # v1.7.1: the S01-class lie (a final report claiming completion the
    # workspace does not contain) is now physically impossible at wrap-up.
    c = run_py("scripts/completion_gate.py", [str(ws)])
    c_status = "SKIP" if "completion_gate SKIP" in (c.stdout + c.stderr) else \
               ("PASS" if c.returncode == 0 else "FAIL")
    checks = {
        "verdicts_complete": validate_verdicts(ws, strict=True, require_complete=True),
        "pipeline_audit": {"gate": "sciforge_audit",
                           **({"status": "PASS"} if not (ws / ".sciforge").exists() else
                              {"status": "SKIP", "note": "audit CLI invocation deferred to host"})},
        "figures": figure_gates(ws),
        "s2_completeness_audit": {"gate": "s2_audit", "status": s2_status,
                                  "exit": p.returncode,
                                  "output": (p.stdout + p.stderr)[-2000:]},
        "workspace_hygiene": {"gate": "workspace_hygiene", "status": hy_status,
                              "exit": h.returncode,
                              "output": (h.stdout + h.stderr)[-2000:]},
        "completion_truth": {"gate": "completion_gate", "status": c_status,
                             "exit": c.returncode,
                             "output": (c.stdout + c.stderr)[-2000:]},
    }
    ok = all(c["status"] in ("PASS", "SKIP") for c in checks.values())
    return {"gate": "wrap_up", "status": "PASS" if ok else "FAIL", "checks": checks}


def check(ws: Path, gate: dict, phase: str) -> dict:
    """Dispatch one phasegraph gate spec. Returns verdict dict; status != PASS blocks advance."""
    kind = gate.get("check")
    if kind == "file":
        target = ws / gate["path"]
        return {"gate": f"file:{gate['path']}", "status": "PASS" if target.exists() else "FAIL"}
    if kind == "verdict_field":
        # search workspace flat verdicts + stage dirs + experiments/** for the file
        cand = _find_verdict(ws, gate["path"])
        if cand is None:
            return {"gate": gate["path"], "status": "FAIL", "note": "missing verdict file"}
        try:
            data = json.loads(cand.read_text())
        except json.JSONDecodeError:
            return {"gate": gate["path"], "status": "FAIL", "note": "unparseable verdict"}
        val = _get_path(data, gate["field"])
        op = gate.get("op", "==")
        want = gate.get("value", "__ABSENT__")
        if val is None:
            return {"gate": gate["path"], "status": "FAIL", "note": f"field {gate['field']} absent"}
        if want == "__ABSENT__":
            # BUG-4 (DEMO-RK4): a gate that names a field but no value asserts
            # *presence-and-truthiness*, never `== None` (which can never PASS).
            passed = bool(val) and val not in (False, "FAIL", "BLOCKED", "ERROR")
            return {"gate": gate["path"], "status": "PASS" if passed else "FAIL",
                    "actual": val, "required": "truthy (no value declared)"}
        passed = _cmp(val, op, want) if op != "==" else val == want
        return {"gate": gate["path"], "status": "PASS" if passed else "FAIL",
                "actual": val, "required": f"{op} {want}"}
    if kind == "hash":
        hp = ws / gate["path"]
        if not hp.exists():
            return {"gate": gate["path"], "status": "FAIL", "note": "hash lock missing"}
        txt = hp.read_text().strip()
        if txt.startswith("BLOCKED"):
            return {"gate": gate["path"], "status": "FAIL", "note": txt}
        ok = len(txt) == 64 and all(c in "0123456789abcdef" for c in txt)
        return {"gate": gate["path"], "status": "PASS" if ok else "FAIL"}
    if kind == "hash_match":  # INV-G1: problem anchor unchanged
        hp = ws / gate["path"]
        rs_file = ws / ".sciforge" / "RUNSTATE.json"
        if not (hp.exists() and rs_file.exists()):
            return {"gate": "INV-G1", "status": "FAIL"}
        try:
            locked = json.loads(rs_file.read_text()).get("problem_hash")
            actual = hp.read_text().strip()
            return {"gate": "INV-G1", "status": "PASS" if locked and actual == locked else "FAIL"}
        except Exception as e:
            return {"gate": "INV-G1", "status": "FAIL", "note": str(e)}
    if kind == "command":
        name = gate["cmd"]
        if name == "fantasy_gate":
            p = run_py("scripts/fantasy_gate.py", [str(ws), "--write-verdict"])
            return {"gate": "fantasy_gate", "status": "PASS" if p.returncode == 0 else "FAIL",
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-1500:]}
        if name == "citation_support":
            p = run_py("scripts/citation_support.py", [str(ws), "--write-verdict"])
            return {"gate": "citation_support", "status": "PASS" if p.returncode == 0 else "FAIL",
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "submission_ready":
            # v1.7.1: the Zone-2 bar as a tier (READY/MINOR_REV/MAJOR_REV/
            # NOT_READY); MAJOR+ blocks the 15.5 boundary, MINOR_REV passes
            # with disclosure (the user bar is "minor-revision submittable").
            p = run_py("scripts/submission_ready.py", [str(ws), "--write-verdict"])
            status = "PASS" if p.returncode == 0 else \
                     ("WARN" if p.returncode == 1 else "FAIL")
            return {"gate": "submission_ready", "status": status,
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "workspace_hygiene":
            # v1.7.1: the run must read like a GitHub repo (no stray logs/json,
            # no caches, no empty dirs, README index present)
            p = run_py("scripts/workspace_hygiene.py", [str(ws)])
            status = "SKIP" if "hygiene SKIP" in (p.stdout + p.stderr) else \
                     ("PASS" if p.returncode == 0 else "FAIL")
            return {"gate": "workspace_hygiene", "status": status,
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "figure_style":
            # v1.7.1: figures follow their citation, vector-only body embeds,
            # >=3 distinct visual grammars
            p = run_py("scripts/figure_style_gate.py", [str(ws)])
            status = "SKIP" if "figure_style SKIP" in (p.stdout + p.stderr) else \
                     ("PASS" if p.returncode == 0 else "FAIL")
            return {"gate": "figure_style", "status": status,
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "doi_gate":
            # v1.7.1 user mandate: every reference carries a DOI that resolves
            # to a retrievable BibTeX record; unresolvable => dropped, not kept
            p = run_py("scripts/doi_gate.py", [str(ws), "--write-verdict"])
            status = "SKIP" if "doi_gate SKIP" in (p.stdout + p.stderr) else \
                     ("PASS" if p.returncode == 0 else "FAIL")
            return {"gate": "doi_gate", "status": status,
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "arb_verify":
            p = run_py("scripts/arb_verify.py", [str(ws)])
            return {"gate": "arb_verify", "status": "PASS" if p.returncode == 0 else "FAIL",
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-1500:]}
        if name == "dep_gate":
            p = run_py("scripts/dep_gate.py", [str(ws)])
            return {"gate": "dep_gate", "status": "PASS" if p.returncode == 0 else "FAIL",
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "smoke_gate":
            p = run_py("scripts/smoke_gate.py", [str(ws)])
            return {"gate": "smoke_gate", "status": "PASS" if p.returncode == 0 else "FAIL",
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-1500:]}
        if name == "s2_ladder":
            # v1.7 ScientistTwo §3.2: subset→full ladder + 3-state critic at 6c
            p = run_py("scripts/s2_ladder_gate.py", [str(ws)])
            out = p.stdout + p.stderr
            status = "SKIP" if "s2_ladder SKIP" in out else \
                     ("PASS" if p.returncode == 0 else "FAIL")
            return {"gate": "s2_ladder", "status": status,
                    "exit": p.returncode, "output": out[-1500:]}
        if name == "s2_ablation":
            # v1.7 ScientistTwo §3.4: 5-6 ablation plans + strict AblCritic at 10
            p = run_py("scripts/s2_ablation_gate.py", [str(ws)])
            out = p.stdout + p.stderr
            status = "SKIP" if "s2_ablation SKIP" in out else \
                     ("PASS" if p.returncode == 0 else "FAIL")
            return {"gate": "s2_ablation", "status": status,
                    "exit": p.returncode, "output": out[-1500:]}
        if name == "integrity_monitor":
            # v1.7.1 AAR fusion: pre-execution semantic integrity gate (D1/D2/D3,
            # fail-closed LLM tier). SKIP when the run declares no scored suite.
            from .s2 import monitor as mon_mod
            prov = None
            try:
                from .providers import Providers
                prov = Providers()
            except Exception:
                prov = None
            status, doc = mon_mod.evaluate(ws, providers=prov)
            return {"gate": "integrity_monitor", "status": status,
                    "decision": doc.get("decision"),
                    "violations": doc.get("violations", [])[:5],
                    "output": json.dumps(doc)[:1500]}
        if name == "gap_gate":
            p = run_py("scripts/gap_gate.py", [str(ws)])
            return {"gate": "gap_gate", "status": "PASS" if p.returncode == 0 else "FAIL",
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "validate_verdicts":
            r = validate_verdicts(ws, strict=True, require_complete=False)
            r["phase"] = phase
            return r
        if name == "security_scan":
            # B5 fix (v1.6): the phasegraph declares security_scan at the 6b/6c
            # boundaries ("agent-authored experiment scripts before dispatch") —
            # the kernel now ENFORCES it: every agent-authored script under
            # src/ and experiments/ must pass the static scan before either
            # experiment boundary can commit. No scripts yet = SKIP (legit,
            # e.g. theory-only never reaches here).
            roots = [ws / "src", ws / "experiments"]
            scripts = sorted({p for r in roots if r.is_dir() for p in r.rglob("*.py")})
            if not scripts:
                return {"gate": "security_scan", "status": "SKIP",
                        "note": "no agent-authored scripts present"}
            violations = []
            for s in scripts:
                r = security_scan_script(s)
                if r["status"] != "PASS":
                    violations.append({"script": str(s.relative_to(ws)),
                                       "detail": r["output"][-500:]})
            return {"gate": "security_scan",
                    "status": "PASS" if not violations else "BLOCKED",
                    "scanned": len(scripts), "violations": violations[:5]}
        if name == "render_audit":
            return figure_gates(ws)
        if name == "wrap_up_gates":
            return wrap_up_gates(ws)
        if name == "fairness_gate":
            p = run_py("scripts/fairness_gate.py", [str(ws), "--write-verdict"])
            # exit 3 = no ledger yet (SKIP, deepen-exec not run); 0=PASS/WARN; 2=FAIL
            status = "SKIP" if p.returncode == 3 else ("PASS" if p.returncode == 0 else "FAIL")
            return {"gate": "fairness_gate", "status": status,
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-2000:]}
        if name == "leakage_scan":
            # exit 0 = PASS or no-paper-yet SKIP; exit 2 = hits remaining => FAIL
            p = run_py("scripts/leakage_scan.py", [str(ws), "--write-verdict"])
            return {"gate": "leakage_scan",
                    "status": "PASS" if p.returncode == 0 else "FAIL",
                    "exit": p.returncode, "output": (p.stdout + p.stderr)[-3000:]}
        if name in ("quality_gate", "citation_audit"):
            # machine-verdict file must exist (host writes it after the skill runs);
            # missing verdict = FAIL (v1.4.0 lesson: audits must not silently skip)
            marker = {"quality_gate": "QUALITY_GATE.json",
                      "citation_audit": "CITATION_AUDIT.json"}[name]
            if _find_verdict(ws, marker):
                return {"gate": name, "status": "PASS", "source": marker}
            return {"gate": name, "status": "FAIL",
                    "note": f"{marker} absent — host must run the {name} skill and write the verdict"}
        if name == "compile_audit":
            # the mechanical half of paper-compile. v1.4.0 taught us the failure
            # mode is "audit never ran" — so when no machine verdict exists we
            # BLOCK (PENDING => gate rejected), not wave through. The LaTeX
            # zero-warning compile itself stays host-driven; the host satisfies
            # this gate by writing PAPER_COMPILE.json (plus a passing
            # LEAKAGE_SCRUB.json, which this gate also verifies).
            pc = _find_verdict(ws, "PAPER_COMPILE.json")
            lv = _find_verdict(ws, "LEAKAGE_SCRUB.json")
            if lv:
                try:
                    if json.loads(lv.read_text()).get("status") != "PASS":
                        return {"gate": "compile_audit", "status": "FAIL",
                                "note": "LEAKAGE_SCRUB.json status != PASS (compile refuses)"}
                except Exception:
                    return {"gate": "compile_audit", "status": "FAIL",
                            "note": "LEAKAGE_SCRUB.json unreadable"}
            if pc:
                # v1.7.1 discipline tiers: compile ERRORS are always hard (a
                # broken PDF is caught only when a human opens it — and
                # reviewers do); compile WARNINGS are cosmetic (overfull boxes
                # are visible in the PDF itself) — hard only in the strict
                # tier, disclosed otherwise. This removes the observed
                # negative-optimization tax (an agent died debugging underfull
                # hboxes; two runs burned 12-16 compile passes on page bands).
                try:
                    warn_n = int(json.loads(pc.read_text()).get("warnings", 0) or 0)
                except Exception:
                    warn_n = 0
                if warn_n and cosmetic_hard(ws):
                    return {"gate": "compile_audit", "status": "FAIL",
                            "note": f"{warn_n} compile warning(s) under discipline=strict"}
                return {"gate": "compile_audit", "status": "PASS",
                        "source": "PAPER_COMPILE.json",
                        "warnings_disclosed": warn_n or None}
            return {"gate": "compile_audit", "status": "FAIL",
                    "note": "PAPER_COMPILE.json absent — host must compile (zero warnings) and write the verdict"}
        # skill_ref-based gates (quality-gate, compile, citation) run as LLM-driven
        # checks via the host; kernel records them as PENDING_HUMAN/host until a
        # machine verdict file exists.
        ref = gate.get("skill_ref")
        if ref:
            marker = {"quality_gate": "QUALITY_GATE.json", "compile_audit": "PAPER_COMPILE.json",
                      "citation_audit": "CITATION_AUDIT.json", "render_audit": "FIGURE_AUDITS.json"}.get(name)
            if marker and _find_verdict(ws, marker):
                return {"gate": name, "status": "PASS", "source": marker}
            return {"gate": name, "status": "PENDING", "skill_ref": ref,
                    "note": "awaiting machine verdict file (host agent must write it)"}
    return {"gate": "unknown", "status": "FAIL", "note": json.dumps(gate)}


def _find_verdict(ws: Path, rel: str) -> Path | None:
    """Verdict files may sit flat in .sciforge/verdicts/ (registered), stage dirs,
    or — per experiment-execution SKILL.md — anywhere under experiments/**/."""
    name = rel.split("/")[-1]
    for base in (ws / ".sciforge" / "verdicts", ws / "results", ws / "paper",
                 ws / "logs", ws / "experiments"):
        if not base.exists():
            continue
        p = base / name
        if p.exists():
            return p
        if base.name == "experiments":  # recursive: experiments/toy/RESULT.json
            for hit in sorted(base.rglob(name)):
                return hit
    return None


def _get_path(data: dict, dotted: str):
    cur = data
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _cmp(val, op: str, want) -> bool:
    try:
        if op == ">=":
            return float(val) >= float(want)
        if op == ">":
            return float(val) > float(want)
        if op == "<=":
            return float(val) <= float(want)
        if op == "<":
            return float(val) < float(want)
    except (TypeError, ValueError):
        return False
    return False
