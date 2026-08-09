#!/usr/bin/env bash
# verify_review_ledger.sh — external verifier for verdicts/REVIEW_LEDGER.json
#
# Checks (per Artifact Registry row for REVIEW_LEDGER.json):
#   1. ledger file exists (verdicts/REVIEW_LEDGER.json, fallback
#      review-stage/REVIEW_LEDGER.json for pre-v5.2 workspaces)
#   2. file is valid JSON
#   3. top-level object has a details.rounds[] array
#   4. every round object contains keys: score, verdict, action_items
#   5. every verdict value is within the 6-state vocabulary:
#      PASS / WARN / FAIL / NOT_APPLICABLE / BLOCKED / ERROR
#
# Exit 0 + "VERIFY PASS: review ledger" on success; exit 1 + precise
# reason on failure. python3 is used for JSON work (jq not required).
set -euo pipefail

usage() {
    echo "Usage: verify_review_ledger.sh <workspace_root>"
}

if [[ $# -ne 1 ]]; then
    usage
    exit 1
fi

WS="$1"

if [[ ! -d "$WS" ]]; then
    echo "VERIFY FAIL: workspace root not found: $WS" >&2
    exit 1
fi

# Locate the ledger: v5.2 canonical path first, pre-v5.2 fallback second.
LEDGER="$WS/verdicts/REVIEW_LEDGER.json"
if [[ ! -f "$LEDGER" ]]; then
    LEDGER="$WS/review-stage/REVIEW_LEDGER.json"
fi
if [[ ! -f "$LEDGER" ]]; then
    echo "VERIFY FAIL: REVIEW_LEDGER.json not found (looked in $WS/verdicts/ and $WS/review-stage/)" >&2
    exit 1
fi

if ! python3 - "$LEDGER" <<'PYEOF'
import json
import sys

ALLOWED = {"PASS", "WARN", "FAIL", "NOT_APPLICABLE", "BLOCKED", "ERROR"}
REQUIRED_ROUND_KEYS = ("score", "verdict", "action_items")
path = sys.argv[1]

def fail(msg: str) -> "None":
    print(f"VERIFY FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

try:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
except (OSError, ValueError) as exc:
    fail(f"{path} is not valid JSON: {exc}")

if not isinstance(doc, dict):
    fail(f"{path}: top-level value must be a JSON object, got {type(doc).__name__}")

details = doc.get("details")
if not isinstance(details, dict):
    fail(f"{path}: missing 'details' object")

rounds = details.get("rounds")
if not isinstance(rounds, list):
    fail(f"{path}: 'details.rounds' must be an array, got {type(rounds).__name__}")

if len(rounds) == 0:
    fail(f"{path}: 'details.rounds' is empty")

for i, rnd in enumerate(rounds):
    where = f"{path}: details.rounds[{i}]"
    if not isinstance(rnd, dict):
        fail(f"{where}: round entry must be an object, got {type(rnd).__name__}")
    missing = [k for k in REQUIRED_ROUND_KEYS if k not in rnd]
    if missing:
        fail(f"{where}: missing required key(s): {', '.join(missing)}")
    verdict = rnd["verdict"]
    if not isinstance(verdict, str) or verdict not in ALLOWED:
        fail(f"{where}: verdict {verdict!r} not in 6-state vocabulary "
             f"{sorted(ALLOWED)}")

print(f"VERIFY PASS: review ledger ({len(rounds)} round(s) checked, "
      f"all verdicts within 6-state vocabulary) [{path}]")
PYEOF
then
    # python already printed the precise reason; propagate failure.
    exit 1
fi
