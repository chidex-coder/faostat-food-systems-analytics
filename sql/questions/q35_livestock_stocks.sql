-- Q35 How have global livestock herds (cattle, pigs, sheep, goats, chickens) changed since 1961?
SELECT i.item, o.year, o.element_code, o.value
FROM observation o JOIN dim_item i ON i.domain = o.domain AND i.item_code = o.item_code
WHERE o.domain = 'QCL' AND o.area_code = 5000 AND o.element_code IN (5111, 5112)
  AND o.item_code IN ('866', '1034', '976', '1016', '1057')
ORDER BY i.item, o.year;
