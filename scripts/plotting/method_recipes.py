#!/usr/bin/env python3
"""SciForge method-figure recipes — declarative pipeline/architecture diagrams (v1.6.1).

WHY: the d2/tikz spec path let the model improvise layout, so method figures
oscillated between "publication-grade" and "boxes-and-arrows soup". Research
(openJiuwen PaperBanana style-guide, cathrynlavery/diagram-design budgets,
opentikz edit_contract, thesis-figure-skill layout-by-construction) converged
on one answer: LOCK THE LAYOUT in a 5-level template ladder; the model fills
content only. A `.method.json` spec names a template and supplies stage/module/
edge TEXT; the generated d2 source is deterministic.

LADDER (simple -> complex; each level adds exactly one structural device):
    L1-linear          4-7 numbered stages, solid chain          (fill: names)
    L2-branch-loop     + decision branch + dashed retry edge     (fill: texts)
    L3-container-legend + nested phase containers + legend + callout
    L4-macro-micro     + mechanism inset zoomed from a focus stage
    L5-zones           + banded grid layout (full-page architecture)

LOCKED (never model-controlled): direction, border-radius, stroke widths,
palette (dopamine tokens; focus tint = 85% white mix per PaperBanana zone
strategy; focus colors <= 2), dashed=auxiliary convention, legend placement,
edge label style, node text budget (<= 4 words per node — enforced here, the
diagram-design complexity budget compiled to a hard error).

USAGE: python3 method_recipes.py spec.method.json --out <dir>
       (or via render_figure.py: `x.method.json` auto-detects engine=method)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sciforge_style as st  # noqa: E402

MAX_WORDS = 4          # diagram-design text-overload budget, per node label
MAX_STAGES = 7
MAX_MODULES = 5        # modules per container
TEMPLATES = ("L1-linear", "L2-branch-loop", "L3-container-legend",
             "L4-macro-micro", "L5-zones")


def _words(label: str, what: str) -> str:
    n = len([w for w in str(label).split() if w.isalnum() or w[0].isalpha()])
    if n > MAX_WORDS:
        raise ValueError(f"{what} '{label}' exceeds the {MAX_WORDS}-word node "
                         f"budget (text overload — split into modules or move to caption)")
    return str(label)


def _tid(name: str, used: dict) -> str:
    """Stable d2 identifier from a display label."""
    t = "".join(c if c.isalnum() else "_" for c in name).strip("_") or "n"
    t = t[:28]
    if t in used:
        used[t] += 1
        t = f"{t}_{used[t]}"
    else:
        used[t] = 0
    return t


def _tint(hexcolor: str) -> str:
    """Zone strategy: 15% token + 85% white fill, token as stroke."""
    return st.mix(hexcolor, "#FFFFFF", 0.85)


def _classes(focus_hex: str, focus2_hex: str | None = None) -> list[str]:
    lines = [
        "classes: {",
        "  stage: { style: { fill: \"%s\"; stroke: \"%s\"; stroke-width: 2; border-radius: 8; font-color: \"%s\"; font-size: %d } }"
        % (st.TOKENS["surface"], st.TOKENS["ink-soft"], st.INK_TEXT, st.D2_FONT_PX["node"]),
        "  focus: { style: { fill: \"%s\"; stroke: \"%s\"; stroke-width: 3; border-radius: 8; font-color: \"%s\"; font-size: %d } }"
        % (_tint(focus_hex), focus_hex, st.INK_TEXT, st.D2_FONT_PX["node"]),
    ]
    if focus2_hex:
        lines.append(
            "  focus2: { style: { fill: \"%s\"; stroke: \"%s\"; stroke-width: 3; border-radius: 8; font-color: \"%s\"; font-size: %d } }"
            % (_tint(focus2_hex), focus2_hex, st.INK_TEXT, st.D2_FONT_PX["node"]))
    lines += [
        "  module: { style: { fill: \"%s\"; stroke: \"%s\"; stroke-width: 1; border-radius: 6; font-color: \"%s\"; font-size: %d } }"
        % (st.GROUND, st.TOKENS["ink-soft"], st.INK_TEXT, st.D2_FONT_PX["node"]),
        "  aux: { style: { stroke-dash: 3; opacity: 0.75 } }",
        "}",
    ]
    return lines


def _legend(focus_hex: str) -> list[str]:
    lid = "key"
    return [
        f"{lid}: \"Legend\" {{",
        "  near: bottom-right; label: \"Legend\"",
        f"  l1: \"stage\" {{ class: stage }}",
        f"  l2: \"focus\" {{ style: {{ fill: \"{_tint(focus_hex)}\"; stroke: \"{focus_hex}\"; stroke-width: 3; border-radius: 8; font-size: {st.D2_FONT_PX['node']} }} }}",
        f"  l3: \"aux flow\" {{ style: {{ stroke-dash: 3; opacity: 0.75; fill: \"{st.GROUND}\"; stroke: \"{st.TOKENS['ink-soft']}\"; font-size: {st.D2_FONT_PX['node']} }} }}",
        "}",
    ]


def build_d2(spec: dict) -> str:
    tpl = spec.get("template")
    if tpl not in TEMPLATES:
        raise ValueError(f"template must be one of {TEMPLATES}, got '{tpl}'")
    stages = spec.get("stages") or []
    if not (2 <= len(stages) <= MAX_STAGES):
        raise ValueError(f"stages must be 2..{MAX_STAGES} items, got {len(stages)}")
    used: dict[str, int] = {}
    ids = {}
    for s in stages:
        name = _words(s["name"], "stage") if isinstance(s, dict) else _words(s, "stage")
        ids[name] = _tid(name, used)
    # focus <= 2 (diagram-design budget): first stage + optional spec.focus
    cyc = st.cycle_hex()
    f1 = cyc[0]
    f2 = cyc[2] if tpl in ("L3-container-legend", "L4-macro-micro", "L5-zones") else None
    # no `//` comment in the figure source: d2 renders it as a 16px text node
    # that fails the A4 font floor. Provenance lives in render.log instead.
    lines = ["direction: right"]
    lines += _classes(f1, f2)

    stage_cls: dict[str, str] = {}  # id -> class, so L5 zones can re-apply it

    def stage_node(s, idx):
        if isinstance(s, str):
            s = {"name": s}
        name = _words(s["name"], "stage")
        nid = ids[name]
        cls = "focus" if s.get("focus") else ("focus2" if s.get("focus2") else "stage")
        stage_cls[nid] = cls
        mods = s.get("modules") or []
        if len(mods) > MAX_MODULES:
            raise ValueError(f"stage '{name}' has {len(mods)} modules > {MAX_MODULES}")
        out = [f"{nid}: \"{name}\" {{", f"  class: {cls}"]
        mids = []
        for m in mods:
            mlabel = _words(m, "module")
            mid = _tid(f"{nid}_{mlabel}", used)
            mids.append(mid)
            out.append(f"  {mid}: \"{mlabel}\" {{ class: module }}")
        for a, b in zip(mids, mids[1:]):
            out.append(f"  {a} -> {b}")
        out.append("}")
        return out

    if not any((isinstance(s, dict) and (s.get("focus") or s.get("focus2"))) for s in stages):
        stages[0] = ({"name": stages[0], "focus": True} if isinstance(stages[0], str)
                     else {**stages[0], "focus": True})
    for i, s in enumerate(stages):
        lines += stage_node(s, i)
    sids = [ids[_words(s["name"] if isinstance(s, dict) else s, "stage")] for s in stages]
    for a, b in zip(sids, sids[1:]):
        lines.append(f"{a} -> {b}")

    if tpl == "L1-linear":
        pass
    elif tpl == "L2-branch-loop":
        dec = spec.get("decision") or {"question": "valid?", "yes": sids[-1], "no_label": "retry"}
        dq = _words(dec["question"], "decision")
        did = _tid(dq, used)
        lines.append(f"{did}: \"{dq}?\" {{ style: {{ fill: \"{st.GROUND}\"; stroke: \"{st.TOKENS['ink-soft']}\"; stroke-width: 2; border-radius: 20; font-size: {st.D2_FONT_PX['node']} }} }}")
        lines.append(f"{sids[0]} -> {did}")
        lines.append(f"{did} -> {sids[-1]}: \"yes\" {{ style.font-size: {st.D2_FONT_PX['edge']} }}")
        lines.append(f"{did} -> {sids[0]}: \"{_words(dec['no_label'], 'edge')}\" {{ style.stroke-dash: 3; style.font-size: {st.D2_FONT_PX['edge']} }}")
    elif tpl in ("L3-container-legend", "L4-macro-micro", "L5-zones"):
        lines += _legend(f1)
        call = spec.get("callout")
        if call:
            # Nature callout convention: a dashed LEADER from the anchor node to
            # the callout box (object-`near` needs the tala layout; the leader
            # works on dagre/elk and reads better than a floating annotation).
            anchor = ids.get(_words(call["anchor"], "callout anchor"), sids[0])
            cid = _tid("callout", used)
            lines.append(f"{cid}: \"{_words(call['text'], 'callout')}\" {{")
            lines.append(f"  class: aux; style.fill: \"{st.GROUND}\"; style.border-radius: 6; style.font-size: {st.D2_FONT_PX['edge']}")
            lines.append("}")
            lines.append(f"{anchor} -> {cid} {{ class: aux }}")
    if tpl == "L4-macro-micro":
        inset = spec.get("inset") or {"name": "Mechanism detail",
                                      "modules": ["component A", "component B"]}
        iname = _words(inset["name"], "inset")
        iid = _tid(iname, used)
        lines.append(f"{iid}: \"{iname}\" {{")
        lines.append(f"  class: {'focus2' if f2 else 'focus'}")
        mids = []
        for m in inset.get("modules", [])[:MAX_MODULES]:
            mid = _tid(f"inset_{_words(m, 'inset module')}", used)
            mids.append(mid)
            lines.append(f"  {mid}: \"{m}\" {{ class: module }}")
        for a, b in zip(mids, mids[1:]):
            lines.append(f"  {a} -> {b}")
        lines.append("}")
        focus_sid = next((ids[_words(s["name"], "stage")] for s in stages
                          if isinstance(s, dict) and (s.get("focus") or s.get("focus2"))), sids[0])
        lines.append(f"{focus_sid} -> {iid}: \"detail\" {{ class: aux; style.font-size: {st.D2_FONT_PX['edge']} }}")
    if tpl == "L5-zones":
        zones = spec.get("zones") or []
        if not zones:
            raise ValueError("L5-zones requires zones: [{name, stages:[...]}]")
        # regroup: wrap listed stage ids into zone containers via near-grid rows
        lines.append(f"canvas: \"\" {{ grid-columns: {max(1, len(zones))}; style.fill: \"{st.GROUND}\"")
        for z in zones:
            zid = _tid(_words(z["name"], "zone"), used)
            members = [ids[_words(s, "zone member")] for s in z.get("stages", [])]
            lines.append(f"  {zid}: \"{z['name']}\" {{ class: stage")
            for m in members:
                # re-declare with the original class: a bare id reference inside
                # a container loses its class (and thus the locked font-size)
                lines.append(f"    {m}: {{ class: {stage_cls.get(m, 'stage')} }}")
            lines.append("  }")
        lines.append("}")
    return "\n".join(lines) + "\n"


def render(spec: dict, outdir: Path) -> Path:
    d2src = build_d2(spec)
    outdir.mkdir(parents=True, exist_ok=True)
    spec_path = outdir / "spec.method.d2"
    spec_path.write_text(d2src, encoding="utf-8")
    return spec_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text())
    p = render(spec, a.out or a.spec.parent)
    print(f"OK method {spec.get('template')} -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
