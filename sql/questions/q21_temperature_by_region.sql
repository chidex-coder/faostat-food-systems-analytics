-- Q21 How much has land surface temperature changed in each region (vs the 1951-1980 baseline)?
SELECT a.area AS region, t.year, t.temp_change_c
FROM v_temperature t JOIN dim_area a USING (area_code)
WHERE t.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND t.temp_change_c IS NOT NULL
ORDER BY a.area, t.year;
