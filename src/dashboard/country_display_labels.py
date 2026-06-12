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
    "albania": "Albania",
    "alemania": "Germany",
    "alemanha": "Germany",
    "angola": "Angola",
    "arabia saudi": "Saudi Arabia",
    "arabia saudita": "Saudi Arabia",
    "argentina": "Argentina",
    "argelia": "Algeria",
    "armenia": "Armenia",
    "australia": "Australia",
    "austria": "Austria",
    "azerbaiyan": "Azerbaijan",
    "banglades": "Bangladesh",
    "barbados": "Barbados",
    "barein": "Bahrain",
    "belgica": "Belgium",
    "belice": "Belize",
    "benin": "Benin",
    "bielorrusia": "Belarus",
    "blgica": "Belgium",
    "bolivia": "Bolivia",
    "bosnia y herzegovina": "Bosnia and Herzegovina",
    "botsuana": "Botswana",
    "brasil": "Brazil",
    "bulgaria": "Bulgaria",
    "burkina faso": "Burkina Faso",
    "burundi": "Burundi",
    "butan": "Bhutan",
    "camboya": "Cambodia",
    "camerun": "Cameroon",
    "canada": "Canada",
    "chad": "Chad",
    "chile": "Chile",
    "china": "China",
    "chipre": "Cyprus",
    "colombia": "Colombia",
    "corea del sur": "South Korea",
    "coreia do sul": "South Korea",
    "costa de marfil": "Ivory Coast",
    "costa rica": "Costa Rica",
    "croacia": "Croatia",
    "cuba": "Cuba",
    "dinamarca": "Denmark",
    "ecuador": "Ecuador",
    "egipto": "Egypt",
    "el salvador": "El Salvador",
    "emiratos arabes unidos": "United Arab Emirates",
    "emirados arabes unidos": "United Arab Emirates",
    "eritrea": "Eritrea",
    "eslovaquia": "Slovakia",
    "eslovenia": "Slovenia",
    "espaa": "Spain",
    "espana": "Spain",
    "espanha": "Spain",
    "estados unidos": "United States",
    "estonia": "Estonia",
    "etiopia": "Ethiopia",
    "filipinas": "Philippines",
    "finlandia": "Finland",
    "francia": "France",
    "franca": "France",
    "gabon": "Gabon",
    "georgia": "Georgia",
    "ghana": "Ghana",
    "grecia": "Greece",
    "guadalupe": "Guadeloupe",
    "guatemala": "Guatemala",
    "guayana francesa": "French Guiana",
    "guinea": "Guinea",
    "guinea bissau": "Guinea-Bissau",
    "guinea ecuatorial": "Equatorial Guinea",
    "guyana": "Guyana",
    "haiti": "Haiti",
    "honduras": "Honduras",
    "hong kong": "Hong Kong",
    "hungria": "Hungary",
    "india": "India",
    "indonesia": "Indonesia",
    "irak": "Iraq",
    "iran": "Iran",
    "irlanda": "Ireland",
    "israel": "Israel",
    "italia": "Italy",
    "jamaica": "Jamaica",
    "jordania": "Jordan",
    "japon": "Japan",
    "japao": "Japan",
    "kazajistan": "Kazakhstan",
    "kenia": "Kenya",
    "kirguistan": "Kyrgyzstan",
    "kuwait": "Kuwait",
    "laos": "Laos",
    "lesoto": "Lesotho",
    "libano": "Lebanon",
    "liberia": "Liberia",
    "libia": "Libya",
    "lituania": "Lithuania",
    "luxemburgo": "Luxembourg",
    "macedonia": "North Macedonia",
    "madagascar": "Madagascar",
    "malasia": "Malaysia",
    "mali": "Mali",
    "martinica": "Martinique",
    "marruecos": "Morocco",
    "marrocos": "Morocco",
    "mauritania": "Mauritania",
    "mexico": "Mexico",
    "moldavia": "Moldova",
    "mongolia": "Mongolia",
    "montenegro": "Montenegro",
    "mozambique": "Mozambique",
    "myanmar birmania": "Myanmar",
    "mxico": "Mexico",
    "namibia": "Namibia",
    "nepal": "Nepal",
    "nicaragua": "Nicaragua",
    "nigeria": "Nigeria",
    "niger": "Niger",
    "noruega": "Norway",
    "nueva zelanda": "New Zealand",
    "oman": "Oman",
    "pakistan": "Pakistan",
    "panama": "Panama",
    "papua nueva guinea": "Papua New Guinea",
    "paraguay": "Paraguay",
    "paises bajos": "Netherlands",
    "pases bajos": "Netherlands",
    "peru": "Peru",
    "polonia": "Poland",
    "portugal": "Portugal",
    "qatar": "Qatar",
    "reino unido": "United Kingdom",
    "republica centroafricana": "Central African Republic",
    "republica checa": "Czech Republic",
    "republica democratica del congo": "Democratic Republic of the Congo",
    "republica de gambia": "Gambia",
    "republica del congo": "Republic of the Congo",
    "repblica democrtica del congo": "Democratic Republic of the Congo",
    "republica dominicana": "Dominican Republic",
    "ruanda": "Rwanda",
    "rumania": "Romania",
    "rusia": "Russia",
    "sahara occidental": "Western Sahara",
    "senegal": "Senegal",
    "serbia": "Serbia",
    "sierra leona": "Sierra Leone",
    "singapur": "Singapore",
    "singapura": "Singapore",
    "siria": "Syria",
    "somalia": "Somalia",
    "sri lanka": "Sri Lanka",
    "suazilandia": "Eswatini",
    "sudafrica": "South Africa",
    "sudan": "Sudan",
    "sudan del sur": "South Sudan",
    "suecia": "Sweden",
    "suiza": "Switzerland",
    "suica": "Switzerland",
    "surinam": "Suriname",
    "taiwan": "Taiwan",
    "tailandia": "Thailand",
    "tanzania": "Tanzania",
    "tayikistan": "Tajikistan",
    "togo": "Togo",
    "trinidad y tobago": "Trinidad and Tobago",
    "tunez": "Tunisia",
    "turkmenistan": "Turkmenistan",
    "turquia": "Turkey",
    "ucrania": "Ukraine",
    "uganda": "Uganda",
    "uruguay": "Uruguay",
    "uzbekistan": "Uzbekistan",
    "venezuela": "Venezuela",
    "vietna": "Vietnam",
    "vietnam": "Vietnam",
    "yemen": "Yemen",
    "yibuti": "Djibouti",
    "zambia": "Zambia",
    "zimbabue": "Zimbabwe",
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
