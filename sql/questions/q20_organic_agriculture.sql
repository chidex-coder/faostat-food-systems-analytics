-- Q20 How fast is organically farmed agricultural area growing?
SELECT a.area AS region, l.year, l.organic_agri_kha, l.agri_land_kha,
       100.0 * l.organic_agri_kha / l.agri_land_kha AS organic_share_pct
FROM v_land l JOIN dim_area a USING (area_code)
WHERE l.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND l.organic_agri_kha IS NOT NULL
ORDER BY a.area, l.year;
