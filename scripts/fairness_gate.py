#!/usr/bin/env python3
"""Experiment fairness gate (S33/S54, mode=deepen) — experimental fairness is the
load-bearing property of a deepened paper.

v1.7.3 upgrade: the ledger used to be the ONLY input, so a run could PASS by
writing pretty numbers into methods/FAIRNESS_LEDGER.json without ever running
the claimed experiment. The three mechanically checkable claims are now
cross-validated against raw evidence on disk:

  * data split lock   — claimed split hashes must match a hash declared in
                        EVALUATION_PROTOCOL/RESULT/STATUS/events, a node
                        sha256 (`.sciforge/nodes/NODES.json`), or a real
                        data-split manifest under data/; a contradiction
                        (two declarations disagree) is FAIL, an unreconcilable
                        claim is WARN with a reason_code (never a silent PASS).
  * seed policy       — the claimed seed_count must be backed by that many
                        independent execution traces (STATUS/RESULT/per-seed
                        dirs/NODES/events); fewer traces = FAIL, no traces =
                        WARN (or FAIL when the claim exceeds the locked
                        EXPERIMENT_MATRIX seed list).
  * compute budget    — claimed per-method budgets are reconciled with
                        RUN_BUDGET.json wall-clock and per-run durations in
                        STATUS/RESULT files (time units), or at least their
                        parity is corroborated by observed per-method runtimes.

Scope rule (no false positives on non-experiment runs): cross-validation is
N/A for a "ledger-only" workspace (no EXPERIMENT_MATRIX, experiments/, NODES,
STATUS/RESULT, events) — e.g. a deepen audit whose raw run lives elsewhere.
A real run always has at least one of those artifacts, so the escape hatch is
narrow; theory-only runs still return SKIP because no ledger exists.

The six self-reported checks are retained unchanged (they remain the primary
contract); cross-validation can only add FAIL/WARN, never remove a failure.

Input: {workspace}/methods/FAIRNESS_LEDGER.json (produced by deepen-mode exec) or
{workspace}/methods/comparisons/*.json per table. Output: FAIRNESS.json (registered verdict).

Exit 0 = PASS/WARN (WARN allowed), 2 = FAIL, 3 = no ledger yet (SKIP).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

MIN_SEEDS = 3  # default (balanced+); lite tier allows >=2 (method-registry)
EFFORT_MIN = {"lite": 2, "balanced": 3, "max": 3, "beast": 3}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SEED_RE = re.compile(r"(?:^|[^a-z0-9])s(?:eed)?[-_]?(\d{1,4})(?:[^0-9]|$)", re.I)
DURATION_KEYS = ("duration_s", "duration_seconds", "execution_time_seconds",
                 "elapsed_seconds", "wall_seconds")
UNIT_SECONDS = {
    "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0,
    "m": 60.0, "min": 60.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hr": 3600.0, "hrs": 3600.0, "hour": 3600.0, "hours": 3600.0,
    "gpu-h": 3600.0, "gpu_h": 3600.0, "gpu-hours": 3600.0, "gpu_hours": 3600.0,
    "cpu-h": 3600.0, "cpu_h": 3600.0,
}
SPLIT_KEYS = ("split_hash_per_method", "split_hashes", "split_hash",
              "data_split_hash", "split_lock", "data_split_lock")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _load_json(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return None


def _load_jsonl(path: Path) -> list:
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        pass
    return out


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def _group_match(a, b) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    if a.startswith("group_"):
        a = a[6:]
    if b.startswith("group_"):
        b = b[6:]
    if a == b:
        return True
    # containment only for non-trivial names ("a" must not match everything)
    if len(a) >= 4 and len(b) >= 4:
        return a in b or b in a
    return False


def _int_seed(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


def _seeds_from_text(text: str) -> set[int]:
    return {int(m.group(1)) for m in SEED_RE.finditer(str(text))}


def _seed_ids(obj, _depth: int = 0) -> set[int]:
    """Explicit seed IDENTITIES (not counts) anywhere in a JSON value."""
    out: set[int] = set()
    if _depth > 8:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl == "seed":
                s = _int_seed(v)
                if s is not None:
                    out.add(s)
                elif isinstance(v, list):
                    out |= {x for x in (_int_seed(y) for y in v) if x is not None}
            elif kl in ("seeds", "seed_list", "seed_ids") and isinstance(v, list):
                out |= {x for x in (_int_seed(y) for y in v) if x is not None}
            else:
                out |= _seed_ids(v, _depth + 1)
    elif isinstance(obj, list):
        for x in obj:
            out |= _seed_ids(x, _depth + 1)
    return out


def _declared_seed_counts(obj, _depth: int = 0) -> set[int]:
    """seed_count / seeds_used style counts (corroboration only, never identity)."""
    out: set[int] = set()
    if _depth > 8:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("seeds_used", "seed_count", "n_seeds") and \
                    isinstance(v, int) and not isinstance(v, bool):
                out.add(v)
            else:
                out |= _declared_seed_counts(v, _depth + 1)
    elif isinstance(obj, list):
        for x in obj:
            out |= _declared_seed_counts(x, _depth + 1)
    return out


def _collect_split_strings(obj, _depth: int = 0) -> set[str]:
    """Strings held under keys whose name mentions a split (declarations)."""
    out: set[str] = set()
    if _depth > 8:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "split" in str(k).lower():
                if isinstance(v, str):
                    out.add(v)
                elif isinstance(v, (list, tuple)):
                    out |= {x for x in v if isinstance(x, str)}
                elif isinstance(v, dict):
                    out |= {x for x in v.values() if isinstance(x, str)}
            out |= _collect_split_strings(v, _depth + 1)
    elif isinstance(obj, list):
        for x in obj:
            out |= _collect_split_strings(x, _depth + 1)
    return out


def _norm_hash(v: str) -> str:
    s = str(v).strip().lower()
    if s.startswith("sha256:"):
        s = s[7:]
    return s


def _unit_seconds(unit: str) -> float | None:
    return UNIT_SECONDS.get(str(unit).strip().lower())


def _is_wall_clock_unit(unit: str) -> bool:
    """GPU/CPU-hours are aggregate device time and may legitimately exceed the
    run's wall clock (parallel workers); only plain wall-time units are
    comparable to RUN_BUDGET.wall_clock_seconds."""
    u = str(unit).strip().lower()
    return u in UNIT_SECONDS and "gpu" not in u and "cpu" not in u


def _parse_budget_value(v, default_unit: str):
    """Return (number, unit) or None. Numeric values inherit default_unit."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v), str(default_unit or "").strip().lower()
    s = str(v).strip()
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z_-]+)?$", s)
    if not m:
        return None
    return float(m.group(1)), (m.group(2) or default_unit or "").strip().lower()


