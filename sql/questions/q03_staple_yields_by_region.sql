-- Q03 How do wheat, maize and rice yields compare across continents and how fast are they rising?
SELECT a.area AS region, i.item, p.year, p.yield_kg_ha / 1000.0 AS yield_t_ha
FROM v_production p
JOIN dim_area a USING (area_code)
JOIN dim_item i ON i.domain = 'QCL' AND i.item_code = p.item_code
WHERE p.area_code IN (5100, 5200, 5300, 5400, 5500)
  AND p.item_code IN ('15', '56', '27')
ORDER BY i.item, a.area, p.year;
