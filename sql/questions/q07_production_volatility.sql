-- Q07 Which sizeable cereal producers have the most volatile output (2010-2024)?
SELECT area, region, year, production_t
FROM v_production
WHERE item_code = '1717' AND is_aggregate = 0 AND region IS NOT NULL AND year BETWEEN 2010 AND 2024;
