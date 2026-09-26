#!/usr/bin/env python3
"""Dependency gate (v1.6.0) — "the model cannot use whatever it wants."

The toolchain-unity promise is hollow if agent-authored code imports anything it
likes: an unlisted package silently breaks reproducibility on another machine,
and a stray `import seaborn` in a figure bypasses the unified renderer contract.
This gate makes the dependency surface DECLARATIVE and ENFORCED:

  - the single source of truth is kernel/config/dependencies.json (tiers mirror
    requirements.txt);
  - stdlib is always allowed (auto-detected via sys.stdlib_module_names, so the
    manifest never has to enumerate it);
  - every import root in agent-authored code (src/**.py and figures/**/render.py)
    must be in the manifest or it is a violation -> FAIL;
  - `always_forbidden` roots (pip/setuptools) fail even if a tier lists them.

This is the SAME architecture as gap_gate/fairness_gate/smoke_gate: a standalone
script the kernel boundary runs, exit 0 = PASS/SKIP, exit 2 = FAIL. It does NOT
touch security_scan.py (which guards *how* code behaves — network, credentials,
destructive ops); dep_gate guards *what it imports*. Together: supply-chain
(SEC-106 pip) + import allowlist + behavior scan = the dependency story.

Usage: python3 scripts/dep_gate.py <workspace> [--manifest PATH] [--json]
Exit: 0 PASS/SKIP, 2 FAIL (undeclared imports).
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "kernel" / "config" / "dependencies.json"

# stdlib roots (3.10+); union with the running interpreter's own set so the gate
# never blocks a standard import regardless of Python version drift.
_STDLIB = set(getattr(sys, "stdlib_module_names", set()))


def _allowed_roots(manifest: dict) -> set[str]:
    roots: set[str] = set()
    for tier in (manifest.get("python") or {}).values():
        roots.update(tier)
    # a dotted package (torch_npu, language_tool_python) is its own root token;
    # also register the top segment so `import a.b` resolves
    for r in list(roots):
        roots.add(r.split(".")[0])
    return roots


def _import_roots(path: Path) -> list[tuple[int, str]]:
    """(lineno, root) for every import in a .py file (best-effort on syntax errors)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []  # security_scan already flags unparseable; not this gate's job
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((node.lineno, a.name.split(".")[0]))
        elif isinstance(node, ast.ImportFrom):
            # relative imports (node.level>0) are intra-package: always allowed
            if node.module and node.level == 0:
                out.append((node.lineno, node.module.split(".")[0]))
    return out


def check(ws: Path, manifest: dict) -> dict:
    allowed = _allowed_roots(manifest)
    forbidden = set((manifest.get("always_forbidden") or {}).get("roots", []))
    targets = sorted({p for pat in ("src", "figures")
                      for p in (ws / pat).rglob("*.py")} if (ws / "src").is_dir()
                     or (ws / "figures").is_dir() else [])
    violations = []
    scanned = 0
    for f in targets:
        scanned += 1
        for lineno, root in _import_roots(f):
            if root in forbidden:
                violations.append({"file": str(f.relative_to(ws)), "line": lineno,
                                   "import": root, "why": "always-forbidden root"})
            elif root in _STDLIB:
                continue
            elif root not in allowed:
                violations.append({"file": str(f.relative_to(ws)), "line": lineno,
                                   "import": root,
                                   "why": "not in dependencies.json (add to a tier "
                                          "+ requirements.txt, or use an allowed package)"})
    return {"scanned": scanned, "violations": violations,
            "allowed_roots": len(allowed)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.manifest.exists():
        print(f"dep_gate: FAIL — manifest missing {args.manifest}", file=sys.stderr)
        return 2
    manifest = json.loads(args.manifest.read_text())
    res = check(args.workspace, manifest)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    if res["violations"]:
        if not args.json:
            for v in res["violations"]:
                print(f"dep_gate: FAIL — {v['file']}:{v['line']} import {v['import']} — {v['why']}")
        return 2
    if res["scanned"] == 0:
        print("dep_gate: SKIP (no agent-authored python under src/ or figures/)")
    else:
        print(f"dep_gate: PASS ({res['scanned']} file(s), all imports declared)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
