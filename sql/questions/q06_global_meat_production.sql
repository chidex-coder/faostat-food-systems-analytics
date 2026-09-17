-- Q06 How has world meat production shifted between poultry, pig, bovine and sheep/goat meat?
SELECT i.item, o.year, o.value / 1e6 AS production_mt
FROM observation o JOIN dim_item i ON i.domain = o.domain AND i.item_code = o.item_code
WHERE o.domain = 'QCL' AND o.area_code = 5000 AND o.element_code = 5510
  AND o.item_code IN ('1806', '1808', '1035', '1807')
ORDER BY i.item, o.year;
