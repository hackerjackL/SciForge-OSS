# SciForge-OSS

> **[English](README.md)** | **[中文](README.zh.md)**

[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.7.2-green.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub](https://img.shields.io/badge/repo-gitcode-blue)](https://gitcode.com/GewisLab/SciForge-OSS)
[![AI for Science](https://img.shields.io/badge/AI%20for-Science-ff69b4)](https://gitcode.com/GewisLab/SciForge-OSS)

> **AI for Scientist Anything** — a Skill-driven universal research runtime: **Skill Library (pure Markdown) + Runtime Kernel (code-enforced control loop) + RSI evolution layer**.
>
> The knowledge layer keeps its spirit: **the skills are pure Markdown** — no IDE-specific syntax, consumable by any agent that can read files (Claude Code, Cursor, Trae, Codex…). The 1.5.0 change is the split, and v1.6.0 hardens it into a verifiable evidence chain (kernel-enforced experiment security scan, TDAL joint confidence, fantasy 5-gate, Arb certified intervals, sentence-level citation support, SMOKE gate, injection sanitizer, rate limiter, dual-timer): **what to do stays in Markdown; how it is enforced moves into code**. v1.7.0 adds the **ScientistTwo parity layer** — the mechanisms behind Google's arXiv:2609.19644 result, reimplemented as open code: subset→full-set experiment ladder with the 3-state Critic (6c boundary gate), 5–6-plan ablation ledger with the strict AblCritic (phase-10 gate), score<8 rebuttal loop + Meta-Review {ACCEPT|REFINE} with anchor-calibrated review scores, reward-hacking + method↔code completeness audit at wrap-up, exploration-guaranteed idea evolution, and the CPU-only `bench/s2demo` sub-bench in their mold. v1.7.1 adds the **AAR anti-Goodhart layer** (patterns ported from Anthropic's arXiv:2608.28945): a fail-closed pre-execution integrity monitor (D1/D2/D3) at the experiment boundary, geometric-mean headline metrics, and results-free pre-registration — plus figure fixes and the evidence-based S2 disclosure voice, all driven by a two-round five-domain ARC-Bench evaluation. The optional `kernel/` (Python ≥3.10, stdlib-only) runs the 21-phase DAG as a real state machine with event-sourced resume, mechanical gates, human checkpoints as code, multi-backend providers, a cross-model review panel, and a recursive skill-library evolution loop. **No UI** — headless CLI (`sciforge run …`) or host-agent mode.
>
> Two ways to use: **(A) skills-only** (inside any AI agent: `/auto-pipeline "problem"`) — unchanged from before; **(B) skills + kernel** (`sciforge run --workspace … --host claude`) — the pipeline can no longer silently skip a gate, survives process death, and gets measurably better with every run (RSI).
>
> SciForge is a **fully autonomous research system**, not a problem-solving benchmark: the human supplies ONE research question (any domain), and the pipeline runs end-to-end from idea discovery to submission-ready paper.

---

## Table of Contents

- [What is this](#what-is-this)
- [Runtime kernel (v1.5.0)](#runtime-kernel-v150)
- [RSI: the skill library evolves itself](#rsi-the-skill-library-evolves-itself)
- [Installation](#installation)
- [Architecture: DAG-driven research loop](#architecture-dag-driven-research-loop)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Quality gates](#quality-gates)
- [Full-domain support](#full-domain-support)
- [Verification paths: four routes](#verification-paths-four-routes)
- [Multi-domain examples](#multi-domain-examples)
- [Core design principles](#core-design-principles)
- [Figure toolchain](#figure-toolchain)
- [Acknowledgments](#acknowledgments)
- [Stargazers over time](#stargazers-over-time)
- [License](#license)

## What is this

**SciForge-OSS** is a pure-Skill-driven **universal AI Scientist framework**. Its *method* is domain-agnostic — one pipeline, no discipline branches — and it has been exercised across physics, mathematics, computer science, life science, medicine, economics, education, materials, earth science, and more. Its *capability envelope*, stated honestly, is **code-runnable science**: any domain whose methodology can be carried out as code, data, and literature work on a commodity Linux machine or GPU cluster.

**Core philosophy**: Domain-Agnostic *method*. The framework itself hardcodes no domain knowledge; all domain-specific methodology is handled by the agent's runtime reasoning — expressed as programs, numerical/symbolic computation, and retrieved evidence.

### Scope & capability boundary (v1.4.0 — honest positioning)

- **In scope (v1.7.1 restatement — "code is science")**: every discipline whose evidence is producible as code/data/literature on one machine or cluster — humanities, social sciences, natural sciences, engineering alike: numerical & symbolic simulation (NumPy/SciPy/SymPy/Julia), ML & statistical estimation, causal inference, econometrics & metrology, agent-based/ODE-PDE models solved in code, PINN/surrogate modelling, computer vision & NLP, atmospheric/pollution modelling, optical-sensor simulation, financial forecasting, smart-education analytics, embodied-AI & LLM/RSI/auto-research studies, edge computing, and web-search-augmented qualitative analysis (retrieve → reason → write → figure). Computational biology (genome-scale models, simulation) is in scope as code-runnable science.
- **Out of scope**: **wet-lab / clinical biomedicine** (evidence that demands physical experiments or patient data), and any domain whose core evidence demands **proprietary or GUI-bound solvers** (commercial CFD/FEA suites, optical-instrument bench software) or **physical hardware**. If such a method reduces to a scriptable, open, or code-callable pipeline (OpenFOAM/Julia PDE instead of GUI CFD), it re-enters scope; the GUI-only workflow itself does not.
- **COMSOL (v1.7.1 positioning)**: not a first-class domain here. COMSOL enters only *jointly* — as simulation data feeding PINN/surrogate or materials-prediction studies — and a dedicated COMSOL interface/MCP is the planned integration path; "run COMSOL for me" requests are refused by `/intake-triage`.
- This is a statement about the *evidence-producing instrument*, not about intelligence: the same pipeline reasons about any field, but it produces evidence only where a machine-executable method exists.

**OSS = Open Single-question Stream** — single-question execution: each invocation processes one Q-id and does not auto-iterate all questions; one universal pipeline for all domains (no overlays, no discipline branches); the agent's runtime reasoning handles domain methods; a single `senior-reviewer-agnostic` persona; a single unified `elsarticle` template; four optional verification routes (theory-only / computational / theory+experiment / qualitative); INV-G1 as the sole invariant (PROBLEM_ANCHOR_FREEZE, universal).

SciForge-OSS distills **4 universal meta-skills**, handling any problem with one invariant set:

| Meta-skill | Role | Description |
|------------|------|-------------|
| **Dynamic Sandbox** | Compute engine | Run arbitrary Python/Julia scientific computation (NumPy/SciPy/SymPy) — numerical sanity check |
| **Dynamic Tooling** | Tool factory | When tools are insufficient at runtime, dynamically write and register temporary tools |
| **Universal Retrieval** | Literature search | Multi-source academic search (arXiv/S2/CrossRef/PubMed/Web/OpenAlex) + 3-layer anti-hallucination verification |
| **Unified Plotting** | Figure rendering | Structured data → publication-quality vector figures (PDF+SVG); dopamine palette (Layer 1, CVD-verified high-saturation) + viridis/magma/cividis data colormaps (Layer 2) |

## Runtime kernel (v1.5.0)

`kernel/` is a **code control plane** for the skill library (Python ≥3.10, stdlib-only — the only extra pip dep is pytest). Skills stay the single source of *method*; the kernel is where *control* lives:

| Capability | Mechanism |
|---|---|
| **State machine** | `kernel/config/phasegraph.json` encodes the 21-phase DAG, loopbacks L1–L13 with budgets, per-phase gates — the orchestrator loop runs as code, not prose |
| **Event-sourced resume** | `.sciforge/events.ndjson` (append-only) + `RUNSTATE.json`; a dead process is detected via stale lockfile and **replays from the exact boundary** (kill -9 verified on macOS) |
| **Gates in control flow** | every boundary runs `validate_verdicts.py --strict`, `security_scan.py`, `gap_gate.py`, `check_figure_embedding.py --require-renderer`, `leakage_scan.py` **as code**; a failing gate blocks the transition — audits can no longer be silently skipped |
| **HITL as data** | checkpoints = `paused_checkpoint` + approval records + `APPROVAL_LOG.txt`; decide with `sciforge approve/deny`, or delegate via `--human-skip` / `--test-mode` |
| **Providers** | role-tiered multi-backend routing (Anthropic/OpenAI-compatible/Ollama; env gateway honored) with real token accounting into `RUN_BUDGET.json` |
| **Hosts** | `--host claude` (Claude Code CLI, reports `total_cost_usd`), `--host codex`, or `manual` bundle protocol (any agent drives via `.sciforge/host/*.done.json`) |
| **Experiments** | sandbox-gated dispatch (Seatbelt on macOS, bubblewrap on Linux), worker pool, background nohup + STATUS.json aggregation, device planning (CUDA/ROCm/NPU/MPS/CPU via `detect_device.py`) |
| **Verifiable evidence (v1.6)** | security_scan enforced at 6b/6c · TDAL joint (tdal_compute.py) · fantasy 5-gate · Arb certified intervals · sentence-level citation support · SMOKE gate · injection sanitizer · rate limiter + 429 cooldown · dual-timer |
| **ScientistTwo parity (v1.7)** | `s2/` package + gates: subset→full ladder & 3-state Critic (`s2_ladder` @6c) · 5–6 ablation plans & strict AblCritic (`s2_ablation` @10) · score<8 rebuttal ≤2 rounds + Meta-Review {ACCEPT\|REFINE} · anchor-calibrated panel scores · reward-hacking + method↔code parity audit (`s2_audit` @wrap-up) · exploration-guaranteed idea evolution · `bench/s2demo` (CPU, numpy-only) |
| **Research-OS layer (v1.7.2)** | XScientist-ARA adapted: content-addressed experiment nodes + `sciforge fork` (resume from any node, never cold-start) + claim→node anchors (claim_anchor_gate blocks drift) + SCION-REP run plans (fallback conditions, off-plan recovery = contract violation) + semantic memory (`memory build --semantic`, verified facts) + batch active search (`sota next -k`) + multi-source daemon scheduling (`SOURCES.json`) |
| **SOTA hill-climb + failure memory (v1.7.1)** | `sota.py` driver: declared incumbent → variant proposals seeded by the cross-run lesson index (`sciforge memory build/query`) → per-iteration geomean closed-fraction headline with capability-floor & regression-CI invalidation → plateau/budget stop. `completion_gate` makes S01-class lying reports physically impossible at wrap-up; `submission_ready` tiers the manuscript READY / MINOR_REV / MAJOR_REV / NOT_READY against the Zone-2 bar |
| **Constraint tiers (v1.7.1)** | `--discipline strict|balanced|lean`: severity ∝ consequence × post-hoc undetectability. lean keeps only fabrication/leakage/ladder/integrity/citation/compile-ERROR hard; cosmetic checks (warnings, page bands, counts) disclose instead of looping back — no negative-optimization tax on strong models |
| **Daemon** | `sciforge serve` — headless queue + loopback HTTP (:4510) for overnight server runs; no GUI anywhere |

```bash
sciforge run --workspace ./runs/Q001 --problem "your question" --host claude --loop
sciforge run --workspace ./runs/Q001 --problem "..." --discipline lean \
             --claim-mode sota                     # strong-model host + SOTA target
sciforge status --workspace ./runs/Q001
sciforge resume --workspace ./runs/Q001 --loop     # after crash: replays events, continues
sciforge approve --workspace ./runs/Q001 idea-pick # human checkpoint
sciforge memory build && sciforge memory query "bootstrap coverage heavy tails" -k 5
sciforge sota next --workspace ./runs/Q001         # hill-climb: next variant proposal
sciforge sota next --workspace ./runs/Q001 -k 3        # batch active search (3 parallel proposals)
sciforge sota record --workspace ./runs/Q001 --variant v2 --legs legs.json
sciforge fork --workspace ./runs/Q001 --node n003 --out ./runs/Q001B   # resume from an experiment node
sciforge memory build --semantic && sciforge memory query --semantic "linear ceiling"
sciforge doctor                                    # environment self-check
```

## RSI: the skill library evolves itself

Completed runs emit signals (loopback counts, gate rejections, `LESSONS.json`, event log). `sciforge evolve` turns them into **SKILL.md patch candidates** and searches for the best one with a real optimizer — PUCT tree or MAP-Elites islands — scoring each candidate with **hybrid gates**: mechanical CI / schemas / golden regression (hard-zero on failure) + a frozen-rubric LLM judge (discrimination). Defenses absorbed from openJiuwen/ScienceDiscovery and AI-Scientist v2, live-verified:

- **Three-shard** rollout/gate/**held-out test** — a reported improvement cannot be inflated by the search itself
- **Pre-flight probe** — a scorer that cannot separate good from corrupt patches is rejected before spending budget
- **Scorer freeze** — candidates may never edit `tests/`, `schemas/`, validators, or the rubric itself
- **Freeze + extensions** — staged skill packages are read-only (`0444` + package hash); evolution output lands in `skill-extensions/`
- **Human merge** — `sciforge submit` applies the winner only after the full `ci_check` gate passes; a failing post-merge check **auto-rolls-back** (observed live on first loop)

```bash
sciforge evolve --workspace ./runs --proposes ./patches.json --budget 8 --algorithm puct
sciforge submit --workspace ./runs evo_123456   # human-authorized merge, full CI gate
sciforge daily  --workspace ./runs              # plain-text digest (print/push anywhere)
```

## Deepen mode & SCI body voice (v1.5.0 wave 2)

- **`mode=deepen`** — the third first-class mode: raise an existing paper's evidential
  depth and **experimental fairness** WITHOUT touching its innovation structure
  (claim/contributions/method identity are frozen; violating them is `BLOCKED`).
  The fairness checklist (identical compute budget, frozen data splits, seed policy,
  hyperparameter budget parity, metric identity, effect size + CI everywhere,
  multiple-comparison control) is machine-checked by `scripts/fairness_gate.py` →
  registered `FAIRNESS.json` (22nd verdict).
- **SCI body voice** (`writing-principles §0.6`) — the manuscript body is written for
  the reader of the science: **zero apologies, zero defensive framing**; hedges are
  legal only as bounded regime statements; Limitations is a regime ledger, not a
  confession. Enforced by `leakage_scan.py` class K (machine-checked, zero tolerance
  in body sections).
- **DeepMind pattern fusion** (`docs/DEEPMIND_FUSION.md`) — cascading multi-evaluator
  evolution (AlphaEvolve), generate-verify-reinforce (AlphaProof), active-learning
  retrain (GNoME), neuro-symbolic split (AlphaGeometry).
- **Claude Code seamless**: the package installs a thin `sciforge` skill adapter
  (`~/.claude/skills/sciforge/`) + `CLAUDE.md` project memory — invoke `/sciforge` or
  `/auto-pipeline` directly inside Claude Code.

## Installation

> **v1.4.0**: literature-first gap chain (ideas anchor to mined literature gaps), evidence-norm domain learning, `.sciforge/` two-tier workspace with RUNSTATE long-horizon resume and routing-aware N/A verdicts. Pure Skill package + optional toolchain. The skills themselves are pure Markdown that any Markdown-capable AI agent can consume directly; fully running through (figures / literature / compile / experiments) needs the optional toolchain, see "Toolchain (optional but recommended)" below.

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

The skills themselves are pure Markdown, but fully running through (figure rendering / literature search / LaTeX compile / experiment execution) needs the optional tools below. `sciforge tools-check` reports missing items; `sciforge tools-install` installs them in one shot. The Python side is a single file at the repo root: `pip install -r requirements.txt` (core: matplotlib/numpy/Pillow; recommended: SciencePlots). The full cross-platform "arsenal" (d2/texlive/rsvg/… with per-OS commands) is in [scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md).

> 📊 **Figure toolchain**: all figures (data plots, architecture/process/mechanism diagrams — every discipline) are produced through ONE unified entry point, `scripts/plotting/render_figure.py` (12 engines: matplotlib / d2 / graphviz / tikz / asymptote / typst / diagrams / blockdiag-family / mermaid / pikchr / hand-assembled SVG / composite multi-panel — single pipeline, never parallel tools; PDF+PNG dual output + embedded Nature-level audit). **Cross-platform: Linux / macOS / Windows** (WSL2 recommended on Windows; fonts auto-discovered per platform, no machine-specific paths). Full dependency list, per-OS install commands, mirrors, fonts and not-adopted tools: **[scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md)**. Environment self-check: `python scripts/plotting/render_figure.py --doctor`.

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

**Why not drawio / blender**: drawio-desktop is a GUI app, not headless-friendly; Blender headless rendering produced black frames that could not be reliably fixed. mermaid-cli (`mmdc`) IS supported (auto `--no-sandbox` under root); pikchr, resvg and cairosvg are also integrated. Full engine ledger with evaluation notes: [scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md). If a human later wants to hand-edit a diagram in drawio's GUI, they can import the d2/dot-produced SVG — but the pipeline itself uses headless tools only.

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
     │  ── Experiment execution layer ── non-theory-only path ──
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
Phase 15.5: /publishability-score — 6-dim score (main-experiment-logic is the gating axis) (MUST)
Phase 16: Final assembly + cleanliness audit (project-architecture-contract)
```

**Fallback contract (bounded 3 rounds)**: each phase with a ↻ falls back to the relevant prior phase on failure, bounded to 3 rounds per failure-type. Past round 3 → BLOCKED + surfaced to the human. **BA (Backtracking-After)**: when an experiment falsifies the idea's core claim (Phase 6c full FAIL after toy PASS / Phase 8 FATAL contradiction / Phase 14 kill-argument sustained), the orchestrator backtracks to Phase 2 to regenerate the idea (bounded 2 rounds) — distinct from phase-internal 3-round fallback.

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
├── bin/sciforge.js                  # local CLI (init / tools-check / tools-install / run·resume·approve·evolve·serve → kernel)
├── bench/s2demo/                    # v1.7 ScientistTwo-mold CPU demo sub-bench (4 numpy tasks + ladder harness)
├── kernel/                          # v1.5.0 runtime kernel (Python >= 3.10, stdlib-only control plane)
│   ├── config/phasegraph.json       # 21-phase DAG as executable config (loopbacks, gates, budgets)
│   ├── config/providers.json        # role-tiered multi-backend model routing
│   ├── config/evolve.json           # RSI gate battery (CI + schemas + golden)
│   └── sciforge/                    # pipeline.py state machine · state.py events+RUNSTATE · gates.py · approvals.py · execution.py (sandbox+pool) · providers.py · review.py (cross-model panel) · evolve.py (PUCT+MAP-Elites) · propose.py · skills_pack.py (frozen packages) · litcache.py · proxy.py · memory.py · daemon.py · golden.py · cli.py
├── scripts/
│   ├── plotting/                    # figure toolchain (single entry point)
│   │   ├── render_figure.py         # unified renderer — 12 engines, one pipeline, embedded audit
│   │   ├── sciforge_style.py        # dopamine design tokens (single source of truth)
│   │   ├── figure_audit.py          # A1–A10 Nature-level audit (embedded)
│   │   └── INSTALL.md               # cross-platform replication manual
│   ├── validate_verdicts.py         # verdict JSON schema validator (stdlib-only)
│   ├── security_scan.py             # static pre-dispatch scan for agent-authored experiments
│   ├── s2_ladder_gate.py            # v1.7 ScientistTwo subset→full ladder gate (phase 6c)
│   ├── s2_ablation_gate.py          # v1.7 ablation ledger gate (phase 10)
│   ├── s2_audit.py                  # v1.7 completeness audit (wrap-up: reward-hacking + method↔code parity)
│   ├── ci_check.py                  # single CI entry point (links/versions/plotting/tests)
│   └── verifiers/                   # external artifact verifiers (review ledger, paper audits)
├── tests/                           # 300+ pytest cases (palette, audits, validator, e2e smoke, verifiers)
├── fixtures/e2e_minimal/            # minimal end-to-end fixture (toy experiment + full verdict trail)
├── .workflow/ci.yml                 # AtomGit Actions CI (same gate as ci_check.py)
├── skills/
│   ├── orchestrator/
│   │   └── auto-pipeline/SKILL.md   # the single entry orchestrator (21-phase DAG loop)
│   ├── meta-skills/                 # 8 universal meta-skills
│   │   ├── idea-discovery/          # MCTS-enhanced idea generation (4 perspectives incl. empirical)
│   │   ├── universal-retrieval/     # literature search + 3-layer anti-hallucination (mihomo proxy)
│   │   ├── unified-plotting/        # publication-quality figures (PDF+SVG dual; 16:9; d2 for diagrams)
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
│   │   ├── experiment-execution/    # toy + full + background dispatch (device auto-detect)
│   │   ├── theory-derivation/       # SymPy symbolic derivation + machine verification
│   │   ├── leakage-audit/           # Type I + Type IV audit
│   │   ├── logic-verification/      # 6-dim logical consistency audit
│   │   ├── result-to-claim/         # 3-fidelity claim gate
│   │   ├── invariant-check/         # INV-G1 verification
│   │   ├── kill-argument/           # anti-self-deception
│   │   ├── method-registry/         # method registry + hash lock
│   │   ├── citation-audit/          # final 3-layer citation verification
│   │   ├── adversarial-falsification/  # adversarial falsification
│   │   ├── publishability-score/    # 6-dim publishability score
│   │   └── rebuttal/                # point-by-point rebuttal letter after rejection
│   └── shared-references/           # shared contracts (discipline-agnostic)
│       ├── artifact-registry.md     # single source of truth for cross-skill artifacts
│       ├── output-protocol.md       # single authority for the workspace directory tree
│       ├── schemas/                 # JSON Schemas for every machine-readable verdict
│       ├── paper-modes.md           # 5-mode selector (theory/experiment/computational/survey/hybrid)
│       ├── figure-quality-contract.md  # 16:9, PDF+SVG dual, Nature readability, d2 pipeline
│       ├── project-architecture-contract.md  # GitHub-style project tree + cleanliness audit
│       ├── background-dispatch-protocol.md     # >5min background dispatch
│       ├── citation-discipline.md   # 3-layer anti-hallucination
│       ├── writing-principles.md    # academic writing + per-domain style contract
│       ├── discipline-writing.md    # universal section-by-section guide
│       ├── color-themes.md          # Dopamine (Layer 1) + viridis/magma/cividis (Layer 2)
│       ├── venue-profiles.md        # single elsarticle template spec
│       ├── multi-fidelity-evaluation.md  # universal Low/Mid/High
│       ├── effort-contract.md       # lite/balanced/max/beast
│       ├── engineering-grounding-contract.md  # 5-dim EG axis
│       └── ... (31+ shared references)
└── templates/
    └── (paper-writing/templates/default/ — unified elsarticle skeleton)
```

## Quality gates

The pipeline is guarded by machine-checkable gates, not prose promises.

| Gate | What enforces it |
|------|------------------|
| **Verdict schemas** | every machine-readable verdict in a run's `.sciforge/verdicts/` must validate against `shared-references/schemas/*.schema.json` — `scripts/validate_verdicts.py` runs at every phase boundary and at wrap-up (misspelled/omitted fields are caught) |
| **Run budget ledger** | `.sciforge/verdicts/RUN_BUDGET.json` caps wall-clock / API cost / PIVOT / BA rounds per effort level; the orchestrator books every boundary and BLOCKs + escalates to the human on breach |
| **KILL checkpoint** | killing an idea pauses for human confirmation by default (`human_skip=true` or `kill_checkpoint=false` to delegate) |
| **Experiment security gate** | agent-authored full-experiment scripts pass `scripts/security_scan.py` before dispatch (credential access / env exfiltration / destructive ops / non-allowlisted egress → BLOCKED) |
| **Figure contract** | unified renderer + embedded A1–A10 Nature-level audit; composite figures deliver true-vector LaTeX assembly (`composite.tex`), raster previews are audit-downgraded |
| **ScientistTwo gates (v1.7)** | `scripts/s2_ladder_gate.py` at 6c (no promotion without strict full-set improvement, engineer rounds ≤2) · `scripts/s2_ablation_gate.py` at phase 10 (5–6 plans, monotone ledger) · `scripts/s2_audit.py` at wrap-up (gain arithmetic + split discipline + method↔code parity ≥80%) — see `skills/shared-references/s2-protocol.md` |
| **Repo CI** | `scripts/ci_check.py` (AtomGit Actions + pre-commit): markdown link scan, repo-wide version consistency, plotting `--doctor`, and the full pytest suite incl. the e2e smoke fixture |

Developer quick checks: `python3 scripts/ci_check.py` · `python3 -m pytest tests/ -q` · `python3 scripts/plotting/render_figure.py --doctor`.

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

## Figure toolchain

Publication-grade figures are produced by ONE unified entry point — `scripts/plotting/render_figure.py` (Phase 11 of the pipeline), with **15 engines behind a single chain (incl. declarative recipe + method-template engines)** (never parallel tools): matplotlib (data), d2, graphviz, TikZ, Asymptote, Typst, diagrams, blockdiag-family, mermaid, pikchr, hand-assembled SVG, and the **composite multi-panel engine** (Nature-style (a)(b)(c)… panel figures, panel cap 9, SCI Q1 composition rules).

- **Dual output**: vector PDF (LaTeX embed) + 300 DPI PNG (agent review)
- **Embedded Nature-level audit (A1–A10)**: readability floors, dopamine palette (C* ≥ 30 + pairwise CVD ΔE ≥ 15 numerically validated), 16:9 default, complexity floors (icon density / edge density), visual richness, **brand-leak guard** (figures are paper figures, never tool posters), **zero text overlap** with actionable fix suggestions
- **Two-tier visual review**: vision-capable host agents self-review the PNG against a 9-item checklist (no external API — the host's native vision is the reviewer); text-only hosts degrade to the mechanical audit
- **Journal column-width presets**: `--width-preset nature-single|aaai-double|...` (14 venues)
- **Cross-platform**: Linux / macOS / Windows — fonts auto-discovered per platform, no machine-specific paths; see [scripts/plotting/INSTALL.md](scripts/plotting/INSTALL.md)

## Acknowledgments

The development of SciForge-OSS would not have been possible without the following contributions, which we gratefully acknowledge:

- **Luo H. W.** (leader of GewisLab) — project initiation, core research ideas, and overall architecture design.
- **Yang J. T.** — lead developer, responsible for the implementation and engineering of the framework.
- **Yang J. T., Lu Y. H., Li L. S., Jia W. H., Qiu Y. M., Zhang W. B., Wang C. Y., Fan L. X., and Zhao J.** (in no particular order) — generous provision of computational resources (API tokens), which sustain the continuous self-iteration, optimization, and maintenance of this repository.

We also thank all contributors who have improved SciForge-OSS through issues and pull requests.

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). It is free for personal and noncommercial use (research, study, education, charity, etc.); commercial use requires a paid commercial license from GewisLab.

## Stargazers over time

![Stargazers over time](https://atomgit.com/GewisLab/SciForge-OSS/starcharts.svg?variant=adaptive)

---

**SciForge-OSS — AI for Scientist Anything**
