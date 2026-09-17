-- Q24 Do hotter-than-usual years coincide with below-trend wheat yields?
SELECT p.area, p.region, p.year, p.yield_kg_ha / 1000.0 AS wheat_yield_t_ha, t.temp_change_c, p.area_harvested_ha
FROM v_production p JOIN v_temperature t ON t.area_code = p.area_code AND t.year = p.year
WHERE p.item_code = '15' AND p.is_aggregate = 0 AND p.region IS NOT NULL AND p.year >= 1990
  AND p.area_harvested_ha >= 200000;
