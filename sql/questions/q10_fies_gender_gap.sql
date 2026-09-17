-- Q10 How large is the gender gap in moderate-or-severe food insecurity, by region?
SELECT area AS region, year, fies_mod_sev_f_pct, fies_mod_sev_m_pct,
       fies_mod_sev_f_pct - fies_mod_sev_m_pct AS gap_pp
FROM v_food_security
WHERE area_code IN (5000, 5100, 5200, 5300, 5400, 5500)
  AND fies_mod_sev_f_pct IS NOT NULL AND fies_mod_sev_m_pct IS NOT NULL
ORDER BY area, year;
