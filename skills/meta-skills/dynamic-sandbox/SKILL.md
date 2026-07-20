---
name: dynamic-sandbox
type: reference-skill
role: computation-sandbox
---

# Meta-Skill: Dynamic Execution Sandbox

## Use When

当 AI scientist 需要对任何科学问题进行数值计算、符号验证、仿真或数据分析时——无论学科——使用此 skill。

典型 prompt：
- "验证这个数学推导"
- "计算这个方程"
- "run numerical simulation"
- "verify this formula with actual numbers"
- "generate synthetic data for this hypothesis"

这是替代传统"做实验"的核心元技能。任何科学问题——从量子力学到教育统计——最终都归结为数学方程、矩阵运算或统计分析，这个沙盒都能处理。

## Job

提供一个预装了完整科学计算栈的 Python/Julia 沙盒环境。AI scientist 针对问题现场编写验证代码；此 skill 负责执行代码、捕获输出/错误、返回结构化结果。

**skill 不理解科学——它只运行代码并返回数据。**

不可妥协的目标：
1. **每次计算都可复现**——代码 + 随机种子 + 输入数据都保留
2. **每个结果都可验证**——输出是结构化的（JSON/CSV），不只在终端输出中
3. **错误被捕获，不被吞没**——失败的运算返回完整 traceback
4. **沙盒没有学科偏见**——PDE 求解器和统计检验同等对待

## 预装库

### Python（默认）
```
numpy, scipy, sympy, matplotlib, pandas, statsmodels, sklearn,
networkx, itertools, functools, math, cmath, random, json, csv
```

### 按需（代码中检测到自动安装）
```
biopython, rdkit, astropy, qiskit, tensorflow, torch, transformers
```

## 配置

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `language` | enum | `python` | `python` 或 `julia` |
| `timeout` | int | `120` | 每个脚本最大执行秒数 |
| `seed` | int | `42` | 随机种子，保证可复现 |
| `packages` | list | `[]` | 额外 pip 包 |
| `output_format` | enum | `json` | `json` / `csv` / `markdown` |

## Steps

### Step 1: 解析计算请求

提取：
1. **领域上下文**——什么科学领域（用于库选择，而非逻辑）
2. **计算类型**——符号推导、数值模拟、统计分析、数据转换
3. **输入数据**——结构化数据、公式或参数
4. **预期输出形状**——数值、矩阵、方程、图表、数据文件

如果请求太模糊（"explore this data"），要求调用者提供具体的计算计划。

### Step 2: 生成沙盒代码

编写一个自包含的 Python 脚本：
- 在顶部设置随机种子
- 导入所有需要的库
- 从 `input.json` 读取输入（如适用）
- 执行计算
- 将结构化输出写入 `output.json`
- 处理边界情况（空输入、除零、收敛失败）
- 包含内联注释解释方法

**代码质量规则：**
- 无交互式图表（使用 `plt.savefig()` 矢量格式）
- 无硬编码路径
- 每个非平凡函数必须有 docstring
- 每个函数至少处理一个错误情况
- 输出结构必须是可解析的，不能是自由文本 print

### Step 3: 执行并捕获

在隔离子进程中运行脚本：
1. 创建会话目录：`sandbox/session_{timestamp}/`
2. 写入 `code.py` 和 `input.json`
3. 用 `subprocess.run(timeout={timeout}s)` 执行
4. 捕获 stdout、stderr 和 return code

**成功时：**
- 读取 `output.json`
- 计算 `code.py + input.json + output.json` 的 SHA-256 hash
- 注册到 `sandbox/MANIFEST.json`

**失败时：**
- 向调用者返回完整 traceback
- 建议 3 个可能的修复（库未安装、语法错误、逻辑错误）
- 不要静默重试——让调用者决定是否修复并重试

### Step 4: 验证输出

对照 Step 1 中声明的预期形状检查输出：
- 如果期望矩阵 → 验证输出是 2D 数组
- 如果期望标量 → 验证输出是数值
- 如果期望图表 → 验证 `artifacts/` 包含非空 SVG 文件

如果验证失败，返回结构化错误。

### Step 5: 返回结构化结果

```json
{
  "status": "success" | "error" | "partial",
  "session_id": "session_20260719_120000",
  "output": { ... },
  "artifacts": ["artifacts/plot.svg"],
  "code_hash": "sha256:...",
  "execution_time_ms": 1234,
  "error": null | { "type": "...", "traceback": "..." }
}
```

## 输出产物

- `sandbox/session_{timestamp}/code.py` — 可复现的脚本
- `sandbox/session_{timestamp}/output.json` — 结构化结果
- `sandbox/session_{timestamp}/artifacts/*.svg` — 矢量图

## 调用下游 skill

- `/dynamic-tooling` — 当标准库不足时，让此 skill 动态创建工具
- `/theory-derivation` — 当需要符号推导时，先调用推导再数值验证

## 共享契约引用

- [effort-contract](../shared-references/effort-contract.md) — 努力等级定义
- [output-manifest](../shared-references/output-manifest.md) — 产物结构契约