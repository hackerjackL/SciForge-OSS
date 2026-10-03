"""Experience replay with vector search (S18) — stdlib embeddings, no torch.

LESSONS.json per run (contract existing since v1.4.0) now becomes QUERYABLE:
- embed: hashing-trick bag-of-words → L2-normalized dense vector (deterministic,
  stdlib, model-agnostic; if sentence-transformers is installed the kernel uses
  it automatically for real embeddings).
- index: cross-run archive directory → JSONL of {text, vec, meta, run_id}.
- query: top-k cosine — Phase 2 ideation priors and Phase 6b `avoid` exclusions
  consume real retrievable lessons, not "remember to read LESSONS.json".
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _hash_vec(text: str) -> list[float]:
    """Deterministic hashing-trick embedding (md5-based; stable across processes)."""
    v = [0.0] * DIM
    toks = _TOKEN.findall(text.lower())
    for t in toks:
        h = int(hashlib.md5(t.encode()).hexdigest()[:4], 16) % DIM
        v[h] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


_ST_MODEL = None


def embed(text: str) -> list[float]:
    global _ST_MODEL
    if _ST_MODEL is False:
        return _hash_vec(text)
    if _ST_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer  # optional upgrade
            _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _ST_MODEL = False
            return _hash_vec(text)
    emb = _ST_MODEL.encode(text).tolist()
    n = math.sqrt(sum(x * x for x in emb)) or 1.0
    return [x / n for x in emb]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def build_index(archive_dir: Path, out: Path) -> int:
    """Scan sibling runs' LESSONS.json; one entry per lesson with embedding."""
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w") as f:
        for run in sorted(Path(archive_dir).iterdir()):
            for cand in (run / "output" / "LESSONS.json", run / ".sciforge" / "verdicts" / "LESSONS.json"):
                if not cand.exists():
                    continue
                try:
                    d = json.loads(cand.read_text())
                except Exception:
                    continue
                for bucket in ("failed_experiments", "idea_rollbacks", "code_errors", "lessons", "what_worked", "verified_proofs"):
                    for item in d.get(bucket, []):
                        if isinstance(item, str):
                            text = item
                        else:
                            # v1.7.1: index the HUMAN-READABLE fields, not the
                            # raw JSON dump — artifact paths dominate the dump
                            # and drown the semantic signal (measured: top
                            # cosine 0.16 on a topic query against JSON noise).
                            keys = ("lesson", "error", "fix", "note", "reason",
                                    "avoid", "what", "why", "description", "text",
                                    "summary", "root_cause")
                            text = " | ".join(str(item[k]) for k in keys
                                              if item.get(k)) or \
                                   json.dumps(item, ensure_ascii=False)
                        if not text.strip():
                            continue
                        f.write(json.dumps({"text": text[:800], "vec": embed(text),
                                            "bucket": bucket, "run_id": d.get("run_id", run.name)}) + "\n")
                        n += 1
    return n


# ---------------------------------------------------------------------------
# Semantic layer (v1.7.2, D2): cross-run VERIFIED FACTS, not lessons.
# A lesson says "what went wrong"; a fact says "what is true about this
# world" (e.g. "on generator G the linear family ceiling is 0.645 full-split,
# measured by run X"). Facts are what make re-discovery cheap — the
# ResearchClawBench re-discovery-accuracy dimension scores exactly this.
# Source: CLAIMS_FROM_RESULTS.md polarity-positive claims + ladder fullset
# numbers, content-hashed so a fact can be traced to the run that measured it.
# ---------------------------------------------------------------------------
SEMANTIC_REL = Path("MEMORY_FACTS.jsonl")


def _fact_text(claim: dict) -> str:
    parts = [claim.get("claim", ""), claim.get("evidence", ""),
             claim.get("regime", "")]
    return " | ".join(p for p in parts if p)


