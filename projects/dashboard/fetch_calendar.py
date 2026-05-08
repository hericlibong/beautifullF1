"""Régénère calendar_2026.json depuis FastF1.

À lancer ponctuellement (idéalement une seule fois en début de saison, et si le
calendrier officiel évolue). Le fichier produit est ensuite consommé par
build_dashboard_data.py.

Convention des noms de GP : alignée sur race_chart_builder._col_name :
    - "{Country} - {Location}" pour USA et Italy (pays à plusieurs GP)
    - "{Country}" sinon
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import fastf1

HERE = Path(__file__).resolve().parent
OUT = HERE / "calendar_2026.json"
SEASON = 2026

DUAL_LOCATION_COUNTRIES = {"United States", "USA", "Italy"}

SHORT_NAMES = {
    "Australia":                       "Australia",
    "China":                           "China",
    "Japan":                           "Japan",
    "United States - Miami Gardens":   "Miami",
    "Canada":                          "Canada",
    "Monaco":                          "Monaco",
    "Spain":                           "Madrid",
    "Austria":                         "Austria",
    "United Kingdom":                  "Silverstone",
    "Belgium":                         "Spa",
    "Hungary":                         "Hungaroring",
    "Netherlands":                     "Zandvoort",
    "Italy - Monza":                   "Monza",
    "Azerbaijan":                      "Baku",
    "Singapore":                       "Singapore",
    "United States - Austin":          "Austin",
    "Mexico":                          "Mexico",
    "Brazil":                          "Interlagos",
    "United States - Las Vegas":       "Las Vegas",
    "Qatar":                           "Lusail",
    "United Arab Emirates":            "Yas Marina",
}


def col_name(country: str, location: str) -> str:
    if country in DUAL_LOCATION_COUNTRIES:
        return f"{country} - {location}"
    return country


def short_name(name: str, location: str) -> str:
    return SHORT_NAMES.get(name) or location or name


def main() -> int:
    schedule = fastf1.get_event_schedule(SEASON, include_testing=False)
    rounds = []
    for _, row in schedule.iterrows():
        country = str(row.get("Country", ""))
        location = str(row.get("Location", ""))
        name = col_name(country, location)
        rounds.append({
            "round":     int(row["RoundNumber"]),
            "name":      name,
            "shortName": short_name(name, location),
            "date":      str(row["EventDate"])[:10],
            "isSprint":  str(row.get("EventFormat", "")).startswith("sprint"),
        })

    payload = {
        "season":     SEASON,
        "totalRaces": len(rounds),
        "rounds":     rounds,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {OUT.relative_to(HERE.parents[1])} ({len(rounds)} GP)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
