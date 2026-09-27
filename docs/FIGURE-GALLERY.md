# Figure System v1.6.0 — Gallery & Level Analysis (demo run 2026-09-27)

> 全部图经**统一入口** `render_figure.py --strict` 渲染并通过 A1–A10 审计。
> 联系表：`docs/assets/figure-ladder-gallery.png`（左列数据配方、右列方法阶梯）。
> 本文件是"跑 demo → 分析图的水平"的书面结论，诚实标注强项与弱点。

## 数据配方阶梯（声明式 recipe，布局零自由度）

| # | recipe | 水平评估 | 证据 |
|---|--------|---------|------|
| 1 | line-comparison | **出版级** | log 轴科学计数、误差带+图例自动标注 ±1 SEM、色+marker 双编码、顶部图例、去顶脊 |
| 2 | bar-grouped | **出版级** | 分组柱、误差棒 capsize、零基线、类别轴标签正确 |
| 3 | scatter-fit | **良好，一处可改进** | 点+回归虚线+r 标注齐全；**弱点**：线性拟合在 log-log 轴上呈曲线（数学正确但视觉易误读）——v1.7 应默认在 log 空间拟合 |
| 4 | heatmap | **出版级** | cividis（CVD 设计色图）、colorbar、单元格数值按背景亮度自动黑白反色 |
| 5 | forest-plot | **出版级** | CI 触须、零线虚线、合并菱形（绯红强调）、研究标签 y 轴——生统/循证标准形态 |

## 方法图阶梯（L1→L5 从简到繁，模板锁布局）

| 级 | 模板 | 水平评估 | 证据 |
|----|------|---------|------|
| L1 | 线性流程 | **干净达标** | 编号阶段链、focus 节点高亮（绿描边+浅底 tint）、统一圆角 |
| L2 | 分支+循环 | **达标** | 决策节点、yes 实线/revise 红虚线回边——控制环语义清晰 |
| L3 | 容器+图例+callout | **出版级（最高样张）** | 嵌套容器（1.Data/2.Model/3.Eval）、模块内链、虚线 callout 引导线、Legend 框右下——正交布线，无杂散线（修复 d2 全局边样式伪连线的直接证据） |
| L4 | 宏-微 inset | **达标** | 主链 + "Attention detail" zoom 框（focus2 青色）虚线连出——macro-micro 惯例正确 |
| L5 | 分带架构 | **可用，最弱一级** | zone 容器成立，但主链边穿越带界造成视觉张力；真实论文用法应让 zone 间边只走代表节点——v1.7 改进项 |

## 工具链统一性验证（本轮核心主张）

1. **单一入口**：15 引擎（含新 recipe/method）全部 `render_figure.py` 分发，审计/latex_include/双矢量输出对所有路径一致。
2. **模型无布局自由度**：数据图 = `.recipe.json`（填数据+标签）；方法图 = `.method.json`（填阶段/模块文本）。字号/图例/色板/误差语义/复杂度预算（≤4 词/节点、≤7 阶段、≤2 焦点色）全部代码锁死。
3. **依赖强制**：`dependencies.json` + `dep_gate`（6b/6c 边界）——未声明 import 直接 BLOCKED；"想用什么用什么"在结构上不可能。
4. **色板即审计**：多巴胺 8 色 CVD 双网 + 派生 tint 白名单 + prop_cycle 可见性排序（naive 路径也 line-safe）。

## 审计抓真 bug 的记录（本轮的元证据）

方法阶梯开发中，A4 字号地板抓出 4 个 d2 真缺陷（注释渲染成 16px 文本、class/glob 字号不传播到边标签、保留字 legend+全局边样式画伪连线、容器重引用丢 class）——**每个都是先 FAIL 后修，strict 5/5 才放行**。这正是"门即代码"的运作方式。

## v1.7 候选（诚实遗留）

- scatter-fit 默认 log 空间拟合；L5 zone 间边规则；proplot 式 fontscale 联动；km-survival + box-distribution 两配方（调研建议）；A12–A13 审计（面板字母格式、误差声明）。

## 版面原型（v1.6 二轮 · figure-layout-contract.md §3）

GitHub 调研（2026-09-27）锁定排版权威源并落地：`Yuan1z0825/nature-skills` 的 `nature-figure`（figure contract + multipanel evidence architecture + 1.5pt panel-alignment auditor）、`Zhangyanbo/nature-style-skill`（journal grid + point-scale type）、`0xE1337/thesis-figure-skill`（layout-by-construction + anti-AI-slop）、`shuang-afk/research-figure-composer-skill`、`LawrenceRiver/FigFox-Gen-skill`（human construction order）、`ai4paper/apaper-plugin`（block/tap-junction）、`BAIKEMARK/happy-figure-skill`（figure-type layout candidates）。

四个版面原型进 `figure_recipes.py` 的 `panel-grid` `layout` 字段，几何代码锁死：

| 原型 | 几何锁 | 水平评估 | 样张 |
|------|--------|---------|------|
| `equal-grid` | 等宽等高，A11 全局 width lock | **出版级** | `layout-equal-grid.png` |
| `schematic-led` | hero 45–60% 高（`height_ratios=[2.0,1.15]`）+ support 行降字号/去轴标签 | **出版级** | `layout-schematic-led.png` |
| `asymmetric-hero` | 中央面板跨行占右列，support 安静 | **出版级** | `layout-asymmetric-hero.png` |
| `clinical-triptych` | `height_ratios=[1.0,1.35,0.8]` 三行叙事 | **出版级** | `layout-clinical-triptych.png` |

**A11 面板对齐门**（`figure_audit.py`）：1.5pt 物理公差比对同行/同列共享边、等宽、重复 gutter；hero 只豁免自身不放宽全局公差（负向测试 30pt 宽度漂移正确 FAIL）。`panel_layout.json` 清单由 `figure_recipes` 自动产出。

**修掉的真排版缺陷**（每项都是先看图再改码）：
1. `fig.subplots_adjust` 不移动 `add_gridspec` 的 axes → 行距全部失效，hero x 标签穿入 support 行。几何改由 gridspec 直接持有。
2. `NATURE_FLOOR`（16pt 单图字号）在半栏 support 面板上放大 2–3 倍挤爆邻居。support 降为 point-scale（0.5×轴标签 / 0.55×刻度），与契约 §6 的 6–8pt 印刷档一致。
3. panel 字母外置 `(a)` 压邻面板 y 轴标签 → 改内侧左上小写 `a` + 白底 halo（Nature §3.6 "near the upper-left"）。
4. 图例压 x 轴标签 → 底部预留 x-label band + 每行图例 0.065 独立带。
5. support 面板双轴标签与 hero 争语义 → 按 P3 静音（去轴标签，保留刻度数字）。

**五点图画契约**（写码前必填，缺 `claim`/`archetype` 拒绝渲染）：核心结论（一句带谓语）→ 证据链（每面板一个推断角色，10 角色表）→ 版面原型 → 锁定工具链 → 导出契约。必要性检验：删掉该面板是否丢失独特推断？否则进 Extended Data/删除。
