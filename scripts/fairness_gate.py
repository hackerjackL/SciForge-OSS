#!/usr/bin/env python3
"""Experiment fairness gate (S33/S54, mode=deepen) — experimental fairness is the
load-bearing property of a deepened paper.

Checks, per comparison table in the workspace, that every method was evaluated
under:
  1. compute_budget_parity   — identical budget lines in the manifest (wall/GPU-h/steps)
  2. data_split_lock         — one frozen split_hash shared by all arms
  3. seed_policy             — seed_count >= min_seeds (default 3) and mean±std present
  4. hparam_budget_parity    — identical search budget per method (no cherry-tuned baselines)
  5. metric_definitions      — same metric names/definitions across arms
  6. reporting completeness  — effect size + CI present in every claim-bearing cell;
     multiple-comparison control declared (none is a WARN, not a FAIL, for single-comparison
     families)

Input: {workspace}/methods/FAIRNESS_LEDGER.json (produced by deepen-mode exec) or
{workspace}/methods/comparisons/*.json per table. Output: FAIRNESS.json (registered verdict).

Exit 0 = PASS/WARN (WARN allowed), 2 = FAIL, 3 = no ledger yet (SKIP).
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

MIN_SEEDS = 3


def load_comparisons(ws: Path) -> list[dict]:
    ledger = ws / "methods" / "FAIRNESS_LEDGER.json"
    if ledger.exists():
        try:
            d = json.loads(ledger.read_text())
            return d.get("comparisons", d if isinstance(d, list) else [])
        except json.JSONDecodeError:
            return []
    cdir = ws / "methods" / "comparisons"
    out = []
    if cdir.is_dir():
        for f in sorted(cdir.glob("*.json")):
            try:
                out.append(json.loads(f.read_text()))
            except json.JSONDecodeError:
                continue
    return out


def check_comparison(c: dict, min_seeds: int = MIN_SEEDS) -> dict:
    problems = []
    if c.get("seed_count", 0) < min_seeds:
        problems.append(f"seed_count {c.get('seed_count', 0)} < {min_seeds}")
    if not c.get("mean_std_reported"):
        problems.append("mean±std not reported")
    if not c.get("effect_size_reported"):
        problems.append("effect size missing in claim-bearing cells")
    if not c.get("ci_reported"):
        problems.append("confidence intervals missing")
    if c.get("multiple_comparison_control") == "none" and len(c.get("methods", [])) > 2:
        problems.append("no multiple-comparison control over >2 methods (WARN)")
    methods = c.get("methods", [])
    budgets = c.get("budget_per_method", {})
    if budgets and len(set(map(str, budgets.values()))) > 1:
        problems.append(f"compute budget asymmetry across methods: {budgets}")
    splits = c.get("split_hash_per_method", {})
    if splits and len(set(splits.values())) > 1:
        problems.append(f"data split not locked (hashes differ): {splits}")
    hparam = c.get("hparam_budget_per_method", {})
    if hparam and len(set(map(str, hparam.values()))) > 1:
        problems.append(f"hparam search budget asymmetry: {hparam}")
    metrics = c.get("metric_definitions", {})
    if metrics and len(set(map(str, metrics.values()))) > 1:
        problems.append("metric definitions differ across methods")
    return {"table_id": c.get("table_id", "?"), "problems": problems,
            "warn_only": all(p.startswith("no multiple-comparison") for p in problems) and bool(problems)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    ap.add_argument("--min-seeds", type=int, default=MIN_SEEDS)
    args = ap.parse_args(argv)
    ws = args.workspace
    comps = load_comparisons(ws)
    if not comps:
        print("fairness_gate: no FAIRNESS_LEDGER.json / methods/comparisons/*.json — SKIP")
        return 3
    results = [check_comparison(c, args.min_seeds) for c in comps]
    hard_fails = [r for r in results if r["problems"] and not r["warn_only"]]
    warns = [r for r in results if r["warn_only"]]
    verdict = "FAIL" if hard_fails else ("WARN" if warns else "PASS")
    out = {
        "gate": "experiment-fairness", "version": "v1.5.0-w2",
        "verdict": verdict,
        "checks": {
            "compute_budget_parity": "FAIL" if any("budget asymmetry" in p for r in results for p in r["problems"]) else "PASS",
            "data_split_lock": "FAIL" if any("split not locked" in p for r in results for p in r["problems"]) else "PASS",
            "seed_policy": "FAIL" if any("seed_count" in p for r in results for p in r["problems"]) else "PASS",
            "hparam_budget_parity": "FAIL" if any("hparam" in p for r in results for p in r["problems"]) else "PASS",
            "metric_definitions": "FAIL" if any("metric definitions" in p for r in results for p in r["problems"]) else "PASS",
        },
        "comparisons": [{
            "table_id": r["table_id"],
            "methods": next((c.get("methods", []) for c in comps if c.get("table_id") == r["table_id"]), []),
            "seed_count": next((c.get("seed_count", 0) for c in comps if c.get("table_id") == r["table_id"]), 0),
            "mean_std_reported": not any("mean±std" in p for p in r["problems"]),
            "effect_size_reported": not any("effect size" in p for p in r["problems"]),
            "ci_reported": not any("confidence intervals" in p for p in r["problems"]),
            "multiple_comparison_control": next((c.get("multiple_comparison_control", "none")
                                                 for c in comps if c.get("table_id") == r["table_id"]), "none"),
        } for r in results],
        "numbers_stale": False,
        "unfair_notes": [f"{r['table_id']}: {'; '.join(r['problems'])}" for r in results if r["problems"]],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    print(json.dumps({"verdict": verdict,
                      "fail_tables": [r["table_id"] for r in hard_fails],
                      "warn_tables": [r["table_id"] for r in warns]}, indent=2))
    if args.write_verdict:
        vp = ws / ".sciforge" / "verdicts"
        vp.mkdir(parents=True, exist_ok=True)
        (vp / "FAIRNESS.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        (ws / "methods" / "FAIRNESS.md").parent.mkdir(exist_ok=True)
        (ws / "methods" / "FAIRNESS.md").write_text(
            "# Experiment Fairness Audit\n\n"
            + "\n".join(f"- **{r['table_id']}**: " + ("clean" if not r["problems"] else "; ".join(r["problems"]))
                        for r in results) + "\n")
    return 0 if verdict in ("PASS", "WARN") else 2


if __name__ == "__main__":
    sys.exit(main())
