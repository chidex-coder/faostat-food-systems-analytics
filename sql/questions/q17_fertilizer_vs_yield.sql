-- Q17 How does nitrogen intensity relate to cereal yield across countries?
SELECT p.area, p.region, p.year, f.n_kg_per_ha, p.yield_kg_ha / 1000.0 AS cereal_yield_t_ha, p.area_harvested_ha
FROM v_production p JOIN v_fertilizer f ON f.area_code = p.area_code AND f.year = p.year
WHERE p.item_code = '1717' AND p.is_aggregate = 0 AND p.region IS NOT NULL
  AND p.year = (SELECT MAX(year) FROM v_fertilizer WHERE n_kg_per_ha IS NOT NULL)
  AND f.n_kg_per_ha > 0 AND p.area_harvested_ha >= 50000;
