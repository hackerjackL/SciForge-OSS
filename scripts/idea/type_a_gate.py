#!/usr/bin/env python3
"""SciForge-OSS Type-A objective hard gate — P2 mechanism (0 LLM cost, pure Python).

Decouples OBJECTIVE hard-elimination from SUBJECTIVE quality judgment:

- Type-A (this script): purely mechanical checks — estimated GPU memory fit,
  data availability, dependency conflicts, code syntax (AST parse) for any
  proposed method. Any FAIL eliminates the idea at ZERO LLM cost, BEFORE any
  LLM quality scoring (Phase 2.5 / Phase 3).
- Type-B (NOT here): subjective quality adjudication (Novelty / Soundness /
  Impact) done by review sub-agents AFTER Type-A passes.

Input: a JSON idea spec (see schema below). Output: verdict JSON.

CLI:
    python3 scripts/idea/type_a_gate.py <idea_spec.json> [--gpu-gb 24]
Schema (idea_spec.json):
{
  "id": "Q042-idea-3",
  "requires_gpu_gb": 8.0,            // estimated peak GPU memory in GB
  "requires_packages": ["torch", "numpy"],
  "data_required": true,             // does the method need external data?
  "data_sources": ["https://huggingface.co/datasets/x", "local:data/"],
  "code_snippet": "import numpy as np\n...",  // optional small AST-checkable snippet
  "notes": "any free text"
}
"""
import ast
import json
import os
import sys
import urllib.request

GPU_EST_OVERHEAD = 1.5   # multiplier: estimate vs actual allocation safety


# --------------------------------------------------------------------------- #
# Type-A sub-checks (all mechanical, 0 LLM cost)
# --------------------------------------------------------------------------- #
def check_gpu(idea: dict, gpu_total_gb: float) -> dict:
    need = float(idea.get("requires_gpu_gb", 0.0)) * GPU_EST_OVERHEAD
    if need <= 0.0:
        return {"ok": True, "check": "gpu", "detail": "no GPU required"}
    ok = need <= gpu_total_gb
    return {"ok": ok, "check": "gpu",
            "detail": f"need ~{need:.1f}GB (est {idea.get('requires_gpu_gb')}x1.5) vs available {gpu_total_gb}GB",
            "fail_reason": "gpu_oom_estimated" if not ok else None}


def _data_source_ok(src: str) -> tuple[bool, str]:
    src = src.strip()
    if src.startswith("local:") or src.startswith("./") or src.startswith("../") or src.startswith("/"):
        p = src.split("local:", 1)[-1] if src.startswith("local:") else src
        if os.path.exists(p) and os.path.isdir(p):
            return True, "local-dir-exists"
        # allow "local:data/" even if not yet created — treated as plan, not blocker
        return True, "local-path-declared"
    if src.startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(src, method="HEAD")
            with urllib.request.urlopen(req, timeout=6) as r:
                return r.status < 400, f"http-{r.status}"
        except Exception as e:
            return False, f"unreachable:{type(e).__name__}"
    return True, "unknown-source-pass"


def check_data(idea: dict) -> dict:
    if not idea.get("data_required"):
        return {"ok": True, "check": "data", "detail": "no external data required"}
    sources = idea.get("data_sources", []) or []
    if not sources:
        return {"ok": False, "check": "data",
                "detail": "data_required=true but data_sources empty",
                "fail_reason": "missing_data_source"}
    failures = []
    for src in sources:
        ok, why = _data_source_ok(src)
        if not ok:
            failures.append({"src": src, "why": why})
    return {"ok": len(failures) == 0, "check": "data",
            "detail": f"{len(sources) - len(failures)}/{len(sources)} sources reachable",
            "failures": failures,
            "fail_reason": "data_unavailable" if failures else None}


def check_dependencies(idea: dict) -> dict:
    pkgs = idea.get("requires_packages", []) or []
    if not pkgs:
        return {"ok": True, "check": "deps", "detail": "no packages required"}
    missing = []
    for p in pkgs:
        try:
            __import__(p.replace("-", "_").split("[")[0])
        except ImportError:
            missing.append(p)
    return {"ok": len(missing) == 0, "check": "deps",
            "detail": f"missing={missing}" if missing else f"all {len(pkgs)} importable",
            "fail_reason": "missing_dependency" if missing else None}


def check_syntax(idea: dict) -> dict:
    snippet = idea.get("code_snippet", "") or ""
    if not snippet.strip():
        return {"ok": True, "check": "syntax", "detail": "no code snippet to check"}
    try:
        ast.parse(snippet)
        return {"ok": True, "check": "syntax", "detail": "AST parse OK"}
    except SyntaxError as e:
        return {"ok": False, "check": "syntax",
                "detail": f"SyntaxError: {e}",
                "fail_reason": "code_syntax_error"}


# --------------------------------------------------------------------------- #
# orchestrator
# --------------------------------------------------------------------------- #
def run_type_a(idea: dict, gpu_total_gb: float = 24.0) -> dict:
    checks = [
        check_gpu(idea, gpu_total_gb),
        check_data(idea),
        check_dependencies(idea),
        check_syntax(idea),
    ]
    verdict = "PASS" if all(c["ok"] for c in checks) else "FAIL"
    return {
        "gate": "Type-A",
        "id": idea.get("id", "?"),
        "verdict": verdict,
        "llm_cost": 0,
        "checks": checks,
        "next": "Type-B review (novelty/soundness/impact)" if verdict == "PASS"
                else "eliminated at zero cost — do NOT advance to Type-B",
        "fail_reasons": [c["fail_reason"] for c in checks if c.get("fail_reason")],
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    with open(argv[1], "r", encoding="utf-8") as f:
        idea = json.load(f)
    gpu = 24.0
    for i, a in enumerate(argv):
        if a == "--gpu-gb" and i + 1 < len(argv):
            gpu = float(argv[i + 1])
    result = run_type_a(idea, gpu)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
