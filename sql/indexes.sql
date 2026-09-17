CREATE INDEX IF NOT EXISTS ix_obs_domain_item_elem_year ON observation (domain, item_code, element_code, year);
CREATE INDEX IF NOT EXISTS ix_obs_area_year ON observation (area_code, year);
CREATE INDEX IF NOT EXISTS ix_area_region ON dim_area (region, subregion);
ANALYZE;
