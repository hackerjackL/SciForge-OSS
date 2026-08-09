#!/usr/bin/env python3
"""SciForge-OSS end-to-end evaluation harness (v1.4.0).

Phase-level driver for running the auto-pipeline with an external model fleet
(default: deepseek-v4-flash-0731 via the Aliyun MaaS gateway) while keeping
checkpoint/resume semantics identical to the v6.0 RUNSTATE contract.

Design rules:
  - The pipeline SKILLS are the contract; this harness only dispatches,
    verifies, and checkpoints. It never does research itself.
  - Every phase runs as a headless `claude -p` subprocess (clean sub-agent;
    no session state leaks between phases). Stdout/stderr of each phase goes
    to {ws}/.sciforge/logs/phase_<id>.log.
  - After each phase the harness rewrites {ws}/.sciforge/RUNSTATE.json
    (current_phase / last_completed_boundary / next_action / status) and runs
    the cheap structural gates (artifact existence + validate_verdicts.py).
  - Resume: `run`/`run-all` always continue from RUNSTATE.json. Delete the
    workspace to start from scratch; delete nothing to keep the trail.

Subcommands:
    init <ws> [--problem-file F]     create workspace + PROBLEM.md + RUNSTATE
    status <ws>                      show RUNSTATE + gate summary
    next <ws>                        print the prompt packet for the next phase
    run <ws> [--model M] [--dry]     execute ONE phase, gate it, checkpoint
    run-all <ws> [--model M]         loop `run` until completed/blocked
    judge <ws> [--model M]           adversarial EI-conference rubric judge ->
                                     .sciforge/verdicts/EVALUATION_REVIEW.json

Stdlib only (subprocess dispatches the external model + repo tooling).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate_verdicts.py"
DEFAULT_MODEL = os.environ.get("SCIFORGE_EVAL_MODEL", "deepseek-v4-flash-0731")
# Claude Code's settings.json `env` block OVERRIDES process-level env vars, so
# the fleet model must be pinned in a dedicated config dir (settings.json
# ANTHROPIC_MODEL=<fleet model>), selected via CLAUDE_CONFIG_DIR. The default
# ~/.claude/settings.json points at the lead model and must never run phases.
EVAL_CONFIG_DIR = os.environ.get("SCIFORGE_EVAL_CONFIG_DIR", "/root/.claude-ds")

# ---------------------------------------------------------------------------
# Phase table — ids match auto-pipeline SKILL.md (21-phase DAG, sub-phases
# included). gate = artifacts that must exist after the phase completes
# (relative to the workspace root). verdicts_gate additionally runs
# validate_verdicts.py on {ws}/.sciforge/verdicts.
# ---------------------------------------------------------------------------

PHASES: list[dict] = [
    {"id": "0", "name": "load problem / freeze Q-id (INV-G1 anchor)",
     "skills": ["skills/orchestrator/auto-pipeline/SKILL.md"],
     "gate": ["PROBLEM.md", "AGENT_DOC.md"]},
    {"id": "1", "name": "problem understanding & decomposition",
     "skills": ["skills/orchestrator/auto-pipeline/SKILL.md"],
     "gate": [".sciforge/refine-logs/PROBLEM_ANALYSIS.md"]},
    {"id": "1b", "name": "domain-learner (literature-based domain signature)",
     "skills": ["skills/meta-skills/domain-learner/SKILL.md",
                "skills/shared-references/domain-signature-consumer.md"],
     "gate": [".sciforge/refine-logs/domain-signature.json"]},
    {"id": "4a", "name": "universal-retrieval broad wave + GAP_REPORT (v6.0 gap chain runs BEFORE idea scoring)",
     "skills": ["skills/meta-skills/universal-retrieval/SKILL.md"],
     "gate": ["literature/references.bib", "literature/landscape_report.md",
              "literature/GAP_REPORT.md"]},
    {"id": "2", "name": "idea-discovery (gap-anchored, MCTS)",
     "skills": ["skills/meta-skills/idea-discovery/SKILL.md",
                "skills/shared-references/mcts-search-protocol.md"],
     "gate": [".sciforge/refine-logs/IDEA_CANDIDATES.md",
              ".sciforge/refine-logs/IDEA_DAG.json",
              ".sciforge/refine-logs/GAP_ANCHOR_LOG.md"]},
    {"id": "2.5", "name": "adversarial-falsification",
     "skills": ["skills/support/adversarial-falsification/SKILL.md"],
     "gate": [".sciforge/refine-logs/FALSIFICATION_REPORT.md"]},
    {"id": "3", "name": "novelty-check (FRONTIER_MAP + collision audit) + final idea selection",
     "skills": ["skills/meta-skills/novelty-check/SKILL.md"],
     "gate": [".sciforge/refine-logs/FRONTIER_MAP.json",
              ".sciforge/refine-logs/FINAL_PROPOSAL.md"]},
    {"id": "4b", "name": "universal-retrieval targeted waves for the surviving idea",
     "skills": ["skills/meta-skills/universal-retrieval/SKILL.md"],
     "gate": ["literature/TARGETED_WAVE_LOG.md"]},
    {"id": "5", "name": "method-registry (method binding + experiment matrix + evaluation protocol)",
     "skills": ["skills/support/method-registry/SKILL.md"],
     "gate": ["methods/METHOD_REGISTRY.md", "methods/METHOD_BINDING.md",
              ".sciforge/verdicts/EXPERIMENT_MATRIX.json",
              ".sciforge/verdicts/EVALUATION_PROTOCOL.json",
              ".sciforge/verdicts/REGISTRY_HASH.txt"]},
    {"id": "6", "name": "verification-routing (+ na_verdicts declaration)",
     "skills": ["skills/shared-references/verification-routing.md"],
     "gate": [".sciforge/verdicts/VERIFICATION_ROUTING.json"]},
    {"id": "6a", "name": "theory-derivation (symbolic + step verification)",
     "skills": ["skills/support/theory-derivation/SKILL.md"],
     "gate": [".sciforge/verdicts/PROOF_AUDIT.json"]},
    {"id": "6b", "name": "experiment-execution toy gate (REAL execution)",
     "skills": ["skills/support/experiment-execution/SKILL.md",
                "skills/shared-references/background-dispatch-protocol.md"],
     "gate": [".sciforge/verdicts/BUDGET_FLOOR.json"]},
    {"id": "6c", "name": "experiment-execution full matrix (REAL execution)",
     "skills": ["skills/support/experiment-execution/SKILL.md"],
     "gate": ["experiments/full/RESULT.json"]},
    {"id": "7", "name": "leakage-audit (Type I/IV)",
     "skills": ["skills/support/leakage-audit/SKILL.md"],
     "gate": [".sciforge/verdicts/LEAKAGE_AUDIT.json"]},
    {"id": "8", "name": "logic-verification (6-dimension)",
     "skills": ["skills/support/logic-verification/SKILL.md"],
     "gate": [".sciforge/verdicts/LOGIC_VERIFICATION.json"]},
    {"id": "9", "name": "invariant-check (INV-G1)",
     "skills": ["skills/support/invariant-check/SKILL.md"],
     "gate": [".sciforge/verdicts/PROBLEM_HASH.txt",
              ".sciforge/verdicts/INVARIANT_CHECK.json"]},
    {"id": "10", "name": "result-to-claim (3-fidelity gate)",
     "skills": ["skills/support/result-to-claim/SKILL.md"],
     "gate": [".sciforge/audits/CLAIMS_FROM_RESULTS.md"]},
    {"id": "11", "name": "unified-plotting (figures via render_figure.py)",
     "skills": ["skills/meta-skills/unified-plotting/SKILL.md"],
     "gate": ["figures/FIGURE_INDEX.md"]},
    {"id": "12", "name": "paper-writing (elsarticle template)",
     "skills": ["skills/support/paper-writing/SKILL.md",
                "skills/shared-references/writing-principles.md"],
     "gate": ["paper/main.tex"]},
    {"id": "13", "name": "paper-compile (zero-warning PDF)",
     "skills": ["skills/support/paper-compile/SKILL.md"],
     "gate": ["paper/main.pdf", "paper/COMPILE_REPORT.json"]},
    {"id": "14", "name": "auto-review-loop (structured self-review)",
     "skills": ["skills/support/auto-review-loop/SKILL.md"],
     "gate": [".sciforge/verdicts/REVIEW_STATE.json",
              ".sciforge/verdicts/REVIEW_LEDGER.json",
              ".sciforge/verdicts/BLINDSPOT_CHECK.json"]},
    {"id": "15", "name": "citation-audit (3-layer verification of every reference)",
     "skills": ["skills/support/citation-audit/SKILL.md"],
     "gate": [".sciforge/verdicts/CITATION_AUDIT.json"]},
    {"id": "15.5", "name": "publishability-score",
     "skills": ["skills/support/publishability-score/SKILL.md"],
     "gate": [".sciforge/verdicts/PUBLISHABILITY_SCORE.json"]},
    {"id": "16", "name": "final assembly + archive (output/ bundle + RUN_PREPRINT)",
     "skills": ["skills/orchestrator/auto-pipeline/SKILL.md"],
     "gate": ["output/ARTIFACT_MANIFEST.json", "output/RUN_PREPRINT.md"]},
]

PHASE_INDEX = {p["id"]: i for i, p in enumerate(PHASES)}

PROMPT_TEMPLATE = """You are a clean SciForge-OSS pipeline execution agent. You run EXACTLY ONE phase of the auto-pipeline, then stop.

