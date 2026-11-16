# Data Center Explorer

The Data Center Explorer ranks US data centers by their potential impacts in four pillars: environmental justice, climate footprint, water, and biodiversity and land. It is served at `/explorer/` beside the map and chat app, and it has no JavaScript of its own: it is configuration on [glen-charts](https://github.com/SchmidtDSE/glen-charts). The design and the decisions behind it are in [DESIGN.md](DESIGN.md).

All scores are provisional. They describe each facility's setting and what its source reports about it, not measured impacts, and the variables and weights have not been reviewed.

## Layout

| Path | Contents |
|---|---|
| `config/app.json` | settings, the facility unit type, the national view and the leaderboard |
| `config/themes/<t>/theme.json` | each pillar's charts and method text |
| `config/themes/<t>/*.sql` | generated queries: edit `sql/`, not these |
| `sql/units.sql` | the facilities of the chosen source and their H3 cells, shared by every query |
| `sql/themes/<t>.sql`, `sql/score.sql` | each pillar's variables, and the shared percentile ranking |
| `sql/overview/facility.sql` | the facility card |
| `sql/list.sql` | the facility list |
| `config/data.html` | the Data tab, above the citations in `data/sources.json` |
| `data/` | precomputed results that the page reads |

## Building the data

The queries run on the app's MCP server, which reads the catalog on NRP.

```bash
# 1. write the theme queries and the list into config/
python3 scripts/build-explorer-sql.py

# 2. precompute the lists and every facility's rows for every setting
npx github:SchmidtDSE/glen-charts#<version> precompute --site explorer lists \
  --param source=all --param status=all --param growth=all --param radius=all
npx github:SchmidtDSE/glen-charts#<version> precompute --site explorer results \
  --param source=all --param status=all --param growth=all --param radius=all
npx github:SchmidtDSE/glen-charts#<version> precompute --site explorer sources

# 3. the national view, from a fixed sample of US locations scored with the same SQL
python3 scripts/build-national.py
```

`build-national.py` caches the sample's results in `data/national/`; pass `--refresh` after changing a theme's SQL.