# ---------------------------------------------------------------------------
# raw evidence collection
# ---------------------------------------------------------------------------
class Evidence:
    """Everything on disk that can contradict a fairness ledger."""

    def __init__(self, ws: Path, evidence_root: Path | str | None = None):
        self.ws = Path(ws)
        self.root = self.ws
        if evidence_root:
            root = Path(evidence_root)
            self.root = root if root.is_absolute() else (self.ws / root)
        vd = self.ws / ".sciforge" / "verdicts"
        self.matrix = _load_json(vd / "EXPERIMENT_MATRIX.json")
        self.protocol = _load_json(vd / "EVALUATION_PROTOCOL.json")
        self.run_budget = _load_json(vd / "RUN_BUDGET.json")
        self.nodes_doc = (_load_json(self.root / ".sciforge" / "nodes" / "NODES.json")
                          or _load_json(self.ws / ".sciforge" / "nodes" / "NODES.json")
                          or {})
        self.nodes = [n for n in (self.nodes_doc.get("nodes") or [])
                      if isinstance(n, dict)]
        self.results: list[dict] = []
        self.statuses: list[dict] = []
        self.smokes: list[dict] = []
        self.events: list[dict] = []
        self._declared_split: set[str] = set()
        self._artifact_hashes: set[str] = set()
        self._split_manifest_hashes: set[str] = set()
        self._collect()

    # ---- collection -----------------------------------------------------
    def _collect(self):
        root = self.root
        exp_roots = [root / "experiments", root / "src" / "experiments",
                     root / "code" / "experiments"]
        for exp in exp_roots:
            if not exp.is_dir():
                continue
            for p in sorted(exp.rglob("RESULT.json"))[:500]:
                d = _load_json(p)
                if isinstance(d, dict):
                    self.results.append({"kind": "result", "path": p, "data": d})
            for p in sorted(exp.rglob("STATUS.json"))[:500]:
                d = _load_json(p)
                if isinstance(d, dict):
                    self.statuses.append({"kind": "status", "path": p, "data": d})
            for p in sorted(exp.rglob("*.SMOKE.json"))[:500]:
                d = _load_json(p)
                if isinstance(d, dict):
                    self.smokes.append({"kind": "smoke", "path": p, "data": d})
        for logs in (root / "logs", root / ".sciforge" / "logs"):
            if not logs.is_dir():
                continue
            for p in sorted(logs.glob("*.STATUS.json"))[:1000]:
                d = _load_json(p)
                if isinstance(d, dict):
                    self.statuses.append({"kind": "status", "path": p, "data": d})
        ev = root / ".sciforge" / "events.ndjson"
        if ev.exists():
            self.events = _load_jsonl(ev)
        # declared split hashes from runtime declarations
        for doc in (self.protocol, self.run_budget):
            if doc:
                self._declared_split |= _collect_split_strings(doc)
        for rec in self.results + self.statuses + self.smokes:
            self._declared_split |= _collect_split_strings(rec["data"])
        for e in self.events:
            self._declared_split |= _collect_split_strings(e)
        self._declared_split = {_norm_hash(x) for x in self._declared_split
                                if SHA256_RE.match(_norm_hash(x))}
        # artifact hashes: node content hashes + real split-manifest files
        for n in self.nodes:
            for field in ("inputs_sha", "outputs_sha", "code_sha"):
                for sha in (n.get(field) or {}).values():
                    if isinstance(sha, str) and SHA256_RE.match(sha.lower()):
                        self._artifact_hashes.add(sha.lower())
        for base_name in ("data", "datasets", "dataset", "splits"):
            base = root / base_name
            if not base.is_dir():
                continue
            count = 0
            for p in sorted(base.rglob("*")):
                if count >= 200:
                    break
                if not p.is_file() or not re.search(r"split|fold|partition", p.name, re.I):
                    continue
                try:
                    if p.stat().st_size > 100 * 1024 * 1024:
                        continue
                    h = _sha256_file(p)
                    self._artifact_hashes.add(h)
                    self._split_manifest_hashes.add(h)
                    count += 1
                except OSError:
                    continue

    # ---- scope ----------------------------------------------------------
    def scope(self) -> str:
        if (self.matrix or self.nodes or self.results or self.statuses or
                self.smokes or self.events):
            return "run"
        exp = self.root / "experiments"
        if exp.is_dir():
            try:
                if any(exp.rglob("*")):
                    return "run"
            except OSError:
                pass
        rs = self.ws / ".sciforge" / "RUNSTATE.json"
        if rs.exists():
            return "run"
        if isinstance(self.run_budget, dict):
            phases = self.run_budget.get("per_phase")
            if isinstance(phases, dict) and ({"6b", "6c"} & set(phases)):
                return "run"
        return "ledger_only"

    # ---- groups / seeds -------------------------------------------------
    def matrix_groups(self) -> list[dict]:
        groups = (self.matrix or {}).get("groups") if isinstance(self.matrix, dict) else None
        return [g for g in (groups or []) if isinstance(g, dict)]

    def matched_group_keys(self, comp: dict) -> set[str]:
        keys = [comp.get("table_id", "")]
        methods = comp.get("methods")
        keys += methods if isinstance(methods, list) else []
        gpm = comp.get("group_per_method")
        if isinstance(gpm, dict):
            keys += list(gpm.values())
        matched = set()
        for g in self.matrix_groups():
            name = str(g.get("name", ""))
            if name and any(_group_match(k, name) for k in keys if k):
                matched.add(name)
        return matched

    @staticmethod
    def group_of_record(rec: dict) -> str:
        d = rec["data"]
        for k in ("group", "group_name", "experiment_group", "table_id"):
            v = d.get(k)
            if isinstance(v, str) and v:
                return v
        rid = d.get("run_id")
        if isinstance(rid, str) and rid:
            return re.split(r"_s\d+_|_r\d+_", rid)[0]
        return rec["path"].parent.name

    def record_matches(self, rec: dict, keys: set[str]) -> bool:
        if not keys:
            return True
        candidates = [self.group_of_record(rec), rec["path"].parent.name,
                      rec["path"].stem]
        return any(_group_match(c, k) for c in candidates for k in keys)

    def seed_evidence(self, comp: dict) -> dict:
        keys = self.matched_group_keys(comp)
        planned: set[int] = set()
        for g in self.matrix_groups():
            if keys and not any(_group_match(g.get("name", ""), k) for k in keys):
                continue
            for x in (g.get("seeds") or []):
                s = _int_seed(x)
                if s is not None:
                    planned.add(s)
        executed: set[int] = set()
        declared: set[int] = set()
        traces: set[str] = set()
        sources: Counter = Counter()
        if planned:
            sources["experiment_matrix"] = len(planned)
        for rec in self.statuses + self.results:
            if not self.record_matches(rec, keys):
                continue
            traces.add(str(rec["path"]))
            found = _seed_ids(rec["data"])
            found |= _seeds_from_text(rec["data"].get("run_id") or rec["path"].stem)
            found |= _seeds_from_text(rec["path"].parent.name)
            if found:
                executed |= found
                sources[rec["kind"]] += 1
            declared |= _declared_seed_counts(rec["data"])
        for n in self.nodes:
            blob = " ".join(
                [str(n.get("kind", "")), str(n.get("reexec_cmd", ""))]
                + list((n.get("inputs_sha") or {}).keys())
                + list((n.get("outputs_sha") or {}).keys()))
            if keys and not any(_group_match(blob, k) or
                                _group_match(n.get("kind", ""), k) for k in keys):
                continue
            traces.add("node:" + str(n.get("id")))
            found = _seeds_from_text(blob)
            if found:
                executed |= found
                sources["nodes"] += 1
        for e in self.events:
            blob = json.dumps(e, ensure_ascii=False)
            if keys and not any(_group_match(blob, k) for k in keys):
                continue
            found = _seed_ids(e) | _seeds_from_text(blob)
            if found:
                executed |= found
                sources["events"] += 1
        observed = len(executed)
        basis = "independent_seed_traces"
        if observed == 0 and declared:
            max_declared = max(declared)
            # one RESULT.json claiming seeds_used=N is a declaration, not N
            # traces: only accept it when N distinct run artifacts exist.
            if max_declared > 0 and len(traces) >= max_declared:
                observed = max_declared
                basis = "declared_counts_corroborated_by_traces"
        return {"planned": sorted(planned), "executed": sorted(executed),
                "declared_counts": sorted(declared), "traces": len(traces),
                "observed": observed, "basis": basis,
                "sources": dict(sources)}

    # ---- split ----------------------------------------------------------
    def split_claims(self, comp: dict) -> list[str]:
        vals: list[str] = []
        for key in SPLIT_KEYS:
            v = comp.get(key)
            if isinstance(v, str):
                vals.append(v)
            elif isinstance(v, dict):
                vals += [x for x in v.values() if isinstance(x, str)]
            elif isinstance(v, (list, tuple)):
                vals += [x for x in v if isinstance(x, str)]
        # nested evidence block produced by some hosts
        ev = comp.get("evidence")
        if isinstance(ev, dict):
            vals += [x for x in _collect_split_strings(ev)]
        return sorted({_norm_hash(v) for v in vals if v.strip()})

    def split_check(self, comp: dict) -> dict:
        claims = self.split_claims(comp)
        if not claims:
            return {"status": "N_A", "reason_codes": [], "claims": []}
        hex_claims = [c for c in claims if SHA256_RE.match(c)]
        nonhex = [c for c in claims if not SHA256_RE.match(c)]
        reasons: list[str] = []
        status = "PASS"
        if nonhex:
            reasons.append("split_lock_not_hash")
            status = "WARN"
        if hex_claims:
            if self._declared_split:
                if not all(c in self._declared_split for c in hex_claims):
                    reasons.append("split_hash_mismatch")
                    status = "FAIL"
            elif len(self._split_manifest_hashes) == 1:
                # exactly one real split manifest on disk: the claim must be
                # that file's sha256, otherwise the "frozen split" is fiction
                manifest = next(iter(self._split_manifest_hashes))
                if not all(c == manifest for c in hex_claims):
                    reasons.append("split_hash_mismatch")
                    status = "FAIL"
            elif self._artifact_hashes:
                if not all(c in self._artifact_hashes for c in hex_claims):
                    reasons.append("split_hash_unverifiable")
                    status = "WARN"
            else:
                reasons.append("split_hash_unverifiable")
                status = "WARN"
        return {"status": status, "reason_codes": reasons,
                "claims": claims,
                "declared_hashes": sorted(self._declared_split),
                "split_manifest_hashes": len(self._split_manifest_hashes),
                "artifact_hashes_checked": len(self._artifact_hashes)}

    # ---- budget ---------------------------------------------------------
    def method_duration_map(self, comp: dict) -> dict[str, list[float]]:
        keys = self.matched_group_keys(comp)
        gpm = comp.get("group_per_method")
        gpm = gpm if isinstance(gpm, dict) else {}
        declared_methods = comp.get("methods")
        methods = list(declared_methods) if isinstance(declared_methods, list) else []
        if not methods:
            methods = list((comp.get("budget_per_method") or {}).keys())
        out: dict[str, list[float]] = {}
        for m in methods:
            target = gpm.get(m)
            mkeys = {target} if target else {k for k in keys if _group_match(m, k)}
            if not mkeys and len(keys) == 1:
                # a single table maps to a single locked experiment group;
                # attribution to one arm is unknown, but the group's runtime
                # envelope still bounds every arm.
                mkeys = set(keys)
            if not mkeys and keys:
                continue  # cannot attribute this method to an experiment group
            ds: list[float] = []
            for rec in self.statuses + self.results:
                if mkeys:
                    if not any(_group_match(self.group_of_record(rec), k)
                               for k in mkeys):
                        continue
                elif keys and not self.record_matches(rec, keys):
                    continue
                for k in DURATION_KEYS:
                    v = rec["data"].get(k)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
                        ds.append(float(v))
                        break
            if ds:
                out[str(m)] = ds
        return out

    def budget_check(self, comp: dict, ledger_unit: str = "") -> dict:
        budgets = comp.get("budget_per_method")
        if not isinstance(budgets, dict) or not budgets:
            return {"status": "N_A", "reason_codes": [], "claims": {}}
        unit_default = str(comp.get("budget_unit") or ledger_unit or "")
        parsed: dict[str, tuple[float, str]] = {}
        reasons: list[str] = []
        status = "PASS"
        for m, v in budgets.items():
            p = _parse_budget_value(v, unit_default)
            if p is None:
                reasons.append("budget_unparseable")
                status = "WARN"
            else:
                parsed[str(m)] = p
        if not parsed:
            return {"status": status if reasons else "N_A", "reason_codes": reasons,
                    "claims": {}}
        units = {u for _, u in parsed.values() if u}
        time_like = bool(units) and all(_is_wall_clock_unit(u) for u in units)
        observed = self.method_duration_map(comp)
        evidence_used = False
        if time_like:
            claimed_s = {m: n * _unit_seconds(u) for m, (n, u) in parsed.items()}
            wall = None
            parallelism = 1.0
            if isinstance(self.run_budget, dict):
                wall = self.run_budget.get("wall_clock_seconds")
                p = self.run_budget.get("parallelism") or self.run_budget.get("devices")
                if isinstance(p, (int, float)) and not isinstance(p, bool) and p >= 1:
                    parallelism = float(p)
                elif isinstance(p, (list, tuple)) and p:
                    parallelism = float(len(p))
            if isinstance(wall, (int, float)) and not isinstance(wall, bool) and wall > 0:
                evidence_used = True
                # a wall-clock budget cannot exceed the whole run's elapsed
                # time times the number of parallel workers
                if max(claimed_s.values()) > float(wall) * parallelism + 60:
                    reasons.append("budget_exceeds_run_wallclock")
                    status = "FAIL"
            for m, sec in claimed_s.items():
                ds = observed.get(m)
                if ds:
                    evidence_used = True
                    # a run cannot take materially longer than its own budget
                    if sec + 60 < min(ds):
                        reasons.append("budget_claim_below_observed")
                        status = "FAIL"
        if len(observed) >= 2:
            evidence_used = True
            means = [sum(v) / len(v) for v in observed.values() if v]
            if len(means) >= 2 and min(means) > 30:
                if max(means) / max(1.0, min(means)) > 3:
                    reasons.append("budget_parity_contradicted")
                    status = "FAIL"
        if status == "PASS" and not evidence_used:
            # nothing on disk can contradict or corroborate the claimed budget
            reasons.append("budget_unverifiable")
            status = "WARN"
        return {"status": status, "reason_codes": sorted(set(reasons)),
                "claims": {m: {"value": n, "unit": u} for m, (n, u) in parsed.items()},
                "observed_durations": observed}


