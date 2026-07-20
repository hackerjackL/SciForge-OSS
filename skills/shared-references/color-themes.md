# Color Themes (SciForge-OSS — Condensed)

> **核心**: 莫兰迪色系 (Layer 1) + viridis/magma 数据热图 (Layer 2)。禁止使用 jet/rainbow/hsv。

## 快速参考

| 用途 | 色系 | 说明 |
|------|------|------|
| 分类/语义色 | 莫兰迪 (Layer 1) | 低饱和度、柔和、优雅。C* ≤ 25 |
| 连续数据热图 | viridis / magma / plasma (Layer 2) | 感知均匀，色盲友好 |
| 强调/标注 | accent 色 (3 种) | 箭头、高亮、边框 |

## 莫兰迪主色板 (Layer 1)

| 角色 | HEX | 用途 |
|------|-----|------|
| hero | #9B9B7B | 提出方法 |
| baseline | #B8A9A9 | 对比方法 |
| positive | #A9B8A9 | 改进 |
| negative | #C4A9A9 | 退化 |
| neutral | #D4CFC9 | 背景/参考 |
| ablation-1 | #A9B8B8 | 消融 |
| ablation-2 | #B8B8A9 | 消融 |
| accent | #C4A9B8 | 强调 |

## 数据热图 (Layer 2)

- **连续数据**: viridis (默认) / magma / plasma
- **发散数据**: coolwarm / RdBu
- **分类数据**: 莫兰迪主色板
- **禁止**: jet / rainbow / hsv / gist_*

## 图表格式规范

| 属性 | 规则 |
|------|------|
| 格式 | 矢量 PDF (首选) 或 SVG |
| 字体 | 衬线体 (embedded) |
| 线宽 | 1.5-2pt (主线条), 0.5-1pt (辅助) |
| 标记 | 圆形/方形/菱形, 填充 vs 空心区分 |
| 图注 | 自包含: "图 N. 内容 + 关键结论" |
| 引用 | `\cref{fig:label}` — 非硬编码 "Figure 3" |

## 快速检查

- 莫兰迪色系 (C* ≤ 25) 用于分类/语义
- viridis/magma 用于连续数据
- 无 jet/rainbow/hsv
- 矢量图 (PDF/SVG)
- 渲染脚本 + 输入数据保留
- 图注自包含