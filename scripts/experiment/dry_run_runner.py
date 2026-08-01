#!/usr/bin/env python3
"""SciForge-OSS Dry-Run Early-Exit runner — P5 sub-agent dry-run mechanism.

After an idea is confirmed and code is generated, run a minimal dry-run on a
1%-5% toy subset for 3-5 minutes and EARLY-EXIT on:

  1. UNCAUGHT_EXCEPTION — the run script raises (syntax/runtime/import error)
  2. LOSS_EXPLOSION     — loss/metric becomes NaN/Inf or grows beyond threshold
  3. BELOW_BASELINE     — final metric significantly below the given baseline

On early-exit, the failure feedback is returned to the idea-fix loop so the
full-scale compute is never wasted. Returns a structured JSON verdict.

CLI:
    python3 scripts/experiment/dry_run_runner.py <run_script> \
        [--timeout 300] [--scale 0.02] [--baseline 0.5] \
        [--metric-key val_loss] [--loss-explosion-threshold 1e6]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

EARLY_EXIT_REASONS = ("UNCAUGHT_EXCEPTION", "LOSS_EXPLOSION", "BELOW_BASELINE")


def _scan_output(text: str, metric_key: str | None, explosion_threshold: float) -> str | None:
    """Scan run output for NaN/Inf or exploding metric -> return reason or None."""
    if "nan" in text.lower() and "loss" in text.lower():
        return "LOSS_EXPLOSION"
    if metric_key:
        # crude scan: find last `metric_key = <value>` or `metric_key: <value>`
        for line in reversed(text.splitlines()):
            low = line.lower()
            if metric_key.lower() in low and ("=" in line or ":" in line):
                try:
                    val = float(line.split("=")[-1].split(":")[-1].strip().rstrip(","))
                    if val != val or val in (float("inf"), float("-inf")) or abs(val) > explosion_threshold:
                        return "LOSS_EXPLOSION"
                except ValueError:
                    continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_script", help="path to the experiment script to dry-run")
    ap.add_argument("--timeout", type=int, default=300, help="dry-run hard cap seconds (3-5min)")
    ap.add_argument("--scale", type=float, default=0.02, help="toy subset ratio (1%-5% default 2%)")
    ap.add_argument("--baseline", type=float, default=None, help="baseline metric to compare")
    ap.add_argument("--metric-key", default=None, help="metric key to extract for baseline check")
    ap.add_argument("--loss-explosion-threshold", type=float, default=1e6)
    ap.add_argument("--env", nargs="*", default=[], help="extra KEY=VALUE env vars")
    args = ap.parse_args()

    if not os.path.exists(args.run_script):
        print(json.dumps({"verdict": "ERROR", "reason": "UNCAUGHT_EXCEPTION",
                          "detail": f"run script not found: {args.run_script}"}))
        return 2

    env = dict(os.environ)
    env["DRY_RUN_SCALE"] = str(args.scale)
    for kv in args.env:
        k, _, v = kv.partition("=")
        env[k] = v

    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, args.run_script],
            capture_output=True, text=True, timeout=args.timeout, env=env)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        print(json.dumps({"verdict": "TIMEOUT", "reason": "DRY_RUN_TIMEOUT",
                          "detail": f"exceeded {args.timeout}s cap",
                          "elapsed_seconds": round(time.time() - start, 2)}))
        return 1
    except Exception as e:  # pragma: no cover
        print(json.dumps({"verdict": "ERROR", "reason": "UNCAUGHT_EXCEPTION",
                          "detail": f"{type(e).__name__}: {e}"}))
        return 2

    text = (out + "\n" + err)
    if rc != 0:
        print(json.dumps({"verdict": "EARLY_EXIT", "reason": "UNCAUGHT_EXCEPTION",
                          "exit_code": rc, "detail": err[-400:] or out[-400:],
                          "elapsed_seconds": round(time.time() - start, 2)}))
        return 1

    explosion = _scan_output(text, args.metric_key, args.loss_explosion_threshold)
    if explosion:
        print(json.dumps({"verdict": "EARLY_EXIT", "reason": "LOSS_EXPLOSION",
                          "detail": "NaN/Inf or exploding metric detected in output",
                          "elapsed_seconds": round(time.time() - start, 2)}))
        return 1

    # baseline comparison: extract last metric value if baseline provided
    if args.baseline is not None and args.metric_key:
        last_val = None
        for line in reversed(text.splitlines()):
            low = line.lower()
            if args.metric_key.lower() in low and ("=" in line or ":" in line):
                try:
                    last_val = float(line.split("=")[-1].split(":")[-1].strip().rstrip(","))
                    break
                except ValueError:
                    continue
        if last_val is not None:
            # metric is a loss: below-baseline means ABOVE baseline value
            if last_val > args.baseline * 1.5:
                print(json.dumps({"verdict": "EARLY_EXIT", "reason": "BELOW_BASELINE",
                                  "metric_key": args.metric_key,
                                  "metric_value": last_val, "baseline": args.baseline,
                                  "detail": f"metric {last_val} > 1.5x baseline {args.baseline}",
                                  "elapsed_seconds": round(time.time() - start, 2)}))
                return 1

    print(json.dumps({"verdict": "PASS", "exit_code": 0,
                      "elapsed_seconds": round(time.time() - start, 2),
                      "scale_ratio": args.scale,
                      "output_tail": out[-300:]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
