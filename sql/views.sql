-- Analysis views: thin, named slices of the fact table so questions read as prose.

DROP VIEW IF EXISTS v_country;
CREATE VIEW v_country AS
SELECT area_code, area, iso3, region, subregion, is_ldc, is_lldc, is_sids
FROM dim_area WHERE is_aggregate = 0 AND region IS NOT NULL;

DROP VIEW IF EXISTS v_production;
CREATE VIEW v_production AS
SELECT o.area_code, a.area, a.region, a.subregion, a.is_aggregate, o.item_code, i.item, o.year,
       MAX(CASE WHEN o.element_code = 5312 THEN o.value END) AS area_harvested_ha,
       MAX(CASE WHEN o.element_code = 5412 THEN o.value END) AS yield_kg_ha,
       MAX(CASE WHEN o.element_code = 5510 THEN o.value END) AS production_t
FROM observation o
JOIN dim_area a USING (area_code)
JOIN dim_item i ON i.domain = o.domain AND i.item_code = o.item_code
WHERE o.domain = 'QCL' AND o.element_code IN (5312, 5412, 5510)
GROUP BY o.area_code, o.item_code, o.year;

DROP VIEW IF EXISTS v_population;
CREATE VIEW v_population AS
SELECT area_code, year,
       MAX(CASE WHEN element_code = 511 THEN value END) * 1000 AS population,
       MAX(CASE WHEN element_code = 551 THEN value END) * 1000 AS rural_population,
       MAX(CASE WHEN element_code = 561 THEN value END) * 1000 AS urban_population
FROM observation WHERE domain = 'OA' GROUP BY area_code, year;

DROP VIEW IF EXISTS v_food_security;
CREATE VIEW v_food_security AS
-- FAO publishes annual PoU / FIES only for regional aggregates; countries carry
-- 3-year averages (stored at the middle year). The *_pct columns therefore use
-- the 3-year averages so countries and regions are comparable; *_annual_pct
-- columns expose the annual aggregate series.
SELECT o.area_code, a.area, a.region, a.subregion, a.is_aggregate, o.year,
       MAX(CASE WHEN o.item_code = '210041' THEN o.value END) AS pou_pct,
       MAX(CASE WHEN o.item_code = '210011' THEN o.value END) AS undernourished_m,
       MAX(CASE WHEN o.item_code = '210040' THEN o.value END) AS pou_annual_pct,
       MAX(CASE WHEN o.item_code = '210010' THEN o.value END) AS undernourished_annual_m,
       MAX(CASE WHEN o.item_code = '21010'  THEN o.value END) AS des_adequacy_pct,
       MAX(CASE WHEN o.item_code = '22000'  THEN o.value END) AS des_kcal,
       MAX(CASE WHEN o.item_code = '21013'  THEN o.value END) AS protein_g,
       MAX(CASE WHEN o.item_code = '21014'  THEN o.value END) AS animal_protein_g,
       MAX(CASE WHEN o.item_code = '21012'  THEN o.value END) AS cereal_share_pct,
       MAX(CASE WHEN o.item_code = '210091' THEN o.value END) AS fies_mod_sev_pct,
       MAX(CASE WHEN o.item_code = '210091F' THEN o.value END) AS fies_mod_sev_f_pct,
       MAX(CASE WHEN o.item_code = '210091M' THEN o.value END) AS fies_mod_sev_m_pct,
       MAX(CASE WHEN o.item_code = '210401' THEN o.value END) AS fies_severe_pct,
       MAX(CASE WHEN o.item_code = '22013'  THEN o.value END) AS gdp_cap_ppp,
       MAX(CASE WHEN o.item_code = '21035'  THEN o.value END) AS cereal_import_dep_pct,
       MAX(CASE WHEN o.item_code = '21034'  THEN o.value END) AS irrigation_share_pct,
       MAX(CASE WHEN o.item_code = '21033'  THEN o.value END) AS food_import_share_pct,
       MAX(CASE WHEN o.item_code = '21025'  THEN o.value END) AS stunting_pct,
       MAX(CASE WHEN o.item_code = '21041'  THEN o.value END) AS overweight_u5_pct,
       MAX(CASE WHEN o.item_code = '21042'  THEN o.value END) AS obesity_pct,
       MAX(CASE WHEN o.item_code = '21043'  THEN o.value END) AS anemia_pct,
       MAX(CASE WHEN o.item_code = '21047'  THEN o.value END) AS water_basic_pct,
       MAX(CASE WHEN o.item_code = '21048'  THEN o.value END) AS sanitation_basic_pct,
       MAX(CASE WHEN o.item_code = '21031'  THEN o.value END) AS supply_variability_kcal
