"""Write layers-input.json for the US data centers app.

Run from the repo root: python3 scripts/build-layers.py
Edit the layer list here rather than hand-editing the JSON.
"""
import json

GLEN = "https://cdn.jsdelivr.net/gh/SchmidtDSE/glen@v4.0.6"
S3 = "https://s3-west.nrp-nautilus.io"
DC = f"{S3}/public-datacenters"


def outline(color, width=0.4, opacity=0.6):
    return {"line-color": color, "line-width": width, "line-opacity": opacity}


STATUS = [
    ("Proposed", "#E6550D"),
    ("Pre-proposal", "#FDAE6B"),
    ("Approved/Permitted/Under construction", "#FFD92F"),
    ("Operating", "#3182BD"),
    ("Expanding", "#6BAED6"),
    ("Suspended", "#969696"),
    ("Cancelled", "#525252"),
]
ACTION = [
    ("Moratorium", "#E6550D"),
    ("Ban", "#A50F15"),
    ("Zoning restriction", "#3182BD"),
    ("Curative Amendment", "#756BB1"),
    ("Other", "#969696"),
]
FEATURE = [
    ("Building", "#5f5f5f"),
    ("Cooling", "#1f78b4"),
    ("Backup generator", "#6a3d9a"),
    ("Power substation", "#ff7f00"),
    ("Power generator", "#d01c8b"),
]
OWNER = [
    ("Google", "#EA8D00"), ("Meta", "#0058DC"), ("Microsoft", "#009AF1"),
    ("Amazon", "#FC6538"), ("CoreWeave", "#279E27"), ("Oracle", "#E03D90"),
    ("SpaceXAI", "#6A3ECB"),
]


def match(field, pairs, other="#bdbdbd"):
    expr = ["match", ["get", field]]
    for k, c in pairs:
        expr += [k, c]
    return expr + [other]


def legend(pairs):
    return [{"label": k, "color": c} for k, c in pairs]


def projected(alias, growth, name, color, visible=False):
    return {
        "id": "projected-pmtiles",
        "alias": alias,
        "display_name": name,
        "visible": visible,
        "default_style": {"fill-color": color, "fill-opacity": 0.8},
        "outline_style": outline(color, 1.2, 0.9),
        "default_filter": ["all",
                           ["==", ["get", "growth_scenario"], growth],
                           ["==", ["get", "market_gravity_weight"], 50]],
        "tooltip_fields": ["growth_scenario", "market_gravity_weight", "region",
                           "cooling_water_consumption_mgy", "cooling_energy_demand_mwh"],
    }


