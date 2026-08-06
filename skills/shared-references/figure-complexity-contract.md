# Figure Complexity Contract (SciForge-OSS — Anti-Elementary-Figure Rules)

> **Status (v1.1)**: 本契约专治"小学生级别"图——纯基础形状+大段文字、箭头乱飞、没有视觉层次的图。与 [`figure-quality-contract.md`](figure-quality-contract.md)（格式/色板/字号）互补：那份管"规范"，这份管"复杂与美观"。由 `/unified-plotting` 执行、由 `render_figure.py` 内嵌审计机械检查（A7 复杂度层）。

## 0. 领域中立（Discipline Neutrality）——最高原则

SciForge-OSS 服务**全领域**：理工农医、社科人文、经管法学皆然。本契约所有规则按**图的结构角色**（structural role）表述，不按图的具体内容或领域表述：

- **测试图 ≠ skill 边界**: 开发期使用的示例图只是管线验证载体，不构成 skill 支持的图类型清单。任何领域、任何内容的图都适用同一套规则。
- **领域只决定语义，不决定规则**: 医学通路图、材料晶格图、法条层级图、历史时间轴、生态网络图……组件语义随领域变，本契约的丰富度下限、连线治理、图层模型、纵深技法、白底与品牌纪律一律不变。
- **审计是领域无知的**: A4–A10 审计层只检查结构属性（字号、色度、重叠、图标占比、品牌泄露），不含任何领域假设——新增领域不需要改审计。

## 0.5 全领域图表角色类型学（Role Typology × Engine Mapping）

任何一张论文插图，先归入一个结构角色，再按表选引擎与技法（引擎均经统一入口 `render_figure.py` 渲染，单一链路）：

| 结构角色 | 各领域示例（仅示意） | 首选引擎 | 关键技法 |
|---------|---------------------|---------|---------|
| **结构/组成** | 系统架构、装置结构、解剖层次、晶胞/分子结构、组织框架 | 手工装配 SVG（Visio 级）/ tikz / 等距 SVG | 分层容器、图标组件、编号徽章、渐变卡面 |
| **过程/流程** | 方法论、反应路径、临床路径、法律程序、制造工艺 | d2 / blockdiag(actdiag) / mermaid / pikchr / 手工 SVG | 泳道、检查门/决策点、里程碑脊柱、交付物标注 |
| **机制/因果** | 分子机制、生理反馈环、经济因果链、证明草图、注意力机制 | tikz（`\pic` 自绘）/ 等距 SVG / asy / pikchr | 自绘组件、束宽∝强度、虚线反馈、公式标注 |
| **关系/网络** | 引用网络、知识图谱、食物网、社交网络、定理依赖 | d2（elk 密集）/ graphviz | 容器级汇流、边密度控制、图例 |
| **层级/分类** | 分类树、系统发育、法条层级、本体结构 | d2 / blockdiag tree | 树形布局、分支标签、深度着墨递进 |
| **时间/演变** | 历史时间轴、演化序列、临床病程、政策沿革 | 手工装配 SVG / d2 timeline | 轴+事件锚点、分期着色带、callout |
| **空间/地理** | 地图、剖面图、晶体结构、3D 装置 | 等距 SVG / asy / diagrams | 等距投影、网格底板、方位标注 |
| **证据/数据** | 实验曲线、临床统计、问卷结果、仿真输出 | matplotlib（白底 + apply_matplotlib_style） | 复合面板、inset zoom、显著性标注、不确定度带 |

**用法**: agent 拿到绘图任务先判角色（可复合，如"机制+数据"用复合面板）；角色决定引擎与技法，领域只决定组件画什么。复合角色图优先手工装配 SVG 统一画布，禁止多引擎产物拼接（保持单一链路）。

---

## 1. 组件丰富度下限（Component Richness Floor）

**≥5 节点的图，禁止全部由素矩形/素椭圆构成。** 至少 60% 的主要组件必须具备自定义视觉身份，三选一（agent 现写，不依赖仓库资产库）：

| 手段 | 引擎 | 做法 |
|------|------|------|
| **图标组件** | d2 | 节点声明 `icon: ./icons/<name>.svg`，图标由 agent 现写（§5 方法论） |
| **自绘 pic** | TikZ | `\pic` 宏多层绘制（投影层+主体+符号细部），不用 `rectangle` 裸框 |
| **复合形状** | Asymptote/SVG | 组合 ≥3 个基元 + 双色调（主体填充 + 强调细部），如带液面的试管、带栅格的芯片 |

**审计**: 5+ 节点的图零图标/零自绘组件 → `A7 WARN plain_shapes_only`。

## 2. 视觉层次（Visual Hierarchy）

- **至少两级分组**: 容器嵌套（容器内再分组）或横向 band 分区，容器带标题与浅一档的填充色（`surface` → `surface-alt` 递进）。
- **每个容器 ≤6 个直接子组件**; 超过就再嵌一层分组。
- **主角突出**: 图的核心组件（该图叙事的主角——可以是方法、器官、装置、事件）用 `ochre`（唯一强调位）或 `diamond`/`hexagon` 异形；其余组件一律低饱和。

