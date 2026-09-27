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
        if not isinstance(p, dict) or not {"effect", "lo", "hi"} <= set(p):
            raise ValueError(
                "forest-plot 'pooled' must be an object {effect, lo, hi} — "
                "a boolean is not a pooled estimate (figure-layout-contract §2)")
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


# ---- page-archetype layout presets (figure-layout-contract.md §3) ----
# Each preset locks GridSpec geometry + subplots_adjust; the model fills content only.
# height_ratios / width_ratios come from the Nature-2026 corpus patterns.
# Geometry notes (tuned against docs/assets/layout-archetype-gallery v2 collisions):
#   hspace must absorb (x-label of this row) + (panel letter of next row);
#   wspace must absorb (y-label of left panel) + (panel letter of right panel);
#   bottom margin is computed at render time from the figure-level legend rows.
LAYOUTS = {
    # equal grid spans: comparable panels must share width/height/gutter (A11)
    "equal-grid":       {"gs": None, "hspace": 1.10, "wspace": 0.55,
                         "aspect": 0.78},
    # P12 / Archetype 3.1: schematic hero 45-60% height + quieter quant row
    # hero x-label + quant-row panel letters need a tall gap between the bands
    "schematic-led":    {"gs": (2, 4), "height_ratios": [2.0, 1.15],
                         "hspace": 0.85, "wspace": 0.70,
                         "hero_span": (0, slice(0, 4)), "hero_frac": (0.45, 0.60),
                         "aspect": 0.72},
    # P15 / Archetype 3.2: one conceptually central panel dominates
    "asymmetric-hero":  {"gs": (2, 4), "height_ratios": [1.0, 1.0],
                         "hspace": 1.00, "wspace": 0.70,
                         "hero_span": (slice(0, 2), 3),
                         "aspect": 0.70},
    # P14 / Archetype 3.4: longitudinal -> forest -> summary, shared legend above
    "clinical-triptych": {"gs": (3, 3), "height_ratios": [1.0, 1.35, 0.8],
                          "hspace": 1.15, "wspace": 0.75,
                          "aspect": 0.95},
}
DEFAULT_LAYOUT = "equal-grid"


