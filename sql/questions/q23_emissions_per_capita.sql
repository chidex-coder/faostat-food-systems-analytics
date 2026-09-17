-- Q23 Which countries have the highest agrifood emissions per person, and how does that relate to income?
WITH latest AS (SELECT MAX(year) AS y FROM v_emissions WHERE agrifood_kt_co2eq IS NOT NULL)
SELECT a.area, a.region, e.year,
       e.agrifood_kt_co2eq * 1000.0 / p.population AS agrifood_t_per_cap,
       e.farm_gate_kt_co2eq * 1000.0 / p.population AS farm_gate_t_per_cap,
       p.population / 1e6 AS population_m, f.gdp_cap_ppp
FROM v_emissions e JOIN latest ON e.year = latest.y
JOIN dim_area a USING (area_code)
JOIN v_population p ON p.area_code = e.area_code AND p.year = e.year
LEFT JOIN v_food_security f ON f.area_code = e.area_code AND f.year = e.year
WHERE a.is_aggregate = 0 AND a.region IS NOT NULL AND p.population > 1e6;
