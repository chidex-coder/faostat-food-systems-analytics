-- Q30 Where has cereal production growth lagged population growth since 2010?
SELECT p.area, p.region, p.year, p.production_t, pop.population
FROM v_production p JOIN v_population pop ON pop.area_code = p.area_code AND pop.year = p.year
WHERE p.item_code = '1717' AND p.is_aggregate = 0 AND p.region IS NOT NULL AND p.year IN (2010, 2024);
