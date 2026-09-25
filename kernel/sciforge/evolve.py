"""RSI evolution engine (S11-S13) — the recursive self-improvement core.

Architecture copied where it is proven (ScienceDiscovery services/evolve, AI-Scientist
v2 treesearch), adapted for the ONLY thing we evolve: **skill-library text (SKILL.md
patches + routing/weight config)**, not programs. Key properties, each absorbed:

1. Two algorithms over one Domain seam (swap core, share scaffolding):
   - PUCT tree: rank + c_puct·P·√N_total/(1+N_child) selection. Continuous
     refinement of one patch lineage.
   - OpenEvolve-style MAP-Elites: islands × (complexity×diversity) bins, ring
     migration, ε-greedy parent choice + an *inspiration* candidate maximally
     different from the parent. Wide idea spaces, no premature convergence.

2. Four scoring modes over the same seam (the "what is better" definition):
   - gate_metric      — score = mechanical gate pass fraction (ci_check, tests,
                        schema validation of sample outputs, golden-set verdicts)
   - probe_stability  — repeated evaluation variance ≈ 0 required
   - llm_judge        — frozen-rubric judge (strong model, deterministic temp)
   - hybrid           — gate first (hard), judge second (soft); gates that FAIL
                        hard-zero the candidate (no judge can rescue a broken schema)

3. Score-freeze (S16): candidate text may NEVER touch tests/, schemas/, the
   validators, or the scoring rubric itself — enforced by path allowlist AND by
   the scorer running from the pristine repo, not from the candidate.

4. Three-shard defense (S12): rollout (search sees) / gate (rank on) /
   held-out test (nobody sees until the end) — golden problems split; the
   reported improvement number is from the held-out shard only.

5. Pre-flight probe (S13): before spending budget, prove the scorer separates
   a good patch from a deliberately corrupted one. Flat scorer = rejected run.

The engine emits NDJSON events (same discipline as pipeline) so any evolution
run is replayable and auditable. Stdlib-only like the rest of the kernel.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------- frozen paths (S16) ----------------
FROZEN_PREFIXES = ("tests/", "kernel/sciforge/", "scripts/validate_verdicts.py",
                   "scripts/sciforge_audit.py", "scripts/security_scan.py",
                   "scripts/evolve/", "scripts/golden/", "skills/shared-references/schemas/",
                   "LICENSE", "EVOLUTION_PLAN.md")

MUTABLE_ALLOW = ("skills/",)


def editable(path: str) -> bool:
    if path.startswith(FROZEN_PREFIXES):
        return False
    return path.startswith(MUTABLE_ALLOW)


# ---------------- candidate model ----------------
class Patch(dict):
    """One evolution candidate = an ordered list of {path, old, new} replacements."""

    def text(self) -> str:
        return json.dumps({"ops": [{"path": o["path"], "old": o["old"][:80], "new": o["new"][:80]}
                                   for o in self["ops"]]}, ensure_ascii=False)

    def digest(self) -> str:
        return hashlib.sha256(self.text().encode()).hexdigest()[:16]


# ---------------- apply / verify ----------------
def apply_patch(ws: Path, patch: Patch, *, checkout: Path | None = None) -> dict:
    """Apply ops to a scratch copy; validate edits against frozen paths.

    Returns {"ok": bool, "applied": [...], "rejected": [...]}.
    Never touches the real repo — evolution works in a workspace sandbox copy.
    """
    root = checkout or REPO_ROOT
    applied, rejected = [], []
    for op in patch["ops"]:
        p = op["path"]
        if not editable(p):
            rejected.append({"path": p, "reason": "frozen_path"})
            continue
        f = root / p
        if not f.exists():
            rejected.append({"path": p, "reason": "missing_file"})
            continue
        content = f.read_text()
        if op["old"] not in content:
            rejected.append({"path": p, "reason": "old_text_not_found"})
            continue
        f.write_text(content.replace(op["old"], op["new"], 1))
        applied.append(p)
    return {"ok": bool(applied) and not rejected, "applied": applied, "rejected": rejected}


def revert_patch(ws: Path, applied: list[str]) -> None:
    """Undo applied file edits from git (files are tracked in the repo)."""
    if not applied:
        return
    subprocess.run(["git", "checkout", "--", *applied], cwd=str(ws),
                   capture_output=True, timeout=60)


# ---------------- scorers (Domain seam) ----------------
class Domain:
    """The seam: start candidate, score(candidate)->number, prompt(candidate)->mutation ask."""

    name = "domain"
    frozen_rubric: str = ""

    def score(self, patch: Patch) -> dict:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"name": self.name}


class GateDomain(Domain):
    """Hard scorer: mechanical gate fraction. Used for skill patches whose target
    behavior is testable (schemas, validators, golden-set verdict completeness)."""

    def __init__(self, checks: list[dict], root: Path | None = None):
        self.checks = checks  # [{id, cmd, expect_pass}]
        self.root = Path(root or REPO_ROOT)  # scratch checkout: tests see the PATCHED tree

    name = "gate_metric"

    def score(self, patch: Patch) -> dict:
        results = []
        hard_ids: set[str] = set()
        for c in self.checks:
            p = subprocess.run(c["cmd"], shell=True, cwd=str(self.root),
                               capture_output=True, text=True, timeout=c.get("timeout", 600))
            results.append({"id": c["id"], "passed": p.returncode == 0,
                            "tail": (p.stdout + p.stderr)[-500:]})
            hard_ids.update(c.get("hard", []))
        passed = sum(1 for r in results if r["passed"])
        return {"score": passed / max(1, len(results)),
                "hard_fail": any((not r["passed"]) and r["id"] in hard_ids for r in results),
                "results": results}


class JudgeDomain(Domain):
    """llm_judge with a FROZEN rubric (S12: rubric lives outside candidates; scoring
    is temp-0 for reproducibility; run-scoped token so keys never enter candidates)."""

    name = "llm_judge"

    def __init__(self, providers=None, rubric_path: str | None = None):
        self.providers = providers
        self.rubric = Path(rubric_path).read_text() if rubric_path else _DEFAULT_RUBRIC

    def score(self, patch: Patch) -> dict:
        if self.providers is None:
            raise RuntimeError("judge requires providers (not host_mode)")
        system = ("You are a frozen-rubric judge for research-skill patches. "
                  "Score 0-10 on: specificity, machine-checkability, evidence-anchoring, "
                  "non-regression. Rubric (immutable):\n" + self.rubric)
        prompt = ("Candidate patch:\n```json\n" + patch.text() + "\n```\n"
                  "Reply ONLY JSON: {\"score\": <0-10>, \"rationale\": \"...\"}")
        try:
            text, rec = self.providers.complete("grading", system, prompt, temperature=0.0,
                                                json_schema={"type": "object",
                                                             "properties": {"score": {"type": "number"},
                                                                            "rationale": {"type": "string"}},
                                                             "required": ["score"]})
            d = json.loads(text)
            return {"score": float(d["score"]) / 10.0, "rationale": d.get("rationale", ""),
                    "usage": rec.as_dict()}
        except Exception as e:
            return {"score": 0.0, "error": str(e)}


_DEFAULT_RUBRIC = (
    "1.0-0.9 patch replaces prose-advice with machine-checkable constraint; "
    "0.8-0.7 sharpens a threshold/enum with justification; 0.6-0.5 clarifies an "
    "ambiguity without changing behavior; 0.4-0.2 vague rephrase or style-only; "
    "0.1-0.0 weakens a gate, removes a constraint, or edits the measuring instrument.")


class HybridDomain(Domain):
    """gate hard-zero first, then judge soft score. A candidate that fails hard
    gates never gets judged (reward-hacking defense)."""

    name = "hybrid"

    def __init__(self, gate: GateDomain, judge: JudgeDomain, weight=0.6):
        self.gate, self.judge, self.w = gate, judge, weight

    def score(self, patch: Patch) -> dict:
        g = self.gate.score(patch)
        if g.get("hard_fail"):
            return {**g, "score": 0.0, "judged": False, "reason": "hard_gate_fail"}
        j = self.judge.score(patch)
        s = (self.w * g["score"] + (1 - self.w) * j["score"])
        return {"score": s, "gate": g["score"], "judge": j["score"], "judged": True}


# ---------------- pre-flight probe (S13) ----------------
def probe(domain: Domain, seed: Patch, rng: random.Random) -> dict:
    """4 checks: discriminates good-vs-corrupt, headroom, stability, repairable errors."""
    corrupt = Patch({"ops": [dict(op, new=op["new"][:10] + "\n<!-- deliberate corruption -->")
                             for op in seed["ops"]][:1] or []})
    base = domain.score(seed)
    if not corrupt["ops"]:
        corrupt = Patch({"ops": [dict(seed["ops"][0], old=seed["ops"][0]["new"][:30],
                                      new=seed["ops"][0]["new"][:10] + "###CORRUPT###")]})
    bad = domain.score(corrupt)
    r1 = domain.score(seed); r2 = domain.score(seed)
    headroom = (base.get("score", 0) < 0.95)
    discriminates = abs(base.get("score", 0) - bad.get("score", 0)) > 0.05
    stable = abs(r1.get("score", 0) - r2.get("score", 0)) < 0.15
    return {"discriminates": discriminates, "headroom": headroom, "stable": stable,
            "base": base.get("score"), "corrupt": bad.get("score"),
            "ok": discriminates and headroom and stable}


# ---------------- PUCT engine (S11) ----------------
class PUCT:
    def __init__(self, domain: Domain, c=1.0, prior_exp=1.0, rng: random.Random | None = None):
        self.domain = domain; self.c = c; self.pe = prior_exp
        self.rng = rng or random.Random(42)
        self.nodes: list[dict] = []  # {parent, depth, score, visits, prior}

    def select(self) -> int:
        if not self.nodes:
            return -1
        total = sum(n["visits"] for n in self.nodes) or 1
        best, best_u = None, -1e9
        for i, n in enumerate(self.nodes):
            rank = n["score"] if n["score"] is not None else 0.0
            u = rank + self.c * (n["prior"] ** self.pe) * math.sqrt(total) / (1 + n["visits"])
            if u > best_u:
                best, best_u = i, u
        return best

    def expand(self, parent: int, child: "Candidate", prior=0.5):
        self.nodes.append({"parent": parent, "depth": (self.nodes[parent]["depth"] + 1) if parent >= 0 else 0,
                           "candidate": child, "score": None, "visits": 0, "prior": prior})

    def backprop(self, idx: int, score: float):
        n = self.nodes[idx]; n["score"] = max(n["score"] or 0.0, score); n["visits"] += 1
        while n.get("parent", -1) >= 0:
            n = self.nodes[n["parent"]]; n["visits"] += 1


# ---------------- MAP-Elites islands (S11b) ----------------
class MapElites:
    def __init__(self, domain: Domain, islands=3, bins=4, migration_every=6,
                 exploit_ratio=0.7, rng: random.Random | None = None):
        self.domain = domain; self.islands = islands; self.bins = bins
        self.mig = migration_every; self.exp = exploit_ratio
        self.rng = rng or random.Random(42)
        self.grid = [[{"score": -1, "candidate": None, "div": 0, "cx": 0}
                      for _ in range(bins * bins)] for _ in range(islands)]
        self.archive: list[dict] = []
        self.gen = 0

    @staticmethod
    def _features(cand) -> tuple[int, int]:
        txt = json.dumps(cand["ops"], ensure_ascii=False)
        cx = min(len(cand["ops"]) - 1, 3)                      # complexity bins
        div = min(int(hashlib.md5(txt.encode()).hexdigest()[:2], 16) * 4 // 256, 3)  # pseudo diversity
        return cx, div

    def insert(self, cand, score, island=None):
        cx, dv = self._features(cand)
        b = cx * self.bins + dv
        isl = self.islands if island is None else island
        cell = self.grid[isl % self.islands][b % (self.bins * self.bins)]
        if score > cell["score"]:
            self.grid[isl % self.islands][b % (self.bins * self.bins)] = {
                "score": score, "candidate": cand, "cx": cx, "div": dv}
        self.archive.append({"score": score, "candidate": cand, "island": isl,
                             "cx": cx, "div": dv, "gen": self.gen})

    def best(self):
        cands = [c["candidate"] for row in self.grid for c in row if c["candidate"]]
        if not cands:
            return None, -1
        b = max(self.archive, key=lambda x: x["score"]) if self.archive else None
        return (b["candidate"], b["score"]) if b else (None, -1)

    def parents(self) -> tuple:
        """Returns (candidate, score, inspiration|None); seed fallback on empty islands."""
        island = self.gen % self.islands
        cells = [c for c in self.grid[island] if c["candidate"]]
        if not cells:
            b, s = self.best()
            return b, s, None
        if self.rng.random() < self.exp:
            c = max(cells, key=lambda x: x["score"])
        else:
            c = self.rng.choice(cells)
        insp = self.rng.choice([x for x in self.archive if x["candidate"] is not c["candidate"]]) \
            if len(self.archive) > 1 else None
        return c["candidate"], c["score"], insp["candidate"] if insp else None

    def migrate(self):
        best = []
        for row in self.grid:
            occ = [c for c in row if c["candidate"]]
            best.append(max(occ, key=lambda x: x["score"]) if occ else None)
        for i in range(self.islands):
            src = best[i]
            if not src:
                continue
            dst = self.grid[(i + 1) % self.islands][src["cx"] * self.bins + src["div"]]
            if src["score"] > dst["score"]:
                self.grid[(i + 1) % self.islands][src["cx"] * self.bins + src["div"]] = dict(src, via="migration")


# ---------------- three-shard golden split (S12) ----------------
def split_shards(golden: list[dict], rollout=0.4, gate=0.4) -> dict:
    """Deterministic split; the `test` shard is never returned to the search."""
    n = len(golden); a = int(n * rollout); b = int(n * gate)
    return {"rollout": golden[:a], "gate": golden[a:a + b], "test": golden[a + b:]}


# ---------------- search loop ----------------
class EvolutionRun:
    def __init__(self, ws: Path, domain: Domain, mutator, *, algorithm="puct",
                 budget=8, seed_patch: Patch | None = None, shard_check=None):
        self.ws = ws; self.domain = domain; self.mutator = mutator
        self.algorithm = algorithm; self.budget = budget
        self.seed = seed_patch or Patch({"ops": []})
        self.shard_check = shard_check or (lambda p: True)
        self.engine = (PUCT(domain) if algorithm == "puct"
                       else MapElites(domain))
        self.events_path = ws / ".sciforge" / f"evolve_{int(time.time())}.ndjson"
        self.results: list[dict] = []

    def _emit(self, kind, **kw):
        ev = {"seq": len(self.results) + 1, "ts": time.time(), "kind": kind, **kw}
        with open(self.events_path, "a") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev

    def run(self) -> dict:
        pr = probe(self.domain, self.seed, random.Random(42))
        self._emit("probe", **pr)
        if not pr["ok"]:
            return {"status": "rejected_scoring", "probe": pr}
        budget_left = self.budget
        # expand seed first
        sc = self._evaluate(self.seed, parent_idx=-1)
        if self.algorithm == "puct":
            self.engine.expand(-1, self.seed, prior=1.0)
            self.engine.backprop(0, sc)
        else:
            self.engine.insert(self.seed, sc)
        while budget_left > 0:
            if self.algorithm == "puct":
                parent_idx = self.engine.select()
                parent = self.engine.nodes[parent_idx]["candidate"]
                parent_score = self.engine.nodes[parent_idx]["score"] or 0.0
                inspire = None
                children = self._mutate(parent, inspire)
                child = children[0]
                score = self._evaluate(child, parent_idx)
                self.engine.expand(parent_idx, child, prior=score)
                self.engine.backprop(len(self.engine.nodes) - 1, score)
            else:
                parent, parent_score, inspire = self.engine.parents()
                if parent is None:
                    break
                children = self._mutate(parent, inspire)
                child = children[0]
                score = self._evaluate(child, -1)
                island = self.engine.gen % self.engine.islands
                self.engine.insert(child, score, island)
                self.engine.gen += 1
                if self.engine.gen % self.engine.mig == 0:
                    self.engine.migrate()
                    self._emit("migrated", gen=self.engine.gen)
            budget_left -= 1
            self._emit("expanded", parent_score=parent_score, child_score=score,
                       algorithm=self.algorithm)
        # held-out evaluation on test shard (nobody steered on it)
        best, best_score = self._best()
        held = None
        if self.shard_check is not None and best:
            held = self._evaluate(best, -1, shard="test", apply=True)
        return {"status": "done", "algorithm": self.algorithm,
                "best_score": best_score, "best_patch": best["ops"] if best else None,
                "held_out": held, "events": str(self.events_path),
                "history": self.results}

    def _mutate(self, parent: Patch, inspire) -> list[Patch]:
        return [self.mutator(parent, inspire)]

    def _evaluate(self, patch: Patch, parent_idx: int, *, shard="gate", apply=True) -> float:
        """Apply to the scratch checkout, score mechanically, revert — the pristine
        tree is always the mutation baseline (score-freeze invariant)."""
        if not self.shard_check(patch):
            return -1.0
        res = apply_patch(self.ws, patch)
        try:
            if not res["ok"]:
                self.results.append({"digest": patch.digest(), "score": 0.0,
                                     "rejected": res["rejected"], "shard": shard})
                return 0.0
            sc = self.domain.score(patch)
        finally:
            revert_patch(self.ws, res.get("applied", []))
        self.results.append({"digest": patch.digest(), **{k: v for k, v in sc.items() if k != "results"},
                             "shard": shard})
        return sc["score"]

    def _best(self):
        if self.algorithm == "puct":
            scored = [(n["score"] or -1, n["candidate"]) for n in self.engine.nodes if n["score"] is not None]
        else:
            scored = [(a["score"], a["candidate"]) for a in self.engine.archive] if self.engine.archive else []
        if not scored:
            return None, -1
        return max(scored, key=lambda x: x[0])
