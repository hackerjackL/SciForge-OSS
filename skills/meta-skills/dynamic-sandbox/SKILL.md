---
name: dynamic-sandbox
version: 1.2.0
description: "Execute agent-written code in an isolated sandbox for toy experiments and numerical sanity checks. Invoke when experiment-execution or theory-derivation needs to run a script and capture structured output."
type: reference-skill
role: computation-sandbox
---

# Meta-Skill: Dynamic Execution Sandbox

## Quick Reference

- **Purpose**: run Python/Julia scientific computation (NumPy/SciPy/SymPy)
- **Input**: verification script + parameters
- **Output**: structured results (JSON/CSV) + executed code
- **Key**: no GPU, numerical sanity checks only; code + random seed retained

## Use When

Use this skill whenever the AI scientist needs numerical computation, symbolic verification, simulation, or data analysis for any scientific question — regardless of discipline.

Typical prompts:
- "verify this mathematical derivation"
- "compute this equation"
- "run numerical simulation"
- "verify this formula with actual numbers"
- "generate synthetic data for this hypothesis"

This is the core meta-skill replacing traditional "running experiments". Any scientific question — from quantum mechanics to educational statistics — ultimately reduces to mathematical equations, matrix operations, or statistical analysis, and this sandbox handles them all.

## Job

Provide a Python/Julia sandbox environment preloaded with the full scientific-computing stack. The AI scientist writes verification code on the spot for the problem; this skill executes the code, captures output/errors, and returns structured results.

**The skill does not understand science — it only runs code and returns data.**

Non-negotiable goals:
1. **Every computation is reproducible** — code + random seed + input data are all retained
2. **Every result is verifiable** — output is structured (JSON/CSV), not only in terminal output
3. **Errors are captured, not swallowed** — failed operations return the full traceback
4. **The sandbox has no discipline bias** — PDE solvers and statistical tests are treated equally

## Preinstalled Libraries

### Python (default)
```
numpy, scipy, sympy, matplotlib, pandas, statsmodels, sklearn,
networkx, itertools, functools, math, cmath, random, json, csv
```

### On demand (auto-installed when detected in code)
```
biopython, rdkit, astropy, qiskit, tensorflow, torch, transformers
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `language` | enum | `python` | `python` or `julia` |
| `timeout` | int | `300` | Max execution seconds per script (v2.1: aligned with experiment-execution toy's 5min foreground budget, preventing the sandbox's 120s from killing toy runs by mistake) |
| `seed` | int | `42` | Random seed, guarantees reproducibility |
| `packages` | list | `[]` | Extra pip packages |
| `output_format` | enum | `json` | `json` / `csv` / `markdown` |

## Steps

### Step 1: Parse the Computation Request

Extract:
1. **Domain context** — which scientific field (for library selection, not logic)
2. **Computation type** — symbolic derivation, numerical simulation, statistical analysis, data transformation
3. **Input data** — structured data, formulas, or parameters
4. **Expected output shape** — numbers, matrix, equation, plot, data file

If the request is too vague ("explore this data"), ask the caller for a concrete computation plan.

### Step 2: Generate Sandbox Code

Write a self-contained Python script:
- Set the random seed at the top
- Import all required libraries
- Read inputs from `input.json` (if applicable)
- Perform the computation
- Write structured output to `output.json`
- Handle edge cases (empty input, division by zero, convergence failure)
- Include inline comments explaining the approach

**Code quality rules:**
- No interactive plots (use `plt.savefig()` in vector format)
- No hardcoded paths
- Every non-trivial function must have a docstring
- Every function handles at least one error case
- Output structure must be parseable — no free-text prints

### Step 3: Execute and Capture

Run the script in an isolated subprocess:
1. Create session directory: `sandbox/session_{timestamp}/`
2. Write `code.py` and `input.json`
3. Execute with `subprocess.run(timeout={timeout}s)`
4. Capture stdout, stderr, and return code

**On success:**
- Read `output.json`
- Compute the SHA-256 hash of `code.py + input.json + output.json`
- Register in `sandbox/MANIFEST.json`

**On failure:**
- Return the full traceback to the caller
- Suggest 3 possible fixes (library not installed, syntax error, logic error)
- Do not silently retry — let the caller decide whether to fix and retry

### Step 4: Validate Output

Check the output against the expected shape declared in Step 1:
- Matrix expected → verify the output is a 2D array
- Scalar expected → verify the output is a number
- Plot expected → verify `artifacts/` contains a non-empty SVG file

If validation fails, return a structured error.

### Step 5: Return Structured Result

```json
{
  "status": "one of: success | error | partial",
  "session_id": "session_20260719_120000",
  "output": {},
  "artifacts": ["artifacts/plot.svg"],
  "code_hash": "sha256:...",
  "execution_time_ms": 1234,
  "error": null
}
```

## Output Artifacts

- `sandbox/session_{timestamp}/code.py` — the reproducible script
- `sandbox/session_{timestamp}/output.json` — structured results
- `sandbox/session_{timestamp}/artifacts/*.svg` — vector plots

## Invoking Downstream Skills

- `/dynamic-tooling` — when the standard libraries are insufficient, let this skill create tools dynamically
- `/theory-derivation` — when symbolic derivation is needed, invoke the derivation first, then verify numerically

## Shared Contract References

- [effort-contract](../../shared-references/effort-contract.md) — effort level definitions
- [output-manifest](../../shared-references/output-manifest.md) — artifact structure contract