# ---------------------------------------------------------------------------
# ledger checks (self-reported fields, unchanged contract)
# ---------------------------------------------------------------------------
def load_ledger(ws: Path) -> tuple[list[dict], dict]:
    ledger = Path(ws) / "methods" / "FAIRNESS_LEDGER.json"
    if ledger.exists():
        d = _load_json(ledger)
        if isinstance(d, list):
            return [c for c in d if isinstance(c, dict)], {}
        if isinstance(d, dict):
            comps = d.get("comparisons")
            if isinstance(comps, list):
                return [c for c in comps if isinstance(c, dict)], \
                    {k: v for k, v in d.items() if k != "comparisons"}
            return [], {}
        return [], {}
    cdir = Path(ws) / "methods" / "comparisons"
    out: list[dict] = []
    if cdir.is_dir():
        for f in sorted(cdir.glob("*.json")):
            d = _load_json(f)
            if isinstance(d, dict):
                out.append(d)
            elif isinstance(d, list):
                out += [c for c in d if isinstance(c, dict)]
    return out, {}


def load_comparisons(ws: Path) -> list[dict]:
    return load_ledger(ws)[0]


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


# ---------------------------------------------------------------------------
# cross-validation driver
# ---------------------------------------------------------------------------
def crossvalidate_comparison(comp: dict, ev: Evidence, scope: str,
                             ledger_unit: str = "") -> dict:
    if scope != "run":
        return {"scope": scope, "status": "N_A",
                "reason_codes": ["ledger_only_no_raw_evidence"],
                "split": {"status": "N_A", "reason_codes": []},
                "seeds": {"status": "N_A", "reason_codes": []},
                "budget": {"status": "N_A", "reason_codes": []}}
    split = ev.split_check(comp)
    seeds_ev = ev.seed_evidence(comp)
    claim = _int_seed(comp.get("seed_count")) or 0
    seed_reasons: list[str] = []
    if claim <= 0:
        seed_status = "N_A"  # the self-report check already FAILs this
    elif seeds_ev["observed"] >= claim:
        seed_status = "PASS"
    elif seeds_ev["observed"] > 0:
        seed_status = "FAIL"
        seed_reasons.append("seed_count_unsupported")
    elif seeds_ev["planned"] and claim > len(seeds_ev["planned"]):
        seed_status = "FAIL"
        seed_reasons.append("seed_count_exceeds_planned_matrix")
    else:
        seed_status = "WARN"
        seed_reasons.append("seed_evidence_missing")
    # optional per-method seed counts
    per_method = comp.get("seed_count_per_method")
    if isinstance(per_method, dict):
        for m, v in per_method.items():
            n = _int_seed(v)
            if n is not None and n > seeds_ev["observed"] and seeds_ev["observed"] > 0:
                seed_status = "FAIL"
                seed_reasons.append("seed_count_per_method_unsupported")
                break
    budget = ev.budget_check(comp, ledger_unit=ledger_unit)
    axes = [split, {"status": seed_status, "reason_codes": seed_reasons}, budget]
    statuses = [a.get("status", "N_A") for a in axes]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "WARN" in statuses:
        overall = "WARN"
    elif "PASS" in statuses:
        overall = "PASS"
    else:
        overall = "N_A"
    reasons = sorted({r for a in axes for r in a.get("reason_codes", [])})
    return {"scope": scope, "status": overall, "reason_codes": reasons,
            "split": split, "seeds": {"status": seed_status, "reason_codes": seed_reasons,
                                      **seeds_ev},
            "budget": budget}


