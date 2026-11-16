-- Biodiversity and land: natural land on the site, and the intactness, species richness and
-- protected or critical habitat of the radius.
cells AS MATERIALIZED (SELECT DISTINCT h8, h0 FROM ring),
-- NLCD 2024 natural classes (forest 41-43, shrub 51-52, grassland 71-74, wetland 90, 95)
-- as a share of the site cell, from res-10 class fractions
natland AS (
  SELECT s.id, SUM(n.frac) / 49.0 AS share
  FROM site s
  JOIN read_parquet('s3://public-land-cover/nlcd/hex-fractions/year=*/h0=*/data_0.parquet', hive_partitioning = true) n
    ON n.h0 = s.h0 AND n.h8 = s.h8
  WHERE n.year = 2024 AND n.nlcd IN (41, 42, 43, 51, 52, 71, 72, 73, 74, 90, 95)
  GROUP BY s.id
),
ghm8 AS MATERIALIZED (
  SELECT g.h8, AVG(g.ghm) AS ghm
  FROM read_parquet('s3://public-human-modification/ghm/hex/h0=*/data_0.parquet') g
  SEMI JOIN cells c ON c.h8 = g.h8 AND c.h0 = g.h0
  WHERE NOT isnan(g.ghm)
  GROUP BY g.h8
),
-- IUCN 2025 threatened species richness on IUCN's ~10 km grid (res 5)
thr5 AS MATERIALIZED (
  SELECT t.h5, AVG(t.combined_thr_sr) AS thr
  FROM read_parquet('s3://public-iucn/hex/combined_thr_sr/h0=*/data_0.parquet') t
  SEMI JOIN (SELECT DISTINCT h3_cell_to_parent(h8, 5) AS h5, h0 FROM cells) c ON c.h5 = t.h5 AND c.h0 = t.h0
  WHERE NOT isnan(t.combined_thr_sr)
  GROUP BY t.h5
),
mobi8 AS MATERIALIZED (
  SELECT m.h8, MAX(m.species_richness) AS mobi
  FROM read_parquet('s3://public-mobi/mobi-species-richness-all/hex/h0=*/data_0.parquet') m
  SEMI JOIN cells c ON c.h8 = m.h8 AND c.h0 = m.h0
  GROUP BY m.h8
),
crit8 AS MATERIALIZED (
  SELECT DISTINCT k.h8
  FROM read_parquet('s3://public-usfws/critical-habitat/final/hex/h0=*/data_0.parquet') k
  SEMI JOIN cells c ON c.h8 = k.h8 AND c.h0 = k.h0
),
-- PAD-US 4.1 fee lands managed for biodiversity (GAP 1-3), share of each res-8 cell
pad8 AS MATERIALIZED (
  SELECT p.h8, COUNT(DISTINCT p.h10) / 49.0 AS p
  FROM read_parquet('s3://public-padus/padus-4-1/fee/hex/h0=*/data_0.parquet') p
  SEMI JOIN cells c ON c.h8 = p.h8 AND c.h0 = p.h0
  WHERE p.GAP_Sts IN ('1', '2', '3')
  GROUP BY p.h8
),
ringv AS (
  SELECT r.id,
         1 - SUM(r.a * g.ghm) / NULLIF(SUM(r.a) FILTER (WHERE g.ghm IS NOT NULL), 0) AS intact,
         SUM(r.a * t.thr) / NULLIF(SUM(r.a) FILTER (WHERE t.thr IS NOT NULL), 0) AS thr,
         SUM(r.a * m.mobi) / NULLIF(SUM(r.a) FILTER (WHERE m.mobi IS NOT NULL), 0) AS mobi,
         SUM(r.a) FILTER (WHERE k.h8 IS NOT NULL) / SUM(r.a) AS crit,
         SUM(r.a * COALESCE(p.p, 0)) / SUM(r.a) AS pad
  FROM ring r
  LEFT JOIN ghm8 g USING (h8)
  LEFT JOIN thr5 t ON t.h5 = h3_cell_to_parent(r.h8, 5)
  LEFT JOIN mobi8 m USING (h8)
  LEFT JOIN crit8 k USING (h8)
  LEFT JOIN pad8 p USING (h8)
  GROUP BY r.id
),
agg AS (
  SELECT f.id, COALESCE(n.share, 0) AS natural_share, v.intact, v.thr, v.mobi, COALESCE(v.crit, 0) AS crit, v.pad
  FROM fac f LEFT JOIN natland n USING (id) LEFT JOIN ringv v USING (id)
),
vals AS (
  SELECT id, 'natural_site' AS variable, 'Natural land in the site cell' AS label, natural_share AS value, 'share' AS unit, 'pct' AS fmt, 'linear' AS scale, 1 AS dir FROM agg
  UNION ALL SELECT id, 'intactness', 'Landscape intactness in the radius', intact, '1 − gHM', 'num2', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'threatened', 'Mean threatened species richness', thr, 'species', 'num1', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'imperiled', 'Mean imperiled species richness', mobi, 'species', 'num1', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'critical_habitat', 'Critical habitat share of the radius', crit, 'share', 'pct', 'linear', 1 FROM agg
  UNION ALL SELECT id, 'protected', 'Protected area share of the radius', pad, 'share', 'pct', 'linear', 1 FROM agg
),
