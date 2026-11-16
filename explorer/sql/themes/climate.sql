-- Climate footprint: the facility's reported size and power, and the carbon stored on its site.
-- FracTracker text fields are read with TRY_CAST, so an entry such as "300+" counts as missing.
attr AS (
  SELECT _cng_fid AS id,
         NULLIF(TRY_CAST(mw AS DOUBLE), 0) AS mw,
         NULLIF(TRY_CAST(replace(facility_size_sqft, ',', '') AS DOUBLE), 0) AS sqft,
         CASE WHEN regexp_matches(lower(COALESCE(power_source, '') || ' ' || COALESCE(dedicated_power_plant, '')),
                                  'gas|coal|oil|diesel|turbine|fracked|fossil') THEN 1 ELSE 0 END AS fossil,
         NULL::DOUBLE AS cool_mwh
  FROM read_parquet('s3://public-datacenters/fractracker/data-centers.parquet') WHERE '{{SOURCE}}' = 'fractracker'
  UNION ALL
  SELECT _cng_fid, NULLIF(current_power_mw, 0), NULL, NULL, NULL
  FROM read_parquet('s3://public-datacenters/epoch/ai-data-centers.parquet') WHERE '{{SOURCE}}' = 'epoch'
  UNION ALL
  SELECT _cng_fid, NULL, NULLIF(sqft, 0), NULL, NULL
  FROM read_parquet('s3://public-datacenters/pnnl-im3/atlas-campus.parquet') WHERE '{{SOURCE}}' = 'pnnl-atlas'
  UNION ALL
  SELECT _cng_fid, data_center_it_power_mw, campus_size_square_ft, NULL, cooling_energy_demand_mwh
  FROM read_parquet('s3://public-datacenters/pnnl-im3/projected.parquet') WHERE '{{SOURCE}}' = 'pnnl-projected'
),
-- Conservation International vulnerable carbon 2024, total Mg C in the facility's res-8 cell
carbon AS (
  SELECT s.id, SUM(c.carbon) AS mg
  FROM site s
  JOIN read_parquet('s3://public-carbon/vulnerable-carbon-2024/hex/h0=*/data_0.parquet') c
    ON c.h0 = s.h0 AND c.h8 = s.h8
  WHERE NOT isnan(c.carbon)
  GROUP BY s.id
),
agg AS (
  SELECT f.id, a.mw, a.sqft, a.fossil, a.cool_mwh, COALESCE(c.mg, 0) AS carbon
  FROM fac f LEFT JOIN attr a USING (id) LEFT JOIN carbon c USING (id)
),
vals AS (
  SELECT id, 'power_mw' AS variable, 'Power capacity' AS label, mw AS value, 'MW' AS unit, 'compact' AS fmt, 'log' AS scale, 1 AS dir FROM agg
  UNION ALL SELECT id, 'floor_area', 'Floor area', sqft, 'sq ft', 'compact', 'log', 1 FROM agg
  UNION ALL SELECT id, 'fossil_power', 'Dedicated fossil power reported', fossil, 'yes = 1', 'int', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'site_carbon', 'Vulnerable carbon in the site cell', carbon, 'Mg C', 'compact', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'cooling_energy', 'Cooling energy demand', cool_mwh, 'MWh per year', 'compact', 'linear', 1 FROM agg
),
