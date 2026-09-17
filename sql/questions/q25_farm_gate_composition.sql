-- Q25 What makes up farm-gate emissions globally and how has the mix changed?
SELECT year, enteric_kt_co2eq / 1e6 AS enteric_gt, manure_mgmt_kt_co2eq / 1e6 AS manure_gt,
       rice_kt_co2eq / 1e6 AS rice_gt, synthetic_fert_kt_co2eq / 1e6 AS synthetic_fert_gt,
       farm_gate_kt_co2eq / 1e6 AS farm_gate_gt
FROM v_emissions WHERE area_code = 5000 AND farm_gate_kt_co2eq IS NOT NULL ORDER BY year;
