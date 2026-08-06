# SciForge-OSS Figure Toolchain — INSTALL

> 单一入口：所有图（数据图 + 架构/机制/理论/3D 图）只通过
> `python scripts/plotting/render_figure.py` 产出（PDF+PNG 双产出 + 内嵌 Nature 级审计）。
> 装完依赖后先跑自检：`python scripts/plotting/render_figure.py --doctor`。

## 核心依赖（必需）

| 工具 | 用途 | 安装 |
|------|------|------|
| `d2` | 复杂架构/流程/拓扑图（首选引擎） | `curl -fsSL https://d2lang.com/install.sh \| sh -s --`（国内可经代理） |
| `graphviz` | 图布局回退 | `apt-get install graphviz` |
| `rsvg-convert` | SVG → PDF/PNG | `apt-get install librsvg2-bin` |
| `texlive` (pdflatex + tikz + standalone) | 理论图/交换图 + PDF 栅格化 | `apt-get install texlive-latex-base texlive-pictures texlive-science texlive-latex-extra texlive-extra-utils` |
| `poppler-utils` (`pdftoppm`/`pdfinfo`) | PDF → PNG | `apt-get install poppler-utils` |
| Python: `matplotlib`, `numpy`, `Pillow` | 数据图管线 + 审计 | `pip install matplotlib numpy Pillow` |

## 增强引擎（推荐，决定"高级感"上限）

| 工具 | 用途 | 安装 |
|------|------|------|
| `asymptote` | 数学/几何/机制示意图（矢量） | `apt-get install asymptote` |
| `typst` | 毫秒级声明式图（fletcher/CeTZ） | GitHub release 二进制解压到 `/usr/local/bin/typst` |
| `diagrams` (mingrammer) + `blockdiag` 家族 | Diagram-as-code 专业图标集 / 泳道活动图、时序图 | `pip install diagrams blockdiag actdiag seqdiag nwdiag`（aliyun 镜像） |
| `SciencePlots` | 数据图期刊级几何规范 | `pip install SciencePlots` |
| `inkscape` | SVG 转换回退 | `apt-get install inkscape` |
| `svgo` | SVG 瘦身 | `npm install -g svgo` |

## 字体（与 LaTeX 正文一致的关键）

```bash
# TeX Gyre（Times/Palatino/Helvetica 的学术克隆，matplotlib/LaTeX 共用）
mkdir -p ~/.local/share/fonts/texgyre
cp /usr/share/texmf/fonts/opentype/public/tex-gyre/texgyre{termes,pagella,heros}-{regular,bold,italic,bolditalic}.otf ~/.local/share/fonts/texgyre/
fc-cache -f
# Liberation Sans（d2 通过 --font-* 注入，Helvetica 度量兼容）
apt-get install fonts-liberation
```

## 国内镜像（网络慢时）

- pip：`pip config set global.index-url http://mirrors.aliyun.com/pypi/simple && pip config set global.trusted-host mirrors.aliyun.com`
- apt：使用华为云/清华源（`/etc/apt/sources.list`）
- d2/typst 二进制：经 HTTP 代理下载（如 mihomo 混合端口）：
  `https_proxy=http://127.0.0.1:8099 curl -fsSL https://d2lang.com/install.sh | sh -s --`

## 单一入口用法速查

```bash
# 架构图（d2，自动注入莫兰迪前导 + dagre/elk 布局）
python scripts/plotting/render_figure.py spec.d2  --out figures/arch/ --label arch --caption "..." --strict

# 理论/机制图（tikz / asymptote / typst）
python scripts/plotting/render_figure.py spec.tex --out figures/thm/  --label thm  --caption "..." --strict
python scripts/plotting/render_figure.py spec.asy --out figures/mech/ --label mech --caption "..." --strict

# 数据图（render.py 顶部调用 apply_matplotlib_style()）
python scripts/plotting/render_figure.py render.py --out figures/res/ --label res --caption "..." --strict

# 环境自检
python scripts/plotting/render_figure.py --doctor
```

每张图产出：`output.pdf`（LaTeX 嵌入）+ `output.png`（300 DPI 审阅）+ 保留源码 +
`latex_include.tex` + `figure_audit.json`（PASS/WARN/FAIL）。
