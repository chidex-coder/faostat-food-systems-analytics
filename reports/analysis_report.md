# Analysis report

Each question is answered with SQL against `data/faostat.db`, summarised in prose and rendered as an interactive Plotly figure.

## Production

### Q01. How has world cereal production, harvested area and yield evolved since 1961?

- World cereal production rose from 877 Mt in 1961 to 3,133 Mt in 2024 (3.6x, 2.0 % a year).
- Harvested area grew only 15 % (648 -> 745 Mha); yield rose 211 % (1.35 -> 4.21 t/ha), so intensification, not expansion, fed the growth.

Figure: [figures/q01_global_cereal_production.html](figures/q01_global_cereal_production.html) · Table: [tables/q01_global_cereal_production.csv](tables/q01_global_cereal_production.csv) · SQL: [sql/questions/q01_global_cereal_production.sql](../sql/questions/q01_global_cereal_production.sql)

### Q02. Which countries produce the most cereals today and what share of the world total is that?

- China, mainland, United States of America, India produce 48 % of world cereals (1,497 Mt of the top-15 total 2,345 Mt).
- The 15 largest producers account for 75 % of global output; Asia contributes the most entries in the list.

Figure: [figures/q02_top_cereal_producers.html](figures/q02_top_cereal_producers.html) · Table: [tables/q02_top_cereal_producers.csv](tables/q02_top_cereal_producers.csv) · SQL: [sql/questions/q02_top_cereal_producers.sql](../sql/questions/q02_top_cereal_producers.sql)

### Q03. How do wheat, maize and rice yields compare across continents and how fast are they rising?

- Wheat: Europe leads at 4.2 t/ha while Oceania trails at 2.6 t/ha - a 1.6x gap in 2024.
- Maize (corn): Americas leads at 7.9 t/ha while Africa trails at 2.1 t/ha - a 3.8x gap in 2024.
- Rice: Oceania leads at 11.1 t/ha while Africa trails at 2.4 t/ha - a 4.7x gap in 2024.
- Since 1961 maize yields multiplied 5.1x in Asia but only 2.0x in Africa.

Figure: [figures/q03_staple_yields_by_region.html](figures/q03_staple_yields_by_region.html) · Table: [tables/q03_staple_yields_by_region.csv](tables/q03_staple_yields_by_region.csv) · SQL: [sql/questions/q03_staple_yields_by_region.sql](../sql/questions/q03_staple_yields_by_region.sql)

### Q04. Where is the maize yield gap largest? (2022-2024 average vs the top-decile yield)

- The top-decile maize yield among countries harvesting >= 100 kha is 9.1 t/ha; the median country reaches 3.5 t/ha.
- Closing the gap in just China, mainland, Brazil, India would add 252 Mt - the 20 largest gaps together represent 586 Mt of latent production.
- By region the median yield is Africa 1.7 t/ha, Americas 4.0 t/ha, Asia 5.5 t/ha, Europe 7.0 t/ha.

Figure: [figures/q04_maize_yield_gap.html](figures/q04_maize_yield_gap.html) · Table: [tables/q04_maize_yield_gap.csv](tables/q04_maize_yield_gap.csv) · SQL: [sql/questions/q04_maize_yield_gap.sql](../sql/questions/q04_maize_yield_gap.sql)

### Q05. Since 2000, how much of each region's cereal production growth came from yield versus area?

- Europe: production +24 %, of which yield explains 152 % and area -53 %.
- Oceania: production +52 %, of which yield explains 75 % and area 25 %.
- World: production +52 %, of which yield explains 76 % and area 24 %.
- Americas: production +54 %, of which yield explains 82 % and area 18 %.
- Asia: production +57 %, of which yield explains 82 % and area 18 %.
- Africa: production +100 %, of which yield explains 40 % and area 60 %.

Figure: [figures/q05_growth_decomposition.html](figures/q05_growth_decomposition.html) · Table: [tables/q05_growth_decomposition.csv](tables/q05_growth_decomposition.csv) · SQL: [sql/questions/q05_growth_decomposition.sql](../sql/questions/q05_growth_decomposition.sql)

### Q06. How has world meat production shifted between poultry, pig, bovine and sheep/goat meat?

- Total meat output grew from 68 Mt (1961) to 368 Mt (2024).
- Poultry's share rose from 13 % to 40 %; it overtook pig meat in 2016.
- Bovine meat's share fell from 42 % to 21 %.

