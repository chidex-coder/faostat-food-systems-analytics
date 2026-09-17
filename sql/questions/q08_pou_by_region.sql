-- Q08 How has the prevalence of undernourishment moved in each region since 2000?
SELECT f.area AS region, f.year, f.pou_pct, f.undernourished_m
FROM v_food_security f
WHERE f.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND f.pou_pct IS NOT NULL
ORDER BY f.area, f.year;
