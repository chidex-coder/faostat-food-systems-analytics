-- Q09 Which countries have the highest undernourishment now, and where has it changed most since 2010?
SELECT area, region, year, pou_pct, undernourished_m
FROM v_food_security
WHERE is_aggregate = 0 AND region IS NOT NULL AND pou_pct IS NOT NULL AND year >= 2010;
