-- Q28 How have producer prices for wheat, maize and rice moved across countries since 1991?
SELECT item, year, usd_per_tonne, area_code FROM v_price_usd WHERE item_code IN ('15', '56', '27') AND usd_per_tonne > 0;