## Context
- Repository (read-only contracts): {repo}
- Workspace (all artifacts go here): {ws}
- Phase id: {phase_id} — {phase_name}
- Model fleet policy: you are the worker; do not redesign the pipeline.

## Your contract
1. Read the phase skill file(s) listed below (and anything they pointer-load, e.g. shared-references/output-protocol.md for artifact paths). Follow them exactly.
{skill_list}
2. Study the existing workspace state (MANIFEST, existing artifacts, verdicts) before producing anything.
3. Produce ALL artifacts this phase owes, at their canonical v6.0 paths (machine-readable verdicts -> .sciforge/verdicts/, narratives -> .sciforge/audits/ or stage dirs). Append one row per artifact to .sciforge/MANIFEST.md.
4. HARD RULES: every citation must be a REAL verifiable paper (arXiv/Semantic Scholar/CrossRef — never invent); every experiment must be ACTUALLY EXECUTED by running real code (no imagined results); the paper template is elsarticle and the figure palette/audit contract must not be altered.
5. Evaluation mode: the two human checkpoints (idea selection, method approval) and the KILL checkpoint are auto-approved — record each auto-approval in .sciforge/APPROVAL_LOG.txt with approver=eval-harness.
6. Do NOT write .sciforge/RUNSTATE.json yourself — the eval harness owns the checkpoint (it rewrites RUNSTATE at every boundary after gating your phase).

