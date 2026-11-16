#!/usr/bin/env python3
"""Score an ARC-Bench run against its official rubric, mechanically.

Why this exists: three evaluation agents each self-assessing in prose produce
three incomparable answers. The rubric is a weighted tree whose leaves sum to
100, so a single scorer turns their per-leaf verdicts into one number and, more
importantly, makes the *evidence* for each leaf auditable.

Input: a JSON assessment file mapping leaf id -> {verdict, evidence}, where
verdict is one of met / partial / unmet. Weights come from the official rubric
file, never from the assessor — an agent cannot inflate its score by rewriting
weights.

Scoring: met = full leaf weight, partial = half, unmet = 0. `partial` is a real
category in these rubrics ("partial but well-motivated simulations deserve
partial credit"), so it is not rounded up to met.

Also reports the hard requirements (must_pass) separately: a run can score well
on the rubric and still fail a must_pass artifact requirement, and those two
facts must not be averaged into one misleading number.

Usage:
  python scripts/bench_score.py <run_dir> [--assessment <file>] [--json]

With no --assessment it prints the rubric leaves and a template to fill in.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERDICT_CREDIT = {"met": 1.0, "partial": 0.5, "unmet": 0.0}


def leaves(node: dict, out: list | None = None) -> list[dict]:
    out = [] if out is None else out
    kids = node.get("sub_tasks") or []
    if not kids:
        out.append(node)
    for k in kids:
        leaves(k, out)
    return out


def load_rubric(run: Path) -> dict:
    p = run / "results" / "benchmark" / "ARC_RUBRIC.json"
    if not p.is_file():
        raise SystemExit(f"no rubric at {p}")
    return json.loads(p.read_text())


def load_task(run: Path) -> dict:
    p = run / "results" / "benchmark" / "ARC_TASK.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def must_pass_requirements(task: dict) -> list[dict]:
    reqs = task.get("requirements")
    if isinstance(reqs, str):
        try:
            reqs = json.loads(reqs)
        except ValueError:
            return []
    if not isinstance(reqs, list):
        return []
    return [r for r in reqs if isinstance(r, dict) and r.get("must_pass")]


def check_requirements(run: Path, task: dict) -> list[dict]:
    """Mechanically verify the artifact requirements we can verify from disk.

    Deliberately narrow: only claims about files and JSON fields are checked
    here. Anything needing judgement stays with the assessor, and is reported
    as `unchecked` rather than silently passed.
    """
    out = []
    results = run / "results.json"
    doc = None
    if results.is_file():
        try:
            doc = json.loads(results.read_text())
        except ValueError:
            doc = None
    for r in must_pass_requirements(task):
        rid = r.get("id", "?")
        status, detail = "unchecked", "needs assessor judgement"
        if rid == "req_results_json":
            if not isinstance(doc, dict):
                status, detail = "unmet", "results.json missing or not an object"
            else:
                need = ("primary_metric", "metric_key", "metrics", "hypotheses", "summary")
                missing = [k for k in need if k not in doc]
                hyp = doc.get("hypotheses") or {}
                bad_hyp = [h for h in ("h1", "h2", "h3")
                           if not isinstance(hyp.get(h), dict)
                           or not isinstance(hyp[h].get("supported"), bool)]
                if missing or bad_hyp:
                    status = "unmet"
                    detail = f"missing={missing} hypotheses_without_supported={bad_hyp}"
                else:
                    status, detail = "met", "all required keys present"
        elif rid == "req_hypotheses_supported_flags":
            hyp = (doc or {}).get("hypotheses") or {}
            bad = []
            for h in ("h1", "h2", "h3"):
                e = hyp.get(h)
                if not isinstance(e, dict) or not isinstance(e.get("supported"), bool):
                    bad.append(f"{h}:no_bool")
                elif len(str(e.get("details") or "")) < 40:
                    bad.append(f"{h}:details<40")
                elif not any(c.isdigit() for c in str(e.get("details") or "")):
                    bad.append(f"{h}:no_number_in_details")
            status = "unmet" if bad else "met"
            detail = ", ".join(bad) if bad else "flags + numeric details present"
        out.append({"id": rid, "status": status, "detail": detail,
                    "description": (r.get("description") or "")[:160]})
    return out


def score(run: Path, assessment: dict) -> dict:
    rub = load_rubric(run)
    ls = leaves(rub)
    total_w = sum(float(x.get("weight") or 0) for x in ls)
    rows, earned = [], 0.0
    for leaf in ls:
        lid = leaf["id"]
        a = assessment.get(lid) or {}
        v = str(a.get("verdict") or "unmet").lower()
        if v not in VERDICT_CREDIT:
            v = "unmet"
        w = float(leaf.get("weight") or 0)
        got = w * VERDICT_CREDIT[v]
        earned += got
        rows.append({"id": lid, "weight": w, "verdict": v, "earned": round(got, 4),
                     "category": leaf.get("task_category"),
                     "evidence": a.get("evidence", ""),
                     "requirement": (leaf.get("requirements") or "")[:200]})
    task = load_task(run)
    return {
        "run": run.name,
        "task_id": task.get("id"),
        "domain": task.get("domain"),
        "leaf_count": len(ls),
        "total_weight": round(total_w, 4),
        "earned_weight": round(earned, 4),
        "score_pct": round(100.0 * earned / total_w, 2) if total_w else None,
        "by_category": _by_category(rows),
        "must_pass": check_requirements(run, task),
        "leaves": rows,
    }


def _by_category(rows: list[dict]) -> dict:
    agg: dict[str, dict] = {}
    for r in rows:
        c = r.get("category") or "uncategorised"
        a = agg.setdefault(c, {"weight": 0.0, "earned": 0.0})
        a["weight"] += r["weight"]
        a["earned"] += r["earned"]
    for c, a in agg.items():
        a["pct"] = round(100.0 * a["earned"] / a["weight"], 2) if a["weight"] else None
        a["weight"] = round(a["weight"], 4)
        a["earned"] = round(a["earned"], 4)
    return agg


def template(run: Path) -> dict:
    return {leaf["id"]: {"verdict": "unmet", "evidence": ""}
            for leaf in leaves(load_rubric(run))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--assessment", type=Path, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--template", action="store_true",
                    help="print an assessment template to fill in")
    a = ap.parse_args(argv)
    run = a.run
    if a.template or not a.assessment:
        tpl = template(run)
        if a.template:
            print(json.dumps(tpl, indent=2, ensure_ascii=False))
            return 0
        print(f"{run.name}: {len(tpl)} rubric leaves")
        for leaf in leaves(load_rubric(run)):
            print(f"  {leaf['id']:<34} w={leaf.get('weight'):<8} "
                  f"{(leaf.get('requirements') or '')[:70]}")
        print("\nProvide --assessment <file> mapping leaf id -> "
              "{verdict: met|partial|unmet, evidence: str}")
        return 0
    assessment = json.loads(a.assessment.read_text())
    res = score(run, assessment)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    print(f"{res['run']} ({res['domain']}) — {res['score_pct']}% "
          f"({res['earned_weight']}/{res['total_weight']}, {res['leaf_count']} leaves)")
    for c, v in res["by_category"].items():
        print(f"  {c:<22} {v['pct']}%  ({v['earned']}/{v['weight']})")
    hard = res["must_pass"]
    if hard:
        print("  must_pass requirements:")
        for r in hard:
            print(f"    {r['id']:<34} {r['status']:<10} {r['detail'][:60]}")
    unmet = [r for r in res["leaves"] if r["verdict"] != "met"]
    if unmet:
        print("  not fully met:")
        for r in unmet:
            print(f"    {r['id']:<34} {r['verdict']:<8} w={r['weight']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())