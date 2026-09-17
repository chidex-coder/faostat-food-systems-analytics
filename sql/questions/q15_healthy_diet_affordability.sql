-- Q15 What does a healthy diet cost and who cannot afford it?
SELECT h.area_code, a.area, a.region, a.is_aggregate, h.year, h.cohd_ppp_per_day, h.unaffordable_pct, h.unaffordable_m
FROM v_healthy_diet h JOIN dim_area a USING (area_code)
WHERE (a.is_aggregate = 0 AND a.region IS NOT NULL) OR h.area_code IN (5000, 5100, 5200, 5300, 5400, 5500)
ORDER BY h.year, h.unaffordable_pct DESC;
