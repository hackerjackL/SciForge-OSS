#!/usr/bin/env bash
# verify_review_ledger.sh — external verifier for verdicts/REVIEW_LEDGER.json
#
# Checks (per Artifact Registry row for REVIEW_LEDGER.json):
#   1. ledger file exists (.sciforge/verdicts/REVIEW_LEDGER.json since v6.0,
#      fallback verdicts/REVIEW_LEDGER.json (v5.2) and
#      review-stage/REVIEW_LEDGER.json (pre-v5.2) for old workspaces)
#   2. file is valid JSON
#   3. top-level object has a details.rounds[] array
#   4. every round object contains keys: score, verdict, action_items
#      (the phase="finalized" termination entry carries score + verdict +
#      final_score/final_verdict/total_rounds instead of action_items)
#   5. vocabulary: the TOP-LEVEL verdict is 6-state (PASS / WARN / FAIL /
#      NOT_APPLICABLE / BLOCKED / ERROR); per-round verdicts use the review
#      loop vocabulary (ready / almost / not_ready) — the 6-state values are
#      also accepted per-round for producer tolerance
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

# Locate the ledger: v6.0 canonical path first, then v5.2 and pre-v5.2 fallbacks.
LEDGER="$WS/.sciforge/verdicts/REVIEW_LEDGER.json"
if [[ ! -f "$LEDGER" ]]; then
    LEDGER="$WS/verdicts/REVIEW_LEDGER.json"
fi
if [[ ! -f "$LEDGER" ]]; then
    LEDGER="$WS/review-stage/REVIEW_LEDGER.json"
fi
if [[ ! -f "$LEDGER" ]]; then
    echo "VERIFY FAIL: REVIEW_LEDGER.json not found (looked in $WS/.sciforge/verdicts/, $WS/verdicts/ and $WS/review-stage/)" >&2
    exit 1
fi

if ! python3 - "$LEDGER" <<'PYEOF'
import json
import sys

ALLOWED = {"PASS", "WARN", "FAIL", "NOT_APPLICABLE", "BLOCKED", "ERROR"}
# per-round verdicts are review-loop outcomes (ready / almost / not_ready per
# auto-review-loop Phase E.5 and REVIEW_STATE's last_verdict vocabulary);
# 6-state values are tolerated for producers that write the envelope form.
ROUND_ALLOWED = {"ready", "almost", "not_ready", "not ready"} | ALLOWED
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
    # the phase="finalized" termination entry is a closing summary: it needs
    # score + verdict but carries no action_items
    required = REQUIRED_ROUND_KEYS
    if rnd.get("phase") == "finalized":
        required = ("score", "verdict")
    missing = [k for k in required if k not in rnd]
    if missing:
        fail(f"{where}: missing required key(s): {', '.join(missing)}")
    verdict = rnd["verdict"]
    if not isinstance(verdict, str) or verdict not in ROUND_ALLOWED:
        fail(f"{where}: verdict {verdict!r} not in the per-round vocabulary "
             f"{sorted(ROUND_ALLOWED)}")

print(f"VERIFY PASS: review ledger ({len(rounds)} round(s) checked, "
      f"all round verdicts within the review vocabulary) [{path}]")
PYEOF
then
    # python already printed the precise reason; propagate failure.
    exit 1
fi
