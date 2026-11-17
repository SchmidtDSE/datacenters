-- Regulatory screen: how close each facility is to resources that trigger federal review
-- under NEPA and related laws, and how many of them lie in the site cell. Distances run from
-- the facility point to the centre of the nearest res-8 cell holding the resource, or 0 when
-- the site cell holds it; a facility with none within the radius gets the radius itself.
cells AS MATERIALIZED (SELECT DISTINCT h8, h0 FROM ring),
-- ESA section 7: USFWS final and proposed critical habitat
crit8 AS MATERIALIZED (
  SELECT DISTINCT k.h8
  FROM read_parquet('s3://public-usfws/critical-habitat/final/hex/h0=*/data_0.parquet') k
  SEMI JOIN cells c ON c.h8 = k.h8 AND c.h0 = k.h0
),
prop8 AS MATERIALIZED (
  SELECT DISTINCT k.h8
  FROM read_parquet('s3://public-usfws/critical-habitat/proposed/hex/h0=*/data_0.parquet') k
  SEMI JOIN cells c ON c.h8 = k.h8 AND c.h0 = k.h0
),
-- ESA section 7: USFWS ranges of listed and proposed species that cover the site cell, as
-- IPaC screens a project location. Ranges are coarse, often whole counties, so only the site
-- cell is used.
spsite AS MATERIALIZED (SELECT DISTINCT r.h8, r.h0 FROM ring r JOIN fac f USING (id) WHERE r.h8 = f.h8),
spp8 AS MATERIALIZED (
  SELECT s.h8, COUNT(DISTINCT s.ENTITY_ID) AS n
  FROM read_parquet('s3://public-usfws/species-ranges/hex/h0=*/data_0.parquet') s
  SEMI JOIN spsite c ON c.h8 = s.h8 AND c.h0 = s.h0
  WHERE s.STATUS_ABB IN ('Endangered', 'Threatened', 'Proposed Endangered', 'Proposed Threatened')
  GROUP BY s.h8
),
-- Clean Water Act section 404: NWI wetlands, the same classes as the water pillar
wet8 AS MATERIALIZED (
  SELECT DISTINCT n.h8
  FROM read_parquet('s3://public-wetlands/nwi-v2/hex/h0=*/data_0.parquet') n
  SEMI JOIN cells c ON c.h8 = n.h8 AND c.h0 = n.h0
  WHERE n.WETLAND_TYPE IN ('Freshwater Emergent Wetland', 'Freshwater Forested/Shrub Wetland', 'Estuarine and Marine Wetland')
),
-- Executive Order 11988: FEMA special flood hazard areas (1% annual chance A and V zones)
fld8 AS MATERIALIZED (
  SELECT DISTINCT z.h8
  FROM read_parquet('s3://public-hazard/flood-hazard/hex/h0=*/data_0.parquet') z
  SEMI JOIN cells c ON c.h8 = z.h8 AND c.h0 = z.h0
  WHERE z.SFHA_TF = 'T'
),
-- Wild and Scenic Rivers Act: designated rivers and Nationwide Rivers Inventory segments
riv8 AS MATERIALIZED (
  SELECT DISTINCT w.h8
  FROM read_parquet('s3://public-rivers/american-rivers/wild-scenic-designated/hex/h0=*/data_0.parquet') w
  SEMI JOIN cells c ON c.h8 = w.h8 AND c.h0 = w.h0
  UNION
  SELECT DISTINCT n.h8
  FROM read_parquet('s3://public-rivers/american-rivers/nri-2024/hex/h0=*/data_0.parquet') n
  SEMI JOIN cells c ON c.h8 = n.h8 AND c.h0 = n.h0
),
-- NHPA section 106 and Executive Order 13175: Census AIANNH legal land bases, meaning
-- federal and state reservations, off-reservation trust land and Hawaiian home lands, plus the
-- Oklahoma tribal statistical areas, several of which courts have held to be reservations since
-- McGirt v. Oklahoma (2020); the other statistical areas (tribal and state designated, Alaska
-- Native village, joint-use) are left out
trb8 AS MATERIALIZED (
  SELECT DISTINCT t.h8
  FROM read_parquet('s3://public-census/census-2024/aiannh/hex/h0=*/data_0.parquet') t
  SEMI JOIN cells c ON c.h8 = t.h8 AND c.h0 = t.h0
  WHERE t.CLASSFP IN ('D2', 'D3', 'D4', 'D5', 'D8', 'F1') OR t.MTFCC = 'G2140'
),
-- distance in miles from each facility to each ring cell, 0 for the site cell
dist AS MATERIALIZED (
  SELECT r.id, r.h8,
         CASE WHEN r.h8 = f.h8 THEN 0
              ELSE 2 * 3958.7613 * ASIN(SQRT(
                     POWER(SIN(RADIANS(h3_cell_to_lat(r.h8) - f.lat) / 2), 2)
                     + COS(RADIANS(f.lat)) * COS(RADIANS(h3_cell_to_lat(r.h8)))
                       * POWER(SIN(RADIANS(h3_cell_to_lng(r.h8) - f.lon) / 2), 2))) END AS mi
  FROM ring r JOIN fac f USING (id)
),
near AS (
  SELECT d.id,
         MIN(d.mi) FILTER (WHERE k.h8 IS NOT NULL) AS crit,
         MIN(d.mi) FILTER (WHERE p.h8 IS NOT NULL) AS prop,
         MIN(d.mi) FILTER (WHERE w.h8 IS NOT NULL) AS wet,
         MIN(d.mi) FILTER (WHERE z.h8 IS NOT NULL) AS fld,
         MIN(d.mi) FILTER (WHERE v.h8 IS NOT NULL) AS riv,
         MIN(d.mi) FILTER (WHERE t.h8 IS NOT NULL) AS trb
  FROM dist d
  LEFT JOIN crit8 k USING (h8) LEFT JOIN prop8 p USING (h8) LEFT JOIN wet8 w USING (h8)
  LEFT JOIN fld8 z USING (h8) LEFT JOIN riv8 v USING (h8) LEFT JOIN trb8 t USING (h8)
  GROUP BY d.id
),
agg AS (
  SELECT f.id,
         COALESCE(n.crit, {{RADIUS}}) AS crit, COALESCE(n.prop, {{RADIUS}}) AS prop,
         COALESCE(n.wet, {{RADIUS}}) AS wet, COALESCE(n.fld, {{RADIUS}}) AS fld,
         COALESCE(n.riv, {{RADIUS}}) AS riv, COALESCE(n.trb, {{RADIUS}}) AS trb, COALESCE(sp.n, 0) AS species,
         COALESCE(n.crit = 0, false)::INT + COALESCE(n.prop = 0, false)::INT + COALESCE(n.wet = 0, false)::INT
           + COALESCE(n.fld = 0, false)::INT + COALESCE(n.riv = 0, false)::INT + COALESCE(n.trb = 0, false)::INT AS on_site
  FROM fac f LEFT JOIN near n USING (id) LEFT JOIN spp8 sp ON sp.h8 = f.h8
),
vals AS (
  SELECT id, 'on_site' AS variable, 'Screened resources in the site cell' AS label, on_site AS value, 'resources' AS unit, 'int' AS fmt, 'linear' AS scale, 1 AS dir FROM agg
  UNION ALL SELECT id, 'listed_species', 'Listed and proposed species whose range covers the site', species, 'species', 'int', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'critical_habitat_mi', 'Distance to final critical habitat', crit, 'miles', 'num1', 'linear', -1 FROM agg
  UNION ALL SELECT id, 'proposed_habitat_mi', 'Distance to proposed critical habitat', prop, 'miles', 'num1', 'linear', -1 FROM agg
  UNION ALL SELECT id, 'wetland_mi', 'Distance to a mapped wetland', wet, 'miles', 'num1', 'linear', -1 FROM agg
  UNION ALL SELECT id, 'floodplain_mi', 'Distance to a special flood hazard area', fld, 'miles', 'num1', 'linear', -1 FROM agg
  UNION ALL SELECT id, 'river_mi', 'Distance to a Wild and Scenic or inventoried river', riv, 'miles', 'num1', 'linear', -1 FROM agg
  UNION ALL SELECT id, 'tribal_mi', 'Distance to tribal land', trb, 'miles', 'num1', 'linear', -1 FROM agg
),
