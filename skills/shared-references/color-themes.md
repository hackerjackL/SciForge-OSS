# Color Themes (SciForge-OSS — Unified Morandi Design System v2.0)

> **核心**: 莫兰迪色系 (Layer 1) + viridis/magma/plasma 数据热图 (Layer 2)。禁止使用 jet/rainbow/hsv。
>
> **单一事实源**: 本文件与 [`unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) 的色表均以 **`scripts/plotting/sciforge_style.py`** 的 `TOKENS` 字典为唯一权威定义（每个颜色经过数值校验：CIELAB 色度 C* ≤ 25 且 ink 文字对比度 ≥ 4.5）。若本文档与代码不一致，以代码为准。

## 快速参考

| 用途 | 色系 | 说明 |
|------|------|------|
| 分类/语义色 | 莫兰迪 (Layer 1) | 低饱和度、柔和、优雅。C* ≤ 25（数值校验） |
| 连续数据热图 | viridis / magma / plasma (Layer 2) | 感知均匀，色盲友好 |
| 强调/标注 | `ochre` / `rose` token | 箭头、高亮、边框 |
| 文字/坐标轴 | `ink` (#3A3733) | 所有正文文字、轴线 |

## 莫兰迪色板 (Layer 1) — 与 sciforge_style.py 完全一致

### 墨色与底面（文字、轴线、背景）

| Token | HEX | C* | 用途 |
|-------|-----|-----|------|
| ink | #3A3733 | 3.0 | 主文字、坐标轴、箭头 |
| ink-soft | #6E675F | 5.6 | 次要文字、节点描边、网格线 |
| canvas | #FAF8F5 | 1.7 | 画布背景 |
| surface | #EDE9E2 | 3.9 | 默认节点填充/面板背景 |
| surface-alt | #E3DDD3 | 5.6 | 交替容器填充 |

### 分类系列色（按视觉优先级排序）

| Token | HEX | C* | ink 对比度 | 语义角色 |
|-------|-----|-----|-----------|---------|
| blue | #93A7BB | 12.9 | 4.78 | 第 1 系列 / hero（提出方法） |
| sage | #A4B294 | 17.2 | 5.28 | 第 2 系列 / positive（改进） |
| mauve | #BDA5A7 | 9.3 | 5.13 | 第 3 系列 |
| ochre | #C4A880 | 24.9 | 5.22 | accent / 高亮 |
| taupe | #B0A292 | 10.4 | 4.75 | 第 4 系列 / baseline（对比方法） |
| rose | #D9BCBC | 11.0 | 6.69 | 柔和强调 / 标注填充 |
| slate | #97A2B2 | 9.6 | 4.58 | ablation-2 |
| moss | #A5AB91 | 14.4 | 4.98 | ablation-1 |
| clay | #C2A193 | 15.5 | 4.97 | negative（退化） |

### 语义别名（向后兼容旧 spec）

| 旧角色名 | 映射 token | 旧 slot 名 | 映射 token |
|---------|-----------|-----------|-----------|
| hero | blue | warm-grey | surface |
| baseline | taupe | dusty-blue | blue |
| positive | sage | dusty-rose | rose |
| negative | clay | charcoal | ink |
| neutral | surface | muted-ochre | ochre |
| ablation-1 | moss | | |
| ablation-2 | slate | | |
| accent | ochre | | |

**描边规则**: 节点描边 = 填充色向 ink 混合 45%（`sciforge_style.stroke_for(fill)`），审计自动认可；禁止手写高饱和描边。

## 数据热图 (Layer 2)

- **连续数据**: viridis (默认) / magma / plasma
- **分类数据**: 莫兰迪 Layer 1 系列色
- **禁止**: jet / rainbow / hsv / gist_* / coolwarm / bwr（感知不均匀、制造虚假边界）
- **两层规则**: Layer 1 用于分类/语义色；Layer 2 用于连续标量场。绝不混用。

## 图表格式规范（Nature 下限）

| 属性 | 规则 |
|------|------|
| 格式 | PDF（LaTeX 嵌入，唯一交付格式）+ PNG（300 DPI，审阅用）双产出 |
| 字体 | 数据图 TeX Gyre Termes（衬线，匹配 LaTeX）；d2 图 Liberation Sans（通过 CLI 字体文件注入） |
| 字号 | 轴标签 ≥12pt, 刻度 ≥10pt, 图例 ≥10pt, 标题 ≥13pt, 注释 ≥9pt |
| 线宽 | 主线条 ≥1.5pt, 辅助 ≥0.8pt |
| 标记 | ≥6pt, 形状区分（圆/方/菱） |
| 图注 | 自包含: "图 N. 内容 + 关键结论" |
| 引用 | `\cref{fig:label}` — 非硬编码 "Figure 3" |

## 禁用色（数值校验拒绝）

Tailwind 高饱和（`#2563EB`/`#10B981`/`#7C3AED`/`#EA580C`）、Material 蓝（`#1565C0`/`#0D47A1`）、matplotlib 默认（tab10/Set2）、以及 d2/graphviz 引擎默认主题色（渲染器输出前经 `sanitize_palette()` 确定性重映射回莫兰迪）。

## 快速检查

- 莫兰迪 Layer 1（C* ≤ 25）用于分类/语义
- viridis/magma/plasma 用于连续数据
- 无 jet/rainbow/hsv/coolwarm/bwr
- 矢量 PDF + PNG 300dpi 双产出
- 渲染脚本 + 输入数据保留
- 图注自包含
