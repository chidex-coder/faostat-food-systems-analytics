-- Q12 Does dietary energy supply adequacy explain child stunting?
WITH latest AS (
  SELECT area_code, MAX(year) AS y FROM v_food_security
  WHERE stunting_pct IS NOT NULL AND des_adequacy_pct IS NOT NULL GROUP BY area_code)
SELECT f.area, f.region, f.year, f.des_adequacy_pct, f.stunting_pct, f.sanitation_basic_pct, f.water_basic_pct
FROM v_food_security f JOIN latest l ON l.area_code = f.area_code AND l.y = f.year
WHERE f.is_aggregate = 0 AND f.region IS NOT NULL;