FROM observation o JOIN dim_area a USING (area_code)
WHERE o.domain = 'FS'
GROUP BY o.area_code, o.year;

DROP VIEW IF EXISTS v_land;
CREATE VIEW v_land AS
SELECT area_code, year,
       MAX(CASE WHEN item_code = '6601' THEN value END) AS land_area_kha,
       MAX(CASE WHEN item_code = '6610' THEN value END) AS agri_land_kha,
       MAX(CASE WHEN item_code = '6620' THEN value END) AS cropland_kha,
       MAX(CASE WHEN item_code = '6621' THEN value END) AS arable_kha,
       MAX(CASE WHEN item_code = '6650' THEN value END) AS perm_crops_kha,
       MAX(CASE WHEN item_code = '6655' THEN value END) AS pastures_kha,
       MAX(CASE WHEN item_code = '6646' THEN value END) AS forest_kha,
       MAX(CASE WHEN item_code = '6690' THEN value END) AS irrigated_equipped_kha,
       MAX(CASE WHEN item_code = '6671' THEN value END) AS organic_agri_kha
FROM observation WHERE domain = 'RL' AND element_code = 5110
GROUP BY area_code, year;

DROP VIEW IF EXISTS v_fertilizer;
CREATE VIEW v_fertilizer AS
SELECT area_code, year,
       MAX(CASE WHEN item_code = '3102' AND element_code = 5157 THEN value END) AS n_use_t,
       MAX(CASE WHEN item_code = '3103' AND element_code = 5157 THEN value END) AS p2o5_use_t,
       MAX(CASE WHEN item_code = '3104' AND element_code = 5157 THEN value END) AS k2o_use_t,
       MAX(CASE WHEN item_code = '3102' AND element_code = 5159 THEN value END) AS n_kg_per_ha,
       MAX(CASE WHEN item_code = '3103' AND element_code = 5159 THEN value END) AS p2o5_kg_per_ha,
       MAX(CASE WHEN item_code = '3104' AND element_code = 5159 THEN value END) AS k2o_kg_per_ha
FROM observation WHERE domain = 'RFN' GROUP BY area_code, year;

DROP VIEW IF EXISTS v_temperature;
CREATE VIEW v_temperature AS
SELECT area_code, year,
       MAX(CASE WHEN element_code = 7271 THEN value END) AS temp_change_c,
       MAX(CASE WHEN element_code = 6078 THEN value END) AS temp_change_sd
FROM observation WHERE domain = 'ET' AND item_code = '7020' GROUP BY area_code, year;

DROP VIEW IF EXISTS v_emissions;
CREATE VIEW v_emissions AS
SELECT area_code, year,
       MAX(CASE WHEN item_code = '6518' THEN value END) AS agrifood_kt_co2eq,
       MAX(CASE WHEN item_code = '6996' THEN value END) AS farm_gate_kt_co2eq,
       MAX(CASE WHEN item_code = '6516' THEN value END) AS land_use_change_kt_co2eq,
       MAX(CASE WHEN item_code = '6517' THEN value END) AS pre_post_kt_co2eq,
       MAX(CASE WHEN item_code = '6825' THEN value END) AS all_sectors_kt_co2eq,
       MAX(CASE WHEN item_code = '5058' THEN value END) AS enteric_kt_co2eq,
       MAX(CASE WHEN item_code = '5059' THEN value END) AS manure_mgmt_kt_co2eq,
       MAX(CASE WHEN item_code = '5060' THEN value END) AS rice_kt_co2eq,
       MAX(CASE WHEN item_code = '5061' THEN value END) AS synthetic_fert_kt_co2eq
FROM observation WHERE domain = 'GT' AND element_code = 723113 GROUP BY area_code, year;

DROP VIEW IF EXISTS v_healthy_diet;
CREATE VIEW v_healthy_diet AS
SELECT area_code, year,
       -- 70040 = country cost; 70043 = population-weighted average for aggregates
       MAX(CASE WHEN item_code IN ('70040', '70043') AND element_code = 6226 THEN value END) AS cohd_ppp_per_day,
       MAX(CASE WHEN item_code = '7005'  AND element_code = 6121 THEN value END) AS unaffordable_pct,
       MAX(CASE WHEN item_code = '7006'  AND element_code = 6132 THEN value END) AS unaffordable_m
FROM observation WHERE domain = 'CAHD' GROUP BY area_code, year;

DROP VIEW IF EXISTS v_price_usd;
CREATE VIEW v_price_usd AS
SELECT o.area_code, o.item_code, i.item, o.year, o.value AS usd_per_tonne
FROM observation o JOIN dim_item i ON i.domain = o.domain AND i.item_code = o.item_code
WHERE o.domain = 'PP' AND o.element_code = 5532;
