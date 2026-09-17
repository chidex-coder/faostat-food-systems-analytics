"""Central configuration: paths, the domain registry and the analysis window.

Every other module imports from here so that a change to a domain (adding one,
dropping an element, moving the analysis window) is made in exactly one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
REFERENCE_DIR = DATA_DIR / "reference"
DB_PATH = DATA_DIR / "faostat.db"
SQL_DIR = ROOT / "sql"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = ROOT / "models"
DOCS_DIR = ROOT / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"

# FAOSTAT publishes every domain as a zipped "normalized" (long-format) CSV on a
# public bucket. The REST API (faostatservices.fao.org/api/v1) requires a personal
# bearer token since 2026; the pipeline can use it when FAOSTAT_TOKEN is set, but
# the bulk files are the primary, token-free path.
BULK_BASE_URL = "https://bulks-faostat.fao.org/production/"
BULK_CATALOGUE_URL = BULK_BASE_URL + "datasets_E.json"
API_BASE_URL = "https://faostatservices.fao.org/api/v1/en/"

# Analysis window. FAOSTAT population carries projections to 2100 and the
# emissions domain carries 2030/2050 scenarios; we keep observed years only.
YEAR_MIN = 1961
YEAR_MAX = 2025


@dataclass(frozen=True)
class Domain:
    code: str                      # FAOSTAT domain code (QCL, FS, ...)
    name: str
    zip_name: str                  # file name on the bulk bucket
    elements: tuple[int, ...] = () # keep only these element codes ("" = all)
    item_col: str = "Item"         # ET uses "Months" instead of "Item"
    extra_filters: dict = field(default_factory=dict)
    notes: str = ""


DOMAINS: dict[str, Domain] = {
    "QCL": Domain(
        "QCL", "Production: Crops and livestock products",
        "Production_Crops_Livestock_E_All_Data_(Normalized).zip",
        elements=(5312, 5412, 5510, 5111, 5112, 5320, 5321, 5417, 5424, 5318, 5313, 5413, 5513, 5114),
        notes="Area harvested (ha), yield (kg/ha), production (t), stocks, slaughtered.",
    ),
    "FS": Domain(
        "FS", "Food Security and Nutrition: Suite of Food Security Indicators",
        "Food_Security_Data_E_All_Data_(Normalized).zip",
        elements=(6121, 6123, 6124, 6126, 6128, 6132, 6173),
        notes="Point estimates only; confidence-interval elements are dropped.",
    ),
    "RFN": Domain(
        "RFN", "Land, Inputs and Sustainability: Fertilizers by Nutrient",
        "Inputs_FertilizersNutrient_E_All_Data_(Normalized).zip",
        elements=(5157, 5159, 5172, 5173, 5510, 5610, 5910),
    ),
    "RL": Domain(
        "RL", "Land, Inputs and Sustainability: Land Use",
        "Inputs_LandUse_E_All_Data_(Normalized).zip",
        elements=(5110, 7208, 7209, 7210, 7252, 7277, 7278, 72151),
    ),
    "ET": Domain(
        "ET", "Land, Inputs and Sustainability: Temperature change on land",
        "Environment_Temperature_change_E_All_Data_(Normalized).zip",
        elements=(7271, 6078),
        item_col="Months",
        notes="Item dimension is the month/season; 7020 = meteorological year.",
    ),
    "GT": Domain(
        "GT", "Climate Change: Agrifood systems emissions totals",
        "Emissions_Totals_E_All_Data_(Normalized).zip",
        elements=(723113, 7225, 7230, 7273),
        extra_filters={"Source Code": 3050},   # FAO TIER 1 only, not UNFCCC submissions
        notes="CO2eq (AR5 GWP) plus the three gases; 2030/2050 scenario rows dropped by the year window.",
    ),
    "OA": Domain(
        "OA", "Population and Employment: Annual population",
        "Population_E_All_Data_(Normalized).zip",
        elements=(511, 512, 513, 551, 561),
        notes="UN WPP estimates; projections beyond the window are dropped.",
    ),
    "PP": Domain(
        "PP", "Prices: Producer Prices",
        "Prices_E_All_Data_(Normalized).zip",
        elements=(5532, 5530),
        extra_filters={"Months Code": 7021},   # annual values only
        notes="USD/tonne and LCU/tonne annual producer prices.",
    ),
    "CAHD": Domain(
        "CAHD", "Cost and Affordability of a Healthy Diet",
        "Cost_Affordability_Healthy_Diet_(CoAHD)_E_All_Data_(Normalized).zip",
        elements=(6121, 6132, 6226),
        notes="CoHD in PPP dollars, prevalence and number unable to afford.",
    ),
}

# FAOSTAT area codes >= 5000 are regional / special aggregates (World = 5000).
AGGREGATE_AREA_CODE_MIN = 5000
WORLD_AREA_CODE = 5000

# Flag semantics differ slightly between domains but these letters mean
# "no value" everywhere they occur and are counted, not loaded.
MISSING_FLAGS = {"O", "Q", "L", "M"}

# Curated item codes used repeatedly in analysis and the dashboard.
ITEMS = {
    "cereals_primary": 1717,
    "wheat": 15,
    "rice": 27,
    "maize": 56,
    "potatoes": 116,
    "cassava": 125,
    "soya": 236,
    "vegetables_primary": 1735,
    "fruit_primary": 1738,
    "roots_tubers": 1720,
    "pulses_total": 1726,
    "milk_total": 1780,
    "eggs_primary": 1783,
    "meat_cattle": 867,
    "meat_chicken": 1058,
    "meat_pig": 1035,
    "meat_sheep": 977,
    "meat_goat": 1017,
    "meat_poultry": 1808,
    "beef_buffalo": 1806,
    "sheep_goat_meat": 1807,
}
ELEMENTS = {
    "area_harvested": 5312,
    "yield": 5412,
    "production": 5510,
    "value": 6121,
    "kcal": 6128,
    "gcap": 6123,
    "million_people": 6132,
    "gdp_cap": 6126,
    "fert_use": 5157,
    "fert_per_ha": 5159,
    "land_area": 5110,
    "temp_change": 7271,
    "co2eq": 723113,
    "pop_total": 511,
    "pop_rural": 551,
    "pop_urban": 561,
    "price_usd": 5532,
    "cohd_ppp": 6226,
}
FS_ITEMS = {
    "pou": "210041",            # Prevalence of undernourishment (%), 3-year average (countries + regions)
    "pou_annual": "210040",     # annual variant, regional aggregates only
    "n_undernourished": "210011",
    "des_adequacy": "21010",    # Average dietary energy supply adequacy (%)
    "des_kcal": "22000",        # Dietary energy supply kcal/cap/day 3-yr avg
    "protein": "21013",
    "animal_protein": "21014",
    "cereal_share": "21012",
    "fies_mod_sev": "210091",   # 3-year average; 210090 is the annual aggregate-only variant
    "fies_mod_sev_f": "210091F",
    "fies_mod_sev_m": "210091M",
    "fies_severe": "210401",
    "gdp_cap_ppp": "22013",
    "cereal_import_dep": "21035",
    "irrigation_share": "21034",
    "food_import_share": "21033",
    "stunting": "21025",
    "overweight_u5": "21041",
    "obesity": "21042",
    "anemia": "21043",
    "water_basic": "21047",
    "sanitation_basic": "21048",
    "supply_variability": "21031",
    "caloric_losses": "21059",
}
CAHD_ITEMS = {"cohd": "70040", "pua": "7005", "nua": "7006"}
RL_ITEMS = {"land_area": 6601, "agri_land": 6610, "cropland": 6620, "arable": 6621,
            "perm_crops": 6650, "pastures": 6655, "forest": 6646, "irrigated_equipped": 6690,
            "organic_agri": 6671}
GT_ITEMS = {"agrifood": 6518, "farm_gate": 6996, "land_use_change": 6516, "pre_post": 6517,
            "all_with_lulucf": 6825, "enteric": 5058, "manure_mgmt": 5059, "rice": 5060,
            "synthetic_fert": 5061, "ipcc_agriculture": 1711}
RFN_ITEMS = {"N": 3102, "P2O5": 3103, "K2O": 3104}
ET_ITEMS = {"met_year": 7020}
