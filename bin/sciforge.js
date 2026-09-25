#!/usr/bin/env node
// SciForge-OSS CLI — thin wrapper for skill-file distribution + toolchain helpers.
// The skills themselves are pure Markdown; this script only provides:
//   init            — scaffold a SciForge project skeleton in a target dir
//   tools-check     — report which optional toolchain tools are installed
//   tools-install   — install the optional toolchain (apt/npm, Linux-focused)
import { execSync, spawn } from "node:child_process";
import { existsSync, mkdirSync, copyFileSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = resolve(__dirname, "..");

const TOOLS = [
  { cmd: "python3", min: "3.10", check: "python3 --version", install: "system (apt/conda)" },
  { cmd: "pdflatex", min: "texlive", check: "which pdflatex", install: "apt install texlive-latex-base texlive-latex-extra texlive-science texlive-publishers texlive-bibtex-extra texlive-lang-chinese latexmk" },
  { cmd: "d2", min: "0.7", check: "d2 --version", install: "curl -fsSL https://d2lang.com/install.sh | sh -s --" },
  { cmd: "dot", min: "graphviz", check: "dot -V", install: "apt install graphviz" },
  { cmd: "rsvg-convert", min: "librsvg2-bin", check: "rsvg-convert --version", install: "apt install librsvg2-bin" },
  { cmd: "inkscape", min: "inkscape", check: "inkscape --version", install: "apt install inkscape" },
  { cmd: "svgo", min: "svgo", check: "svgo --version", install: "npm install -g svgo" },
  { cmd: "mihomo", min: "proxy", check: "probe 127.0.0.1:{8099,7890,7892,1080,8080} (auto-detect, not just pgrep)", install: "see https://wiki.metacubex.one/ — mixed-port 8099, mode rule (skills auto-detect 8099→7890→7892→1080→8080)" },
];

function have(cmd) {
  try { execSync(`which ${cmd} 2>/dev/null`, { stdio: "ignore" }); return true; }
  catch { return false; }
}

function cmd_init(target) {
  const dst = resolve(target || ".");
  if (!existsSync(dst)) mkdirSync(dst, { recursive: true });
  // copy skills/ + AGENT_GUIDE.md + SKILL.md + README.md into target
  const copyTree = (sub) => {
    const src = join(PKG_ROOT, sub);
    if (!existsSync(src)) return;
    const out = join(dst, sub);
    if (!existsSync(out)) mkdirSync(out, { recursive: true });
    for (const e of readdirSync(src, { withFileTypes: true })) {
      if (e.isDirectory()) copyTree(join(sub, e.name));
      else copyFileSync(join(src, e.name), join(out, e.name));
    }
  };
  copyTree("skills");
  copyTree("scripts");  // v5.3: toolchain (plotting/validators/security scan) ships with the skills
  copyTree("tests");    // v1.3.2: self-verification suite ships with the package
  copyTree("fixtures"); // v1.3.2: e2e fixture workspace (verdict contract pins)
  copyTree("kernel");   // v1.5.0: runtime kernel (control plane; needs Python >= 3.10)
  for (const f of ["AGENT_GUIDE.md", "SKILL.md", "README.md", "LICENSE", "VERSIONING.md", "CITATION.cff", "package.json"]) {
    const s = join(PKG_ROOT, f);
    if (existsSync(s)) copyFileSync(s, join(dst, f));
  }
  console.log(`[sciforge] initialized project skeleton at ${dst}`);
  console.log(`[sciforge] next: cd ${dst} && your-ai-agent (claude/codex/cursor/trae)`);
  console.log(`[sciforge] then: /auto-pipeline "your scientific problem"`);
}

function cmd_tools_check() {
  console.log("SciForge-OSS optional toolchain check:");
  console.log("========================================");
  let missing = 0;
  for (const t of TOOLS) {
    const ok = t.cmd === "mihomo" ? (() => {
      // Probe candidate proxy ports (must match universal-retrieval auto-detect list).
      // pgrep alone is a false positive when the process runs but the port isn't bound —
      // the proxy is unusable in that state, so we require a reachable port.
      for (const port of [8099, 7890, 7892, 1080, 8080]) {
        try {
          execSync(`python3 -c "import socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0 if s.connect_ex(('127.0.0.1',${port}))==0 else 1)"`, { stdio: "ignore" });
          return true;
        } catch {}
      }
      return false;
    })() : have(t.cmd);
    console.log(`${ok ? "[OK]   " : "[MISS] "}${t.cmd.padEnd(16)} (min ${t.min})  ${ok ? "" : "-> install: " + t.install}`);
    if (!ok && t.cmd !== "mihomo") missing++;
  }
  console.log("========================================");
  console.log(missing === 0 ? "All core tools present." : `${missing} tool(s) missing — run: sciforge tools-install`);
}

function cmd_tools_install() {
  console.log("Installing SciForge-OSS optional toolchain (Linux/apt + npm)...");
  const steps = [
    "apt-get update -y",
    "apt-get install -y texlive-latex-base texlive-latex-extra texlive-science texlive-publishers texlive-bibtex-extra texlive-lang-chinese latexmk graphviz librsvg2-bin inkscape",
    "curl -fsSL https://d2lang.com/install.sh | sh -s --",
    "npm install -g svgo",
  ];
  for (const s of steps) {
    try { execSync(s, { stdio: "inherit" }); }
    catch (e) { console.error(`[sciforge] step failed: ${s}\n${e.message}`); }
  }
  cmd_tools_check();
}

// ---- runtime kernel (v1.5.0: the control plane; skills stay pure Markdown) ----
// The kernel needs Python >= 3.10. Search order: repo .venv, python3.13/.12/.11/.10,
// python3 (only if its version passes), conda. Cache nothing — cheap probes.
function findKernelPython() {
  const cands = [
    join(PKG_ROOT, ".venv/bin/python"),
    join(PKG_ROOT, ".venv/Scripts/python.exe"),
  ];
  for (const m of ["3.13", "3.12", "3.11", "3.10"]) cands.push(`python${m}`);
  cands.push("python3");
  if (process.env.CONDA_PREFIX) cands.push(join(process.env.CONDA_PREFIX, "bin/python"));
  for (const c of cands) {
    try {
      const v = execSync(`"${c}" -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); sys.exit(0 if sys.version_info>=(3,10) else 1)"`,
        { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
      if (v.trim()) return { path: c, version: v.trim() };
    } catch {}
  }
  return null;
}

function cmd_run(rest, inherit = true) {
  const py = findKernelPython();
  if (!py) {
    console.error("[sciforge] kernel requires Python >= 3.10 (found none).");
    console.error("  fix: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt");
    console.error("  or:  conda create -n sciforge python=3.12");
    process.exit(1);
  }
  const env = { ...process.env, SCIFORGE_PY: py.path, PYTHONPATH: join(PKG_ROOT, "kernel") };
  const args = rest.length ? rest : ["--help"];
  const cmd = `"${py.path}" -m sciforge.cli ${args.map((a) => `"${String(a).replaceAll('"', '\\"')}"`).join(" ")}`;
  if (!inherit) {
    // detached daemon: survives the calling shell
    const child = spawn(py.path, ["-m", "sciforge.cli", ...args], {
      env, cwd: process.cwd(), stdio: "ignore", detached: true,
    });
    child.unref();
    console.log(`[sciforge] daemon starting pid=${child.pid}`);
    return;
  }
  try {
    execSync(cmd, { stdio: "inherit", cwd: process.cwd(), env });
  } catch (e) {
    process.exit(e.status ?? 1);
  }
}

const [,, sub, ...rest] = process.argv;
switch (sub) {
  case "init": cmd_init(rest[0]); break;
  case "tools-check": cmd_tools_check(); break;
  case "tools-install": cmd_tools_install(); break;
  case "run": case "resume": case "status": case "step": case "approve":
  case "gate": case "doctor": case "dispatch": case "jobs": case "evolve": case "submit":
  case "daily":
    cmd_run([sub, ...rest]);
    break;
  case "serve":
    cmd_run([sub, ...rest], false);
    break;
  case "deny":
    cmd_run(["approve", ...rest, "--deny"]);
    break;
  case "selftest": {
    const py = findKernelPython();
    if (!py) { console.error("[sciforge] no Python >= 3.10 found"); process.exit(1); }
    try {
      execSync(`"${py.path}" "${join(PKG_ROOT, "scripts", "ci_check.py")}"`,
        { stdio: "inherit", cwd: PKG_ROOT });
    } catch (e) { process.exit(e.status ?? 1); }
    break;
  }
  case "--help": case "-h": case undefined:
    console.log("SciForge — AI for Scientist Anything (skill library + runtime kernel, v1.5.0)\n");
    console.log("Usage (skill-only mode — read in any Markdown-capable agent):");
    console.log("  /auto-pipeline \"your scientific problem\"   (inside claude/codex/cursor/trae)");
    console.log("\nUsage (runtime kernel — headless CLI, needs Python >= 3.10):");
    console.log("  sciforge run --workspace DIR --problem \"...\" [--effort lite|balanced|max|beast] [--host auto|claude|codex|manual] [--loop] [--test-mode] [--human-skip]");
    console.log("  sciforge resume --workspace DIR [--loop]      # replay events, continue crashed run");
    console.log("  sciforge status --workspace DIR");
    console.log("  sciforge step --workspace DIR                 # one phase boundary (manual host protocol)");
    console.log("  sciforge approve --workspace DIR [checkpoint] | sciforge deny ...");
    console.log("  sciforge gate --workspace DIR verdicts|wrapup|figures");
    console.log("  sciforge dispatch --workspace DIR --script s.py [--group g] [--seed 3]");
    console.log("  sciforge jobs --workspace DIR --group g");
    console.log("  sciforge evolve --workspace DIR --proposes p.json [--budget 8] [--algorithm puct|openevolve]");
    console.log("  sciforge submit --workspace DIR evo_<id>       # human-authorized skill patch merge");
    console.log("  sciforge daily --workspace DIR");
    console.log("  sciforge doctor · sciforge cache|proxy · sciforge selftest");
    console.log("  sciforge serve --archive DIR                    # headless daemon (loopback :4510)");
    console.log("  sciforge init [dir] · sciforge tools-check · sciforge tools-install");
    console.log("\nKnowledge stays in skills/ (pure Markdown); control lives in kernel/. See AGENT_GUIDE.md.");
    break;
  default: console.error(`unknown subcommand: ${sub}`); process.exit(1);
}
