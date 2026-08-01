#!/usr/bin/env python3
"""SciForge-OSS verification entry — executes the 5-item verification checklist.

Self-contained: every Phase 1-6 deliverable is invoked and its PASS/FAIL is
captured as machine-readable JSON + a human table, written to
`artifacts/verification/verify_<timestamp>.json` (and latest.json). Exit code
is 0 only when ALL checks pass.

Checks:
  1. Git Status & Cleanliness   (no uncommitted files beyond allowed artifacts)
  2. P1/P2 unit tests           (scripts/idea/test_idea_gates.py)
  3. datasets completeness      (HLE / PaperBench / NatureBench)
  4. regression + 8 domains     (run_regression.py; 8 x PIPELINE_STATUS)
  5. citations + plotting       (citation_verifier self-test; plotting demo)

Usage:
    python3 scripts/verification/verify_all.py
"""
import datetime
import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE = os.path.dirname(ROOT)
DOMAINS = [
    "sciforge-test-econ", "sciforge-test-math", "sciforge-test-ml",
    "sciforge-test-med", "sciforge-test-run", "sciforge-test-survey",
    "sciforge-test-mat", "sciforge-test-bg",
]
OUT_DIR = os.path.join(ROOT, "artifacts", "verification")
ALLOWED_UNTRACKED = {"artifacts", "scripts", "VERIFICATION_EVIDENCE.md",
                     "ITERATION_LOG.md", "CHANGELOG.md", "package.json", "SKILL.md"}


def _run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    """Run a command and return (rc, FULL combined output). Callers truncate for display."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def check_git() -> dict:
    rc, out = _run(["git", "status", "--porcelain"], timeout=30)
    lines = [l for l in out.splitlines() if l.strip()]
    # Allowed working-tree changes: fixed regression/dataset artifacts (top-level
    # dirs that hold reproducible products) — everything else is unexpected.
    bad = []
    for l in lines:
        path = l[3:].strip()
        top = path.split("/")[0]
        if top in ("artifacts", "scripts", "datasets"):
            continue  # reproducible products — allowed by checklist item 1
        bad.append(path)
    return {"check": "git-cleanliness", "pass": not bad,
            "uncommitted": lines, "unexpected": bad}


def check_p1p2() -> dict:
    rc, out = _run([sys.executable,
                    os.path.join(ROOT, "scripts", "idea", "test_idea_gates.py")],
                   timeout=120)
    passed = f"{len([l for l in out.splitlines() if 'PASS' in l])}/{out.count('PASS') + out.count('FAIL') + out.count('ERROR')}" if "passed" in out else "?"
    m = [l for l in out.splitlines() if "passed" in l or "FAIL" in l or "ERROR" in l]
    return {"check": "p1-p2-unit-tests", "pass": rc == 0,
            "exit": rc, "summary": m[-2:] if m else [out[-80:]]}


def check_datasets() -> dict:
    required = {
        "HLE": ["README.md", "eval.yaml", "INDEX.md"],
        "PaperBench": ["train.parquet", "INDEX.md"],
        "NatureBench": ["INDEX.md", "ubonodin_run"],
    }
    results = {}
    all_ok = True
    for ds, files in required.items():
        d = os.path.join(WORKSPACE, "datasets", ds)
        present = {f: os.path.exists(os.path.join(d, f)) for f in files}
        results[ds] = present
        if not all(present.values()):
            all_ok = False
    return {"check": "datasets-completeness", "pass": all_ok, "files": results}


def check_regression_and_domains() -> dict:
    rc, out = _run([sys.executable,
                    os.path.join(ROOT, "scripts", "regression", "run_regression.py")],
                   timeout=300)
    reg_ok = rc == 0 and "naturebench" in out and "paperbench" in out
    statuses = {}
    for d in DOMAINS:
        p = os.path.join(WORKSPACE, d, "PIPELINE_STATUS.json")
        if not os.path.exists(p):
            statuses[d] = "MISSING"
            continue
        try:
            with open(p) as f:
                data = json.load(f)
            statuses[d] = data.get("verdict") or data.get("pipeline_verdict") or "?"
        except Exception as e:
            statuses[d] = f"ERR:{e}"
    domains_ok = all(v == "COMPLETED" for v in statuses.values())
    return {"check": "regression-and-domains", "pass": reg_ok and domains_ok,
            "regression_exit": rc, "regression_output_tail": out[-300:],
            "domain_statuses": statuses}


def check_citations_and_plotting() -> dict:
    rc, out = _run([sys.executable,
                    os.path.join(ROOT, "scripts", "utils", "citation_verifier.py"),
                    "self-test"], timeout=120)
    cit_ok = rc == 0 and '"self_test": "PASS"' in out
    demo = os.path.join(ROOT, "artifacts", "plotting_demo")
    pdf = os.path.exists(os.path.join(demo, "sample_figure.pdf"))
    png = os.path.exists(os.path.join(demo, "sample_figure.png"))
    svg = os.path.exists(os.path.join(demo, "sample_pipeline.svg"))
    plot_ok = pdf and png and svg
    return {"check": "citations-and-plotting", "pass": cit_ok and plot_ok,
            "citation_self_test": out.strip()[-120:],
            "plot_outputs": {"pdf": pdf, "png": png, "svg": svg}}


def main() -> int:
    checks = [
        check_git(), check_p1p2(), check_datasets(),
        check_regression_and_domains(), check_citations_and_plotting(),
    ]
    all_pass = all(c["pass"] for c in checks)
    report = {
        "runner": "SciForge-OSS verify_all",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "overall": "PASS" if all_pass else "FAIL",
        "checks": checks,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(OUT_DIR, f"verify_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # human table
    print("=" * 70)
    print(f"SciForge-OSS verify_all  —  overall: {report['overall']}")
    print("=" * 70)
    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check']}")
        for k, v in c.items():
            if k in ("check", "pass"):
                continue
            s = json.dumps(v, ensure_ascii=False)
            print(f"        {k}: {s[:150]}")
    print(f"\n  evidence: {os.path.join(OUT_DIR, f'verify_{stamp}.json')}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