collections = [
    # ── Data centers ──────────────────────────────────────────────
    {
        "collection_id": "fractracker-data-centers",
        "collection_url": f"{DC}/fractracker/data-centers/stac-collection.json",
        "assets": [{
            "id": "data-centers-pmtiles",
            "display_name": "Existing and proposed data centers",
            "group": "Data centers",
            "visible": True,
            "layer_type": "circle",
            "default_style": {
                "circle-color": match("status", STATUS, "#cccccc"),
                "circle-radius": 4.5,
                "circle-stroke-color": "#ffffff",
                "circle-stroke-width": 0.6,
            },
            "tooltip_fields": ["facility_name", "status", "operator_name", "mw",
                               "sizerank", "community_pushback", "city", "state"],
            "legend_type": "categorical",
            "legend_classes": legend(STATUS),
        }],
    },
    {
        "collection_id": "epoch-ai-data-centers",
        "collection_url": f"{DC}/epoch/ai-data-centers/stac-collection.json",
        "assets": [{
            "id": "ai-data-centers-pmtiles",
            "display_name": "Large AI data centers",
            "group": "Data centers",
            "visible": False,
            "layer_type": "circle",
            "default_style": {
                "circle-color": match("owner_name", OWNER),
                "circle-radius": 6,
                "circle-stroke-color": "#222222",
                "circle-stroke-width": 0.8,
            },
            "tooltip_fields": ["name", "owner_name", "current_power_mw",
                               "current_h100_equivalents", "operational", "state"],
            "legend_type": "categorical",
            "legend_classes": legend(OWNER) + [{"label": "Other owner", "color": "#bdbdbd"}],
        }],
    },
    {
        "collection_id": "epoch-ai-data-center-footprints",
        "collection_url": f"{DC}/epoch/ai-data-center-footprints/stac-collection.json",
        "assets": [{
            "id": "ai-data-center-footprints-pmtiles",
            "display_name": "AI data center footprints",
            "group": "Data centers",
            "visible": False,
            "default_style": {"fill-color": match("feature_type", FEATURE, "#cccccc"),
                              "fill-opacity": 0.75},
            "outline_style": outline("#4d4d4d"),
            "tooltip_fields": ["data_center", "feature_type", "building_label", "start_date"],
            "legend_type": "categorical",
            "legend_classes": legend(FEATURE),
        }],
    },
    {
        "collection_id": "pnnl-im3-atlas-campus",
        "collection_url": f"{DC}/pnnl-im3/atlas-campus/stac-collection.json",
        "assets": [{
            "id": "atlas-campus-pmtiles",
            "display_name": "Mapped data center campuses",
            "group": "Data centers",
            "visible": False,
            "default_style": {"fill-color": "#08519C", "fill-opacity": 0.35},
            "outline_style": outline("#08306B", 0.8, 0.9),
            "tooltip_fields": ["name", "operator", "sqft", "county", "state_abb"],
        }],
    },
    {
        "collection_id": "pnnl-im3-atlas-building",
        "collection_url": f"{DC}/pnnl-im3/atlas-building/stac-collection.json",
        "assets": [{
            "id": "atlas-building-pmtiles",
            "display_name": "Mapped data center buildings",
            "group": "Data centers",
            "visible": False,
            "default_style": {"fill-color": "#3182BD", "fill-opacity": 0.6},
            "outline_style": outline("#08519C", 0.6, 0.9),
            "tooltip_fields": ["name", "operator", "sqft", "county", "state_abb"],
        }],
    },
    {
        "collection_id": "pnnl-im3-atlas-point",
        "collection_url": f"{DC}/pnnl-im3/atlas-point/stac-collection.json",
        "assets": [{
            "id": "atlas-point-pmtiles",
            "display_name": "Mapped data center points",
            "group": "Data centers",
            "visible": False,
            "layer_type": "circle",
            "default_style": {"circle-color": "#3182BD", "circle-radius": 4,
                              "circle-stroke-color": "#ffffff", "circle-stroke-width": 0.6},
            "tooltip_fields": ["name", "operator", "county", "state_abb"],
        }],
    },
    # ── Projections and local actions ─────────────────────────────
    {
        "collection_id": "pnnl-im3-projected",
        "collection_url": f"{DC}/pnnl-im3/projected/stac-collection.json",
        "assets": [
            projected("projected-moderate", "moderate",
                      "Projected sites to 2035 under moderate growth", "#fd8d3c"),
            projected("projected-higher", "higher",
                      "Projected sites to 2035 under higher growth", "#800026"),
        ],
        "group": "Projections and local actions",
    },
    {
        "collection_id": "fractracker-moratoriums",
        "collection_url": f"{DC}/fractracker/moratoriums/stac-collection.json",
        "assets": [{
            "id": "moratoriums-pmtiles",
            "display_name": "Local moratoriums and restrictions",
            "group": "Projections and local actions",
            "visible": False,
            "default_style": {"fill-color": match("action", ACTION, "#cccccc"),
                              "fill-opacity": 0.45},
            "outline_style": outline("#4d4d4d"),
            "tooltip_fields": ["jurisdiction", "state", "action", "status",
                               "date_enacted", "expiration_date"],
            "legend_type": "categorical",
            "legend_classes": legend(ACTION),
        }],
    },
    # ── Equity ────────────────────────────────────────────────────
    {
        "collection_id": "svi-2022",
        "collection_url": f"{S3}/public-social-vulnerability/2022/stac-collection.json",
        "assets": [
            {
                "id": "tract-pmtiles",
                "display_name": "Social vulnerability by tract",
                "group": "Equity",
                "visible": False,
                "default_style": {"fill-color": ["interpolate", ["linear"], ["get", "RPL_THEMES"],
                                                 0, "#ffffcc", 0.5, "#fd8d3c", 1, "#bd0026"],
                                  "fill-opacity": 0.65},
                "default_filter": [">=", ["get", "RPL_THEMES"], 0],
                "tooltip_fields": ["COUNTY", "ST_ABBR", "FIPS", "RPL_THEMES"],
                "legend_type": "continuous",
                "legend_label": "SVI percentile",
            },
            {
                "id": "county-pmtiles",
                "display_name": "Social vulnerability by county",
                "group": "Equity",
                "visible": False,
                "default_style": {"fill-color": ["interpolate", ["linear"], ["get", "RPL_THEMES"],
                                                 0, "#ffffcc", 0.5, "#fd8d3c", 1, "#bd0026"],
                                  "fill-opacity": 0.65},
                "default_filter": [">=", ["get", "RPL_THEMES"], 0],
                "tooltip_fields": ["COUNTY", "ST_ABBR", "RPL_THEMES"],
                "legend_type": "continuous",
                "legend_label": "SVI percentile",
            },
        ],
    },
    {
        "collection_id": "acs-2020-2024-blockgroup",
        "collection_url": f"{S3}/public-census/acs-2020-2024/blockgroup/stac-collection.json",
        "assets": [{
            "id": "blockgroup-pmtiles",
            "display_name": "Median household income by block group",
            "group": "Equity",
            "visible": False,
            "default_style": {"fill-color": ["case", ["==", ["typeof", ["get", "MHHI"]], "number"],
                                             ["interpolate", ["linear"], ["get", "MHHI"],
                                              40000, "#D7191C", 75000, "#FDAE61", 101550, "#FFFFBF",
                                              150000, "#A6D96A", 200000, "#1A9641"],
                                             "#cccccc"],
                              "fill-opacity": 0.65},
            "tooltip_fields": ["NAMELSAD", "GEOID", "MHHI", "TotPop", "PovInd", "NoCar"],
            "legend_type": "continuous",
            "legend_label": "Median household income in dollars",
        }],
    },
    {
        "collection_id": "mappinginequality",
        "collection_url": f"{S3}/public-mappinginequality/stac-collection.json",
        "assets": [{
            "id": "mappinginequality-pmtiles",
            "display_name": "Historical redlining grades",
            "group": "Equity",
            "visible": False,
            "default_style": {"fill-color": ["match", ["get", "grade"], "A", "#76A865", "B", "#7CB5BD",
                                             "C", "#F0DE6C", "D", "#D9838D", "#BDBDBD"],
                              "fill-opacity": 0.7},
            "tooltip_fields": ["grade", "city", "label", "category"],
            "legend_type": "categorical",
            "legend_classes": [{"label": "A Best", "color": "#76A865"},
                               {"label": "B Still desirable", "color": "#7CB5BD"},
                               {"label": "C Definitely declining", "color": "#F0DE6C"},
                               {"label": "D Hazardous", "color": "#D9838D"}],
        }],
    },
    {
        "collection_id": "ghs-pop-2020",
        "collection_url": f"{S3}/public-population/ghs-pop-2020/stac-collection.json",
        "assets": [{
            "id": "ghs-pop-2020-cog",
            "display_name": "Population density in 2020",
            "group": "Equity",
            "visible": False,
            "colormap": "magma",
            "rescale": "0,200",
            "nodata": 0,
            "legend_label": "People per 90 m cell",
        }],
    },
    # ── Water ─────────────────────────────────────────────────────
    {
        "collection_id": "epa-sab-v3-cws",
        "collection_url": f"{S3}/public-epa-water/epa-sab-v3/cws/stac-collection.json",
        "assets": [{
            "id": "sab-cws-pmtiles",
            "display_name": "Community water system service areas",
            "group": "Water",
            "visible": False,
            "default_style": {"fill-color": "#5C6BC0", "fill-opacity": 0.3},
            "outline_style": outline("#283593"),
            "tooltip_fields": ["PWS_Name", "PWSID", "Population_Served_Count", "Service_Area_Type"],
        }],
    },
    {
        "collection_id": "usgs-wbd-hu8",
        "collection_url": f"{S3}/public-usgs-wbd/wbd/hu8/stac-collection.json",
        "assets": [{
            "id": "hu8-pmtiles",
            "display_name": "Watersheds",
            "group": "Water",
            "visible": False,
            "default_style": {"fill-color": "#0277BD", "fill-opacity": 0},
            "outline_style": outline("#0277BD", 0.7, 0.6),
            "tooltip_fields": ["name", "huc8", "areasqkm", "states"],
        }],
    },
    {
        "collection_id": "wetlands-nwi",
        "collection_url": f"{S3}/public-wetlands/nwi/stac-collection.json",
        "assets": [{
            "id": "nwi-pmtiles",
            "display_name": "Wetlands",
            "group": "Water",
            "visible": False,
            "default_style": {"fill-color": ["match", ["get", "WETLAND_TYPE"],
                                             "Freshwater Emergent Wetland", "#66C2A5",
                                             "Freshwater Forested/Shrub Wetland", "#1B7837",
                                             "Freshwater Pond", "#41B6C4", "Lake", "#225EA8",
                                             "Riverine", "#7FCDBB",
                                             "Estuarine and Marine Wetland", "#8C6BB1",
                                             "Estuarine and Marine Deepwater", "#4D004B", "#969696"],
                              "fill-opacity": 0.7},
            "tooltip_fields": ["WETLAND_TYPE", "ATTRIBUTE", "state_code"],
        }],
    },
    # ── Hazards ───────────────────────────────────────────────────
    {
        "collection_id": "flood-hazard",
        "collection_url": f"{S3}/public-hazard/flood-hazard/stac-collection.json",
        "assets": [{
            "id": "flood-hazard-pmtiles",
            "display_name": "Flood hazard zones",
            "group": "Hazards",
            "visible": False,
            "default_style": {"fill-color": ["match", ["get", "FLD_ZONE"], "A", "#0D47A1", "AE", "#0D47A1",
                                             "AH", "#1565C0", "AO", "#1565C0", "A99", "#1565C0",
                                             "V", "#B71C1C", "VE", "#B71C1C", "X", "#90CAF9", "#B0BEC5"],
                              "fill-opacity": 0.5},
            "tooltip_fields": ["FLD_ZONE", "ZONE_SUBTY", "SFHA_TF"],
            "legend_type": "categorical",
            "legend_classes": [{"label": "High risk A and AE", "color": "#0D47A1"},
                               {"label": "Coastal high hazard V and VE", "color": "#B71C1C"},
                               {"label": "Minimal risk X", "color": "#90CAF9"}],
        }],
    },
    {
        "collection_id": "sea-level-rise",
        "collection_url": f"{S3}/public-hazard/sea-level-rise/stac-collection.json",
        "assets": [{
            "id": "sea-level-rise-pmtiles",
            "display_name": "Sea level rise of 5 feet",
            "group": "Hazards",
            "visible": False,
            "default_style": {"fill-color": "#01579B", "fill-opacity": 0.55},
            "tooltip_fields": ["state", "region", "slr_ft"],
        }],
    },
    # ── Land and habitat ──────────────────────────────────────────
    {
        "collection_id": "pad-us-4.1-fee",
        "collection_url": f"{S3}/public-padus/padus-4-1/fee/stac-collection.json",
        "assets": [{
            "id": "fee-pmtiles",
            "display_name": "Protected areas",
            "group": "Land and habitat",
            "visible": False,
            "default_style": {"fill-color": ["match", ["get", "GAP_Sts"], "1", "#26633A", "2", "#3E9C47",
                                             "3", "#7EB3D3", "4", "#BDBDBD", "#888888"],
                              "fill-opacity": 0.6},
            "tooltip_fields": ["Unit_Nm", "GAP_Sts", "Mang_Type"],
            "legend_type": "categorical",
            "legend_classes": [{"label": "GAP 1 managed for biodiversity", "color": "#26633A"},
                               {"label": "GAP 2 managed with some extractive use", "color": "#3E9C47"},
                               {"label": "GAP 3 multiple use", "color": "#7EB3D3"},
                               {"label": "GAP 4 no known mandate", "color": "#BDBDBD"}],
        }],
    },
    {
        "collection_id": "usfws-species-ranges",
        "collection_url": f"{S3}/public-usfws/species-ranges/stac-collection.json",
        "assets": [{
            "id": "species-ranges-pmtiles",
            "display_name": "Listed species ranges",
            "group": "Land and habitat",
            "visible": False,
            # ranges overlap heavily, so a faint fill shows where many species meet
            "default_style": {"fill-color": "#6A1B9A", "fill-opacity": 0.06},
            "outline_style": outline("#4A148C", 0.3, 0.4),
            "default_filter": ["match", ["get", "STATUS_ABB"],
                               ["Endangered", "Threatened", "Proposed Endangered", "Proposed Threatened"], True, False],
            "tooltip_fields": ["COMNAME", "SCINAME", "STATUS_ABB", "POP_ABBREV"],
        }],
    },
    {
        "collection_id": "usfws-critical-habitat-final",
        "collection_url": f"{S3}/public-usfws/critical-habitat/final/stac-collection.json",
        "assets": [{
            "id": "final-pmtiles",
            "display_name": "Critical habitat",
            "group": "Land and habitat",
            "visible": False,
            "default_style": {"fill-color": "#AD1457", "fill-opacity": 0.45},
            "outline_style": outline("#880E4F", 0.5, 0.7),
            "tooltip_fields": ["comname", "sciname", "unitname", "status"],
        }],
    },
    {
        "collection_id": "nlcd",
        "collection_url": f"{S3}/public-land-cover/nlcd/stac-collection.json",
        "assets": [{"id": "nlcd-cog-2024", "display_name": "Land cover in 2024",
                    "group": "Land and habitat", "legend_type": "categorical"}],
    },
]

