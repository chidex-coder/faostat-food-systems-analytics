-- Q19 Is a higher share of irrigated arable land associated with higher cereal yields?
-- The FS indicator 21034 ("percent of arable land equipped for irrigation") is published
-- relative to *total land area* (Egypt = 4 %), so the ratio is rebuilt from the land-use
-- domain: land equipped for irrigation / (arable land + permanent crops).
WITH latest AS (
  SELECT area_code, MAX(year) AS y FROM v_land WHERE irrigated_equipped_kha IS NOT NULL AND arable_kha IS NOT NULL GROUP BY area_code)
SELECT a.area, a.region, l.year,
       100.0 * l.irrigated_equipped_kha / (l.arable_kha + COALESCE(l.perm_crops_kha, 0)) AS irrigation_share_pct,
       p.yield_kg_ha / 1000.0 AS cereal_yield_t_ha, p.area_harvested_ha
FROM v_land l JOIN latest ON latest.area_code = l.area_code AND latest.y = l.year
JOIN dim_area a ON a.area_code = l.area_code
JOIN v_production p ON p.area_code = l.area_code AND p.year = l.year AND p.item_code = '1717'
WHERE a.is_aggregate = 0 AND a.region IS NOT NULL AND p.area_harvested_ha >= 50000 AND l.arable_kha > 0;
