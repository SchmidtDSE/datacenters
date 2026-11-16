-- Score: mid-rank percentile, 0-100, among the facilities in view that have a value. Tied
-- values share the midpoint of their rank range. dir = +1 when a higher value means more
-- likely impact or concern, -1 when a lower value does.
ranked AS (
  SELECT *, CASE WHEN value IS NULL THEN NULL
                 ELSE ROUND(100 * ((RANK() OVER w - 1) + (COUNT(*) OVER w - 1)) / 2.0
                            / NULLIF(COUNT(*) OVER (PARTITION BY variable, value IS NULL) - 1, 0), 1)
            END AS pct
  FROM vals
  WINDOW w AS (PARTITION BY variable, value IS NULL ORDER BY dir * value)
)
-- value is kept to 4 significant figures
SELECT id, variable, label,
       CASE WHEN value IS NULL OR value = 0 THEN value
            ELSE ROUND(value, 3 - CAST(FLOOR(LOG10(ABS(value))) AS INTEGER)) END AS value,
       unit, fmt, scale, dir, pct,
       ROUND(AVG(pct) OVER (PARTITION BY id), 1) AS pillar_score
FROM ranked
ORDER BY id, variable
