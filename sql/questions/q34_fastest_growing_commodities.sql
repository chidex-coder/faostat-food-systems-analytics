-- Q34 Which commodities have grown fastest in world production since 2000?
-- Item codes >= 1700 are FAOSTAT commodity groups (Cereals primary, Milk total, ...) and are excluded.
SELECT i.item, o.year, o.value / 1e6 AS production_mt
FROM observation o JOIN dim_item i ON i.domain = o.domain AND i.item_code = o.item_code
WHERE o.domain = 'QCL' AND o.area_code = 5000 AND o.element_code = 5510 AND o.year IN (2000, 2024)
  AND CAST(o.item_code AS INTEGER) < 1700
ORDER BY i.item, o.year;