Figure: [figures/q06_global_meat_production.html](figures/q06_global_meat_production.html) · Table: [tables/q06_global_meat_production.csv](tables/q06_global_meat_production.csv) · SQL: [sql/questions/q06_global_meat_production.sql](../sql/questions/q06_global_meat_production.sql)

### Q07. Which sizeable cereal producers have the most volatile output (2010-2024)?

- Morocco has the most volatile cereal output (39 % of its 7.0 Mt mean), followed by Syrian Arab Republic and Iraq.
- 8 of the 20 most volatile producers are African; the median de-trended CV across all 107 producers is 9.9 %.

Figure: [figures/q07_production_volatility.html](figures/q07_production_volatility.html) · Table: [tables/q07_production_volatility.csv](tables/q07_production_volatility.csv) · SQL: [sql/questions/q07_production_volatility.sql](../sql/questions/q07_production_volatility.sql)

### Q34. Which commodities have grown fastest in world production since 2000?

- Fastest growth: Mushrooms and truffles (+488 %), Oil palm fruit (+247 %), Spinach (+222 %).
- Largest absolute additions: Sugar cane +687 Mt, Maize (corn) +626 Mt, Raw milk of cattle +308 Mt, Oil palm fruit +298 Mt, Soya beans +236 Mt.

Figure: [figures/q34_fastest_growing_commodities.html](figures/q34_fastest_growing_commodities.html) · Table: [tables/q34_fastest_growing_commodities.csv](tables/q34_fastest_growing_commodities.csv) · SQL: [sql/questions/q34_fastest_growing_commodities.sql](../sql/questions/q34_fastest_growing_commodities.sql)

### Q35. How have global livestock herds (cattle, pigs, sheep, goats, chickens) changed since 1961?

- Head counts in 2024: Chickens 27,681 M, Cattle 1,579 M, Sheep 1,363 M, Goats 1,188 M, Swine / pigs 962 M.
- Chickens grew 7.1x since 1961, goats 3.4x, cattle 1.7x, sheep 1.4x.

Figure: [figures/q35_livestock_stocks.html](figures/q35_livestock_stocks.html) · Table: [tables/q35_livestock_stocks.csv](tables/q35_livestock_stocks.csv) · SQL: [sql/questions/q35_livestock_stocks.sql](../sql/questions/q35_livestock_stocks.sql)

## Food security

### Q08. How has the prevalence of undernourishment moved in each region since 2000?

- World undernourishment fell from 13.0 % (2001) to a low of 7.3 % in 2018, then rose to 8.1 % in 2024 - 663 million people.
- Latest regional rates: Africa 20.1 %, Oceania 8.2 %, Asia 6.5 %.
- Africa is the only region above 15 %: 20.1 % in 2024, up from its 15.7 % low in 2013.

Figure: [figures/q08_pou_by_region.html](figures/q08_pou_by_region.html) · Table: [tables/q08_pou_by_region.csv](tables/q08_pou_by_region.csv) · SQL: [sql/questions/q08_pou_by_region.sql](../sql/questions/q08_pou_by_region.sql)

### Q09. Which countries have the highest undernourishment now, and where has it changed most since 2010?

- Somalia (56 %), Haiti (51 %) and Madagascar (42 %) have the highest undernourishment in 2024.
- Biggest improvement since 2010: Tajikistan (-16 pp to 8 %). Biggest deterioration: Syrian Arab Republic (+35 pp to 41 %).
- 53 of 97 countries improved; 17 worsened by more than 5 pp.

Figure: [figures/q09_pou_change_countries.html](figures/q09_pou_change_countries.html) · Table: [tables/q09_pou_change_countries.csv](tables/q09_pou_change_countries.csv) · SQL: [sql/questions/q09_pou_change_countries.sql](../sql/questions/q09_pou_change_countries.sql)

### Q10. How large is the gender gap in moderate-or-severe food insecurity, by region?

- Globally 24.7 % of women vs 23.5 % of men were moderately or severely food insecure in 2024 - a gap of +1.2 pp.
- Largest gaps: Africa +1.2 pp, Europe +0.7 pp, Asia +0.7 pp.
- The world gap peaked at +2.6 pp in 2021 (pandemic years).

Figure: [figures/q10_fies_gender_gap.html](figures/q10_fies_gender_gap.html) · Table: [tables/q10_fies_gender_gap.csv](tables/q10_fies_gender_gap.csv) · SQL: [sql/questions/q10_fies_gender_gap.sql](../sql/questions/q10_fies_gender_gap.sql)

### Q11. How strongly is national income associated with undernourishment?

