#!/usr/bin/env python3
"""Numbers, tables and figures for the scoring review (review/report.md).

Reads the explorer's precomputed rows (explorer/data/results) and its config, so it needs no
network. Writes build/values.json, build/*.md tables and build/*.png figures.

  python3 explorer/review/analysis.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EXPLORER = HERE.parent
BUILD = HERE / "build"
BUILD.mkdir(exist_ok=True)
APP = json.loads((EXPLORER / "config" / "app.json").read_text())
PILLARS = [p["theme"] for p in APP["leaderboard"]["pillars"]]
SOURCES = {"fractracker": "source-fractracker_status-all", "epoch": "source-epoch",
           "pnnl-atlas": "source-pnnl_atlas", "pnnl-projected": "growth-moderate_source-pnnl_projected"}
RADIUS = 3


def weights():
    """Default leaderboard weights: {pillar: w} and {pillar.variable: w}."""
    pw, vw = {}, {}
    for p in APP["leaderboard"]["pillars"]:
        pw[p["theme"]] = p.get("weight", 1)
        for v, o in (p.get("variables") or {}).items():
            vw[f"{p['theme']}.{v}"] = o.get("weight", 1)
    return pw, vw


def load(source):
    """Long rows for one source at the default radius: pillar, id, variable, label, value, pct, dir."""
    rows = []
    for theme in PILLARS:
        d = EXPLORER / "data" / "results" / theme / theme
        # the file whose param key holds this source's settings, at the default radius when the
        # query uses one (climate does not)
        want = set(SOURCES[source].split("_"))
        f = next(p for p in sorted(d.glob("facility-*.json"))
                 if want <= set(p.stem[len("facility-"):].split("_"))
                 and ({f"radius-{RADIUS}"} | want == set(p.stem[len("facility-"):].split("_"))
                      or want == set(p.stem[len("facility-"):].split("_"))))
        for fid, rs in json.loads(f.read_text()).items():
            for r in rs:
                rows.append({"pillar": theme, "id": fid, "variable": r["variable"], "label": r["label"],
                             "value": r["value"], "pct": r["pct"], "dir": r["dir"],
                             "pillar_score": r["pillar_score"]})
    return pd.DataFrame(rows)


def variable_table(df, vw):
    out = []
    for (pillar, var), g in df.groupby(["pillar", "variable"], sort=False):
        vals = g["value"].dropna()
        top = vals.value_counts().iloc[0] / len(vals) if len(vals) else np.nan
        out.append({"pillar": pillar, "variable": var, "label": g["label"].iloc[0],
                    "weight": vw.get(f"{pillar}.{var}", 1), "n": len(g), "coverage": len(vals) / len(g),
                    "distinct": vals.nunique(), "tied": top})
    return pd.DataFrame(out)


def overall(df, pw):
    """Overall score per facility: weighted mean of pillar scores, as the leaderboard computes it by default."""
    ps = df.groupby(["id", "pillar"])["pillar_score"].first().unstack()
    w = pd.Series(pw)
    def score(weights):
        ww = weights[ps.columns]
        return (ps * ww).sum(axis=1) / ps.notna().mul(ww).sum(axis=1)
    return ps, score(w), score(w.where(w > 0, 1))


def pct(x):
    return "no values" if pd.isna(x) else f"{100 * x:.0f}%"


def md_table(frame, cols, header):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for _, r in frame.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main():
    pw, vw = weights()
    values = {"radius": RADIUS}
    df = load("fractracker")
    values["n_facilities"] = df["id"].nunique()
    values["n_variables"] = df.groupby(["pillar", "variable"]).ngroups
    pillar_label = {t: json.loads((EXPLORER / "config" / "themes" / t / "theme.json").read_text())["label"] for t in PILLARS}

    # variables: coverage, ties
    vt = variable_table(df, vw)
    vt["Pillar"] = vt["pillar"].map(pillar_label)
    vt["Coverage"] = vt["coverage"].map(pct)
    vt["Largest tie"] = vt["tied"].map(pct)
    vt["Weight"] = vt["weight"]
    vt["Distinct values"] = vt["distinct"]
    (BUILD / "variables.md").write_text(md_table(vt, ["Pillar", "label", "Weight", "Coverage", "Distinct values", "Largest tie"],
                                                  ["Pillar", "Variable", "Weight", "Coverage", "Distinct values", "Largest tie"]))
    weak = vt[(vt["tied"] >= 0.5) | (vt["coverage"] < 0.5)]
    values["n_weak"] = len(weak)
    (BUILD / "weak.md").write_text(md_table(weak.assign(Pillar=weak["Pillar"]), ["Pillar", "label", "Coverage", "Largest tie"],
                                            ["Pillar", "Variable", "Coverage", "Largest tie"]))

    # correlations between variables (Spearman, on values with direction applied)
    wide = df.assign(key=df["pillar"] + "." + df["variable"], v=df["value"] * df["dir"]) \
             .pivot_table(index="id", columns="key", values="v", aggfunc="first")
    rho = wide.corr(method="spearman", min_periods=30)
    labels = df.assign(key=df["pillar"] + "." + df["variable"]).groupby("key")["label"].first()
    pairs = []
    keys = list(rho.columns)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            r = rho.loc[a, b]
            if pd.notna(r) and abs(r) >= 0.6:
                pairs.append({"A": f"{pillar_label[a.split('.')[0]]}: {labels[a]}", "B": f"{pillar_label[b.split('.')[0]]}: {labels[b]}",
                              "rho": f"{r:.2f}", "same": a.split(".")[0] == b.split(".")[0]})
    pairs = pd.DataFrame(pairs, columns=["A", "B", "rho", "same"])
    pairs = pairs.reindex(pairs["rho"].astype(float).abs().sort_values(ascending=False).index)
    values["n_pairs"] = len(pairs)
    values["n_pairs_cross"] = int((~pairs["same"]).sum()) if len(pairs) else 0
    (BUILD / "pairs.md").write_text(md_table(pairs, ["A", "B", "rho"], ["Variable", "Variable", "Spearman ρ"]) if len(pairs)
                                    else "No pair of variables has |ρ| of 0.6 or more.\n")

    fig, ax = plt.subplots(figsize=(9, 8))
    order = [k for t in PILLARS for k in keys if k.startswith(t + ".")]
    m = rho.loc[order, order]
    im = ax.imshow(m, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(order)), [labels[k] for k in order], rotation=90, fontsize=6)
    ax.set_yticks(range(len(order)), [labels[k] for k in order], fontsize=6)
    for t in PILLARS[1:]:
        i = next(j for j, k in enumerate(order) if k.startswith(t + "."))
        ax.axhline(i - 0.5, color="k", lw=0.6); ax.axvline(i - 0.5, color="k", lw=0.6)
    fig.colorbar(im, ax=ax, shrink=0.7, label="Spearman ρ")
    fig.tight_layout(); fig.savefig(BUILD / "correlations.png", dpi=300); plt.close(fig)

    # pillar scores and the overall score
    ps, score0, score1 = overall(df, pw)
    pr = ps.corr(method="spearman")
    prt = pr.rename(index=pillar_label, columns=pillar_label).round(2).reset_index().rename(columns={"pillar": "Pillar"})
    (BUILD / "pillars.md").write_text(md_table(prt, list(prt.columns), list(prt.columns)))
    values["rho_overall_regulatory"] = f"{score0.corr(score1, method='spearman'):.2f}"
    top = lambda s: set(s.sort_values(ascending=False).index[:100])
    values["top100_overlap"] = len(top(score0) & top(score1))
    values["top100_overlap_complement"] = 100 - values["top100_overlap"]
    r = lambda a, b: f"{rho.loc[a, b]:.2f}".replace("-", "−")
    values["rho_crit"] = r("biodiversity.critical_habitat", "regulatory.critical_habitat_mi")
    values["rho_intact"] = r("biodiversity.intactness", "justice.residents")
    values["rho_size"] = r("climate.floor_area", "climate.power_mw")
    values["power_coverage"] = pct(vt.set_index(["pillar", "variable"]).loc[("climate", "power_mw"), "coverage"])
    values["pillar_weight_zero"] = ", ".join(pillar_label[p] for p, w in pw.items() if w == 0) or "none"
    values["variable_weight_zero"] = ", ".join(f"{labels[k]} ({pillar_label[k.split('.')[0]]})" for k, w in vw.items() if w == 0) or "none"

    # the same checks on the other sources: coverage and ties, in one line per source
    rows = []
    for s in SOURCES:
        d = load(s)
        t = variable_table(d, vw)
        rows.append({"Source": s, "Facilities": d["id"].nunique(),
                     "Variables mostly tied": int((t["tied"] >= 0.5).sum()),
                     "Variables under half covered": int((t["coverage"] < 0.5).sum())})
    (BUILD / "sources.md").write_text(md_table(pd.DataFrame(rows), ["Source", "Facilities", "Variables mostly tied", "Variables under half covered"],
                                               ["Source", "Facilities", "Variables mostly tied", "Variables under half covered"]))

    (BUILD / "values.json").write_text(json.dumps(values, indent=2))
    print(json.dumps(values, indent=2))


if __name__ == "__main__":
    main()
