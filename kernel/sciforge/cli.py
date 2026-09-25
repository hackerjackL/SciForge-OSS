"""SciForge kernel CLI (S09): run/resume/status/step/approve/deny/gate/doctor/evolve/submit.

No UI by design: one command surface, headless-first, works over SSH.
`run` drives the loop with a host agent (claude/codex) or manual bundle protocol.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import skills_pack
from .approvals import Approvals
from .execution import dispatch, group_status, plan_device, sandbox_cmd, worker_pool
from .gates import run_py
from .pipeline import Kernel
from .state import EventLog, RunState, recover


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sciforge-kernel",
                                 description="SciForge runtime kernel (control plane for skill assets)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="start or resume a pipeline run on a workspace")
    p_run.add_argument("--workspace", type=Path, required=True)
    p_run.add_argument("--problem", help="research question (required for fresh runs)")
    p_run.add_argument("--run-id", default=None)
    p_run.add_argument("--effort", default="balanced",
                       choices=["lite", "balanced", "max", "beast"])
    p_run.add_argument("--host", choices=["auto", "claude", "codex", "manual"], default="auto")
    p_run.add_argument("--test-mode", action="store_true")
    p_run.add_argument("--human-skip", action="store_true")
    p_run.add_argument("--max-steps", type=int, default=60)
    p_run.add_argument("--loop", action="store_true",
                       help="loop until done/blocked (headless overnight)")

    p_step = sub.add_parser("step", help="advance exactly one phase boundary")
    p_step.add_argument("--workspace", type=Path, required=True)

    p_res = sub.add_parser("resume", help="replay events and continue a crashed run")
    p_res.add_argument("--workspace", type=Path, required=True)
    p_res.add_argument("--loop", action="store_true")

    p_st = sub.add_parser("status", help="RUNSTATE + verdict trail + budget summary")
    p_st.add_argument("--workspace", type=Path, required=True)

    p_ap = sub.add_parser("approve", help="decide a pending checkpoint")
    p_ap.add_argument("--workspace", type=Path, required=True)
    p_ap.add_argument("checkpoint", nargs="?", help="omit to list pending")
    p_ap.add_argument("--deny", action="store_true")
    p_ap.add_argument("--note", default="")

    p_g = sub.add_parser("gate", help="run a mechanical gate standalone")
    p_g.add_argument("--workspace", type=Path, required=True)
    p_g.add_argument("which", choices=["verdicts", "wrapup", "figures"])

    p_do = sub.add_parser("doctor", help="environment self-check (S28)")
    p_do.add_argument("--json", action="store_true")

    p_dis = sub.add_parser("dispatch", help="sandbox-gated experiment dispatch")
    p_dis.add_argument("--workspace", type=Path, required=True)
    p_dis.add_argument("--script", type=Path, required=True)
    p_dis.add_argument("--args", nargs="*", default=[])
    p_dis.add_argument("--group", default=None)
    p_dis.add_argument("--seed", type=int, default=None)
    p_dis.add_argument("--foreground", action="store_true")

    p_gs = sub.add_parser("jobs", help="group STATUS.json aggregation")
    p_gs.add_argument("--workspace", type=Path, required=True)
    p_gs.add_argument("--group", required=True)

    p_ev = sub.add_parser("evolve", help="RSI skill-library evolution (S15, needs kernel/config/evolve.json)")
    p_ev.add_argument("--workspace", type=Path, required=True, help="archive dir with completed runs")
    p_ev.add_argument("--proposes", type=Path, required=True, help="patches JSON (from `evolve-analyze`)")
    p_ev.add_argument("--budget", type=int, default=8, help="max candidate expansions")
    p_ev.add_argument("--algorithm", choices=["puct", "openevolve"], default="puct")
    p_ev.add_argument("--fast", action="store_true",
                       help="quick gate subsets only (demo/iteration; submit still runs full ci_check)")

    p_sub = sub.add_parser("submit", help="accept an evolved skill patch into skill-extensions")
    p_sub.add_argument("--workspace", type=Path, required=True)
    p_sub.add_argument("run_id")

    p_dr = sub.add_parser("daily", help="evolution/progress daily digest -> text (S17)")
    p_dr.add_argument("--workspace", type=Path, required=True)

    p_srv = sub.add_parser("serve", help="headless daemon: queue + HTTP control (loopback :4510)")
    p_srv.add_argument("--archive", type=Path, required=True, help="runs archive dir")
    p_srv.add_argument("--port", type=int, default=4510)
    p_srv.add_argument("--host-agent", choices=["manual", "claude", "codex"], default="manual")
    p_srv.add_argument("--effort", default="balanced",
                       choices=["lite", "balanced", "max", "beast"])

    p_ca = sub.add_parser("cache", help="verified-reference cache (S24)")
    p_ca.add_argument("what", choices=["lookup", "put", "stats"])
    p_ca.add_argument("--id", default=None)
    p_ca.add_argument("--kind", default="auto")
    p_ca.add_argument("--verified", action="store_true")
    p_ca.add_argument("--payload", default="{}")

    p_px = sub.add_parser("proxy", help="literature-proxy auto-discovery (S24)")
    p_px.add_argument("--write", type=Path, default=None,
                       help="write discovery result JSON to this path")

    a = ap.parse_args(argv)

    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "step":
        k = Kernel(a.workspace)
        print(json.dumps(k.step(), indent=2, ensure_ascii=False))
        return 0
    if a.cmd == "resume":
        k = Kernel(a.workspace)
        action = recover(k.log, k.rs, k.ws)
        print(f"recovery: {action}")
        if action == "fresh":
            print("nothing to resume"); return 1
        r = k.run() if a.loop else k.step()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    if a.cmd == "status":
        return cmd_status(a)
    if a.cmd == "approve":
        return cmd_approve(a)
    if a.cmd == "gate":
        return cmd_gate(a)
    if a.cmd == "doctor":
        return cmd_doctor(a)
    if a.cmd == "dispatch":
        return cmd_dispatch(a)
    if a.cmd == "jobs":
        print(json.dumps(group_status(a.workspace, a.group), indent=2)); return 0
    if a.cmd == "evolve":
        from .evolve_cli import run_evolve_cli
        return run_evolve_cli(a)
    if a.cmd == "submit":
        from .evolve_cli import submit_patch
        return submit_patch(a)
    if a.cmd == "daily":
        from .evolve_cli import daily_digest
        print(daily_digest(a.workspace))
        return 0
    if a.cmd == "serve":
        from .daemon import serve
        serve(a.archive, port=a.port, run_host=a.host_agent, effort=a.effort)
        return 0
    if a.cmd == "cache":
        from . import litcache
        if a.what == "stats":
            print(json.dumps(litcache.stats(), indent=2))
        elif a.what == "lookup":
            r = litcache.lookup(a.id, a.kind)
            print(json.dumps(r, indent=2, ensure_ascii=False) if r else '{"cache": "MISS"}')
        else:  # put
            r = litcache.put(a.id, a.verified, json.loads(a.payload), a.kind)
            print(json.dumps(r, indent=2))
        return 0
    if a.cmd == "proxy":
        from .proxy import discover
        print(json.dumps(discover(write_to=a.write), indent=2))
        return 0
    return 2


def cmd_run(a) -> int:
    ws = a.workspace
    k = Kernel(ws)
    if not a.run_id:
        a.run_id = ws.name
    host = a.host
    if host == "auto":
        host = "claude" if shutil.which("claude") else ("codex" if shutil.which("codex") else "manual")
    k.start(a.run_id, a.problem or "(resume)", a.effort, host=host,
            test_mode=a.test_mode, human_skip=a.human_skip)
    if a.loop:
        r = k.run(max_steps=a.max_steps)
    else:
        r = k.step()
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0 if r["status"] in ("advanced", "done", "halted") else 1


def cmd_status(a) -> int:
    rs = RunState(a.workspace)
    log = EventLog(a.workspace)
    ev = log.replay()
    print(json.dumps({
        "run_id": rs.data.get("run_id"), "status": rs.status,
        "current_phase": rs.data.get("current_phase"),
        "last_boundary": rs.data.get("last_completed_boundary"),
        "next_action": rs.data.get("next_action"),
        "pending": rs.data.get("pending_approvals", []),
        "reason_code": rs.data.get("reason_code"),
        "events": len(ev),
        "budget": k_budget(a.workspace),
        "integrity": skills_pack.verify(a.workspace) if (a.workspace / ".sciforge" / "skills-snapshot").exists() else {"integrity": "NOT_STAGED"},
    }, indent=2, ensure_ascii=False))
    return 0


def k_budget(ws):
    p = ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json"
    try:
        d = json.loads(p.read_text())
        return {k: d[k] for k in ("wall_clock_seconds", "api_cost_usd", "pivot_count", "ba_rounds_used", "limits") if k in d}
    except Exception:
        return {}


def cmd_approve(a) -> int:
    ap_ = Approvals(a.workspace)
    pend = ap_.pending_records()
    if not a.checkpoint:
        print(json.dumps(pend, indent=2, ensure_ascii=False)); return 0
    rs = RunState(a.workspace)
    rec = ap_.decide(a.checkpoint, not a.deny, decided_by=f"cli@{time.strftime('%H:%M')}",
                     rs=rs, note=a.note)
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    # advance past the checkpoint into the gated phase
    if not a.deny:
        from .pipeline import Kernel
        k = Kernel(a.workspace)
        nxt = k.rs.data.get("current_phase")
        k.log.emit(nxt, "checkpoint_cleared", {"checkpoint": a.checkpoint})
        if k.rs.status == "paused_checkpoint" and not ap_.pending_records():
            k.rs.status = "running"
            k.rs.write()
    return 0


def cmd_gate(a) -> int:
    if a.which == "verdicts":
        p = run_py("scripts/validate_verdicts.py", [str(a.workspace / ".sciforge" / "verdicts"), "--strict"])
    elif a.which == "wrapup":
        p = run_py("scripts/sciforge_audit.py", [str(a.workspace)])
    else:
        p = run_py("scripts/check_figure_embedding.py", [str(a.workspace), "--require-renderer"])
    print(p.stdout or p.stderr)
    return p.returncode


def cmd_doctor(a) -> int:
    checks = {}
    checks["python"] = sys.version.split()[0]
    checks["python_ok"] = sys.version_info >= (3, 10)
    for tool in ("claude", "codex", "d2", "dot", "rsvg-convert", "pdflatex", "latexmk",
                 "bibtex", "inkscape", "mmdc", "typst", "git", "tmux", "nohup"):
        checks[tool] = bool(shutil.which(tool))
    checks["sandbox"] = {"available": sandbox_cmd(Path.cwd()) is not None}
    checks["devices"] = plan_device(Path.cwd()) if False else None  # device probe lazy
    # python libs
    try:
        import matplotlib  # noqa
        checks["matplotlib"] = True
    except Exception:
        checks["matplotlib"] = False
    for m in ("numpy", "PIL", "sympy", "scipy", "pytest"):
        try:
            __import__(m); checks[m] = True
        except Exception:
            checks[m] = False
    # repo gates self-test
    ci = run_py("scripts/ci_check.py", ["--quiet"]) if (Path(__file__).resolve().parents[2] / "scripts" / "ci_check.py").exists() else None
    checks["ci_check_available"] = ci is not None
    print(json.dumps(checks, indent=2, default=str))
    return 0 if checks["python_ok"] else 1


def cmd_dispatch(a) -> int:
    r = dispatch(a.workspace, a.script, a.args, background=not a.foreground,
                 group=a.group, seed=a.seed)
    print(json.dumps(r, indent=2, ensure_ascii=False, default=str))
    if not r.get("dispatched"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