## 3. 连线治理（Edge Governance）——治"线太多太乱"

1. **容器级汇流**: 同一对分组之间 ≥3 条平行流时，必须合并为一条带标签的干线（trunk edge）或总线（bus），禁止 N×M 全连接式箭头雨。例：3 个输入源各自连同一处理模块 → 改为输入容器一条带符号标签的干线。
2. **边密度上限**: `edges / nodes ≤ 1.6`（审计 WARN 超出者）。确实需要的密集图（定理依赖 DAG 等）在图目录放 `complexity_override.txt` 说明理由（如"依赖关系本身就是内容"）。
3. **箭头样式族 ≤3 种**: 实线=主数据流；虚线=反馈/辅助；粗线=主干。禁止一图出现 4 种以上线型。
4. **反馈边绕行**: 反馈/更新边走图形外沿（d2: 独立方向声明; TikZ: `to[out=,in=]` 绕行），禁止穿越其他组件。
5. **标签精简**: 边标签 ≤3 词；能用符号（$z_v$, $\alpha$）不用句子。
6. **手工 SVG 专用布线走廊（Visio 级）**: 手工装配 SVG 时，跨泳道连线必须走**预分配的垂直走廊**（如 x=460–520、940–1000 等列带），走廊内只允许垂直走线，水平段在走廊两端 90° 接入——即"正交圆角布线"。禁止斜线、禁止连线穿越卡片。总线在走廊中合并后，从走廊对侧以短水平段分出各目标，形成梳齿状（comb）分发。

## 4. 文字纪律（Text Discipline）

- 节点标签 ≤3 行、≤4 词/行；长解释移入 caption 或侧注。
- 图内出现整句解释（>8 词）→ 重构：拆成组件或移入 caption。
- 数学符号用引擎原生数学排版（TikZ `$...$` / d2 LaTeX `$$..$$`）。

## 4.5 图层模型（Layer Model）——文字零重叠的组织纪律

手工装配 SVG 必须按图层组织，审计 A10 层机械检查（文字-文字 bbox 相交 >12% 即 FAIL；布线穿字无 halo 即 WARN；≥20 标签无图层结构即 WARN）：

```
<g class="layer-0-bg">       背景与地面（白底矩形、泳道底板、网格）
<g class="layer-1-cards">    卡片/容器及其内嵌图标、mini 可视化（卡片内文字属于本层）
<g class="layer-2-wiring">   所有连线、总线、箭头（画在卡片之上、标签之下）
<g class="layer-3-labels">   边标签、callout、图例（最顶层；每个标签必须落在无遮挡空位）
```

**硬性规则**:
1. 任何两个文字 bbox 不得相交（边标签压字、标题压卡片文字都算违规）——放标签前先查空位（A10 会扫出来）
2. 边标签放线段**旁**（垂直偏移 ≥1.2×字号）或带 halo rect，禁止骑在线上无背景
3. 卡片文字距卡片边 ≥12px；相邻卡片文字列不得互相侵入
4. 布线在 layer-2、文字在 layer-3——布线永远盖不住文字

## 4.6 审阅修订纪律（Scoped Revision — 借鉴 Memslides 局部修订，Apache-2.0）

审计报出问题后，修订必须**局部化**，禁止整图重写：

1. 只修改被 A4/A5/A8/A9/A10 点名的具体元素（该标签/该卡片/该连线），重渲染整图但改动限于该处
2. 一次只修一类问题（先修 FAIL 再修 WARN），修完跑审计确认，再进入下一类
3. 修订保留迭代痕迹：图目录 `revision_log.md` 逐条记录"审计发现 → 修改内容"（可复现、可追溯）
4. 连续 3 轮同一问题未消除 → 回到骨架层重新布局该区域，而不是继续微调坐标

（Memslides 的分层记忆/工具记忆思想已对照评估：其渲染链为 slides 导出，与本管线的矢量插图定位不同，不作为引擎集成；仅采纳其 scoped revision 方法论，保持单一链路。）

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

### 5.4 背景与品牌纪律

- **所有类型图的背景一律纯白 `#FFFFFF`**（数据图、架构图、方法论图、机制图全部），与论文白纸融为一体；莫兰迪仅用于组件/系列/填充色。数据图在 `apply_matplotlib_style()` 后覆盖 `figure.facecolor`/`axes.facecolor`；SVG 图底 `<rect fill="#FFFFFF">`。
- **图是论文插图，不是工具海报**: 图内任何位置禁止出现内部品牌/工具名/调色板代号（SciForge、unified renderer、morandi、figure-lab 路径、渲染器版本号等）。审计 A9 层扫描图源强制拦截；标题条只放图的学术内容，工具信息一律留在 caption 与正文。

### 5.5 运行时图标词汇协议（Runtime Icon Vocabulary — 抬视觉天花板，不入库）

