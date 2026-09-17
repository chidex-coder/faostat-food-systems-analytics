-- Q33 How do least-developed, land-locked and small-island states compare with everyone else?
-- Each indicator is taken at its own latest available year per country.
WITH c AS (SELECT area_code, area, region, is_ldc, is_sids, is_lldc FROM v_country)
SELECT c.area, c.region,
       CASE WHEN c.is_ldc = 1 THEN 'Least developed' WHEN c.is_sids = 1 THEN 'Small island'
            WHEN c.is_lldc = 1 THEN 'Land-locked developing' ELSE 'Other' END AS grp,
  (SELECT pou_pct FROM v_food_security f WHERE f.area_code = c.area_code AND pou_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS pou_pct,
  (SELECT fies_mod_sev_pct FROM v_food_security f WHERE f.area_code = c.area_code AND fies_mod_sev_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS fies_mod_sev_pct,
  (SELECT cereal_import_dep_pct FROM v_food_security f WHERE f.area_code = c.area_code AND cereal_import_dep_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS cereal_import_dep_pct,
  (SELECT stunting_pct FROM v_food_security f WHERE f.area_code = c.area_code AND stunting_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS stunting_pct,
  (SELECT unaffordable_pct FROM v_healthy_diet h WHERE h.area_code = c.area_code AND unaffordable_pct IS NOT NULL ORDER BY year DESC LIMIT 1) AS unaffordable_pct,
  (SELECT yield_kg_ha / 1000.0 FROM v_production v WHERE v.area_code = c.area_code AND v.item_code = '1717' AND yield_kg_ha IS NOT NULL ORDER BY year DESC LIMIT 1) AS cereal_yield_t_ha
FROM c
WHERE pou_pct IS NOT NULL;
