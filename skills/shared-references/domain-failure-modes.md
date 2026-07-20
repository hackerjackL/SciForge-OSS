# Domain Failure Mode Catalog (SciForge-OSS — Reference)

> **Status**: Reference catalog of domain-specific failure modes. This is NOT a hard-coded classification — the agent uses the domain signature (from `/domain-signature`) to query this catalog and select relevant failure modes.
>
> **Core principle**: Every domain knows how it fails. Economics knows about endogeneity, physics knows about unit mismatch, medicine knows about confounding. This catalog makes that knowledge available to the agent.

## How to Use

1. `/domain-signature` extracts the domain signature from the problem
2. The agent queries this catalog using the signature's `evidence_type` and `methodology_profile`
3. The selected failure modes are added to `/adversarial-falsification` and `/leakage-audit`
4. The agent checks each failure mode against the specific problem

## Failure Mode Catalog

### causal_inference (因果推断类)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **endogeneity** | 解释变量与误差项相关，导致估计有偏 | 经济学、计量、社科 | Hausman test, DWH test | fatal |
| **omitted_variable_bias** | 遗漏重要变量，遗漏变量与解释变量相关 | 经济学、社会学、教育学 | Control for known confounders, sensitivity analysis | fatal |
| **reverse_causality** | 因果方向反了 — Y 导致 X 而非 X 导致 Y | 经济学、流行病学 | Granger causality, lag analysis, instrumental variables | fatal |
| **selection_bias** | 样本选择非随机，处理组与对照组不可比 | 经济学、医学、教育学 | Heckman correction, propensity score matching | fatal |
| **measurement_error** | 变量测量不准，导致 attenuation bias | 经济学、心理学、医学 | Instrumental variables, multiple measures | severe |
| **simultaneity** | X 和 Y 同时决定，无法分离因果 | 宏观经济学、金融 | Simultaneous equations, VAR | fatal |
| **attrition_bias** | 样本流失非随机 | 医学临床试验、教育学 | Attrition analysis, bounds | severe |
| **publication_bias** | 只发表正面结果，meta-analysis 有偏 | 医学、心理学、经济学 | Funnel plot, Egger's test | severe |

### experimental (实验类)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **no_placebo** | 无安慰剂对照，无法排除安慰剂效应 | 医学、心理学 | Check for placebo control | fatal |
| **no_blinding** | 非盲法，实验者/受试者知道分组 | 医学、心理学 | Check blinding status | fatal |
| **insufficient_power** | 样本量太小，无法检测到效应 | 医学、生物学、心理学 | Power analysis, sample size calculation | severe |
| **multiple_testing** | 多假设检验未校正，假阳性膨胀 | 医学、基因组学、心理学 | Bonferroni, FDR, Holm correction | severe |
| **regression_to_mean** | 极端值在重复测量中自然回归 | 医学、心理学、教育学 | Control group, multiple measurements | severe |
| **confounding_by_indication** | 治疗指征本身与结局相关 | 医学、流行病学 | Propensity score, restriction | fatal |
| **lead_time_bias** | 早期诊断导致表面生存期延长 | 医学、癌症研究 | Landmark analysis, adjust for lead time | severe |

### correlational (相关性类)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **spurious_correlation** | 两个无关变量因共同趋势而相关 | 所有领域 | Differencing, detrending, randomization | fatal |
| **ecological_fallacy** | 群体层面的结论不能推广到个体 | 社会学、经济学、流行病学 | Multi-level analysis, individual-level data | fatal |
| **simpson_paradox** | 分层后相关方向反转 | 统计学、社会学、医学 | Stratification, interaction terms | fatal |
| **survivorship_bias** | 只分析幸存者，忽略失败者 | 金融、军事、历史 | Include failures, survival analysis | fatal |
| **confirmation_bias** | 只找支持自己假设的证据 | 所有领域 | Pre-registration, adversarial search | severe |

### derivational (推导类)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **hidden_assumption** | 证明中使用了未声明的假设 | 数学、理论 CS、理论物理 | Assumption audit, step-by-step verification | fatal |
| **circular_reasoning** | 结论已在假设中隐含 | 数学、哲学 | Check assumption → conclusion independence | fatal |
| **quantifier_error** | ∀/∃ 顺序错误，量词范围错 | 数学、逻辑 | Formal verification, counterexample | fatal |
| **division_by_zero** | 推导中除以可能为零的量 | 数学、物理、工程 | Check denominator conditions | fatal |
| **limit_order_error** | 极限的顺序不能交换 | 数学、物理 | Check dominated convergence, uniform convergence | fatal |
| **dimensional_error** | 方程两边量纲不一致 | 物理、工程 | Dimensional analysis | fatal |
| **boundary_condition_error** | 边界条件未验证或错误 | 物理、工程、微分方程 | Check boundary conditions at all limits | severe |

### simulational (模拟类)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **numerical_instability** | 算法不稳定，误差指数增长 | 物理、工程、气候 | Stability analysis, adaptive step size | fatal |
| **convergence_failure** | 迭代算法未收敛到真实解 | 优化、ML、物理 | Convergence criteria, multiple starting points | fatal |
| **discretization_error** | 离散化导致的系统误差 | 物理、工程、气候 | Grid refinement study, error estimation | severe |
| **parameter_tuning_bias** | 参数调优导致过拟合到验证集 | ML、工程 | Cross-validation, separate test set | fatal |
| **seed_dependence** | 随机种子影响结果 | ML、物理模拟 | Multiple seeds, statistical aggregation | severe |

### interpretive (诠释类)

| Failure Mode | Description | Domains | Detection Method | Severity |
|-------------|-------------|---------|-----------------|----------|
| **cherry_picking** | 只选支持论点的证据，忽略反例 | 人文、社科、法学 | Systematic literature review | fatal |
| **anecdotal_evidence** | 以个别案例代替系统证据 | 教育学、心理学、管理学 | Case study limitations, generalizability check | severe |
| **straw_man** | 歪曲对立观点以便驳斥 | 哲学、法学、政治学 | Check if opposing view is accurately represented | severe |
| **ad_hoc_hypothesis** | 为挽救理论添加无根据的假设 | 科学哲学、理论 | Occam's razor, independent testability | fatal |
| **equivocation** | 同一术语在不同语境下含义不同 | 哲学、法学、语言学 | Define all terms, check consistency | fatal |

## How to Extend

Add new failure modes following this template:

```markdown
| **failure_name** | description | domain_tags | detection_method | severity |
```

Keep the catalog focused on **known, well-documented** failure modes. Do not add speculative failure modes.

## Boundaries

- **This catalog is never complete.** New failure modes are discovered as science progresses.
- **The agent must check if a failure mode applies.** Not all failure modes apply to all problems.
- **Failure mode severity is domain-dependent.** What's "severe" in one domain may be "fatal" in another.
- **Do not treat this as a checklist.** Treat it as a reference — the agent uses domain knowledge to decide which modes apply.

## See Also

- [`../meta-skills/domain-signature/SKILL.md`](../meta-skills/domain-signature/SKILL.md) — extracts the domain signature that queries this catalog
- [`../support/adversarial-falsification/SKILL.md`](../support/adversarial-falsification/SKILL.md) — uses failure modes for stress testing
- [`../support/leakage-audit/SKILL.md`](../support/leakage-audit/SKILL.md) — uses failure modes for leakage audit