def _write_panel_manifest(fig, axes, spec, outdir):
    """Emit panel_layout.json (schema of nature-skills audit_panel_alignment).

    figure_audit.py A11 consumes this to enforce the 1.5 pt shared-edge /
    width / height / gutter tolerance. Comparable groups are inferred from
    equal grid spans; asymmetric heroes are recorded as exemptions.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = fig.dpi_scale_trans.inverted()
    panels = []
    for i, ax in enumerate(axes):
        if not ax.axison and not ax.get_children():
            continue
        bb = ax.get_window_extent(renderer=r).transformed(inv)
        # convert inches -> pt (1 in = 72 pt)
        panels.append({
            "id": f"p{i}",
            "bbox_pt": {"left": round(bb.x0 * 72, 2), "bottom": round(bb.y0 * 72, 2),
                        "right": round(bb.x1 * 72, 2), "top": round(bb.y1 * 72, 2)},
        })
    layout_name = spec.get("layout", DEFAULT_LAYOUT)
    manifest = {
        "schema_version": 1,
        "figure": {
            "width_pt": round(fig.get_figwidth() * 72, 2),
            "height_pt": round(fig.get_figheight() * 72, 2),
        },
        "panels": panels,
        "layout_preset": layout_name,
        "tolerance_pt": 1.5,
    }
    if layout_name != "equal-grid":
        # Only the hero panel is exempt (it intentionally spans unequal grid
        # cells). Every other panel stays comparable so A11 still enforces the
        # 1.5pt shared-edge/gutter tolerance inside its row/column band —
        # never weaken the global tolerance to hide one intentional exception
        # (figure-layout-contract.md §5).
        hero_idx = 0
        for i, pn in enumerate(spec.get("panels", [])):
            if isinstance(pn, dict) and pn.get("hero"):
                hero_idx = i
                break
        else:
            if layout_name == "asymmetric-hero":
                hero_idx = len(panels) - 1  # hero axes is appended last
        if panels and hero_idx < len(panels):
            manifest["exemptions"] = [{
                "reason": f"layout preset '{layout_name}' hero panel intentionally "
                          f"spans unequal grid cells (figure-layout-contract.md §3)",
                "panels": [panels[hero_idx]["id"]],
            }]
    (outdir / "panel_layout.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")


@recipe("panel-grid")
def _panel(spec, outdir):
    """Compose sub-recipes into a page archetype.

    spec: {"panels":[{"recipe":...,...},...], "cols":2,
           "layout": "equal-grid|schematic-led|asymmetric-hero|clinical-triptych"}
    Each panel gets a/b/c; one shared theme; geometry locked by the layout
    preset (figure-layout-contract.md §3/§4), not by the model.
    """
    panels = spec["panels"]
    layout_name = spec.get("layout", DEFAULT_LAYOUT)
    if layout_name not in LAYOUTS:
        raise ValueError(f"unknown layout '{layout_name}'; available: {sorted(LAYOUTS)}")
    L = LAYOUTS[layout_name]
    cols = spec.get("cols", min(len(panels), 2))
    st.apply_matplotlib_style()

    # Estimate the figure-level legend footprint BEFORE any axes exist:
    # gridspec positions its own axes, so the bottom band must be passed to
    # add_gridspec — a later fig.subplots_adjust() does NOT move them
    # (this was the bug that jammed schematic-led's quant row into the hero).
    est_handles = sum(max(1, len(p.get("series", []))) for p in panels
                      if isinstance(p, dict))
    ncol_est = min(max(est_handles, 1), 4)
    legend_rows_est = (est_handles + ncol_est - 1) // ncol_est if est_handles else 0
    if spec.get("legend", True) is False:
        legend_rows_est = 0
    xlabel_band = 0.115
    bottom = 0.03 + xlabel_band + legend_rows_est * 0.065 if legend_rows_est else 0.03 + xlabel_band

    # ---- build axes slots from the locked layout preset ----
    if L["gs"] is None:
        rows = (len(panels) + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols,
                                 figsize=st.figsize_full(aspect=L.get("aspect", 0.72)))
        axes = np.atleast_1d(axes).ravel()
        fig.subplots_adjust(hspace=L["hspace"], wspace=L["wspace"],
                            top=0.92, bottom=bottom, left=0.10, right=0.98)
        slots = list(axes)                       # one slot per panel, in order
        hero_slot = None
    else:
        rows, gcols = L["gs"]
        fig = plt.figure(figsize=st.figsize_full(aspect=L.get("aspect", 0.72)))
        gs = fig.add_gridspec(rows, gcols, height_ratios=L.get("height_ratios"),
                              hspace=L["hspace"], wspace=L["wspace"],
                              top=0.92, bottom=bottom, left=0.09, right=0.98)
        hero_span = L.get("hero_span")
        covered = set()
        if hero_span is not None:
            hr, hc = hero_span
            r_rng = range(rows) if isinstance(hr, slice) else [hr]
            c_rng = range(gcols) if isinstance(hc, slice) else [hc]
            covered = {rr * gcols + cc for rr in r_rng for cc in c_rng}
        # free slots first (row-major), hero slot last — content order below
        slots = []
        for r in range(rows):
            for c in range(gcols):
                idx = r * gcols + c
                if idx in covered:
                    continue
                slots.append(fig.add_subplot(gs[r, c]))
        hero_slot = fig.add_subplot(gs[hero_span[0], hero_span[1]]) if hero_span else None

    # ---- assign panels to slots: hero-marked panel takes the hero slot ----
    hero_flag = next((i for i, pn in enumerate(panels) if pn.get("hero")), None)
    assignments = []          # (panel_idx, axes) in spec order
    free = list(slots)
    for i in range(len(panels)):
        if hero_slot is not None and i == hero_flag:
            assignments.append((i, hero_slot))
        elif free:
            assignments.append((i, free.pop(0)))
    for ax in free:           # unused grid cells
        ax.axis("off")

    letters = "abcdefghijklmnopqrstuvwxyz"  # panel hard-cap is 9 (contract §8)
    # Nature multi-panel convention: ONE figure-level legend, not per-panel
    # legends (per-panel legend_top collides with panel letters and the row
    # above's x-labels in a grid). Panels render legend-less; handles merge.
    seen, handles, labels = set(), [], []
    hero_flag = next((j for j, pn in enumerate(panels) if pn.get("hero")), None)
    for i, ax in assignments:
        p = dict(panels[i])
        p.setdefault("size", "panel2" if cols == 2 else "panel3")
        p["panel_label"] = None       # drawn at figure level below (Nature §3.6)
        p["legend"] = False
        is_support = L.get("hero_span") is not None and i != hero_flag
        if is_support:
            # Contract §3.1/§3.2: support panels are quieter than the hero.
            # Drop their axis labels (pattern P3) — the shared legend / hero
            # labels carry the semantics — and use the §6 point-scale type
            # (6-8pt) instead of the single-panel NATURE_FLOOR, which is 2-3x
            # too large for a half-column cell.
            p["x_label"] = ""
            p["y_label"] = ""
            p["quiet"] = True
        else:
            p["x_label_pad"] = 2       # keep hero xlabel clear of the next row
        _render_to_ax(p, ax)
        if is_support:
            # belt-and-braces: clear whatever the sub-recipe set
            ax.set_xlabel(""); ax.set_ylabel("")
            ax.tick_params(labelsize=st.NATURE_FLOOR["tick_label"] * 0.55)
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in seen:
                seen.add(lab); handles.append(h); labels.append(lab)

    # ---- panel labels: small bold lowercase, top-left OUTSIDE each axes ----
    # Nature §3.6: never large badges, never riding on data/labels.
    for i, ax in assignments:
        ax.text(0.025, 0.965, letters[i], transform=ax.transAxes,
                fontsize=st.NATURE_FLOOR.get("panel_label", 9),
                fontweight="bold", ha="left", va="top",
                zorder=10,
                bbox=dict(boxstyle="square,pad=0.15", facecolor="white",
                          edgecolor="none", alpha=0.85))

    # ---- figure-level legend in the band reserved above ----
    if handles and spec.get("legend", True):
        n_handles = len(handles)
        ncol = min(n_handles, 4)
        fig.legend(handles, labels, loc="lower center",
                   bbox_to_anchor=(0.5, 0.0),
                   ncol=ncol,
                   frameon=False, fontsize=st.NATURE_FLOOR["legend"],
                   markerscale=0.55, borderaxespad=0.1,
                   columnspacing=1.5, handlelength=1.6)
    fig.savefig(outdir / "output.pdf")
    _write_panel_manifest(fig, [ax for _, ax in assignments], spec, outdir)
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
    quiet = spec.get("quiet", False)
    fs_ax = st.NATURE_FLOOR["axis_label"] * (0.5 if quiet else 1.0)
    fs_tk = st.NATURE_FLOOR["tick_label"] * (0.55 if quiet else 1.0)
    ax.set_xlabel(spec.get("x_label", ""), fontsize=fs_ax)
    ax.set_ylabel(spec.get("y_label", ""), fontsize=fs_ax)
    ax.tick_params(labelsize=fs_tk)
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
