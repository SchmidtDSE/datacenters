-- Environmental justice: who lives within the radius. Tract and block-group values are
-- weighted by GHS-POP 2020 population per res-8 cell, so a cell with no residents adds nothing.
cells AS MATERIALIZED (SELECT DISTINCT h8, h0 FROM ring),
pop8 AS MATERIALIZED (
  SELECT p.h8, SUM(p.population) AS pop
  FROM read_parquet('s3://public-population/ghs-pop-2020/hex/h0=*/data_0.parquet') p
  SEMI JOIN cells c ON c.h8 = p.h8 AND c.h0 = p.h0
  WHERE NOT isnan(p.population)
  GROUP BY p.h8
),
-- SVI 2022 by tract, averaged over the res-10 cells of each res-8 cell (an area weight)
svi8 AS MATERIALIZED (
  SELECT s.h8,
         AVG(s.RPL_THEMES) FILTER (WHERE s.RPL_THEMES >= 0) AS svi,
         AVG(s.E_MINRTY / s.E_TOTPOP) FILTER (WHERE s.E_TOTPOP > 0 AND s.E_MINRTY >= 0) AS poc
  FROM read_parquet('s3://public-social-vulnerability/svi-2022-tract/hex/h0=*/data_0.parquet') s
  SEMI JOIN cells c ON c.h8 = s.h8 AND c.h0 = s.h0
  GROUP BY s.h8
),
-- ACS 2020-2024 by block group
acs8 AS MATERIALIZED (
  SELECT a.h8,
         AVG(a.PovInd / a.TotPop) FILTER (WHERE a.TotPop > 0 AND a.PovInd >= 0) AS pov,
         AVG(a.MHHI) FILTER (WHERE a.MHHI > 0) AS mhhi
  FROM read_parquet('s3://public-census/acs-2020-2024/blockgroup/hex/h0=*/data_0.parquet') a
  SEMI JOIN cells c ON c.h8 = a.h8 AND c.h0 = a.h0
  GROUP BY a.h8
),
-- HOLC grade D ("hazardous") share of each res-8 cell, from its res-10 cells
red8 AS MATERIALIZED (
  SELECT m.h8, COUNT(DISTINCT m.h10) / 49.0 AS d
  FROM read_parquet('s3://public-mappinginequality/hex/h0=*/data_0.parquet') m
  SEMI JOIN cells c ON c.h8 = m.h8 AND c.h0 = m.h0
  WHERE m.grade = 'D'
  GROUP BY m.h8
),
agg AS (
  SELECT r.id,
         SUM(COALESCE(p.pop, 0)) AS pop,
         SUM(p.pop * s.svi) / NULLIF(SUM(p.pop) FILTER (WHERE s.svi IS NOT NULL), 0) AS svi,
         SUM(p.pop * s.poc) / NULLIF(SUM(p.pop) FILTER (WHERE s.poc IS NOT NULL), 0) AS poc,
         SUM(p.pop * a.pov) / NULLIF(SUM(p.pop) FILTER (WHERE a.pov IS NOT NULL), 0) AS pov,
         SUM(p.pop * a.mhhi) / NULLIF(SUM(p.pop) FILTER (WHERE a.mhhi IS NOT NULL), 0) AS mhhi,
         SUM(r.a * COALESCE(d.d, 0)) / SUM(r.a) AS red
  FROM ring r
  LEFT JOIN pop8 p USING (h8) LEFT JOIN svi8 s USING (h8) LEFT JOIN acs8 a USING (h8) LEFT JOIN red8 d USING (h8)
  GROUP BY r.id
),
vals AS (
  SELECT id, 'svi' AS variable, 'Social vulnerability index' AS label, svi AS value, 'percentile 0–1' AS unit, 'num2' AS fmt, 'linear' AS scale, 1 AS dir FROM agg
  UNION ALL SELECT id, 'people_of_colour', 'Share of residents who are people of colour', poc, 'share', 'pct', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'poverty', 'Share of residents below the poverty line', pov, 'share', 'pct', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'income', 'Median household income', mhhi, 'USD', 'usd', 'linear', -1 FROM agg
  UNION ALL SELECT id, 'residents', 'Residents within the radius', pop, 'people', 'compact', 'log', 1 FROM agg
  UNION ALL SELECT id, 'redlined', 'Share of the radius graded hazardous in the 1930s', red, 'share', 'pct', 'linear', 1 FROM agg
),