- Across 130 countries the log-log correlation between income and undernourishment is r = -0.73; each doubling of income is associated with a 39 % lower PoU.
- Countries above Int$ 30,000 per head have a maximum PoU of 10.4 % (2.5 % is FAO's reporting floor); below Int$ 3,000 the median PoU is 26 %.
- Worst performers for their income level: Trinidad and Tobago, Botswana, Gabon; best: Kiribati, Uzbekistan, Bosnia and Herzegovina.

Figure: [figures/q11_income_vs_pou.html](figures/q11_income_vs_pou.html) · Table: [tables/q11_income_vs_pou.csv](tables/q11_income_vs_pou.csv) · SQL: [sql/questions/q11_income_vs_pou.sql](../sql/questions/q11_income_vs_pou.sql)

### Q12. Does dietary energy supply adequacy explain child stunting?

- Energy adequacy alone explains stunting only moderately (r = -0.57, n = 136); 14 countries with >= 120 % adequacy still have stunting above 20 %.
- Basic sanitation coverage correlates more strongly with stunting (r = -0.73) - calories are necessary but not sufficient.
- Highest stunting: Niger 48 %, Angola 48 %, Papua New Guinea 48 %.

Figure: [figures/q12_stunting_vs_supply.html](figures/q12_stunting_vs_supply.html) · Table: [tables/q12_stunting_vs_supply.csv](tables/q12_stunting_vs_supply.csv) · SQL: [sql/questions/q12_stunting_vs_supply.sql](../sql/questions/q12_stunting_vs_supply.sql)

### Q13. How is adult obesity trending by region, and how does it relate to income?

- World adult obesity rose from 8.7 % in 2000 to 16.2 % in 2024 - it has never fallen in a single year.
- Latest: Oceania 31.2 %, Europe 19.6 %, Africa 16.6 %, Asia 11.2 %.
- Fastest-rising region: Oceania.

Figure: [figures/q13_obesity_trends.html](figures/q13_obesity_trends.html) · Table: [tables/q13_obesity_trends.csv](tables/q13_obesity_trends.csv) · SQL: [sql/questions/q13_obesity_trends.sql](../sql/questions/q13_obesity_trends.sql)

### Q14. Which countries depend most on imported cereals?

- 20 countries import essentially all (>= 99 %) of the cereals they consume, led by Djibouti, China, Hong Kong SAR, Jordan.
- 81 countries import at least half their cereals; 34 are net exporters (negative ratio).
- Regionally the median dependency is Oceania 96 %, Americas 58 %, Asia 48 %, Africa 43 %, Europe 20 %.

Figure: [figures/q14_cereal_import_dependency.html](figures/q14_cereal_import_dependency.html) · Table: [tables/q14_cereal_import_dependency.csv](tables/q14_cereal_import_dependency.csv) · SQL: [sql/questions/q14_cereal_import_dependency.sql](../sql/questions/q14_cereal_import_dependency.sql)

### Q15. What does a healthy diet cost and who cannot afford it?

- A healthy diet cost 4.28 PPP$ per person per day in 2025, up from 2.94 in 2017.
- 32.7 % of the world's people (2,692 million) could not afford it in 2025, down from 41.0 % in 2017.
- Worst affected: South Sudan 94 %, Malawi 93 %, Mozambique 91 %.

Figure: [figures/q15_healthy_diet_affordability.html](figures/q15_healthy_diet_affordability.html) · Table: [tables/q15_healthy_diet_affordability.csv](tables/q15_healthy_diet_affordability.csv) · SQL: [sql/questions/q15_healthy_diet_affordability.sql](../sql/questions/q15_healthy_diet_affordability.sql)

## Inputs & land

### Q16. How has nitrogen fertilizer use per hectare of cropland evolved by region?

- World nitrogen use is 71 kg N/ha of cropland (115 Mt N in 2024), 8.3x the 1961 level.
- Latest intensity: Asia 112, Oceania 93, Americas 71, Europe 50, Africa 15 kg N/ha.
- Africa applies 7x less nitrogen per hectare than Asia.

Figure: [figures/q16_nitrogen_by_region.html](figures/q16_nitrogen_by_region.html) · Table: [tables/q16_nitrogen_by_region.csv](tables/q16_nitrogen_by_region.csv) · SQL: [sql/questions/q16_nitrogen_by_region.sql](../sql/questions/q16_nitrogen_by_region.sql)

### Q17. How does nitrogen intensity relate to cereal yield across countries?

- Across 138 countries yield scales with nitrogen intensity at r = 0.69; a doubling of N/ha is associated with 24 % higher cereal yields.
- Diminishing returns are visible: countries above 150 kg N/ha average 5.6 t/ha vs 4.7 t/ha for 50-150 kg.
- Most nitrogen-efficient large producers (>= 1 Mha cereals, yield furthest above the fit): South Sudan, United States of America, Democratic People's Republic of Korea.

Figure: [figures/q17_fertilizer_vs_yield.html](figures/q17_fertilizer_vs_yield.html) · Table: [tables/q17_fertilizer_vs_yield.csv](tables/q17_fertilizer_vs_yield.csv) · SQL: [sql/questions/q17_fertilizer_vs_yield.sql](../sql/questions/q17_fertilizer_vs_yield.sql)

### Q18. How is land used in each region, and how has cropland / pasture / forest changed since 1990?

- Cropland covers 12 % of the world's land, pastures 24 % and forest 32 %.
- Since 1990 forest area fell 193 Mha globally (-4.5 %); Africa -14.3 %, Americas -9.2 %, Europe +2.5 %, Asia +10.5 %.
- Cropland expanded most in Africa (+52 %) and contracted in Europe (-22 %).

Figure: [figures/q18_land_use_by_region.html](figures/q18_land_use_by_region.html) · Table: [tables/q18_land_use_by_region.csv](tables/q18_land_use_by_region.csv) · SQL: [sql/questions/q18_land_use_by_region.sql](../sql/questions/q18_land_use_by_region.sql)

### Q19. Is a higher share of irrigated arable land associated with higher cereal yields?

- Irrigation share and cereal yield correlate at r = 0.39 across 141 countries; each additional 10 pp of irrigated arable land is associated with +0.28 t/ha.
- Countries with under 5 % irrigated arable land average 2.5 t/ha; those above 40 % average 4.6 t/ha.
- Rain-fed high performers (< 10 % irrigated, > 6 t/ha): Germany, Croatia, Slovenia, United Kingdom of Great Britain and Northern Ireland, Belgium.
- Data note: FAOSTAT's food-security indicator 21034 reports Egypt at 4 % 'of arable land', i.e. it is effectively expressed against total land area; the ratio here is rebuilt from the land-use domain (RL 6690 / (6621 + 6650)).

Figure: [figures/q19_irrigation_vs_yield.html](figures/q19_irrigation_vs_yield.html) · Table: [tables/q19_irrigation_vs_yield.csv](tables/q19_irrigation_vs_yield.csv) · SQL: [sql/questions/q19_irrigation_vs_yield.sql](../sql/questions/q19_irrigation_vs_yield.sql)

### Q20. How fast is organically farmed agricultural area growing?

- Organic farming covers 99 Mha worldwide (2.13 % of agricultural land) in 2024, 4.5x the 2004 area.
- Regional shares: Oceania 14.16 %, Europe 4.26 %, Americas 1.33 %, Asia 0.59 %, Africa 0.24 %.

Figure: [figures/q20_organic_agriculture.html](figures/q20_organic_agriculture.html) · Table: [tables/q20_organic_agriculture.csv](tables/q20_organic_agriculture.csv) · SQL: [sql/questions/q20_organic_agriculture.sql](../sql/questions/q20_organic_agriculture.sql)

## Climate & emissions

### Q21. How much has land surface temperature changed in each region (vs the 1951-1980 baseline)?

- World land temperature in the last five years averaged +1.72 °C above the 1951-1980 baseline; the single warmest year was 2024 at +2.11 °C.
- Five-year mean by region: Europe +2.27 °C, Asia +1.80 °C, Americas +1.75 °C, Africa +1.37 °C, Oceania +1.03 °C.
- Europe has warmed fastest; Oceania least. The 1960s world average was -0.02 °C.

Figure: [figures/q21_temperature_by_region.html](figures/q21_temperature_by_region.html) · Table: [tables/q21_temperature_by_region.csv](tables/q21_temperature_by_region.csv) · SQL: [sql/questions/q21_temperature_by_region.sql](../sql/questions/q21_temperature_by_region.sql)

### Q22. How large are agrifood-system emissions by region, and what share of all emissions are they?

- Global agrifood systems emitted 16.5 Gt CO2eq in 2023 - 32 % of all anthropogenic emissions - split into farm gate 8.1 Gt, land-use change 3.2 Gt and pre/post-production 5.2 Gt.
- Since 1990 agrifood emissions rose 12 % while their share of the total fell from 43 % to 32 % as energy emissions grew faster.
- Latest by region: Asia 7.10 Gt, Americas 4.82 Gt, Africa 2.38 Gt, Europe 1.87 Gt, Oceania 0.37 Gt.

Figure: [figures/q22_agrifood_emissions_by_region.html](figures/q22_agrifood_emissions_by_region.html) · Table: [tables/q22_agrifood_emissions_by_region.csv](tables/q22_agrifood_emissions_by_region.csv) · SQL: [sql/questions/q22_agrifood_emissions_by_region.sql](../sql/questions/q22_agrifood_emissions_by_region.sql)

### Q23. Which countries have the highest agrifood emissions per person, and how does that relate to income?

- Mongolia (17.5 t), Trinidad and Tobago (14.0 t) and Central African Republic (11.0 t) have the highest agrifood emissions per person - land-use change and cattle dominate.
- The population-weighted world average is 2.04 t per person; the median country is 1.92 t.
- Per-capita agrifood emissions are only weakly tied to income (log-log r = 0.31) - unlike energy emissions, they follow land and livestock.

Figure: [figures/q23_emissions_per_capita.html](figures/q23_emissions_per_capita.html) · Table: [tables/q23_emissions_per_capita.csv](tables/q23_emissions_per_capita.csv) · SQL: [sql/questions/q23_emissions_per_capita.sql](../sql/questions/q23_emissions_per_capita.sql)

### Q24. Do hotter-than-usual years coincide with below-trend wheat yields?

- In 68 % of the 53 major wheat producers, hotter-than-usual years coincide with below-trend yields (negative r); the median correlation is -0.09.
- Most heat-sensitive: Mongolia (r = -0.36), Republic of Moldova (r = -0.35), Italy (r = -0.30).
- Heat-tolerant or cold-limited systems where warm years help: Kyrgyzstan (r = +0.26), Turkmenistan (r = +0.28), Sweden (r = +0.35).

Figure: [figures/q24_temperature_vs_wheat_yield.html](figures/q24_temperature_vs_wheat_yield.html) · Table: [tables/q24_temperature_vs_wheat_yield.csv](tables/q24_temperature_vs_wheat_yield.csv) · SQL: [sql/questions/q24_temperature_vs_wheat_yield.sql](../sql/questions/q24_temperature_vs_wheat_yield.sql)

### Q25. What makes up farm-gate emissions globally and how has the mix changed?

- Farm-gate emissions reached 8.10 Gt CO2eq in 2023: enteric fermentation 36 %, manure 5 %, synthetic fertilizers 8 %, rice 9 %.
- Synthetic-fertilizer emissions grew fastest since 1990 (1.4x) versus 1.2x for enteric fermentation.

Figure: [figures/q25_farm_gate_composition.html](figures/q25_farm_gate_composition.html) · Table: [tables/q25_farm_gate_composition.csv](tables/q25_farm_gate_composition.csv) · SQL: [sql/questions/q25_farm_gate_composition.sql](../sql/questions/q25_farm_gate_composition.sql)

## People & prices

### Q26. Is cereal production keeping up with population? Per-capita output by region.

- World cereal output per person rose from 286 kg in 1961 to 384 kg in 2024 even as population grew from 3.1 to 8.2 billion.
- Latest by region: Oceania 1161 kg, Americas 779 kg, Europe 639 kg, Asia 325 kg, Africa 147 kg.
- Africa's per-capita output (147 kg) is 5.3x below the Americas'.

Figure: [figures/q26_per_capita_cereal.html](figures/q26_per_capita_cereal.html) · Table: [tables/q26_per_capita_cereal.csv](tables/q26_per_capita_cereal.csv) · SQL: [sql/questions/q26_per_capita_cereal.sql](../sql/questions/q26_per_capita_cereal.sql)

### Q27. How is urbanisation changing, and how much agricultural land is left per person?

- The urban share of the world population rose from 34 % (1961) to 58 % (2024).
- Agricultural land per person fell from 1.47 ha to 0.57 ha over the same period (-61 %).

Figure: [figures/q27_urbanisation_and_land.html](figures/q27_urbanisation_and_land.html) · Table: [tables/q27_urbanisation_and_land.csv](tables/q27_urbanisation_and_land.csv) · SQL: [sql/questions/q27_urbanisation_and_land.sql](../sql/questions/q27_urbanisation_and_land.sql)

### Q28. How have producer prices for wheat, maize and rice moved across countries since 1991?

- Maize (corn): median producer price 289 USD/t in 2024, peak 342 USD/t in 2022; +17 % vs 2019.
- Rice: median producer price 458 USD/t in 2024, peak 500 USD/t in 2023; +24 % vs 2019.
- Wheat: median producer price 244 USD/t in 2024, peak 341 USD/t in 2022; +14 % vs 2019.

Figure: [figures/q28_staple_price_trends.html](figures/q28_staple_price_trends.html) · Table: [tables/q28_staple_price_trends.csv](tables/q28_staple_price_trends.csv) · SQL: [sql/questions/q28_staple_price_trends.sql](../sql/questions/q28_staple_price_trends.sql)

### Q29. How dispersed are producer prices for staples across countries in the latest year?

- The 90th/10th percentile price ratio across countries is widest for Maize (5.1x) and narrowest for Cow milk (1.8x).
- Median prices: Wheat 244, Maize 289, Rice 458, Soya beans 487, Potatoes 506, Cow milk 529, Hen eggs 2,194 USD/t.

Figure: [figures/q29_price_dispersion.html](figures/q29_price_dispersion.html) · Table: [tables/q29_price_dispersion.csv](tables/q29_price_dispersion.csv) · SQL: [sql/questions/q29_price_dispersion.sql](../sql/questions/q29_price_dispersion.sql)

### Q30. Where has cereal production growth lagged population growth since 2010?

- In 68 of 136 countries cereal output grew slower than population between 2010 and 2024 (points below the diagonal).
- Largest shortfalls: Somalia (-119 pp), Yemen (-110 pp), Gambia (-109 pp), Zambia (-96 pp), Namibia (-92 pp).
- 41 African countries are in the sample; 23 of them fell behind population growth.

Figure: [figures/q30_production_vs_population_growth.html](figures/q30_production_vs_population_growth.html) · Table: [tables/q30_production_vs_population_growth.csv](tables/q30_production_vs_population_growth.csv) · SQL: [sql/questions/q30_production_vs_population_growth.sql](../sql/questions/q30_production_vs_population_growth.sql)

## Composite & governance

### Q31. A composite food-system scorecard: which countries combine adequate supply, low insecurity and low emissions intensity?

- Composite score across 8 indicators (n = 133 countries with >= 6): strongest Republic of Korea, Bulgaria, Serbia; weakest Democratic Republic of the Congo, Somalia, Central African Republic.
- Median score by region: Europe +0.53, Asia +0.20, Americas +0.05, Africa -0.28, Oceania -0.35.
- Least-developed countries score -0.31 on median versus +0.16 for the rest.

Figure: [figures/q31_food_system_scorecard.html](figures/q31_food_system_scorecard.html) · Table: [tables/q31_food_system_scorecard.csv](tables/q31_food_system_scorecard.csv) · SQL: [sql/questions/q31_food_system_scorecard.sql](../sql/questions/q31_food_system_scorecard.sql)

### Q32. How much of each domain is official data versus estimated, imputed or externally sourced?

- Across all 7,333,827 loaded observations, 31 % carry the official flag, 57 % are FAO estimates, 7 % imputed and 4 % come from external organisations (UN population, WHO, World Bank).
- Only the production domain (QCL) is majority official (45 %); temperature, emissions and healthy-diet indicators are 100 % modelled estimates by construction.
- Analyses that lean on FS, RL and RFN should be read as FAO's best estimate rather than reported statistics.

Figure: [figures/q32_data_provenance.html](figures/q32_data_provenance.html) · Table: [tables/q32_data_provenance.csv](tables/q32_data_provenance.csv) · SQL: [sql/questions/q32_data_provenance.sql](../sql/questions/q32_data_provenance.sql)

### Q33. How do least-developed, land-locked and small-island states compare with everyone else?

- Least-developed countries (n = 39) have median undernourishment of 18 % vs 5 % elsewhere, and 66 % cannot afford a healthy diet.
- Median cereal import dependency: Small island 93 %, Other 46 %, Land-locked developing 34 %, Least developed 25 % (n: LDC 39, LLDC 15, SIDS 20).
- Cereal yields: LDC median 1.6 t/ha vs 3.7 t/ha for other countries.

Figure: [figures/q33_vulnerable_groups.html](figures/q33_vulnerable_groups.html) · Table: [tables/q33_vulnerable_groups.csv](tables/q33_vulnerable_groups.csv) · SQL: [sql/questions/q33_vulnerable_groups.sql](../sql/questions/q33_vulnerable_groups.sql)
