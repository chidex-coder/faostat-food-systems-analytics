-- Q29 How dispersed are producer prices for staples across countries in the latest year?
WITH latest AS (SELECT item_code, MAX(year) AS y FROM v_price_usd GROUP BY item_code)
SELECT p.item, a.area, a.region, p.year, p.usd_per_tonne
FROM v_price_usd p JOIN latest l ON l.item_code = p.item_code AND l.y = p.year
JOIN dim_area a USING (area_code)
WHERE p.item_code IN ('15', '56', '27', '116', '236', '882', '1062') AND p.usd_per_tonne > 0 AND a.region IS NOT NULL;
