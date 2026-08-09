# SciForge-OSS Evaluation Harness (v1.4.0)

Phase-level end-to-end evaluation driver: runs the auto-pipeline with an
external model fleet (default: `deepseek-v4-flash-0731` through the Aliyun
MaaS gateway), keeps checkpoint/resume semantics identical to the v6.0
RUNSTATE contract, and gates every phase structurally.

**Division of labor (hard rule):** the fleet *executes* phases; the harness
*dispatches, gates, checkpoints*; humans/lead model *fix the skills*. The
harness never does research.

## Dependencies (full list — install all before running)

Everything except the model gateway is already required by the pipeline
itself (see `scripts/plotting/INSTALL.md`); repeated here so the eval loop is
reproducible on a bare machine.

| Dependency | Why the eval needs it | Install |
|---|---|---|
| Python ≥ 3.10 | harness + validators + plotting | system / conda |
| Node.js ≥ 18 + Claude Code CLI | headless phase agents (`claude -p`) | `npm install -g @anthropic-models... claude-code` (mirror: `--registry=https://registry.npmmirror.com`) |
| Model gateway env | fleet model dispatch | a Claude Code config dir whose `settings.json` env block sets `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_MODEL=<fleet model>`; point the harness at it via `SCIFORGE_EVAL_CONFIG_DIR` (default `/root/.claude-ds`). **Secret hygiene: tokens/keys live ONLY in that out-of-repo config dir — never commit them to this repo or write them into skill/script files.** The harness refuses to dispatch if the config dir's pinned model disagrees with `--model` |
| texlive (pdflatex/latexmk/bibtex) | Phase 13 compile gate | `apt install texlive-latex-base texlive-latex-extra texlive-science texlive-publishers texlive-bibtex-extra latexmk` |
| matplotlib / numpy / sympy / Pillow | experiments + figures + `--doctor` | `pip install matplotlib numpy sympy pillow` |
| d2, graphviz, rsvg-convert (+ inkscape/svgo optional) | figure engines | see `scripts/plotting/INSTALL.md` (per-OS commands + CN mirrors) |
| mihomo (or any HTTP proxy) | arXiv/S2/CrossRef/OpenAlex access from CN networks | `mixed-port: 8099`, `mode: rule`; start before Phase 1b/4a: `setsid /usr/local/bin/mihomo -d ~/.config/mihomo &`; skills carry the `http_proxy=http://127.0.0.1:8099` contract |
| pytest | the harness reuses the repo test gate | `pip install pytest` |

Check readiness: `sciforge tools-check` + `python3 scripts/plotting/render_figure.py --doctor`.

## Usage

```bash
# 1. initialize a workspace from a problem seed
python3 scripts/eval/sciforge_eval.py init /path/to/runs/Q-XXX --problem-file seed.md

# 2. inspect
python3 scripts/eval/sciforge_eval.py status /path/to/runs/Q-XXX   # RUNSTATE + gate preview
python3 scripts/eval/sciforge_eval.py next   /path/to/runs/Q-XXX   # print next phase packet

# 3. execute (each call = one phase = one clean headless agent)
python3 scripts/eval/sciforge_eval.py run     /path/to/runs/Q-XXX [--model M] [--dry]
python3 scripts/eval/sciforge_eval.py run-all /path/to/runs/Q-XXX [--model M]

# 4. adversarial review of the finished paper
python3 scripts/eval/sciforge_eval.py judge /path/to/runs/Q-XXX [--model M]
```

Model override: `--model` flag or `SCIFORGE_EVAL_MODEL` env (default
`deepseek-v4-flash-0731`).

## Checkpoint / resume / restart semantics

- `run` always continues from `{ws}/.sciforge/RUNSTATE.json`. A passing phase
  advances `current_phase`; a failed gate sets `status=paused_blocked` and
  records the exact missing artifacts in `next_action`.
- **Fix and continue:** repair the skill or hand-fix the workspace, set
  `RUNSTATE.json` `status` back to `"running"`, rerun — the phase is retried
  from the top (artifacts are overwritten by the phase contract).
- **Restart from scratch:** delete the workspace directory and `init` again.
- Phase transcripts: `{ws}/.sciforge/logs/phase_<id>.log` (stdout+stderr of
  the headless agent; `claude -p` buffers output until the phase ends).

## Phase gates

Structural, cheap, stdlib-only: required artifact existence (per the phase
table in `sciforge_eval.py`) + `validate_verdicts.py` over
`{ws}/.sciforge/verdicts/`. They catch contract violations, not science
quality — science quality is the judge's job.

## Judge contract (EI-conference / general-journal line)

`judge` runs an adversarial reviewer ("try hard to REJECT") over
`paper/main.tex`, figures, claims, and citation-audit verdicts. Output:
`.sciforge/verdicts/EVALUATION_REVIEW.json` with six 0-10 dimensions
(novelty_and_positioning, methodological_soundness, experimental_rigor,
claim_evidence_alignment, writing_and_structure, reproducibility),
`fatal_flaws[]`, `required_revisions[]`, `overall`, `verdict ∈
{ACCEPT, REVISE, REJECT}`. **Accept line: `overall ≥ 6` AND `fatal_flaws`
empty**; human has the final word (model self-scoring never counts as
acceptance — CRUX lesson).

Known judge biases and mitigations: same-model-family judging → adversarial
prompt + structured fatal-flaw list + human final review; rubric anchoring →
dimensions map to the pipeline's own gates so a paper cannot score high on
the rubric while failing a repo gate.

## Hard rules enforced on every phase (also in the prompt packet)

1. Citations: REAL papers only, verified via arXiv/Semantic Scholar/CrossRef.
2. Experiments: ACTUALLY EXECUTED (code runs; no imagined numbers).
3. Template (elsarticle) and figure palette/audit contract: never modified.
4. Human checkpoints: auto-approved in eval mode, logged to
   `.sciforge/APPROVAL_LOG.txt` with `approver=eval-harness`.
5. The phase agent never writes `RUNSTATE.json` (harness-owned).
