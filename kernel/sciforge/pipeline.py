"""The code-driven 21-phase loop (S01).

Kernel is the orchestrator: knowledge lives in skills/ (Markdown), control lives
here (phasegraph.json + this engine). The loop:

  pick phase -> build pointer-load bundle (constraints re-injected verbatim)
    -> dispatch (host adapter / providers / kernel-native)
    -> collect verdict JSON -> run mechanical gates -> on PASS commit boundary
    (events + RUNSTATE + budget accrual) -> apply loopback/BA/KILL rules
    -> next phase (routing-aware).

Advances are impossible without gates passing: `boundary_committed` is only
written after every gate for that transition returns PASS. Crash => recover()
replays events; dangling boundaries redo. Checkpoints become blocked state
(S05 approvals). 3-round cap per failure type is counted from the event log,
never from memory.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import bundle as bundle_mod
from . import gates as gates_mod
from .approvals import Approvals, accrue, breach, init_budget, underuse
from .state import EventLog, RunState, recover, release_lock, take_lock

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = REPO_ROOT / "kernel" / "config" / "phasegraph.json"

# verdict severity order (worst wins) — assurance-contract.md
SEV = {"ERROR": 6, "BLOCKED": 5, "FAIL": 4, "WARN": 3, "NOT_APPLICABLE": 2, "PASS": 1}


class PhaseGraph:
    def __init__(self, path: Path = GRAPH_PATH):
        self.spec = json.loads(Path(path).read_text())
        self.phases = {p["id"]: p for p in self.spec["phases"]}
        self.order = [p["id"] for p in self.spec["phases"]]

    def nxt(self, pid: str, routing: dict | None) -> str | None:
        p = self.phases[pid]
        if "next_by_route" in p:
            route = (routing or {}).get("route", "experiment-first")
            return p["next_by_route"].get(route, p["next_by_route"].get("theory-only"))
        nxt = p.get("next")
        return None if nxt == "DONE" else nxt

    @property
    def limits(self):
        return self.spec["effort_limits"]


class Verdict:
    def __init__(self, v: str, artifacts: list | None = None, notes: str = "",
                 cost_usd: float | None = None, reason_code: str = ""):
        self.v = v if v in SEV else "ERROR"
        self.artifacts = artifacts or []
        self.notes = notes
        self.cost_usd = cost_usd
        self.reason_code = reason_code

    @property
    def sev(self):
        return SEV[self.v]

    def as_dict(self):
        return {"verdict": self.v, "artifacts": self.artifacts,
                "notes": self.notes, "cost_usd": self.cost_usd}


class DispatchError(RuntimeError):
    pass


class Kernel:
    def __init__(self, ws: Path, graph: PhaseGraph | None = None):
        self.ws = Path(ws)
        self.graph = graph or PhaseGraph()
        self.log = EventLog(self.ws)
        self.rs = RunState(self.ws)
        self.appr = Approvals(self.ws)
        self._providers = None  # lazily: gateway present => real cross-model review

    def providers(self):
        if self._providers is None:
            from .providers import Providers
            self._providers = Providers()
        return self._providers

    # ---------------- state helpers ----------------
    @property
    def budget(self) -> dict:
        p = self.ws / ".sciforge" / "verdicts" / "RUN_BUDGET.json"
        try:
            d = json.loads(p.read_text())
            d["_problem_hash"] = self.rs.data.get("problem_hash", "")
            return d
        except Exception:
            return {}

    def routing(self) -> dict | None:
        try:
            return json.loads((self.ws / ".sciforge" / "verdicts" /
                               "VERIFICATION_ROUTING.json").read_text())
        except Exception:
            return None

    def _declare_na(self, filename: str) -> None:
        """Append a legitimately-skipped verdict file to VERIFICATION_ROUTING.na_verdicts."""
        rp = self.ws / ".sciforge" / "verdicts" / "VERIFICATION_ROUTING.json"
        try:
            d = json.loads(rp.read_text())
            na = d.get("na_verdicts", [])
            if filename not in na:
                na.append(filename)
                d["na_verdicts"] = na
                rp.write_text(json.dumps(d, indent=2))
        except Exception:
            pass

    def check_deepen_freeze(self) -> dict:
        """mode=deepen: core claim / contributions / method identity are FROZEN.
        A deepen run that proposes a different method/claim is drift -> BLOCKED
        (reason_code: deepen_frozen_violation). The thesis hash is locked at start
        the same way INV-G1 locks the Q-id."""
        frozen = self.ws / ".sciforge" / "verdicts" / "DEEPEN_FREEZE.json"
        if not frozen.exists():
            return {"ok": True, "note": "no deepen freeze declared"}
        try:
            d = json.loads(frozen.read_text())
        except json.JSONDecodeError:
            return {"ok": False, "reason_code": "deepen_freeze_unreadable"}
        from .state import sha256_file
        for rel in d.get("frozen_files", []):
            f = self.ws / rel
            if not f.exists():
                return {"ok": False, "reason_code": "deepen_frozen_violation",
                        "detail": f"frozen file deleted: {rel}"}
            if sha256_file(f) != d["hashes"].get(rel):
                return {"ok": False, "reason_code": "deepen_frozen_violation",
                        "detail": f"frozen file mutated: {rel}"}
        return {"ok": True, "frozen": d.get("frozen_files", [])}

    def _round_count(self, loopback_id: str) -> int:
        return sum(1 for e in self.log.replay()
                   if e["kind"] == "loopback" and e["payload"].get("id") == loopback_id)

    def _ba_used(self) -> int:
        return self.budget.get("ba_rounds_used", 0)

    # ---------------- start / resume ----------------
    def start(self, run_id: str, problem: str, effort: str = "balanced",
              host: str | None = None, test_mode: bool = False,
              human_skip: bool = False, mode: str = "full") -> None:
        recov = recover(self.log, self.rs, self.ws)
        if recov == "wait":
            raise DispatchError("another kernel process holds this workspace")
        if recov == "completed":
            raise DispatchError(f"run already {self.rs.status}; use a fresh workspace")
        if recov in ("fresh", "stale"):
            rs = self.rs  # reuse bound instance (EventLog/Approvals share self.ws)
            rs.data = {}
            RunState.open_workspace(self.ws, run_id, problem)  # dirs + guard
            rs.data.update({"schema_version": "2.0", "run_id": run_id,
                            "problem_id": run_id, "problem": problem, "effort": effort,
                            "host": host or "manual",
                            "flags": {"test_mode": test_mode, "human_skip": human_skip, "mode": mode},
                            "created_at": time.time()})
            rs.status = "running"
            rs.update(phase="0", next_action="freeze problem anchor")
            rs.write()
            from .state import sha256_file
            anchor = self.ws / ".sciforge" / "verdicts" / "PROBLEM_HASH.txt"
            pf = self.ws / "PROBLEM.md"
            pf.parent.mkdir(exist_ok=True)
            pf.write_text(f"# {run_id}\n\n{problem}\n")
            digest = sha256_file(pf)
            anchor.write_text(digest + "\n")
            rs.data["problem_hash"] = digest
            rs.write()
            init_budget(self.ws, run_id, effort, self.graph.limits)
            self.log.emit("0", "run_started", {"run_id": run_id, "problem": problem, "effort": effort})
            take_lock(self.ws)
        else:
            self.log.emit(self.rs.data.get("current_phase", "?"), "resumed",
                          {"from": self.rs.status})

    # ---------------- boundary: gates then commit (S04) ----------------
    def commit_boundary(self, pid: str, v: Verdict) -> dict:
        """Gate check then, only on PASS, commit boundary atomically."""
        ph = self.graph.phases[pid]
        results = []
        # NOT_APPLICABLE (routing skip) legitimately never produces the phase's
        # artifacts — its file gates are vacuous; extend na_verdicts instead
        # (output-protocol: declared skips, never silent absences).
        # na_verdicts uses registered artifact names (output-protocol.md §5;
        # validate_verdicts WARNs on unregistered names — RESULT.json/STATUS.json
        # are live experiment records in experiments/, not verdicts).
        if v.v == "NOT_APPLICABLE":
            for art in ph.get("na_on_skip", []):
                self._declare_na(art)
        else:
            for g in ph.get("gates", [ph["gate"]] if ph.get("gate") else []):
                results.append(gates_mod.check(self.ws, g, pid))
        # every boundary: registered verdicts validation (strict from phase 5)
        strict = _ord(ph) >= 5
        results.append(gates_mod.validate_verdicts(self.ws, strict=strict))
        # wrap-up gates at 16
        if pid == "16":
            results.append(gates_mod.wrap_up_gates(self.ws))
        # anything that is not a clean pass/skip blocks the boundary
        # (PENDING = host has not produced the machine verdict yet — v1.4.0's
        #  "audit never ran" failure mode must NOT be able to advance)
        failed = [r for r in results if r.get("status") not in ("PASS", "SKIP", "NOT_APPLICABLE")]
        self.log.emit(pid, "gates", {"results": results})
        if failed:
            # boundary NOT committed: phase stays in progress; record gate failure
            self.log.emit(pid, "gate_rejected", {"failed": failed})
            return {"committed": False, "failed": failed}
        dur = time.time() - self.rs.data.get("phase_started_at", time.time())
        b = accrue(self.ws, phase=pid, cost_usd=v.cost_usd, duration_s=dur)
        br = breach(b)
        pend = self.appr.pending_records()
        self.log.emit(pid, "phase_done", {"phase": pid, "verdict": v.v, "artifacts": v.artifacts})
        self.log.emit(pid, "boundary_committed", {"phase": pid, "verdict": v.v})
        nxt = self.graph.nxt(pid, self.routing())
        self.rs.update(phase=nxt or pid, last_boundary=pid,
                       next_action=(f"enter phase {nxt}" if nxt else "done"),
                       budget_snapshot={"wall": b.get("wall_clock_seconds"), "cost": b.get("api_cost_usd")},
                       verdict=v.v)
        if br:
            self.rs.status = "paused_blocked"
            self.rs.update(reason_code=br)
            self.log.emit(pid, "blocked", {"reason_code": br})
        elif pend:
            self.rs.status = "paused_checkpoint"
        elif nxt is None:
            self.rs.status = "completed"
            release_lock(self.ws)
            self._write_preprint()
        self.rs.write()
        if pid == "16" and underuse(self.budget) and any(
                e["kind"] == "phase_done" and e["payload"]["verdict"] in ("WARN", "FAIL")
                for e in self.log.replay()[-30:]):
            self.log.emit("16", "warn", {"code": "budget_underuse"})
        return {"committed": True, "next": nxt, "budget": b, "breach": br}

    # ---------------- dispatch ----------------
    def run_phase(self, pid: str) -> Verdict:
        ph = self.graph.phases[pid]
        self.rs.update(phase=pid)
        self.rs.data["phase_started_at"] = time.time()
        self.rs.write()
        self.log.emit(pid, "phase_entered", {"skill": ph.get("skill"), "mode": ph.get("mode")})

        # kernel-native phases handled internally
        if ph.get("kernel_native"):
            return self._native(pid, ph)

        # Routing-aware skip (orchestrator phase-mode table, v5.0): phases that
        # declare skip_on_route SKIP under that route — no dispatch, no gate
        # demand (theory-only legitimately never produces RESULT.json/STATUS.json).
        # 6a is MUST on theory-only (primary verification) and declares no skip.
        route = (self.routing() or {}).get("route")
        if route and route in ph.get("skip_on_route", []):
            self.log.emit(pid, "routed_skip", {"route": route})
            return Verdict("NOT_APPLICABLE", notes=f"phase {pid} N/A on {route} route")

        # Phase 14: if a model gateway is configured, run the cross-model review
        # panel in-process (S20/S21) and write the machine verdicts. In host
        # mode we fall through to the host dispatch (manual/claude/codex).
        if pid == "14" and not self.providers().host_mode:
            return self._native_review()

        b = self.budget
        bundle = bundle_mod.build(self.ws, ph, b)
        host = self.rs.data.get("host", "manual")
        try:
            if host in ("claude", "codex"):
                ph["_host"] = host
                return self._dispatch_host_bg(pid, ph, bundle)
            return self._dispatch_host_file(pid, bundle)  # manual: wait for done.json
        except DispatchError as e:
            self.log.emit(pid, "dispatch_error", {"error": str(e)})
            return Verdict("ERROR", notes=str(e))

    # --- host adapters (S08) ---
    # claude/codex phases are dispatched BACKGROUND (same discipline as full
    # experiments): a heavy phase (MCTS ideation) legitimately runs 1-2h; the
    # kernel must not block a foreground subprocess on it. Launch once, poll per
    # step; a dead kernel orphan-harms nothing (the claude child survives and
    # a re-launched kernel adopts its result from the outfile).
    def _host_cmd(self, pid: str, ph: dict) -> tuple[list[str], str]:
        prompt = self._phase_prompt(pid, ph)
        if ph.get("_host") == "codex":
            return ["codex", "exec", prompt], "codex"
        cmd = ["claude", "-p", prompt, "--output-format", "json",
               "--allowedTools", "Read,Write,Edit,Bash(python3:*),Bash(python:*)",
               "--add-dir", str(self.ws)]
        # claude CLI accepts only its own aliases (sonnet/opus/…); a gateway model
        # id like ANTHROPIC_MODEL="qwen…[1m]" is NOT a valid --model value and the
        # host claude already resolves its backend via its own config. Pass
        # --model only for an explicit SCIFORGE_HOST_MODEL override.
        host_model = os.environ.get("SCIFORGE_HOST_MODEL")
        if host_model:
            cmd += ["--model", host_model]
        return cmd, "claude"

    def _dispatch_host_bg(self, pid, ph, bundle: Path) -> Verdict:
        hostdir = self.ws / ".sciforge" / "host"
        hostdir.mkdir(parents=True, exist_ok=True)
        job = hostdir / f"{pid}.job.json"
        outfile = hostdir / f"{pid}.out.json"
        if job.exists():
            try:
                meta = json.loads(job.read_text())
            except json.JSONDecodeError:
                job.unlink()
                return Verdict("ERROR", notes=f"corrupt job file for {pid}")
            alive = _child_alive(int(meta["pid"]))
            cap = int(os.environ.get("SCIFORGE_HOST_PHASE_TIMEOUT", "7200"))
            if alive and time.time() - meta.get("started_at", 0) > cap:
                try:
                    os.kill(int(meta["pid"]), 9)  # stuck child (observed: claude
                except ProcessLookupError:       # wrote an error line then hung)
                    pass
                job.unlink()
                self.log.emit(pid, "host_timeout", {"pid": meta["pid"], "cap_s": cap})
                return Verdict("ERROR", reason_code=f"host_timeout:{pid}",
                               notes=f"{meta.get('bin')} exceeded {cap}s on phase {pid}; killed")
            if alive:
                self.log.emit(pid, "host_running", {"pid": meta["pid"], "since": meta["started_at"]})
                return Verdict("BLOCKED", reason_code=f"await_host:{pid}",
                               notes=f"{meta.get('bin')} running (pid {meta['pid']})")
            # exited (or died) — collect the result
            job.unlink()
            try:
                raw = outfile.read_text()
                data = json.loads(_first_json(raw))
                result = data.get("result", raw)
                cost = float(data.get("total_cost_usd") or 0.0)  # S23 real host cost
            except FileNotFoundError:
                return Verdict("ERROR", notes=f"{meta.get('bin')} died leaving no output")
            except json.JSONDecodeError:
                result, cost = raw[:4000], 0.0
            v = self._parse_verdict_json(result)
            v.cost_usd = v.cost_usd or cost or None
            self.log.emit(pid, "host_result", {"raw": str(result)[:2000], "cost_usd": cost})
            return v
        cmd, binname = self._host_cmd(pid, ph)
        # claude absent -> fall back to manual bundle protocol (host answers done.json)
        import shutil as _sh
        if _sh.which(cmd[0]) is None:
            return self._dispatch_host_file(pid, bundle)
        with open(outfile, "wb") as of:
            proc = subprocess.Popen(cmd, stdout=of, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, cwd=str(self.ws),
                                    env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "kernel")},
                                    start_new_session=True)
        job.write_text(json.dumps({"pid": proc.pid, "bin": binname,
                                   "started_at": time.time(), "phase": pid}))
        self.log.emit(pid, "host_dispatched", {"pid": proc.pid, "bin": binname})
        return Verdict("BLOCKED", reason_code=f"await_host:{pid}",
                       notes=f"{binname} dispatched for phase {pid}")

    def _dispatch_host_file(self, pid, bundle: Path) -> Verdict:
        """manual/bundle protocol: kernel writes a request; the driving agent answers.

        Used when sciforge itself has no LLM (host agent drives via `sciforge step`).
        """
        req = self.ws / ".sciforge" / "host" / f"phase_{pid}.request.json"
        req.parent.mkdir(parents=True, exist_ok=True)
        req.write_text(json.dumps({"phase": pid, "bundle": str(bundle),
                                   "respond_by": f".sciforge/host/phase_{pid}.done.json",
                                   "contract": "write the verdict JSON object there, then `sciforge step`"},
                                  indent=2))
        done = self.ws / ".sciforge" / "host" / f"phase_{pid}.done.json"
        if done.exists():
            try:
                v = self._parse_verdict_json(done.read_text())
                done.unlink()
                self.log.emit(pid, "host_result", {"from": "done.json", "verdict": v.v})
                return v
            except Exception as e:
                return Verdict("ERROR", notes=f"done.json unparseable: {e}")
        return Verdict("BLOCKED", reason_code=f"await_host:{pid}",
                       notes=f"host must answer {done.relative_to(self.ws)} per bundle {bundle.relative_to(self.ws)}")

    def _phase_prompt(self, pid, ph) -> str:
        b = bundle_mod.build(self.ws, ph, self.budget)
        return (f"You are executing SciForge-OSS pipeline phase {pid} ({ph['name']}) "
                f"as the host agent. Follow the pointer-load bundle EXACTLY; read "
                f"{b} first. Repo root: {REPO_ROOT}. Workspace: {self.ws}. "
                f"When done, your FINAL message must be only the JSON verdict object.")

    @staticmethod
    def _parse_verdict_json(raw: str) -> Verdict:
        start = raw.rfind("{")
        # find the LAST complete JSON object
        depth = 0; obj = None
        for i in range(start, -1, -1):
            pass
        # simpler: try full parse, then trailing-object extraction
        for candidate in _json_candidates(raw):
            try:
                d = json.loads(candidate)
                if isinstance(d, dict) and "verdict" in d:
                    return Verdict(d.get("verdict", "PASS"), d.get("artifacts", []),
                                   d.get("notes", ""), d.get("cost_usd"))
            except Exception:
                continue
        return Verdict("ERROR", notes=f"no verdict JSON in host output: {raw[:200]}")

    # ---------------- checkpoints & kill ----------------
    def _checkpoint_satisfied(self, ck: str, pid: str) -> bool:
        flags = self.rs.data.get("flags", {})
        log = self.appr.log
        if not log.exists():
            if flags.get("human_skip"):
                self.appr.skipped("human_skip", ck, pid, self.rs)
                return True
            if flags.get("test_mode"):
                # bypass, not skip: agent does the guarded work, approval deferred
                self.appr.skipped("test_mode_bypass", ck, pid, self.rs)
                self.rs.data["production_ready"] = False
                return True
            return False
        # approved or logged-skip for this checkpoint?
        text = log.read_text()
        return (f"checkpoint={ck} decision=APPROVE" in text or
                f"checkpoint={ck} human_skip=True" in text or
                f"checkpoint={ck} test_mode_bypass=True" in text)

    def _checkpoint_payload(self, ck, pid) -> dict:
        """Summarize what the human is deciding (idea pick / method approval)."""
        out = {"checkpoint": ck, "phase": pid}
        rl = self.ws / ".sciforge" / "refine-logs"
        if ck == "idea-pick":
            fp = rl / "FINAL_PROPOSAL.md"
            cand = rl / "IDEA_CANDIDATES.md"
            out["digest"] = _tail(fp if fp.exists() else cand, 2000)
        elif ck == "method-approval":
            mr = self.ws / "methods" / "METHOD_REGISTRY.md"
            out["digest"] = _tail(mr, 2000) if mr.exists() else "(registry not yet written)"
        return out

    def kill_checkpoint(self, pid: str, kill_payload: dict) -> Verdict:
        """v5.3 KILL human checkpoint, default ON (unless flags delegate)."""
        flags = self.rs.data.get("flags", {})
        ck = "kill-confirmation"
        if flags.get("human_skip") or os.environ.get("SCIFORGE_KILL_CHECKPOINT") == "0":
            self.appr.skipped("human_skip", ck, pid, self.rs)
            return Verdict("PASS", notes="kill checkpoint delegated")
        if self.appr.log.exists() and f"checkpoint={ck} decision=APPROVE" in self.appr.log.read_text():
            return Verdict("PASS", notes="kill confirmed")
        self.appr.request(ck, pid, {"kill_argument": kill_payload}, self.rs)
        return Verdict("BLOCKED", reason_code="kill_checkpoint", notes="awaiting KILL confirmation")

    # ---------------- loopbacks (L1-L13 enforcement) ----------------
    def apply_loopback(self, pid: str, v: Verdict) -> str | None:
        ph = self.graph.phases[pid]
        lb = ph.get("loopback")
        if not lb or v.v not in ("FAIL", "WARN"):
            return None
        # toy FAIL triggers KILL-or-PIVOT decision (L5) — route by notes marker
        trigger = "FAIL"
        used = self._round_count(lb["id"])
        if lb.get("budget", -1) >= 0 and used >= lb["budget"]:
            self.log.emit(pid, "loopback_exhausted", {"id": lb["id"], "used": used})
            return None  # caller turns to BLOCKED
        # anti-deadloop #2: re-entry must consume failure evidence
        ev = self.ws / ".sciforge" / "refine-logs" / "failed_ideas.json"
        if ev.exists():
            self.log.emit(pid, "failure_evidence_present", {"file": str(ev)})
        target = lb["target"]
        self.log.emit(pid, "loopback", {"id": lb["id"], "target": target, "round": used + 1})
        return target

    # ---------------- native phases ----------------
    def _native_review(self) -> Verdict:
        """S20/S21 in-process: 3 independent-model blind review + adjudication.

        Writes: .sciforge/audits/REVIEW_PANEL.json (full panel narrative) and
        registered REVIEW_STATE.json (mapped verdict) so the boundary gate +
        validate_verdicts see the same machine truth the host agent would write.
        """
        import time as _t
        from . import review as review_mod
        paper = self.ws / "paper" / "main.tex"
        text = paper.read_text(errors="replace") if paper.exists() else "(paper not yet assembled)"
        claims = self.ws / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md"
        ctext = claims.read_text(errors="replace") if claims.exists() else ""
        panel = review_mod.review_paper(self.providers(), text)
        if panel.get("adjudication_needed"):
            adj = review_mod.adjudicate_cross(self.providers(), panel, text, ctext)
            panel["adjudication"] = adj
        (self.ws / ".sciforge" / "audits").mkdir(parents=True, exist_ok=True)
        (self.ws / ".sciforge" / "audits" / "REVIEW_PANEL.json").write_text(
            json.dumps(panel, indent=2, ensure_ascii=False))
        rs_verdict = ("ready" if panel["verdict"] == "ACCEPT" else
                      "almost" if panel["verdict"] == "ADJUDICATE_REQUIRED" else "not_ready")
        rs = {"round": 1, "threadId": self.rs.data.get("run_id", ""),
              "status": "completed", "difficulty": "medium",
              "last_score": panel.get("overall") or 0, "last_verdict": rs_verdict,
              "pending_derivations": [],
              "timestamp": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
              "response_class": ["panel"],
              "panel_source": "kernel/sciforge/review.py (S20 cross-model)"}
        (self.ws / ".sciforge" / "verdicts" / "REVIEW_STATE.json").write_text(
            json.dumps(rs, indent=2, ensure_ascii=False))
        v = "PASS" if panel["verdict"] == "ACCEPT" else \
            "WARN" if panel["verdict"] == "ADJUDICATE_REQUIRED" else "FAIL"
        cost = sum((r.get("usage") or {}).get("cost_usd") or 0.0 for r in panel.get("per_reviewer", {})
                   if isinstance(r, dict))
        return Verdict(v, artifacts=[".sciforge/audits/REVIEW_PANEL.json",
                                     ".sciforge/verdicts/REVIEW_STATE.json"],
                       notes=panel["verdict"], cost_usd=cost or None,
                       reason_code=f"panel_{panel['verdict']}")

    def _native(self, pid: str, ph: dict) -> Verdict:
        if pid == "0":
            b = self.budget
            if breach(b):
                return Verdict("BLOCKED", reason_code=breach(b))
            return Verdict("PASS", artifacts=[".sciforge/verdicts/PROBLEM_HASH.txt"])
        if pid == "1":
            # decomposition digest written by host next turn; native only checks anchor present
            return Verdict("PASS")
        if pid == "6":  # verification-routing (S04 deterministic-first)
            return self._route()
        if pid == "16":
            self._write_preprint()
            return Verdict("PASS", artifacts=["output/RUN_PREPRINT.md", "output/LESSONS.json"])
        return Verdict("PASS")

    def _route(self) -> Verdict:
        """Deterministic routing from prior verdict artifacts (rule-based first, LLM fallback)."""
        sig = None
        idea = None
        for p in (self.ws / ".sciforge" / "refine-logs" / "domain-signature.json",):
            try:
                sig = json.loads(p.read_text())
            except Exception:
                pass
        # verification_type should be produced by idea-discovery
        try:
            idea = json.loads((self.ws / ".sciforge" / "refine-logs" /
                               "FINAL_PROPOSAL.json").read_text())
        except Exception:
            pass
        vt = (idea or {}).get("verification_type") or (sig or {}).get("suggested_verification_type")
        if not vt:
            ev = (sig or {}).get("evidence_type", "")
            vt = {"computational": "computational", "empirical": "theory+experiment"}.get(ev, "theory-only")
        route = {"theory-only": "theory-only", "qualitative": "theory-only",
                 "computational": "experiment-first",
                 "theory+experiment": "hybrid"}.get(vt, "experiment-first")
        na = []
        if route == "theory-only":
            na = ["BUDGET_FLOOR.json", "FIGURE_AUDITS.json"] if vt == "qualitative" else ["BUDGET_FLOOR.json"]
        vp = self.ws / ".sciforge" / "verdicts"
        vp.mkdir(parents=True, exist_ok=True)
        (vp / "VERIFICATION_ROUTING.json").write_text(json.dumps({
            "schema_version": "1.0", "route": route, "evidence_type": (sig or {}).get("evidence_type", "unknown"),
            "verification_type": vt, "reason": f"kernel deterministic routing from {vt}",
            "na_verdicts": na}, indent=2))
        self.log.emit("6", "routed", {"route": route, "na_verdicts": na})
        return Verdict("PASS", artifacts=[".sciforge/verdicts/VERIFICATION_ROUTING.json"])

    # ---------------- preprint + lessons (cross-run memory, S15 input) ----------------
    def _write_preprint(self):
        out = self.ws / "output"
        out.mkdir(exist_ok=True)
        rs = self.rs.data
        events = self.log.replay()
        kills = [e for e in events if e["kind"] in ("loopback", "checkpoint_requested")
                 and "kill" in json.dumps(e).lower()]
        verdicts = rs.get("phase_verdicts", {})
        lines = [f"# RUN_PREPRINT — {rs.get('run_id')}",
                 f"generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
                 "", f"## Problem\n{rs.get('problem', '')}",
                 "", "## Verdict trail",
                 *[f"- {p}: {v}" for p, v in sorted(verdicts.items())],
                 "", "## Kills/loopbacks fired",
                 *([f"- {e['phase']}: {e['kind']}" for e in kills[:20]] or ["(none)"]),
                 "", "## Budget", json.dumps(self.budget.get("per_phase", {}), indent=1),
                 "", "## Failure notes (for next runs' ideation prior)",
                 *[f"- {e['phase']} {e['kind']}: {json.dumps(e['payload'])[:200]}"
                   for e in events if e["kind"] in ("gate_rejected", "blocked", "loopback_exhausted")][:20]]
        (out / "RUN_PREPRINT.md").write_text("\n".join(lines))
        # AlphaProof generate-verify-reinforce: verified results are reinforced
        # evidence for the next run's idea prior (not just "what worked" prose).
        verified = []
        for pth in (self.ws / "experiments").glob("**/RESULT.json") if (self.ws / "experiments").exists() else []:
            try:
                r = json.loads(pth.read_text())
                if r.get("status") == "PASS":
                    verified.append({"artifact": str(pth.relative_to(self.ws)),
                                     "metric": r.get("result_summary") or r.get("metrics"),
                                     "reinforce": True})
            except Exception:
                continue
        lessons = {"schema_version": "1.0", "run_id": rs.get("run_id"),
                   "failed_experiments": [], "idea_rollbacks": kills,
                   "what_worked": [p for p, v in verdicts.items() if v == "PASS"],
                   "verified_proofs": verified,
                   "lessons": []}
        (out / "LESSONS.json").write_text(json.dumps(lessons, indent=2, ensure_ascii=False))

    # ---------------- outer loop ----------------
    def step(self) -> dict:
        """Advance one phase boundary. Returns status dict."""
        if self.rs.status == "completed":
            release_lock(self.ws)
            return {"status": "done", "phase": self.rs.data.get("current_phase")}
        pid = self.rs.data.get("current_phase")
        ph = self.graph.phases.get(pid)
        if ph is None:
            return {"status": "done", "phase": pid}
        if self.rs.status == "paused_checkpoint" and self.appr.pending_records():
            pend = self.appr.pending_records()
            return {"status": "blocked_checkpoint", "pending": [p["checkpoint"] for p in pend],
                    "hint": "run `sciforge approve <checkpoint>` or set human_skip"}
        if self.rs.status == "paused_blocked":
            return {"status": "blocked", "reason": self.rs.data.get("reason_code", "")}
        v = self.run_phase(pid)
        if v.v in ("BLOCKED",):
            # await_host or checkpoint: not a failure — boundary not attempted
            self.log.emit(pid, "halted", {"reason": v.reason_code or v.notes})
            self.rs.write()
            if str(v.reason_code).startswith("await_host"):
                time.sleep(5)  # background host job: poll throttle, no busy-wait
            return {"status": "halted", "phase": pid, "reason": v.reason_code or v.notes}
        if v.v == "ERROR":
            self.rs.status = "paused_blocked"
            self.rs.update(reason_code=f"phase_{pid}_error")
            self.rs.write()
            return {"status": "error", "phase": pid, "notes": v.notes}
        # post-phase checkpoints (S05): advance is gated on human approval
        ck = ph.get("checkpoint_after")
        if ck and not self._checkpoint_satisfied(ck, pid):
            payload = self._checkpoint_payload(ck, pid)
            self.appr.request(ck, pid, payload, self.rs)
            self.log.emit(pid, "checkpoint_requested", {"checkpoint": ck})
            self.rs.write()
            return {"status": "blocked_checkpoint", "pending": [ck],
                    "hint": "run `sciforge approve` or rerun with human_skip=true"}
        if v.v == "FAIL":
            target = self.apply_loopback(pid, v)
            if target:
                self.rs.update(phase=target, next_action=f"loopback to {target}")
                self.rs.write()
                return {"status": "loopback", "from": pid, "to": target}
            self.rs.status = "paused_blocked"
            self.rs.update(reason_code=f"unresolved_{pid}_fail")
            self.rs.write()
            return {"status": "blocked", "phase": pid, "reason": "loopback exhausted"}
        # PASS/WARN/NA -> try boundary
        b = self.commit_boundary(pid, v)
        if not b["committed"]:
            # gate rejected: bounded retry like prose fallback, kernel-enforced
            gid = f"gate_{pid}"
            used = self._round_count(gid)
            self.log.emit(pid, "gate_retry", {"round": used + 1})
            if used >= 3:
                self.rs.status = "paused_blocked"
                self.rs.update(reason_code=f"unresolved_{pid}_gate")
                self.rs.write()
                return {"status": "blocked", "phase": pid, "reason": "gate 3-round cap"}
            return {"status": "gate_fail", "phase": pid,
                    "failed_gates": b.get("failed", [])}
        if b.get("breach"):
            return {"status": "blocked", "phase": pid, "reason": b["breach"]}
        return {"status": "advanced", "from": pid, "to": b["next"]}

    def run(self, max_steps: int = 400, max_polls: int = 4320) -> dict:
        """Loop boundaries until terminal. Polls (await_host) don't consume the
        step budget — max_polls caps a stuck child at ~6h (5s throttle)."""
        polls = 0
        for _ in range(max_steps):
            r = self.step()
            if r["status"] == "halted":
                polls += 1
                if polls > max_polls:
                    self.rs.status = "paused_blocked"
                    self.rs.update(reason_code=f"host_poll_cap_{r.get('phase')}")
                    self.rs.write()
                    return {"status": "error", "phase": r.get("phase"),
                            "notes": "host job stuck past poll cap"}
                continue
            polls = 0
            if r["status"] in ("done", "blocked", "error", "blocked_checkpoint"):
                return r
        return {"status": "max_steps"}


def _child_alive(pid: int) -> bool:
    """Liveness for host-adapter children. os.kill(pid, 0) LIES for zombies —
    an exited child the kernel loop hasn't reaped still "exists". So: try
    waitpid(WNOHANG) for our own children (reaps+detects exit); signal-0 probe
    for external pids."""
    try:
        r, _ = os.waitpid(pid, os.WNOHANG)
        if r == pid:
            return False  # our child exited (and was just reaped)
        if r == 0:
            return True   # our child still running
    except ChildProcessError:
        pass  # not our child — probe instead
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True  # exists, not ours to signal


def _ord(ph) -> int:
    try:
        return int(ph["id"])
    except ValueError:
        try:
            return int(ph["id"].split(".")[0])
        except Exception:
            return 0


def _tail(p: Path, n: int) -> str:
    try:
        return p.read_text()[-n:]
    except Exception:
        return ""


def _json_candidates(raw: str):
    """Extract balanced JSON objects from noisy text (host prose + code block)."""
    i = 0; out = []
    while i < len(raw):
        if raw[i] == "{":
            depth = 0
            for j in range(i, len(raw)):
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0:
                        out.append(raw[i:j + 1])
                        i = j
                        break
        i += 1
    return reversed(out)


def _first_json(raw: str) -> str:
    """Result-bearing JSON object from host stdout. claude -p --output-format json
    writes one line, but a leading error may dump other JSON first (observed:
    {"model":...,"query_source":"sdk"} noise before the real envelope), so prefer
    objects carrying "type":"result" / "result" / "verdict", fall back to first."""
    objs = []
    i = 0
    while i < len(raw):
        if raw[i] == "{":
            depth = 0
            for j in range(i, len(raw)):
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0:
                        objs.append(raw[i:j + 1])
                        i = j
                        break
        i += 1
    for o in objs:
        if '"type":"result"' in o or '"type": "result"' in o or '"result"' in o \
           or '"verdict"' in o:
            return o
    return objs[0] if objs else raw
