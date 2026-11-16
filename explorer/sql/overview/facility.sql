-- Facility card: what the source reports about the facility, local actions covering its
-- site, and the other sources that list a facility within 1.5 km. Not scored.
attr AS (
  SELECT _cng_fid AS id, 'FracTracker' AS source, status,
         NULLIF(NULLIF(operator_name, 'nan'), '') AS operator, NULLIF(NULLIF(tenant, 'nan'), '') AS tenant,
         TRY_CAST(mw AS DOUBLE) AS mw, NULLIF(NULLIF(expected_date_online, 'nan'), '') AS online,
         NULLIF(NULLIF(power_source, 'nan'), '') AS power_source, NULLIF(NULLIF(dedicated_power_plant, 'nan'), '') AS dedicated_power,
         NULLIF(NULLIF(cooling_source, 'nan'), '') AS cooling, NULLIF(NULLIF(community_pushback, 'nan'), '') AS pushback,
         NULLIF(NULLIF(resistance_status, 'nan'), '') AS resistance, NULLIF(NULLIF(nda, 'nan'), '') AS nda
  FROM read_parquet('s3://public-datacenters/fractracker/data-centers.parquet') WHERE '{{SOURCE}}' = 'fractracker'
  UNION ALL
  SELECT _cng_fid, 'Epoch AI', CASE WHEN operational THEN 'Operational' ELSE 'Not yet operational' END,
         NULLIF(owner_name, ''), NULLIF(users, ''), current_power_mw, NULL, NULLIF(energy_companies, ''), NULL, NULL, NULL, NULL, NULL
  FROM read_parquet('s3://public-datacenters/epoch/ai-data-centers.parquet') WHERE '{{SOURCE}}' = 'epoch'
  UNION ALL
  SELECT _cng_fid, 'PNNL IM3 atlas', 'Mapped campus', NULLIF(operator, ''), NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
  FROM read_parquet('s3://public-datacenters/pnnl-im3/atlas-campus.parquet') WHERE '{{SOURCE}}' = 'pnnl-atlas'
  UNION ALL
  SELECT _cng_fid, 'PNNL IM3 projected', 'Modelled site, ' || growth_scenario || ' growth', NULL, NULL,
         data_center_it_power_mw, NULL, NULL, NULL,
         CAST(ROUND(100 * water_cooling_frac) AS INTEGER) || '% water cooling', NULL, NULL, NULL
  FROM read_parquet('s3://public-datacenters/pnnl-im3/projected.parquet') WHERE '{{SOURCE}}' = 'pnnl-projected'
),
place AS (
  SELECT s.id, ANY_VALUE(st.STUSPS) AS state, ANY_VALUE(co.NAMELSAD) AS county
  FROM site s
  LEFT JOIN read_parquet('s3://public-census/census-2024/state/hex/h0=*/data_0.parquet') st ON st.h0 = s.h0 AND st.h8 = s.h8
  LEFT JOIN read_parquet('s3://public-census/census-2024/county/hex/h0=*/data_0.parquet') co ON co.h0 = s.h0 AND co.h8 = s.h8
  GROUP BY s.id
),
actions AS (
  SELECT s.id, STRING_AGG(DISTINCT m.action || ' (' || lower(m.status) || ') in ' || m.jurisdiction, '; ') AS actions
  FROM site s
  JOIN read_parquet('s3://public-datacenters/fractracker/moratoriums/hex/h0=*/data_0.parquet') m ON m.h0 = s.h0 AND m.h8 = s.h8
  GROUP BY s.id
),
others AS (
  SELECT 'FracTracker' AS src, lat, long AS lon FROM read_parquet('s3://public-datacenters/fractracker/data-centers.parquet') WHERE lat IS NOT NULL
  UNION ALL SELECT 'Epoch AI', latitude, longitude FROM read_parquet('s3://public-datacenters/epoch/ai-data-centers.parquet') WHERE country = 'United States'
  UNION ALL SELECT 'PNNL atlas', lat, lon FROM read_parquet('s3://public-datacenters/pnnl-im3/atlas-campus.parquet')
  UNION ALL SELECT 'PNNL atlas', lat, lon FROM read_parquet('s3://public-datacenters/pnnl-im3/atlas-point.parquet')
),
near AS (
  SELECT id, STRING_AGG(src || ' ' || n, ', ' ORDER BY src) AS nearby
  FROM (
    SELECT f.id, o.src, COUNT(*) AS n
    FROM fac f JOIN others o ON ABS(o.lat - f.lat) < 0.02 AND ABS(o.lon - f.lon) < 0.03
    WHERE o.src <> (SELECT source FROM attr LIMIT 1) AND NOT (o.src = 'PNNL atlas' AND '{{SOURCE}}' = 'pnnl-atlas')
      AND 2 * 6371.0088 * ASIN(SQRT(POWER(SIN(RADIANS(o.lat - f.lat) / 2), 2)
            + COS(RADIANS(f.lat)) * COS(RADIANS(o.lat)) * POWER(SIN(RADIANS(o.lon - f.lon) / 2), 2))) <= 1.5
    GROUP BY ALL
  )
  GROUP BY id
)
SELECT f.id, f.name, a.source, a.status, a.operator, a.tenant, a.mw, a.online, a.power_source, a.dedicated_power,
       a.cooling, a.pushback, a.resistance, a.nda, p.state, p.county,
       COALESCE(x.actions, 'None recorded') AS actions, COALESCE(n.nearby, 'None') AS nearby
FROM fac f LEFT JOIN attr a USING (id) LEFT JOIN place p USING (id) LEFT JOIN actions x USING (id) LEFT JOIN near n USING (id)
ORDER BY f.id
