# Data Center Explorer design

**Status: draft for discussion.** Nothing here is built yet. Numbers marked [verify] are estimates.

## Purpose

The Data Center Explorer ranks individual US data centers by their likely impacts in four areas: environmental justice, climate footprint, water, and biodiversity and land. A reader picks a source and a project status, sees every facility ranked in a leaderboard, opens a scorecard for any one facility, and compares it with national aggregates. It is a no-LLM companion to the map and chat app, served at `/explorer/`, as the Wetland Basin Explorer is for wetlands-v2.

## Model

The Wetland Basin Explorer (`boettiger-lab/wetlands-v2/explorer`) is configuration on [glen-charts](https://github.com/SchmidtDSE/glen-charts) v0.16.1 with no JavaScript of its own. We reuse its structure as it stands:

- `config/app.json` declares the unit type (`jurisdictions`), its list and boundary tiles, user settings (`params`), the leaderboard and an overview card.
- Each pillar is a theme folder with `theme.json` and two SQL files. `<t>-all.sql` returns one row per (unit, variable) with `id, variable, label, value, unit, fmt, scale, dir, pct, pillar_score`; `<t>.sql` is generated from it by filtering to `{{ID}}`.
- `pct` is the mid-rank percentile among units with data, with direction applied, and `pillar_score` is the mean of a unit's `pct`. The leaderboard recomputes both in the browser among the units in view, with adjustable weights, and colours the map by overall score in deciles.
- Results are precomputed with the glen-charts CLI into `data/`, so the page reads static JSON.
- The scorecard for a unit shows a headline score and two charts for each pillar: percentile by variable, and the unit's position on the distribution across all units.

## Units

A unit is one data center from the chosen source. Its area of interest is the set of H3 resolution-8 cells within a radius of the facility, computed with `h3_grid_disk` around the facility's cell. Sources with footprints (PNNL campuses, Epoch footprints, PNNL projected sites) add the cells of the footprint itself. Some variables use the radius, which describes the neighbourhood; others use only the facility's own cells, which describe the land the facility occupies. Each variable's method text says which.

A radius setting offers 1, 3 and 5 miles, close to the 1- and 3-mile rings common in environmental justice screening. Resolution-8 cell centres are about 0.9 km apart, so these correspond to rings of about k = 2, 5 and 9 [verify].

## Sources and settings

Three settings sit above the scorecard. Each is a glen-charts `param`, kept in the link and part of every precomputed file name.

| Setting | Options | Notes |
|---|---|---|
| Source | FracTracker, Epoch AI, PNNL atlas, PNNL projected | One source at a time for now; see Overlap between sources |
| Status | Proposed, Approved or under construction, Operating or expanding, Suspended or cancelled | FracTracker only (`when` drill-down); multiple choice |
| Scenario | Growth (low, moderate, high, higher) and market gravity weight (0 to 100) | PNNL projected only; default moderate growth at weight 50 |
| Radius | 1, 3 or 5 miles | Slider |

The list of units depends on source and status (`list_params: true`), so the leaderboard ranks only the facilities in view: proposed FracTracker projects are ranked against each other, not against operating campuses, unless the reader chooses both.

## Map units

glen-charts draws units as polygons (`jur-fill` and `jur-line` layers in `core/map.js`). Facilities are points, so we need one library change: a `boundary.geometry: "point"` option that draws the units as circles, with the same hover, click, selection outline and leaderboard colouring. Following the wetlands README, this goes into glen-charts and not into this repo. Polygon footprints are too small to see at national zoom, so points serve every source.

The boundary tiles come from one harmonised points layer, `public-datacenters/explorer-units.parquet` and `.pmtiles`, built in `boettiger-lab/data-workflows`. It has one row per facility per source, with `id` (unique across sources), `source`, `name`, `status_class`, `operator`, `state`, `county`, `lat`, `lon` and `h8`. The boundary `filter` selects the chosen source and status through param tokens.

## Scoring

Scores follow the wetlands explorer: mid-rank percentiles from 0 to 100 among the facilities in view, and a pillar score that is the weighted mean of its variables' percentiles. The direction is reversed: a higher percentile means greater likely impact or concern. Labels say "impact percentile" so a reader does not assume higher is better.

Each variable is NULL where its source does not record it, and NULL values are left out of the ranking rather than counted as zero. The availability column in the tables below shows which sources carry facility attributes; variables built from context layers are available for every source.

## Environmental justice

| Variable | Data | Higher percentile when | Area |
|---|---|---|---|
| Social vulnerability | CDC SVI 2022 `RPL_THEMES`, population-weighted over tracts (tract hex, res 10) | more vulnerable | radius |
| Share of residents who are people of colour | SVI `E_MINRTY / E_TOTPOP` | higher | radius |
| Share of residents below the poverty line | ACS 2020–2024 `PovInd / TotPop` (block-group hex) | higher | radius |
| Median household income | ACS `MHHI`, population-weighted | lower | radius |
| Residents within the radius | GHS-POP 2020 | more people | radius |
| Historically redlined area | Mapping Inequality, grade D share | higher | radius; weight 0, since it covers only cities mapped in the 1930s |

## Climate footprint

| Variable | Data | Higher percentile when | Available for |
|---|---|---|---|
| Power capacity | FracTracker `mw` (697 of 1,733 records), Epoch `current_power_mw` | larger | FracTracker, Epoch |
| On-site fossil generation | FracTracker `power_source` naming gas, coal or oil, or `dedicated_power_plant` = Yes | present | FracTracker |
| Backup generators | FracTracker `number_of_generators`; count of Epoch footprint polygons of type Backup generator | more | FracTracker, Epoch |
| Carbon stored on the site | Conservation International vulnerable carbon 2024 in the facility's own cells | more | all |
| Cooling energy demand | PNNL `cooling_energy_demand_mwh` | more | PNNL projected |

Grid emissions are missing from the catalog. A facility drawing from a coal-heavy grid has a far larger footprint than one of the same size on a clean grid, so EPA eGRID subregion emission rates are the most important addition for this pillar (see Data gaps). Every PNNL projected site is modelled at 36 MW, so power capacity carries no information there and has weight 0 for that source.

## Water

| Variable | Data | Higher percentile when | Available for |
|---|---|---|---|
| Water-based cooling | FracTracker `cooling_source` Water or Hybrid; PNNL `cooling_water_consumption_mgy` | water used | FracTracker, PNNL projected |
| People served by the local water system | EPA community water system service areas containing the facility, `Population_Served_Count` | more | all |
| Other data centers in the same watershed | count and total power of facilities from the same source in the facility's HUC8 | more | all |
| Wetland share | NWI wetlands in the radius | higher | all |
| Flood zone share | FEMA high-risk (A and V) zones in the radius | higher | all |

The cumulative variable matters because data centers cluster, as in Loudoun County, Virginia: one facility's water draw is modest, but dozens in one watershed are not. Baseline water stress (WRI Aqueduct) is the largest gap in this pillar.

## Biodiversity and land

| Variable | Data | Higher percentile when | Area |
|---|---|---|---|
| Natural land on the site | NLCD 2024 forest, shrub, grassland and wetland classes (hex fractions) | more natural land | facility cells |
| Landscape intactness | Global Human Modification | less modified | radius |
| Threatened species richness | IUCN 2025 combined threatened richness (hex, res 5) | more species | radius |
| Imperiled species richness | NatureServe MOBI | more species | radius |
| Critical habitat share | USFWS final critical habitat | higher | radius |
| Protected area share | PAD-US 4.1 fee lands, GAP 1–3 | higher | radius |

## Hazard exposure

A fifth pillar is optional. It would hold hazards to the facility itself: sea level rise of 5 feet, wildland-urban interface, and projected summer warming from CHELSA SSP3-7.0 for 2041–2070, which raises cooling demand. These describe risk to the facility, not its impact on others, so we propose starting with them in the facility card, outside the score.

## Facility card

The overview card, the counterpart of the Ramsar card, describes the facility and does not enter any score: source, status, operator and tenant, power capacity and size class, expected date online, cooling and power sources, community pushback and resistance status, nondisclosure agreement, any moratorium or restriction covering its jurisdiction (by intersection with `fractracker-moratoriums`), and the other sources that list a facility within 1.5 km.

## National aggregates

The whole-region mode (`statewide` in glen-charts, labelled United States) gives national context in two forms:

- A national baseline for each variable, such as population-weighted SVI over all US tracts. This appears as a "United States" comparison on every scorecard tile.
- An aggregate over the facilities in view, such as the number of people living within 3 miles of proposed FracTracker projects, or their mean SVI against the national baseline. This is the national view's headline section, with a chart of facility counts and mean pillar scores by state.

The second form needs a theme whose query aggregates over the listed facilities. Whether the current `statewide` mode can show both forms without a library change is the first thing to test.

## Overlap between sources

The sources overlap but carry different information. Matching facilities within 1.5 km of each other:

| Source | Facilities | Within 1.5 km of a FracTracker facility |
|---|---|---|
| Epoch AI, US sites | 77 | 69 |
| PNNL atlas points and campuses | 382 | 238 |

Of FracTracker's 536 operating facilities, 251 are near a PNNL atlas site, so each source holds facilities the others lack. FracTracker has status and community response, Epoch has power and compute, and PNNL has mapped footprints. For now the reader chooses one source. A later version can build a crosswalk in data-workflows, matching by distance and operator name, and score one merged facility list that takes each attribute from its best source.

## Data gaps

These additions to the catalog would most improve the scores, roughly in order:

1. EPA eGRID subregion emission rates, for grid emissions in the climate footprint.
2. WRI Aqueduct baseline water stress, for the water pillar.
3. EIA-860 power plants, to identify new gas plants built to serve data centers.
4. An archived copy of EPA EJScreen (air toxics, diesel particulates, PM2.5), for pollution burden in the environmental justice pillar.

## Work plan

1. Build the harmonised `explorer-units` points layer in data-workflows.
2. Add point units to glen-charts, and test whether `statewide` can show both forms of national aggregate.
3. Write `explorer/config` and the theme SQL here, precompute, and serve `/explorer/` from the existing deployment as wetlands-v2 does.
4. Review the variables, directions and weights with the team. All scores stay marked provisional until then.

## Open questions

- Are 1, 3 and 5 miles the right radii?
- Should proposed and operating facilities be ranked together by default, or kept apart?
- Should population count toward concern (more people exposed) or be reported only as context?
- Should hazard exposure become a scored pillar?
- Is "impact percentile" the right label, given that the scores measure the setting and reported attributes and are not measured impacts?
