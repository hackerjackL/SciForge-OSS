#!/usr/bin/env python3
"""Verify the manuscript's universal claims against the artifacts (CLAIM_WITNESS).

Why this exists: three ARC-Bench runs shipped manuscripts whose machine-readable
artifacts were exact and whose PROSE was wrong. Not fabricated -- overclaimed.
ML18 asserted "the standard deviation over replicates never exceeds a third of
the pooled gap in any cell" when 11 of 36 exceed it; "the ordering of the four
conditions is unchanged across the whole range" when its own Table 5 shows them
swapping. Q07 asserted "every trained model covers all ten classes" while its
own appendix records 9. B01 attributed the #1 knockout's effect to a route that
its own isozyme analysis records as carrying flux. Every one of those sentences
sits in a run whose results.json is correct.

No grep can catch this: the claims are number-free relational assertions ("never
exceeds a third", "negative at every size", "unchanged across the range"), the
numbers live in LaTeX macros, and a regex over "all/every/never" has ~25%
precision -- it fires on design statements ("every condition is evaluated on
identical splits") that are true by construction.

So the gate does not judge the prose. It enumerates the candidate sentences
(recall is the gate's job) and requires the host to register a WITNESS for each
one, then re-derives that witness mechanically from the artifact. The design
rests on one observation: an agent that writes a false universal does not know
it is false, so it registers the claim honestly with expected=true -- and the
re-derivation refutes it. The failure mode this closes is an honest mistake,
which is the only kind that reaches a compiled PDF.

Verdict:
  FAIL  a registered empirical witness whose re-derivation disagrees with what
        the host declared -- the claim is false on the host's own evidence
  WARN  candidate sentences with no registered witness (disclosed, counted).
        A claim nobody registered is unverifiable, not false; failing it would
        punish a run for the gate's own recall.
  PASS  every candidate registered and every empirical witness verifies

Witness entry:
  {"sha256": "<sha256 of the normalised sentence>",
   "kind": "empirical" | "protocol",
   "artifact": "results/analysis.json",   # empirical only
   "field": "cells[*].delta",             # dotted path; may end in [*]
   "check": "all_negative",               # see CHECKS
   "expected": true,
   "note": "why this sentence is/is not empirical"}

Usage:
  python scripts/claim_witness.py <workspace> [--write-verdict] [--json]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

# A universal / absolute assertion. Recall matters more than precision here:
# the gate only uses these as a checklist, and the verdict comes from the
# witness re-derivation, not from this match.
QUANTIFIER = re.compile(
    r"\b(?:never|always|every|each|all|none|no \w+|at most|at least|exactly|"
    r"unchanged|identical|uniformly|monoton(?:ic|ically)|across the whole|"
    r"throughout|in every|in all|for all|only)\b", re.I)
# ...about a measured relation, which is what separates an empirical claim from
# a protocol statement.
RELATION = re.compile(
    r"\b(?:exceed\w*|below|above|under|negative|positive|greater|less|higher|"
    r"lower|unchanged|identical|constant|stable|monoton\w*|within|outside|"
    r"ties?|match\w*|equals?|reach\w*|falls?|rises?|reduc\w+|improv\w+|"
    r"defici\w+|cover\w*|contain\w*|includ\w+|span\w*|attain\w*|achiev\w+|"
    r"remain\w*|stay\w*|hold\w*|differ\w*|separat\w+|domin\w+|beat\w*|"
    r"win\w*|los[et]\w*|collaps\w+|survive\w+|degrad\w+|scal\w+)\b", re.I)
# Empirical claims live in the results/discussion/conclusion, never in the
# method -- "every condition is evaluated on identical splits" is a protocol
# statement and belongs to the code, not to a witness.
EMPIRICAL_SECTION = re.compile(r"^(?:[0-9]+_)?(?:results|discussion|conclusion)", re.I)
GENERATED = re.compile(r"^(?:tab|numbers)\b", re.I)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _prose(ws: Path) -> list[tuple[str, str]]:
    """(file, sentence) for every sentence in the empirical sections."""
    out = []
    for tex in sorted((ws / "paper" / "sections").glob("*.tex")):
        if GENERATED.match(tex.name) or not EMPIRICAL_SECTION.match(tex.name):
            continue
        text = tex.read_text(errors="replace")
        # Strip \command{arg} and $math$ so the matcher sees prose, not macros.
        # The numbers live in the macros, which is exactly why no grep can
        # judge these claims -- but the QUANTIFIER and RELATION words do not.
        text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", text)
        text = re.sub(r"\$[^$]*\$", " ", text)
        for raw in _SENT_SPLIT.split(text):
            s = " ".join(raw.split())
            if len(s) < 30:
                continue
            if QUANTIFIER.search(s) and RELATION.search(s):
                out.append((tex.name, s))
    return out


def _sha(sentence: str) -> str:
    return hashlib.sha256(sentence.encode("utf-8")).hexdigest()


def _fan(sub):
    """A wildcard's result, flattened one level: a dict contributes its values,
    a list contributes its elements, anything else is a single value."""
    if isinstance(sub, dict):
        return list(sub.values())
    if isinstance(sub, list):
        return list(sub)
    return [sub]


def _select(container, name: str, sel: str | None):
    """Pick `name` out of `container`, applying `sel`.

    `sel` is None (plain key), "*" (fan out: a dict's values or a list's
    elements), or "<prefix>*" (dict entries whose key starts with <prefix>).
    """
    if not isinstance(container, dict) or name not in container:
        return None
    value = container[name]
    if sel is None:
        return value
    if sel == "*":
        return list(value.values()) if isinstance(value, dict) else (
            list(value) if isinstance(value, list) else None)
    if sel.endswith("*"):
        if not isinstance(value, dict):
            return None
        prefix = sel[:-1]
        return [value[k] for k in value if k.startswith(prefix)]
    return None


_PART = re.compile(r"^([^\[\]]*)(?:\[([^\]]*)\])?$")


def _parse_part(part: str) -> tuple[str, str | None]:
    """`cells[*]` -> ("cells", "*"); `binning_table[platt__*]` ->
    ("binning_table", "platt__*"); `ece_std` -> ("ece_std", None)."""
    m = _PART.match(part)
    if not m:
        return part, None
    return m.group(1), m.group(2)


def _resolve(doc, dotted: str):
    """Walk a dotted path.

    Selectors:
      none        a plain key
      *           fan out across a level (a dict's values, a list's elements)
      <prefix>*   entries of a dict whose key starts with <prefix>

    Real artifacts need all three. metrics.json has `cells` as a dict keyed by
    dataset__classifier whose values hold a `conditions` dict keyed by condition
    name, so `cells[*].conditions[*].ece_std` fans out twice and then maps a
    plain key. Its `binning_table` flattens two dimensions into one key
    (`condition__b<bins>`), so "Platt at every bin count" is
    `binning_table[platt__*]`. Prefix selection preserves document key order, so
    two selections over the same table correspond element-wise.
    """
    cur = doc
    for part in dotted.split("."):
        name, sel = _parse_part(part)
        if not name:
            return None
        if isinstance(cur, list):
            out = []
            for item in cur:
                if not isinstance(item, dict):
                    return None
                picked = _select(item, name, sel)
                if picked is None:
                    return None
                out += _fan(picked)
            cur = out
            continue
        picked = _select(cur, name, sel) if isinstance(cur, dict) else None
        if picked is None:
            return None
        cur = _fan(picked)
    return cur


def _flatten(value):
    if isinstance(value, list):
        out = []
        for v in value:
            out += _flatten(v)
        return out
    return [value]


def _numbers(value) -> list[float]:
    out = []
    for v in _flatten(value):
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out.append(float(v))
        elif isinstance(v, str):
            try:
                out.append(float(v))
            except ValueError:
                pass
    return out


def _derive(check: str, values: list[float], expected,
            values_b: list[float] | None = None) -> bool | None:
    """Re-derive `check` from `values`. None = check not understood.

    `values_b` is the second operand for the two-field checks, collected in the
    same order as `values` so element i of one corresponds to element i of the
    other -- which is what "the ordering of A against B is unchanged" and "the
    standard deviation never exceeds a third of the gap" actually assert.
    """
    if not values:
        return None
    if check in ("all_le_ratio", "all_ge_ratio", "all_lt_ratio") and values_b:
        if len(values_b) != len(values):
            return None
        pairs = list(zip(values, values_b))
        if check == "all_le_ratio":
            return all(a <= float(expected) * b for a, b in pairs)
        if check == "all_ge_ratio":
            return all(a >= float(expected) * b for a, b in pairs)
        return all(a < float(expected) * b for a, b in pairs)
    if check.startswith("diff_") and values_b:
        if len(values_b) != len(values):
            return None
        values = [a - b for a, b in zip(values, values_b)]
        check = check[len("diff_"):]
    n = len(values)
    if check == "all_negative":
        return all(v < 0 for v in values)
    if check == "all_nonnegative":
        return all(v >= 0 for v in values)
    if check == "all_positive":
        return all(v > 0 for v in values)
    if check == "all_zero":
        return all(v == 0 for v in values)
    if check == "constant":
        return max(values) - min(values) == 0
    if check == "monotone_increasing":
        return all(b >= a for a, b in zip(values, values[1:]))
    if check == "monotone_decreasing":
        return all(b <= a for a, b in zip(values, values[1:]))
    if check == "min_ge":
        return min(values) >= float(expected)
    if check == "max_le":
        return max(values) <= float(expected)
    if check == "min_gt":
        return min(values) > float(expected)
    if check == "max_lt":
        return max(values) < float(expected)
    if check == "count_negative":
        return sum(1 for v in values if v < 0) == int(expected)
    if check == "count_positive":
        return sum(1 for v in values if v > 0) == int(expected)
    if check == "count_zero":
        return sum(1 for v in values if v == 0) == int(expected)
    if check == "count_ge":
        thr = float(expected[0]) if isinstance(expected, (list, tuple)) else None
        return thr is not None and sum(1 for v in values if v >= thr) == int(
            expected[1] if isinstance(expected, (list, tuple)) else expected)
    if check == "count_le":
        thr = float(expected[0]) if isinstance(expected, (list, tuple)) else None
        return thr is not None and sum(1 for v in values if v <= thr) == int(
            expected[1] if isinstance(expected, (list, tuple)) else expected)
    return None


def _artifacts(ws: Path, rel: str) -> list[Path]:
    """Resolve a witness `artifact`, which may be a glob.

    A claim like "every trained model covers all ten classes" spans one
    RESULT.json per group, so the witness has to name the set rather than pick a
    file -- picking one would let the false group escape unregistered.
    """
    target = ws / str(rel)
    if target.is_file():
        return [target]
    hits = sorted(p for p in ws.glob(str(rel)) if p.is_file())
    return hits


def _load_artifact(ws: Path, rel: str, field: str):
    """Numbers for `field` across every artifact `rel` names, or (None, why)."""
    docs = []
    for path in _artifacts(ws, rel):
        try:
            docs.append(json.loads(path.read_text()))
        except ValueError as exc:
            return None, f"artifact {path.relative_to(ws)} is not valid JSON ({exc})"
    if not docs:
        return None, f"artifact {rel!r} matches no file under the workspace"
    values: list[float] = []
    for doc in docs:
        got = _numbers(_resolve(doc, field))
        if not got:
            return None, (f"field {field!r} resolves to no numbers in "
                          f"{rel} ({len(docs)} artifact(s) matched)")
        values += got
    return values, None


def check(ws: Path) -> dict:
    ws = Path(ws)
    candidates = _prose(ws)
    vdir = ws / ".sciforge" / "verdicts"
    wit_path = vdir / "CLAIM_WITNESS.json"
    witnesses = []
    if wit_path.is_file():
        try:
            doc = json.loads(wit_path.read_text())
        except ValueError:
            doc = None
        if isinstance(doc, dict):
            witnesses = doc.get("witnesses") or []
        elif isinstance(doc, list):
            witnesses = doc

    by_sha = {}
    for w in witnesses:
        if isinstance(w, dict) and isinstance(w.get("sha256"), str):
            by_sha[w["sha256"]] = w

    verified = refuted = unregistered = protocol = unknown_check = 0
    failures: list[str] = []
    rows = []
    for fname, sentence in candidates:
        h = _sha(sentence)
        w = by_sha.get(h)
        if w is None:
            unregistered += 1
            rows.append({"file": fname, "sha256": h, "status": "unregistered",
                         "sentence": sentence[:160]})
            continue
        kind = w.get("kind")
        if kind == "protocol":
            protocol += 1
            rows.append({"file": fname, "sha256": h, "status": "protocol",
                         "sentence": sentence[:160]})
            continue
        if kind != "empirical":
            unknown_check += 1
            failures.append(f"{fname}: witness kind {kind!r} is not empirical|protocol")
            continue
        rel = w.get("artifact")
        field = w.get("field")
        chk = w.get("check")
        expected = w.get("expected")
        if not rel or not field:
            failures.append(f"{fname}: empirical witness needs both artifact and field")
            continue
        values, why = _load_artifact(ws, str(rel), str(field))
        if values is None:
            failures.append(f"{fname}: {why}")
            continue
        # A second field is only needed for the two-field checks, so a missing
        # field_b is an error only when the check asks for one.
        needs_b = str(chk).startswith("diff_") or str(chk).endswith("_ratio")
        values_b = None
        if needs_b:
            fb = w.get("field_b")
            if not fb:
                failures.append(f"{fname}: check {chk!r} requires field_b")
                continue
            values_b, why_b = _load_artifact(ws, str(rel), str(fb))
            if values_b is None:
                failures.append(f"{fname}: {why_b}")
                continue
                continue
            if len(values_b) != len(values):
                failures.append(
                    f"{fname}: field {field} has {len(values)} value(s) but field_b "
                    f"{fb} has {len(values_b)}; they must correspond element-wise")
                continue
        got = _derive(str(chk), values, expected, values_b)
        if got is None:
            unknown_check += 1
            failures.append(f"{fname}: check {chk!r} is not in the supported vocabulary")
            continue
        if bool(got) == bool(expected):
            verified += 1
            rows.append({"file": fname, "sha256": h, "status": "verified",
                         "check": chk, "n_values": len(values),
                         "sentence": sentence[:160]})
        else:
            refuted += 1
            detail = (f"{fname}: claim refuted by its own evidence — "
                      f"{field} in {rel} over {len(values)} value(s) gives "
                      f"{chk}={got}, the manuscript declares {expected}. "
                      f"Sentence: \"{sentence[:150]}\"")
            failures.append(detail)
            rows.append({"file": fname, "sha256": h, "status": "refuted",
                         "check": chk, "derived": got, "declared": expected,
                         "sentence": sentence[:160]})

    if failures:
        verdict = "FAIL"
    elif unregistered:
        verdict = "WARN"
    else:
        verdict = "PASS"
    return {
        "gate": "claim-witness", "version": "1.0",
        "verdict": verdict,
        "candidates": len(candidates),
        "verified": verified, "refuted": refuted,
        "unregistered": unregistered, "protocol": protocol,
        "unknown_check": unknown_check,
        "failures": failures,
        "rows": rows,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--write-verdict", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = check(args.workspace)
    if args.json:
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    else:
        print(f"claim_witness: {doc['verdict']} — {doc['candidates']} candidate(s): "
              f"{doc['verified']} verified, {doc['refuted']} refuted, "
              f"{doc['protocol']} protocol, {doc['unregistered']} unregistered")
        for f in doc["failures"][:10]:
            print("  -", f)
    if args.write_verdict:
        vd = args.workspace / ".sciforge" / "verdicts"
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "CLAIM_WITNESS.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return 0 if doc["verdict"] in ("PASS", "WARN") else 2


if __name__ == "__main__":
    sys.exit(main())
