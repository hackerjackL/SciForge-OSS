#!/usr/bin/env python3
"""Validate SciForge pipeline verdict artifacts against JSON Schemas.

Usage:
    python3 scripts/validate_verdicts.py <workspace_verdicts_dir> [--strict]

Scans a research workspace's flat ``verdicts/`` directory (v5.2 layout, see
skills/shared-references/output-protocol.md) and validates every known verdict
artifact against its JSON Schema in skills/shared-references/schemas/.

Behavior
--------
- Registered *.json verdict files are validated against <NAME>.schema.json plus
  cross-field post-checks (below).
- Unknown *.json / *.txt files => WARN (unregistered verdict).
- Registered-but-missing files are NOT errors; they are listed as "pending"
  (verdicts appear progressively as the pipeline advances).
- Hash files PROBLEM_HASH.txt / REGISTRY_HASH.txt are not JSON and are checked
  directly: single-line lowercase SHA256 hex, 64 chars (regex ^[0-9a-f]{64}$).
  Exception: per method-registry SKILL.md section 3.5, REGISTRY_HASH.txt may
  instead contain "BLOCKED: <reason>" when the hash-lock refused to generate
  (incomplete experiment matrix).

Cross-field invariants (post-checks)
------------------------------------
1. Audit-family 6-state verdict vocabulary. PROOF_AUDIT, LOGIC_VERIFICATION,
   LEAKAGE_AUDIT, CITATION_AUDIT, KILL_ARGUMENT, PAPER_CLAIM_AUDIT and
   INVARIANT_CHECK must carry ``verdict`` (or ``overall_verdict`` for
   INVARIANT_CHECK) in {PASS, WARN, FAIL, NOT_APPLICABLE, BLOCKED, ERROR}
   (assurance-contract.md). Also encoded as enums in the schemas.
2. Audit input hashes. PROOF_AUDIT, CITATION_AUDIT, KILL_ARGUMENT,
   LEAKAGE_AUDIT and PAPER_CLAIM_AUDIT must contain ``audited_input_hashes``
   (object mapping filename -> sha256); encoded in the schemas as required +
   value pattern (artifact-registry.md schema invariant 2).
3. Budget floor hard rules (experiment-execution SKILL.md): budget_floor
   ``satisfied == false`` forbids ``verdict: PASS`` (only IN_PROGRESS or
   BLOCKED allowed), and ``verdict: PASS`` requires ``completion_justification``.

Supported JSON-Schema subset (stdlib-only validator, no `jsonschema` package)
------------------------------------------------------------------------------
    type             "object" | "array" | "string" | "integer" | "number" |
                     "boolean" | "null"
    required         list of required property names
    properties       map of property name -> sub-schema
    additionalProperties  boolean, or a sub-schema applied to every property
                          not listed in `properties`
    enum             exact-match value list
    pattern          regex (re.search) applied to strings
    minimum/maximum  numeric bounds (inclusive)
    items            sub-schema applied to every array element

Annotation keywords are ignored: $schema, $id, $comment, title, description,
examples, default. Any other keyword ($ref, oneOf, anyOf, allOf, const,
format, minItems, patternProperties, ...) is reported as an internal error
instead of being silently ignored, so a schema can never over-promise.

Exit codes
----------
    0  all present artifacts valid (WARNs allowed in default mode)
    1  violations found (any FAIL; in --strict mode WARNs also fail => BLOCKED)
    2  usage error (bad arguments, missing directory)
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Contract tables
# ---------------------------------------------------------------------------

SIX_STATE_VERDICTS = ("PASS", "WARN", "FAIL", "NOT_APPLICABLE", "BLOCKED", "ERROR")
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "skills" / "shared-references" / "schemas"

# verdict filename -> metadata
#   schema:       schema file name in skills/shared-references/schemas/
#   audit_family: must carry a 6-state verdict (post-check 1)
#   audit_hashes: must carry audited_input_hashes (post-check 2, schema-enforced too)
REGISTRY = {
    "VERIFICATION_ROUTING.json": {"schema": "VERIFICATION_ROUTING.schema.json"},
    "EXPERIMENT_MATRIX.json": {"schema": "EXPERIMENT_MATRIX.schema.json"},
    "EVALUATION_PROTOCOL.json": {"schema": "EVALUATION_PROTOCOL.schema.json"},
    "BUDGET_FLOOR.json": {"schema": "BUDGET_FLOOR.schema.json"},
    "PROOF_AUDIT.json": {
        "schema": "PROOF_AUDIT.schema.json",
        "audit_family": True,
        "audit_hashes": True,
    },
    "LOGIC_VERIFICATION.json": {
        "schema": "LOGIC_VERIFICATION.schema.json",
        "audit_family": True,
    },
    "LEAKAGE_AUDIT.json": {
        "schema": "LEAKAGE_AUDIT.schema.json",
        "audit_family": True,
        "audit_hashes": True,
    },
    "BLINDSPOT_CHECK.json": {"schema": "BLINDSPOT_CHECK.schema.json"},
    "REVIEW_STATE.json": {"schema": "REVIEW_STATE.schema.json"},
    "REVIEW_LEDGER.json": {"schema": "REVIEW_LEDGER.schema.json"},
    "KILL_ARGUMENT.json": {
        "schema": "KILL_ARGUMENT.schema.json",
        "audit_family": True,
        "audit_hashes": True,
    },
    "PAPER_CLAIM_AUDIT.json": {
        "schema": "PAPER_CLAIM_AUDIT.schema.json",
        "audit_family": True,
        "audit_hashes": True,
    },
    "LEAKAGE_SCRUB.json": {"schema": "LEAKAGE_SCRUB.schema.json"},
    "CITATION_AUDIT.json": {
        "schema": "CITATION_AUDIT.schema.json",
        "audit_family": True,
        "audit_hashes": True,
    },
    "INVARIANT_CHECK.json": {
        "schema": "INVARIANT_CHECK.schema.json",
        "audit_family": True,  # uses overall_verdict + checks[].verdict
    },
    "PUBLISHABILITY_SCORE.json": {"schema": "PUBLISHABILITY_SCORE.schema.json"},
    "RUN_BUDGET.json": {"schema": "RUN_BUDGET.schema.json"},
    "FIGURE_AUDITS.json": {"schema": "FIGURE_AUDITS.schema.json"},
}

# Hash artifacts: single-line lowercase sha256 hex (no schema file).
HASH_FILES = ("PROBLEM_HASH.txt", "REGISTRY_HASH.txt")

# ---------------------------------------------------------------------------
# Minimal JSON-Schema-subset validator
# ---------------------------------------------------------------------------

ANNOTATION_KEYWORDS = {"$schema", "$id", "$comment", "title", "description", "examples", "default"}
SUPPORTED_KEYWORDS = {
    "type",
    "required",
    "properties",
    "additionalProperties",
    "enum",
    "pattern",
    "minimum",
    "maximum",
    "items",
}


def type_matches(instance, type_name):
    """Check an instance against a single JSON type name (bool is not an int)."""
    if type_name == "object":
        return isinstance(instance, dict)
    if type_name == "array":
        return isinstance(instance, list)
    if type_name == "string":
        return isinstance(instance, str)
    if type_name == "boolean":
        return isinstance(instance, bool)
    if type_name == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if type_name == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if type_name == "null":
        return instance is None
    return False


TYPE_NAMES = ("object", "array", "string", "boolean", "integer", "number", "null")


def lint_schema(schema, path="$"):
    """Reject unsupported keywords so a schema can never silently over-promise."""
    errors = []
    if not isinstance(schema, dict):
        return errors
    for key, value in schema.items():
        if key in ANNOTATION_KEYWORDS or key in SUPPORTED_KEYWORDS:
            continue
        errors.append("%s: unsupported schema keyword '%s' (stdlib validator subset)" % (path, key))
    # recurse into sub-schemas
    if isinstance(schema.get("properties"), dict):
        for name, sub in schema["properties"].items():
            errors.extend(lint_schema(sub, "%s.properties.%s" % (path, name)))
    if isinstance(schema.get("items"), dict):
        errors.extend(lint_schema(schema["items"], path + ".items"))
    if isinstance(schema.get("additionalProperties"), dict):
        errors.extend(lint_schema(schema["additionalProperties"], path + ".additionalProperties"))
    return errors


def validate_against(instance, schema, path="$"):
    """Validate `instance` against `schema`; return a list of error strings."""
    errors = []
    if not isinstance(schema, dict):
        return errors

    # type
    type_name = schema.get("type")
    if type_name is not None:
        if type_name not in TYPE_NAMES:
            errors.append("%s: schema declares unknown type '%s'" % (path, type_name))
        elif not type_matches(instance, type_name):
            errors.append("%s: expected %s, got %s" % (path, type_name, json_type_name(instance)))
            return errors  # further checks assume the right type

    # enum
    if "enum" in schema:
        allowed = schema["enum"]
        if not isinstance(allowed, list) or instance not in allowed:
            errors.append("%s: value %r not in enum %r" % (path, instance, allowed))

    # pattern (strings)
    if "pattern" in schema:
        if isinstance(instance, str):
            try:
                if re.search(schema["pattern"], instance) is None:
                    errors.append("%s: string %r does not match pattern %r" % (path, instance, schema["pattern"]))
            except re.error as exc:
                errors.append("%s: invalid schema pattern %r (%s)" % (path, schema["pattern"], exc))
        # non-strings: pattern simply does not apply (JSON Schema semantics)

    # numeric bounds
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: value %s < minimum %s" % (path, instance, schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append("%s: value %s > maximum %s" % (path, instance, schema["maximum"]))

    # object keywords
    if isinstance(instance, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for name in required:
                if name not in instance:
                    errors.append("%s: missing required field '%s'" % (path, name))
        else:
            errors.append("%s: schema 'required' must be a list" % path)

        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            errors.append("%s: schema 'properties' must be an object" % path)
            properties = {}
        additional = schema.get("additionalProperties", True)
        for name, value in instance.items():
            if name in properties:
                errors.extend(validate_against(value, properties[name], "%s.%s" % (path, name)))
            elif additional is False:
                errors.append("%s: additional property '%s' is not allowed" % (path, name))
            elif isinstance(additional, dict):
                errors.extend(validate_against(value, additional, "%s.%s" % (path, name)))
            # additional is True -> unconstrained

    # array keywords
    if isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for idx, element in enumerate(instance):
                errors.extend(validate_against(element, items, "%s[%d]" % (path, idx)))

    return errors


def json_type_name(instance):
    if instance is None:
        return "null"
    if isinstance(instance, bool):
        return "boolean"
    if isinstance(instance, int):
        return "integer"
    if isinstance(instance, float):
        return "number"
    if isinstance(instance, str):
        return "string"
    if isinstance(instance, list):
        return "array"
    if isinstance(instance, dict):
        return "object"
    return type(instance).__name__


# ---------------------------------------------------------------------------
# Cross-field post-checks
# ---------------------------------------------------------------------------

def post_checks(filename, data):
    """Documented cross-field invariants that go beyond per-field schema checks."""
    errors = []
    meta = REGISTRY[filename]

    if meta.get("audit_family") and isinstance(data, dict):
        # INVARIANT_CHECK uses overall_verdict; everyone else uses verdict.
        if "verdict" in data:
            value = data["verdict"]
            field = "verdict"
        elif "overall_verdict" in data:
            value = data["overall_verdict"]
            field = "overall_verdict"
        else:
            value, field = None, "verdict"
        if value not in SIX_STATE_VERDICTS:
            errors.append(
                "audit-family %s %r is not in the 6-state vocabulary %s"
                % (field, value, "/".join(SIX_STATE_VERDICTS))
            )

    if filename == "BUDGET_FLOOR.json" and isinstance(data, dict):
        floor = data.get("budget_floor")
        satisfied = floor.get("satisfied") if isinstance(floor, dict) else None
        verdict = data.get("verdict")
        if satisfied is False and verdict == "PASS":
            errors.append(
                "budget_floor.satisfied=false forbids verdict PASS "
                "(experiment-execution hard rule: only IN_PROGRESS or BLOCKED allowed)"
            )
        if verdict == "PASS" and "completion_justification" not in data:
            errors.append(
                "verdict PASS declares completion and requires completion_justification "
                "(attempted routes + status of each + remaining untried routes)"
            )

    if filename == "KILL_ARGUMENT.json" and isinstance(data, dict):
        # kill-argument verdict mapping: PASS requires still_unresolved == 0
        if data.get("verdict") == "PASS":
            details = data.get("details")
            counts = details.get("counts") if isinstance(details, dict) else None
            unresolved = counts.get("still_unresolved") if isinstance(counts, dict) else None
            if unresolved is None:
                errors.append(
                    "verdict PASS requires details.counts.still_unresolved == 0 "
                    "(counts block missing)"
                )
            elif unresolved != 0:
                errors.append(
                    "verdict PASS requires details.counts.still_unresolved == 0, got %r "
                    "(unresolved points force FAIL/WARN per the verdict mapping)"
                    % (unresolved,)
                )

    return errors


# ---------------------------------------------------------------------------
# Hash-file checks
# ---------------------------------------------------------------------------

def check_hash_file(filename, text):
    """Single-line lowercase sha256 hex; REGISTRY_HASH.txt may also be BLOCKED: <reason>."""
    errors = []
    stripped = text.strip()
    if not stripped:
        return ["file is empty"]
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    if len(non_empty_lines) > 1:
        errors.append("must be a single line (found %d non-empty lines)" % len(non_empty_lines))
    line = non_empty_lines[0].strip() if non_empty_lines else ""
    if SHA256_HEX_RE.match(line):
        return errors
    if filename == "REGISTRY_HASH.txt" and re.match(r"^BLOCKED:\s*\S", line):
        # method-registry SKILL.md section 3.5: hash-lock refusal form
        return errors
    errors.append(
        "expected single-line lowercase sha256 hex (64 chars), got %r%s"
        % (line[:80], " (REGISTRY_HASH.txt may also be 'BLOCKED: <reason>')" if filename == "REGISTRY_HASH.txt" else "")
    )
    return errors


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def load_schema(schema_name):
    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.is_file():
        return None, "schema file not found: %s" % schema_path
    try:
        with open(schema_path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, ValueError) as exc:
        return None, "cannot load schema %s: %s" % (schema_name, exc)


def validate_json_file(filename, filepath):
    """Validate one registered verdict JSON. Returns (status, notes)."""
    meta = REGISTRY[filename]
    schema, err = load_schema(meta["schema"])
    if schema is None:
        return "FAIL", [err]

    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        return "FAIL", ["cannot read file: %s" % exc]

    def _reject_constant(c):
        # NaN/Infinity are Python json extensions, not RFC-8259; they also
        # sail through numeric bounds checks (NaN compares False to
        # everything). Verdict files must be strict JSON.
        raise ValueError("non-standard JSON constant %r is not allowed" % c)

    try:
        data = json.loads(raw, parse_constant=_reject_constant)
    except RecursionError:
        return "FAIL", ["invalid JSON: nesting too deep to parse "
                        "(possible malformed/adversarial file)"]
    except ValueError as exc:
        note = "invalid JSON: %s" % exc
        if filename == "REVIEW_LEDGER.json" and len(raw.splitlines()) > 1:
            note += (
                " (multi-line JSONL detected: auto-review-loop SKILL.md describes a JSONL "
                "ledger, but the registered artifact is a single JSON object per "
                "artifact-registry.md; see schemas/README.md known gaps)"
            )
        return "FAIL", [note]

    errors = lint_schema(schema)
    errors.extend(validate_against(data, schema))
    errors.extend(post_checks(filename, data))

    if errors:
        return "FAIL", errors
    return "PASS", []


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate_verdicts.py",
        description="Validate a SciForge workspace verdicts/ directory against the schemas "
        "in skills/shared-references/schemas/ (stdlib only).",
    )
    parser.add_argument("verdicts_dir", help="path to the workspace verdicts/ directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat WARN (unregistered artifacts) as violations too (BLOCKED semantics)",
    )
    args = parser.parse_args(argv)

    verdicts_dir = Path(args.verdicts_dir)
    if not verdicts_dir.is_dir():
        print("error: not a directory: %s" % verdicts_dir, file=sys.stderr)
        return 2

    results = []  # (filename, status, notes)
    seen = set()

    for entry in sorted(verdicts_dir.iterdir()):
        if not entry.is_file():
            continue
        name = entry.name
        seen.add(name)
        if name.endswith(".json"):
            if name in REGISTRY:
                status, notes = validate_json_file(name, entry)
                results.append((name, status, notes))
            else:
                results.append((name, "WARN", ["unregistered verdict file (no schema in skills/shared-references/schemas/)"]))
        elif name.endswith(".txt"):
            if name in HASH_FILES:
                try:
                    text = entry.read_text(encoding="utf-8")
                except OSError as exc:
                    results.append((name, "FAIL", ["cannot read file: %s" % exc]))
                    continue
                errors = check_hash_file(name, text)
                results.append((name, "PASS" if not errors else "FAIL", errors))
            else:
                results.append((name, "WARN", ["unregistered .txt artifact in verdicts/"]))
        # other extensions (e.g. PIPELINE_VERDICT_SUMMARY.md narrative) are ignored

    # registered but missing -> pending (never an error)
    pending = sorted((set(REGISTRY) | set(HASH_FILES)) - seen)

    # ----- report -----
    print("SciForge verdict validation")
    print("  directory : %s" % verdicts_dir)
    print("  mode      : %s" % ("strict (WARN => BLOCKED)" if args.strict else "default"))
    print("  schemas   : %s" % SCHEMA_DIR)
    print()

    name_width = max([len(r[0]) for r in results] + [len(p) for p in pending] + [4])
    print("%-*s  %-8s  %s" % (name_width, "FILE", "STATUS", "NOTES"))
    print("%-*s  %-8s  %s" % (name_width, "-" * name_width, "-" * 8, "-" * 40))

    n_pass = n_fail = n_warn = 0
    for name, status, notes in results:
        if status == "PASS":
            n_pass += 1
        elif status == "FAIL":
            n_fail += 1
        else:
            n_warn += 1
        joined = "; ".join(notes) if notes else ""
        print("%-*s  %-8s  %s" % (name_width, name, status, joined))
    for name in pending:
        print("%-*s  %-8s  %s" % (name_width, name, "PENDING", "registered but not yet written"))

    print()
    print(
        "Summary: %d pass, %d fail, %d warn, %d pending (of %d registered artifacts)"
        % (n_pass, n_fail, n_warn, len(pending), len(REGISTRY) + len(HASH_FILES))
    )

    if n_fail > 0:
        return 1
    if args.strict and n_warn > 0:
        print("strict mode: WARN treated as violation => BLOCKED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
