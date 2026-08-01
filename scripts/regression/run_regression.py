#!/usr/bin/env python3
"""SciForge-OSS unified regression runner — P4 automation.

One-shot runner that executes sampled tasks from NatureBench / HLE / PaperBench,
computes correlation / accuracy / MAE metrics and writes a formatted JSON report
into `artifacts/regression/`.

Default registry (edit to extend):
    NatureBench : scripts/regression/naturebench_ubonodin_baseline.py (reproducible)
    HLE         : sample QA from datasets/HLE (requires gated data — skips with note)
    PaperBench  : sample rubric tasks from datasets/PaperBench/train.parquet

Usage:
    python3 scripts/regression/run_regression.py [--out artifacts/regression] [--quick]
"""
import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASETS = os.path.join(ROOT, "..", "datasets") if os.path.isdir(os.path.join(ROOT, "..", "datasets")) \
    else os.path.join(os.path.dirname(ROOT), "datasets")
ARTIFACTS = os.path.join(ROOT, "artifacts", "regression")


def _run_naturebench() -> dict:
    """Run the reproducible NatureBench ubonodin baseline; return its metrics."""
    nb_dir = os.path.join(DATASETS, "NatureBench", "ubonodin_run")
    script = os.path.join(ROOT, "scripts", "regression", "naturebench_ubonodin_baseline.py")
    if not all(os.path.exists(os.path.join(nb_dir, f)) for f in
               ("train.csv", "test_input.csv", "ground_truth.csv")):
        return {"status": "SKIPPED", "reason": "naturebench data missing"}
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(
            [sys.executable, script,
             "--train", os.path.join(nb_dir, "train.csv"),
             "--test", os.path.join(nb_dir, "test_input.csv"),
             "--gt", os.path.join(nb_dir, "ground_truth.csv"),
             "--out", td],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return {"status": "FAIL", "reason": r.stderr[-400:]}
        try:
            with open(os.path.join(td, "score.json")) as f:
                return {"status": "PASS", "metrics": json.load(f)}
        except (json.JSONDecodeError, FileNotFoundError):
            return {"status": "FAIL", "reason": "no score.json produced"}


def _run_hle() -> dict:
    """HLE sample QA — gated dataset; report index-only registration."""
    hle_dir = os.path.join(DATASETS, "HLE")
    if not os.path.exists(os.path.join(hle_dir, "eval.yaml")):
        return {"status": "SKIPPED", "reason": "HLE index missing"}
    # Without authenticated full parquet we cannot run QA; keep as registered-index probe.
    return {"status": "INDEX_ONLY", "reason": "gated dataset — full parquet needs HF auth",
            "note": "registered: README.md + eval.yaml + schema (see datasets/HLE/INDEX.md)"}


def _run_paperbench(quick: bool = True) -> dict:
    """PaperBench rubric sample — parse parquet, count tasks, sanity-check rubric tree."""
    pb = os.path.join(DATASETS, "PaperBench", "train.parquet")
    if not os.path.exists(pb):
        return {"status": "SKIPPED", "reason": "paperbench parquet missing"}
    try:
        import pandas as pd
        df = pd.read_parquet(pb)
        n = min(len(df), 5) if quick else len(df)
        rows = []
        for i in range(n):
            rub = df.iloc[i].get("rubric") or {}
            rows.append({
                "paper_id": df.iloc[i].get("paper_id"),
                "requirements": (rub.get("requirements") or "")[:120],
                "sub_tasks_count": len(rub.get("sub_tasks") or []) if isinstance(rub.get("sub_tasks"), (list, tuple)) else 0,
            })
        return {"status": "PASS", "total_tasks": int(len(df)),
                "sampled": n, "sample": rows,
                "metric": "rubric-coverage (checklist-based scoring)"}
    except Exception as e:
        return {"status": "FAIL", "reason": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=ARTIFACTS)
    ap.add_argument("--quick", action="store_true", default=True,
                    help="limit PaperBench sample to 5 tasks (default)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    report = {
        "runner": "SciForge-OSS regression",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "env": {"mihomo": os.path.exists("/usr/local/bin/mihomo")},
        "results": {
            "naturebench": _run_naturebench(),
            "hle": _run_hle(),
            "paperbench": _run_paperbench(quick=args.quick),
        },
    }
    out_path = os.path.join(args.out, f"regression_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # also write latest.json for stable path
    with open(os.path.join(args.out, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n[report] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
