-- Q02 Which countries produce the most cereals today and what share of the world total is that?
WITH latest AS (SELECT MAX(year) AS y FROM v_production WHERE area_code = 5000 AND item_code = '1717')
SELECT p.area, p.region, p.year,
       p.production_t / 1e6 AS production_mt,
       100.0 * p.production_t / w.production_t AS share_pct
FROM v_production p
JOIN latest ON p.year = latest.y
JOIN v_production w ON w.area_code = 5000 AND w.item_code = '1717' AND w.year = p.year
WHERE p.item_code = '1717' AND p.is_aggregate = 0 AND p.region IS NOT NULL
ORDER BY p.production_t DESC
LIMIT 15;