def harvest_facts(ws: Path) -> list[dict]:
    """Extract verified facts from one finished run (polarity-positive claims
    + ladder fullset values), each carrying the run id and a content hash."""
    import hashlib
    ws = Path(ws)
    facts = []
    run_id = ws.name
    claims = ws / ".sciforge" / "audits" / "CLAIMS_FROM_RESULTS.md"
    if claims.exists():
        # real format: "## C1 — fidelity numerical — polarity positive (…) — to: …"
        # followed by the claim body until the next "## " header.
        text_all = claims.read_text(errors="replace")
        blocks = re.split(r"(?m)^## ", text_all)[1:]
        for blk in blocks:
            head = blk.splitlines()[0] if blk else ""
            m = re.match(r"(C\d+)", head.strip())
            if not m or "polarity positive" not in head:
                continue  # only verified positive findings become facts
            body = re.sub(r"\s+", " ", "\n".join(blk.splitlines()[1:])).strip()
            fact_text = f"{m.group(1)}: {body}"[:400]
            facts.append({"run_id": run_id, "kind": "claim",
                          "claim_id": m.group(1), "text": fact_text,
                          "hash": "sha256:" + hashlib.sha256(
                              fact_text.encode()).hexdigest()})
    ladder = ws / ".sciforge" / "audits" / "S2_LADDER.json"
    if ladder.exists():
        try:
            d = json.loads(ladder.read_text())
            fs = d.get("fullset") or {}
            text = (f"{d.get('problem_id')}: full-set baseline="
                    f"{(fs.get('baseline') or {}).get('value')} candidate="
                    f"{(fs.get('candidate') or {}).get('value')} "
                    f"gain={d.get('relative_gain_pct')}% state={d.get('critic', {}).get('state')}")
            facts.append({"run_id": run_id, "kind": "ladder", "text": text,
                          "hash": "sha256:" + hashlib.sha256(
                              text.encode()).hexdigest()})
        except Exception:
            pass
    return facts


def build_semantic_index(archive_dir: Path, out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w") as f:
        for run in sorted(Path(archive_dir).iterdir()):
            for fact in harvest_facts(run):
                fact["vec"] = embed(fact["text"])
                f.write(json.dumps(fact, ensure_ascii=False) + "\n")
                n += 1
    return n


def query_facts(index: Path, text: str, k: int = 6,
                min_sim: float = 0.12) -> list[dict]:
    if not Path(index).exists():
        return []
    q = embed(text)
    scored = []
    for line in Path(index).read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        s = cosine(q, e.get("vec", []))
        if s >= min_sim:
            scored.append({k2: v for k2, v in e.items() if k2 != "vec"}
                           | {"sim": round(s, 3)})
    scored.sort(key=lambda x: -x["sim"])
    return scored[:k]


def default_index_path() -> Path:
    """Cross-run lesson index location (v1.7.1 wiring): the runs archive root
    holds LESSONS.json per run; the index is built once per archive and
    consumed by phase-2 ideation priors and the sota hill-climb driver."""
    from pathlib import Path as _P
    import os as _os
    root = _P(_os.environ.get("SCIFORGE_RUNS_ARCHIVE",
                              str(_P(__file__).resolve().parents[2] / "runs")))
    return root / "LESSONS_INDEX.jsonl"


def query(index: Path, text: str, k: int = 8, min_sim: float = 0.12) -> list[dict]:
    """Top-k cosine hits. min_sim default 0.12 (v1.7.1): hashing-trick BoW over
    short lesson texts yields genuinely low cosines (0.1-0.3 for on-topic
    hits); a 0.3 floor returned nothing on real archives."""
    if not Path(index).exists():
        return []
    q = embed(text)
    scored = []
    with open(index) as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            s = cosine(q, e["vec"])
            if s >= min_sim:
                scored.append({**e, "sim": round(s, 3), "vec": None})
    scored.sort(key=lambda x: -x["sim"])
    return scored[:k]
