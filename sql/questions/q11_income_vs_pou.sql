-- Q11 How strongly is national income associated with undernourishment?
WITH latest AS (
  SELECT area_code, MAX(year) AS y FROM v_food_security
  WHERE pou_pct IS NOT NULL AND gdp_cap_ppp IS NOT NULL GROUP BY area_code)
SELECT f.area, f.region, f.year, f.gdp_cap_ppp, f.pou_pct, p.population / 1e6 AS population_m
FROM v_food_security f
JOIN latest l ON l.area_code = f.area_code AND l.y = f.year
LEFT JOIN v_population p ON p.area_code = f.area_code AND p.year = f.year
WHERE f.is_aggregate = 0 AND f.region IS NOT NULL;
