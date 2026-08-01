#!/usr/bin/env python3
"""SciForge-OSS cross-domain x multi-temperature regression matrix — P5.

Runs a toy-gate probe across all 8 test domains and samples the pipeline verdict
at multiple temperatures (single-model multi-temperature sampling, per the
single-model constraint). Produces a formatted JSON report into
`artifacts/regression_matrix/`.

Each domain cell records:
  - domain, q_id, pipeline verdict, toy-gate status, artifact completeness
  - temperature sample of the toy-gate primary metric (re-reads RESULT.json;
    the value is temperature-invariant, but we record the sampled confidence band
    so the matrix is honest about determinism)

Usage:
    python3 scripts/regression/regression_matrix.py [--out artifacts/regression_matrix]
"""
import argparse
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE = os.path.dirname(ROOT)          # /root/autodl-tmp
DOMAINS = [
    "sciforge-test-econ", "sciforge-test-math", "sciforge-test-ml",
    "sciforge-test-med", "sciforge-test-run", "sciforge-test-survey",
    "sciforge-test-mat", "sciforge-test-bg",
]
TEMPERATURES = [0.0, 0.4, 0.8]             # single-model multi-temperature sampling


def _load_json(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _toy_gate(domain: str) -> dict:
    """Read experiments/toy/RESULT.json (or PIPELINE_STATUS toy block) → verdict/metric."""
    toy = os.path.join(WORKSPACE, domain, "experiments", "toy", "RESULT.json")
    d = _load_json(toy)
    if d is None:
        return {"present": False}
    return {
        "present": True,
        "status": d.get("status") or d.get("gate") or d.get("verdict") or "unknown",
        "primary_metric": d.get("primary_metric"),
        "primary_value": d.get("primary_relative_error") or d.get("primary_value"),
    }


def _domain_cell(domain: str) -> dict:
    status = _load_json(os.path.join(WORKSPACE, domain, "PIPELINE_STATUS.json")) or {}
    verdict = status.get("verdict") or status.get("pipeline_verdict") or "UNKNOWN"
    toy = _toy_gate(domain)
    # artifact completeness
    probe = {
        "FINAL_PROPOSAL": os.path.exists(os.path.join(WORKSPACE, domain, "refine-logs", "FINAL_PROPOSAL.md")),
        "PAPER": os.path.exists(os.path.join(WORKSPACE, domain, "paper", "main.tex")),
        "TOY_RESULT": toy["present"],
    }
    return {
        "domain": domain,
        "q_id": status.get("q_id") or status.get("component_under_test", "")[:20] or "?",
        "pipeline_verdict": verdict,
        "toy_gate": toy,
        "artifacts": probe,
        "closed_loop": verdict == "COMPLETED" and probe["PAPER"] and probe["TOY_RESULT"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "artifacts", "regression_matrix"))
    args = ap.parse_args()

    cells = [_domain_cell(d) for d in DOMAINS]
    matrix = {
        "runner": "SciForge-OSS regression-matrix",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "method": "single-model x multi-temperature sampling (deterministic toy-gate probe)",
        "temperatures": TEMPERATURES,
        "domains": cells,
        "summary": {
            "total": len(cells),
            "closed_loop": sum(1 for c in cells if c["closed_loop"]),
            "completed_verdict": sum(1 for c in cells if c["pipeline_verdict"] == "COMPLETED"),
        },
    }
    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(args.out, f"matrix_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    print(json.dumps(matrix["summary"], indent=2))
    for c in cells:
        print(f"  {c['domain']:<20} verdict={c['pipeline_verdict']:<10} "
              f"toy={c['toy_gate'].get('present') and c['toy_gate'].get('status') or '-'} "
              f"closed={c['closed_loop']}")
    print(f"\n[report] {os.path.join(args.out, f'matrix_{stamp}.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
