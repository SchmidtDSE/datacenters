# Data Center Explorer design

**Status: first version built, scores provisional.** The explorer in this folder follows this design, with the changes and decisions noted below. The variables, directions and weights have not been reviewed.

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

A unit is one data center from the chosen source. Neighbourhood variables use the H3 resolution-8 cells whose centre lies within the chosen radius of the facility point (a disk from `h3_grid_disk`, trimmed by great-circle distance). At 5 miles the cells cover 203 km² on average, against 203.6 km² for the exact circle. Site variables use the single resolution-8 cell (about 0.7 km²) that holds the facility point; footprints are not used yet. Each variable's method text says which.

A radius setting offers 1, 3 and 5 miles, close to the 1- and 3-mile rings common in environmental justice screening. The default is 3 miles.

## Sources and settings

Four settings sit above the scorecard. Each is a glen-charts `param`, kept in the link and part of every precomputed file name.

| Setting | Options | Notes |
|---|---|---|
| Source | FracTracker, Epoch AI, PNNL atlas, PNNL projected | One source at a time for now; see Overlap between sources |
| Status | Proposed, Approved or under construction, Operating or expanding, Suspended or cancelled | FracTracker only (`when` drill-down); multiple choice |
| Growth scenario | Low, moderate, high, higher | PNNL projected only; default moderate, at market gravity weight 50 |
| Radius | 1, 3 or 5 miles | Slider |

The list of units depends on source and status (`list_params: true`), so the leaderboard ranks only the facilities in view: proposed FracTracker projects are ranked against each other, not against operating campuses, unless the reader chooses both.

## Map units

No new dataset is needed. Each source's own PMTiles serve as the unit boundaries, keyed by its `_cng_fid`, which the queries also use as the facility id. Two small glen-charts changes (branch `point-units`) make this work:

- Point features in boundary tiles are drawn as circles, with the same hover, click, selection ring and leaderboard colouring as polygons. PNNL campuses and projected sites stay polygons.
- A param option may carry its own `tokens`, so the Source setting switches the tile URL, layer and name field together.

The boundary filter keeps Epoch's US sites and the chosen PNNL growth scenario. FracTracker points are not filtered by status on the map; points outside the leaderboard's view stay grey.

The PNNL atlas source uses its 254 mapped campuses. Its 128 point records are in a separate tile set and are left out of this version.

## Scoring

Scores follow the wetlands explorer: mid-rank percentiles from 0 to 100 among the facilities in view, and a pillar score that is the weighted mean of its variables' percentiles. The direction is reversed: a higher percentile means greater likely impact or concern. Labels say that a higher percentile means a greater potential impact, so a reader does not assume higher is better.

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
| Power capacity | FracTracker `mw` (589 of 1,733 records give a number), Epoch `current_power_mw`, PNNL projected IT power | larger | FracTracker, Epoch, PNNL projected |
| Floor area | FracTracker `facility_size_sqft`, PNNL campus `sqft`, PNNL projected campus size | larger | FracTracker, PNNL |
| Dedicated fossil power reported | FracTracker `power_source` or `dedicated_power_plant` naming gas, coal, oil, diesel, turbines or fracked gas | reported | FracTracker; weight 0, as few records report it |
| Vulnerable carbon in the site cell | Conservation International vulnerable carbon 2024 | more | all |
| Cooling energy demand | PNNL `cooling_energy_demand_mwh` | more | PNNL projected |

Grid emissions are missing from the catalog. A facility drawing from a coal-heavy grid has a far larger footprint than one of the same size on a clean grid, so EPA eGRID subregion emission rates are the most important addition for this pillar (see Data gaps). Every PNNL projected site is modelled at 36 MW, so power capacity does not separate them. Backup generators are reported for only 11 FracTracker records, so they are left out.

## Water

| Variable | Data | Higher percentile when | Available for |
|---|---|---|---|
| People served by the local water system | The largest EPA community water system whose service area covers the site cell, `Population_Served_Count` | more | all |
| Other facilities in the same HUC8 subbasin | count of facilities from the same source and status in the site cell's subbasin | more | all |
| Wetland share of the radius | vegetated NWI wetland (lakes, rivers and ponds left out) | higher | all |
| Flood zone share of the radius | FEMA special flood hazard areas (A and V zones) | higher | all |
| Cooling water consumption | PNNL `cooling_water_consumption_mgy` | more | PNNL projected |

The cumulative variable matters because data centers cluster, as in Loudoun County, Virginia: one facility's water draw is modest, but dozens in one watershed are not. Only 77 FracTracker records report a cooling source, so cooling is shown in the facility card and not scored. Baseline water stress (WRI Aqueduct) is the largest gap in this pillar.

## Biodiversity and land

| Variable | Data | Higher percentile when | Area |
|---|---|---|---|
| Natural land in the site cell | NLCD 2024 forest, shrub, grassland and wetland classes (hex fractions) | more natural land | site cell |
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

The whole-region mode (`statewide` in glen-charts, labelled United States) gives national context. glen-charts runs a theme's per-unit query over the whole region, which these queries cannot do, so `scripts/build-national.py` writes the region's rows instead and the queries are marked `"statewide": false`.

- The national value of each variable comes from a fixed sample of about 2,000 resolution-8 cells in the contiguous US, scored with the same SQL as the facilities. Composition variables (SVI, people of colour, poverty, income) are weighted by the residents around each sample cell, so they describe the typical US resident; the rest describe a typical place.
- Its percentile is where that typical value would rank among the facilities in view, so the national scorecard reads as how a typical US location compares with these facilities.
- The national facility card reports the number of facilities in view, their total reported power capacity and, for FracTracker, how many report community pushback.

A chart of counts and mean scores by state is not built yet.

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

## Decisions in the first version

- The radii are 1, 3 and 5 miles, with 3 miles as the default.
- FracTracker facilities of every status are ranked together by default. The reader can narrow the status, and the scores are then recomputed among those facilities.
- Residents within the radius counts toward concern, since more people are exposed.
- Hazard exposure is not scored.
- Labels say "potential impact" and the intro says the scores describe each facility's setting and reported attributes, not measured impacts.
- Sparse FracTracker attributes (cooling source, generators, dedicated power, community response) are shown in the facility card and not scored, except a dedicated fossil power flag kept at weight 0.

## Next steps

1. Review the variables, directions and weights with the team. All scores stay marked provisional until then.
2. Add EPA eGRID emission rates and WRI Aqueduct water stress to the catalog, and add them to the climate and water pillars.
3. Merge the sources into one facility list through a crosswalk built in data-workflows.
