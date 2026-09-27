#!/usr/bin/env python3
"""S2-demo bench harness — our demo sub-bench in the ScientistTwo mold.

Why this exists: ScientistTwo scored 86/107 real conference problems with a
subset→full-set ladder and a human-anchored reviewer; we have no GPU here, so
this bench keeps their *structure* on CPU-only synthetic problems:

  - open-ended research briefing per task (task.json / task.py docstring)
  - a real baseline that must be reproduced before the candidate counts
  - subset → full-set two-stage verification with the SAME 3-state Critic the
    kernel enforces at the 6c boundary (kernel/sciforge/s2/ladder.py — this
    harness imports the production gate logic, not a copy)
  - relative-gain-over-baseline reporting (their "+25.2% over human SOTA"
    metric, ours over the task baseline)
  - rubric + human-anchor fields per task for calibrated review scoring

Everything is numpy-only and runs offline in seconds on any CPU (Colab free
tier included). Solutions are plain python files exposing:

    solve(train: dict, test: dict) -> np.ndarray   # predictions / labels

Usage:
  python3 bench/s2demo/run.py --list
  python3 bench/s2demo/run.py --task T1                 # baseline vs candidate
  python3 bench/s2demo/run.py --task all --out DIR
  python3 bench/s2demo/run.py --task T1 --solution my.py # evaluate your solve()

Exit codes: 0 = every run PROMOTED (candidate strictly beats baseline on the
full set), 2 = at least one task DISCARDED/TUNE/invalid.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parents[1]
if str(REPO_ROOT / "kernel") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge.s2 import ladder as ladder_mod  # noqa: E402  production gate logic


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def discover_tasks() -> list[Path]:
    tasks_dir = BENCH_DIR / "tasks"
    return sorted(p.parent for p in tasks_dir.glob("*/task.py"))


def _metric(task, y_true, y_pred) -> float:
    return float(task.score(y_true, y_pred))


def run_task(task_dir: Path, solution_path: Path | None = None,
             out_dir: Path | None = None) -> dict:
    task = load_module(task_dir / "task.py", f"s2task_{task_dir.name}")
    baseline = load_module(task_dir / "baseline.py", f"s2base_{task_dir.name}")
    cand_path = solution_path or (task_dir / "candidate.py")
    candidate = load_module(cand_path, f"s2cand_{task_dir.name}_{abs(hash(str(cand_path)))}")

    splits: dict[str, dict] = {}
    t0 = time.time()
    for split in ("subset", "full"):
        data = task.make_data(split)
        y = data["test"]["y"]
        t_b = time.time()
        pred_b = baseline.solve(data["train"], data["test"])
        dur_b = time.time() - t_b
        t_c = time.time()
        pred_c = candidate.solve(data["train"], data["test"])
        dur_c = time.time() - t_c
        b = _metric(task, y, pred_b)
        c = _metric(task, y, pred_c)
        splits[split] = {"n_train": len(data["train"]["y"]), "n_eval": len(y),
                         "baseline": round(b, 6), "candidate": round(c, 6),
                         "baseline_s": round(dur_b, 3), "candidate_s": round(dur_c, 3)}

    direction = task.DIRECTION
    subset_state = ladder_mod.decide(splits["subset"]["baseline"],
                                     splits["subset"]["candidate"], direction)
    full_improved = ladder_mod.is_improvement(splits["full"]["baseline"],
                                              splits["full"]["candidate"], direction)
    if subset_state == "GOOD" and not full_improved:
        # subset win that vanishes at full scale = did not replicate => BAD
        final_state, rationale = "BAD", "subset GOOD but full-set verification failed"
    elif subset_state == "GOOD":
        final_state, rationale = "GOOD", "subset GOOD + full-set strictly better"
    else:
        final_state, rationale = subset_state, f"subset critic={subset_state}"

    gain = ladder_mod.relative_gain(splits["full"]["baseline"],
                                    splits["full"]["candidate"], direction)
    ladder_doc = {
        "schema_version": ladder_mod.SCHEMA_VERSION,
        "problem_id": task_dir.name,
        "metric": {"name": task.METRIC_NAME, "direction": direction},
        "subset": {"n": splits["subset"]["n_eval"],
                   "baseline": {"value": splits["subset"]["baseline"]},
                   "candidate": {"value": splits["subset"]["candidate"]}},
        "critic": {"state": final_state, "engineer_rounds": 0, "rationale": rationale},
        "fullset": {"n": splits["full"]["n_eval"], "verified": full_improved,
                    "baseline": {"value": splits["full"]["baseline"]},
                    "candidate": {"value": splits["full"]["candidate"]}},
        "relative_gain_pct": round(gain, 4),
    }
    problems = ladder_mod.validate(ladder_doc)
    verdict = {"GOOD": "PROMOTED", "ENGINEER": "TUNE", "BAD": "DISCARDED"}[final_state]

    report = {
        "task": task_dir.name,
        "title": getattr(task, "TITLE", task_dir.name),
        "metric": {"name": task.METRIC_NAME, "direction": direction},
        "solution": str(cand_path),
        "splits": splits,
        "critic": ladder_doc["critic"],
        "verdict": verdict,
        "relative_gain_pct": ladder_doc["relative_gain_pct"],
        "ladder_valid": not problems,
        "ladder_problems": problems,
        "rubric": getattr(task, "RUBRIC", []),
        "human_anchor": getattr(task, "HUMAN_ANCHOR", None),
        "wall_s": round(time.time() - t0, 3),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = f"{task_dir.name}__{Path(cand_path).stem}"
        (out / f"{stem}.report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False))
        (out / f"{stem}.S2_LADDER.json").write_text(
            json.dumps(ladder_doc, indent=2, ensure_ascii=False))
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", default=None, help="task dir name or 'all'")
    ap.add_argument("--solution", type=Path, default=None,
                    help="external solution .py exposing solve(train, test)")
    ap.add_argument("--out", type=Path, default=BENCH_DIR / "results",
                    help="report output dir (default: bench/s2demo/results, gitignored)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    tasks = discover_tasks()
    if args.list or not args.task:
        for t in tasks:
            print(t.name)
        if not args.task:
            print("(pass --task <name>|all to run)")
        return 0
    if args.task == "all":
        selected = tasks
    else:
        selected = [t for t in tasks if t.name.startswith(args.task) or t.name == args.task]
        if not selected:
            print(f"no task matching {args.task!r}", file=sys.stderr)
            return 2

    rc = 0
    for t in selected:
        try:
            rep = run_task(t, args.solution, args.out)
        except Exception:
            print(f"[{t.name}] ERROR\n{traceback.format_exc()}")
            rc = 2
            continue
        ok = rep["verdict"] == "PROMOTED" and rep["ladder_valid"]
        rc = rc or (0 if ok else 2)
        print(f"[{rep['task']}] {rep['verdict']}  "
              f"subset={rep['splits']['subset']}  full={rep['splits']['full']}  "
              f"gain={rep['relative_gain_pct']}%  ladder_valid={rep['ladder_valid']}")
        if rep["ladder_problems"]:
            for p in rep["ladder_problems"]:
                print(f"    - {p}")
    print(f"reports -> {args.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
