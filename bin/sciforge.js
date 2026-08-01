#!/usr/bin/env node
// SciForge-OSS CLI — thin wrapper for skill-file distribution + toolchain helpers.
// The skills themselves are pure Markdown; this script only provides:
//   init            — scaffold a SciForge project skeleton in a target dir
//   tools-check     — report which optional toolchain tools are installed
//   tools-install   — install the optional toolchain (apt/npm, Linux-focused)
import { execSync } from "node:child_process";
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
  { cmd: "mihomo", min: "proxy", check: "pgrep -x mihomo || echo 'mihomo not running'", install: "see https://wiki.metacubex.one/ — mixed-port 8099, mode rule" },
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
  for (const f of ["AGENT_GUIDE.md", "SKILL.md", "README.md", "CITATION.cff", "package.json"]) {
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
    const ok = t.cmd === "mihomo" ? (() => { try { execSync("pgrep -x mihomo", { stdio: "ignore" }); return true; } catch { return false; } })() : have(t.cmd);
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

const [,, sub, ...rest] = process.argv;
switch (sub) {
  case "init": cmd_init(rest[0]); break;
  case "tools-check": cmd_tools_check(); break;
  case "tools-install": cmd_tools_install(); break;
  case "--help": case "-h": case undefined:
    console.log("SciForge-OSS CLI — pure-Markdown AI scientist skill package\n");
    console.log("Usage:");
    console.log("  sciforge init [dir]        Scaffold a SciForge project skeleton in [dir] (default: .)");
    console.log("  sciforge tools-check       Check which optional toolchain tools are installed");
    console.log("  sciforge tools-install     Install the optional toolchain (Linux/apt + npm)");
    console.log("\nThe skills are pure Markdown — read AGENT_GUIDE.md in any AI agent to start.");
    console.log("Then: /auto-pipeline \"your scientific problem\"");
    break;
  default: console.error(`unknown subcommand: ${sub}`); process.exit(1);
}
