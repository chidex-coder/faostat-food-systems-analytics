-- Q05 Since 2000, how much of each region's cereal production growth came from yield versus area?
WITH latest AS (SELECT MAX(year) AS y FROM v_production WHERE area_code = 5000 AND item_code = '1717')
SELECT a.area AS region, p.year, p.production_t, p.area_harvested_ha, p.yield_kg_ha
FROM v_production p JOIN dim_area a USING (area_code), latest
WHERE p.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND p.item_code = '1717'
  AND p.year IN (2000, latest.y)
ORDER BY a.area, p.year;
