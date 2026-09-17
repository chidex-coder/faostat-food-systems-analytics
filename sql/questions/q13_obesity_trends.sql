-- Q13 How is adult obesity trending by region, and how does it relate to income?
SELECT area AS region, year, obesity_pct
FROM v_food_security
WHERE area_code IN (5000, 5100, 5200, 5300, 5400, 5500) AND obesity_pct IS NOT NULL
ORDER BY area, year;
