# SciForge-OSS Figure Toolchain — INSTALL（跨平台复刻手册）

> **单一入口**：所有图（数据图 + 架构/流程/机制/组图）只通过
> `python scripts/plotting/render_figure.py` 产出（PDF+PNG 双产出 + 内嵌 Nature 级审计）。
> 装完依赖后先跑自检：`python scripts/plotting/render_figure.py --doctor`
>
> **跨平台**：Linux / macOS / Windows 均支持。代码内**无机器专属绝对路径**——字体按
> fontconfig → 三平台目录扫描动态发现，工具按 `PATH` 查找（`shutil.which`）。
> Windows 推荐 WSL2（Ubuntu）获得与 Linux 完全一致的体验；原生 Windows 也全部可行（见下文）。

## 0. 快速复刻（最小可用集）

只需 4 件东西就能跑通数据图 + d2 架构图 + 审计：

| 组件 | Linux (apt) | macOS (brew) | Windows |
|------|------------|--------------|---------|
| Python ≥3.10 + matplotlib/numpy/Pillow | `sudo apt install python3-pip && pip install matplotlib numpy Pillow` | `brew install python && pip install matplotlib numpy Pillow` | 装 [python.org](https://python.org) 或 `winget install Python.Python.3.12`，然后同左 pip 命令 |
| d2 | `curl -fsSL https://d2lang.com/install.sh \| sh -s --`（国内经代理） | `brew install d2` | `scoop install d2`（或安装脚本 PowerShell 版） |
| librsvg (`rsvg-convert`) | `sudo apt install librsvg2-bin` | `brew install librsvg` | 装 MSYS2 后 `pacman -S mingw-w64-x86_64-librsvg`，或用 WSL2 |
| poppler (`pdftoppm`) | `sudo apt install poppler-utils` | `brew install poppler` | `choco install poppler` 或 WSL2 |

```bash
python scripts/plotting/render_figure.py --doctor   # 全绿即最小可用
```

## 1. 核心依赖（必需）

| 工具 | 用途 | Linux (apt) | macOS (brew) | Windows |
|------|------|------------|--------------|---------|
| `d2` (v0.7+) | 复杂架构/流程/拓扑图（首选引擎） | 安装脚本（见上） | `brew install d2` | `scoop install d2` |
| `graphviz` | 图布局回退 | `sudo apt install graphviz` | `brew install graphviz` | `choco install graphviz` |
| `rsvg-convert` | SVG → PDF/PNG | `sudo apt install librsvg2-bin` | `brew install librsvg` | MSYS2 `librsvg` / WSL2 |
| texlive (pdflatex + tikz) | 理论图/交换图 + PDF 栅格化 | `sudo apt install texlive-latex-base texlive-pictures texlive-science texlive-latex-extra texlive-extra-utils` | `brew install --cask mactex-no-gui` 或 `basictex` + `tlmgr install tikz standalone pdfcrop` | [MiKTeX](https://miktex.org)（`miktex setup`）或 TeX Live installer；WSL2 同 Linux |
| `poppler-utils` (`pdftoppm`/`pdfinfo`) | PDF → PNG、组图面板栅格化 | `sudo apt install poppler-utils` | `brew install poppler` | `choco install poppler` / WSL2 |
| Python: `matplotlib`, `numpy`, `Pillow` | 数据图管线 + 审计 | `pip install matplotlib numpy Pillow`（aliyun 镜像见 §6） | 同左 | 同左 |

> **Fedora/RHEL/openSUSE**：把 `apt install` 换成 `dnf install`，包名基本一致
> （`graphviz`、`librsvg2-tools`、`texlive-scheme-basic`、`poppler-utils`）。
> **Arch**：`pacman -S graphviz librsvg texlive-most poppler`。

## 2. 增强引擎（推荐，决定"高级感"上限）

| 工具 | 用途 | Linux | macOS | Windows |
|------|------|-------|-------|---------|
| `asymptote` | 数学/几何/机制示意图（矢量） | `sudo apt install asymptote` | `brew install asymptote` | `choco install asymptote`（或官网 msi） |
| `typst` | 毫秒级声明式图（fletcher/CeTZ） | GitHub release 二进制 → `~/.local/bin/typst` | `brew install typst` | `scoop install typst` / `choco install typst` |
| `diagrams` (mingrammer) | Diagram-as-code 专业图标集 | `pip install diagrams`（任一平台同） | 同左 | 同左 |
| `blockdiag` 家族 | 泳道活动图、时序图 | `pip install blockdiag actdiag seqdiag nwdiag` | 同左 | 同左 |
| `mermaid` (mmdc) | 流程图/时序图/状态图（root 下自动 `--no-sandbox`） | `npm install -g @mermaid-js/mermaid-cli`（需 Node ≥18） | 同左 | 同左（`winget install OpenJS.NodeJS`） |
| `pikchr` | 轻量机制/序列示意 DSL（SQLite 项目；注意颜色用 `fill 0xRRGGBB` 数值而非引号字符串） | pikchr.org tarball 编译：`tar xzf Pikchr.tar.gz && cd Pikchr && make && sudo install pikchr /usr/local/bin/` | 同左（自带 clang） | WSL2 编译，或 mingw 交叉编译；原生 Windows 无官方二进制 |
| `resvg` | 高保真 SVG 栅格化（可选增强） | GitHub linebender/resvg release 二进制 → `/usr/local/bin/resvg` | `brew install resvg` | release 二进制解压入 `PATH` |
| `cairosvg` | 纯 Python SVG→PDF/PNG 兜底转换器（无 rsvg/inkscape 时的最小回退） | `pip install cairosvg` | 同左（需 `brew install cairo pango gdk-pixbuf libffi`） | 同左（需 GTK runtime 或改用 WSL2） |
| `SciencePlots` | 数据图期刊级几何规范 | `pip install SciencePlots` | 同左 | 同左 |
| `inkscape` | SVG 转换回退 | `sudo apt install inkscape` | `brew install --cask inkscape` | `choco install inkscape` |
| `svgo` | SVG 瘦身 | `npm install -g svgo` | 同左 | 同左 |

**明确不采用（评估记录）**: `blender`（无头黑屏不可修复）、`plotly+kaleido`（依赖 headless Chrome）。`Memslides`/`AutoFigure-Edit` 仅借鉴方法论（scoped revision / 分阶段装配），不作为引擎集成——保持单一链路 `render_figure.py`。

## 3. 组图装配（契约 §7，SCI 一区规范）

多面板组图经 `.composite.json` 清单装配（单一入口内置 composite 引擎，无额外依赖）：`python scripts/plotting/render_figure.py fig.composite.json --out figures/figN/ --label figN --caption "..."`。面板数硬上限 9（超出直接拒绝）；(a)(b)(c)… 编号标签自动生成于面板上方预留条；按叙事单元组版（Nature/Science/Cell 逻辑）。

## 4. 字体（与 LaTeX 正文一致的关键）

代码**自动发现**字体（fontconfig `fc-match` 优先，否则按平台扫描目录，用户目录优先），无需配置；只需把字体装到系统能找到的位置：

### TeX Gyre（Times/Palatino/Helvetica 的学术克隆，matplotlib/LaTeX 共用）

```bash
# Linux：从 texlive 自带字体复制（或 dnf install tex-gyre / brew 装 mactex 后同理）
mkdir -p ~/.local/share/fonts/texgyre
cp /usr/share/texmf/fonts/opentype/public/tex-gyre/texgyre{termes,pagella,heros}-{regular,bold,italic,bolditalic}.otf ~/.local/share/fonts/texgyre/
fc-cache -f

# macOS：MacTeX 已含（/usr/local/texlive/.../texmf-dist/fonts/opentype/public/tex-gyre/），
#        复制到 ~/Library/Fonts/ 后系统可见
# Windows：从 CTAN 下载 tex-gyre 包解压，TTF/OTF 双击安装（或复制到
#        %LOCALAPPDATA%\Microsoft\Windows\Fonts）
```

### Liberation Sans（d2 `--font-*` 注入，Helvetica 度量兼容）

```bash
# Linux
sudo apt install fonts-liberation        # Debian/Ubuntu
sudo dnf install liberation-sans-fonts   # Fedora
# macOS
brew install --cask font-liberation      # 或从 Liberation 官网下载 TTF 装入 ~/Library/Fonts
# Windows：多数系统已自带 Liberation（部分 Office 安装附带）；
#        没有则 choco install liberation-fonts 或手动下载 TTF 安装
```

找不到 Liberation 时，d2 自动回退到其内嵌 Source Sans Pro（不会报错）。

## 5. Windows 专项说明

1. **推荐 WSL2**（`wsl --install -d Ubuntu`）：一行获得与 Linux 完全一致的工具链（apt 全部可用），本手册 Linux 列命令直接照抄。SciForge-OSS 在 WSL2 内即"Linux 部署"。
2. **原生 Windows** 也全部可行：上表 Windows 列逐项安装；注意：
   - PATH 生效：新装工具需重开终端
   - `pikchr` 无官方 Windows 二进制 → 走 WSL2 或跳过（可选引擎）
   - `cairosvg` 依赖 GTK → 装不全时优先保证 `rsvg-convert`（MSYS2）或 WSL2
   - mermaid 在 Windows 无需 `--no-sandbox`（代码自动判断，仅 root/超级用户场景启用）
3. **路径**：代码全部使用 `pathlib.Path` 与相对路径（图目录、spec 引用均相对），跨盘符无碍。

## 6. 国内镜像（网络慢时）

```bash
# pip：aliyun 镜像
pip config set global.index-url http://mirrors.aliyun.com/pypi/simple
pip config set global.trusted-host mirrors.aliyun.com

# apt：华为云/清华源（编辑 /etc/apt/sources.list）
# d2/typst/resvg 二进制：经 HTTP 代理下载（如 mihomo 混合端口 8099）
https_proxy=http://127.0.0.1:8099 curl -fsSL https://d2lang.com/install.sh | sh -s --
https_proxy=http://127.0.0.1:8099 curl -sL -o /tmp/typst.tar.xz \
  https://github.com/typst/typst/releases/download/v0.13.1/typst-x86_64-unknown-linux-musl.tar.xz
```

## 7. 运行时图标词汇（契约 §5.5）

图标资产库**不随仓库分发**；agent 运行时从白名单来源抓取专业图标（bioicons.com 生医、Tabler/Lucide/Feather 技术通用、Font Awesome Free、d2 bundled），强制经 `sciforge_style.recolor_icon()` 重着色为莫兰迪后使用，来源与许可记录在图的 `revision_log.md`。抓取失败回退 agent 手绘，不阻塞管线。国内网络经 mihomo 代理（8099）访问。

## 8. 验证清单（装完逐项核对）

```bash
# 1) 环境自检——期望 verdict: READY
python scripts/plotting/render_figure.py --doctor

# 2) 数据图冒烟（任一平台）
python scripts/plotting/render_figure.py path/to/render.py --out /tmp/t1 --label t1 --strict

# 3) d2 架构图冒烟
printf 'a -> b\nb -> c\n' > /tmp/t.d2
python scripts/plotting/render_figure.py /tmp/t.d2 --out /tmp/t2 --label t2 --strict

# 4) 组图冒烟（两个面板 + (a)(b) 标签）
python scripts/plotting/render_figure.py fig.composite.json --out /tmp/t3 --label t3 --strict
```

三项均输出 `[audit: PASS]`（或仅 A2/A5 WARN）即复刻成功。
