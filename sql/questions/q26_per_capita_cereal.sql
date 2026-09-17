-- Q26 Is cereal production keeping up with population? Per-capita output by region.
SELECT a.area AS region, p.year, p.production_t / pop.population * 1000.0 AS kg_per_capita,
       p.production_t / 1e6 AS production_mt, pop.population / 1e6 AS population_m
FROM v_production p JOIN v_population pop ON pop.area_code = p.area_code AND pop.year = p.year
JOIN dim_area a ON a.area_code = p.area_code
WHERE p.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND p.item_code = '1717'
ORDER BY a.area, p.year;
