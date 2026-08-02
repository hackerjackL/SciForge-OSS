# SciForge-OSS

> **[English](README.md)** | **[中文](README.zh.md)**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-green.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub](https://img.shields.io/badge/repo-gitcode-blue)](https://gitcode.com/GewisLab/SciForge-OSS)
[![AI for Science](https://img.shields.io/badge/AI%20for-Science-ff69b4)](https://gitcode.com/GewisLab/SciForge-OSS)

> **AI for Scientist Anything** — a pure Skill-driven universal scientific intelligence framework.
>
> The pure-skill-driven spirit: **no `.py` scripts, no bash code blocks, no IDE-specific syntax**.
> Any AI agent that can read Markdown (Claude Code, Cursor, Trae, Codex, etc.) can consume these skills.
>
> The 125 science problems are a "AI for Scientist Anything" demo showcase — the world's questions go far beyond 125.

---

## Table of Contents

- [What is this](#what-is-this)
- [Installation](#installation)
- [Architecture: DAG-driven research loop](#architecture-dag-driven-research-loop)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Full-domain support](#full-domain-support)
- [Verification paths: four routes](#verification-paths-four-routes)
- [Multi-domain examples](#multi-domain-examples)
- [Core design principles](#core-design-principles)
- [125 Science Problems Demo](#125-science-problems-demo)
- [FAQ](#faq)
- [License](#license)

## What is this

**SciForge-OSS** is a pure-Skill-driven **universal AI Scientist framework** with no discipline restriction. Whether physics, mathematics, computer science, life science, medicine, economics, education, materials science, earth science, atmospheric science, astronomy, chemistry, engineering, sensors, optoelectronics — any scientific domain can use this framework.

**Core philosophy**: Domain-Agnostic. The framework itself hardcodes no domain knowledge; all domain-specific methodology is handled by the agent's runtime reasoning.

**OSS = Open Single-question Stream** — single-question execution: each invocation processes one Q-id and does not auto-iterate all questions; one universal pipeline for all domains (no overlays, no discipline branches); the agent's runtime reasoning handles domain methods; a single `senior-reviewer-agnostic` persona; a single unified `elsarticle` template; four optional verification routes (theory-only / computational / theory+experiment / qualitative); INV-G1 as the sole invariant (PROBLEM_ANCHOR_FREEZE, universal).

SciForge-OSS distills **4 universal meta-skills**, handling any problem with one invariant set:

| Meta-skill | Role | Description |
|------------|------|-------------|
| **Dynamic Sandbox** | Compute engine | Run arbitrary Python/Julia scientific computation (NumPy/SciPy/SymPy) — numerical sanity check |
| **Dynamic Tooling** | Tool factory | When tools are insufficient at runtime, dynamically write and register temporary tools |
| **Universal Retrieval** | Literature search | Multi-source academic search (arXiv/S2/CrossRef/PubMed/Web/OpenAlex) + 3-layer anti-hallucination verification |
| **Unified Plotting** | Figure rendering | Structured data → publication-quality vector figures (PDF+PNG); Morandi palette (Layer 1) + viridis/magma data colormaps (Layer 2) |

## Installation

> **v1.1.0**: pure Skill package + optional toolchain. The skills themselves are pure Markdown that any Markdown-capable AI agent can consume directly; fully running through (figures / literature / compile / experiments) needs the optional toolchain, see "Toolchain (optional but recommended)" below.

### Method 1: Clone the repository (recommended, standard skill integration)

```bash
git clone https://gitcode.com/GewisLab/SciForge-OSS.git
cd SciForge-OSS
```

Then open the project directory in an AI agent (Claude Code / Cursor / Trae / Codex, etc.); the agent auto-reads `AGENT_GUIDE.md` as the entry point. The skill files themselves need no installation, no compilation, no dependency management.

### Method 2: Install from npm (global `sciforge` command, published)

The package is published to the npm registry as `@gewislab/sciforge-oss` — that's it:

```bash
npm install -g @gewislab/sciforge-oss

sciforge --help          # installed — the sciforge command is globally available
```

Step 3 — check the optional toolchain (install on demand):

```bash
sciforge tools-check     # reports which optional toolchain tools are installed
sciforge tools-install   # one-shot install of the optional toolchain (apt: texlive/d2/rsvg-convert/inkscape/graphviz; npm: svgo)
```

Scaffold a project skeleton:

```bash
sciforge init ./my-research   # scaffold a SciForge project skeleton in a target dir
```

`package.json`'s `bin` field registers `sciforge` pointing at `./bin/sciforge.js`; the `files` field declares the distribution contents (`skills/` + `AGENT_GUIDE.md` + root `SKILL.md` + `bin/`). The CLI has no external dependencies (pure Node stdlib).

> Prefer a local checkout? Clone the repo and run `node bin/sciforge.js --help` from the repo root (see Method 1) — same commands, no npm install.

If you prefer not to use npm, clone and use `bin/sciforge.js` directly (no external deps, pure Node stdlib):

```bash
git clone https://github.com/hackerjackL/SciForge-OSS.git
cd SciForge-OSS

# call bin directly with node (no install)
node bin/sciforge.js --help
node bin/sciforge.js tools-check
node bin/sciforge.js init ./my-research

# or npm link to register a global command from this clone
npm link
sciforge --help
```

`package.json`'s `bin` field registers `sciforge` pointing at `./bin/sciforge.js`; the `files` field declares the distribution contents (`skills/` + `AGENT_GUIDE.md` + root `SKILL.md` + `bin/`). The scoped name `@gewislab/sciforge-oss` means the npm registry shows it under the `gewislab` organization.

### Method 4: Add the skill files to an existing research project

```bash
cp -r SciForge-OSS/skills/ /your-project/
cp SciForge-OSS/AGENT_GUIDE.md /your-project/
```

### AI agent configuration

#### Claude Code / Codex / Cursor / Trae

```bash
cd SciForge-OSS        # or the npm-init project dir
claude                  # or codex / cursor / trae
# then type directly:
/auto-pipeline "Q001: origin and evolution of the universe" — effort: max, language: english
# or in test mode (bypass human checkpoints, agent runs the whole loop):
/auto-pipeline "your problem" — test_mode=true
```

#### Other AI agents

Any AI agent supporting Markdown context or custom skill sets works: provide `AGENT_GUIDE.md` to the agent as a system prompt / initial context; the agent reads it and auto-understands the 21-phase DAG loop and all available skills; type `/auto-pipeline "your scientific problem"` to launch.

### Toolchain (optional but recommended — needed to fully run through)

The skills themselves are pure Markdown, but fully running through (figure rendering / literature search / LaTeX compile / experiment execution) needs the optional tools below. `sciforge tools-check` reports missing items; `sciforge tools-install` installs them in one shot.

| Tool | Purpose | Install | Necessity |
|------|---------|---------|-----------|
| **Python 3.10+** | Data plots, SymPy derivation, experiment scripts | system (apt/conda) | Required (core compute) |
| **texlive (pdflatex/latexmk/bibtex)** | Phase 13 zero-warning PDF compile | `apt install texlive-latex-base texlive-latex-extra texlive-science texlive-publishers texlive-bibtex-extra texlive-lang-chinese latexmk` | Required (paper compile) |
| **d2** (v0.7+) | Complex architecture/flow/topology diagrams (headless-native, primary) | `curl -fsSL https://d2lang.com/install.sh \| sh -s --` | Recommended (figures) |
| **graphviz/dot** | Dense network/dependency graphs (d2 fallback) | `apt install graphviz` | Recommended (figures fallback) |
| **rsvg-convert** (librsvg) | SVG → PDF+PNG conversion (dual output from d2/graphviz) | `apt install librsvg2-bin` | Recommended (figure dual output) |
| **inkscape** | rsvg-convert fallback (SVG→PDF+PNG) | `apt install inkscape` | Optional (figures fallback) |
| **svgo** | SVG optimization (smaller intermediate files) | `npm install -g svgo` | Optional (figure optimization) |
| **mihomo** (or any HTTP/SOCKS5 proxy) | Phase 4 literature search access to arxiv/s2/crossref/openalex/huggingface | see [mihomo docs](https://wiki.metacubex.one/), rule mode `mode: rule`, `mixed-port: 8099` | Required (literature search; direct arxiv from a CN network times out) |
| **PyTorch** (optional) | ML / deep-learning experiments (CPU/GPU/NPU) | `pip install torch` or conda | Optional (only ML problems; CPU/GPU auto-detected) |

**GPU/NPU**: SciForge auto-detects (experiment-execution Step 0a) — `nvidia-smi`(cuda) / `rocminfo`(rocm) / `npu-smi`(npu) / `torch.backends.mps`(Apple Silicon); missing GPU auto-falls back to CPU + WARN, never blocks. Never hardcode `.cuda()`.

**Why not mermaid-cli / drawio**: mermaid-cli (`mmdc`) renders via headless Chromium (puppeteer), which is fragile on headless servers; drawio-desktop is a GUI app, not headless-friendly. d2 and graphviz/dot are both headless-native and stable in server environments. If a human later wants to hand-edit a diagram in drawio's GUI, they can import the d2/dot-produced SVG — but the pipeline itself uses headless tools only.

### mihomo proxy configuration (required for literature search)

Phase 4 universal-retrieval accesses the external network via mihomo rule mode. Example config (`~/.config/mihomo/config.yaml`):

```yaml
mixed-port: 8099          # HTTP + SOCKS5
mode: rule                # rule mode (CN direct, external via proxy)
# node list + proxy groups omitted; use your VPN config
```

After start, all arxiv/s2/crossref/openalex/huggingface/github requests auto-route via the proxy. The skill's `universal-retrieval` has the `http_proxy=http://127.0.0.1:8099` contract built in. On timeout, `nohup` retries in the background; Phase 4 is never skipped.

## Architecture: DAG-driven research loop

The core of SciForge-OSS is a **21-phase DAG research loop** driven by a single entry orchestrator (`/auto-pipeline`). Each invocation runs the complete loop on one Q-id, producing a full paper (LaTeX/PDF) + all intermediate artifacts.

```
Phase  0: Load problem (freeze Q-id — INV-G1 anchor)
Phase  1: Problem understanding + decomposition
Phase 1a: /domain-signature (OPTIONAL fast-path hint)
Phase 1b: /domain-learner (MUST, sole writer of domain-signature.json)
Phase  2: /idea-discovery [DAG branch] — 4 perspectives + MCTS iteration
Phase 2.5: /adversarial-falsification [falsification gate] — hypothesis scoring + counterexample + literature adversarial
Phase 2.5b: Phase 5b AI Engineering Grounding (EG report)
Phase  3: /novelty-check [DAG gate] — 4-axis scoring + pruning
     ─── Forced human checkpoint: pick the final idea ─── (test_mode bypasses: agent auto-selects)
Phase  4: /universal-retrieval — literature survey + 3-layer anti-hallucination (MUST, no-skip; via mihomo proxy)
Phase  5: /method-registry — method binding + hash lock + forced human approval (test_mode bypasses)
Phase  6: /theory-derivation — SymPy symbolic derivation + step-by-step machine verification
     │  ── Experiment execution layer (v2.0) ── non-theory-only path ──
Phase  6b: /experiment-execution --stage=toy [CONDITIONAL] — toy: minimal-scale core-reasoning-chain validation (foreground ≤5min, else toy_bg background)
Phase  6c: /experiment-execution --stage=full --background [CONDITIONAL] — full: background dispatch (nohup/tmux/systemd)
Phase  7: /leakage-audit — Type I logic gap + Type IV escape audit
Phase  8: /logic-verification — 6-dim logical consistency audit (FATAL contradiction → BA back to Phase 2)
Phase  9: /invariant-check — INV-G1 problem-anchor freeze verification
Phase 10: /result-to-claim — 3-fidelity claim gate (symbolic/numerical/qualitative); reads background STATUS.json
Phase 11: /unified-plotting — academic figures (MUST; PDF+PNG dual output; 16:9; Nature readability; d2 for diagrams)
Phase 12: /paper-writing — elsarticle single template (mode-selected section set)
Phase 13: /paper-compile — LaTeX zero-warning zero-error compile (MUST, non-waivable)
Phase 14: /auto-review-loop — structured self-review (role switch: researcher→reviewer→adjudicator) + kill-argument (MUST)
Phase 15: /citation-audit — final 3-layer citation verification
Phase 15.5: /publishability-score — 6-dim score (main-experiment-logic is the gating axis) (MUST, new v2.2)
Phase 16: Final assembly + cleanliness audit (project-architecture-contract)
```

**Fallback contract (bounded 3 rounds)**: each phase with a ↻ falls back to the relevant prior phase on failure, bounded to 3 rounds per failure-type. Past round 3 → BLOCKED + surfaced to the human. **BA (Backtracking-After, v2.2.1)**: when an experiment falsifies the idea's core claim (Phase 6c full FAIL after toy PASS / Phase 8 FATAL contradiction / Phase 14 kill-argument sustained), the orchestrator backtracks to Phase 2 to regenerate the idea (bounded 2 rounds) — distinct from phase-internal 3-round fallback.

**Forced human checkpoints (2)**: Phase 3→4 (pick the final idea) and Phase 5→6 (approve the method registry). `test_mode=true` bypasses these (agent does the work each guards, defers only the human approval; logs `human_review_status=PENDING_DEFERRED, production_ready=false`).

## Quick Start

### Solve one problem (default)

```
/auto-pipeline "Q001: origin and evolution of the universe" — effort: max, language: english
/auto-pipeline "Q042: high-efficiency energy storage"
/auto-pipeline "Analyze this economics model: general equilibrium under incomplete markets"
/auto-pipeline "Study: AI-driven drug discovery for Alzheimer's disease"
```

The orchestrator runs the full 21-phase loop. Forced human checkpoints at Phase 3→4 and 5→6 (bypassed in test_mode).

### Test mode (autonomous, bypasses the 2 checkpoints)

```
/auto-pipeline "your problem" — test_mode=true
```

The agent runs the full loop end-to-end, bypassing (not skipping) the 2 human checkpoints — it still selects the idea and builds the method registry, logging the bypass with `production_ready=false` so a human must later confirm.

### Resume from a checkpoint

```
"resume Q015 — I picked idea 2"
"resume Q042 — method registry approved, proceed to theory derivation"
```

### Partial run (debugging)

The user can invoke individual skills directly:

```
"/theory-derivation on the Q015 derivation plan"
"/logic-verification on derivations/Q015/derivation_output.md"
"/paper-compile paper/main.tex"
```

But the canonical workflow is the full 21-phase orchestrator loop; partial runs are for debugging only.

## Project Structure

```
SciForge-OSS/
├── SKILL.md                         # package manifest (entry: skills/orchestrator/auto-pipeline/SKILL.md)
├── AGENT_GUIDE.md                   # the agent entry guide (read this first)
├── README.md                        # this file (English)
├── README.zh.md                     # Chinese version
├── CHANGELOG.md                     # version history
├── CITATION.cff                      # citation metadata
├── package.json                     # npm distribution metadata (local CLI; not published to registry)
├── bin/sciforge.js                  # local CLI (init / tools-check / tools-install)
├── problems/
│   └── 125-SCIENCE-PROBLEMS.md      # 125-problem demo index (NOT auto-searched; human supplies Q-id)
├── skills/
│   ├── orchestrator/
│   │   └── auto-pipeline/SKILL.md   # the single entry orchestrator (21-phase DAG loop)
│   ├── meta-skills/                 # 8 universal meta-skills
│   │   ├── idea-discovery/          # MCTS-enhanced idea generation (4 perspectives incl. empirical)
│   │   ├── universal-retrieval/     # literature search + 3-layer anti-hallucination (mihomo proxy)
│   │   ├── unified-plotting/        # publication-quality figures (PDF+PNG dual; 16:9; d2 for diagrams)
│   │   ├── dynamic-sandbox/         # lightweight numerical sanity checks (Python/numpy)
│   │   ├── dynamic-tooling/         # on-the-fly tooling for the sandbox
│   │   ├── domain-learner/          # learns domain signature from literature (sole writer)
│   │   ├── domain-signature/        # rule-based signature hint (optional fast-path)
│   │   └── novelty-check/          # novelty detection
│   ├── support/                     # support skills
│   │   ├── paper-writing/           # compose the paper (mode-selected section set)
│   │   ├── paper-compile/           # LaTeX → PDF (zero warnings, anti-deadloop)
│   │   ├── quality-gate/            # hard gate at the final pre-writing boundary
│   │   ├── auto-review-loop/        # structured self-review (role switch)
│   │   ├── experiment-execution/    # toy + full + background dispatch (v2.0; device auto-detect v2.2)
│   │   ├── theory-derivation/       # SymPy symbolic derivation + machine verification
│   │   ├── leakage-audit/           # Type I + Type IV audit
│   │   ├── logic-verification/      # 6-dim logical consistency audit
│   │   ├── result-to-claim/         # 3-fidelity claim gate
│   │   ├── invariant-check/         # INV-G1 verification
│   │   ├── kill-argument/           # anti-self-deception
│   │   ├── method-registry/         # method registry + hash lock
│   │   ├── citation-audit/          # final 3-layer citation verification
│   │   ├── adversarial-falsification/  # adversarial falsification
│   │   └── publishability-score/    # 6-dim publishability score (new v2.2)
│   └── shared-references/           # shared contracts (discipline-agnostic)
│       ├── paper-modes.md           # 5-mode selector (theory/experiment/computational/survey/hybrid)
│       ├── figure-quality-contract.md  # 16:9, PDF+PNG dual, Nature readability, d2 pipeline
│       ├── project-architecture-contract.md  # GitHub-style project tree + cleanliness audit
│       ├── background-dispatch-protocol.md     # >5min background dispatch
│       ├── citation-discipline.md   # 3-layer anti-hallucination
│       ├── writing-principles.md    # academic writing + per-domain style contract (v2.2.1)
│       ├── discipline-writing.md    # universal section-by-section guide
│       ├── color-themes.md          # Morandi (Layer 1) + viridis/magma (Layer 2)
│       ├── venue-profiles.md        # single elsarticle template spec
│       ├── multi-fidelity-evaluation.md  # universal Low/Mid/High
│       ├── effort-contract.md       # lite/balanced/max/beast
│       ├── engineering-grounding-contract.md  # 5-dim EG axis
│       └── ... (31+ shared references)
└── templates/
    └── (paper-writing/templates/default/ — unified elsarticle skeleton)
```

## Full-domain support

SciForge-OSS supports **all scientific domains**. The framework hardcodes no discipline knowledge; the agent's runtime reasoning handles domain-specific methodology. The `domain-learner` (Phase 1b) learns the domain signature from literature, and the downstream skills adapt to that signature.

Domains validated in real end-to-end runs (10 rounds, all 21 phases PASS):
- **Physics** (damped oscillator energy conservation) — hybrid mode
- **Economics** (minimum-wage DiD) — experiment mode
- **CS/ML** (label-smoothing ablation) — computational mode
- **Materials** (MoS2→WS2 band gap) — hybrid mode
- **Medicine** (Alzheimer's biomarker diagnosis) — experiment mode
- **Pure math** (AM-GM inequality) — theory mode
- **Humanities** (Fall of Rome historiography) — survey mode
- **Background-dispatch** stress test — nohup + STATUS.json polling

## Verification paths: four routes

Each problem's `verification_type` (a canonical token: `theory-only` | `computational` | `theory+experiment` | `qualitative`) selects the verification route and the paper mode:

| verification_type | Phase 6b/6c | Paper mode | Example |
|-------------------|-------------|-----------|---------|
| `theory-only` | SKIP | theory | Pure math proof |
| `computational` | MUST | computational | ML ablation, numerical sweep |
| `theory+experiment` | MUST | hybrid | Physics derivation + numerical check |
| `qualitative` | SKIP | survey | Literature taxonomy/synthesis |

## Multi-domain examples

### Physics
```
/auto-pipeline "Q001: origin and evolution of the universe" — effort: max, language: english
```
→ Output: cosmological theory derivation + ΛCDM model verification

### Mathematics
```
/auto-pipeline "Prove: for any n≥3, no positive integer solutions satisfy x^n + y^n = z^n"
```
→ Output: elementary proof sketch of Fermat's last theorem + literature survey

### Economics
```
/auto-pipeline "Analyze: general equilibrium under incomplete markets"
```
→ Output: existence-of-equilibrium proof + numerical verification

### Education
```
/auto-pipeline "Study: instructional-design optimization based on cognitive-load theory"
```
→ Output: theoretical model + logic verification + experiment-design suggestions

### Materials science
```
/auto-pipeline "Predict: band structure of MoS2 under strain"
```
→ Output: band-structure derivation + numerical verification

### Medicine
```
/auto-pipeline "Study: AI-driven drug discovery for Alzheimer's disease"
```
→ Output: drug-target identification + molecular-dynamics verification

### Humanities
```
/auto-pipeline "Survey: historiographical debate on the causes of the Fall of the Western Roman Empire"
```
→ Output: 4-school taxonomy (Gibbon / barbarian-invasion / economic-fiscal / late-antique-continuity) + d2 timeline + comparison table

## Core design principles

1. **Single entry** — `/auto-pipeline` is the only entry orchestrator; every run goes through the complete 21-phase DAG loop.

2. **DAG over linear** — multiple ideas explored in parallel; weak ideas pruned at gates; only the strongest survive. The DAG structure is traceable and visualizable.

3. **Meta-skills over discipline skills** — 4 universal meta-skills replace discipline-specific skills. The system handles any scientific problem without hardcoding domain knowledge.

4. **Computation over knowledge** — when the AI does not know the answer, it derives it. The dynamic sandbox executes AI-written code, not pre-written programmer code.

5. **Anti-hallucination first** — every citation is verified by 3 independent academic APIs (arXiv + CrossRef + Semantic Scholar). No paper is fabricated from memory.

6. **Structured self-review** — review uses a role-switch mode (researcher→reviewer→adjudicator); no cross-model collaboration required.

7. **Reproducible** — every computation, derivation, and figure is preserved as executable code + input data, not just output text.

8. **Publication-grade, not engineering-report** — writing follows Nature/Science/top-SCI-Q1 style; the per-domain style contract (writing-principles §0) adapts prose to the domain (humanities/CS/physics/medicine/materials/earth/economics), and a hard anti-engineering-report clause forbids step-listing流水账.

## 125 Science Problems Demo

`problems/125-SCIENCE-PROBLEMS.md` contains 125 science problems as a **"AI for Scientist Anything" demo showcase**. The world's questions go far beyond 125 — the framework is a universal design that handles any number of problems in any domain.

- The 125 problems are a **demo index**, not a complete problem bank
- The framework supports any number of problems (auto-discovered via the `problems/` directory)
- Q-id format is flexible; rigid naming is not required

## FAQ

### Q: Which disciplines does SciForge-OSS support?
A: All disciplines. Physics, mathematics, computer science, medicine, economics, education, materials science, earth science, atmospheric science, astronomy, chemistry, engineering, sensors, optoelectronics — any scientific domain.

### Q: Are the 125 problems required?
A: No. The 125 science problems are a "AI for Scientist Anything" demo showcase. The framework supports any number of problems in any domain.

### Q: Does it need multiple AI models to run?
A: No. SciForge-OSS uses a **structured self-review** mode — the same agent switches roles (researcher→reviewer→adjudicator) for adversarial review; no cross-model collaboration needed.

### Q: How to run a complete scientific-problem study?
A: Execute `/auto-pipeline "Q001: problem description" — effort: max`; it auto-completes the 21-phase DAG loop.

### Q: What format is the output paper?
A: Unified `elsarticle` LaTeX format, compilable to PDF. Theory papers use the theory structure (Main Results + Proofs); experimental papers use the standard structure; survey papers use the taxonomy structure. All compile to a zero-warning PDF.

### Q: How to contribute a new skill?
A: See [CONTRIBUTING.md](CONTRIBUTING.md). All skills are pure Markdown files following a unified frontmatter format.

## License

This project is licensed under MIT. See [LICENSE](LICENSE).

---

**SciForge-OSS — AI for Scientist Anything**
