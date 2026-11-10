#!/usr/bin/env python3
"""SciForge-OSS single CI entry point (python3 stdlib only, zero deps).

Runs five checks and prints a PASS/FAIL summary table:

  0. environment          `.venv/bin/python` must actually run: a dangling
                          interpreter symlink (e.g. the target interpreter
                          was uninstalled) fails REPRODUCE.md step 0 with a
                          bare shell "no such file or directory" that never
                          names the real cause.  No `.venv` at all is the
                          normal CI-container case and PASSES.  Broken links
                          are reported with the target, whether
                          site-packages is intact, and the exact fix.
  1. markdown-links       every .md file in the repo (skipping .git):
                          relative markdown links ](path) and <img src>
                          targets must exist on disk. Anchors (#...) are
                          stripped; http(s)/mailto/etc. links are ignored.
  2. version-consistency  package.json "version" must equal CITATION.cff
                          "version:" and every semver mentioned on
                          version-bearing lines of README.md / README.zh.md.
  3. plotting-module      py_compile the four plotting modules, then run
                          `render_figure.py --doctor` and require exit 0
                          (non-zero => toolchain DEGRADED => CI failure).
  4. test-suite           the repo's own gates, executed end-to-end:
                          pytest tests/ (missing pytest => FAIL with hint),
                          validate_verdicts.py on the e2e mock-verdict
                          fixture, and security_scan.py --self-test.

Exit code: 0 when all checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

PLOT_MODULES = [
    "scripts/plotting/sciforge_style.py",
    "scripts/plotting/figure_audit.py",
    "scripts/plotting/render_figure.py",
    "scripts/plotting/_pil_compat.py",
]

# Inline markdown link:  [text](target)  — target may carry a "title" part.
MD_LINK_RE = re.compile(r"\]\(\s*<?([^)<>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")
# HTML image source:     <img ... src="target" ...>
IMG_SRC_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
SEMV_RE = re.compile(r"v?\d+\.\d+\.\d+")
SKIP_SCHEMES = ("http://", "https://", "mailto:", "ftp://", "tel:", "data:")


def iter_markdown_files(root: Path):
    for path in sorted(root.rglob("*.md")):
        if any(part.startswith(".") for part in path.parts):
            continue  # .git and other hidden dirs
        yield path


def _strip_code_fences(text: str) -> str:
    """Blank out fenced code blocks (``` / ~~~) so documentation EXAMPLES
    of links do not count as links. Line structure is preserved so line
    numbers stay correct."""
    out_lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if fence is None and (stripped.startswith("```") or
                              stripped.startswith("~~~")):
            fence = stripped[:3]
            out_lines.append("")
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            out_lines.append("")
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _extract_md_links(text: str) -> list[tuple[int, str]]:
    """(line, target) pairs for inline markdown links. Handles one level of
    balanced parens in the target (docs/parens_(nested).md), <wrapped
    targets with spaces>, and plain targets. Reference-style links are
    intentionally not resolved (rare in this repo)."""
    links: list[tuple[int, str]] = []
    i = 0
    while True:
        i = text.find("](", i)
        if i < 0:
            break
        j = i + 2
        target: list[str] = []
        if j < len(text) and text[j] == "<":
            end = text.find(">", j + 1)
            if end < 0:
                i = j
                continue
            target.append(text[j + 1:end])
            j = end + 1
        else:
            depth = 0
            k = j
            while k < len(text):
                ch = text[k]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    if depth == 0:
                        break
                    depth -= 1
                elif ch in "\n" and depth == 0:
                    break  # malformed; stop at line end
                target.append(ch)
                k += 1
            j = k + 1
        links.append((text.count("\n", 0, i) + 1, "".join(target)))
        i = j
    return links


