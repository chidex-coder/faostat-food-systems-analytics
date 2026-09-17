-- Q22 How large are agrifood-system emissions by region, and what share of all emissions are they?
SELECT a.area AS region, e.year, e.agrifood_kt_co2eq / 1e6 AS agrifood_gt,
       e.farm_gate_kt_co2eq / 1e6 AS farm_gate_gt, e.land_use_change_kt_co2eq / 1e6 AS luc_gt,
       e.pre_post_kt_co2eq / 1e6 AS pre_post_gt,
       100.0 * e.agrifood_kt_co2eq / e.all_sectors_kt_co2eq AS agrifood_share_pct
FROM v_emissions e JOIN dim_area a USING (area_code)
WHERE e.area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND e.agrifood_kt_co2eq IS NOT NULL
ORDER BY a.area, e.year;
