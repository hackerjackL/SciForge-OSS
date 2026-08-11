# SciForge-OSS Figure Toolchain — INSTALL (Cross-Platform Replication Manual)

> **Single entry point**: every figure (data plots + architecture/flow/mechanism/composite figures) is produced only through
> `python scripts/plotting/render_figure.py` (dual PDF+SVG output + embedded Nature-grade audit).
> After installing dependencies, run the self-check first: `python scripts/plotting/render_figure.py --doctor`
>
> **Cross-platform**: Linux / macOS / Windows are all supported. The code contains **no machine-specific absolute paths** — fonts are
> discovered dynamically via fontconfig → per-platform directory scans, and tools are located via `PATH` (`shutil.which`).
> On Windows, WSL2 (Ubuntu) is recommended for an experience fully identical to Linux; native Windows works for everything too (see below).

## 0. Quick Replication (Minimal Viable Set)

Only 4 items are needed to get data plots + d2 architecture diagrams + audit running:

| Component | Linux (apt) | macOS (brew) | Windows |
|------|------------|--------------|---------|
| Python ≥3.10 + matplotlib/numpy/Pillow | `sudo apt install python3-pip && pip install matplotlib numpy Pillow` | `brew install python && pip install matplotlib numpy Pillow` | Install from [python.org](https://python.org) or `winget install Python.Python.3.12`, then the same pip command as the left |
| d2 | `curl -fsSL https://d2lang.com/install.sh \| sh -s --` (via proxy in China) | `brew install d2` | `scoop install d2` (or the PowerShell version of the install script) |
| librsvg (`rsvg-convert`) | `sudo apt install librsvg2-bin` | `brew install librsvg` | Install MSYS2 first, then `pacman -S mingw-w64-x86_64-librsvg`, or use WSL2 |
| poppler (`pdftoppm`) | `sudo apt install poppler-utils` | `brew install poppler` | `choco install poppler` or WSL2 |

```bash
python scripts/plotting/render_figure.py --doctor   # all green means minimally viable
```

## 1. Core Dependencies (Required)

| Tool | Purpose | Linux (apt) | macOS (brew) | Windows |
|------|------|------------|--------------|---------|
| `d2` (v0.7+) | Complex architecture/flow/topology diagrams (preferred engine) | Install script (see above) | `brew install d2` | `scoop install d2` |
| `graphviz` | Graph layout fallback | `sudo apt install graphviz` | `brew install graphviz` | `choco install graphviz` |
| `rsvg-convert` | SVG → PDF/PNG | `sudo apt install librsvg2-bin` | `brew install librsvg` | MSYS2 `librsvg` / WSL2 |
| texlive (pdflatex + tikz) | Theory diagrams/commutative diagrams + PDF rasterization | `sudo apt install texlive-latex-base texlive-pictures texlive-science texlive-latex-extra texlive-extra-utils` | `brew install --cask mactex-no-gui`, or `basictex` + `tlmgr install tikz standalone pdfcrop` | [MiKTeX](https://miktex.org) (`miktex setup`) or the TeX Live installer; WSL2 same as Linux |
| `poppler-utils` (`pdftoppm`/`pdfinfo`) | PDF → PNG, rasterizing composite-figure panels | `sudo apt install poppler-utils` | `brew install poppler` | `choco install poppler` / WSL2 |
| Python: `matplotlib`, `numpy`, `Pillow` | Data-plot pipeline + audit | `pip install matplotlib numpy Pillow` (aliyun mirror: see §6) | Same as left | Same as left |

> **Fedora/RHEL/openSUSE**: replace `apt install` with `dnf install`; package names are essentially the same
> (`graphviz`, `librsvg2-tools`, `texlive-scheme-basic`, `poppler-utils`).
> **Arch**: `pacman -S graphviz librsvg texlive-most poppler`.

## 2. Enhancement Engines (Recommended — they set the ceiling of the "premium look")

| Tool | Purpose | Linux | macOS | Windows |
|------|------|-------|-------|---------|
| `asymptote` | Math/geometry/mechanism schematics (vector) | `sudo apt install asymptote` | `brew install asymptote` | `choco install asymptote` (or the official-site msi) |
| `typst` | Millisecond-speed declarative diagrams (fletcher/CeTZ) | GitHub release binary → `~/.local/bin/typst` | `brew install typst` | `scoop install typst` / `choco install typst` |
| `diagrams` (mingrammer) | Diagram-as-code professional icon set | `pip install diagrams` (same on any platform) | Same as left | Same as left |
| `blockdiag` family | Swimlane activity diagrams, sequence diagrams | `pip install blockdiag actdiag seqdiag nwdiag` | Same as left | Same as left |
| `mermaid` (mmdc) | Flowcharts/sequence diagrams/state diagrams (auto `--no-sandbox` when running as root) | `npm install -g @mermaid-js/mermaid-cli` (requires Node ≥18) | Same as left | Same as left (`winget install OpenJS.NodeJS`) |
| `pikchr` | Lightweight mechanism/sequence schematic DSL (SQLite project; note that colors use the `fill 0xRRGGBB` numeric form, not quoted strings) | Compile from the pikchr.org tarball: `tar xzf Pikchr.tar.gz && cd Pikchr && make && sudo install pikchr /usr/local/bin/` | Same as left (clang ships with the system) | Compile under WSL2, or cross-compile with mingw; no official binary for native Windows |
| `resvg` | High-fidelity SVG rasterization (optional enhancement) | GitHub linebender/resvg release binary → `/usr/local/bin/resvg` | `brew install resvg` | Unpack the release binary into `PATH` |
| `cairosvg` | Pure-Python SVG→PDF/PNG fallback converter (minimal fallback when rsvg/inkscape are absent) | `pip install cairosvg` | Same as left (requires `brew install cairo pango gdk-pixbuf libffi`) | Same as left (requires the GTK runtime, or switch to WSL2) |
| `SciencePlots` | Journal-grade geometric conventions for data plots | `pip install SciencePlots` | Same as left | Same as left |
| `inkscape` | SVG conversion fallback | `sudo apt install inkscape` | `brew install --cask inkscape` | `choco install inkscape` |
| `svgo` | SVG slimming | `npm install -g svgo` | Same as left | Same as left |

**Explicitly not adopted (evaluation record)**: `blender` (the headless black-screen problem is unfixable), `plotly+kaleido` (depends on headless Chrome). `Memslides`/`AutoFigure-Edit` are consulted for methodology only (scoped revision / staged assembly), not integrated as engines — keep the single pipeline `render_figure.py`.

## 3. Composite-Figure Assembly (Contract §7, SCI top-journal standards)

Multi-panel composite figures are assembled via `.composite.json` manifests (the composite engine is built into the single entry point; no extra dependencies): `python scripts/plotting/render_figure.py fig.composite.json --out figures/figN/ --label figN --caption "..."`. The panel count has a hard cap of 9 (going over is rejected outright); the (a)(b)(c)… numbering labels are generated automatically in the reserved strip above each panel; layout follows narrative units (Nature/Science/Cell logic).

## 4. Fonts (The key to consistency with the LaTeX body text)

The code **auto-discovers** fonts (fontconfig `fc-match` first, otherwise per-platform directory scans, with user directories taking priority); no configuration is needed — just install the fonts somewhere the system can find them:

### TeX Gyre (academic clones of Times/Palatino/Helvetica, shared by matplotlib/LaTeX)

```bash
# Linux: copy from the fonts bundled with texlive (or likewise after dnf install tex-gyre / installing mactex via brew)
mkdir -p ~/.local/share/fonts/texgyre
cp /usr/share/texmf/fonts/opentype/public/tex-gyre/texgyre{termes,pagella,heros}-{regular,bold,italic,bolditalic}.otf ~/.local/share/fonts/texgyre/
fc-cache -f

# macOS: MacTeX already includes them (/usr/local/texlive/.../texmf-dist/fonts/opentype/public/tex-gyre/);
#        after copying them to ~/Library/Fonts/ the system can see them
# Windows: download the tex-gyre package from CTAN and unzip it; double-click the TTF/OTF to install (or copy them to
#        %LOCALAPPDATA%\Microsoft\Windows\Fonts)
```

### Liberation Sans (injected via d2 `--font-*`, Helvetica-metrics compatible)

```bash
# Linux
sudo apt install fonts-liberation        # Debian/Ubuntu
sudo dnf install liberation-sans-fonts   # Fedora
# macOS
brew install --cask font-liberation      # or download the TTFs from the Liberation official site and place them in ~/Library/Fonts
# Windows: most systems already ship Liberation (bundled with some Office installs);
#        if not, choco install liberation-fonts or manually download and install the TTFs
```

When Liberation is not found, d2 automatically falls back to its embedded Source Sans Pro (no error is raised).

## 5. Windows-Specific Notes

1. **WSL2 recommended** (`wsl --install -d Ubuntu`): one line gives you a toolchain fully identical to Linux (all apt commands work); just copy the Linux-column commands in this manual verbatim. SciForge-OSS inside WSL2 counts as a "Linux deployment".
2. **Native Windows** also works for everything: install item by item from the Windows column of the tables above; notes:
   - PATH activation: newly installed tools require reopening the terminal
   - `pikchr` has no official Windows binary → use WSL2 or skip it (optional engine)
   - `cairosvg` depends on GTK → if that cannot be fully installed, prioritize making sure `rsvg-convert` (MSYS2) or WSL2 is in place
   - mermaid does not need `--no-sandbox` on Windows (the code decides automatically; it is only enabled for the root/superuser scenario)
3. **Paths**: the code uses `pathlib.Path` and relative paths throughout (figure directories and spec references are all relative), so crossing drive letters causes no issue.

## 6. China Mirrors (for slow networks)

```bash
# pip: aliyun mirror
pip config set global.index-url http://mirrors.aliyun.com/pypi/simple
pip config set global.trusted-host mirrors.aliyun.com

# apt: Huawei Cloud / Tsinghua mirrors (edit /etc/apt/sources.list)
# d2/typst/resvg binaries: download via an HTTP proxy (e.g., the mihomo mixed port 8099)
https_proxy=http://127.0.0.1:8099 curl -fsSL https://d2lang.com/install.sh | sh -s --
https_proxy=http://127.0.0.1:8099 curl -sL -o /tmp/typst.tar.xz \
  https://github.com/typst/typst/releases/download/v0.13.1/typst-x86_64-unknown-linux-musl.tar.xz
```

## 7. Runtime Icon Vocabulary (Contract §5.5)

The icon asset library is **not distributed with the repository**; at runtime the agent fetches professional icons from whitelisted sources (bioicons.com for biomedical, Tabler/Lucide/Feather for general tech, Font Awesome Free, d2 bundled), and they are mandatorily recolored to the Morandi palette via `sciforge_style.recolor_icon()` before use, with sources and licenses recorded in the figure's `revision_log.md`. On fetch failure it falls back to agent hand-drawing, without blocking the pipeline. Networks in China connect through the mihomo proxy (8099).

## 8. Verification Checklist (check item by item after installation)

```bash
# 1) Environment self-check — expected verdict: READY
python scripts/plotting/render_figure.py --doctor

# 2) Data-plot smoke test (any platform)
python scripts/plotting/render_figure.py path/to/render.py --out /tmp/t1 --label t1 --strict

# 3) d2 architecture-diagram smoke test
printf 'a -> b\nb -> c\n' > /tmp/t.d2
python scripts/plotting/render_figure.py /tmp/t.d2 --out /tmp/t2 --label t2 --strict

# 4) Composite-figure smoke test (two panels + (a)(b) labels)
python scripts/plotting/render_figure.py fig.composite.json --out /tmp/t3 --label t3 --strict
```

If all three print `[audit: PASS]` (or only A2/A5 WARN), the replication succeeded.

## 9. v1.4.0 Notes (no new dependencies; boundary clarifications)

- **Print-size / black-text contract (v2.2 design system)** requires **no new
  dependencies** — it is pure `sciforge_style.py` rcParams/token changes
  (black `#000000` text on `#FFFFFF`, raised font floors, `figsize_*` helpers,
  composite default ≤2 columns). Re-render existing figures to pick it up.
- **The skill ships NO model and NO eval harness.** The run-while-testing
  evaluation harness lives OUTSIDE this repository (see `sciforge-eval-runner`);
  the skill itself contains only pure pytest tests (`tests/`, `fixtures/`) that
  need nothing beyond `pip install pytest` plus the core figure deps above.
  Model endpoints (for actually running the pipeline) are configured by the
  deployment, never inside the skill, and no model name is hard-coded anywhere
  in the skill.
- **Python floor**: ≥3.10 (the toolchain is stdlib + matplotlib/numpy/Pillow;
  `SciencePlots` is optional but recommended for journal-grade geometry).
