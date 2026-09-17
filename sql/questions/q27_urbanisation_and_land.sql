-- Q27 How is urbanisation changing, and how much agricultural land is left per person?
SELECT a.area AS region, p.year, 100.0 * p.urban_population / p.population AS urban_share_pct,
       l.agri_land_kha * 1000.0 / p.population AS agri_ha_per_capita
FROM v_population p JOIN dim_area a USING (area_code)
LEFT JOIN v_land l ON l.area_code = p.area_code AND l.year = p.year
WHERE p.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND p.urban_population IS NOT NULL
ORDER BY a.area, p.year;
