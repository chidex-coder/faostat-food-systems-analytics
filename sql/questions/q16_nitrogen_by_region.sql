-- Q16 How has nitrogen fertilizer use per hectare of cropland evolved by region?
SELECT a.area AS region, f.year, f.n_kg_per_ha, f.p2o5_kg_per_ha, f.k2o_kg_per_ha, f.n_use_t / 1e6 AS n_use_mt
FROM v_fertilizer f JOIN dim_area a USING (area_code)
WHERE f.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND f.n_kg_per_ha IS NOT NULL
ORDER BY a.area, f.year;
