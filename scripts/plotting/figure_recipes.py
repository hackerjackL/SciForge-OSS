#!/usr/bin/env python3
"""SciForge figure recipes — declarative, layout-locked publication plots (v1.6.0).

WHY: the render.py path let the model freely choose legend position, tick style,
band vs bar, label sizes — every figure drifted from every other. A recipe
inverts control: the model supplies DATA + LABELS + a small enum of semantic
choices; the LAYOUT is fixed code shared by every figure in the corpus. This is
the "toolchain unity" the figure-quality contract demands, learned from the
proplot/mplhep/SciencePlots style-registry pattern (one theme object consumed
by all plots) and the journal-figure conventions (error type always labeled,
n always stated, panel letters always (a)(b)(c)).

USAGE (from render_figure.py, or standalone):
    python3 figure_recipes.py spec.recipe.json --out <dir>
    # spec: {"recipe": "line-comparison", "size": "single|full|panel2|panel3",
    #        "x_label": ..., "y_label": ..., "series": [{"name","x","y","err","stat"}],
    #        "log_x": false, "log_y": false, "title": null, "panel_label": null,
    #        "hlines": [...], "annotate": [...]}

RECIPES (each locks geometry, fonts, palette, legend, error semantics):
    line-comparison  multi-series lines, marker+color double encoding,
                     error BANDS (stat: sd|sem|ci95, always labeled)
    bar-grouped      grouped bars, error BARS, value-free axes, category labels
    scatter-fit      points + OLS fit + 95% CI ribbon + R2/r annotation
    heatmap          matrix + Layer-2 colormap + colorbar + optional cell values
    hist-dist        overlaid step histograms/densities per group (alpha-locked)
    forest-plot      effect sizes + CI whiskers + zero line + pooled diamond
    panel-grid       compose sub-recipes into (a)(b)(c) panels, one shared theme

Every recipe calls sciforge_style.apply_matplotlib_style() first (dopamine
visibility-ordered cycle, black-on-white, Nature floors) and saves output.pdf
in CWD — the same single-entry contract as render.py, minus the freedom.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sciforge_style as st  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SIZE_FIGSIZE = {
    "single": st.figsize_single, "full": st.figsize_full,
    "panel2": lambda: st.figsize_panel(2), "panel3": lambda: st.figsize_panel(3),
}
STAT_LABEL = {"sd": "±1 SD", "sem": "±1 SEM", "ci95": "95% CI"}
RECIPES = {}


def recipe(name):
    def deco(fn):
        RECIPES[name] = fn
        return fn
    return deco


# ---------------- shared frame helpers (the locked degrees of freedom) ----------------

def _fig(spec: dict):
    st.apply_matplotlib_style()
    size = spec.get("size", "single")
    if size not in SIZE_FIGSIZE:
        raise ValueError(f"size must be one of {sorted(SIZE_FIGSIZE)}")
    w, h = SIZE_FIGSIZE[size]()
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlabel(spec.get("x_label", ""))
    ax.set_ylabel(spec.get("y_label", ""))
    ax.set_xscale("log" if spec.get("log_x") else "linear")
    ax.set_yscale("log" if spec.get("log_y") else "linear")
    if spec.get("title"):
        ax.set_title(spec["title"], fontsize=st.NATURE_FLOOR["title"])
    for y in spec.get("hlines", []):
        ax.axhline(y, color=st.TOKENS["ink-soft"], lw=st.LINEWIDTH["secondary"], ls="--")
    return fig, ax


def _finish(fig, ax, spec: Path | dict, outdir: Path):
    if isinstance(spec, dict) and spec.get("legend", True):
        handles, _labels = ax.get_legend_handles_labels()
        if handles:  # forest-plot labels via y-ticks, not a legend — skip cleanly
            st.legend_top(ax, ncol=spec.get("legend_ncols") or min(len(handles), 4))
    if spec.get("panel_label"):
        ax.text(-0.16, 1.08, f"({spec['panel_label']})", transform=ax.transAxes,
                fontsize=st.NATURE_FLOOR["title"], fontweight="bold")
    fig.savefig(outdir / "output.pdf")
    plt.close(fig)


def _err_label(series, stat):
    return f"{series['name']} ({STAT_LABEL.get(stat, stat)})" if stat else series["name"]


# ---------------- recipes ----------------

@recipe("line-comparison")
def _line(spec, outdir):
    fig, ax = _fig(spec)
    for i, s in enumerate(spec["series"]):
        sty = st.series_style(i)
        x, y = np.asarray(s["x"], float), np.asarray(s["y"], float)
        ax.plot(x, y, marker=sty["marker"], ms=st.MARKER_SIZE_MIN,
                lw=st.LINEWIDTH["primary"], color=sty["color"],
                label=_err_label(s, s.get("stat")))
        if s.get("err") and s.get("stat"):
            st.add_error_band(ax, x, y, np.asarray(s["err"], float), sty["color"])
    _finish(fig, ax, spec, outdir)


@recipe("bar-grouped")
def _bar(spec, outdir):
    fig, ax = _fig(spec)
    groups = spec["groups"]                      # category labels
    series = spec["series"]                      # [{name, values, err?, stat?}]
    n, m = len(groups), len(series)
    width = 0.8 / m
    xs = np.arange(n)
    for j, s in enumerate(series):
        sty = st.series_style(j)
        pos = xs + (j - (m - 1) / 2) * width
        y = np.asarray(s["values"], float)
        e = np.asarray(s["err"], float) if s.get("err") else None
        ax.bar(pos, y, width * 0.9, color=sty["color"], edgecolor=st.stroke_for(sty["color"]),
               linewidth=0.8, yerr=e, capsize=3, error_kw={"lw": st.LINEWIDTH["secondary"]},
               label=_err_label(s, s.get("stat")))
    ax.set_xticks(xs)
    ax.set_xticklabels(groups)
    _finish(fig, ax, spec, outdir)


@recipe("scatter-fit")
def _scatter(spec, outdir):
    fig, ax = _fig(spec)
    for i, s in enumerate(spec["series"]):
        sty = st.series_style(i)
        x = np.asarray(s["x"], float); y = np.asarray(s["y"], float)
        ax.scatter(x, y, s=st.MARKER_SIZE_MIN ** 1.5, marker=sty["marker"],
                   facecolor=sty["color"], edgecolor=st.stroke_for(sty["color"]),
                   linewidth=0.6, alpha=0.85, label=s["name"])
        if spec.get("fit", True) and len(x) > 2:
            b1, b0 = np.polyfit(x, y, 1)
            xs = np.linspace(x.min(), x.max(), 100)
            ax.plot(xs, b0 + b1 * xs, color=sty["color"], lw=st.LINEWIDTH["primary"], ls="--")
            r = np.corrcoef(x, y)[0, 1]
            if spec.get("annotate_r", True):
                ax.annotate(f"r = {r:+.2f}", xy=(0.02, 0.97 - 0.12 * i),
                            xycoords="axes fraction", fontsize=st.NATURE_FLOOR["annotation"])
    _finish(fig, ax, spec, outdir)


@recipe("heatmap")
def _heatmap(spec, outdir):
    st.apply_matplotlib_style()
    size = spec.get("size", "single")
    w, h = SIZE_FIGSIZE[size]()
    fig, ax = plt.subplots(figsize=(w, h))
    data = np.asarray(spec["matrix"], float)
    cmap = spec.get("colormap", "viridis")
    if cmap not in st.LAYER2_COLORMAPS:
        raise ValueError(f"colormap must be one of {st.LAYER2_COLORMAPS} (Layer 2 rule)")
    im = ax.imshow(data, cmap=cmap, aspect=spec.get("aspect", "auto"),
                   vmin=spec.get("vmin"), vmax=spec.get("vmax"))
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label(spec.get("cbar_label", ""))
    cbar.ax.tick_params(labelsize=st.NATURE_FLOOR["tick_label"])
    cbar.set_ticks([]) if spec.get("bare_cbar") else None
    if spec.get("cell_values"):
        mid = (float(np.nanmin(data)) + float(np.nanmax(data))) / 2
        for (r, c, v) in spec["cell_values"]:
            ax.text(c, r, str(v), ha="center", va="center",
                    fontsize=st.NATURE_FLOOR["annotation"],
                    color="#FFFFFF" if float(data[r][c]) > mid else "#000000")
    if spec.get("x_labels"):
        ax.set_xticks(range(len(data[0]))); ax.set_xticklabels(spec["x_labels"],
                                                               fontsize=st.NATURE_FLOOR["tick_label"])
    if spec.get("y_labels"):
        ax.set_yticks(range(len(data))); ax.set_yticklabels(spec["y_labels"],
                                                            fontsize=st.NATURE_FLOOR["tick_label"])
    ax.set_xlabel(spec.get("x_label", "")); ax.set_ylabel(spec.get("y_label", ""))
    if spec.get("panel_label"):
        ax.text(-0.16, 1.08, f"({spec['panel_label']})", transform=ax.transAxes,
                fontsize=st.NATURE_FLOOR["title"], fontweight="bold")
    fig.savefig(outdir / "output.pdf")
    plt.close(fig)


@recipe("hist-dist")
def _hist(spec, outdir):
    fig, ax = _fig(spec)
    bins = spec.get("bins", 20)
    for i, s in enumerate(spec["series"]):
        sty = st.series_style(i)
        ax.hist(np.asarray(s["values"], float), bins=bins, histtype="step",
                lw=st.LINEWIDTH["primary"], color=sty["color"],
                label=_err_label(s, None))
    _finish(fig, ax, spec, outdir)


@recipe("forest-plot")
def _forest(spec, outdir):
    fig, ax = _fig(spec)
    rows = spec["rows"]  # [{label, effect, lo, hi}]
    ys = np.arange(len(rows))[::-1]
    for y, r in zip(ys, rows):
        sty = st.series_style(0)
        ax.plot([r["lo"], r["hi"]], [y, y], color=st.TOKENS["ink"],
                lw=st.LINEWIDTH["secondary"], solid_capstyle="butt")
        ax.plot([r["lo"], r["lo"]], [y - .12, y + .12], color=st.TOKENS["ink"], lw=1.2)
        ax.plot([r["hi"], r["hi"]], [y - .12, y + .12], color=st.TOKENS["ink"], lw=1.2)
        ax.scatter([r["effect"]], [y], marker="D", s=st.MARKER_SIZE_MIN ** 1.8,
                   color=sty["color"], edgecolor=st.stroke_for(sty["color"]), zorder=3)
    if spec.get("pooled"):
        p = spec["pooled"]
        y = -1
        ax.plot([p["lo"], p["hi"]], [y, y], color=st.TOKENS["crimson"], lw=st.LINEWIDTH["primary"])
        w = (p["hi"] - p["lo"]) / 2
        ax.fill([p["effect"] - w, p["effect"], p["effect"] + w, p["effect"]],
                [y, y + .3, y, y - .3], color=st.TOKENS["crimson"],
                edgecolor=st.stroke_for(st.TOKENS["crimson"]))
    ax.axvline(spec.get("null", 0), color=st.TOKENS["ink-soft"], ls="--", lw=1)
    ax.set_yticks(list(ys) + ([-1] if spec.get("pooled") else []))
    ax.set_yticklabels([r["label"] for r in rows] + (["pooled"] if spec.get("pooled") else []),
                       fontsize=st.NATURE_FLOOR["tick_label"])
    ax.set_ylim(-1.8, len(rows) - 0.2)
    _finish(fig, ax, spec, outdir)


@recipe("panel-grid")
def _panel(spec, outdir):
    """Compose sub-recipes: {"panels":[{"recipe":...,...},...], "cols":2}.
    Each panel gets (a)(b)(c); one shared theme; sizes fixed by cols."""
    panels = spec["panels"]
    cols = spec.get("cols", min(len(panels), 2))
    rows = (len(panels) + cols - 1) // cols
    st.apply_matplotlib_style()
    fig, axes = plt.subplots(rows, cols, figsize=st.figsize_full(aspect=0.62 * rows / cols))
    axes = np.atleast_1d(axes).ravel()
    letters = "abcdefgh"
    # Nature multi-panel convention: ONE figure-level legend, not per-panel
    # legends (per-panel legend_top collides with panel letters and the row
    # above's x-labels in a grid). Panels render legend-less; handles merge.
    seen, handles, labels = set(), [], []
    for i, (p, ax) in enumerate(zip(panels, axes)):
        p = dict(p); p.setdefault("size", "panel2" if cols == 2 else "panel3")
        p["panel_label"] = letters[i]
        p["legend"] = False
        _render_to_ax(p, ax)
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in seen:
                seen.add(lab); handles.append(h); labels.append(lab)
    for ax in axes[len(panels):]:
        ax.axis("off")
    fig.subplots_adjust(hspace=0.72, wspace=0.42, top=0.96, bottom=0.17 if handles else 0.11)
    if handles and spec.get("legend", True):
        fig.legend(handles, labels, loc="lower center",
                   bbox_to_anchor=(0.5, 0.0), ncol=min(len(handles), 4),
                   frameon=False, fontsize=st.NATURE_FLOOR["legend"],
                   markerscale=0.6)  # scatter handles otherwise dwarf the text
    fig.savefig(outdir / "output.pdf")
    plt.close(fig)


def _render_to_ax(spec, ax):
    """Single-recipe rendering onto a provided axes (panel-grid reuse)."""
    kind = spec["recipe"]
    if kind == "line-comparison":
        for i, s in enumerate(spec["series"]):
            sty = st.series_style(i)
            x, y = np.asarray(s["x"], float), np.asarray(s["y"], float)
            ax.plot(x, y, marker=sty["marker"], ms=st.MARKER_SIZE_MIN,
                    lw=st.LINEWIDTH["primary"], color=sty["color"],
                    label=_err_label(s, s.get("stat")))
            if s.get("err") and s.get("stat"):
                st.add_error_band(ax, x, y, np.asarray(s["err"], float), sty["color"])
    elif kind == "bar-grouped":
        groups, series = spec["groups"], spec["series"]
        n, m = len(groups), len(series)
        width = 0.8 / m; xs = np.arange(n)
        for j, s in enumerate(series):
            sty = st.series_style(j)
            ax.bar(xs + (j - (m - 1) / 2) * width, np.asarray(s["values"], float),
                   width * 0.9, color=sty["color"],
                   edgecolor=st.stroke_for(sty["color"]), linewidth=0.8,
                   yerr=s.get("err"), capsize=3, label=_err_label(s, s.get("stat")))
        ax.set_xticks(xs); ax.set_xticklabels(groups)
    elif kind == "scatter-fit":
        for i, s in enumerate(spec["series"]):
            sty = st.series_style(i)
            x = np.asarray(s["x"], float); y = np.asarray(s["y"], float)
            ax.scatter(x, y, s=st.MARKER_SIZE_MIN ** 1.5, marker=sty["marker"],
                       facecolor=sty["color"], edgecolor=st.stroke_for(sty["color"]),
                       alpha=0.85, label=s["name"])
            if spec.get("fit", True) and len(x) > 2:  # same regression as the
                b1, b0 = np.polyfit(x, y, 1)          # standalone scatter-fit
                xs = np.linspace(x.min(), x.max(), 100)
                ax.plot(xs, b0 + b1 * xs, color=sty["color"],
                        lw=st.LINEWIDTH["primary"], ls="--")
    elif kind == "hist-dist":
        for i, s in enumerate(spec["series"]):
            sty = st.series_style(i)
            ax.hist(np.asarray(s["values"], float), bins=spec.get("bins", 20),
                    histtype="step", lw=st.LINEWIDTH["primary"], color=sty["color"],
                    label=s["name"])
    else:
        raise ValueError(f"panel-grid sub-recipe must be one of "
                         f"line-comparison/bar-grouped/scatter-fit/hist-dist, got {kind}")
    ax.set_xlabel(spec.get("x_label", "")); ax.set_ylabel(spec.get("y_label", ""))
    if spec.get("log_y"):
        ax.set_yscale("log")
    if spec.get("legend", True) and ax.get_legend_handles_labels()[0]:
        st.legend_top(ax)  # unified with the single-figure path (out-of-axes,
                           # never occludes the data — the panel bug was upper-left)
    if spec.get("panel_label"):
        # inside-axes top-left (Nature convention): a per-panel legend no longer
        # sits above the axes, and outside placement collides with the row
        # above's x-labels in a grid.
        ax.text(0.02, 0.97, f"({spec['panel_label']})", transform=ax.transAxes,
                fontsize=st.NATURE_FLOOR["title"], fontweight="bold", va="top")


def render(spec: dict, outdir: Path) -> None:
    kind = spec.get("recipe")
    if kind not in RECIPES:
        raise ValueError(f"unknown recipe '{kind}'; available: {sorted(RECIPES)}")
    outdir.mkdir(parents=True, exist_ok=True)
    RECIPES[kind](spec, outdir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text())
    outdir = a.out or a.spec.parent
    render(spec, outdir)
    print(f"OK recipe={spec['recipe']} -> {outdir/'output.pdf'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
