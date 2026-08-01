#!/usr/bin/env python3
"""SciForge-OSS failed-ideas memory — P1 anti-repetition mechanism (zero paid API).

Persists killed/falsified ideas to `refine-logs/failed_ideas.json`, provides:

1. HARD CHECK (0 LLM cost): TF-IDF + cosine similarity (pure stdlib) against the
   failed-ideas corpus. Similarity > 0.78 -> idea is REJECTED (duplicate of a
   known-failed idea).
2. SOFT PROMPT INJECTION: emits the top-N most similar historically-killed ideas
   with their lessons-learned, to be injected into the MCTS generation prompt.

Usage (CLI):
    python3 scripts/idea/failed_ideas_memory.py add <id> <description> <reason>
    python3 scripts/idea/failed_ideas_memory.py check "<description>"   # -> verdict
    python3 scripts/idea/failed_ideas_memory.py prompt <n>              # -> injection text
    python3 scripts/idea/failed_ideas_memory.py list

Pure-Python TF-IDF: tokenize lowercase word tokens, IDF with smoothing,
L2-normalized vectors, cosine similarity. No sklearn / numpy required.
"""
import json
import math
import os
import re
import sys

DEFAULT_CORPUS = os.path.join("refine-logs", "failed_ideas.json")
SIM_THRESHOLD = 0.78   # hard-reject threshold (task spec)
TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")


# --------------------------------------------------------------------------- #
# tokenize + tf-idf (pure stdlib)
# --------------------------------------------------------------------------- #
def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _idf(corpus_docs: list[list[str]]) -> dict[str, float]:
    n = len(corpus_docs)
    df: dict[str, int] = {}
    for doc in corpus_docs:
        for t in set(doc):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}


def _tfidf_vec(doc: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf: dict[str, float] = {}
    for t in doc:
        tf[t] = tf.get(t, 0.0) + 1.0
    v = {t: (cnt / max(len(doc), 1)) * idf.get(t, 1.0) for t, cnt in tf.items()}
    norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
    return {t: x / norm for t, x in v.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    return sum(a[k] * b[k] for k in keys)


# --------------------------------------------------------------------------- #
# corpus I/O
# --------------------------------------------------------------------------- #
def _load(corpus_path: str) -> list[dict]:
    if not os.path.exists(corpus_path):
        return []
    try:
        with open(corpus_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict], corpus_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(corpus_path)), exist_ok=True)
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def add_idea(idea_id: str, description: str, reason: str,
             corpus_path: str = DEFAULT_CORPUS) -> dict:
    entries = _load(corpus_path)
    entries = [e for e in entries if e.get("id") != idea_id]
    entries.append({
        "id": idea_id,
        "description": description,
        "reason": reason,
        "ts": None,
    })
    _save(entries, corpus_path)
    return {"added": idea_id, "corpus_size": len(entries)}


def check_idea(description: str, corpus_path: str = DEFAULT_CORPUS,
               threshold: float = SIM_THRESHOLD) -> dict:
    """Hard check: similarity to the most-similar failed idea.

    Returns {verdict: REJECT|PASS, similarity, matched_id, matched_reason}.
    REJECT when similarity > threshold (idea duplicates a known-failed idea).
    """
    entries = _load(corpus_path)
    if not entries:
        return {"verdict": "PASS", "similarity": 0.0, "matched_id": None,
                "matched_reason": None, "corpus_size": 0}
    docs = [_tokens(e["description"]) for e in entries]
    idf = _idf(docs)
    q = _tfidf_vec(_tokens(description), idf)
    best = 0.0
    best_i = -1
    for i, d in enumerate(docs):
        s = _cosine(q, _tfidf_vec(d, idf))
        if s > best:
            best, best_i = s, i
    if best > threshold:
        return {"verdict": "REJECT", "similarity": round(best, 4),
                "matched_id": entries[best_i]["id"],
                "matched_reason": entries[best_i].get("reason"),
                "corpus_size": len(entries)}
    return {"verdict": "PASS", "similarity": round(best, 4),
            "matched_id": entries[best_i]["id"] if best_i >= 0 else None,
            "matched_reason": entries[best_i].get("reason") if best_i >= 0 else None,
            "corpus_size": len(entries)}


def prompt_injection(description: str, n: int = 5,
                     corpus_path: str = DEFAULT_CORPUS) -> str:
    """Soft prompt injection: top-N most similar killed ideas + lessons."""
    entries = _load(corpus_path)
    if not entries:
        return "[failed-ideas: empty corpus]"
    docs = [_tokens(e["description"]) for e in entries]
    idf = _idf(docs)
    q = _tfidf_vec(_tokens(description), idf)
    scored = sorted(
        ((_cosine(q, _tfidf_vec(d, idf)), e) for d, e in zip(docs, entries)),
        key=lambda x: x[0], reverse=True,
    )[:n]
    lines = ["[failed-ideas prompt injection] avoid regenerating these killed ideas:"]
    for sim, e in scored:
        lines.append(f"- [{e['id']}] sim={sim:.2f}: {e['description'][:120]}"
                     f" | reason: {e.get('reason', '')[:120]}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 0
    cmd = argv[1]
    corpus = os.environ.get("FAILED_IDEAS_CORPUS", DEFAULT_CORPUS)
    if cmd == "add" and len(argv) >= 5:
        print(json.dumps(add_idea(argv[2], argv[3], argv[4], corpus), ensure_ascii=False))
        return 0
    if cmd == "check" and len(argv) >= 3:
        print(json.dumps(check_idea(argv[2], corpus), ensure_ascii=False))
        return 0
    if cmd == "prompt":
        n = int(argv[2]) if len(argv) >= 3 else 5
        desc = argv[3] if len(argv) >= 4 else ""
        print(prompt_injection(desc, n, corpus))
        return 0
    if cmd == "list":
        print(json.dumps(_load(corpus), ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
