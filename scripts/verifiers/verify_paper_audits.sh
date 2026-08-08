#!/usr/bin/env bash
# verify_paper_audits.sh — external verifier for the paper-audit family
# (CITATION_AUDIT / PROOF_AUDIT / KILL_ARGUMENT), per Artifact Registry.
#
# Usage: verify_paper_audits.sh <workspace_root> [--assurance submission]
#
# For each audit in the family:
#   1. locate verdicts/<NAME>.json (fallback paper/<NAME>.json, pre-v5.2)
#   2. require valid JSON with a 6-state `verdict` field
#      (PASS / WARN / FAIL / NOT_APPLICABLE / BLOCKED / ERROR)
#   3. require an `audited_input_hashes` object
#   4. re-hash every listed input file that exists in the workspace
#      (sha256sum); any mismatch => STALE warning + exit 1
#
# Missing audit JSON:
#   - default (draft) mode  => print "SKIP (not present)" and continue
#   - --assurance submission => exit 1
# KILL_ARGUMENT is required only when assurance=submission AND the
# workspace contains a derivations/ directory (theory-heavy content).
set -euo pipefail

usage() {
    echo "Usage: verify_paper_audits.sh <workspace_root> [--assurance submission]"
}

WS=""
ASSURANCE="draft"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --assurance)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --assurance requires a value (draft|submission)" >&2
                usage
                exit 1
            fi
            ASSURANCE="$2"
            shift 2
            ;;
        --assurance=*)
            ASSURANCE="${1#--assurance=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [[ -n "$WS" ]]; then
                echo "ERROR: unexpected extra argument: $1" >&2
                usage
                exit 1
            fi
            WS="$1"
            shift
            ;;
    esac
done

if [[ -z "$WS" ]]; then
    usage
    exit 1
fi

if [[ "$ASSURANCE" != "draft" && "$ASSURANCE" != "submission" ]]; then
    echo "ERROR: --assurance must be 'draft' or 'submission', got: $ASSURANCE" >&2
    exit 1
fi

if [[ ! -d "$WS" ]]; then
    echo "VERIFY FAIL: workspace root not found: $WS" >&2
    exit 1
fi

VERDICTS_6="PASS WARN FAIL NOT_APPLICABLE BLOCKED ERROR"

fail() {
    echo "VERIFY FAIL: $*" >&2
    exit 1
}

# check_audit <NAME> — validate one audit JSON; returns via exit on error.
check_audit() {
    local name="$1"
    local path="$WS/verdicts/${name}.json"
    if [[ ! -f "$path" ]]; then
        path="$WS/paper/${name}.json"   # pre-v5.2 fallback location
    fi

    if [[ ! -f "$path" ]]; then
        if [[ "$ASSURANCE" == "submission" ]]; then
            fail "${name}.json missing (assurance=submission requires it; looked in $WS/verdicts/ and $WS/paper/)"
        fi
        echo "SKIP (not present): ${name}"
        return 0
    fi

    # 1) valid JSON + 6-state verdict + audited_input_hashes object;
    #    then emit "key<TAB>expected_hash" lines for the re-hash loop.
    local listing
    if ! listing=$(python3 - "$path" "$WS" <<'PYEOF'
import json
import sys

ALLOWED = {"PASS", "WARN", "FAIL", "NOT_APPLICABLE", "BLOCKED", "ERROR"}
path, ws = sys.argv[1], sys.argv[2]

def fail(msg: str) -> None:
    print(f"VERIFY FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

try:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
except (OSError, ValueError) as exc:
    fail(f"{path} is not valid JSON: {exc}")

if not isinstance(doc, dict):
    fail(f"{path}: top-level value must be a JSON object")

verdict = doc.get("verdict")
if not isinstance(verdict, str) or verdict not in ALLOWED:
    fail(f"{path}: verdict {verdict!r} not in 6-state vocabulary {sorted(ALLOWED)}")

hashes = doc.get("audited_input_hashes")
if not isinstance(hashes, dict):
    fail(f"{path}: 'audited_input_hashes' must be an object")

for key, val in hashes.items():
    if not isinstance(val, str):
        fail(f"{path}: audited_input_hashes[{key!r}] must be a string hash")
    print(f"{key}\t{val}")

print(f"OK: {path} (verdict={verdict}, {len(hashes)} audited input(s))",
      file=sys.stderr)
PYEOF
    ); then
        exit 1
    fi

    # 2) re-hash every listed input that exists in the workspace.
    local key expected candidate actual
    while IFS=$'\t' read -r key expected; do
        [[ -z "$key" ]] && continue
        expected="${expected#sha256:}"

        candidate=""
        if [[ "$key" = /* ]]; then
            [[ -f "$key" ]] && candidate="$key"
        else
            for cand in "$WS/$key" "$WS/paper/$key"; do
                if [[ -f "$cand" ]]; then
                    candidate="$cand"
                    break
                fi
            done
        fi

        if [[ -z "$candidate" ]]; then
            echo "WARN: ${name}: audited input not present in workspace, cannot re-hash: $key"
            continue
        fi

        actual=$(sha256sum "$candidate" | cut -d' ' -f1)
        if [[ "${actual,,}" != "${expected,,}" ]]; then
            echo "STALE: ${name}: hash mismatch for $key (audited ${expected:0:12}... != current ${actual:0:12}...)" >&2
            exit 1
        fi
    done <<< "$listing"

    echo "PASS: ${name} (${path})"
}

check_audit "CITATION_AUDIT"
check_audit "PROOF_AUDIT"

# KILL_ARGUMENT: required only when assurance=submission AND derivations/ exists.
if [[ "$ASSURANCE" == "submission" && -d "$WS/derivations" ]]; then
    check_audit "KILL_ARGUMENT"
else
    if [[ ! -f "$WS/verdicts/KILL_ARGUMENT.json" && ! -f "$WS/paper/KILL_ARGUMENT.json" ]]; then
        echo "SKIP (not required): KILL_ARGUMENT (assurance=$ASSURANCE, derivations/ $([[ -d "$WS/derivations" ]] && echo present || echo absent))"
    else
        check_audit "KILL_ARGUMENT"
    fi
fi

echo "VERIFY PASS: paper audits (assurance=$ASSURANCE)"
