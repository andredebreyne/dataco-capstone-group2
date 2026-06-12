"""Country display-label helpers for Power BI serving tables."""

from __future__ import annotations

from pyspark.sql import Column
from pyspark.sql.functions import coalesce, col, create_map, initcap, lit, lower, regexp_replace, trim


PORTUGUESE_COUNTRY_LABEL_TOKENS = (
    "afeganistao",
    "alemanha",
    "arabia saudita",
    "argelia",
    "belgica",
    "brasil",
    "coreia do sul",
    "egito",
    "emirados arabes unidos",
    "espanha",
    "estados unidos",
    "finlandia",
    "franca",
    "grecia",
    "india",
    "indonesia",
    "italia",
    "japao",
    "marrocos",
    "paises baixos",
    "polonia",
    "portugal",
    "reino unido",
    "republica democratica do congo",
    "russia",
    "singapura",
    "suecia",
    "suica",
    "tailandia",
    "turquia",
    "vietna",
    "vietname",
)

COUNTRY_DISPLAY_LABELS = {
    "afeganistao": "Afghanistan",
    "alemanha": "Germany",
    "arabia saudita": "Saudi Arabia",
    "argelia": "Algeria",
    "australia": "Australia",
    "belgica": "Belgium",
    "brasil": "Brazil",
    "canada": "Canada",
    "chile": "Chile",
    "china": "China",
    "coreia do sul": "South Korea",
    "egito": "Egypt",
    "emirados arabes unidos": "United Arab Emirates",
    "espanha": "Spain",
    "estados unidos": "United States",
    "finlandia": "Finland",
    "franca": "France",
    "grecia": "Greece",
    "guatemala": "Guatemala",
    "india": "India",
    "indonesia": "Indonesia",
    "italia": "Italy",
    "japao": "Japan",
    "marrocos": "Morocco",
    "mexico": "Mexico",
    "paises baixos": "Netherlands",
    "peru": "Peru",
    "polonia": "Poland",
    "portugal": "Portugal",
    "reino unido": "United Kingdom",
    "republica democratica do congo": "Democratic Republic of the Congo",
    "republica democratica del congo": "Democratic Republic of the Congo",
    "russia": "Russia",
    "singapur": "Singapore",
    "singapura": "Singapore",
    "suecia": "Sweden",
    "suica": "Switzerland",
    "tailandia": "Thailand",
    "turquia": "Turkey",
    "venezuela": "Venezuela",
    "vietna": "Vietnam",
    "vietname": "Vietnam",
}


def _country_map_expression() -> Column:
    map_items = []
    for source_label, display_label in COUNTRY_DISPLAY_LABELS.items():
        map_items.extend([lit(source_label), lit(display_label)])
    return create_map(*map_items)


def normalize_country_lookup_value(country_column: Column | str) -> Column:
    """Normalize source country text for deterministic display-label lookup."""
    source = col(country_column) if isinstance(country_column, str) else country_column
    cleaned = trim(regexp_replace(source.cast("string"), r"[_-]+", " "))
    return lower(regexp_replace(cleaned, r"\s+", " "))


def standardize_country_display_label(country_column: Column | str) -> Column:
    """Return an English country display label for Power BI maps and slicers."""
    source = col(country_column) if isinstance(country_column, str) else country_column
    cleaned = trim(regexp_replace(source.cast("string"), r"[_-]+", " "))
    normalized = normalize_country_lookup_value(source)
    return coalesce(_country_map_expression().getItem(normalized), initcap(cleaned))