BOUNDS = {"name": "Boundaries", "collapsed": True}
for cid, path, asset, name, color, width, tips in [
    ("census-2024-state", "census-2024/state", "state-pmtiles", "States", "#6A1B9A", 0.8,
     ["NAME", "STUSPS", "GEOID"]),
    ("census-2024-county", "census-2024/county", "county-pmtiles", "Counties", "#6A1B9A", 0.4,
     ["NAMELSAD", "STATEFP", "GEOID"]),
    ("census-2024-tract", "census-2024/tract", "tract-pmtiles", "Census tracts", "#6A1B9A", 0.25,
     ["NAMELSAD", "GEOID", "COUNTYFP"]),
]:
    collections.append({
        "collection_id": cid,
        "collection_url": f"{S3}/public-census/{path}/stac-collection.json",
        "group": BOUNDS,
        "assets": [{"id": asset, "display_name": name, "visible": False,
                    "default_style": {"fill-color": color, "fill-opacity": 0.03},
                    "outline_style": outline(color, width, 0.5),
                    "tooltip_fields": tips}],
    })

# glen draws collections in config order, the first at the bottom of the map. Raster and area
# fills go first, boundary outlines and local actions above them, and data center points last
# so no layer covers them.
DRAW_ORDER = [
    "nlcd", "pad-us-4.1-fee", "usfws-species-ranges", "usfws-critical-habitat-final", "sea-level-rise", "flood-hazard",
    "wetlands-nwi", "usgs-wbd-hu8", "epa-sab-v3-cws", "ghs-pop-2020", "mappinginequality",
    "acs-2020-2024-blockgroup", "svi-2022",
    "census-2024-tract", "census-2024-county", "census-2024-state",
    "fractracker-moratoriums", "pnnl-im3-projected",
    "pnnl-im3-atlas-campus", "pnnl-im3-atlas-building", "epoch-ai-data-center-footprints",
    "pnnl-im3-atlas-point", "epoch-ai-data-centers", "fractracker-data-centers",
]
assert sorted(DRAW_ORDER) == sorted(c["collection_id"] for c in collections), "update DRAW_ORDER"
collections.sort(key=lambda c: DRAW_ORDER.index(c["collection_id"]))