## Deliverable check (harness-enforced, do not skip)
After you finish, these paths MUST exist:
{gate_list}

End your final message with exactly one line:
PHASE_VERDICT: PASS | WARN: <reason> | FAIL: <reason> | BLOCKED: <reason>
"""

JUDGE_PROMPT = """You are an adversarial reviewer for an EI-conference / general-journal submission. Your job is to try hard to REJECT this paper. Be specific and evidence-based; do not be nice.

Workspace under review: {ws}
Read at minimum: paper/main.tex (and paper/sections/), figures/FIGURE_INDEX.md, .sciforge/audits/CLAIMS_FROM_RESULTS.md, .sciforge/verdicts/CITATION_AUDIT.json, experiments/ results.

Score each dimension 0-10 with 1-3 sentences of justification:
1. novelty_and_positioning — does it claim a real, well-positioned gap vs real literature?
2. methodological_soundness — model assumptions, derivation, identification of limits
3. experimental_rigor — executed experiments, seeds, baselines, sensitivity
4. claim_evidence_alignment — every claim traceable to executed evidence
5. writing_and_structure — EI-conference readability, figures, abstract/intro quality
6. reproducibility — scripts, data, parameters all present

Then:
- fatal_flaws: list (empty if none) — any item here means REJECT
- required_revisions: ordered list of concrete fixes
- overall: 0-10 (>=6 with zero fatal flaws = accept-ish line for EI/general journal)
- verdict: ACCEPT | REVISE | REJECT