def check_markdown_links(root: Path) -> tuple[bool, list[str]]:
    """Return (ok, list of 'file:line -> target' broken-link reports)."""
    broken: list[str] = []
    for md in iter_markdown_files(root):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            broken.append(f"{md}:0 -> unreadable ({exc})")
            continue
        text = _strip_code_fences(text)
        targets: list[tuple[int, str]] = _extract_md_links(text)
        for m in IMG_SRC_RE.finditer(text):
            targets.append((text.count("\n", 0, m.start()) + 1, m.group(1)))
        for line, target in targets:
            tgt = target.strip().strip("<>")
            if not tgt or tgt.startswith("#"):
                continue  # pure anchor
            if tgt.startswith("//"):
                continue  # scheme-relative external URL
            if tgt.lower().startswith(SKIP_SCHEMES):
                continue  # external link
            path_part = unquote(tgt.split("#", 1)[0].split("?", 1)[0])
            if not path_part:
                continue  # was only an anchor / query after all
            if path_part.startswith("/"):
                # repo-root-absolute convention (GitHub/AtomGit style)
                candidates = [root / path_part.lstrip("/"), Path(path_part)]
            else:
                candidates = [md.parent / path_part]
            if not any(c.resolve().exists() for c in candidates):
                broken.append(f"{md}:{line} -> {tgt}")
    return (not broken, broken)


def check_version_consistency(root: Path) -> tuple[bool, list[str]]:
    """Return (ok, messages). All collected versions must be identical."""
    found: dict[str, list[str]] = {}  # source file -> versions
    problems: list[str] = []

    pkg = root / "package.json"
    if pkg.is_file():
        try:
            found["package.json"] = [json.loads(pkg.read_text())["version"]]
        except (OSError, ValueError, KeyError) as exc:
            problems.append(f"package.json: cannot read version ({exc})")
    else:
        problems.append("package.json: not found")

    cff = root / "CITATION.cff"
    if cff.is_file():
        m = re.search(r"^version:\s*(\S+)", cff.read_text(), re.MULTILINE)
        if m:
            found["CITATION.cff"] = [m.group(1)]
        else:
            problems.append("CITATION.cff: no 'version:' line found")
    else:
        problems.append("CITATION.cff: not found")

    for readme in ("README.md", "README.zh.md"):
        path = root / readme
        if not path.is_file():
            continue  # absence is tolerated; only explicit mentions are checked
        versions: list[str] = []
        in_fence = False
        for line in path.read_text(errors="replace").splitlines():
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            # code-fence examples and toolchain versions ("Python version
            # 3.12.4") are not release-version claims
            if in_fence or re.search(r"python\s+version", line, re.I):
                continue
            if "version" not in line.lower():
                continue
            versions.extend(
                v.lstrip("v") for v in SEMV_RE.findall(line)
            )
        if versions:
            found[readme] = versions

    distinct = sorted({v for vs in found.values() for v in vs})
    if len(distinct) > 1:
        for source, versions in sorted(found.items()):
            problems.append(f"{source}: {', '.join(versions)}")
        problems.insert(0, f"version mismatch across files: {distinct}")
    return (not problems and bool(found), problems or
            [f"all sources agree on version {distinct[0]}" if distinct else "no versions found"])


def check_plotting(root: Path) -> tuple[bool, list[str]]:
    """Return (ok, messages). py_compile modules + run render --doctor."""
    messages: list[str] = []
    ok = True
    for rel in PLOT_MODULES:
        target = root / rel
        try:
            py_compile.compile(str(target), doraise=True)
        except py_compile.PyCompileError as exc:
            ok = False
            messages.append(f"py_compile FAIL: {rel}: {exc.msg}")
    if ok:
        messages.append(f"py_compile OK: {', '.join(Path(p).name for p in PLOT_MODULES)}")

    doctor = root / "scripts/plotting/render_figure.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(doctor), "--doctor"],
            cwd=root, capture_output=True, text=True, timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        ok = False
        messages.append(f"render_figure.py --doctor could not run: {exc}")
        return (ok, messages)
    if proc.returncode == 0:
        messages.append("render_figure.py --doctor: READY (exit 0)")
    else:
        ok = False
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-3:]
        messages.append(
            f"render_figure.py --doctor: DEGRADED (exit {proc.returncode}); "
            + " | ".join(line.strip() for line in tail)
        )
    return (ok, messages)


