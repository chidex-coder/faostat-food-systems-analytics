-- Q04 Where is the maize yield gap largest? (2022-2024 average vs the top-decile yield)
SELECT area, region, subregion,
       AVG(yield_kg_ha) / 1000.0 AS yield_t_ha,
       AVG(area_harvested_ha)    AS area_ha,
       AVG(production_t)         AS production_t
FROM v_production
WHERE item_code = '56' AND is_aggregate = 0 AND region IS NOT NULL
  AND year BETWEEN 2022 AND 2024
GROUP BY area_code
HAVING COUNT(*) = 3 AND AVG(area_harvested_ha) >= 100000;
