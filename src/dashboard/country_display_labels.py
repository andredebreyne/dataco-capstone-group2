"""Country display-label helpers for Power BI serving tables."""

from __future__ import annotations

from pyspark.sql import Column
from pyspark.sql.functions import coalesce, col, create_map, initcap, lit, lower, regexp_replace, translate, trim


ACCENTED_CHARACTERS = (
    "\u00c1\u00c0\u00c2\u00c3\u00c4"
    "\u00e1\u00e0\u00e2\u00e3\u00e4"
    "\u00c9\u00c8\u00ca\u00cb"
    "\u00e9\u00e8\u00ea\u00eb"
    "\u00cd\u00cc\u00ce\u00cf"
    "\u00ed\u00ec\u00ee\u00ef"
    "\u00d3\u00d2\u00d4\u00d5\u00d6"
    "\u00f3\u00f2\u00f4\u00f5\u00f6"
    "\u00da\u00d9\u00db\u00dc"
    "\u00fa\u00f9\u00fb\u00fc"
    "\u00c7\u00e7\u00d1\u00f1"
)
ASCII_REPLACEMENTS = "AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCcNn"

COUNTRY_DISPLAY_LABELS = {
    "afeganistao": "Afghanistan",
    "afganistan": "Afghanistan",
    "alemania": "Germany",
    "alemanha": "Germany",
    "arabia saudita": "Saudi Arabia",
    "argelia": "Algeria",
    "belgica": "Belgium",
    "blgica": "Belgium",
    "brasil": "Brazil",
    "corea del sur": "South Korea",
    "coreia do sul": "South Korea",
    "egipto": "Egypt",
    "emiratos arabes unidos": "United Arab Emirates",
    "emirados arabes unidos": "United Arab Emirates",
    "espaa": "Spain",
    "espana": "Spain",
    "espanha": "Spain",
    "estados unidos": "United States",
    "finlandia": "Finland",
    "francia": "France",
    "franca": "France",
    "grecia": "Greece",
    "italia": "Italy",
    "japon": "Japan",
    "japao": "Japan",
    "marruecos": "Morocco",
    "marrocos": "Morocco",
    "mexico": "Mexico",
    "mxico": "Mexico",
    "paises bajos": "Netherlands",
    "pases bajos": "Netherlands",
    "polonia": "Poland",
    "reino unido": "United Kingdom",
    "republica democratica del congo": "Democratic Republic of the Congo",
    "repblica democrtica del congo": "Democratic Republic of the Congo",
    "republica dominicana": "Dominican Republic",
    "rusia": "Russia",
    "singapur": "Singapore",
    "singapura": "Singapore",
    "suecia": "Sweden",
    "suiza": "Switzerland",
    "suica": "Switzerland",
    "tailandia": "Thailand",
    "turquia": "Turkey",
    "vietna": "Vietnam",
    "vietnam": "Vietnam",
}

TECHNICAL_COUNTRY_TOKENS = tuple(
    sorted(
        {
            "blgica",
            "espaa",
            "mxico",
            "pases bajos",
            "repblica dominicana",
            "repblica democrtica del congo",
        }
    )
)


def _country_map_expression() -> Column:
    map_items = []
    for source_label, display_label in COUNTRY_DISPLAY_LABELS.items():
        map_items.extend([lit(source_label), lit(display_label)])
    return create_map(*map_items)


def normalize_country_lookup_value(country_column: Column | str) -> Column:
    """Normalize country text for display-label lookup."""
    source = col(country_column) if isinstance(country_column, str) else country_column
    cleaned = trim(regexp_replace(source.cast("string"), r"[_-]+", " "))
    ascii_cleaned = translate(cleaned, ACCENTED_CHARACTERS, ASCII_REPLACEMENTS)
    normalized = lower(regexp_replace(ascii_cleaned, r"\s+", " "))
    return regexp_replace(normalized, r"[^a-z0-9 ]", "")


def standardize_country_display_label(country_column: Column | str) -> Column:
    """Return an English country display label for dashboard fields."""
    source = col(country_column) if isinstance(country_column, str) else country_column
    cleaned = trim(regexp_replace(source.cast("string"), r"[_-]+", " "))
    normalized = normalize_country_lookup_value(source)
    return coalesce(_country_map_expression().getItem(normalized), initcap(cleaned))