def _cv_verdict(cvs: list[dict]) -> str:
    statuses = [c.get("status", "N_A") for c in cvs]
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    if "PASS" in statuses:
        return "PASS"
    return "N_A"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    ap.add_argument("--min-seeds", type=int, default=None,
                    help="override; default = effort-aware (lite>=2, others>=3)")
    args = ap.parse_args(argv)
    ws = args.workspace
    comps, meta = load_ledger(ws)
    if not comps:
        print("fairness_gate: no FAIRNESS_LEDGER.json / methods/comparisons/*.json — SKIP")
        return 3
    min_seeds = args.min_seeds or EFFORT_MIN.get(os.environ.get("SCIFORGE_EFFORT", "lite"), MIN_SEEDS)
    ev = Evidence(ws, evidence_root=meta.get("evidence_root"))
    scope = ev.scope()
    ledger_unit = str(meta.get("budget_unit") or "")
    results = [check_comparison(c, min_seeds) for c in comps]
    cvs = [crossvalidate_comparison(c, ev, scope, ledger_unit) for c in comps]
    hard_fails = [r for r in results if r["problems"] and not r["warn_only"]]
    warns = [r for r in results if r["warn_only"]]
    cv = _cv_verdict(cvs)
    verdict = "FAIL" if (hard_fails or cv == "FAIL") else \
              ("WARN" if (warns or cv == "WARN") else "PASS")
    cv_notes = [f"{cv_res['table_id']}: crossvalidation {cv_doc['status']} "
                f"({', '.join(cv_doc['reason_codes']) or 'clean'})"
                for cv_res, cv_doc in zip(results, cvs)]
    out = {
        "gate": "experiment-fairness", "version": "v1.7.3-cv",
        "verdict": verdict,
        "checks": {
            "compute_budget_parity": "FAIL" if any("budget asymmetry" in p for r in results for p in r["problems"]) else "PASS",
            "data_split_lock": "FAIL" if any("split not locked" in p for r in results for p in r["problems"]) else "PASS",
            "seed_policy": "FAIL" if any("seed_count" in p for r in results for p in r["problems"]) else "PASS",
            "hparam_budget_parity": "FAIL" if any("hparam" in p for r in results for p in r["problems"]) else "PASS",
            "metric_definitions": "FAIL" if any("metric definitions" in p for r in results for p in r["problems"]) else "PASS",
            "evidence_crossvalidation": cv,
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
            "crossvalidation": cv_doc,
        } for r, cv_doc in zip(results, cvs)],
        "evidence_crossvalidation": {
            "scope": scope,
            "verdict": cv,
            "reason_codes": sorted({x for c in cvs for x in c.get("reason_codes", [])}),
            "evidence_sources": {
                "experiment_matrix": bool(ev.matrix),
                "evaluation_protocol": bool(ev.protocol),
                "run_budget": bool(ev.run_budget),
                "nodes": len(ev.nodes),
                "results": len(ev.results),
                "statuses": len(ev.statuses),
                "events": len(ev.events),
                "declared_split_hashes": len(ev._declared_split),
                "artifact_hashes": len(ev._artifact_hashes),
            },
        },
        "numbers_stale": False,
        "unfair_notes": [f"{r['table_id']}: {'; '.join(r['problems'])}" for r in results if r["problems"]]
                        + [n for n in cv_notes if "clean" not in n],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    print(json.dumps({"verdict": verdict,
                      "fail_tables": [r["table_id"] for r in hard_fails],
                      "warn_tables": [r["table_id"] for r in warns],
                      "crossvalidation_fail_tables":
                          [r["table_id"] for r, c in zip(results, cvs)
                           if c["status"] == "FAIL"],
                      "crossvalidation_warn_tables":
                          [r["table_id"] for r, c in zip(results, cvs)
                           if c["status"] == "WARN"],
                      "evidence_crossvalidation": out["evidence_crossvalidation"]},
                     indent=2))
    if args.write_verdict:
        vp = ws / ".sciforge" / "verdicts"
        vp.mkdir(parents=True, exist_ok=True)
        (vp / "FAIRNESS.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        (ws / "methods").mkdir(exist_ok=True)
        (ws / "methods" / "FAIRNESS.md").write_text(
            "# Experiment Fairness Audit\n\n"
            + "\n".join(f"- **{r['table_id']}**: " + ("clean" if not r["problems"] else "; ".join(r["problems"]))
                        for r in results)
            + "\n\n## Evidence cross-validation\n\n"
            + f"- scope: `{scope}`; verdict: **{cv}**\n"
            + "\n".join(f"- **{cv_res['table_id']}**: {cv_doc['status']} — "
                        + (", ".join(cv_doc["reason_codes"]) or "all claims reconciled")
                        for cv_res, cv_doc in zip(results, cvs)) + "\n")
    return 0 if verdict in ("PASS", "WARN") else 2


if __name__ == "__main__":
    sys.exit(main())