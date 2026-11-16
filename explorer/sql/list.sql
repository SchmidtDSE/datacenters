SELECT f.id, ANY_VALUE(f.name) || COALESCE(' (' || ANY_VALUE(st.STUSPS) || ')', '') AS name,
       ANY_VALUE(f.lon) - 0.06 AS xmin, ANY_VALUE(f.lat) - 0.045 AS ymin,
       ANY_VALUE(f.lon) + 0.06 AS xmax, ANY_VALUE(f.lat) + 0.045 AS ymax
FROM fac f
LEFT JOIN read_parquet('s3://public-census/census-2024/state/hex/h0=*/data_0.parquet') st
  ON st.h0 = h3_cell_to_parent(f.h8, 0)::BIGINT AND st.h8 = f.h8
GROUP BY f.id
ORDER BY name
