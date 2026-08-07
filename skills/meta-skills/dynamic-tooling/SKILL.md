---
name: dynamic-tooling
version: 1.1.1
description: "Build custom ad-hoc tools (parsers, converters, small CLIs) the agent needs mid-run that aren't pre-provided. Invoke when no existing tool fits a pipeline step."
type: reference-skill
role: tool-builder
---

# Meta-Skill: Just-in-Time Dynamic Tooling

## Quick Reference

- **Purpose**: 运行时生成临时工具，填补能力缺口
- **Input**: 工具描述 + 接口契约
- **Output**: 可执行的 Python 模块 + 注册信息
- **Key**: 7 种工具模板 (symbolic-reasoner/statistical-modeler/knowledge-graph/formal-verifier/code-synthesizer/data-transformer/text-analyzer)

## Use When

当 AI scientist 遇到标准沙盒库无法处理的计算或数据处理任务时——需要特定领域的工具、适配器或管道——使用此 skill。

典型 prompt：
- "我需要一个处理化学分子式的工具"
- "这个数据格式需要自定义解析器"
- "write a custom tool for this data format"
- "create a graph analysis utility for this specific problem"
- "build a bridge between the sandbox output and the plotting engine"

这是**力量倍增器**元技能：它让系统在运行时自我扩展能力，确保任何科研问题永远不会遇到"工具不可用"的死胡同。

## Job

动态生成、测试并注册一个临时或永久的工具（Python 模块、CLI 封装器、API 适配器或数据管道），填补研究过程中发现的能力空白。工具由 AI 编写，通过执行验证，然后提供给下游 skill 使用。

不可妥协的目标：
1. **每个工具在注册前都经过测试**——最小的冒烟测试必须通过
2. **每个工具都有清晰的接口契约**——输入 schema、输出 schema、错误模式
3. **失败的工具被诊断，不被丢弃**——错误随建议的修复一起返回
4. **工具有作用域**——临时（仅会话）或持久（跨会话复用）

## 配置

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `scope` | enum | `session` | `session`（临时）或 `persistent`（可复用） |
| `language` | enum | `python` | `python` / `julia` / `bash` |
| `smoke_test` | bool | `true` | 生成后是否运行冒烟测试 |
| `max_retries` | int | `2` | 最大生成+测试轮数 |

## Steps

### Step 1: 识别缺口

分析请求，确定：
1. **缺少什么**——特定的库函数、数据格式解析器、可视化适配器、计算管道
2. **为什么现有工具不足**——不支持的数据格式、缺少库、性能要求、领域特定逻辑
3. **工具的作用域**——一次性工具还是可复用组件
4. **依赖项**——工具需要什么库或外部服务

如果缺口可以通过安装标准库（pip install）填补，**不要创建工具**——委托给 `/dynamic-sandbox` 并附带包列表。

### Step 2: 设计工具接口

在编写代码前定义工具的契约：

```
Tool Name: {name}
Purpose: {一句话描述}
Input: {JSON schema 或函数签名}
Output: {JSON schema 或返回类型}
Side Effects: {文件 I/O、网络调用、状态变更}
Error Modes: {可能出错的地方及如何报告}
```

### Step 2b: 工具模板库 (按需加载)

如果请求的工具类型匹配以下模板之一，直接加载模板而非从头生成。模板提供预定义的输入/输出 schema、测试用例和错误处理。

| 模板类型 | 适用场景 | 输入 | 输出 | 技术栈 |
|---------|---------|------|------|--------|
| **symbolic-reasoner** | 数学定理证明、逻辑推导验证 | 数学命题 + 假设集 | 证明步骤 + 验证状态 | SymPy/symengine |
| **statistical-modeler** | 假设检验、回归分析、因果推断 | 数据 + 检验类型 | 检验统计量 + p值 + 效应量 | scipy.stats/statsmodels |
| **knowledge-graph** | 概念映射、文献网络分析 | 概念列表 + 关系类型 | 知识图谱 (JSON/GraphML) | networkx |
| **formal-verifier** | 逻辑命题验证、模型检查 | 逻辑命题 + 推理规则 | 验证通过/反例 | Z3/pysat SMT 求解 |
| **code-synthesizer** | 自动生成验证/模拟代码 | 问题描述 + 参数 | 可执行 Python 脚本 | AST 模板 + jinja2 |
| **data-transformer** | 多源数据格式转换 | 源数据 + 目标格式 | 转换后数据 | pandas |
| **text-analyzer** | 关键词提取、主题建模 | 文本 + 分析类型 | 结构化分析结果 | sklearn/nltk |

**模板使用流程**：
1. 识别请求匹配的模板类型
2. 加载模板的输入/输出 schema
3. 填充模板参数（领域特定的变量名、函数名）
4. 执行 Step 3 生成实现
5. 如果模板不匹配，回退到 Step 2 的通用设计流程

**示例**：用户请求"验证这个数学推导的正确性"
→ 匹配 `symbolic-reasoner` 模板
→ 输入：数学命题 + 假设集
→ 输出：逐步骤验证结果
→ 使用 SymPy 生成验证脚本

### Step 3: 生成实现

将工具编写为自包含的 Python 模块：
- 一个单一的入口函数（或带 `__call__` 的类）
- 类型注解的参数和返回值
- 带使用示例的 docstring
- 所有已识别错误模式的错误处理
- 无硬编码路径或凭据
- 版本字符串（`__version__`）

**代码质量规则：**
- 每个工具最多 200 行（如果更大，拆分为子模块）
- 注册前必须通过 `py_compile`
- 不得从沙盒或已安装库之外导入
- 除非明确授权，否则不得执行 shell 命令

### Step 4: 冒烟测试

对最小测试用例运行工具：
1. 使用已知输入和预期输出编写测试
2. 导入并调用工具的入口函数
3. 将实际输出与预期输出比较（float 在容差范围内）
4. 如果测试失败，返回错误及建议修复

**测试通过时：**
- 计算源文件的 SHA-256 hash
- 注册到 `tools/registry.json`

**测试失败时（最多重试 max_retries 次）：**
- 返回 traceback
- 建议 3 个可能的修复
- 让调用者决定是否修复并重试

### Step 5: 注册并文档化

**持久工具：**
```json
{
  "name": "tool_name",
  "version": "1.0.0",
  "path": "tools/tool_name/tool_name.py",
  "hash": "sha256:...",
  "description": "...",
  "input_schema": "...",
  "output_schema": "...",
  "created_at": "2026-07-19T12:00:00Z",
  "usage_count": 0
}
```

**临时工具：**
- 写入 `tools/temp/{session_id}_{tool_name}.py`
- 返回文件路径和使用说明
- 不注册到 `registry.json`

### Step 6: 返回给调用者

```json
{
  "status": "one of: created | updated | failed",
  "tool_name": "custom_parser",
  "path": "tools/custom_parser/custom_parser.py",
  "entry_point": "custom_parser.parse(input_data)",
  "smoke_test": "one of: passed | failed",
  "usage": "from tools.custom_parser import parse; result = parse(data)"
}
```

## 下游 skill 调用

- `/dynamic-sandbox` — 使用新创建的工具执行计算
- `/unified-plotting` — 工具的绘图输出可传给此 skill 渲染

## 共享契约引用

- [integration-contract](../../shared-references/integration-contract.md) — skill 集成协议
- [skill-config](../../shared-references/skill-config.md) — skill 配置契约
- [output-manifest](../../shared-references/output-manifest.md) — 产物结构契约