-- Q01 How has world cereal production, harvested area and yield evolved since 1961?
SELECT year,
       production_t / 1e6      AS production_mt,
       area_harvested_ha / 1e6 AS area_mha,
       yield_kg_ha / 1000.0    AS yield_t_ha
FROM v_production
WHERE area_code = 5000 AND item_code = '1717'
ORDER BY year;
