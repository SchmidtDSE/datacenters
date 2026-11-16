-- Water: the local water system, other data centers in the same watershed, and the wetland
-- and flood-zone share of the radius.
cells AS MATERIALIZED (SELECT DISTINCT h8, h0 FROM ring),
-- The largest EPA community water system whose service area covers the site cell
cws AS (
  SELECT s.id, MAX(w.Population_Served_Count) AS served
  FROM site s
  JOIN read_parquet('s3://public-epa-water/epa-sab-v3/cws/hex/h0=*/data_0.parquet') w
    ON w.h0 = s.h0 AND w.h8 = s.h8
  GROUP BY s.id
),
-- HUC8 subbasin of the site cell (the most common one among its HU12 rows)
huc AS MATERIALIZED (
  SELECT s.id, MODE(LEFT(w.huc12, 8)) AS huc8
  FROM site s
  JOIN read_parquet('s3://public-usgs-wbd/wbd/hu12/hex/h0=*/data_0.parquet') w
    ON w.h0 = s.h0 AND w.h8 = s.h8
  GROUP BY s.id
),
peers AS (
  SELECT a.id, COUNT(b.id) AS n
  FROM huc a LEFT JOIN huc b ON b.huc8 = a.huc8 AND b.id <> a.id
  GROUP BY a.id
),
-- Vegetated NWI wetlands (lakes, rivers and ponds left out), share of each res-8 cell
wet8 AS MATERIALIZED (
  SELECT n.h8, COUNT(DISTINCT n.h10) / 49.0 AS w
  FROM read_parquet('s3://public-wetlands/nwi-v2/hex/h0=*/data_0.parquet') n
  SEMI JOIN cells c ON c.h8 = n.h8 AND c.h0 = n.h0
  WHERE n.WETLAND_TYPE IN ('Freshwater Emergent Wetland', 'Freshwater Forested/Shrub Wetland', 'Estuarine and Marine Wetland')
  GROUP BY n.h8
),
-- FEMA special flood hazard areas (the 1% annual chance A and V zones)
fld8 AS MATERIALIZED (
  SELECT z.h8, COUNT(DISTINCT z.h10) / 49.0 AS f
  FROM read_parquet('s3://public-hazard/flood-hazard/hex/h0=*/data_0.parquet') z
  SEMI JOIN cells c ON c.h8 = z.h8 AND c.h0 = z.h0
  WHERE z.SFHA_TF = 'T'
  GROUP BY z.h8
),
ringv AS (
  SELECT r.id, SUM(r.a * COALESCE(w.w, 0)) / SUM(r.a) AS wet, SUM(r.a * COALESCE(f.f, 0)) / SUM(r.a) AS flood
  FROM ring r LEFT JOIN wet8 w USING (h8) LEFT JOIN fld8 f USING (h8)
  GROUP BY r.id
),
cool AS (
  SELECT _cng_fid AS id, cooling_water_consumption_mgy AS mgy
  FROM read_parquet('s3://public-datacenters/pnnl-im3/projected.parquet') WHERE '{{SOURCE}}' = 'pnnl-projected'
),
agg AS (
  SELECT f.id, COALESCE(c.served, 0) AS served, p.n AS peers, v.wet, v.flood, k.mgy
  FROM fac f LEFT JOIN cws c USING (id) LEFT JOIN peers p USING (id) LEFT JOIN ringv v USING (id) LEFT JOIN cool k USING (id)
),
vals AS (
  SELECT id, 'water_system' AS variable, 'People served by the local water system' AS label, served AS value, 'people' AS unit, 'compact' AS fmt, 'log' AS scale, 1 AS dir FROM agg
  UNION ALL SELECT id, 'watershed_peers', 'Other facilities in the same HUC8 subbasin', peers, 'facilities', 'int', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'wetland_share', 'Wetland share of the radius', wet, 'share', 'pct', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'flood_share', 'Flood zone share of the radius', flood, 'share', 'pct', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'cooling_water', 'Cooling water consumption', mgy, 'million gallons per year', 'num1', 'linear', 1 FROM agg
),