> **背景**: agent 手绘图标的艺术性有天然上限。本协议允许**运行时**借用专业开源图标词汇，同时不违反"不把图标资产库写进仓库"的原则——图标随图保存在 `figures/<name>/icons/`，来源与许可记录在图的 `revision_log.md`。

**许可白名单（只从这些来源抓取，禁止其他）**:

| 来源 | 许可 | 领域 |
|------|------|------|
| bioicons.com | 图标逐一标注（多为 CC0/CC-BY） | 生医/分子/细胞 |
| Tabler Icons | MIT | 通用技术 |
| Lucide | ISC | 通用技术 |
| Feather Icons | MIT | 通用技术 |
| Font Awesome Free（solid/regular） | CC-BY-4.0 | 通用（需署名） |
| d2 bundled icons (icons.terrastruct.com) | 随 d2 分发 | 基础设施/云 |

**强制流程（四步，缺一不可）**:
1. **抓取**: 从白名单来源下载 SVG 到 `figures/<name>/icons/<icon>.svg`，经代理（mihomo 8099）访问；**抓取失败不阻塞**——回退到 agent 手绘（§5.1 方法论）
2. **重着色**: 图标必须经过 `sciforge_style.recolor_icon()`（`python -c "from sciforge_style import recolor_icon; ..."`）——按 L* 明度序映射到莫兰迪系列色，中性色保留；未经重着色的原色图标进图会被 A3 审计拦截
3. **引用**: d2 用 `icon: ./icons/<icon>.svg`；手工 SVG 用 `<image>` 或内联 `<g>` 嵌入（内联优先，保持单文件可审计）
4. **记录**: 图的 `revision_log.md` 追加一行 `icon: <name> ← <来源 URL> (<许可>)`；CC-BY/Font Awesome 图标的署名按许可要求写入 LaTeX 致谢或补充材料

**禁止**: 抓取后直接使用原色、从白名单外来源抓取、把图标库批量写入仓库、用图标绕过 A7 复杂度审计（图标是组件词汇，不替代卡片内 mini 可视化）。

## 6. 复杂度下限（Complexity Floor — 量化）

| 图类型 | 组件数 | 图标/自绘占比 | 分组层级 | 附加元素（至少 1 项） |
|--------|--------|--------------|----------|----------------------|
| Intro 问题图 | ≥8 | ≥50% | ≥2 | 图例 / 标注 callout |
| Methods 结构/机制图 | ≥12 | ≥60% | ≥2 | 图例 + 分区标题 (a/b/c) |
| 机制图 | ≥8 | ≥60% | ≥2 | 公式标注 / 注意力权重 |
| 复合面板 | ≥3 面板 | 数据图免图标 | — | (a)(b)(c) 面板标签 |

**达不到下限 = 图还没画完**，继续迭代（加组件、画图标、理连线），而不是降低标准交付。

## 6.5 视觉纵深技法（Visio/Illustrator 级 — 禁止"扁平盒子"）

> 手工装配 SVG 要达到 Visio/AI 级质感，必须叠加纵深语言，审计 A8 层机械计数（`figure_audit.py audit_richness`），卡片数 ≥4 而纵深器件总数少于卡片数 → WARN。

| 技法 | 做法 | 数量建议 |
|------|------|---------|
| **渐变卡面** | `<linearGradient>` 白→token 浅化（opacity 叠加，源码保持色板合规），卡片头部或全卡 | ≥30% 卡片 |
| **投影分层** | `filter feDropShadow`（已验证模板），卡片/门控菱形浮起 | 所有浮起卡片 |
| **端口点** | 卡片边缘的接线锚点：r=3–4 实心圆（ink-soft），总线接合处加 r=5 接点圆 | 每个有出线的卡片 ≥1 |
| **总线接点** | 干线合流/分出处画实心接点圆（电路总线画法），禁止线直接"穿过"卡片 | 每个合流点 |
| **迷你可视化** | 卡片内嵌 sparkline / token 条 / patch 网格 / 注意力矩阵 / 进度条 | ≥40% 卡片 |
| **编号标注** | 卡片角标 ①②③ 或 (1)(2)(3) 小圆章，caption 按编号呼应 | 主流程组件 |
| **状态徽章** | 右上角小圆角章（pretrained ✓ / running / frozen） | 适用处 |
| **刻度/仪表** | 数值用迷你仪表条（fill 百分比）呈现，不用裸文字 | ≥1 |

**纵深配色纪律**: 渐变仅用"token ↔ canvas/白"或"token ↔ ink 低透明度叠加"，禁止引入新色相；审计 A3 仍按源码 hex 校验（叠加透明度不产生新 hex，天然合规）。

## 7. See Also

- [`figure-quality-contract.md`](figure-quality-contract.md) — 格式/色板/字号/比例
- [`figure-quality-review.md`](figure-quality-review.md) — 外部审阅顾问（可选）
- [`../meta-skills/unified-plotting/SKILL.md`](../meta-skills/unified-plotting/SKILL.md) — 消费者