config = {
    "catalog": f"{S3}/public-data/stac/catalog.json",
    "titiler_url": "https://titiler.nrp-nautilus.io",
    "plugins": [
        {"url": f"{GLEN}/core/plugins/mcp.js",
         "options": {"url": "https://duckdb-mcp.nrp-nautilus.io/mcp", "prompt": "geospatial-analyst"}},
        f"{GLEN}/core/plugins/hex.js",
        f"{GLEN}/core/plugins/charts.js",
        f"{GLEN}/core/plugins/draw.js",
        {"url": f"{GLEN}/core/plugins/uploads.js", "options": {}},
        f"{GLEN}/core/plugins/geolocate.js",
    ],
    "auto_approve": True,
    "geocoder": {"provider": "nominatim", "search_box": True},
    "geolocate": {"button": True, "agent_tool": True},
    "sidebar": {"enabled": True, "chat_title": "Chat"},
    "view": {"center": [-96, 38.5], "zoom": 4},
    "welcome": {
        "message": "Explore existing, proposed and projected US data centers alongside social vulnerability, income, water and hazard data. Try asking:",
        "examples": [
            "Show only the proposed data centers that face community pushback.",
            "Which states have the most proposed data center capacity in megawatts?",
            "Show local moratoriums and bans on data centers alongside the proposed data centers.",
            "List the ten largest AI data centers in the US by power and show them on the map.",
            "Show proposed hyperscale and mega campus data centers over social vulnerability by county.",
        ],
    },
    "links": {
        "github": "https://github.com/SchmidtDSE/datacenters",
        "docs": "https://schmidtdse.github.io/glen/",
        "carbon": True,
    },
    "header": {"nav": [
        {"label": "About", "href": "https://schmidtdse.github.io/glen/", "icon": "info"},
        {"label": "Data", "href": "#data", "icon": "database", "external": False},
        {"label": "Explorer", "href": "/explorer/", "external": False},
        {"label": "GitHub", "href": "https://github.com/SchmidtDSE/datacenters", "icon": "github"},
        {"label": "Carbon", "href": "https://carbon-api.nrp-nautilus.io/", "icon": "leaf"},
        {"label": "Contact us", "href": "mailto:dse@berkeley.edu", "icon": "mail", "external": False},
    ]},
    "collections": collections,
}

with open("layers-input.json", "w") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)
    f.write("\n")
print(f"wrote layers-input.json with {len(collections)} collections")
