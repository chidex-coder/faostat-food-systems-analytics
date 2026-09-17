-- Q31 A composite food-system scorecard: which countries combine adequate supply, low insecurity and low emissions intensity?
-- Each indicator is taken at its own latest available year per country (they are published on different lags).
WITH c AS (SELECT area_code, area, region, is_ldc, is_sids, is_lldc FROM v_country)
SELECT c.area, c.region, c.is_ldc, c.is_sids, c.is_lldc,
  (SELECT pou_pct FROM v_food_security f WHERE f.area_code = c.area_code AND pou_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS pou_pct,
  (SELECT des_adequacy_pct FROM v_food_security f WHERE f.area_code = c.area_code AND des_adequacy_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS des_adequacy_pct,
  (SELECT stunting_pct FROM v_food_security f WHERE f.area_code = c.area_code AND stunting_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS stunting_pct,
  (SELECT obesity_pct FROM v_food_security f WHERE f.area_code = c.area_code AND obesity_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS obesity_pct,
  (SELECT cereal_import_dep_pct FROM v_food_security f WHERE f.area_code = c.area_code AND cereal_import_dep_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS cereal_import_dep_pct,
  (SELECT yield_kg_ha / 1000.0 FROM v_production v WHERE v.area_code = c.area_code AND v.item_code = '1717' AND yield_kg_ha IS NOT NULL ORDER BY year DESC LIMIT 1) AS cereal_yield_t_ha,
  (SELECT e.agrifood_kt_co2eq * 1000.0 / p.population FROM v_emissions e JOIN v_population p ON p.area_code = e.area_code AND p.year = e.year
     WHERE e.area_code = c.area_code AND e.agrifood_kt_co2eq IS NOT NULL ORDER BY e.year DESC LIMIT 1) AS agrifood_t_per_cap,
  (SELECT unaffordable_pct FROM v_healthy_diet h WHERE h.area_code = c.area_code AND unaffordable_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS unaffordable_pct,
  (SELECT temp_change_c FROM v_temperature t WHERE t.area_code = c.area_code AND temp_change_c IS NOT NULL ORDER BY year DESC LIMIT 1) AS temp_change_c
FROM c
WHERE pou_pct IS NOT NULL;
