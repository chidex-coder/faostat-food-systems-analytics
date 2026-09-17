-- Q18 How is land used in each region, and how has cropland / pasture / forest changed since 1990?
SELECT a.area AS region, l.year, l.land_area_kha, l.cropland_kha, l.pastures_kha, l.forest_kha, l.agri_land_kha
FROM v_land l JOIN dim_area a USING (area_code)
WHERE l.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND l.year IN (1990, 2000, 2010, 2020, 2022, 2023)
ORDER BY a.area, l.year;
