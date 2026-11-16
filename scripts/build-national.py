#!/usr/bin/env python3
"""Write the explorer's national baseline (data/statewide/<params>.json).

glen-charts shows a whole-region view ("United States") beside every facility. Its rows here
are built from a fixed sample of about 2,000 res-8 cells in the contiguous US (the us-sample
branch of explorer/sql/units.sql), scored with the same theme SQL as the facilities:

  value  the typical US value of each variable. Composition variables (social vulnerability,
         people of colour, poverty, income) are weighted by the residents around each sample
         cell, so they describe the typical US resident; the rest are a plain mean over cells,
         so they describe a typical place. Facility attributes have no national value.
  pct    where that value would rank among the facilities in view (mid-rank, 0-100).

The facility card's national row reports the number of facilities in view and their total
reported power capacity. Run after `glen-charts precompute results`, since the percentiles
read the facilities' precomputed rows. Sample results are cached in data/national/; pass
--refresh to query them again.

  python3 scripts/build-national.py [--refresh]
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "explorer"
APP = json.loads((ROOT / "config" / "app.json").read_text())
MCP = APP["mcp_url"]
PILLARS = ["justice", "climate", "water", "biodiversity"]
RESIDENT_WEIGHTED = {"svi", "people_of_colour", "poverty", "income"}
NO_BASELINE = {"watershed_peers"}  # counts other sample cells, which means nothing


def query(sql):
    wrapped = f"SELECT CAST(to_json(list(__q)) AS VARCHAR) AS __json FROM (\n{sql.strip().rstrip(';')}\n) __q"
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "query", "arguments": {"sql_query": wrapped}}}).encode()
    req = urllib.request.Request(MCP, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    text = urllib.request.urlopen(req, timeout=900).read().decode()
    for line in text.splitlines():
        if line.startswith("data:"):
            text = line[5:]
    msg = json.loads(text)
    if "error" in msg:
        raise RuntimeError(msg["error"])
    out = "".join(c.get("text", "") for c in msg["result"]["content"])
    a, b = out.find("["), out.rfind("]")
    if a < 0 or b < a:
        raise RuntimeError(out[:500])
    return json.loads(out[a:b + 1])


def sample_rows(theme, radius, refresh):
    """The theme's rows for every sample cell at one radius, cached in data/national/."""
    cache = ROOT / "data" / "national" / f"{theme}-radius-{radius}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    sql = (ROOT / "config" / "themes" / theme / f"{theme}-all.sql").read_text()
    for k, v in {"SOURCE": "us-sample", "STATUS": "'all'", "GROWTH": "moderate", "RADIUS": str(radius)}.items():
        sql = sql.replace("{{" + k + "}}", v)
    rows = query(sql)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows))
    print(f"sample {theme} radius {radius}: {len({r['id'] for r in rows})} cells")
    return rows


def baselines(radius, refresh):
    """{theme: {variable: row with the national value}} at one radius."""
    residents = {r["id"]: r["value"] or 0 for r in sample_rows("justice", radius, refresh) if r["variable"] == "residents"}
    out = {}
    for theme in PILLARS:
        by_var = {}
        for r in sample_rows(theme, radius, refresh):
            by_var.setdefault(r["variable"], []).append(r)
        out[theme] = {}
        for var, rows in by_var.items():
            vals = [(r["value"], residents.get(r["id"], 0) if var in RESIDENT_WEIGHTED else 1)
                    for r in rows if r["value"] is not None]
            w = sum(x for _, x in vals)
            value = None if var in NO_BASELINE or not vals or w == 0 else sum(v * x for v, x in vals) / w
            meta = {k: rows[0][k] for k in ("variable", "label", "unit", "fmt", "scale", "dir")}
            out[theme][var] = {**meta, "value": value}
    return out


def pct_among(value, d, facility_values):
    """Mid-rank percentile of value among the facilities' values, direction applied."""
    xs = [d * v for v in facility_values if v is not None]
    if value is None or len(xs) < 2:
        return None
    x = d * value
    below = sum(1 for v in xs if v < x)
    equal = sum(1 for v in xs if v == x)
    return round(100 * (below + equal / 2) / len(xs), 1)


def main():
    refresh = "--refresh" in sys.argv
    results = ROOT / "data" / "results"
    national = {}
    files = {}
    for theme in PILLARS:
        for f in sorted((results / theme / theme).glob("facility-*.json")):
            pk = f.stem[len("facility-"):]
            radius = int(re.search(r"radius-(\d+)", pk).group(1)) if "radius-" in pk else 3
            if radius not in national:
                national[radius] = baselines(radius, refresh)
            facilities = json.loads(f.read_text())
            by_var = {}
            for rows in facilities.values():
                for r in rows:
                    by_var.setdefault(r["variable"], []).append(r["value"])
            rows = []
            for var, base in national[radius][theme].items():
                rows.append({**base, "pct": pct_among(base["value"], base["dir"], by_var.get(var, []))})
            scored = [r["pct"] for r in rows if r["pct"] is not None]
            score = round(sum(scored) / len(scored), 1) if scored else None
            for r in rows:
                r["pillar_score"] = score
            files.setdefault(pk, {})[theme] = {theme: sorted(rows, key=lambda r: r["variable"])}

    # the facility card: the facilities in view, counted and summed
    for f in sorted((results / "facility" / "facility").glob("facility-*.json")):
        pk = f.stem[len("facility-"):]
        facilities = [rows[0] for rows in json.loads(f.read_text()).values() if rows]
        mw = [r["mw"] for r in facilities if r.get("mw")]
        row = {"name": "United States", "source": facilities[0]["source"] if facilities else None,
               "status": f"{len(facilities):,} facilities in view",
               "operator": None, "tenant": None,
               "mw": sum(mw) if mw else None, "online": None, "power_source": None, "dedicated_power": None,
               "cooling": None, "pushback": f"{sum(1 for r in facilities if (r.get('pushback') or '').lower() == 'yes'):,} facilities with community pushback reported"
               if facilities and facilities[0]["source"] == "FracTracker" else None,
               "resistance": None, "nda": None, "state": None, "county": None,
               "actions": None, "nearby": None}
        files.setdefault(pk, {})["facility"] = {"facility": [row]}

    out_dir = ROOT / "data" / "statewide"
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    for pk, res in sorted(files.items()):
        (out_dir / f"{pk}.json").write_text(json.dumps({"generated": now, "results": res}, indent=1))
        print(f"statewide {pk}: {', '.join(sorted(res))}")


if __name__ == "__main__":
    main()