Output ONLY a JSON object with keys: dimensions (object of six ints), justifications (object of six strings), fatal_flaws (array), required_revisions (array), overall (number), verdict (string).
"""


# ---------------------------------------------------------------------------
# workspace helpers
# ---------------------------------------------------------------------------

def sciforge(ws: Path) -> Path:
    return ws / ".sciforge"


def runstate_path(ws: Path) -> Path:
    return sciforge(ws) / "RUNSTATE.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_runstate(ws: Path) -> dict:
    return json.loads(runstate_path(ws).read_text(encoding="utf-8"))


def write_runstate(ws: Path, rs: dict) -> None:
    rs["updated_at"] = now_iso()
    runstate_path(ws).write_text(json.dumps(rs, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")


def phase_prompt(ws: Path, phase: dict) -> str:
    skill_list = "\n".join(f"   - {REPO_ROOT / s}" for s in phase["skills"])
    gate_list = "\n".join(f"   - {ws / g}" for g in phase["gate"])
    return PROMPT_TEMPLATE.format(
        repo=REPO_ROOT, ws=ws, phase_id=phase["id"], phase_name=phase["name"],
        skill_list=skill_list, gate_list=gate_list)


def judge_prompt(ws: Path) -> str:
    return JUDGE_PROMPT.format(ws=ws)


def headless(model: str, prompt: str, log_path: Path, timeout: int = 3600) -> int:
    """Run one clean headless claude subprocess; tee output to log_path.

    The fleet model is pinned through CLAUDE_CONFIG_DIR (a config dir whose
    settings.json sets ANTHROPIC_MODEL=<model>) because Claude Code's
    settings env block overrides process-level environment variables.
    """
    cfg = Path(EVAL_CONFIG_DIR) / "settings.json"
    if not cfg.is_file():
        raise SystemExit(
            f"eval config dir missing: {cfg} — create it with the same env "
            f"block as ~/.claude/settings.json but ANTHROPIC_MODEL={model}")
    settings = json.loads(cfg.read_text(encoding="utf-8"))
    pinned = settings.get("env", {}).get("ANTHROPIC_MODEL")
    if pinned != model:
        raise SystemExit(
            f"model mismatch: harness wants {model} but {cfg} pins "
            f"ANTHROPIC_MODEL={pinned} — refusing to dispatch on the wrong "
            f"(expensive) model; fix the config dir or pass --model {pinned}")
    env = dict(os.environ, ANTHROPIC_MODEL=model, IS_SANDBOX="1",
               CLAUDE_CONFIG_DIR=EVAL_CONFIG_DIR)
    cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n===== {now_iso()} model={model} =====\n")
        log.flush()
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                              env=env, cwd=str(REPO_ROOT), timeout=timeout)
    return proc.returncode


def gate_phase(ws: Path, phase: dict) -> list[str]:
    """Structural gate: artifact existence + verdict validation."""
    problems = []
    for rel in phase["gate"]:
        if not (ws / rel).exists():
            problems.append(f"missing artifact: {rel}")
    verdicts_dir = sciforge(ws) / "verdicts"
    if verdicts_dir.is_dir():
        proc = subprocess.run([sys.executable, str(VALIDATOR), str(verdicts_dir)],
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            tail = " | ".join(proc.stdout.splitlines()[-4:])
            problems.append(f"validate_verdicts FAIL: {tail}")
    return problems


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_init(ws: Path, problem_file: str | None) -> int:
    if runstate_path(ws).exists():
        print(f"workspace already initialized: {ws} (use run/run-all/status, or delete to restart)")
        return 1
    for d in ["verdicts", "logs", "refine-logs", "audits", "tmp"]:
        (sciforge(ws) / d).mkdir(parents=True, exist_ok=True)
    for d in ["literature", "methods", "derivations", "code", "experiments",
              "logs", "figures", "paper", "output"]:
        (ws / d).mkdir(parents=True, exist_ok=True)
    if problem_file:
        text = Path(problem_file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    (ws / "PROBLEM.md").write_text(text, encoding="utf-8")
    (ws / "AGENT_DOC.md").write_text(
        "# AGENT_DOC\n\n- discipline: auto (domain-learner Phase 1b)\n"
        "- venue: EI conference / general journal\n- methodology_class: auto\n"
        "- mode: eval-harness (checkpoints auto-approved, logged)\n"
        "- language: english\n", encoding="utf-8")
    (sciforge(ws) / "MANIFEST.md").write_text(
        "# Artifact Manifest\n\n| Timestamp | Skill | File | Stage | Description |\n"
        "|-----------|-------|------|-------|-------------|\n", encoding="utf-8")
    (sciforge(ws) / "APPROVAL_LOG.txt").write_text(
        f"{now_iso()} eval-harness init: checkpoints policy = auto-approve with log entries\n",
        encoding="utf-8")
    write_runstate(ws, {
        "schema_version": "1.0",
        "run_id": ws.name,
        "problem_id": ws.name,
        "current_phase": PHASES[0]["id"],
        "last_completed_boundary": None,
        "next_action": f"execute phase {PHASES[0]['id']} ({PHASES[0]['name']})",
        "status": "running",
        "pending_human_approvals": [],
        "budget_snapshot": {"wall_clock_seconds": 0, "api_cost_usd": 0},
    })
    print(f"initialized workspace {ws} ({len(PHASES)} phases registered)")
    return 0


def _current_phase(rs: dict) -> dict | None:
    if rs.get("status") in ("completed", "killed"):
        return None
    return PHASES[PHASE_INDEX[rs["current_phase"]]]


def cmd_status(ws: Path) -> int:
    rs = read_runstate(ws)
    print(json.dumps(rs, indent=2, ensure_ascii=False))
    phase = _current_phase(rs)
    if phase:
        problems = gate_phase(ws, phase)
        print("\ncurrent phase gate preview:",
              "clean" if not problems else "\n  " + "\n  ".join(problems))
    return 0


def cmd_next(ws: Path) -> int:
    rs = read_runstate(ws)
    phase = _current_phase(rs)
    if phase is None:
        print("run is terminal:", rs["status"])
        return 0
    print(phase_prompt(ws, phase))
    return 0


def cmd_run(ws: Path, model: str, dry: bool) -> int:
    rs = read_runstate(ws)
    phase = _current_phase(rs)
    if phase is None:
        print("run is terminal:", rs["status"])
        return 0
    prompt = phase_prompt(ws, phase)
    log_path = sciforge(ws) / "logs" / f"phase_{phase['id'].replace('.', '_')}.log"
    if dry:
        print(prompt)
        return 0
    print(f"[eval] phase {phase['id']} ({phase['name']}) -> model={model}")
    t0 = time.time()
    rc = headless(model, prompt, log_path)
    dt = time.time() - t0
    problems = gate_phase(ws, phase)
    verdict = "PASS" if (rc == 0 and not problems) else "FAIL"
    print(f"[eval] phase {phase['id']}: claude_rc={rc}, wall={dt:.0f}s, gate={verdict}")
    for p in problems:
        print("  -", p)
    # checkpoint regardless of outcome (resume contract)
    rs["budget_snapshot"]["wall_clock_seconds"] += int(dt)
    if verdict == "PASS":
        idx = PHASE_INDEX[phase["id"]]
        rs["last_completed_boundary"] = phase["id"]
        if idx + 1 < len(PHASES):
            nxt = PHASES[idx + 1]
            rs["current_phase"] = nxt["id"]
            rs["next_action"] = f"execute phase {nxt['id']} ({nxt['name']})"
        else:
            rs["status"] = "completed"
            rs["next_action"] = "pipeline complete; run judge"
    else:
        rs["status"] = "paused_blocked"
        rs["next_action"] = (f"phase {phase['id']} gate failed: "
                             + "; ".join(problems)[:300])
    write_runstate(ws, rs)
    print(f"[eval] RUNSTATE: status={rs['status']} next={rs['next_action']}")
    return 0 if verdict == "PASS" else 2


def cmd_run_all(ws: Path, model: str) -> int:
    while True:
        rs = read_runstate(ws)
        if rs["status"] in ("completed", "killed"):
            print("[eval] terminal:", rs["status"])
            return 0
        if rs["status"] == "paused_blocked":
            print("[eval] blocked — fix the skill or artifacts, set RUNSTATE status back to 'running', rerun")
            return 2
        rc = cmd_run(ws, model, dry=False)
        if rc != 0:
            return rc


def cmd_judge(ws: Path, model: str) -> int:
    log_path = sciforge(ws) / "logs" / "judge.log"
    out_path = sciforge(ws) / "tmp" / "judge_raw.txt"
    print(f"[eval] adversarial judge -> model={model}")
    # judge needs the JSON back; capture via a marker file the model writes
    verdict_path = sciforge(ws) / "verdicts" / "EVALUATION_REVIEW.json"
    prompt = judge_prompt(ws) + (
        f"\nAfter producing the JSON, ALSO write the exact same JSON object to this file: {verdict_path}\n")
    rc = headless(model, prompt, log_path, timeout=2400)
    if not verdict_path.exists():
        print("[eval] judge did not write EVALUATION_REVIEW.json — inspect", log_path)
        return 2
    review = json.loads(verdict_path.read_text(encoding="utf-8"))
    print(json.dumps(review, indent=2, ensure_ascii=False)[:3000])
    return 0 if rc == 0 else 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sciforge_eval.py", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "status", "next", "run", "run-all", "judge"):
        sp = sub.add_parser(name)
        sp.add_argument("ws", type=Path)
        if name == "init":
            sp.add_argument("--problem-file")
        if name in ("run", "run-all", "judge"):
            sp.add_argument("--model", default=DEFAULT_MODEL)
        if name == "run":
            sp.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)
    ws = args.ws.resolve()
    if args.cmd == "init":
        return cmd_init(ws, args.problem_file)
    if not runstate_path(ws).exists():
        print(f"workspace not initialized: {ws} (run: sciforge_eval.py init {ws} --problem-file F)")
        return 1
    return {"status": cmd_status, "next": cmd_next,
            "run": lambda w: cmd_run(w, args.model, args.dry),
            "run-all": lambda w: cmd_run_all(w, args.model),
            "judge": lambda w: cmd_judge(w, args.model)}[args.cmd](ws)


if __name__ == "__main__":
    sys.exit(main())
