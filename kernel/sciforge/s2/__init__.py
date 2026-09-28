"""ScientistTwo parity layer (v1.7.0).

Faithful re-implementation, as *code*, of the load-bearing mechanisms in
Google's ScientistTwo (arXiv:2609.19644) — the parts that made their run a
measured result instead of an aspiration:

- ladder      — Subset→Full-Set experiment ladder with the 3-state Critic
                {BAD | GOOD | ENGINEER} (Engineer rounds capped at 2, GOOD
                requires strict full-set improvement over the baseline).
- ideas       — seed ranking + idea evolution trace with the exploration
                guarantee (every evolution round force-mixes >=1 unexplored
                seed, so the loop cannot collapse into a local optimum).
- ablation    — Ablation Planner ledger (5-6 plans) + AblCritic with the
                strict "new must strictly beat old" state rule.
- reviewloop  — score-driven rebuttal (score < 8 => rebuttal plan, <=2 rounds)
                + Meta-Review {ACCEPT | REFINE}.
- calibration — anchor calibration: score known-quality papers first, map our
                panel scores onto the human-anchor scale before judging.
- audit       — completeness audit: reward-hacking arithmetic scan +
                method-section vs implementation token parity.

All modules are stdlib-only (the kernel contract); they are imported by
gate scripts (scripts/s2_*_gate.py), by the review panel (review.py /
pipeline._native_review) and by host skills through the bundles.
"""
from . import (ablation, audit, calibration, headline, ideas, ladder,  # noqa: F401
               monitor, reviewloop)

__all__ = ["ladder", "ideas", "ablation", "reviewloop", "calibration", "audit",
           "monitor", "headline"]