def _venv_interpreter(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _site_packages(venv: Path) -> tuple[str | None, int]:
    """(best site-packages dir, entry count) — empty when none exists."""
    best: str | None = None
    count = 0
    candidates = list((venv / "lib").glob("python*/site-packages")) \
        if (venv / "lib").is_dir() else []
    win = venv / "Lib" / "site-packages"  # Windows venv layout
    if win.is_dir():
        candidates.append(win)
    for d in sorted(candidates):
        if not d.is_dir():
            continue
        entries = [p for p in d.iterdir()
                   if p.name != "__pycache__" and not p.name.startswith(".")]
        if len(entries) >= count:
            best, count = str(d), len(entries)
    return best, count


def check_environment(root: Path) -> tuple[bool, list[str]]:
    """Return (ok, messages). Verify the repo-local venv is actually usable.

    Reproducibility contract: REPRODUCE.md step 0 runs `.venv/bin/python`.
    When that path is a symlink to an interpreter that no longer exists
    (e.g. a conda install was removed), the shell reports only "no such
    file or directory" — nothing points at the real cause, and every later
    step is unreachable.  This check turns that silent breakage into an
    actionable FAIL.

    Severity: a broken `.venv` is a development-environment failure, not a
    product-quality one, but it blocks the documented reproduction path, so
    it FAILS.  No `.venv` at all is normal for CI containers running a
    system Python and PASSES explicitly.
    """
    venv = root / ".venv"
    if not venv.exists():
        return (True, [f"no .venv — using the running interpreter "
                       f"({sys.executable}); normal for CI containers"])

    py = _venv_interpreter(venv)
    site_dir, pkg_count = _site_packages(venv)
    cfg = venv / "pyvenv.cfg"
    if site_dir:
        site_note = f"site-packages intact: {site_dir} ({pkg_count} entries)"
    else:
        site_note = "no lib/python*/site-packages directory found"

    fix_hint = (
        "fix: point the link at a matching interpreter — "
        "ln -sfn \"$(command -v pythonX.Y)\" .venv/bin/python "
        "(X.Y must match the lib/pythonX.Y directory, or imports vanish); "
        "or recreate: python3 -m venv .venv && "
        ".venv/bin/pip install -r requirements.txt")

    if py.is_symlink() and not py.exists():
        try:
            target = os.readlink(py)
        except OSError:
            target = "<unreadable>"
        return (False, [
            f"BROKEN .venv interpreter symlink: {py} -> {target} "
            "(the target does not exist)",
            f"{site_note} — the packages are fine; only the interpreter "
            "link is broken",
            "this is why REPRODUCE.md step 0 dies with the shell's "
            "'no such file or directory' instead of naming the real cause",
            fix_hint,
        ])

    if not py.exists():
        if cfg.is_file() or site_dir:
            return (False, [
                f".venv exists but its interpreter is missing ({py})",
                site_note,
                "a partial/broken venv cannot run REPRODUCE.md step 0",
                fix_hint,
            ])
        return (True, [f".venv/ exists but is not a virtualenv "
                       f"(no {py.name}, no pyvenv.cfg) — ignored"])

    if not os.access(py, os.X_OK):
        return (False, [
            f".venv interpreter is not executable: {py}",
            site_note,
            fix_hint,
        ])

    try:
        proc = subprocess.run(
            [str(py), "-c",
             "import sys; print('%d.%d' % sys.version_info[:2]); "
             "print(sys.version.split()[0])"],
            capture_output=True, text=True, timeout=120, cwd=root,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (False, [
            f".venv interpreter cannot run: {py} ({exc})",
            site_note,
            fix_hint,
        ])
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-2:]
        return (False, [
            f".venv interpreter failed to run (exit {proc.returncode}): {py}",
            " | ".join(line.strip() for line in tail) or "no stderr",
            site_note,
            fix_hint,
        ])

    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    abi = lines[0] if lines else ""
    version = lines[1] if len(lines) > 1 else "unknown"
    site_norm = (site_dir or "").replace("\\", "/").lower()
    if abi and "python" in site_norm and f"python{abi}" not in site_norm:
        return (False, [
            f".venv interpreter is Python {version} but its packages live "
            f"under {site_dir}",
            "a venv interpreter must match the lib/pythonX.Y directory or "
            "every installed package silently becomes unimportable",
            f"fix: ln -sfn \"$(command -v python{abi})\" .venv/bin/python",
        ])
    return (True, [
        f".venv interpreter healthy: Python {version} ({py})",
        site_note,
        f"ci_check is running under {sys.executable}",
    ])


def check_test_suite(root: Path) -> tuple[bool, list[str]]:
    """Return (ok, messages). Execute the repo's own gates end-to-end.

    The test suite is the gate — a missing pytest is a FAIL, not a skip,
    so a bare checkout cannot silently pass CI without running the tests.
    """
    messages: list[str] = []
    ok = True

    def run_step(label: str, cmd: list[str], timeout: int = 600) -> bool:
        try:
            proc = subprocess.run(cmd, cwd=root, capture_output=True,
                                  text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            messages.append(f"{label}: could not run ({exc})")
            return False
        if proc.returncode == 0:
            tail = (proc.stdout or "").strip().splitlines()
            summary = tail[-1].strip() if tail else "exit 0"
            messages.append(f"{label}: PASS ({summary[:100]})")
            return True
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-4:]
        messages.append(f"{label}: FAIL (exit {proc.returncode}); "
                        + " | ".join(line.strip() for line in tail))
        return False

    try:
        import pytest  # noqa: F401
        ok &= run_step("pytest tests/",
                       [sys.executable, "-m", "pytest", "tests/", "-q"])
    except ImportError:
        ok = False
        messages.append("pytest tests/: FAIL (pytest not installed — "
                        "`pip install pytest`; the suite is mandatory)")

    validator = root / "scripts/validate_verdicts.py"
    fixture = root / "fixtures/e2e_minimal/.sciforge/verdicts"
    if validator.is_file() and fixture.is_dir():
        ok &= run_step("validate_verdicts e2e fixture",
                       [sys.executable, str(validator), str(fixture)])
    else:
        ok = False
        messages.append("validate_verdicts e2e fixture: FAIL "
                        "(scripts/validate_verdicts.py or "
                        "fixtures/e2e_minimal/.sciforge/verdicts missing)")

    scanner = root / "scripts/security_scan.py"
    if scanner.is_file():
        ok &= run_step("security_scan --self-test",
                       [sys.executable, str(scanner), "--self-test"])
    else:
        ok = False
        messages.append("security_scan --self-test: FAIL "
                        "(scripts/security_scan.py missing)")

    return (ok, messages)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ci_check.py",
        description="SciForge-OSS single CI entry point: environment "
                    "health + markdown link scan + version consistency + "
                    "plotting module + test suite.",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=DEFAULT_ROOT,
        help="repository root to check (default: parent of scripts/)",
    )
    parser.add_argument(
        "--quick", "--quiet", action="store_true", dest="quick",
        help="skip the test suite (the slow leg) — for `sciforge doctor` "
             "and other fast self-checks; `submit` still runs the full set",
    )
    args = parser.parse_args(argv)
    root: Path = args.repo_root.resolve()

    if not (root / "package.json").is_file():
        print(f"ERROR: {root} does not look like the SciForge-OSS repo root "
              "(no package.json)", file=sys.stderr)
        return 1

    checks = {
        "environment": lambda: check_environment(root),
        "markdown-links": lambda: check_markdown_links(root),
        "version-consistency": lambda: check_version_consistency(root),
        "plotting-module": lambda: check_plotting(root),
        "test-suite": lambda: check_test_suite(root),
    }
    if args.quick:
        checks.pop("test-suite")

    results: dict[str, tuple[bool, list[str]]] = {}
    for name, fn in checks.items():
        print(f"=== check: {name}")
        ok, details = fn()
        for line in details:
            print(f"  {line}")
        results[name] = (ok, details)
        print()

    width = max(len(n) for n in results)
    print("=" * (width + 10))
    print(f"{'CHECK'.ljust(width)}   RESULT")
    print("-" * (width + 10))
    all_ok = True
    for name, (ok, _details) in results.items():
        print(f"{name.ljust(width)}   {'PASS' if ok else 'FAIL'}")
        all_ok = all_ok and ok
    print("=" * (width + 10))
    print("OVERALL: " + ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
