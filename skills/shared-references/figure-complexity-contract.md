# Figure Complexity Contract (SciForge-OSS — Anti-Elementary-Figure Rules)

> **Status (v1.0)**: 本契约专治"小学生级别"图——纯基础形状+大段文字、箭头乱飞、没有视觉层次的图。与 [`figure-quality-contract.md`](figure-quality-contract.md)（格式/色板/字号）互补：那份管"规范"，这份管"复杂与美观"。由 `/unified-plotting` 执行、由 `render_figure.py` 内嵌审计机械检查（A7 复杂度层）。

---

## 1. 组件丰富度下限（Component Richness Floor）

**≥5 节点的图，禁止全部由素矩形/素椭圆构成。** 至少 60% 的主要组件必须具备自定义视觉身份，三选一（agent 现写，不依赖仓库资产库）：

| 手段 | 引擎 | 做法 |
|------|------|------|
| **图标组件** | d2 | 节点声明 `icon: ./icons/<name>.svg`，图标由 agent 现写（§5 方法论） |
| **自绘 pic** | TikZ | `\pic` 宏多层绘制（投影层+主体+符号细部），不用 `rectangle` 裸框 |
| **复合形状** | Asymptote/SVG | 组合 ≥3 个基元 + 双色调（主体填充 + 强调细部），如带液面的试管、带栅格的芯片 |

**审计**: 5+ 节点的架构图零图标/零自绘组件 → `A7 WARN plain_shapes_only`。

## 2. 视觉层次（Visual Hierarchy）

- **至少两级分组**: 容器嵌套（容器内再分组）或横向 band 分区，容器带标题与浅一档的填充色（`surface` → `surface-alt` 递进）。
- **每个容器 ≤6 个直接子组件**; 超过就再嵌一层分组。
- **主角突出**: 方法核心组件用 `ochre`（唯一强调位）或 `diamond`/`hexagon` 异形；其余组件一律低饱和。

## 3. 连线治理（Edge Governance）——治"线太多太乱"

1. **容器级汇流**: 同一对分组之间 ≥3 条平行流时，必须合并为一条带标签的干线（trunk edge）或总线（bus），禁止 N×M 全连接式箭头雨。例：3 个 encoder 各自连 fusion → 改为 encoder 容器一条 `z_{v,t,x}` 干线。
2. **边密度上限**: `edges / nodes ≤ 1.6`（审计 WARN 超出者）。确实需要的密集图（定理依赖 DAG 等）在图目录放 `complexity_override.txt` 说明理由（如"依赖关系本身就是内容"）。
3. **箭头样式族 ≤3 种**: 实线=主数据流；虚线=反馈/辅助；粗线=主干。禁止一图出现 4 种以上线型。
4. **反馈边绕行**: 反馈/更新边走图形外沿（d2: 独立方向声明; TikZ: `to[out=,in=]` 绕行），禁止穿越其他组件。
5. **标签精简**: 边标签 ≤3 词；能用符号（$z_v$, $\alpha$）不用句子。
6. **手工 SVG 专用布线走廊（Visio 级）**: 手工装配 SVG 时，跨泳道连线必须走**预分配的垂直走廊**（如 x=460–520、940–1000 等列带），走廊内只允许垂直走线，水平段在走廊两端 90° 接入——即"正交圆角布线"。禁止斜线、禁止连线穿越卡片。总线在走廊中合并后，从走廊对侧以短水平段分出各目标，形成梳齿状（comb）分发。

## 4. 文字纪律（Text Discipline）

- 节点标签 ≤3 行、≤4 词/行；长解释移入 caption 或侧注。
- 图内出现整句解释（>8 词）→ 重构：拆成组件或移入 caption。
- 数学符号用引擎原生数学排版（TikZ `$...$` / d2 LaTeX `$$..$$`）。

## 5. 图标自绘方法论（Agent 现写，不入仓库）

> **原则**: 图标是 agent 的创作产物，随每张图保存在该图目录（`figures/<name>/icons/*.svg`），可复现、可审计。SciForge-OSS 只提供方法，不提供图库。

### 5.1 d2 图标规范

- 尺寸: `viewBox="0 0 64 64"`（方形图标）；节点 `width/height` 由 d2 自动，图标近旁 `style.font-size` ≥20px
- 配色: 只用莫兰迪 token（`sciforge_style.TOKENS`）；描边 `#6E675F`(ink-soft) 1.5–2px，主体填充 `#EDE9E2`/token，强调细部用组件语义色
- 结构: 5–15 个基元、≥2 个色调、必有一个"识别性细部"（数据库的椭圆顶、神经元的突触点、齿轮的齿）
- 引用: `icon: ./icons/db.svg`（相对 spec 所在目录）

