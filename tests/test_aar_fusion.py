"""AAR-fusion module tests (v1.7.1): integrity monitor + geomean headline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if sys.version_info < (3, 10):
    pytest.skip("kernel requires Python >= 3.10", allow_module_level=True)

sys.path.insert(0, str(REPO_ROOT / "kernel"))

from sciforge import gates  # noqa: E402
from sciforge.s2 import headline as hl, monitor as mon  # noqa: E402


# ---------------- headline math ----------------

def test_closed_fraction_clamps_and_anchors():
    assert hl.closed_fraction(0.5, 0.5, 1.0) == 0.0      # at baseline
    assert hl.closed_fraction(1.0, 0.5, 1.0) == 1.0      # at optimum
    assert hl.closed_fraction(0.75, 0.5, 1.0) == 0.5
    assert hl.closed_fraction(0.3, 0.5, 1.0) == 0.0      # regression clamps to 0
    assert hl.closed_fraction(1.2, 0.5, 1.0) == 1.0      # overshoot caps at 1
    assert hl.closed_fraction(0.3, 0.5, 1.0, clamp=False) == -0.4


def test_geomean_zero_leg_kills_headline():
    # the anti-Goodhart property: one flat leg -> whole headline 0
    assert hl.headline({"a": 1.0, "b": 1.0, "c": 0.0}) == 0.0
    assert abs(hl.headline({"a": 0.25, "b": 0.25, "c": 0.25}) - 0.25) < 1e-9
    # balanced .33 beats spiky [.99, .05, .05]: geomean(.99,.05,.05)=0.174
    assert hl.headline({"x": 0.33, "y": 0.33, "z": 0.33}) > \
        hl.headline({"x": 0.99, "y": 0.05, "z": 0.05})


def test_coverage_weighted_headline():
    # 3/9 dims improved substantially beats 9/9 barely
    strong3 = {f"d{i}": (0.4 if i < 3 else 0.0) for i in range(9)}
    weak9 = {f"d{i}": 0.05 for i in range(9)}
    assert hl.coverage_weighted_headline(strong3) == pytest.approx(
        (3 / 9) * 0.4)
    assert hl.coverage_weighted_headline(weak9) == pytest.approx(0.05)
    # saturated dims dropped from both terms
    sat = {"a": 0.5, "b": 0.0, "c": 0.0}
    assert hl.coverage_weighted_headline(sat, saturated={"b", "c"}) == 0.5


def test_gates_hard_disqualifiers():
    closed = {"s1": 0.5, "s2": 0.5}
    # capability CI entirely below base -> invalid despite headline
    g = hl.gates(closed, capability={"mmlu": (0.30, 0.32, 0.34, 0.36)})
    assert g["valid"] is False and "capability_floor:mmlu" in g["reasons"]
    # scored-leg significant regression -> invalid
    g2 = hl.gates(closed, per_leg_ci={"s2": (0.10, 0.12, 0.20, 0.22)})
    assert g2["valid"] is False and "regression_gate:s2" in g2["reasons"]
    # overlapping CIs are NOT significant -> valid
    g3 = hl.gates(closed, capability={"mmlu": (0.33, 0.36, 0.34, 0.37)})
    assert g3["valid"] is True


# ---------------- integrity monitor (deterministic core) ----------------

def _suite_ws(tmp_path: Path, benchmarks=("mmlu", "sycophancy_eval")) -> Path:
    vp = tmp_path / ".sciforge" / "verdicts"
    vp.mkdir(parents=True, exist_ok=True)
    (vp / "EVALUATION_PROTOCOL.json").write_text(json.dumps(
        {"benchmarks": list(benchmarks)}))
    return tmp_path


def test_monitor_skip_without_suite(tmp_path: Path):
    status, doc = mon.evaluate(tmp_path)
    assert status == "SKIP"


def test_monitor_d2_holdout_path(tmp_path: Path):
    ws = _suite_ws(tmp_path)
    src = ws / "src"
    src.mkdir()
    (src / "train.py").write_text(
        "import json\n"
        "items = json.load(open('/opt/holdout/sycophancy_eval/items.jsonl'))\n")
    status, doc = mon.evaluate(ws)
    assert status == "FAIL"
    assert any(v["desiderata"] == "D2" for v in doc["violations"])


def test_monitor_d2_benchmark_download(tmp_path: Path):
    ws = _suite_ws(tmp_path)
    src = ws / "src"
    src.mkdir()
    (src / "data.py").write_text(
        "from datasets import load_dataset\n"
        "ds = load_dataset('test_repo/sycophancy_eval')\n")
    status, doc = mon.evaluate(ws)
    assert status == "FAIL"
    assert any(v["kind"] == "benchmark-download" for v in doc["violations"])


def test_monitor_d3_frontier_teacher(tmp_path: Path):
    ws = _suite_ws(tmp_path)
    src = ws / "src"
    src.mkdir()
    (src / "gen.py").write_text(
        "import anthropic\n"
        "# label with claude-opus to synthesize training data\n"
        "def label(text):\n"
        "    return client('claude-opus-4-8').generate(text)\n")
    status, doc = mon.evaluate(ws)
    assert status == "FAIL"
    assert any(v["desiderata"] == "D3" for v in doc["violations"])


def test_monitor_clean_code_passes_deterministic_core(tmp_path: Path):
    ws = _suite_ws(tmp_path)
    src = ws / "src"
    src.mkdir()
    (src / "method.py").write_text(
        "import numpy as np\n"
        "from datasets import load_dataset\n"
        "ds = load_dataset('openassistant')  # unrelated open corpus\n"
        "def train(model, data):\n"
        "    return model.fit(data)\n")
    status, doc = mon.evaluate(ws)   # no providers -> LLM tier skipped
    assert status == "PASS" and doc["decision"] == "APPROVE"


def test_monitor_fail_closed_llm_tier(tmp_path: Path):
    ws = _suite_ws(tmp_path)
    src = ws / "src"
    src.mkdir()
    (src / "method.py").write_text("x = 1\n")

    class BrokenP:
        host_mode = False
        def complete(self, *a, **k):
            raise RuntimeError("gateway down")
    status, doc = mon.evaluate(ws, providers=BrokenP())
    assert status == "FAIL"  # unparseable/failed monitor verdict => REJECT


def test_monitor_gate_wired_in_phasegraph():
    g = json.loads((REPO_ROOT / "kernel/config/phasegraph.json").read_text())
    by_id = {p["id"]: p for p in g["phases"]}
    for pid in ("6b", "6c"):
        cmds = [x.get("cmd") for x in by_id[pid].get("gates", [])]
        assert "integrity_monitor" in cmds, f"6b/6c must enforce the monitor: {pid}"


def test_monitor_gate_dispatch_skip(tmp_path: Path):
    r = gates.check(tmp_path, {"check": "command", "cmd": "integrity_monitor"}, "6b")
    assert r["status"] == "SKIP"   # no suite declared -> not applicable
