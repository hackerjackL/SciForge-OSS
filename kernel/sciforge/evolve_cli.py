"""`sciforge-kernel evolve` / `submit` / `daily` wiring (S15/S17/S19).

Pipeline per evolution round:
 1. collect completed/blocked run archives -> audit signals
 2. deterministic proposals + optional provider-generated proposals
 3. build Domain: GateDomain(ci/tests/golden verdict completeness) x JudgeDomain
    with frozen rubric; three-shard golden split (test held out)
 4. EvolutionRun (puct | openevolve) search under budget
 5. winner -> skill-extensions/<run_id>/ (S14 writable area, never the frozen tree)
 6. `sciforge-kernel submit` applies the winner to the real repo (human command)
 7. `daily` digests evolution state as plain text (printable/pushable anywhere)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from .evolve import (EvolutionRun, GateDomain, HybridDomain, JudgeDomain, Patch,
                     apply_patch, editable, split_shards)
from .propose import audit_run, proposals_from_signals

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "kernel" / "config" / "evolve.json"


def _load_config() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text())
    return {}


def _demo_mutator(rng_seed: int = 7):
    """Template mutation: vary the RSI-note append wording across proposals.

    Real deployment replaces this with provider.complete('ideation', ...); the
    demo keeps the search loop honest (multiple genuine variants to compare)
    without requiring keys.
    """
    variants = ["", " Track the fire-rate of this signal in LESSONS.json; when it repeats, escalate.",
                " Add a machine-checkable artifact requirement next to the note.",
                " Cap the escalation at 2 repeats to avoid contract bloat.",
                ""]
    state = {"i": 0, "seed": rng_seed}

    def mut(parent: Patch, inspire) -> Patch:
        i = state["i"] % len(variants)
        state["i"] += 1
        ops = []
        for op in parent["ops"]:
            note = variants[i]
            if note and op["new"].endswith("\n"):
                ops.append(dict(op, new=op["new"] + note))
            elif note:
                ops.append(dict(op, new=op["new"] + "\n" + note))
            else:
                ops.append(dict(op, new=op["new"].replace("\n " + (variants[(i - 1) % len(variants)]).strip(), "")))
        return Patch({"ops": ops})
    return mut


def _golden_checks(root: Path | None = None, fast: bool = False) -> list[dict]:
    """fast=True: only the quick gate subsets (demo/iteration); full = + ci_check.
    `submit` ALWAYS runs the full ci_check post-merge regardless of this flag."""
    cfg = _load_config()
    root = root or REPO_ROOT
    py = sys.executable  # the venv running the kernel — scratch gates must not use system python
    checks = []
    for c in cfg.get("gate_checks", []):
        if fast and c.get("id") == "ci_scratch":
            continue
        cmd = c.get("cmd", "").replace("${SCIFORGE_PY:-python3}", py)
        checks.append({**c, "cmd": cmd})
    if not fast:
        checks.append({"id": "ci_check",
                       "cmd": f"{py} {root / 'scripts' / 'ci_check.py'} --repo-root {root}",
                       "timeout": 1800, "hard": ["ci_check"]})
    return checks


def run_evolve_cli(a) -> int:
    ws = a.workspace
    (ws / ".sciforge").mkdir(parents=True, exist_ok=True)
    cfg = _load_config()
    # 1. signals from archives
    sigs = []
    if ws.is_dir():
        for run_dir in sorted(ws.iterdir()):
            if (run_dir / ".sciforge" / "events.ndjson").exists():
                sigs.append(audit_run(run_dir))
    if not sigs:
        # no archives yet: use a synthetic seed proposal to validate the machinery
        sigs = []
    # 2. proposals
    props = proposals_from_signals(sigs, REPO_ROOT) if sigs else []
    prop_file = a.proposes
    if prop_file and prop_file.exists():
        props = json.loads(prop_file.read_text())["proposals"]
    if not props:
        print(json.dumps({"status": "no_proposals",
                          "hint": "pass --proposes <patches.json> (from audit) or complete runs first"},
                         indent=2))
        return 1
    # 3. domain + shards — evolution runs on a SCRATCH checkout clone, never the
    # live repo (S16 hard line); gates also run inside it so they measure the PATCHED tree.
    evo_ws = Path(cfg.get("evo_workspace", "/tmp/sciforge-evo"))
    evo_ws.mkdir(parents=True, exist_ok=True)
    scratch = evo_ws / f"checkout_{int(time.time())}"
    subprocess.run(["git", "clone", "-q", str(REPO_ROOT), str(scratch)], timeout=300, check=True)
    gate = GateDomain(_golden_checks(scratch, fast=getattr(a, "fast", False)))
    judge = None
    try:
        from .providers import Providers
        p = Providers()
        if not p.host_mode:
            judge = JudgeDomain(p, rubric_path=cfg.get("rubric_path"))
    except Exception:
        judge = None
    domain = HybridDomain(gate, judge) if judge else gate
    seed = Patch({"ops": props[0]["ops"] if "ops" in props[0] else [props[0]]})
    # shard_check: candidate may only touch editable paths and golden gate shard
    def shard_check(patch: Patch) -> bool:
        return all(editable(op["path"]) for op in patch["ops"])
    er = EvolutionRun(scratch, domain, _demo_mutator(), algorithm=a.algorithm,
                      budget=a.budget, seed_patch=seed, shard_check=shard_check)
    # rewire apply to scratch
    from . import evolve as evolve_mod
    orig_apply = evolve_mod.apply_patch
    orig_revert = evolve_mod.revert_patch
    def scratch_apply(ws, patch, checkout=None):
        return orig_apply(ws, patch, checkout=scratch)
    def scratch_revert(ws, applied):
        if applied:
            subprocess.run(["git", "checkout", "--", *applied], cwd=str(scratch), capture_output=True)
    evolve_mod.apply_patch = scratch_apply
    evolve_mod.revert_patch = scratch_revert
    try:
        result = er.run()
    finally:
        evolve_mod.apply_patch = orig_apply
        evolve_mod.revert_patch = orig_revert
    # 5. winner -> extensions
    out = {"result_status": result.get("status"),
           "best_score": result.get("best_score"),
           "held_out": result.get("held_out"),
           "events": result.get("events"),
           "expanded": len(result.get("history", []))}
    if result.get("status") == "done" and result.get("best_score", 0) > 0.6:
        run_id = f"evo_{int(time.time())}"
        ext = ws / ".sciforge" / "skill-extensions" / run_id
        ext.mkdir(parents=True, exist_ok=True)
        (ext / "patch.json").write_text(json.dumps(result["best_patch"], indent=2, ensure_ascii=False))
        (ext / "meta.json").write_text(json.dumps({
            "run_id": run_id, "score": result["best_score"], "held_out": result.get("held_out"),
            "created_at": time.time(), "status": "PENDING_HUMAN_MERGE"}, indent=2))
        out["extension"] = str(ext)
        out["next"] = f"sciforge-kernel submit --workspace {ws} {run_id}"
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["result_status"] == "done" else 1


def submit_patch(a) -> int:
    """Human-authorized merge: apply extension patch to the real repo via PR-style commit."""
    ext = a.workspace / ".sciforge" / "skill-extensions" / a.run_id
    meta = json.loads((ext / "meta.json").read_text())
    if meta["status"] != "PENDING_HUMAN_MERGE":
        print(json.dumps({"status": "rejected", "reason": f"state={meta['status']}"}))
        return 1
    patch = Patch({"ops": json.loads((ext / "patch.json").read_text())})
    res = apply_patch(REPO_ROOT, patch)  # real repo only at submit time
    if not res["ok"]:
        print(json.dumps({"status": "rejected", "detail": res}))
        return 1
    # CI gate MUST pass on the real repo after merge (choice pressure, not trust)
    ci = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "ci_check.py"), ],
                        capture_output=True, text=True, timeout=1800)
    if ci.returncode != 0:
        from .evolve import revert_patch
        revert_patch(REPO_ROOT, res["applied"])
        print(json.dumps({"status": "rolled_back", "reason": "ci_check failed post-merge",
                          "tail": (ci.stdout + ci.stderr)[-800:]}))
        return 1
    meta["status"] = "MERGED"
    (ext / "meta.json").write_text(json.dumps(meta, indent=2))
    msg = f"evolve({a.run_id}): merge skill patch score={meta['score']:.2f} held_out={meta.get('held_out')}"
    subprocess.run(["git", "add", *res["applied"], ".sciforge/"], cwd=str(REPO_ROOT), check=True)
    subprocess.run(["git", "-c", "user.name=sciforge-evolve", "-c",
                    "user.email=evolve@sciforge.local", "commit", "-m", msg],
                   cwd=str(REPO_ROOT), capture_output=True, text=True)
    print(json.dumps({"status": "merged", "applied": res["applied"], "commit": msg}))
    return 0


def daily_digest(ws: Path) -> str:
    """Plain-text daily report (S17): runs, budgets, evolution rounds, pending merges."""
    lines = [f"# SciForge daily digest — {time.strftime('%Y-%m-%d')}", ""]
    n_runs = 0
    if ws.is_dir():
        for d in sorted(ws.iterdir()):
            rs = d / ".sciforge" / "RUNSTATE.json"
            if not rs.exists():
                continue
            n_runs += 1
            try:
                s = json.loads(rs.read_text())
                lines.append(f"- {s.get('run_id')}: phase {s.get('current_phase')} "
                             f"[{s.get('status')}] budget ${json.loads((d / '.sciforge' / 'verdicts' / 'RUN_BUDGET.json').read_text()).get('api_cost_usd', 0):.2f}")
            except Exception:
                lines.append(f"- {d.name}: (unreadable state)")
    ext = ws / ".sciforge" / "skill-extensions"
    if ext.exists():
        for e in sorted(ext.iterdir()):
            try:
                m = json.loads((e / "meta.json").read_text())
                lines.append(f"- evolution {e.name}: {m['status']} score={m['score']:.2f}")
            except Exception:
                pass
    lines.append(f"\ntotal runs: {n_runs}")
    return "\n".join(lines)