**示范模板**（agent 依此风格自绘，不得直接复用为图库）:
```svg
<!-- 数据库：椭圆顶 + 柱身 + 分层线（识别性细部=分层） -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <path d="M12 16v28c0 4 9 7 20 7s20-3 20-7V16" fill="#EDE9E2" stroke="#6E675F" stroke-width="2"/>
  <ellipse cx="32" cy="16" rx="20" ry="7" fill="#93A7BB" stroke="#6E675F" stroke-width="2"/>
  <path d="M12 28c0 4 9 7 20 7s20-3 20-7" fill="none" stroke="#6E675F" stroke-width="1.5"/>
</svg>
```
```svg
<!-- 神经层：堆叠圆片 + 连接点（识别性细部=层叠与节点） -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="14" y="40" width="36" height="8" rx="4" fill="#BDA5A7" stroke="#6E675F" stroke-width="1.5"/>
  <rect x="14" y="28" width="36" height="8" rx="4" fill="#A4B294" stroke="#6E675F" stroke-width="1.5"/>
  <rect x="14" y="16" width="36" height="8" rx="4" fill="#93A7BB" stroke="#6E675F" stroke-width="1.5"/>
  <circle cx="22" cy="20" r="2" fill="#FAF8F5"/><circle cx="32" cy="20" r="2" fill="#FAF8F5"/><circle cx="42" cy="20" r="2" fill="#FAF8F5"/>
</svg>
```

### 5.2 TikZ 自绘组件规范

- 用 `\tikzset{pics/<name>/.style={...}}` 定义 pic，内部 ≥3 层绘制：`投影(soft fill)` → `主体(token fill + ink-soft stroke)` → `细部(ochre/rose accent)`
- 组件投影统一：`fill=sfinksoft!12, transform canvas={shift={(0.35mm,-0.35mm)}}`
- 数据张量画成堆叠圆片（`foreach` 循环），不要写 "[h1,h2,...]" 文字

### 5.3 Asymptote / 等距投影（isometric）SVG

- Asy: 组件 = ≥3 基元 + ≥2 色调；机械件加剖面线（`hatch`），流体加渐变（`axialshade`）
- **等距 3D 风格图（替代 Blender/渲染器的轻量方案）**: 用纯 SVG 做 2:1 等距投影（iso(x,y,z) = ((x−y)·cos30°, (x+y)/2 − z)），画家算法按深度排序绘制；立体 = 顶面 + 两个可见侧面，侧面用 token 色叠加半透明 ink（10%/20%）制造明暗，SVG 源码仍 100% 莫兰迪合规（审计通过）；配 callout 引线标注（虚线引线 + 圆点锚 + 标签）、地面网格板、粒子流点缀。适合机制示意图、系统结构图——获得"3D 感"而不引入 3D 渲染依赖。

### 5.4 数据图背景约定

- **实验数据图（曲线/消融/热图/校准等）背景必须纯白 `#FFFFFF`**（覆盖 `apply_matplotlib_style()` 的 canvas token），与正文白纸融为一体；莫兰迪仅用于系列色与元素色。
- 示意图/架构图/方法论图才使用 canvas `#FAF8F5` 底。

## 6. 复杂度下限（Complexity Floor — 量化）

| 图类型 | 组件数 | 图标/自绘占比 | 分组层级 | 附加元素（至少 1 项） |
|--------|--------|--------------|----------|----------------------|
| Intro 问题图 | ≥8 | ≥50% | ≥2 | 图例 / 标注 callout |
| Methods 架构图 | ≥12 | ≥60% | ≥2 | 图例 + 分区标题 (a/b/c) |
| 机制图 | ≥8 | ≥60% | ≥2 | 公式标注 / 注意力权重 |
| 复合面板 | ≥3 面板 | 数据图免图标 | — | (a)(b)(c) 面板标签 |

**达不到下限 = 图还没画完**，继续迭代（加组件、画图标、理连线），而不是降低标准交付。

## 7. See Also

- [`figure-quality-contract.md`](figure-quality-contract.md) — 格式/色板/字号/比例
- [`figure-quality-review.md`](figure-quality-review.md) — 外部审阅顾问（可选）
- [`../meta-skills/unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) — 消费者
