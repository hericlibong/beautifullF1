"""Nommage canonique des Grands Prix — source unique de vérité.

Un GP est identifié dans TOUTE la chaîne par un libellé unique dérivé du couple
(Country, Location) fourni par FastF1 :

    colonne du CSV race chart  ==  clé "name" de calendar_<season>.json
                               ==  clé de circuits_<season>.json
                               ==  attribut data-gp du calendrier front-end

build_dashboard_data.py rapproche le CSV et le calendrier par égalité stricte de
ces chaînes. Deux GP qui partagent un libellé, c'est une colonne de cumul
écrasée et un GP qui n'apparaît jamais comme disputé — d'où ce module unique
plutôt qu'une règle recopiée dans chaque builder.

Règle :
    - "{Country}" par défaut ;
    - "{Country} - {Location}" quand le pays accueille plusieurs GP dans la même
      saison (2026 : États-Unis ×3, Italie, Espagne ×2) ;
    - sauf pour les GP listés dans COUNTRY_ONLY, déjà publiés sous le seul nom
      du pays — les renommer invaliderait les CSV et JSON déjà en ligne.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

# Pays accueillant plusieurs GP dans une même saison : le nom du pays ne suffit
# plus à désigner la course, on suffixe par la localité.
MULTI_GP_COUNTRIES = frozenset({"United States", "USA", "Italy", "Spain"})

# Exceptions : GP déjà publiés sous le seul nom du pays, qui le conservent.
COUNTRY_ONLY = frozenset(
    {
        # GP d'Espagne de Barcelone (round 7 en 2026) : publié sous "Spain"
        # depuis le début de la saison — colonne du CSV race chart, clé de
        # circuits_2026.json, entrée GP_TO_CIRCUIT côté front. Le second GP
        # espagnol, Madrid (round 14), prend donc "Spain - Madrid".
        ("Spain", "Barcelona"),
    }
)

# Libellés courts affichés dans le dashboard, indexés par nom canonique.
SHORT_NAMES = {
    "Australia": "Australia",
    "China": "China",
    "Japan": "Japan",
    "United States - Miami Gardens": "Miami",
    "Canada": "Canada",
    "Monaco": "Monaco",
    "Spain": "Barcelona",
    "Spain - Madrid": "Madrid",
    "Austria": "Austria",
    "United Kingdom": "Silverstone",
    "Belgium": "Spa",
    "Hungary": "Hungaroring",
    "Netherlands": "Zandvoort",
    "Italy - Monza": "Monza",
    "Azerbaijan": "Baku",
    # GP de Bahreïn délocalisé à Sepang (round 16 en 2026) : sans cette entrée,
    # short_name() retomberait sur la localité FastF1, "Kuala Lumpur".
    "Bahrain": "Sepang",
    "Singapore": "Singapore",
    "United States - Austin": "Austin",
    "Mexico": "Mexico",
    "Brazil": "Interlagos",
    "United States - Las Vegas": "Las Vegas",
    "Qatar": "Lusail",
    "United Arab Emirates": "Yas Marina",
}


def col_name(country: str, location: str) -> str:
    """Libellé canonique d'un GP à partir de son pays et de sa localité."""
    country = (country or "").strip()
    location = (location or "").strip()

    if (country, location) in COUNTRY_ONLY:
        return country
    if country in MULTI_GP_COUNTRIES and location:
        return f"{country} - {location}"
    return country


def short_name(name: str, location: str = "") -> str:
    """Libellé court d'affichage ; retombe sur la localité puis sur le nom."""
    return SHORT_NAMES.get(name) or location or name


def find_duplicates(names: Iterable[str]) -> list[str]:
    """Libellés apparaissant plus d'une fois, dans l'ordre de rencontre.

    Une collision signifie qu'un pays accueille un GP supplémentaire non prévu
    par MULTI_GP_COUNTRIES. Les builders s'en servent pour échouer bruyamment
    plutôt que d'écraser silencieusement les points d'un GP par ceux d'un autre.
    """
    names = list(names)
    counts = Counter(names)
    seen: set[str] = set()
    out = []
    for n in names:
        if counts[n] > 1 and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def check_unique(names: Iterable[str], context: str = "calendrier") -> None:
    """Lève ValueError si deux GP partagent le même libellé canonique."""
    dups = find_duplicates(names)
    if dups:
        raise ValueError(
            f"Collision de noms de GP dans {context} : {', '.join(dups)}. "
            "Ajoutez le pays concerné à MULTI_GP_COUNTRIES dans projects/gp_naming.py "
            "(et, si un des GP est déjà publié sous le seul nom du pays, ce GP à "
            "COUNTRY_ONLY) afin que chaque course garde sa propre colonne."
        )
