-- Units: one row per data center from the chosen source ({{SOURCE}}), with its H3 res-8
-- cells. Shared by every theme: scripts/build-explorer-sql.py puts this in front of each
-- theme body, so every pillar ranks exactly the same facilities.
--   fac   one row per facility: id (_cng_fid of the source's own file, which is also the
--         boundary tiles' id), name, status class, lat, lon.
--   site  the res-8 cell holding the facility point (about 0.7 km²), for site variables.
--   ring  the res-8 cells whose centre lies within {{RADIUS}} miles of the facility.
-- FracTracker statuses are grouped into four classes and filtered by {{STATUS}}. Epoch is
-- filtered to US sites. PNNL projected sites are one growth scenario ({{GROWTH}}) at market
-- gravity weight 50, located by the centroid of their footprint.
fac0 AS (
  SELECT _cng_fid AS id, facility_name AS name, lat, long AS lon,
         CASE WHEN status IN ('Proposed', 'Pre-proposal') THEN 'proposed'
              WHEN status = 'Approved/Permitted/Under construction' THEN 'approved'
              WHEN status IN ('Operating', 'Expanding') THEN 'operating'
              ELSE 'halted' END AS status_class
  FROM read_parquet('s3://public-datacenters/fractracker/data-centers.parquet')
  WHERE '{{SOURCE}}' = 'fractracker' AND lat IS NOT NULL AND long IS NOT NULL
  UNION ALL
  SELECT _cng_fid, name, latitude, longitude, CASE WHEN operational THEN 'operating' ELSE 'approved' END
  FROM read_parquet('s3://public-datacenters/epoch/ai-data-centers.parquet')
  WHERE '{{SOURCE}}' = 'epoch' AND country = 'United States' AND latitude IS NOT NULL
  UNION ALL
  SELECT _cng_fid, COALESCE(NULLIF(name, ''), NULLIF(operator, ''), 'Campus ' || id), lat, lon, 'operating'
  FROM read_parquet('s3://public-datacenters/pnnl-im3/atlas-campus.parquet')
  WHERE '{{SOURCE}}' = 'pnnl-atlas'
  UNION ALL
  SELECT _cng_fid, 'Modelled site ' || id, ST_Y(ST_Centroid(geom)), ST_X(ST_Centroid(geom)), 'projected'
  FROM read_parquet('s3://public-datacenters/pnnl-im3/projected.parquet')
  WHERE '{{SOURCE}}' = 'pnnl-projected' AND growth_scenario = '{{GROWTH}}' AND market_gravity_weight = 50
  UNION ALL
  -- National baseline only (scripts/build-national.py; not a choice in the app): about 2,000
  -- res-8 cells of the contiguous US, picked by hash so the sample is the same on every run.
  SELECT DISTINCT h8::BIGINT, 'Sample cell', h3_cell_to_lat(h8), h3_cell_to_lng(h8), 'sample'
  FROM read_parquet('s3://public-census/census-2024/county/hex/h0=*/data_0.parquet')
  WHERE '{{SOURCE}}' = 'us-sample' AND hash(h8) % 5000 = 0 AND STATEFP NOT IN ('02', '15') AND STATEFP < '60'
),
fac AS MATERIALIZED (
  SELECT *, h3_latlng_to_cell(lat, lon, 8)::UBIGINT AS h8
  FROM fac0
  WHERE '{{SOURCE}}' <> 'fractracker' OR 'all' IN ({{STATUS}}) OR status_class IN ({{STATUS}})
),
site AS MATERIALIZED (
  SELECT id, h8, h3_cell_to_parent(h8, 0)::BIGINT AS h0, h3_cell_area(h8, 'km^2') AS a FROM fac
),
ring AS MATERIALIZED (
  SELECT id, h8, h3_cell_to_parent(h8, 0)::BIGINT AS h0, h3_cell_area(h8, 'km^2') AS a
  FROM (
    SELECT f.id, f.lat, f.lon,
           UNNEST(h3_grid_disk(f.h8, CAST(CEIL({{RADIUS}} * 1.609344 / 0.69) AS INTEGER) + 1))::UBIGINT AS h8
    FROM fac f
  )
  WHERE 2 * 6371.0088 * ASIN(SQRT(
          POWER(SIN(RADIANS(h3_cell_to_lat(h8) - lat) / 2), 2)
          + COS(RADIANS(lat)) * COS(RADIANS(h3_cell_to_lat(h8)))
            * POWER(SIN(RADIANS(h3_cell_to_lng(h8) - lon) / 2), 2)))
        <= {{RADIUS}} * 1.609344
),
